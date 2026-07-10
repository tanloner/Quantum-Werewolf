/**
 * Quantum Werewolf - Utility Functions
 */

const Utils = {
    /**
     * Show a toast notification
     */
    toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    /**
     * Show loading overlay
     */
    showLoading() {
        document.getElementById('loadingOverlay').classList.remove('hidden');
    },

    /**
     * Hide loading overlay
     */
    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    },

    /**
     * Switch to a view
     */
    showView(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const view = document.getElementById(`view-${viewId}`);
        if (view) {
            view.classList.add('active');
        }
    },

    /**
     * API request helper
     * @param {string} endpoint - API endpoint
     * @param {object} options - fetch options
     * @param {boolean} options.useGmToken - force use of GM token for this request
     */
    async api(endpoint, options = {}) {
        // For GM actions, prefer GM token; otherwise use player token
        const useGmToken = options.useGmToken || false;
        delete options.useGmToken;

        let token;
        if (useGmToken && GameState.gmToken) {
            token = GameState.gmToken;
        } else if (GameState.isGM && GameState.gmToken) {
            // If user is GM, prefer GM token for authenticated requests
            token = GameState.gmToken;
        } else {
            token = GameState.playerToken;
        }

        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };

        try {
            const response = await fetch(`/api${endpoint}`, {
                ...options,
                headers: { ...headers, ...options.headers }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    /**
     * Format percentage
     */
    formatPercent(value) {
        return `${Math.round(value * 100)}%`;
    },

    /**
     * Get role color class
     */
    getRoleClass(role) {
        const roleMap = {
            werewolf: 'werewolf',
            seer: 'seer',
            villager: 'villager',
            hunter: 'hunter',
            cupid: 'cupid'
        };
        return roleMap[role] || '';
    },

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            // Try modern clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                this.toast('Copied to clipboard!', 'success');
                return;
            }

            // Fallback for older browsers or non-HTTPS
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);

            if (successful) {
                this.toast('Copied to clipboard!', 'success');
            } else {
                // Show the text for manual copying
                this.toast(`Copy this: ${text}`, 'info');
            }
        } catch (err) {
            console.error('Copy failed:', err);
            // Show the text for manual copying
            this.toast(`Copy this: ${text}`, 'info');
        }
    },

    /**
     * Play sound if enabled
     */
    playSound(soundId) {
        if (!GameState.soundEnabled) return;

        const audio = document.getElementById(soundId);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => {});
        }
    },

    /**
     * Store data in localStorage
     */
    store(key, value) {
        try {
            localStorage.setItem(`qw_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('localStorage not available');
        }
    },

    /**
     * Retrieve data from localStorage
     */
    retrieve(key) {
        try {
            const value = localStorage.getItem(`qw_${key}`);
            return value ? JSON.parse(value) : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * Parse URL path to get game ID
     */
    getGameIdFromUrl() {
        const path = window.location.pathname;
        const match = path.match(/\/(join|game|gm)\/([A-Z0-9]{6})/i);
        return match ? match[2].toUpperCase() : null;
    },

    /**
     * Get view type from URL
     */
    getViewFromUrl() {
        const path = window.location.pathname;
        if (path.startsWith('/join/')) return 'join';
        if (path.startsWith('/game/')) return 'game';
        if (path.startsWith('/gm/')) return 'gm';
        return 'home';
    }
};

/**
 * Global game state
 */
const GameState = {
    gameId: null,
    playerToken: null,
    gmToken: null,
    playerName: null,
    isGM: false,
    soundEnabled: true,
    phase: 'lobby',
    turn: 0,
    players: [],
    livingPlayers: [],
    myNumber: null,
    stats: [],
    currentVote: null,
    voteConfirmed: false,
    deck: {
        werewolf: 2,
        seer: 1,
        hunter: 0,
        cupid: 0
    },

    /**
     * Reset state for new game
     */
    reset() {
        this.gameId = null;
        this.playerToken = null;
        this.gmToken = null;
        this.playerName = null;
        this.isGM = false;
        this.phase = 'lobby';
        this.turn = 0;
        this.players = [];
        this.livingPlayers = [];
        this.myNumber = null;
        this.stats = [];
        this.currentVote = null;
        this.voteConfirmed = false;
    },

    /**
     * Save current session to localStorage
     */
    saveSession() {
        Utils.store('session', {
            gameId: this.gameId,
            playerToken: this.playerToken,
            gmToken: this.gmToken,
            playerName: this.playerName,
            isGM: this.isGM
        });
    },

    /**
     * Load session from localStorage
     */
    loadSession() {
        const session = Utils.retrieve('session');
        if (session) {
            this.gameId = session.gameId;
            this.playerToken = session.playerToken;
            this.gmToken = session.gmToken;
            this.playerName = session.playerName;
            this.isGM = session.isGM;
            return true;
        }
        return false;
    },

    /**
     * Clear saved session
     */
    clearSession() {
        Utils.store('session', null);
    }
};

// Expose globally
window.Utils = Utils;
window.GameState = GameState;
