# Quantum Werewolf Server

Backend server for the Quantum Werewolf web application, built with FastAPI and Socket.IO.

## Architecture Overview

```
server/
├── main.py              # FastAPI application entry point
├── game_adapter.py      # Web wrapper for backend.Game
├── game_manager.py      # In-memory game instance management
├── models.py            # Pydantic data models
├── websocket_manager.py # Socket.IO event handlers
└── requirements.txt     # Python dependencies
```

## Module Documentation

### main.py

The FastAPI application entry point that:
- Configures CORS middleware
- Integrates Socket.IO with FastAPI via ASGI
- Defines REST API endpoints
- Serves static files
- Handles SPA routing

**Key Components:**
- `socket_app`: Combined FastAPI + Socket.IO ASGI application
- `get_player_token()`: Dependency for extracting Bearer tokens from Authorization header

### game_adapter.py

Wraps the core `quantumwerewolf.backend.Game` class with web-specific functionality.

**Class: `GameAdapter`**

Manages a single game instance with:
- Player authentication via tokens
- Game phase management (lobby → night → day → voting → ended)
- Turn-based night phase with action tracking
- Voting system with confirmation
- Anonymous stats generation

**Key Methods:**

| Method | Description |
|--------|-------------|
| `add_player(name)` | Add player to game, returns token |
| `start_game()` | Initialize game, generate permutations |
| `get_turn_info(player)` | Get player's turn data (probabilities, available actions) |
| `submit_seer_action(player, target)` | Execute seer observation |
| `submit_werewolf_action(player, target)` | Record werewolf attack |
| `submit_cupid_action(player, l1, l2)` | Pair two lovers |
| `end_player_turn(player)` | Complete player's turn, advance to next |
| `get_anonymous_stats()` | Get shuffled probability table |
| `start_voting()` | Begin voting phase |
| `submit_vote(player, target)` | Record a vote |
| `confirm_vote(player)` | Lock in vote |
| `end_voting()` | Tally votes, execute lynch |
| `start_night()` | Begin next night phase |

**Game Phases:**

```
LOBBY → NIGHT → DAY → VOTING → DAY → NIGHT → ... → ENDED
                  ↑___________|
```

### game_manager.py

Manages multiple concurrent game instances in memory.

**Class: `GameManager`**

| Method | Description |
|--------|-------------|
| `create_game(host_name)` | Create new game, returns (game_id, gm_token, player_token) |
| `get_game(game_id)` | Retrieve game by ID |
| `delete_game(game_id)` | Remove game from memory |
| `get_player_by_token(game_id, token)` | Resolve player name from token |
| `is_gm_token(game_id, token)` | Check if token is GM token |

**Singleton:**
```python
from game_manager import game_manager
```

### models.py

Pydantic models for request/response validation and data structures.

**Request Models:**
- `CreateGameRequest` - host_name
- `JoinGameRequest` - player_name
- `DeckConfig` - werewolf, seer, hunter, cupid counts
- `ActionRequest` - target
- `CupidActionRequest` - lover1, lover2
- `ForceActionRequest` - player, action, target(s)

**Response Models:**
- `CreateGameResponse` - game_id, gm_token, player_token, join_url
- `JoinGameResponse` - player_token, player_name, players

**State Models:**
- `GamePhase` - Enum: LOBBY, NIGHT, DAY, VOTING, ENDED
- `PlayerStats` - number, probabilities, death_probability, is_dead, revealed info
- `TurnInfo` - probabilities, your_number, other_werewolves, available_actions
- `VoteResult` - lynched_player, lynched_role, vote_counts, abstentions
- `GameState` - Full game state for player reconnection
- `GMState` - Game Master state with action log

### websocket_manager.py

Socket.IO server configuration and event handlers.

**Connection Manager:**

Tracks:
- `player_connections`: game_id → {player_name: socket_id}
- `gm_connections`: game_id → socket_id
- `sid_info`: socket_id → (game_id, player_name, is_gm)

**Client → Server Events:**

| Event | Data | Description |
|-------|------|-------------|
| `seer_action` | {target} | Seer observes a player |
| `werewolf_action` | {target} | Werewolf attacks a player |
| `cupid_action` | {lover1, lover2} | Cupid pairs lovers |
| `end_turn` | {} | Player ends their turn |
| `vote` | {target} | Submit vote (null for abstain) |
| `confirm_vote` | {} | Confirm vote |
| `request_stats` | {} | Request current stats |
| `gm_skip_turn` | {} | GM skips current player |
| `gm_start_voting` | {} | GM starts voting |
| `gm_end_voting` | {} | GM ends voting early |
| `gm_start_night` | {} | GM starts next night |

**Server → Client Events:**

| Event | Data | Recipient |
|-------|------|-----------|
| `game_state` | GameState | Single player (on connect) |
| `player_joined` | {player_name, player_count} | All |
| `game_started` | {phase, turn} | All |
| `your_turn` | TurnInfo | Single player |
| `turn_ended` | {} | Single player |
| `turn_skipped` | {} | Single player |
| `phase_change` | {phase, turn, deaths} | All |
| `stats_update` | {stats: PlayerStats[]} | All |
| `your_number` | {number} | Single player |
| `voting_started` | {living_players} | All |
| `vote_progress` | {votes_cast, total, confirmations} | All |
| `voting_ended` | VoteResult | All |
| `game_over` | {winner, final_roles} | All |
| `gm_state` | GMState | GM only |

## REST API Endpoints

### Health

```
GET /api/health
→ {"status": "ok", "service": "quantum-werewolf"}

GET /api/games/health
→ {"status": "ok", "active_games": 3}
```

### Game Management

```
POST /api/games
Body: {"host_name": "Alice"}
→ {"game_id": "ABC123", "gm_token": "...", "player_token": "...", "join_url": "..."}

GET /api/games/{game_id}
→ {"game_id": "ABC123", "player_count": 4, "players": [...], "phase": "lobby", "can_join": true}

DELETE /api/games/{game_id}
Header: Authorization: Bearer {gm_token}
→ {"success": true}
```

### Player Management

```
POST /api/games/{game_id}/join
Body: {"player_name": "Bob"}
→ {"player_token": "...", "player_name": "Bob", "players": ["Alice", "Bob"]}
```

### Game Configuration

```
PUT /api/games/{game_id}/deck
Header: Authorization: Bearer {gm_token}
Body: {"werewolf": 2, "seer": 1, "hunter": 0, "cupid": 0}
→ {"success": true, "deck": {...}}

POST /api/games/{game_id}/start
Header: Authorization: Bearer {gm_token}
→ {"success": true, "phase": "night", "turn": 1}
```

## Authentication

### Player Token
- Generated when player joins game
- Used in WebSocket auth and optional REST calls
- Format: `Bearer {token}` in Authorization header

### GM Token
- Generated when game is created
- Same player also gets a player token
- Required for administrative actions (start, deck config, skip turns)

## Error Handling

All errors return JSON:
```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `400` - Bad request (invalid input, game already started, etc.)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (not GM for admin action)
- `404` - Not found (game doesn't exist)

## Running the Server

```bash
# Development
cd server
pip install -r requirements.txt
python main.py

# Production
uvicorn main:socket_app --host 0.0.0.0 --port 8000

# Docker
docker build -f web/Dockerfile .
docker run -p 8000:8000 quantum-werewolf
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `PUBLIC_HOST` | `localhost:8000` | Public hostname for generated URLs |
| `USE_HTTPS` | `false` | Use HTTPS in generated URLs |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## Testing

```bash
cd server
pytest tests/ -v
```

See `tests/` directory for test coverage.
