/**
 * Quantum Werewolf - Game Master Dashboard Component
 */

const GMDashboard = {
    /**
     * Initialize GM dashboard
     */
    init() {
        Utils.showView('gm');
    },

    /**
     * Update dashboard with new state
     */
    update(data) {
        // Update status panel
        document.getElementById('gmPhase').textContent = data.phase;
        document.getElementById('gmTurn').textContent = data.turn;
        document.getElementById('gmCurrentPlayer').textContent = data.current_player || '--';

        // Update turn order display
        this.updateTurnOrder(data);

        // Update action log
        this.updateActionLog(data.actions_log);

        // Update votes display if voting
        this.updateVotes(data);

        // Update button states
        this.updateButtons(data.phase);
    },

    /**
     * Update turn order display
     */
    updateTurnOrder(data) {
        const container = document.getElementById('gmTurnOrder');

        if (data.phase !== 'night') {
            container.innerHTML = '<em>Not in night phase</em>';
            return;
        }

        const allPlayers = [
            ...data.completed_players.map(p => ({ name: p, status: 'completed' })),
            ...(data.current_player ? [{ name: data.current_player, status: 'current' }] : []),
            ...data.pending_players.map(p => ({ name: p, status: 'pending' }))
        ];

        container.innerHTML = allPlayers.map(p => `
            <span class="player-tag ${p.status}">${p.name}</span>
        `).join('');
    },

    /**
     * Update action log display
     */
    updateActionLog(actions) {
        const container = document.getElementById('gmActionLog');

        if (!actions || actions.length === 0) {
            container.innerHTML = '<em>No actions yet</em>';
            return;
        }

        container.innerHTML = actions.slice().reverse().map(action => {
            let actionText = '';

            switch (action.action) {
                case 'seer':
                    actionText = `observed ${action.target} (${action.result})`;
                    break;
                case 'werewolf':
                    actionText = `attacked ${action.target}`;
                    break;
                case 'cupid':
                    actionText = `paired ${action.target}`;
                    break;
                case 'skipped':
                    actionText = 'was skipped';
                    break;
                case 'lynched':
                    actionText = `was lynched (${action.role})`;
                    break;
                default:
                    actionText = action.action;
            }

            return `
                <div class="log-entry">
                    <span class="turn">T${action.turn}</span>
                    <span class="player">${action.player}</span>
                    <span class="action">${actionText}</span>
                </div>
            `;
        }).join('');
    },

    /**
     * Update votes display
     */
    updateVotes(data) {
        const panel = document.getElementById('gmVotesPanel');
        const container = document.getElementById('gmVotesDisplay');

        if (data.phase !== 'voting') {
            panel.classList.add('hidden');
            return;
        }

        panel.classList.remove('hidden');

        const confirmations = new Set(data.vote_confirmations || []);

        container.innerHTML = Object.entries(data.votes || {}).map(([voter, target]) => {
            const isConfirmed = confirmations.has(voter);
            return `
                <div class="vote-entry">
                    <span class="voter">${voter}</span>
                    <span class="target">${target || '(abstain)'}</span>
                    ${isConfirmed ? '<span class="confirmed">Confirmed</span>' : ''}
                </div>
            `;
        }).join('');
    },

    /**
     * Update button states based on phase
     */
    updateButtons(phase) {
        const skipBtn = document.getElementById('gmBtnSkipTurn');
        const startVotingBtn = document.getElementById('gmBtnStartVoting');
        const endVotingBtn = document.getElementById('gmBtnEndVoting');
        const startNightBtn = document.getElementById('gmBtnStartNight');

        // Disable all by default
        skipBtn.disabled = true;
        startVotingBtn.disabled = true;
        endVotingBtn.disabled = true;
        startNightBtn.disabled = true;

        switch (phase) {
            case 'night':
                skipBtn.disabled = false;
                break;
            case 'day':
                startVotingBtn.disabled = false;
                startNightBtn.disabled = false;
                break;
            case 'voting':
                endVotingBtn.disabled = false;
                break;
        }
    },

    /**
     * Skip current player's turn
     */
    async skipTurn() {
        try {
            const result = await SocketManager.gmSkipTurn();
            if (result.success) {
                Utils.toast(`Skipped ${result.skipped}'s turn`, 'success');
            }
        } catch (error) {
            Utils.toast(error.message || 'Failed to skip turn', 'error');
        }
    },

    /**
     * Start voting phase
     */
    async startVoting() {
        try {
            await SocketManager.gmStartVoting();
            Utils.toast('Voting phase started', 'success');
        } catch (error) {
            Utils.toast(error.message || 'Failed to start voting', 'error');
        }
    },

    /**
     * End voting phase
     */
    async endVoting() {
        try {
            await SocketManager.gmEndVoting();
            Utils.toast('Voting ended', 'success');
        } catch (error) {
            Utils.toast(error.message || 'Failed to end voting', 'error');
        }
    },

    /**
     * Start next night phase
     */
    async startNight() {
        try {
            await SocketManager.gmStartNight();
            Utils.toast('Night phase started', 'success');
        } catch (error) {
            Utils.toast(error.message || 'Failed to start night', 'error');
        }
    },

    /**
     * Setup GM dashboard event listeners
     */
    setupEventListeners() {
        document.getElementById('gmBtnSkipTurn').addEventListener('click', () => {
            this.skipTurn();
        });

        document.getElementById('gmBtnStartVoting').addEventListener('click', () => {
            this.startVoting();
        });

        document.getElementById('gmBtnEndVoting').addEventListener('click', () => {
            this.endVoting();
        });

        document.getElementById('gmBtnStartNight').addEventListener('click', () => {
            this.startNight();
        });
    }
};

// Expose globally
window.GMDashboard = GMDashboard;
