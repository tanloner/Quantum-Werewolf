"""Adapter wrapping the Quantum Werewolf backend for web use."""

import os
import secrets
import sys
from random import shuffle
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path to import quantumwerewolf
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from quantumwerewolf.backend import Game

from models import (
    GamePhase, PlayerStats, TurnInfo, DeckConfig,
    VoteResult, GameState, GMState
)


class GameAdapter:
    """Wraps the Game class with web-specific functionality."""

    def __init__(self, game_id: str, host_name: str):
        self.game_id = game_id
        self.game = Game()
        self.gm_token = secrets.token_urlsafe(32)

        # Player management
        self.player_tokens: Dict[str, str] = {}  # token -> player_name
        self.player_names: Dict[str, str] = {}  # player_name -> token

        # Game state
        self.phase = GamePhase.LOBBY
        self.turn = 0
        self.current_turn_index = 0
        self.turn_order: List[str] = []
        self.pending_night_actions: Dict[str, Dict[str, Any]] = {}
        self.completed_players: List[str] = []

        # Voting state
        self.votes: Dict[str, Optional[str]] = {}
        self.vote_confirmations: set = set()

        # Anonymous display order (shuffled on game start)
        self.display_order: List[int] = []

        # Deaths this round (for announcement)
        self.deaths_this_round: List[Dict[str, str]] = []

        # Action log for GM
        self.actions_log: List[Dict[str, Any]] = []

        # Winner
        self.winner: Optional[str] = None

        # Add host as first player and GM
        self.add_player(host_name)
        self.gm_player = host_name

    def add_player(self, name: str) -> Optional[str]:
        """Add a player and return their token."""
        if self.phase != GamePhase.LOBBY:
            return None

        if name in self.player_names:
            return None

        success = self.game.add_player(name)
        if not success:
            return None

        token = secrets.token_urlsafe(32)
        self.player_tokens[token] = name
        self.player_names[name] = token
        return token

    def get_player_name(self, token: str) -> Optional[str]:
        """Get player name from token."""
        return self.player_tokens.get(token)

    def is_gm(self, token: str) -> bool:
        """Check if token belongs to GM."""
        return token == self.gm_token

    def get_players(self) -> List[str]:
        """Get list of player names."""
        return list(self.game.players)

    def get_living_players(self) -> List[str]:
        """Get list of living player names."""
        if not self.game.started:
            return self.get_players()
        return [
            name for i, name in enumerate(self.game.players)
            if not self.game.killed[i]
        ]

    def configure_deck(self, config: DeckConfig) -> bool:
        """Configure the deck before game start."""
        if self.phase != GamePhase.LOBBY:
            return False

        self.game.deck = {
            'werewolf': config.werewolf,
            'seer': config.seer,
            'hunter': config.hunter,
            'cupid': config.cupid,
        }
        return True

    def start_game(self) -> bool:
        """Start the game."""
        if self.phase != GamePhase.LOBBY:
            return False

        if len(self.game.players) < 3:
            return False

        # Start the backend game
        self.game.start()

        # Set up anonymous display order
        self.display_order = list(range(len(self.game.players)))
        shuffle(self.display_order)

        # Start night phase
        self.phase = GamePhase.NIGHT
        self.turn = 1
        self._start_night_phase()

        return True

    def _start_night_phase(self):
        """Initialize the night phase."""
        self.turn_order = self.get_living_players()
        self.current_turn_index = 0
        self.pending_night_actions = {}
        self.completed_players = []
        self.deaths_this_round = []

    def get_current_turn_player(self) -> Optional[str]:
        """Get the player whose turn it currently is."""
        if self.phase != GamePhase.NIGHT:
            return None
        if self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    def get_pending_players(self) -> List[str]:
        """Get players who haven't taken their turn yet."""
        if self.phase != GamePhase.NIGHT:
            return []
        return self.turn_order[self.current_turn_index + 1:]

    def get_player_number(self, player_name: str) -> int:
        """Get the anonymous display number for a player."""
        player_id = self.game._id(player_name)
        return self.display_order.index(player_id) + 1

    def _get_role_probs_dict(self) -> Dict[str, Dict[str, float]]:
        """Convert role_probabilities tuple to dict keyed by player name."""
        probs_tuple = self.game.role_probabilities()
        result = {}
        for player_data in probs_tuple:
            name = player_data['name']
            # Extract only role probabilities (exclude 'name' and 'dead')
            role_probs = {k: v for k, v in player_data.items()
                          if k not in ('name', 'dead')}
            result[name] = role_probs
        return result

    def get_turn_info(self, player_name: str) -> TurnInfo:
        """Get information for a player's turn."""
        # Role probabilities
        probs = self._get_role_probs_dict()
        my_probs = probs.get(player_name, {})

        # Other werewolves (conditional probabilities)
        other_wolves = []
        if my_probs.get('werewolf', 0) > 0:
            wolf_probs_list = self.game.other_werewolves(player_name)
            for player_data in wolf_probs_list:
                name = player_data['name']
                prob = player_data.get('werewolf', 0)
                if name != player_name and prob > 0:
                    other_wolves.append({'name': name, 'probability': prob})

        # Available actions based on role probabilities
        available = []
        if my_probs.get('seer', 0) > 0:
            available.append('seer')
        if my_probs.get('werewolf', 0) > 0:
            available.append('werewolf')
        if my_probs.get('cupid', 0) > 0 and self.turn == 1:
            available.append('cupid')

        # Lover info for cupid action
        lover_info = None
        if 'cupid' in available:
            living = self.get_living_players()
            lover_info = {'eligible_players': [p for p in living if p != player_name]}

        return TurnInfo(
            your_probabilities=my_probs,
            your_number=self.get_player_number(player_name),
            other_werewolves=other_wolves,
            available_actions=available,
            living_players=self.get_living_players(),
            lover_info=lover_info,
            is_first_night=(self.turn == 1)
        )

    def submit_seer_action(self, player_name: str, target: str) -> Optional[str]:
        """Submit seer action. Returns the revealed role."""
        if player_name not in self.pending_night_actions:
            self.pending_night_actions[player_name] = {}

        # Call seer action - returns the role seen
        result = self.game.seer(player_name, target)
        self.pending_night_actions[player_name]['seer'] = target

        self.actions_log.append({
            'turn': self.turn,
            'player': player_name,
            'action': 'seer',
            'target': target,
            'result': result
        })

        return result

    def submit_werewolf_action(self, player_name: str, target: str) -> bool:
        """Submit werewolf action."""
        if player_name not in self.pending_night_actions:
            self.pending_night_actions[player_name] = {}

        self.game.werewolf(player_name, target)
        self.pending_night_actions[player_name]['werewolf'] = target

        self.actions_log.append({
            'turn': self.turn,
            'player': player_name,
            'action': 'werewolf',
            'target': target
        })

        return True

    def submit_cupid_action(self, player_name: str, lover1: str, lover2: str) -> bool:
        """Submit cupid action."""
        if self.turn != 1:
            return False

        if player_name not in self.pending_night_actions:
            self.pending_night_actions[player_name] = {}

        self.game.cupid(player_name, lover1, lover2)
        self.pending_night_actions[player_name]['cupid'] = (lover1, lover2)

        self.actions_log.append({
            'turn': self.turn,
            'player': player_name,
            'action': 'cupid',
            'target': f'{lover1} & {lover2}'
        })

        return True

    def end_player_turn(self, player_name: str) -> bool:
        """End a player's turn and advance to next player or phase."""
        current = self.get_current_turn_player()
        if current != player_name:
            return False

        self.completed_players.append(player_name)
        self.current_turn_index += 1

        # Check if all players have taken their turn
        if self.current_turn_index >= len(self.turn_order):
            self._process_night_end()

        return True

    def skip_current_turn(self) -> Optional[str]:
        """GM skips the current player's turn. Returns the skipped player."""
        current = self.get_current_turn_player()
        if current is None:
            return None

        self.actions_log.append({
            'turn': self.turn,
            'player': current,
            'action': 'skipped',
            'by': 'GM'
        })

        self.completed_players.append(current)
        self.current_turn_index += 1

        if self.current_turn_index >= len(self.turn_order):
            self._process_night_end()

        return current

    def _process_night_end(self):
        """Process the end of night phase."""
        # Check for deaths
        dead_players = self.game.check_deaths()

        for player_name in dead_players:
            player_id = self.game._id(player_name)
            # Kill returns the role
            role = self.game.kill(player_name)
            self.deaths_this_round.append({
                'name': player_name,
                'role': role,
                'number': self.get_player_number(player_name)
            })

        # Process hunter revenge if needed (simplified - auto-skip for now)

        # Check win condition
        win_result = self.game.check_win()
        if win_result[0]:
            self.winner = win_result[1]
            self.phase = GamePhase.ENDED
            return

        # Transition to day phase
        self.phase = GamePhase.DAY

    def get_anonymous_stats(self) -> List[PlayerStats]:
        """Get anonymous player stats for display."""
        stats = []
        probs = self._get_role_probs_dict()

        for display_num in range(len(self.display_order)):
            player_id = self.display_order[display_num]
            player_name = self.game.players[player_id]
            is_dead = self.game.killed[player_id]

            player_probs = probs.get(player_name, {})

            # Calculate death probability (0 if already dead)
            death_prob = 0.0
            if not is_dead:
                death_prob = self.game.death_probability(player_name)

            stats.append(PlayerStats(
                number=display_num + 1,
                probabilities=player_probs,
                death_probability=death_prob,
                is_dead=is_dead,
                revealed_role=self._get_revealed_role(player_id) if is_dead else None,
                revealed_name=player_name if is_dead else None
            ))

        return stats

    def _get_revealed_role(self, player_id: int) -> Optional[str]:
        """Get the revealed role of a dead player."""
        # Find in deaths log
        player_name = self.game.players[player_id]
        for death in self.deaths_this_round:
            if death['name'] == player_name:
                return death['role']
        # Check all historical deaths from actions log
        for action in self.actions_log:
            if action.get('action') == 'killed' and action.get('player') == player_name:
                return action.get('role')
        return None

    def start_voting(self):
        """Start the voting phase."""
        if self.phase != GamePhase.DAY:
            return False

        self.phase = GamePhase.VOTING
        self.votes = {name: None for name in self.get_living_players()}
        self.vote_confirmations = set()
        return True

    def submit_vote(self, player_name: str, target: Optional[str]) -> bool:
        """Submit a vote (or None for abstain)."""
        if self.phase != GamePhase.VOTING:
            return False

        if player_name not in self.votes:
            return False

        if target is not None and target not in self.get_living_players():
            return False

        self.votes[player_name] = target
        return True

    def confirm_vote(self, player_name: str) -> bool:
        """Confirm a player's vote."""
        if self.phase != GamePhase.VOTING:
            return False

        if player_name not in self.votes:
            return False

        self.vote_confirmations.add(player_name)
        return True

    def get_vote_progress(self) -> Dict[str, Any]:
        """Get current voting progress."""
        living = self.get_living_players()
        return {
            'votes_cast': sum(1 for v in self.votes.values() if v is not None),
            'total_players': len(living),
            'confirmations': len(self.vote_confirmations),
            'all_confirmed': len(self.vote_confirmations) == len(living)
        }

    def end_voting(self) -> VoteResult:
        """End voting and process the result."""
        # Count votes
        vote_counts: Dict[str, int] = {}
        abstentions = 0

        for voter, target in self.votes.items():
            if target is None:
                abstentions += 1
            else:
                vote_counts[target] = vote_counts.get(target, 0) + 1

        # Find player with most votes (if any)
        lynched_player = None
        lynched_role = None

        if vote_counts:
            max_votes = max(vote_counts.values())
            candidates = [p for p, v in vote_counts.items() if v == max_votes]

            # If tie, no one is lynched (could also random select)
            if len(candidates) == 1:
                lynched_player = candidates[0]
                lynched_role = self.game.kill(lynched_player)

                self.deaths_this_round.append({
                    'name': lynched_player,
                    'role': lynched_role,
                    'number': self.get_player_number(lynched_player)
                })

                self.actions_log.append({
                    'turn': self.turn,
                    'player': lynched_player,
                    'action': 'lynched',
                    'role': lynched_role,
                    'votes': vote_counts
                })

                # Prüfen, ob durch die Aufdeckung andere Spieler auf 100% Death% rutschen
                collateral_deaths = self.game.check_deaths()
                for player_name in collateral_deaths:
                    # Verhindern, dass der Gelynchte doppelt verarbeitet wird
                    if player_name != lynched_player:
                        role = self.game.kill(player_name)
                        self.deaths_this_round.append({
                            'name': player_name,
                            'role': role,
                            'number': self.get_player_number(player_name)
                        })

                        self.actions_log.append({
                            'turn': self.turn,
                            'player': player_name,
                            'action': 'quantum_death',
                            'role': role
                        })

        # Check win condition
        win_result = self.game.check_win()
        if win_result[0]:
            self.winner = win_result[1]
            self.phase = GamePhase.ENDED
        else:
            self.phase = GamePhase.DAY

        return VoteResult(
            lynched_player=lynched_player,
            lynched_role=lynched_role,
            vote_counts=vote_counts,
            abstentions=abstentions
        )

    def start_night(self) -> bool:
        """Start the next night phase."""
        if self.phase != GamePhase.DAY:
            return False

        # Check win condition first
        win_result = self.game.check_win()
        if win_result[0]:
            self.winner = win_result[1]
            self.phase = GamePhase.ENDED
            return False

        self.turn += 1
        self.phase = GamePhase.NIGHT
        self._start_night_phase()
        return True

    def get_game_state(self, player_name: str) -> GameState:
        """Get full game state for a player (for reconnection)."""
        return GameState(
            game_id=self.game_id,
            phase=self.phase,
            turn=self.turn,
            players=self.get_players(),
            living_players=self.get_living_players(),
            is_your_turn=(self.get_current_turn_player() == player_name),
            your_name=player_name,
            your_number=self.get_player_number(player_name) if self.game.started else None,
            stats=self.get_anonymous_stats() if self.phase in [GamePhase.DAY, GamePhase.VOTING] else None,
            deaths_this_round=self.deaths_this_round,
            winner=self.winner
        )

    def get_gm_state(self) -> GMState:
        """Get GM-specific state."""
        return GMState(
            phase=self.phase,
            turn=self.turn,
            current_player=self.get_current_turn_player(),
            pending_players=self.get_pending_players(),
            completed_players=self.completed_players,
            actions_log=self.actions_log[-20:],  # Last 20 actions
            votes=self.votes,
            vote_confirmations=list(self.vote_confirmations)
        )

    def get_final_roles(self) -> List[Dict[str, str]]:
        """Get final role assignments (only after game ends)."""
        if self.phase != GamePhase.ENDED:
            return []

        # Get the final role from any valid permutation
        valid = self.game.valid_permutations()
        if not valid:
            return []

        final_perm = valid[0]
        return [
            {'name': self.game.players[i], 'role': final_perm[i]}
            for i in range(len(self.game.players))
        ]
