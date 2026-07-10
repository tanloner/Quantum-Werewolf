"""Pytest configuration and fixtures for Quantum Werewolf tests."""

import os
import sys
from typing import Tuple

import pytest

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from game_adapter import GameAdapter
from game_manager import GameManager
from models import DeckConfig, GamePhase


@pytest.fixture
def game_manager():
    """Fresh GameManager instance for each test."""
    return GameManager()


@pytest.fixture
def empty_game() -> GameAdapter:
    """Game with single host player in lobby."""
    return GameAdapter("TEST01", "Host")


@pytest.fixture
def three_player_game() -> GameAdapter:
    """Game with 3 players in lobby."""
    game = GameAdapter("TEST02", "Alice")
    game.add_player("Bob")
    game.add_player("Craig")
    return game


@pytest.fixture
def five_player_game() -> GameAdapter:
    """Game with 5 players in lobby."""
    game = GameAdapter("TEST03", "Alice")
    game.add_player("Bob")
    game.add_player("Craig")
    game.add_player("David")
    game.add_player("Eve")
    return game


@pytest.fixture
def started_game() -> GameAdapter:
    """Game that has been started (night phase)."""
    game = GameAdapter("TEST04", "Alice")
    game.add_player("Bob")
    game.add_player("Craig")
    game.add_player("David")
    game.start_game()
    return game


@pytest.fixture
def day_phase_game() -> GameAdapter:
    """Game in day phase after first night."""
    game = GameAdapter("TEST05", "Alice")
    game.add_player("Bob")
    game.add_player("Craig")
    game.add_player("David")
    game.start_game()

    # Complete all turns to reach day phase
    while game.phase == GamePhase.NIGHT:
        current = game.get_current_turn_player()
        if current:
            game.end_player_turn(current)

    return game


@pytest.fixture
def voting_game() -> GameAdapter:
    """Game in voting phase."""
    game = GameAdapter("TEST06", "Alice")
    game.add_player("Bob")
    game.add_player("Craig")
    game.add_player("David")
    game.start_game()

    # Complete night to reach day
    while game.phase == GamePhase.NIGHT:
        current = game.get_current_turn_player()
        if current:
            game.end_player_turn(current)

    # Start voting
    game.start_voting()
    return game


@pytest.fixture
def minimal_deck() -> DeckConfig:
    """Minimal deck configuration (1 werewolf, 1 seer)."""
    return DeckConfig(werewolf=1, seer=1, hunter=0, cupid=0)


@pytest.fixture
def standard_deck() -> DeckConfig:
    """Standard deck configuration."""
    return DeckConfig(werewolf=2, seer=1, hunter=0, cupid=0)


@pytest.fixture
def full_deck() -> DeckConfig:
    """Full deck with all special roles."""
    return DeckConfig(werewolf=2, seer=1, hunter=1, cupid=1)


def get_tokens_for_game(game: GameAdapter) -> dict:
    """Helper to get all player tokens for a game."""
    return {name: token for token, name in game.player_tokens.items()}
