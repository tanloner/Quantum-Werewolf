/**
 * Quantum Werewolf - Night Phase Component
 */

const NightPhase = {
    turnData: null,
    seerUsed: false,
    werewolfUsed: false,
    cupidUsed: false,

    /**
     * Show the waiting screen
     */
    showWaiting(message = 'Waiting for other players...') {
        document.getElementById('nightTurn').textContent = GameState.turn;
        document.getElementById('nightYourTurn').classList.add('hidden');
        document.getElementById('nightWaiting').classList.remove('hidden');
        document.getElementById('waitingMessage').textContent = message;
        Utils.showView('night');
    },

    /**
     * Show the player's turn interface
     */
    showYourTurn(data) {
        this.turnData = data;
        this.seerUsed = false;
        this.werewolfUsed = false;
        this.cupidUsed = false;

        document.getElementById('seerTarget').disabled = false;
        document.getElementById('btnSeerAction').disabled = false;
        document.getElementById('werewolfTarget').disabled = false;
        document.getElementById('btnWerewolfAction').disabled = false;
        document.getElementById('cupidLover1').disabled = false;
        document.getElementById('cupidLover2').disabled = false;
        document.getElementById('btnCupidAction').disabled = false;

        document.getElementById('nightTurn').textContent = GameState.turn;
        document.getElementById('nightWaiting').classList.add('hidden');
        document.getElementById('nightYourTurn').classList.remove('hidden');
        Utils.showView('night');

        // Update role probabilities
        this.updateRoleProbabilities(data.your_probabilities);

        // Update werewolf info
        this.updateWerewolfInfo(data.other_werewolves);

        // Show available action panels
        this.updateActionPanels(data.available_actions, data.is_first_night);

        // Populate player selects
        this.populatePlayerSelects();
    },

    /**
     * Update role probability display
     */
    updateRoleProbabilities(probabilities) {
        const container = document.querySelector('#yourRoleProbabilities .prob-bars');
        container.innerHTML = ProbabilityBar.createAll(probabilities);
    },

    /**
     * Update werewolf info display
     */
    updateWerewolfInfo(otherWerewolves) {
        const container = document.getElementById('werewolfInfo');
        const list = document.getElementById('wolfList');

        if (!otherWerewolves || otherWerewolves.length === 0) {
            container.classList.add('hidden');
            return;
        }

        container.classList.remove('hidden');

        list.innerHTML = otherWerewolves.map(wolf => `
            <div class="wolf-item">
                <span class="name">${wolf.name}</span>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${Math.round(wolf.probability * 100)}%"></div>
                </div>
                <span class="percentage">${Math.round(wolf.probability * 100)}%</span>
            </div>
        `).join('');
    },

    /**
     * Update which action panels are visible
     */
    updateActionPanels(availableActions, isFirstNight) {
        // Hide all panels first
        document.getElementById('seerPanel').classList.add('hidden');
        document.getElementById('werewolfPanel').classList.add('hidden');
        document.getElementById('cupidPanel').classList.add('hidden');
        document.getElementById('seerResult').classList.add('hidden');

        // Show available panels
        if (availableActions.includes('seer')) {
            document.getElementById('seerPanel').classList.remove('hidden');
        }
        if (availableActions.includes('werewolf')) {
            document.getElementById('werewolfPanel').classList.remove('hidden');
        }
        if (availableActions.includes('cupid') && isFirstNight) {
            document.getElementById('cupidPanel').classList.remove('hidden');
        }
    },

    /**
     * Populate player select dropdowns
     */
    populatePlayerSelects() {
        // Use living players from turn data, fallback to GameState
        const players = (this.turnData && this.turnData.living_players && this.turnData.living_players.length > 0)
            ? this.turnData.living_players
            : (GameState.livingPlayers.length > 0 ? GameState.livingPlayers : GameState.players);

        const otherPlayers = players.filter(p => p !== GameState.playerName);

        // Seer target
        const seerSelect = document.getElementById('seerTarget');
        seerSelect.innerHTML = '<option value="">-- Select Player --</option>' +
            otherPlayers.map(p => `<option value="${p}">${p}</option>`).join('');

        // Werewolf target
        const werewolfSelect = document.getElementById('werewolfTarget');
        werewolfSelect.innerHTML = '<option value="">-- Select Victim --</option>' +
            otherPlayers.map(p => `<option value="${p}">${p}</option>`).join('');

        // Cupid lovers
        const allPlayers = GameState.livingPlayers.length > 0
            ? GameState.livingPlayers
            : GameState.players;

        const cupid1Select = document.getElementById('cupidLover1');
        cupid1Select.innerHTML = '<option value="">-- First Lover --</option>' +
            allPlayers.map(p => `<option value="${p}">${p}</option>`).join('');

        const cupid2Select = document.getElementById('cupidLover2');
        cupid2Select.innerHTML = '<option value="">-- Second Lover --</option>' +
            allPlayers.map(p => `<option value="${p}">${p}</option>`).join('');

    },

    /**
     * Handle seer action
     */
    async doSeerAction() {
        const target = document.getElementById('seerTarget').value;
        if (!target) {
            Utils.toast('Select a player to observe', 'warning');
            return;
        }

        try {
            const result = await SocketManager.seerAction(target);
            this.seerUsed = true;

            // Show result
            const resultDiv = document.getElementById('seerResult');
            resultDiv.querySelector('.target-name').textContent = target;
            const roleSpan = resultDiv.querySelector('.target-role');
            roleSpan.textContent = result.role;
            roleSpan.className = `target-role ${Utils.getRoleClass(result.role)}`;
            resultDiv.classList.remove('hidden');

            // Disable seer controls
            document.getElementById('seerTarget').disabled = true;
            document.getElementById('btnSeerAction').disabled = true;

            Utils.toast(`${target} is a ${result.role}!`, 'success');
        } catch (error) {
            Utils.toast(error.message || 'Seer action failed', 'error');
        }
    },

    /**
     * Handle werewolf action
     */
    async doWerewolfAction() {
        const target = document.getElementById('werewolfTarget').value;
        if (!target) {
            Utils.toast('Select a victim to attack', 'warning');
            return;
        }

        try {
            await SocketManager.werewolfAction(target);
            this.werewolfUsed = true;

            // Disable werewolf controls
            document.getElementById('werewolfTarget').disabled = true;
            document.getElementById('btnWerewolfAction').disabled = true;

            Utils.toast(`You chose to attack ${target}`, 'success');
        } catch (error) {
            Utils.toast(error.message || 'Werewolf action failed', 'error');
        }
    },

    /**
     * Handle cupid action
     */
    async doCupidAction() {
        const lover1 = document.getElementById('cupidLover1').value;
        const lover2 = document.getElementById('cupidLover2').value;

        if (!lover1 || !lover2) {
            Utils.toast('Select both lovers', 'warning');
            return;
        }

        if (lover1 === lover2) {
            Utils.toast('Lovers must be different players', 'warning');
            return;
        }

        try {
            await SocketManager.cupidAction(lover1, lover2);
            this.cupidUsed = true;

            // Disable cupid controls
            document.getElementById('cupidLover1').disabled = true;
            document.getElementById('cupidLover2').disabled = true;
            document.getElementById('btnCupidAction').disabled = true;

            Utils.toast(`${lover1} and ${lover2} are now lovers!`, 'success');
        } catch (error) {
            Utils.toast(error.message || 'Cupid action failed', 'error');
        }
    },

    /**
     * End the player's turn
     */
    async endTurn() {
        const btnEnd = document.getElementById('btnEndTurn');
        btnEnd.disabled = true;
        try {
            const response = await SocketManager.endTurn();
            console.log('[DEBUG] endTurn response:', response);

            // Check if phase changed in the response
            if (response && response.phase) {
                console.log('[DEBUG] Phase changed in response:', response.phase);
                GameState.phase = response.phase;
                GameState.turn = response.turn;
                GameState.deaths = response.deaths_this_round || [];

                if (response.phase === 'day') {
                    console.log('[DEBUG] Transitioning to day phase from endTurn response');
                    Utils.playSound('soundTurn');
                    DayPhase.show(response.deaths_this_round || []);
                    return;
                }
            }

            // No phase change, just waiting
            this.showWaiting('Waiting for other players...');
        } catch (error) {
            Utils.toast(error.message || 'Failed to end turn', 'error');
        } finally {
            btnEnd.disabled = false;
        }
    },

    /**
     * Setup night phase event listeners
     */
    setupEventListeners() {
        document.getElementById('btnSeerAction').addEventListener('click', () => {
            this.doSeerAction();
        });

        document.getElementById('btnWerewolfAction').addEventListener('click', () => {
            this.doWerewolfAction();
        });

        document.getElementById('btnCupidAction').addEventListener('click', () => {
            this.doCupidAction();
        });

        document.getElementById('btnEndTurn').addEventListener('click', () => {
            this.endTurn();
        });
    }
};

// Expose globally
window.NightPhase = NightPhase;
