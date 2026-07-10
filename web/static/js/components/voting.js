/**
 * Quantum Werewolf - Voting Component
 */

const Voting = {
    /**
     * Show the voting interface
     */
    show() {
        GameState.currentVote = null;
        GameState.voteConfirmed = false;

        // Populate vote options
        const container = document.getElementById('voteOptions');
        const players = GameState.livingPlayers.filter(p => p !== GameState.playerName);

        container.innerHTML = players.map(player => `
            <button class="vote-option" data-player="${player}">
                <span class="player-name">${player}</span>
                <span class="check">&#10003;</span>
            </button>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.vote-option').forEach(btn => {
            btn.addEventListener('click', () => this.selectVote(btn.dataset.player));
        });

        // Reset confirm button
        document.getElementById('btnConfirmVote').disabled = true;

        // Show/hide GM controls
        const gmControls = document.getElementById('gmVotingControls');
        if (GameState.isGM) {
            gmControls.classList.remove('hidden');
        } else {
            gmControls.classList.add('hidden');
        }

        // Update progress
        this.updateProgress({
            votes_cast: 0,
            total_players: GameState.livingPlayers.length,
            confirmations: 0
        });

        Utils.showView('voting');
    },

    /**
     * Select a vote target
     */
    selectVote(player) {
        if (GameState.voteConfirmed) return;

        GameState.currentVote = player;

        // Update UI
        document.querySelectorAll('.vote-option').forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.player === player);
        });

        // Enable confirm button
        document.getElementById('btnConfirmVote').disabled = false;
    },

    /**
     * Submit vote to server
     */
    async submitVote() {
        try {
            await SocketManager.vote(GameState.currentVote);
            Utils.toast(
                GameState.currentVote
                    ? `Voted for ${GameState.currentVote}`
                    : 'Abstaining from vote',
                'success'
            );
        } catch (error) {
            Utils.toast(error.message || 'Failed to submit vote', 'error');
        }
    },

    /**
     * Abstain from voting
     */
    async abstain() {
        if (GameState.voteConfirmed) return;

        GameState.currentVote = null;

        // Deselect all options
        document.querySelectorAll('.vote-option').forEach(btn => {
            btn.classList.remove('selected');
        });

        try {
            await SocketManager.vote(null);
            document.getElementById('btnConfirmVote').disabled = false;
            Utils.toast('You chose to abstain', 'info');
        } catch (error) {
            Utils.toast(error.message || 'Failed to abstain', 'error');
        }
    },

    /**
     * Confirm the vote
     */
    async confirmVote() {
        if (GameState.voteConfirmed) return;

        // First submit the vote if not already
        await this.submitVote();

        try {
            const response = await SocketManager.confirmVote();
            console.log('[DEBUG] confirmVote response:', response);
            GameState.voteConfirmed = true;

            // Disable voting controls
            document.querySelectorAll('.vote-option').forEach(btn => {
                btn.style.pointerEvents = 'none';
            });
            document.getElementById('btnAbstain').disabled = true;
            document.getElementById('btnConfirmVote').disabled = true;
            document.getElementById('btnConfirmVote').textContent = 'Vote Confirmed';

            Utils.toast('Vote confirmed', 'success');

            // Check if voting ended in the response
            if (response && response.voting_ended) {
                console.log('[DEBUG] Voting ended in response, phase:', response.phase);
                // The voting_ended event will handle the transition
                // But we can also update state here
                if (response.phase === 'day') {
                    GameState.phase = 'day';
                }
            }
        } catch (error) {
            Utils.toast(error.message || 'Failed to confirm vote', 'error');
        }
    },

    /**
     * Update voting progress display
     */
    updateProgress(data) {
        document.getElementById('votesCount').textContent = data.votes_cast;
        document.getElementById('votesTotal').textContent = data.total_players;
        document.getElementById('confirmCount').textContent = data.confirmations;
        document.getElementById('confirmTotal').textContent = data.total_players;
    },

    /**
     * Show voting results
     */
    showResults(data) {
        const content = document.getElementById('voteResultContent');

        if (data.lynched_player) {
            content.innerHTML = `
                <div class="lynch-result">
                    <div class="lynched-name">${data.lynched_player}</div>
                    <div class="lynched-role">
                        was lynched and revealed to be a
                        <span class="${Utils.getRoleClass(data.lynched_role)}">${data.lynched_role}</span>
                    </div>
                </div>
                <div class="vote-counts">
                    ${Object.entries(data.vote_counts)
                        .sort((a, b) => b[1] - a[1])
                        .map(([player, count]) => `
                            <div class="vote-count-item">
                                <span>${player}</span>
                                <span>${count} vote${count !== 1 ? 's' : ''}</span>
                            </div>
                        `).join('')}
                    ${data.abstentions > 0 ? `
                        <div class="vote-count-item">
                            <span>Abstentions</span>
                            <span>${data.abstentions}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            content.innerHTML = `
                <p class="no-lynch">No one was lynched today.</p>
                ${data.abstentions > 0 ? `
                    <p class="no-lynch">Abstentions: ${data.abstentions}</p>
                ` : ''}
            `;
        }

        Utils.showView('vote-results');
    },

    /**
     * Continue after viewing vote results
     */
    continueAfterVote() {
        // Return to day phase
        DayPhase.show([]);
    },

    /**
     * GM: End voting early
     */
    async endVoting() {
        if (!GameState.isGM) return;

        try {
            await SocketManager.gmEndVoting();
        } catch (error) {
            Utils.toast(error.message || 'Failed to end voting', 'error');
        }
    },

    /**
     * Setup voting event listeners
     */
    setupEventListeners() {
        document.getElementById('btnAbstain').addEventListener('click', () => {
            this.abstain();
        });

        document.getElementById('btnConfirmVote').addEventListener('click', () => {
            this.confirmVote();
        });

        document.getElementById('btnEndVoting').addEventListener('click', () => {
            this.endVoting();
        });

        document.getElementById('btnContinueAfterVote').addEventListener('click', () => {
            this.continueAfterVote();
        });
    }
};

// Expose globally
window.Voting = Voting;
