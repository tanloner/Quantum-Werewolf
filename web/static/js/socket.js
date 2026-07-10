/**
 * Quantum Werewolf - Socket.IO Connection Management
 */

const SocketManager = {
    socket: null,
    connected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,

    /**
     * Connect to the game server
     */
    connect(gameId, token) {
        if (this.socket) {
            this.socket.disconnect();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        this.socket = io({
            auth: {
                game_id: gameId,
                token: token
            },
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000
        });

        this.setupEventHandlers();
        return this.socket;
    },

    /**
     * Disconnect from server
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.connected = false;
    },

    /**
     * Setup all socket event handlers
     */
    setupEventHandlers() {
        const socket = this.socket;

        // Connection events
        socket.on('connect', () => {
            console.log('Connected to server');
            this.connected = true;
            this.reconnectAttempts = 0;
            Utils.toast('Connected to game server', 'success');
        });

        socket.on('disconnect', (reason) => {
            console.log('Disconnected:', reason);
            this.connected = false;
            Utils.toast('Disconnected from server', 'warning');
        });

        socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.reconnectAttempts++;
            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                Utils.toast('Could not connect to server', 'error');
            }
        });

        // Game state events
        socket.on('game_state', (data) => {
            console.log('Game state:', data);
            this.handleGameState(data);
        });

        socket.on('player_joined', (data) => {
            console.log('Player joined:', data);
            GameState.players = [...GameState.players, data.player_name];
            if (typeof Lobby !== 'undefined') {
                Lobby.updatePlayerList();
            }
            Utils.toast(`${data.player_name} joined the game`, 'info');
        });

        socket.on('game_started', (data) => {
            console.log('Game started:', data);
            GameState.phase = data.phase;
            GameState.turn = data.turn;
            // Update players list from game_started event
            if (data.players) {
                GameState.players = data.players;
            }
            if (data.living_players) {
                GameState.livingPlayers = data.living_players;
            }
            Utils.playSound('soundTurn');
            Utils.showView('night');
            NightPhase.showWaiting('Game started! Waiting for your turn...');
        });

        // Night phase events
        socket.on('your_turn', (data) => {
            console.log('Your turn:', data);
            // Update living players from turn data
            if (data.living_players) {
                GameState.livingPlayers = data.living_players;
            }
            Utils.playSound('soundTurn');
            NightPhase.showYourTurn(data);
        });

        socket.on('turn_ended', () => {
            console.log('Turn ended');
            NightPhase.showWaiting('Waiting for other players...');
        });

        socket.on('turn_skipped', () => {
            console.log('Turn was skipped');
            Utils.toast('Your turn was skipped by the Game Master', 'warning');
            NightPhase.showWaiting('Waiting for other players...');
        });

        // Phase change events
        socket.on('phase_change', (data) => {
            console.log('Phase change:', data);
            GameState.phase = data.phase;
            GameState.turn = data.turn;

            if (data.phase === 'day') {
                Utils.playSound('soundTurn');
                DayPhase.show(data.deaths || []);
            } else if (data.phase === 'night') {
                Utils.showView('night');
                NightPhase.showWaiting('Night has fallen...');
            }
        });

        socket.on('stats_update', (data) => {
            console.log('Stats update:', data);
            GameState.stats = data.stats;
            if (typeof DayPhase !== 'undefined') {
                DayPhase.updateStatsTable();
            }
        });

        socket.on('your_number', (data) => {
            console.log('Your number:', data);
            GameState.myNumber = data.number;
            if (typeof DayPhase !== 'undefined') {
                DayPhase.updateStatsTable();
            }
        });

        // Voting events
        socket.on('voting_started', (data) => {
            console.log('Voting started:', data);
            GameState.phase = 'voting';
            GameState.livingPlayers = data.living_players;
            Utils.playSound('soundVote');
            Voting.show();
        });

        socket.on('vote_progress', (data) => {
            console.log('Vote progress:', data);
            Voting.updateProgress(data);
        });

        socket.on('voting_ended', (data) => {
            console.log('Voting ended:', data);
            if (data.lynched_player) {
                Utils.playSound('soundDeath');
            }
            Voting.showResults(data);
        });

        // Game over
        socket.on('game_over', (data) => {
            console.log('Game over:', data);
            GameState.phase = 'ended';
            this.handleGameOver(data);
        });

        // GM-specific events
        socket.on('gm_state', (data) => {
            console.log('GM state:', data);
            if (typeof GMDashboard !== 'undefined') {
                GMDashboard.update(data);
            }
        });
    },

    /**
     * Handle initial game state on connection
     */
    handleGameState(data) {
        GameState.phase = data.phase;
        GameState.turn = data.turn;
        GameState.players = data.players;
        GameState.livingPlayers = data.living_players;
        GameState.myNumber = data.your_number;
        GameState.playerName = data.your_name;

        if (data.stats) {
            GameState.stats = data.stats;
        }

        // Show appropriate view based on phase
        switch (data.phase) {
            case 'lobby':
                Utils.showView('lobby');
                Lobby.init();
                break;
            case 'night':
                Utils.showView('night');
                if (data.is_your_turn) {
                    // Will receive your_turn event separately
                    NightPhase.showWaiting('Loading your turn...');
                } else {
                    NightPhase.showWaiting('Waiting for other players...');
                }
                break;
            case 'day':
                DayPhase.show(data.deaths_this_round || []);
                break;
            case 'voting':
                GameState.phase = 'voting';
                Voting.show();
                break;
            case 'ended':
                this.handleGameOver({ winner: data.winner });
                break;
        }
    },

    /**
     * Handle game over
     */
    handleGameOver(data) {
        const view = document.getElementById('view-gameover');
        const winnerDisplay = document.getElementById('winnerDisplay');
        const announcement = document.getElementById('winnerAnnouncement');
        const finalRoles = document.getElementById('finalRolesList');

        let icon, text, winnerClass;

        switch (data.winner) {
            case 'villagers':
                icon = '&#127968;';
                text = 'The Village Wins!';
                winnerClass = 'villagers';
                break;
            case 'werewolves':
                icon = '&#128058;';
                text = 'The Werewolves Win!';
                winnerClass = 'werewolves';
                break;
            case 'lovers':
                icon = '&#128149;';
                text = 'The Lovers Win!';
                winnerClass = 'lovers';
                break;
            default:
                icon = '&#9760;';
                text = 'Everyone Died!';
                winnerClass = '';
        }

        winnerDisplay.className = `winner-display ${winnerClass}`;
        winnerDisplay.innerHTML = `
            <div class="winner-icon">${icon}</div>
            <div class="winner-text">${text}</div>
        `;

        // Display final roles if available
        if (data.final_roles && data.final_roles.length > 0) {
            finalRoles.innerHTML = data.final_roles.map(p => `
                <li>
                    <span class="player-name">${p.name}</span>
                    <span class="player-role ${Utils.getRoleClass(p.role)}">${p.role}</span>
                </li>
            `).join('');
        }

        Utils.showView('gameover');
    },

    /**
     * Emit socket event with callback
     */
    emit(event, data = {}) {
        return new Promise((resolve, reject) => {
            if (!this.socket || !this.connected) {
                reject(new Error('Not connected'));
                return;
            }

            this.socket.emit(event, data, (response) => {
                if (response && response.error) {
                    reject(new Error(response.error));
                } else {
                    resolve(response);
                }
            });
        });
    },

    // Player actions
    async seerAction(target) {
        return this.emit('seer_action', { target });
    },

    async werewolfAction(target) {
        return this.emit('werewolf_action', { target });
    },

    async cupidAction(lover1, lover2) {
        return this.emit('cupid_action', { lover1, lover2 });
    },

    async endTurn() {
        return this.emit('end_turn');
    },

    async vote(target) {
        return this.emit('vote', { target });
    },

    async confirmVote() {
        return this.emit('confirm_vote');
    },

    async requestStats() {
        return this.emit('request_stats');
    },

    // GM actions
    async gmSkipTurn() {
        return this.emit('gm_skip_turn');
    },

    async gmStartVoting() {
        return this.emit('gm_start_voting');
    },

    async gmEndVoting() {
        return this.emit('gm_end_voting');
    },

    async gmStartNight() {
        return this.emit('gm_start_night');
    }
};

// Expose globally
window.SocketManager = SocketManager;
