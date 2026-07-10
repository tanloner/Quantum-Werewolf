/**
 * Quantum Werewolf - Probability Bar Component
 */

const ProbabilityBar = {
    /**
     * Create a probability bar element
     */
    create(role, probability) {
        const percent = Math.round(probability * 100);
        const roleClass = Utils.getRoleClass(role);

        return `
            <div class="prob-bar">
                <div class="label-row">
                    <span class="role-name ${roleClass}">${role}</span>
                    <span class="percentage">${percent}%</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill ${roleClass}" style="width: ${percent}%"></div>
                </div>
            </div>
        `;
    },

    /**
     * Create all probability bars for a player
     */
    createAll(probabilities) {
        // Sort by probability (highest first)
        const sorted = Object.entries(probabilities)
            .filter(([_, prob]) => prob > 0)
            .sort((a, b) => b[1] - a[1]);

        return sorted.map(([role, prob]) => this.create(role, prob)).join('');
    },

    /**
     * Create a mini bar for the stats table
     */
    createMini(role, probability) {
        const percent = Math.round(probability * 100);
        const roleClass = Utils.getRoleClass(role);

        return `
            <span class="mini-bar">
                <span class="mini-bar-fill ${roleClass}" style="width: ${percent}%"></span>
            </span>
        `;
    }
};

// Expose globally
window.ProbabilityBar = ProbabilityBar;
