/**
 * Quantum Werewolf - Day Phase Component
 */

const DayPhase = {
    /**
     * Show the day phase view
     */
    show(deaths = []) {
        document.getElementById('dayTurn').textContent = GameState.turn;
        Utils.showView('day');

        // Show death announcements if any
        this.showDeaths(deaths);

        // Update stats table
        this.updateStatsTable();

        // Show/hide GM controls
        const gmControls = document.getElementById('gmDayControls');
        if (GameState.isGM) {
            gmControls.classList.remove('hidden');
        } else {
            gmControls.classList.add('hidden');
        }
    },

    /**
     * Show death announcements
     */
    showDeaths(deaths) {
        const container = document.getElementById('deathAnnouncements');
        const list = document.getElementById('deathsList');

        if (!deaths || deaths.length === 0) {
            container.classList.add('hidden');
            return;
        }

        container.classList.remove('hidden');
        list.innerHTML = deaths.map(death => `
            <div class="death-item">
                <div class="name">${death.name}</div>
                <div class="role">was a <span class="${Utils.getRoleClass(death.role)}">${death.role}</span></div>
            </div>
        `).join('');
    },

    /**
     * Update the anonymous stats table
     */
    updateStatsTable() {
        const tbody = document.getElementById('statsTableBody');

        if (!GameState.stats || GameState.stats.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">Loading stats...</td></tr>';
            return;
        }

        tbody.innerHTML = GameState.stats.map(player => {
            const isYou = player.number === GameState.myNumber;
            const isDead = player.is_dead;

            const rowClass = [
                isYou ? 'your-row' : '',
                isDead ? 'dead-row' : ''
            ].filter(Boolean).join(' ');

            const displayName = isDead
                ? `${player.revealed_name} (${player.revealed_role})`
                : (isYou ? `#${player.number} (You)` : `#${player.number}`);

            const status = isDead ? 'Dead' : 'Alive';

            const probs = player.probabilities || {};
            const wolfProb = probs.werewolf || 0;
            const seerProb = probs.seer || 0;
            const villagerProb = probs.villager || 0;

            return `
                <tr class="${rowClass}">
                    <td>${displayName}</td>
                    <td>${status}</td>
                    <td>
                        ${Math.round(wolfProb * 100)}%
                        ${ProbabilityBar.createMini('werewolf', wolfProb)}
                    </td>
                    <td>
                        ${Math.round(seerProb * 100)}%
                        ${ProbabilityBar.createMini('seer', seerProb)}
                    </td>
                    <td>
                        ${Math.round(villagerProb * 100)}%
                        ${ProbabilityBar.createMini('villager', villagerProb)}
                    </td>
                    <td>
                        ${isDead ? '-' : Math.round(player.death_probability * 100) + '%'}
                        ${isDead ? '' : ProbabilityBar.createMini('death', player.death_probability)}
                    </td>
                </tr>
            `;
        }).join('');
    },

    /**
     * Refresh stats from server
     */
    async refreshStats() {
        try {
            const result = await SocketManager.requestStats();
            if (result.success) {
                GameState.stats = result.stats;
                if (result.your_number) {
                    GameState.myNumber = result.your_number;
                }
                this.updateStatsTable();
                Utils.toast('Stats refreshed', 'success');
            }
        } catch (error) {
            Utils.toast('Failed to refresh stats', 'error');
        }
    },

    /**
     * GM: Start voting phase
     */
    async startVoting() {
        if (!GameState.isGM) return;

        try {
            await SocketManager.gmStartVoting();
        } catch (error) {
            Utils.toast(error.message || 'Failed to start voting', 'error');
        }
    },

    /**
     * GM: Start next night phase
     */
    async startNight() {
        if (!GameState.isGM) return;

        try {
            await SocketManager.gmStartNight();
        } catch (error) {
            Utils.toast(error.message || 'Failed to start night', 'error');
        }
    },

    /**
     * Setup day phase event listeners
     */
    setupEventListeners() {
        document.getElementById('btnRefreshStats').addEventListener('click', () => {
            this.refreshStats();
        });

        document.getElementById('btnStartVoting').addEventListener('click', () => {
            this.startVoting();
        });

        document.getElementById('btnStartNight').addEventListener('click', () => {
            this.startNight();
        });
    }
};

// Expose globally
if (typeof window !== 'undefined') {
    window.DayPhase = DayPhase;
} else {
    globalThis.DayPhase = DayPhase;
}