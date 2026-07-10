"""Comprehensive tests for REST API endpoints."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from main import app
from game_manager import game_manager


@pytest.fixture
def client():
    """Test client for API requests."""
    # Clear any existing games
    game_manager.games.clear()
    return TestClient(app)


@pytest.fixture
def created_game(client):
    """Create a game and return (game_id, gm_token, player_token)."""
    response = client.post("/api/games", json={"host_name": "TestHost"})
    data = response.json()
    return data["game_id"], data["gm_token"], data["player_token"]


@pytest.fixture
def game_with_players(client, created_game):
    """Game with 4 players."""
    game_id, gm_token, host_token = created_game

    players = [("TestHost", host_token)]
    for name in ["Alice", "Bob", "Craig"]:
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": name}
        )
        players.append((name, response.json()["player_token"]))

    return game_id, gm_token, players


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """GET /api/health returns ok."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "quantum-werewolf"

    def test_games_health_check(self, client):
        """GET /api/games/health returns ok with game count."""
        response = client.get("/api/games/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "active_games" in data


class TestGameCreation:
    """Tests for POST /api/games."""

    def test_create_game(self, client):
        """Can create a new game."""
        response = client.post("/api/games", json={"host_name": "Alice"})
        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert "gm_token" in data
        assert "player_token" in data
        assert "join_url" in data

    def test_create_game_generates_id(self, client):
        """Game ID is generated."""
        response = client.post("/api/games", json={"host_name": "Alice"})
        data = response.json()
        assert len(data["game_id"]) == 6
        assert data["game_id"].isalnum()

    def test_create_game_tokens_different(self, client):
        """GM and player tokens are different."""
        response = client.post("/api/games", json={"host_name": "Alice"})
        data = response.json()
        assert data["gm_token"] != data["player_token"]

    def test_create_game_invalid_empty_name(self, client):
        """Empty host name is rejected."""
        response = client.post("/api/games", json={"host_name": ""})
        assert response.status_code == 422  # Validation error

    def test_create_game_missing_name(self, client):
        """Missing host name is rejected."""
        response = client.post("/api/games", json={})
        assert response.status_code == 422


class TestGameInfo:
    """Tests for GET /api/games/{game_id}."""

    def test_get_game_info(self, client, created_game):
        """Can get game info."""
        game_id, _, _ = created_game
        response = client.get(f"/api/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id
        assert data["player_count"] == 1
        assert "TestHost" in data["players"]
        assert data["phase"] == "lobby"
        assert data["can_join"] is True

    def test_get_game_info_case_insensitive(self, client, created_game):
        """Game ID lookup is case insensitive."""
        game_id, _, _ = created_game
        response = client.get(f"/api/games/{game_id.lower()}")
        assert response.status_code == 200

    def test_get_nonexistent_game(self, client):
        """Nonexistent game returns 404."""
        response = client.get("/api/games/XXXXXX")
        assert response.status_code == 404


class TestJoinGame:
    """Tests for POST /api/games/{game_id}/join."""

    def test_join_game(self, client, created_game):
        """Can join an existing game."""
        game_id, _, _ = created_game
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": "Alice"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "Alice"
        assert "player_token" in data
        assert "Alice" in data["players"]

    def test_join_game_case_insensitive(self, client, created_game):
        """Can join with lowercase game ID."""
        game_id, _, _ = created_game
        response = client.post(
            f"/api/games/{game_id.lower()}/join",
            json={"player_name": "Alice"}
        )
        assert response.status_code == 200

    def test_join_nonexistent_game(self, client):
        """Joining nonexistent game returns 404."""
        response = client.post(
            "/api/games/XXXXXX/join",
            json={"player_name": "Alice"}
        )
        assert response.status_code == 404

    def test_join_duplicate_name(self, client, created_game):
        """Cannot join with duplicate name."""
        game_id, _, _ = created_game
        # First join
        client.post(f"/api/games/{game_id}/join", json={"player_name": "Alice"})
        # Second join with same name
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": "Alice"}
        )
        assert response.status_code == 400

    def test_join_empty_name(self, client, created_game):
        """Empty player name is rejected."""
        game_id, _, _ = created_game
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": ""}
        )
        assert response.status_code == 422

    def test_join_started_game(self, client, game_with_players):
        """Cannot join started game."""
        game_id, gm_token, _ = game_with_players

        # Start the game
        client.post(
            f"/api/games/{game_id}/start",
            headers={"Authorization": f"Bearer {gm_token}"}
        )

        # Try to join
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": "NewPlayer"}
        )
        assert response.status_code == 400


class TestDeckConfiguration:
    """Tests for PUT /api/games/{game_id}/deck."""

    def test_configure_deck(self, client, created_game):
        """GM can configure deck."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Bearer {gm_token}"},
            json={"werewolf": 1, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deck"]["werewolf"] == 1

    def test_configure_deck_no_token(self, client, created_game):
        """Deck config without token returns 401."""
        game_id, _, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            json={"werewolf": 1, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 401

    def test_configure_deck_player_token(self, client, created_game):
        """Deck config with player token returns 403."""
        game_id, _, player_token = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Bearer {player_token}"},
            json={"werewolf": 1, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 403

    def test_configure_deck_invalid_token(self, client, created_game):
        """Deck config with invalid token returns 403."""
        game_id, _, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": "Bearer invalid-token"},
            json={"werewolf": 1, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 403

    def test_configure_deck_nonexistent_game(self, client):
        """Deck config on nonexistent game returns 404."""
        response = client.put(
            "/api/games/XXXXXX/deck",
            headers={"Authorization": "Bearer some-token"},
            json={"werewolf": 1, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 404


class TestStartGame:
    """Tests for POST /api/games/{game_id}/start."""

    def test_start_game(self, client, game_with_players):
        """GM can start game."""
        game_id, gm_token, _ = game_with_players
        response = client.post(
            f"/api/games/{game_id}/start",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["phase"] == "night"
        assert data["turn"] == 1

    def test_start_game_insufficient_players(self, client, created_game):
        """Cannot start with less than 3 players."""
        game_id, gm_token, _ = created_game
        # Only host, need 2 more
        response = client.post(
            f"/api/games/{game_id}/start",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 400

    def test_start_game_no_token(self, client, game_with_players):
        """Start without token returns 401."""
        game_id, _, _ = game_with_players
        response = client.post(f"/api/games/{game_id}/start")
        assert response.status_code == 401

    def test_start_game_player_token(self, client, game_with_players):
        """Start with player token returns 403."""
        game_id, _, players = game_with_players
        _, player_token = players[1]  # Non-host player
        response = client.post(
            f"/api/games/{game_id}/start",
            headers={"Authorization": f"Bearer {player_token}"}
        )
        assert response.status_code == 403


class TestDeleteGame:
    """Tests for DELETE /api/games/{game_id}."""

    def test_delete_game(self, client, created_game):
        """GM can delete game."""
        game_id, gm_token, _ = created_game
        response = client.delete(
            f"/api/games/{game_id}",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/api/games/{game_id}")
        assert response.status_code == 404

    def test_delete_game_no_token(self, client, created_game):
        """Delete without token returns 401."""
        game_id, _, _ = created_game
        response = client.delete(f"/api/games/{game_id}")
        assert response.status_code == 401

    def test_delete_game_player_token(self, client, created_game):
        """Delete with player token returns 403."""
        game_id, _, player_token = created_game
        response = client.delete(
            f"/api/games/{game_id}",
            headers={"Authorization": f"Bearer {player_token}"}
        )
        assert response.status_code == 403


class TestStaticRoutes:
    """Tests for static file serving routes."""

    def test_index_route(self, client):
        """GET / serves index.html."""
        response = client.get("/")
        assert response.status_code == 200

    def test_join_route(self, client):
        """GET /join/{game_id} serves index.html."""
        response = client.get("/join/ABC123")
        assert response.status_code == 200

    def test_game_route(self, client):
        """GET /game/{game_id} serves index.html."""
        response = client.get("/game/ABC123")
        assert response.status_code == 200

    def test_gm_route(self, client):
        """GET /gm/{game_id} serves index.html."""
        response = client.get("/gm/ABC123")
        assert response.status_code == 200


class TestTokenFormats:
    """Tests for various token format handling."""

    def test_bearer_token_format(self, client, created_game):
        """Bearer token format works."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Bearer {gm_token}"},
            json={"werewolf": 2, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 200

    def test_missing_bearer_prefix(self, client, created_game):
        """Missing Bearer prefix returns 401."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": gm_token},  # No "Bearer " prefix
            json={"werewolf": 2, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 401

    def test_wrong_auth_type(self, client, created_game):
        """Wrong auth type returns 401."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Basic {gm_token}"},
            json={"werewolf": 2, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 401


class TestEdgeCases:
    """Edge case tests for API."""

    def test_long_player_name(self, client, created_game):
        """Long player name validation."""
        game_id, _, _ = created_game
        long_name = "A" * 50  # Over max_length=30
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": long_name}
        )
        assert response.status_code == 422

    def test_unicode_player_name(self, client, created_game):
        """Unicode characters in player name."""
        game_id, _, _ = created_game
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": "Spieler"}
        )
        # Should work
        assert response.status_code == 200

    def test_special_characters_in_name(self, client, created_game):
        """Special characters in player name."""
        game_id, _, _ = created_game
        response = client.post(
            f"/api/games/{game_id}/join",
            json={"player_name": "Player-1_Test"}
        )
        assert response.status_code == 200

    def test_deck_validation_werewolf_min(self, client, created_game):
        """Werewolf count minimum validation."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Bearer {gm_token}"},
            json={"werewolf": 0, "seer": 1, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 422

    def test_deck_validation_seer_max(self, client, created_game):
        """Seer count maximum validation."""
        game_id, gm_token, _ = created_game
        response = client.put(
            f"/api/games/{game_id}/deck",
            headers={"Authorization": f"Bearer {gm_token}"},
            json={"werewolf": 2, "seer": 5, "hunter": 0, "cupid": 0}
        )
        assert response.status_code == 422

    def test_game_info_after_players_join(self, client, game_with_players):
        """Game info updates with player count."""
        game_id, _, players = game_with_players
        response = client.get(f"/api/games/{game_id}")
        data = response.json()
        assert data["player_count"] == 4
        assert len(data["players"]) == 4

    def test_game_info_after_start(self, client, game_with_players):
        """Game info shows started phase."""
        game_id, gm_token, _ = game_with_players

        client.post(
            f"/api/games/{game_id}/start",
            headers={"Authorization": f"Bearer {gm_token}"}
        )

        response = client.get(f"/api/games/{game_id}")
        data = response.json()
        assert data["phase"] == "night"
        assert data["can_join"] is False


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_multiple_players_join(self, client, created_game):
        """Multiple players can join sequentially."""
        game_id, _, _ = created_game
        names = ["Alice", "Bob", "Craig", "David", "Eve"]

        for name in names:
            response = client.post(
                f"/api/games/{game_id}/join",
                json={"player_name": name}
            )
            assert response.status_code == 200

        response = client.get(f"/api/games/{game_id}")
        assert response.json()["player_count"] == 6  # Host + 5

    def test_create_multiple_games(self, client):
        """Can create multiple games."""
        game_ids = []
        for i in range(5):
            response = client.post(
                "/api/games",
                json={"host_name": f"Host{i}"}
            )
            assert response.status_code == 200
            game_ids.append(response.json()["game_id"])

        # All unique
        assert len(set(game_ids)) == 5

        # All accessible
        for game_id in game_ids:
            response = client.get(f"/api/games/{game_id}")
            assert response.status_code == 200
