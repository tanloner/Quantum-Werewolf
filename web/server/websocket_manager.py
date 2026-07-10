"""WebSocket connection and event management for Quantum Werewolf."""

import logging
import os
from typing import Dict, Set, Optional

import socketio
from game_manager import game_manager
from models import GamePhase

logger = logging.getLogger(__name__)

# Debug mode can be enabled via DEBUG=true environment variable
DEBUG = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes')
DEBUG = 1


def debug_log(msg: str):
    """Log a debug message if DEBUG mode is enabled."""
    if DEBUG:
        logger.info(f"[DEBUG] {msg}")


def info_log(msg: str):
    """Always log info messages."""
    logger.info(f"[WS] {msg}")


# Create Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', logger=False, engineio_logger=False)


class ConnectionManager:
    """Manages WebSocket connections per game."""

    def __init__(self):
        # game_id -> {player_name: sid}
        self.player_connections: Dict[str, Dict[str, str]] = {}
        # game_id -> gm_sid
        self.gm_connections: Dict[str, str] = {}
        # sid -> (game_id, player_name, is_gm)
        self.sid_info: Dict[str, tuple] = {}

    def add_player(self, game_id: str, player_name: str, sid: str):
        """Register a player connection."""
        if game_id not in self.player_connections:
            self.player_connections[game_id] = {}
        self.player_connections[game_id][player_name] = sid
        self.sid_info[sid] = (game_id, player_name, False)

    def add_gm(self, game_id: str, sid: str):
        """Register a GM connection."""
        self.gm_connections[game_id] = sid
        self.sid_info[sid] = (game_id, None, True)

    def remove_connection(self, sid: str):
        """Remove a connection by SID."""
        info = self.sid_info.pop(sid, None)
        if not info:
            return

        game_id, player_name, is_gm = info

        if is_gm:
            if game_id in self.gm_connections and self.gm_connections[game_id] == sid:
                del self.gm_connections[game_id]
        else:
            if game_id in self.player_connections:
                if player_name in self.player_connections[game_id]:
                    if self.player_connections[game_id][player_name] == sid:
                        del self.player_connections[game_id][player_name]

    def get_player_sid(self, game_id: str, player_name: str) -> Optional[str]:
        """Get SID for a specific player."""
        return self.player_connections.get(game_id, {}).get(player_name)

    def get_gm_sid(self, game_id: str) -> Optional[str]:
        """Get SID for the GM of a game."""
        return self.gm_connections.get(game_id)

    def get_all_player_sids(self, game_id: str) -> list:
        """Get all player SIDs for a game."""
        return list(self.player_connections.get(game_id, {}).values())

    def get_info(self, sid: str) -> Optional[tuple]:
        """Get (game_id, player_name, is_gm) for a SID."""
        return self.sid_info.get(sid)


# Global connection manager
connections = ConnectionManager()


# Socket.IO event handlers

@sio.event
async def connect(sid, environ, auth):
    """Handle new WebSocket connection."""
    info_log(f"Connection attempt: {sid}")
    debug_log(f"Connection auth data: {auth}")

    if not auth:
        logger.warning(f"[WS] No auth provided for {sid}")
        return False

    game_id = auth.get('game_id')
    token = auth.get('token')

    debug_log(f"Auth extracted - game_id={game_id}, token={token[:20] if token else None}...")

    if not game_id or not token:
        logger.warning(f"[WS] Missing game_id or token for {sid}")
        return False

    game = game_manager.get_game(game_id)
    if not game:
        logger.warning(f"[WS] Game not found: {game_id}")
        return False

    # Check if GM
    if game.is_gm(token):
        connections.add_gm(game_id, sid)
        await sio.enter_room(sid, f"game:{game_id}")
        await sio.enter_room(sid, f"gm:{game_id}")
        info_log(f"✓ GM connected to game {game_id} (sid={sid})")
        debug_log(f"GM is_gm check passed for token")

        # Send GM state
        await sio.emit('gm_state', game.get_gm_state().model_dump(), to=sid)
        return True

    # Check if player
    player_name = game.get_player_name(token)
    if not player_name:
        logger.warning(f"[WS] Invalid player token for game {game_id} (sid={sid})")
        debug_log(f"get_player_name returned None for token")
        return False

    connections.add_player(game_id, player_name, sid)
    await sio.enter_room(sid, f"game:{game_id}")
    await sio.enter_room(sid, f"player:{game_id}:{player_name}")
    info_log(f"✓ Player '{player_name}' connected to game {game_id} (sid={sid})")

    # Send game state
    await sio.emit('game_state', game.get_game_state(player_name).model_dump(), to=sid)

    # If it's their turn, send turn info
    if game.phase == GamePhase.NIGHT and game.get_current_turn_player() == player_name:
        await sio.emit('your_turn', game.get_turn_info(player_name).model_dump(), to=sid)

    return True


@sio.event
async def disconnect(sid):
    """Handle WebSocket disconnection."""
    info = connections.get_info(sid)
    if info:
        game_id, player_name, is_gm = info
        if is_gm:
            logger.info(f"GM disconnected from game {game_id}")
        else:
            logger.info(f"Player {player_name} disconnected from game {game_id}")

    connections.remove_connection(sid)


@sio.event
async def seer_action(sid, data):
    """Handle seer action."""
    info = connections.get_info(sid)
    if not info or info[2]:  # Not found or is GM
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    if game.get_current_turn_player() != player_name:
        return {'error': 'Not your turn'}

    target = data.get('target')
    if not target:
        return {'error': 'No target specified'}

    result = game.submit_seer_action(player_name, target)
    if result is None:
        return {'error': 'Action failed'}

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True, 'role': result}


@sio.event
async def werewolf_action(sid, data):
    """Handle werewolf action."""
    info = connections.get_info(sid)
    if not info or info[2]:
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    if game.get_current_turn_player() != player_name:
        return {'error': 'Not your turn'}

    target = data.get('target')
    if not target:
        return {'error': 'No target specified'}

    success = game.submit_werewolf_action(player_name, target)
    if not success:
        return {'error': 'Action failed'}

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True}


@sio.event
async def cupid_action(sid, data):
    """Handle cupid action."""
    info = connections.get_info(sid)
    if not info or info[2]:
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    if game.get_current_turn_player() != player_name:
        return {'error': 'Not your turn'}

    lover1 = data.get('lover1')
    lover2 = data.get('lover2')
    if not lover1 or not lover2:
        return {'error': 'Must specify both lovers'}

    success = game.submit_cupid_action(player_name, lover1, lover2)
    if not success:
        return {'error': 'Action failed'}

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True}


@sio.event
async def end_turn(sid, data):
    """Handle end of player's turn."""
    info = connections.get_info(sid)
    if not info or info[2]:
        logger.warning(f"[WS] end_turn: Invalid session for {sid}")
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    debug_log(f"end_turn: {player_name} (sid={sid}) ending turn in game {game_id}")

    game = game_manager.get_game(game_id)
    if not game:
        logger.warning(f"[WS] end_turn: Game not found: {game_id}")
        return {'error': 'Game not found'}

    previous_phase = game.phase
    debug_log(f"end_turn: Current phase before = {previous_phase}, turn={game.turn}")

    success = game.end_player_turn(player_name)
    if not success:
        logger.warning(f"[WS] end_turn: Cannot end turn for {player_name}")
        return {'error': 'Cannot end turn'}

    debug_log(f"end_turn: Phase after = {game.phase}, turn={game.turn}")
    info_log(f"end_turn: {player_name} ended turn (phase: {previous_phase} → {game.phase})")

    # Notify the player their turn ended
    await sio.emit('turn_ended', {}, to=sid)

    # Check if phase changed (night ended)
    if game.phase != previous_phase:
        info_log(f"end_turn: ⚠ PHASE TRANSITION {previous_phase} → {game.phase}, broadcasting to game:{game_id}")
        await _broadcast_phase_change(game_id, game)
        # Include updated state in response so client gets immediate feedback
        response = {'success': True, 'phase': game.phase.value, 'turn': game.turn,
                    'deaths_this_round': game.deaths_this_round}
        debug_log(f"end_turn: Sending phase change response to {player_name}: {response}")

        # Notify GM
        await _notify_gm(game_id, game)
        return response
    else:
        # Notify next player
        next_player = game.get_current_turn_player()
        debug_log(f"end_turn: Next player is {next_player}")
        if next_player:
            next_sid = connections.get_player_sid(game_id, next_player)
            if next_sid:
                debug_log(f"end_turn: Notifying {next_player} (sid={next_sid}) it's their turn")
                await sio.emit('your_turn', game.get_turn_info(next_player).model_dump(), to=next_sid)

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True}


@sio.event
async def vote(sid, data):
    """Handle vote submission."""
    info = connections.get_info(sid)
    if not info or info[2]:
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    if game.phase != GamePhase.VOTING:
        return {'error': 'Not in voting phase'}

    target = data.get('target')  # Can be None for abstain
    success = game.submit_vote(player_name, target)
    if not success:
        return {'error': 'Vote failed'}

    # Broadcast vote progress
    await sio.emit('vote_progress', game.get_vote_progress(), room=f"game:{game_id}")

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True}


@sio.event
async def confirm_vote(sid, data):
    """Handle vote confirmation."""
    info = connections.get_info(sid)
    if not info or info[2]:
        return {'error': 'Invalid session'}

    game_id, player_name, _ = info
    debug_log(f"confirm_vote: {player_name} confirming vote in game {game_id}")

    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    success = game.confirm_vote(player_name)
    if not success:
        logger.warning(f"[WS] confirm_vote: Confirmation failed for {player_name} in {game_id}")
        return {'error': 'Confirmation failed'}

    progress = game.get_vote_progress()
    debug_log(f"confirm_vote: Vote progress - {progress}")

    # Broadcast progress
    await sio.emit('vote_progress', progress, room=f"game:{game_id}")

    # If all confirmed, end voting automatically
    if progress['all_confirmed']:
        debug_log(f"confirm_vote: All votes confirmed! Ending voting phase...")
        info_log(f"confirm_vote: All votes confirmed - ending voting phase in game {game_id}")

        result = game.end_voting()
        debug_log(f"confirm_vote: Voting ended, result={result.model_dump()}, new phase={game.phase}")

        await sio.emit('voting_ended', result.model_dump(), room=f"game:{game_id}")

        if game.phase == GamePhase.ENDED:
            info_log(f"confirm_vote: Game ended in {game_id}")
            await _broadcast_game_over(game_id, game)

        # Notify GM
        await _notify_gm(game_id, game)

        # Return with updated phase info when voting ends
        response = {'success': True, 'phase': game.phase.value, 'voting_ended': True, 'result': result.model_dump()}
        debug_log(f"confirm_vote: Sending response to {player_name}: phase={response['phase']}")
        return response

    # Notify GM
    await _notify_gm(game_id, game)

    return {'success': True}


# GM-specific events

@sio.event
async def gm_skip_turn(sid, data):
    """GM skips current player's turn."""
    info = connections.get_info(sid)
    if not info:
        return {'error': 'Not authorized'}

    game_id, player_name, is_gm = info
    game = game_manager.get_game(game_id)

    if not game:
        return {'error': 'Game not found'}

    # NEU: Erlaube echte GMs ODER den Host-Spieler
    if not is_gm and player_name != game.gm_player:
        return {'error': 'Not authorized'}

    if not game:
        return {'error': 'Game not found'}

    previous_phase = game.phase
    skipped = game.skip_current_turn()
    if not skipped:
        return {'error': 'Cannot skip turn'}

    # Notify skipped player
    skipped_sid = connections.get_player_sid(game_id, skipped)
    if skipped_sid:
        await sio.emit('turn_skipped', {}, to=skipped_sid)

    # Check if phase changed
    if game.phase != previous_phase:
        await _broadcast_phase_change(game_id, game)
        # Update GM
        await _notify_gm(game_id, game)
        return {'success': True, 'skipped': skipped, 'phase': game.phase.value, 'phase_changed': True}
    else:
        # Notify next player
        next_player = game.get_current_turn_player()
        if next_player:
            next_sid = connections.get_player_sid(game_id, next_player)
            if next_sid:
                await sio.emit('your_turn', game.get_turn_info(next_player).model_dump(), to=next_sid)

    # Update GM
    await _notify_gm(game_id, game)

    return {'success': True, 'skipped': skipped}


@sio.event
async def gm_end_voting(sid, data):
    """GM ends voting phase early."""
    info = connections.get_info(sid)
    if not info:
        return {'error': 'Not authorized'}

    game_id, player_name, is_gm = info
    game = game_manager.get_game(game_id)

    if not game:
        return {'error': 'Game not found'}

    # NEU: Erlaube echte GMs ODER den Host-Spieler
    if not is_gm and player_name != game.gm_player:
        return {'error': 'Not authorized'}

    if not game:
        return {'error': 'Game not found'}

    if game.phase != GamePhase.VOTING:
        return {'error': 'Not in voting phase'}

    result = game.end_voting()
    await sio.emit('voting_ended', result.model_dump(), room=f"game:{game_id}")

    if game.phase == GamePhase.ENDED:
        await _broadcast_game_over(game_id, game)

    # Update GM
    await _notify_gm(game_id, game)

    return {'success': True, 'result': result.model_dump()}


@sio.event
async def gm_start_voting(sid, data):
    """GM starts voting phase."""
    debug_log(f"gm_start_voting: Request from {sid}")

    info = connections.get_info(sid)

    if not info:
        logger.warning(f"[WS] gm_start_voting: Connection not found for {sid}")
        return {'error': 'Not authorized - connection not found'}

    game_id, player_name, is_gm = info

    game = game_manager.get_game(game_id)
    if not game:
        logger.warning(f"[WS] gm_start_voting: Game not found: {game_id}")
        return {'error': 'Game not found'}

    # NEU: Der entscheidende Berechtigungs-Check
    if not is_gm and player_name != game.gm_player:
        logger.warning(
            f"[WS] gm_start_voting: Not GM or Host - {player_name if player_name else 'unknown'} (sid={sid})")
        return {'error': 'Not authorized - you are not the GM'}

    debug_log(f"gm_start_voting: Current phase={game.phase}, calling start_voting()")
    success = game.start_voting()
    if not success:
        logger.warning(f"[WS] gm_start_voting: Cannot start voting in phase {game.phase}")
        return {'error': f'Cannot start voting - current phase is {game.phase.value}'}

    info_log(f"✓ GM started voting phase in game {game_id}")
    living = game.get_living_players()
    debug_log(f"gm_start_voting: Broadcasting voting_started to living players: {living}")

    await sio.emit('voting_started', {'living_players': living}, room=f"game:{game_id}")

    # Update GM
    await _notify_gm(game_id, game)

    return {'success': True, 'phase': game.phase.value}


@sio.event
async def gm_start_night(sid, data):
    """GM starts next night phase."""
    info = connections.get_info(sid)
    if not info:
        return {'error': 'Not authorized'}

    game_id, player_name, is_gm = info
    game = game_manager.get_game(game_id)

    if not game:
        return {'error': 'Game not found'}

    # NEU: Erlaube echte GMs ODER den Host-Spieler
    if not is_gm and player_name != game.gm_player:
        return {'error': 'Not authorized'}
    if not game:
        return {'error': 'Game not found'}

    success = game.start_night()
    if not success:
        if game.phase == GamePhase.ENDED:
            await _broadcast_game_over(game_id, game)
            return {'success': False, 'reason': 'Game ended'}
        return {'error': 'Cannot start night'}

    await sio.emit('phase_change', {'phase': 'night', 'turn': game.turn, 'deaths': []}, room=f"game:{game_id}")

    # Notify first player
    first_player = game.get_current_turn_player()
    if first_player:
        first_sid = connections.get_player_sid(game_id, first_player)
        if first_sid:
            await sio.emit('your_turn', game.get_turn_info(first_player).model_dump(), to=first_sid)

    # Update GM
    await _notify_gm(game_id, game)

    return {'success': True}


@sio.event
async def request_stats(sid, data):
    """Player requests current stats."""
    info = connections.get_info(sid)
    if not info:
        return {'error': 'Invalid session'}

    game_id = info[0]
    game = game_manager.get_game(game_id)
    if not game:
        return {'error': 'Game not found'}

    if not info[2]:  # Player
        player_name = info[1]
        stats = game.get_anonymous_stats()
        your_number = game.get_player_number(player_name)
        return {'success': True, 'stats': [s.model_dump() for s in stats], 'your_number': your_number}
    else:  # GM
        stats = game.get_anonymous_stats()
        return {'success': True, 'stats': [s.model_dump() for s in stats]}


# Helper functions

async def _notify_gm(game_id: str, game):
    """Send updated state to GM."""
    gm_sid = connections.get_gm_sid(game_id)
    if gm_sid:
        await sio.emit('gm_state', game.get_gm_state().model_dump(), to=gm_sid)


async def _broadcast_phase_change(game_id: str, game):
    """Broadcast phase change to all players."""
    if game.phase == GamePhase.DAY:
        stats = game.get_anonymous_stats()
        await sio.emit('phase_change', {'phase': 'day', 'turn': game.turn, 'deaths': game.deaths_this_round},
                       room=f"game:{game_id}")

        await sio.emit('stats_update', {'stats': [s.model_dump() for s in stats]}, room=f"game:{game_id}")

        # Send each player their number privately
        for player_name in game.get_players():
            player_sid = connections.get_player_sid(game_id, player_name)
            if player_sid:
                await sio.emit('your_number', {'number': game.get_player_number(player_name)}, to=player_sid)


async def _broadcast_game_over(game_id: str, game):
    """Broadcast game over to all players."""
    final_roles = game.get_final_roles()
    await sio.emit('game_over', {'winner': game.winner, 'final_roles': final_roles}, room=f"game:{game_id}")


async def broadcast_player_joined(game_id: str, player_name: str, player_count: int):
    """Broadcast that a player joined."""
    await sio.emit('player_joined', {'player_name': player_name, 'player_count': player_count}, room=f"game:{game_id}")


async def broadcast_game_started(game_id: str, game):
    """Broadcast that the game has started."""
    await sio.emit('game_started', {'phase': 'night', 'turn': 1, 'players': game.get_players(),
                                    'living_players': game.get_living_players()}, room=f"game:{game_id}")

    # Notify first player
    first_player = game.get_current_turn_player()
    if first_player:
        first_sid = connections.get_player_sid(game_id, first_player)
        if first_sid:
            await sio.emit('your_turn', game.get_turn_info(first_player).model_dump(), to=first_sid)
            logger.info(f"Notified {first_player} of their turn.")

    # Update GM
    await _notify_gm(game_id, game)
