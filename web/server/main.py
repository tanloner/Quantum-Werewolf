"""FastAPI entry point for Quantum Werewolf web server."""

import logging
import os
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from game_manager import game_manager
from models import (
    CreateGameRequest, CreateGameResponse,
    JoinGameRequest, JoinGameResponse,
    DeckConfig, GamePhase
)
from websocket_manager import (
    sio, broadcast_player_joined, broadcast_game_started
)

# Configure logging with enhanced format
DEBUG_MODE = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes')
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if DEBUG_MODE:
    logger.info("🐛 DEBUG MODE ENABLED - Verbose logging active")
else:
    logger.info("Running in normal mode. Set DEBUG=true to enable verbose logging")

# Get static files path
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Quantum Werewolf server starting...")
    yield
    logger.info("Quantum Werewolf server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Quantum Werewolf",
    description="Multiplayer Quantum Werewolf game server",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = os.environ.get('CORS_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


# Dependency for extracting player token
async def get_player_token(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return authorization[7:]


# REST API Endpoints

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "quantum-werewolf"}


@app.get("/api/games/health")
async def games_health_check():
    """Health check endpoint for games service."""
    return {"status": "ok", "active_games": len(game_manager.games)}


@app.post("/api/games", response_model=CreateGameResponse)
async def create_game(request: CreateGameRequest):
    """Create a new game."""
    game_id, gm_token, player_token = game_manager.create_game(request.host_name)

    host = os.environ.get('PUBLIC_HOST', 'localhost:8000')
    protocol = 'https' if os.environ.get('USE_HTTPS', 'false').lower() == 'true' else 'http'

    return CreateGameResponse(
        game_id=game_id,
        gm_token=gm_token,
        player_token=player_token,
        join_url=f"{protocol}://{host}/join/{game_id}"
    )


@app.get("/api/games/{game_id}")
async def get_game_info(game_id: str):
    """Get public game information."""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return {
        "game_id": game.game_id,
        "player_count": len(game.get_players()),
        "players": game.get_players(),
        "phase": game.phase.value,
        "can_join": game.phase == GamePhase.LOBBY
    }


@app.post("/api/games/{game_id}/join", response_model=JoinGameResponse)
async def join_game(game_id: str, request: JoinGameRequest):
    """Join an existing game."""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.phase != GamePhase.LOBBY:
        raise HTTPException(status_code=400, detail="Game already started")

    token = game.add_player(request.player_name)
    if not token:
        raise HTTPException(status_code=400, detail="Could not join game (name taken?)")

    # Broadcast to other players
    await broadcast_player_joined(game_id, request.player_name, len(game.get_players()))

    return JoinGameResponse(
        player_token=token,
        player_name=request.player_name,
        players=game.get_players()
    )


@app.put("/api/games/{game_id}/deck")
async def configure_deck(
        game_id: str,
        config: DeckConfig,
        token: str = Depends(get_player_token)
):
    """Configure the deck (GM only)."""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.is_gm(token):
        raise HTTPException(status_code=403, detail="Only GM can configure deck")

    if not game.configure_deck(config):
        raise HTTPException(status_code=400, detail="Cannot configure deck after game started")

    return {"success": True, "deck": config.model_dump()}


@app.post("/api/games/{game_id}/start")
async def start_game(
        game_id: str,
        token: str = Depends(get_player_token)
):
    """Start the game (GM only)."""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.is_gm(token):
        raise HTTPException(status_code=403, detail="Only GM can start game")

    if not game.start_game():
        raise HTTPException(status_code=400, detail="Cannot start game (need at least 3 players)")

    # Broadcast game started
    await broadcast_game_started(game_id, game)

    return {"success": True, "phase": "night", "turn": 1}


@app.delete("/api/games/{game_id}")
async def delete_game(
        game_id: str,
        token: str = Depends(get_player_token)
):
    """Delete a game (GM only)."""
    game = game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.is_gm(token):
        raise HTTPException(status_code=403, detail="Only GM can delete game")

    game_manager.delete_game(game_id)
    return {"success": True}


# Static file serving

@app.get("/")
async def serve_index():
    """Serve the main page."""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@app.get("/join/{game_id}")
async def serve_join_page(game_id: str):
    """Serve the join page (same as index, JS handles routing)."""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@app.get("/game/{game_id}")
async def serve_game_page(game_id: str):
    """Serve the game page."""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@app.get("/gm/{game_id}")
async def serve_gm_page(game_id: str):
    """Serve the GM dashboard page."""
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


# Mount static files (must be after specific routes)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Run with: uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(socket_app, host=host, port=port)
