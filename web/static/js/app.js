/**
 * Quantum Werewolf - Main Application
 */

const App = {
    /**
     * Initialize the application
     */
    init() {
        console.log('Quantum Werewolf initializing...');

        // Load sound preference
        const soundPref = Utils.retrieve('soundEnabled');
        GameState.soundEnabled = soundPref !== false;
        this.updateSoundIcon();

        // Setup event listeners
        this.setupEventListeners();
        Lobby.setupEventListeners();
        NightPhase.setupEventListeners();
        DayPhase.setupEventListeners();
        Voting.setupEventListeners();
        GMDashboard.setupEventListeners();

        // Check URL for direct navigation
        this.handleUrlRouting();
    },

    /**
     * Handle URL-based routing
     */
    handleUrlRouting() {
        const viewType = Utils.getViewFromUrl();
        const gameId = Utils.getGameIdFromUrl();

        if (viewType === 'join' && gameId) {
            // Pre-fill game code and show join form
            document.getElementById('gameCode').value = gameId;
            Utils.showView('join');
        } else if (viewType === 'game' && gameId) {
            // Try to reconnect to game
            this.tryReconnect(gameId);
        } else if (viewType === 'gm' && gameId) {
            // Try to reconnect as GM
            this.tryReconnectGM(gameId);
        } else {
            // Show home
            Utils.showView('home');
        }
    },

    /**
     * Try to reconnect to a game
     */
    async tryReconnect(gameId) {
        if (GameState.loadSession() && GameState.gameId === gameId && GameState.playerToken) {
            try {
                // Verify game exists
                const info = await Utils.api(`/games/${gameId}`);
                if (info) {
                    SocketManager.connect(gameId, GameState.playerToken);
                    return;
                }
            } catch (error) {
                console.log('Game not found or expired');
            }
        }

        // If reconnect fails, show join form
        document.getElementById('gameCode').value = gameId;
        Utils.showView('join');
    },

    /**
     * Try to reconnect as GM
     */
    async tryReconnectGM(gameId) {
        if (GameState.loadSession() && GameState.gameId === gameId && GameState.gmToken) {
            try {
                const info = await Utils.api(`/games/${gameId}`);
                if (info) {
                    GameState.isGM = true;
                    SocketManager.connect(gameId, GameState.gmToken);
                    GMDashboard.init();
                    return;
                }
            } catch (error) {
                console.log('Game not found or expired');
            }
        }

        // If reconnect fails, go home
        Utils.showView('home');
        Utils.toast('Could not reconnect to game', 'error');
    },

    /**
     * Create a new game
     */
    async createGame(hostName) {
        try {
            Utils.showLoading();

            const response = await Utils.api('/games', {
                method: 'POST',
                body: JSON.stringify({ host_name: hostName })
            });

            // Store game state
            GameState.gameId = response.game_id;
            GameState.gmToken = response.gm_token;
            GameState.playerToken = response.player_token;
            GameState.playerName = hostName;
            GameState.isGM = true;
            GameState.players = [hostName];
            GameState.saveSession();

            // Connect to WebSocket
            SocketManager.connect(response.game_id, response.player_token);

            // Show lobby
            Utils.showView('lobby');
            Lobby.init();

            // Update URL
            history.pushState({}, '', `/game/${response.game_id}`);

            Utils.toast('Game created!', 'success');

        } catch (error) {
            Utils.toast(error.message || 'Failed to create game', 'error');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Join an existing game
     */
    async joinGame(gameCode, playerName) {
        try {
            Utils.showLoading();

            const response = await Utils.api(`/games/${gameCode}/join`, {
                method: 'POST',
                body: JSON.stringify({ player_name: playerName })
            });

            // Store game state
            GameState.gameId = gameCode.toUpperCase();
            GameState.playerToken = response.player_token;
            GameState.playerName = playerName;
            GameState.isGM = false;
            GameState.players = response.players;
            GameState.saveSession();

            // Connect to WebSocket
            SocketManager.connect(GameState.gameId, response.player_token);

            // Show lobby
            Utils.showView('lobby');
            Lobby.init();

            // Update URL
            history.pushState({}, '', `/game/${GameState.gameId}`);

            Utils.toast('Joined game!', 'success');

        } catch (error) {
            Utils.toast(error.message || 'Failed to join game', 'error');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Toggle sound on/off
     */
    toggleSound() {
        GameState.soundEnabled = !GameState.soundEnabled;
        Utils.store('soundEnabled', GameState.soundEnabled);
        this.updateSoundIcon();
    },

    /**
     * Update sound icon based on state
     */
    updateSoundIcon() {
        const toggle = document.getElementById('soundToggle');
        const iconOn = toggle.querySelector('.icon-sound-on');
        const iconOff = toggle.querySelector('.icon-sound-off');

        if (GameState.soundEnabled) {
            iconOn.classList.remove('hidden');
            iconOff.classList.add('hidden');
        } else {
            iconOn.classList.add('hidden');
            iconOff.classList.remove('hidden');
        }
    },

    /**
     * Start a new game (from game over screen)
     */
    newGame() {
        GameState.reset();
        GameState.clearSession();
        SocketManager.disconnect();

        // Clear form inputs
        document.getElementById('gameCode').value = '';
        document.getElementById('hostName').value = '';

        Utils.showView('home');
        history.pushState({}, '', '/');
    },

    /**
     * Setup main event listeners
     */
    setupEventListeners() {
        // Home view buttons
        document.getElementById('btnCreateGame').addEventListener('click', () => {
            document.getElementById('hostName').value = '';
            Utils.showView('create');
        });

        document.getElementById('btnJoinGame').addEventListener('click', () => {
            // Clear game code but preserve player name if set
            document.getElementById('gameCode').value = '';
            Utils.showView('join');
        });

        // Create game form
        document.getElementById('formCreate').addEventListener('submit', (e) => {
            e.preventDefault();
            const hostName = document.getElementById('hostName').value.trim();
            if (hostName) {
                this.createGame(hostName);
            }
        });

        document.getElementById('btnBackFromCreate').addEventListener('click', () => {
            document.getElementById('hostName').value = '';
            Utils.showView('home');
        });

        // Join game form
        document.getElementById('formJoin').addEventListener('submit', (e) => {
            e.preventDefault();
            const gameCode = document.getElementById('gameCode').value.trim();
            const playerName = document.getElementById('playerName').value.trim();
            if (gameCode && playerName) {
                this.joinGame(gameCode, playerName);
            }
        });

        document.getElementById('btnBackFromJoin').addEventListener('click', () => {
            document.getElementById('gameCode').value = '';
            Utils.showView('home');
        });

        // Sound toggle
        document.getElementById('soundToggle').addEventListener('click', () => {
            this.toggleSound();
        });

        // New game button (game over screen)
        document.getElementById('btnNewGame').addEventListener('click', () => {
            this.newGame();
        });

        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            this.handleUrlRouting();
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Expose globally
window.App = App;
