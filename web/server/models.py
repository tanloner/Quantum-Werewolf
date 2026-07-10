"""Pydantic models for the Quantum Werewolf web API."""

from enum import Enum
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"
    ENDED = "ended"


class CreateGameRequest(BaseModel):
    """Request to create a new game."""
    host_name: str = Field(..., min_length=1, max_length=30)


class CreateGameResponse(BaseModel):
    """Response after creating a game."""
    game_id: str
    gm_token: str
    player_token: str
    join_url: str


class JoinGameRequest(BaseModel):
    """Request to join an existing game."""
    player_name: str = Field(..., min_length=1, max_length=30)


class JoinGameResponse(BaseModel):
    """Response after joining a game."""
    player_token: str
    player_name: str
    players: List[str]


class DeckConfig(BaseModel):
    """Deck configuration for the game."""
    werewolf: int = Field(default=2, ge=1, le=10)
    seer: int = Field(default=1, ge=0, le=1)
    hunter: int = Field(default=0, ge=0, le=1)
    cupid: int = Field(default=0, ge=0, le=1)


class PlayerStats(BaseModel):
    """Anonymous player stats for display."""
    number: int
    probabilities: Dict[str, float]
    death_probability: float
    is_dead: bool
    revealed_role: Optional[str] = None
    revealed_name: Optional[str] = None


class TurnInfo(BaseModel):
    """Information sent to player on their turn."""
    your_probabilities: Dict[str, float]
    your_number: int
    other_werewolves: List[Dict[str, Any]]
    available_actions: List[str]
    living_players: List[str]
    lover_info: Optional[Dict[str, Any]] = None
    is_first_night: bool = False


class VoteResult(BaseModel):
    """Result of the voting phase."""
    lynched_player: Optional[str]
    lynched_role: Optional[str]
    vote_counts: Dict[str, int]
    abstentions: int


class GameState(BaseModel):
    """Full game state for reconnection."""
    game_id: str
    phase: GamePhase
    turn: int
    players: List[str]
    living_players: List[str]
    is_your_turn: bool
    your_name: str
    your_number: Optional[int] = None
    stats: Optional[List[PlayerStats]] = None
    deaths_this_round: List[Dict[str, Any]] = []
    winner: Optional[str] = None


class GMState(BaseModel):
    """Game Master state."""
    phase: GamePhase
    turn: int
    current_player: Optional[str]
    pending_players: List[str]
    completed_players: List[str]
    actions_log: List[Dict[str, Any]]
    votes: Dict[str, Optional[str]]
    vote_confirmations: List[str]


class ActionRequest(BaseModel):
    """Generic action request."""
    target: str


class CupidActionRequest(BaseModel):
    """Cupid's action to pair lovers."""
    lover1: str
    lover2: str


class ForceActionRequest(BaseModel):
    """GM request to force a player's action."""
    player: str
    action: str
    target: Optional[str] = None
    target2: Optional[str] = None
