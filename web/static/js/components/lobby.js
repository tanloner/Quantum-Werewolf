/**
 * Quantum Werewolf - Lobby Component
 */

const Lobby = {
    /**
     * Initialize lobby view
     */
    init() {
        this.updatePlayerList();
        this.updateDeckDisplay();

        // Show/hide GM controls
        const gmControls = document.getElementById('gmLobbyControls');
        const waitingText = document.getElementById('waitingForGM');

        if (GameState.isGM) {
            gmControls.classList.remove('hidden');
            waitingText.classList.add('hidden');
        } else {
            gmControls.classList.add('hidden');
            waitingText.classList.remove('hidden');
        }

        // Update game code display
        document.getElementById('lobbyGameCode').textContent = GameState.gameId;
    },

    /**
     * Update the player list display
     */
    updatePlayerList() {
        const list = document.getElementById('playersList');
        const count = document.getElementById('playerCount');

        list.innerHTML = GameState.players.map((name, index) => {
            const isHost = index === 0;
            return `<li class="${isHost ? 'host' : ''}">${name}</li>`;
        }).join('');

        count.textContent = GameState.players.length;
    },

    /**
     * Update deck configuration display
     */
    updateDeckDisplay() {
        document.getElementById('deckWerewolf').textContent = GameState.deck.werewolf;
        document.getElementById('deckSeer').textContent = GameState.deck.seer;
        document.getElementById('deckHunter').textContent = GameState.deck.hunter;
        document.getElementById('deckCupid').textContent = GameState.deck.cupid;
    },

    /**
     * Handle deck counter changes
     */
    async changeDeckRole(role, delta) {
        const current = GameState.deck[role];
        const newValue = Math.max(0, current + delta);

        // Role-specific limits
        if (role === 'werewolf' && newValue < 1) return;
        if (['seer', 'hunter', 'cupid'].includes(role) && newValue > 1) return;
        if (role === 'werewolf' && newValue > 10) return;

        GameState.deck[role] = newValue;
        this.updateDeckDisplay();

        // Send to server if GM
        if (GameState.isGM) {
            try {
                await Utils.api(`/games/${GameState.gameId}/deck`, {
                    method: 'PUT',
                    body: JSON.stringify(GameState.deck)
                });
            } catch (error) {
                // Revert on error
                GameState.deck[role] = current;
                this.updateDeckDisplay();
                Utils.toast('Failed to update deck', 'error');
            }
        }
    },

    /**
     * Start the game (GM only)
     */
    async startGame() {
        if (!GameState.isGM) return;

        if (GameState.players.length < 3) {
            Utils.toast('Need at least 3 players to start', 'warning');
            return;
        }

        try {
            Utils.showLoading();
            await Utils.api(`/games/${GameState.gameId}/start`, {
                method: 'POST'
            });
            // Game start will be handled by socket event
        } catch (error) {
            Utils.toast(error.message || 'Failed to start game', 'error');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Setup lobby event listeners
     */
    setupEventListeners() {
        // Copy game code
        document.getElementById('btnCopyCode').addEventListener('click', () => {
            const url = `${window.location.origin}/join/${GameState.gameId}`;
            Utils.copyToClipboard(url);
        });

        // Deck counters
        document.querySelectorAll('.btn-counter').forEach(btn => {
            btn.addEventListener('click', () => {
                const role = btn.dataset.role;
                const delta = parseInt(btn.dataset.delta);
                this.changeDeckRole(role, delta);
            });
        });

        // Start game
        document.getElementById('btnStartGame').addEventListener('click', () => {
            this.startGame();
        });
    }
};

// Expose globally
window.Lobby = Lobby;
