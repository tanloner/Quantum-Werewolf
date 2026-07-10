"""Manages multiple Quantum Werewolf game instances."""

import secrets
import string
from typing import Dict, Optional, Tuple

from game_adapter import GameAdapter


class GameManager:
    """Manages all active game instances in memory."""

    def __init__(self):
        self.games: Dict[str, GameAdapter] = {}

    def _generate_game_id(self) -> str:
        """Generate a short, readable game ID."""
        chars = string.ascii_uppercase + string.digits
        while True:
            game_id = ''.join(secrets.choice(chars) for _ in range(6))
            if game_id not in self.games:
                return game_id

    def create_game(self, host_name: str) -> Tuple[str, str, str]:
        """Create a new game. Returns (game_id, gm_token, host_player_token)."""
        game_id = self._generate_game_id()
        game = GameAdapter(game_id, host_name)
        self.games[game_id] = game

        # Get host's token
        host_token = game.player_names[host_name]

        return game_id, game.gm_token, host_token

    def get_game(self, game_id: str) -> Optional[GameAdapter]:
        """Get a game by ID."""
        return self.games.get(game_id.upper())

    def delete_game(self, game_id: str) -> bool:
        """Delete a game."""
        if game_id.upper() in self.games:
            del self.games[game_id.upper()]
            return True
        return False

    def get_player_by_token(self, game_id: str, token: str) -> Optional[str]:
        """Get player name from token."""
        game = self.get_game(game_id)
        if game:
            return game.get_player_name(token)
        return None

    def is_gm_token(self, game_id: str, token: str) -> bool:
        """Check if token is the GM token for a game."""
        game = self.get_game(game_id)
        if game:
            return game.is_gm(token)
        return False


# Global singleton instance
game_manager = GameManager()
