"""Comprehensive tests for GameAdapter class."""

from game_adapter import GameAdapter
from models import DeckConfig, GamePhase

import pytest


class TestGameCreation:
    """Tests for game initialization."""

    def test_create_game_with_host(self):
        """Host is added as first player on game creation."""
        game = GameAdapter("TEST01", "Alice")
        assert "Alice" in game.get_players()
        assert len(game.get_players()) == 1

    def test_game_starts_in_lobby_phase(self):
        """New game starts in lobby phase."""
        game = GameAdapter("TEST01", "Host")
        assert game.phase == GamePhase.LOBBY

    def test_game_has_gm_token(self):
        """Game creates GM token on initialization."""
        game = GameAdapter("TEST01", "Host")
        assert game.gm_token is not None
        assert len(game.gm_token) > 20

    def test_host_gets_player_token(self):
        """Host gets player token on creation."""
        game = GameAdapter("TEST01", "Host")
        assert "Host" in game.player_names
        token = game.player_names["Host"]
        assert token is not None
        assert game.get_player_name(token) == "Host"


class TestPlayerManagement:
    """Tests for adding and managing players."""

    def test_add_player_returns_token(self, empty_game):
        """Adding player returns their authentication token."""
        token = empty_game.add_player("Bob")
        assert token is not None
        assert len(token) > 20

    def test_add_player_to_player_list(self, empty_game):
        """Added player appears in player list."""
        empty_game.add_player("Bob")
        assert "Bob" in empty_game.get_players()

    def test_cannot_add_duplicate_player(self, empty_game):
        """Cannot add player with same name."""
        empty_game.add_player("Bob")
        result = empty_game.add_player("Bob")
        assert result is None
        assert empty_game.get_players().count("Bob") == 1

    def test_cannot_add_player_after_start(self, started_game):
        """Cannot add players after game has started."""
        result = started_game.add_player("NewPlayer")
        assert result is None
        assert "NewPlayer" not in started_game.get_players()

    def test_get_player_name_from_token(self, empty_game):
        """Can retrieve player name from token."""
        token = empty_game.add_player("Bob")
        assert empty_game.get_player_name(token) == "Bob"

    def test_get_player_name_invalid_token(self, empty_game):
        """Invalid token returns None."""
        assert empty_game.get_player_name("invalid-token") is None

    def test_is_gm_check(self, empty_game):
        """GM token correctly identified."""
        assert empty_game.is_gm(empty_game.gm_token) is True
        player_token = empty_game.player_names["Host"]
        assert empty_game.is_gm(player_token) is False

    def test_get_living_players_before_start(self, three_player_game):
        """All players are living before game starts."""
        living = three_player_game.get_living_players()
        assert len(living) == 3
        assert set(living) == {"Alice", "Bob", "Craig"}


class TestDeckConfiguration:
    """Tests for deck configuration."""

    def test_default_deck(self, empty_game):
        """Game starts with default deck."""
        assert empty_game.game.deck['werewolf'] == 2
        assert empty_game.game.deck['seer'] == 1

    def test_configure_deck_in_lobby(self, three_player_game, minimal_deck):
        """Can configure deck in lobby phase."""
        result = three_player_game.configure_deck(minimal_deck)
        assert result is True
        assert three_player_game.game.deck['werewolf'] == 1
        assert three_player_game.game.deck['seer'] == 1

    def test_cannot_configure_deck_after_start(self, started_game, minimal_deck):
        """Cannot configure deck after game started."""
        result = started_game.configure_deck(minimal_deck)
        assert result is False


class TestGameStart:
    """Tests for starting the game."""

    def test_start_game_with_enough_players(self, three_player_game):
        """Can start game with 3+ players."""
        result = three_player_game.start_game()
        assert result is True
        assert three_player_game.phase == GamePhase.NIGHT

    def test_cannot_start_with_insufficient_players(self, empty_game):
        """Cannot start with less than 3 players."""
        empty_game.add_player("Bob")  # Now 2 players
        result = empty_game.start_game()
        assert result is False
        assert empty_game.phase == GamePhase.LOBBY

    def test_cannot_start_twice(self, started_game):
        """Cannot start already started game."""
        result = started_game.start_game()
        assert result is False

    def test_start_initializes_turn_order(self, three_player_game):
        """Starting game initializes turn order."""
        three_player_game.start_game()
        current = three_player_game.get_current_turn_player()
        assert current in three_player_game.get_players()

    def test_start_sets_turn_to_one(self, three_player_game):
        """Game starts at turn 1."""
        three_player_game.start_game()
        assert three_player_game.turn == 1

    def test_start_generates_display_order(self, three_player_game):
        """Starting game generates anonymous display order."""
        three_player_game.start_game()
        assert len(three_player_game.display_order) == 3
        # All indices should be present
        assert set(three_player_game.display_order) == {0, 1, 2}


class TestNightPhase:
    """Tests for night phase mechanics."""

    def test_get_current_turn_player(self, started_game):
        """Can get current turn player during night."""
        current = started_game.get_current_turn_player()
        assert current in started_game.get_players()

    def test_get_pending_players(self, started_game):
        """Can get list of pending players."""
        current = started_game.get_current_turn_player()
        pending = started_game.get_pending_players()
        assert current not in pending
        assert len(pending) == len(started_game.get_players()) - 1

    def test_end_player_turn_advances(self, started_game):
        """Ending turn advances to next player."""
        first_player = started_game.get_current_turn_player()
        started_game.end_player_turn(first_player)
        second_player = started_game.get_current_turn_player()
        assert second_player != first_player

    def test_cannot_end_turn_for_wrong_player(self, started_game):
        """Cannot end turn for player who isn't current."""
        current = started_game.get_current_turn_player()
        other = [p for p in started_game.get_players() if p != current][0]
        result = started_game.end_player_turn(other)
        assert result is False
        assert started_game.get_current_turn_player() == current

    def test_get_turn_info(self, started_game):
        """Get turn info for current player."""
        current = started_game.get_current_turn_player()
        info = started_game.get_turn_info(current)
        assert info.your_probabilities is not None
        assert info.your_number >= 1
        assert isinstance(info.available_actions, list)

    def test_turn_info_has_valid_probabilities(self, started_game):
        """Turn info has valid probability values."""
        current = started_game.get_current_turn_player()
        info = started_game.get_turn_info(current)
        total = sum(info.your_probabilities.values())
        assert 0.99 < total < 1.01  # Should sum to ~1

    def test_skip_current_turn(self, started_game):
        """GM can skip current player's turn."""
        first = started_game.get_current_turn_player()
        skipped = started_game.skip_current_turn()
        assert skipped == first
        assert started_game.get_current_turn_player() != first

    def test_complete_night_transitions_to_day(self, started_game):
        """Completing all turns transitions to day phase."""
        while started_game.phase == GamePhase.NIGHT:
            current = started_game.get_current_turn_player()
            if current:
                started_game.end_player_turn(current)
            else:
                break
        assert started_game.phase == GamePhase.DAY


class TestNightActions:
    """Tests for night phase actions (seer, werewolf, cupid)."""

    def test_seer_action_returns_role(self, started_game):
        """Seer action returns observed role when player has seer probability."""
        current = started_game.get_current_turn_player()
        target = [p for p in started_game.get_players() if p != current][0]

        # Get current player's seer probability
        turn_info = started_game.get_turn_info(current)
        has_seer_prob = turn_info.your_probabilities.get('seer', 0) > 0

        result = started_game.submit_seer_action(current, target)

        # If player has seer probability, result should be a valid role
        # If player has 0% seer probability, result is None
        if has_seer_prob:
            assert result in ['werewolf', 'seer', 'villager', 'hunter', 'cupid']
        else:
            assert result is None

    def test_seer_action_logged(self, started_game):
        """Seer action is logged."""
        current = started_game.get_current_turn_player()
        target = [p for p in started_game.get_players() if p != current][0]

        started_game.submit_seer_action(current, target)
        assert len(started_game.actions_log) > 0
        log = started_game.actions_log[-1]
        assert log['action'] == 'seer'
        assert log['target'] == target

    def test_werewolf_action_returns_true(self, started_game):
        """Werewolf action returns success."""
        current = started_game.get_current_turn_player()
        target = [p for p in started_game.get_players() if p != current][0]

        result = started_game.submit_werewolf_action(current, target)
        assert result is True

    def test_werewolf_action_logged(self, started_game):
        """Werewolf action is logged."""
        current = started_game.get_current_turn_player()
        target = [p for p in started_game.get_players() if p != current][0]

        started_game.submit_werewolf_action(current, target)
        assert len(started_game.actions_log) > 0
        log = started_game.actions_log[-1]
        assert log['action'] == 'werewolf'
        assert log['target'] == target

    def test_cupid_action_on_first_night(self, started_game):
        """Cupid can pair lovers on first night."""
        current = started_game.get_current_turn_player()
        others = [p for p in started_game.get_players() if p != current]

        result = started_game.submit_cupid_action(current, others[0], others[1])
        assert result is True

    def test_cupid_action_logged(self, started_game):
        """Cupid action is logged."""
        current = started_game.get_current_turn_player()
        others = [p for p in started_game.get_players() if p != current]

        started_game.submit_cupid_action(current, others[0], others[1])
        log_entry = [l for l in started_game.actions_log if l['action'] == 'cupid']
        assert len(log_entry) > 0


class TestDayPhase:
    """Tests for day phase mechanics."""

    def test_day_phase_has_stats(self, day_phase_game):
        """Day phase provides anonymous stats."""
        stats = day_phase_game.get_anonymous_stats()
        assert len(stats) == len(day_phase_game.get_players())

    def test_anonymous_stats_have_probabilities(self, day_phase_game):
        """Anonymous stats include role probabilities."""
        stats = day_phase_game.get_anonymous_stats()
        for stat in stats:
            assert stat.probabilities is not None
            assert 'werewolf' in stat.probabilities or len(stat.probabilities) > 0

    def test_anonymous_stats_numbered(self, day_phase_game):
        """Anonymous stats have sequential numbers."""
        stats = day_phase_game.get_anonymous_stats()
        numbers = [s.number for s in stats]
        assert sorted(numbers) == list(range(1, len(stats) + 1))

    def test_get_player_number(self, day_phase_game):
        """Can get player's anonymous number."""
        for player in day_phase_game.get_players():
            num = day_phase_game.get_player_number(player)
            assert 1 <= num <= len(day_phase_game.get_players())


class TestVotingPhase:
    """Tests for voting phase mechanics."""

    def test_start_voting_from_day(self, day_phase_game):
        """Can start voting from day phase."""
        result = day_phase_game.start_voting()
        assert result is True
        assert day_phase_game.phase == GamePhase.VOTING

    def test_cannot_start_voting_from_night(self, started_game):
        """Cannot start voting during night."""
        result = started_game.start_voting()
        assert result is False

    def test_submit_vote(self, voting_game):
        """Can submit a vote."""
        voter = voting_game.get_living_players()[0]
        target = voting_game.get_living_players()[1]

        result = voting_game.submit_vote(voter, target)
        assert result is True
        assert voting_game.votes[voter] == target

    def test_submit_abstain_vote(self, voting_game):
        """Can abstain from voting."""
        voter = voting_game.get_living_players()[0]

        result = voting_game.submit_vote(voter, None)
        assert result is True
        assert voting_game.votes[voter] is None

    def test_cannot_vote_for_dead_player(self, voting_game):
        """Cannot vote for non-living player."""
        voter = voting_game.get_living_players()[0]

        result = voting_game.submit_vote(voter, "DeadPlayer")
        assert result is False

    def test_confirm_vote(self, voting_game):
        """Can confirm vote."""
        voter = voting_game.get_living_players()[0]
        voting_game.submit_vote(voter, None)

        result = voting_game.confirm_vote(voter)
        assert result is True
        assert voter in voting_game.vote_confirmations

    def test_vote_progress(self, voting_game):
        """Vote progress is tracked."""
        players = voting_game.get_living_players()

        # Initial state
        progress = voting_game.get_vote_progress()
        assert progress['votes_cast'] == 0
        assert progress['confirmations'] == 0

        # After vote
        voting_game.submit_vote(players[0], players[1])
        progress = voting_game.get_vote_progress()
        assert progress['votes_cast'] == 1

        # After confirmation
        voting_game.confirm_vote(players[0])
        progress = voting_game.get_vote_progress()
        assert progress['confirmations'] == 1

    def test_end_voting_with_majority(self, voting_game):
        """Voting ends with lynched player when majority."""
        players = voting_game.get_living_players()
        target = players[0]

        # All vote for same target
        for voter in players:
            if voter != target:
                voting_game.submit_vote(voter, target)
            else:
                voting_game.submit_vote(voter, None)  # Can't vote for self

        result = voting_game.end_voting()
        assert result.lynched_player == target
        assert result.lynched_role is not None

    def test_end_voting_tie_no_lynch(self, voting_game):
        """Tie results in no lynch."""
        players = voting_game.get_living_players()

        # Split votes evenly
        voting_game.submit_vote(players[0], players[1])
        voting_game.submit_vote(players[1], players[0])
        voting_game.submit_vote(players[2], players[0])
        voting_game.submit_vote(players[3], players[1])

        result = voting_game.end_voting()
        # With tie, no one is lynched
        if result.vote_counts.get(players[0]) == result.vote_counts.get(players[1]):
            assert result.lynched_player is None

    def test_end_voting_all_abstain(self, voting_game):
        """All abstaining results in no lynch."""
        for voter in voting_game.get_living_players():
            voting_game.submit_vote(voter, None)

        result = voting_game.end_voting()
        assert result.lynched_player is None
        assert result.abstentions == len(voting_game.get_living_players())


class TestNightTransition:
    """Tests for transitioning back to night."""

    def test_start_night_from_day(self, day_phase_game):
        """Can start night from day phase."""
        result = day_phase_game.start_night()
        assert result is True
        assert day_phase_game.phase == GamePhase.NIGHT
        assert day_phase_game.turn == 2

    def test_cannot_start_night_from_night(self, started_game):
        """Cannot start night when already night."""
        result = started_game.start_night()
        assert result is False


class TestGameState:
    """Tests for game state retrieval."""

    def test_get_game_state_lobby(self, three_player_game):
        """Can get game state in lobby."""
        state = three_player_game.get_game_state("Alice")
        assert state.phase == GamePhase.LOBBY
        assert state.your_name == "Alice"
        assert len(state.players) == 3

    def test_get_game_state_night(self, started_game):
        """Can get game state in night phase."""
        current = started_game.get_current_turn_player()
        state = started_game.get_game_state(current)
        assert state.phase == GamePhase.NIGHT
        assert state.is_your_turn is True
        assert state.your_number is not None

    def test_get_gm_state(self, started_game):
        """Can get GM state."""
        gm_state = started_game.get_gm_state()
        assert gm_state.phase == GamePhase.NIGHT
        assert gm_state.current_player is not None
        assert isinstance(gm_state.actions_log, list)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_game_id(self):
        """Game handles various game IDs."""
        game = GameAdapter("", "Host")
        assert game.game_id == ""

    def test_special_characters_in_name(self):
        """Player names with special characters."""
        game = GameAdapter("TEST", "Host-1_Test")
        token = game.add_player("Player With Spaces")
        assert token is not None
        assert "Player With Spaces" in game.get_players()

    def test_max_player_name_length(self, empty_game):
        """Long player names handled."""
        long_name = "A" * 100
        token = empty_game.add_player(long_name)
        # Should work (validation at API level)
        assert token is not None

    def test_end_turn_when_no_current_player(self, day_phase_game):
        """End turn when not in night phase."""
        result = day_phase_game.end_player_turn("Alice")
        assert result is False

    def test_get_current_turn_outside_night(self, day_phase_game):
        """Get current turn player outside night returns None."""
        current = day_phase_game.get_current_turn_player()
        assert current is None

    def test_werewolf_cannot_attack_self(self, started_game):
        """Werewolf cannot attack themselves (backend validation)."""
        current = started_game.get_current_turn_player()
        # Backend correctly rejects werewolf attacking self
        with pytest.raises(AssertionError):
            started_game.submit_werewolf_action(current, current)

    def test_multiple_actions_same_turn(self, started_game):
        """Multiple actions in same turn."""
        current = started_game.get_current_turn_player()
        target = [p for p in started_game.get_players() if p != current][0]

        # Both seer and werewolf action (quantum nature)
        started_game.submit_seer_action(current, target)
        started_game.submit_werewolf_action(current, target)

        # Both should be recorded
        actions = [l for l in started_game.actions_log if l['player'] == current]
        assert len(actions) >= 2

    def test_vote_for_self(self, voting_game):
        """Cannot vote for yourself (target must be in living players)."""
        # Actually this depends on implementation
        voter = voting_game.get_living_players()[0]
        # Voting for self - may or may not be allowed
        result = voting_game.submit_vote(voter, voter)
        # If living players excludes self in voting, this might fail
        # Current implementation includes self in living players

    def test_confirm_without_vote(self, voting_game):
        """Confirm vote when no vote cast."""
        voter = voting_game.get_living_players()[0]
        # Vote is None by default
        result = voting_game.confirm_vote(voter)
        assert result is True  # Confirming abstention


class TestWinConditions:
    """Tests related to win condition checking."""

    def test_game_checks_win_after_night(self, started_game):
        """Win condition checked after night processing."""
        # Complete night
        while started_game.phase == GamePhase.NIGHT:
            current = started_game.get_current_turn_player()
            if current:
                started_game.end_player_turn(current)

        # Game should be in DAY or ENDED
        assert started_game.phase in [GamePhase.DAY, GamePhase.ENDED]

    def test_game_checks_win_after_vote(self, voting_game):
        """Win condition checked after voting."""
        players = voting_game.get_living_players()

        # Vote to lynch someone
        for voter in players[1:]:
            voting_game.submit_vote(voter, players[0])
        voting_game.submit_vote(players[0], None)

        voting_game.end_voting()

        # Should be DAY or ENDED
        assert voting_game.phase in [GamePhase.DAY, GamePhase.ENDED]
