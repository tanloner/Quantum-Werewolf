"""Comprehensive tests for GameManager class."""

from game_manager import GameManager, game_manager


class TestGameCreation:
    """Tests for creating games via GameManager."""

    def test_create_game_returns_tuple(self, game_manager):
        """create_game returns (game_id, gm_token, player_token)."""
        result = game_manager.create_game("Host")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_create_game_generates_game_id(self, game_manager):
        """Game ID is 6 uppercase alphanumeric characters."""
        game_id, _, _ = game_manager.create_game("Host")
        assert len(game_id) == 6
        assert game_id.isalnum()
        assert game_id.isupper()

    def test_create_game_generates_unique_ids(self, game_manager):
        """Multiple games have unique IDs."""
        ids = set()
        for i in range(10):
            game_id, _, _ = game_manager.create_game(f"Host{i}")
            ids.add(game_id)
        assert len(ids) == 10

    def test_create_game_returns_gm_token(self, game_manager):
        """GM token is generated and returned."""
        _, gm_token, _ = game_manager.create_game("Host")
        assert gm_token is not None
        assert len(gm_token) > 20

    def test_create_game_returns_player_token(self, game_manager):
        """Host player token is generated and returned."""
        _, _, player_token = game_manager.create_game("Host")
        assert player_token is not None
        assert len(player_token) > 20

    def test_create_game_stores_game(self, game_manager):
        """Created game is stored and retrievable."""
        game_id, _, _ = game_manager.create_game("Host")
        game = game_manager.get_game(game_id)
        assert game is not None
        assert game.game_id == game_id


class TestGameRetrieval:
    """Tests for retrieving games."""

    def test_get_game_by_id(self, game_manager):
        """Can retrieve game by ID."""
        game_id, _, _ = game_manager.create_game("Host")
        game = game_manager.get_game(game_id)
        assert game is not None
        assert "Host" in game.get_players()

    def test_get_game_case_insensitive(self, game_manager):
        """Game ID lookup is case insensitive."""
        game_id, _, _ = game_manager.create_game("Host")
        lower_id = game_id.lower()
        game = game_manager.get_game(lower_id)
        assert game is not None

    def test_get_nonexistent_game(self, game_manager):
        """Nonexistent game returns None."""
        game = game_manager.get_game("XXXXXX")
        assert game is None

    def test_get_game_empty_id(self, game_manager):
        """Empty game ID returns None."""
        game = game_manager.get_game("")
        assert game is None


class TestGameDeletion:
    """Tests for deleting games."""

    def test_delete_game(self, game_manager):
        """Can delete a game."""
        game_id, _, _ = game_manager.create_game("Host")
        result = game_manager.delete_game(game_id)
        assert result is True
        assert game_manager.get_game(game_id) is None

    def test_delete_nonexistent_game(self, game_manager):
        """Deleting nonexistent game returns False."""
        result = game_manager.delete_game("XXXXXX")
        assert result is False

    def test_delete_game_case_insensitive(self, game_manager):
        """Game deletion is case insensitive."""
        game_id, _, _ = game_manager.create_game("Host")
        result = game_manager.delete_game(game_id.lower())
        assert result is True


class TestPlayerLookup:
    """Tests for player token lookup."""

    def test_get_player_by_token(self, game_manager):
        """Can get player name from token."""
        game_id, _, player_token = game_manager.create_game("Host")
        name = game_manager.get_player_by_token(game_id, player_token)
        assert name == "Host"

    def test_get_player_invalid_token(self, game_manager):
        """Invalid token returns None."""
        game_id, _, _ = game_manager.create_game("Host")
        name = game_manager.get_player_by_token(game_id, "invalid-token")
        assert name is None

    def test_get_player_wrong_game(self, game_manager):
        """Token from different game returns None."""
        game_id1, _, player_token1 = game_manager.create_game("Host1")
        game_id2, _, _ = game_manager.create_game("Host2")

        name = game_manager.get_player_by_token(game_id2, player_token1)
        assert name is None

    def test_get_player_nonexistent_game(self, game_manager):
        """Player lookup on nonexistent game returns None."""
        name = game_manager.get_player_by_token("XXXXXX", "some-token")
        assert name is None


class TestGMTokenCheck:
    """Tests for GM token verification."""

    def test_is_gm_token_valid(self, game_manager):
        """Valid GM token recognized."""
        game_id, gm_token, _ = game_manager.create_game("Host")
        assert game_manager.is_gm_token(game_id, gm_token) is True

    def test_is_gm_token_player_token(self, game_manager):
        """Player token is not GM token."""
        game_id, _, player_token = game_manager.create_game("Host")
        assert game_manager.is_gm_token(game_id, player_token) is False

    def test_is_gm_token_invalid(self, game_manager):
        """Invalid token is not GM token."""
        game_id, _, _ = game_manager.create_game("Host")
        assert game_manager.is_gm_token(game_id, "invalid-token") is False

    def test_is_gm_token_wrong_game(self, game_manager):
        """GM token from different game is not valid."""
        game_id1, gm_token1, _ = game_manager.create_game("Host1")
        game_id2, _, _ = game_manager.create_game("Host2")

        assert game_manager.is_gm_token(game_id2, gm_token1) is False

    def test_is_gm_token_nonexistent_game(self, game_manager):
        """GM check on nonexistent game returns False."""
        assert game_manager.is_gm_token("XXXXXX", "some-token") is False


class TestMultipleGames:
    """Tests for managing multiple games."""

    def test_multiple_games_independent(self, game_manager):
        """Multiple games are independent."""
        game_id1, _, _ = game_manager.create_game("Host1")
        game_id2, _, _ = game_manager.create_game("Host2")

        game1 = game_manager.get_game(game_id1)
        game2 = game_manager.get_game(game_id2)

        assert game1 is not game2
        assert "Host1" in game1.get_players()
        assert "Host2" in game2.get_players()
        assert "Host2" not in game1.get_players()

    def test_delete_one_game_preserves_others(self, game_manager):
        """Deleting one game doesn't affect others."""
        game_id1, _, _ = game_manager.create_game("Host1")
        game_id2, _, _ = game_manager.create_game("Host2")

        game_manager.delete_game(game_id1)

        assert game_manager.get_game(game_id1) is None
        assert game_manager.get_game(game_id2) is not None


class TestEdgeCases:
    """Edge case tests for GameManager."""

    def test_create_many_games(self, game_manager):
        """Can create many games without collision."""
        for i in range(50):
            game_id, _, _ = game_manager.create_game(f"Host{i}")
            assert game_manager.get_game(game_id) is not None

    def test_special_host_names(self, game_manager):
        """Various host names work."""
        names = ["Alice", "Bob123", "User_Name", "Player-1", "Name With Spaces"]
        for name in names:
            game_id, _, _ = game_manager.create_game(name)
            game = game_manager.get_game(game_id)
            assert name in game.get_players()

    def test_empty_host_name(self, game_manager):
        """Empty host name - depends on validation."""
        # GameAdapter doesn't validate, API does
        game_id, _, _ = game_manager.create_game("")
        game = game_manager.get_game(game_id)
        assert game is not None


class TestGlobalSingleton:
    """Tests for global game_manager singleton."""

    def test_singleton_exists(self):
        """Global game_manager exists."""
        assert game_manager is not None

    def test_singleton_is_game_manager(self):
        """Global instance is GameManager."""
        assert isinstance(game_manager, GameManager)
