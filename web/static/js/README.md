# Quantum Werewolf Frontend

Vanilla JavaScript single-page application for the Quantum Werewolf game.

## Architecture Overview

```
js/
├── app.js           # Main application controller
├── socket.js        # WebSocket connection manager
├── utils.js         # Utilities and global state
└── components/
    ├── lobby.js         # Game lobby & deck configuration
    ├── night-phase.js   # Night turn interface
    ├── day-phase.js     # Day phase & stats table
    ├── voting.js        # Voting interface
    ├── gm-dashboard.js  # Game Master controls
    └── probability-bar.js # Reusable probability bar component
```

## Module Documentation

### utils.js

Global utilities and state management.

**`Utils` Object:**

| Method | Description |
|--------|-------------|
| `toast(message, type)` | Show toast notification (info/success/error/warning) |
| `showLoading()` | Display loading overlay |
| `hideLoading()` | Hide loading overlay |
| `showView(viewId)` | Switch to a view by ID |
| `api(endpoint, options)` | Make authenticated API request |
| `formatPercent(value)` | Format 0-1 as "XX%" |
| `getRoleClass(role)` | Get CSS class for role |
| `copyToClipboard(text)` | Copy text to clipboard |
| `playSound(soundId)` | Play sound if enabled |
| `store(key, value)` | Save to localStorage |
| `retrieve(key)` | Load from localStorage |
| `getGameIdFromUrl()` | Extract game ID from URL path |
| `getViewFromUrl()` | Get view type from URL path |

**`GameState` Object:**

Global game state container:

```javascript
GameState = {
    gameId: null,        // Current game ID
    playerToken: null,   // Player authentication token
    gmToken: null,       // GM token (if host)
    playerName: null,    // Current player's name
    isGM: false,         // Whether current player is GM
    soundEnabled: true,  // Sound preference
    phase: 'lobby',      // Current game phase
    turn: 0,             // Current turn number
    players: [],         // All player names
    livingPlayers: [],   // Living player names
    myNumber: null,      // Player's anonymous number
    stats: [],           // Anonymous stats array
    currentVote: null,   // Current vote target
    voteConfirmed: false,// Whether vote is confirmed
    deck: {...}          // Deck configuration
}
```

**State Persistence:**
- `saveSession()` - Save to localStorage
- `loadSession()` - Load from localStorage
- `clearSession()` - Clear saved session
- `reset()` - Reset to defaults

### socket.js

Socket.IO connection management.

**`SocketManager` Object:**

| Method | Description |
|--------|-------------|
| `connect(gameId, token)` | Connect to game server |
| `disconnect()` | Disconnect from server |
| `emit(event, data)` | Emit event, returns Promise |

**Player Action Methods:**
```javascript
await SocketManager.seerAction(target)
await SocketManager.werewolfAction(target)
await SocketManager.cupidAction(lover1, lover2)
await SocketManager.endTurn()
await SocketManager.vote(target)  // null for abstain
await SocketManager.confirmVote()
await SocketManager.requestStats()
```

**GM Action Methods:**
```javascript
await SocketManager.gmSkipTurn()
await SocketManager.gmStartVoting()
await SocketManager.gmEndVoting()
await SocketManager.gmStartNight()
```

**Event Handlers:**

The socket manager automatically handles server events:
- `game_state` → Restore full game state
- `player_joined` → Update player list
- `game_started` → Switch to night view
- `your_turn` → Show turn interface
- `turn_ended` → Show waiting screen
- `phase_change` → Switch views, show deaths
- `stats_update` → Update stats table
- `voting_started` → Show voting interface
- `voting_ended` → Show results
- `game_over` → Show game over screen
- `gm_state` → Update GM dashboard

### app.js

Main application controller.

**`App` Object:**

| Method | Description |
|--------|-------------|
| `init()` | Initialize application |
| `handleUrlRouting()` | Route based on URL path |
| `tryReconnect(gameId)` | Attempt to reconnect to game |
| `tryReconnectGM(gameId)` | Attempt GM reconnection |
| `createGame(hostName)` | Create new game |
| `joinGame(gameCode, playerName)` | Join existing game |
| `toggleSound()` | Toggle sound on/off |
| `newGame()` | Start fresh (from game over) |

**URL Routing:**
- `/` → Home view
- `/join/{gameId}` → Join form with pre-filled code
- `/game/{gameId}` → Player game view (attempts reconnect)
- `/gm/{gameId}` → GM dashboard (attempts reconnect)

### components/lobby.js

Game lobby component.

**`Lobby` Object:**

| Method | Description |
|--------|-------------|
| `init()` | Initialize lobby display |
| `updatePlayerList()` | Refresh player list |
| `updateDeckDisplay()` | Update deck counter display |
| `changeDeckRole(role, delta)` | Modify deck configuration |
| `startGame()` | Start game (GM only) |
| `setupEventListeners()` | Bind event handlers |

**Features:**
- Display game code with copy button
- Show player list
- Deck configuration (GM only)
- Start game button (GM only)
- "Waiting for host" message (non-GM)

### components/night-phase.js

Night phase component.

**`NightPhase` Object:**

| Method | Description |
|--------|-------------|
| `showWaiting(message)` | Show "village sleeping" screen |
| `showYourTurn(data)` | Show player's turn interface |
| `updateRoleProbabilities(probs)` | Display role probability bars |
| `updateWerewolfInfo(wolves)` | Show fellow werewolf info |
| `updateActionPanels(actions, isFirst)` | Show available action panels |
| `populatePlayerSelects()` | Fill player dropdowns |
| `doSeerAction()` | Execute seer action |
| `doWerewolfAction()` | Execute werewolf action |
| `doCupidAction()` | Execute cupid action |
| `endTurn()` | End player's turn |
| `setupEventListeners()` | Bind event handlers |

**Turn Data Structure:**
```javascript
{
    your_probabilities: {werewolf: 0.5, seer: 0.25, villager: 0.25},
    your_number: 3,
    other_werewolves: [{name: "Bob", probability: 0.7}],
    available_actions: ["seer", "werewolf"],
    lover_info: {eligible_players: ["Alice", "Craig"]},
    is_first_night: false
}
```

### components/day-phase.js

Day phase component.

**`DayPhase` Object:**

| Method | Description |
|--------|-------------|
| `show(deaths)` | Show day phase with death announcements |
| `showDeaths(deaths)` | Display death announcements |
| `updateStatsTable()` | Render anonymous stats table |
| `refreshStats()` | Request fresh stats from server |
| `startVoting()` | GM: Start voting phase |
| `startNight()` | GM: Start next night |
| `setupEventListeners()` | Bind event handlers |

**Stats Table:**
- Anonymous player numbers
- Role probability mini-bars
- Death probability column
- Dead players show revealed name/role
- Current player's row highlighted
- GM controls for phase transitions

### components/voting.js

Voting phase component.

**`Voting` Object:**

| Method | Description |
|--------|-------------|
| `show()` | Initialize voting interface |
| `selectVote(player)` | Select vote target |
| `submitVote()` | Send vote to server |
| `abstain()` | Vote for no one |
| `confirmVote()` | Lock in vote |
| `updateProgress(data)` | Update vote/confirm counts |
| `showResults(data)` | Display voting results |
| `continueAfterVote()` | Return to day phase |
| `endVoting()` | GM: End voting early |
| `setupEventListeners()` | Bind event handlers |

**Vote Flow:**
1. Select target (or abstain)
2. Click confirm
3. Wait for all players or GM ends
4. View results
5. Continue to day phase

### components/gm-dashboard.js

Game Master dashboard component.

**`GMDashboard` Object:**

| Method | Description |
|--------|-------------|
| `init()` | Initialize GM dashboard |
| `update(data)` | Update all dashboard sections |
| `updateTurnOrder(data)` | Show turn progress |
| `updateActionLog(actions)` | Display action history |
| `updateVotes(data)` | Show current votes |
| `updateButtons(phase)` | Enable/disable controls |
| `skipTurn()` | Skip current player |
| `startVoting()` | Begin voting phase |
| `endVoting()` | End voting early |
| `startNight()` | Begin next night |
| `setupEventListeners()` | Bind event handlers |

**GM State:**
```javascript
{
    phase: "night",
    turn: 2,
    current_player: "Alice",
    pending_players: ["Bob", "Craig"],
    completed_players: ["David"],
    actions_log: [{turn: 2, player: "David", action: "seer", target: "Alice", result: "werewolf"}],
    votes: {Alice: "Bob", Bob: null},
    vote_confirmations: ["Alice"]
}
```

### components/probability-bar.js

Reusable probability bar component.

**`ProbabilityBar` Object:**

| Method | Description |
|--------|-------------|
| `create(role, probability)` | Create full probability bar HTML |
| `createAll(probabilities)` | Create bars for all roles |
| `createMini(role, probability)` | Create mini bar for stats table |

## View Structure

Views are defined in `index.html` and switched via `Utils.showView()`:

| View ID | Description |
|---------|-------------|
| `view-home` | Home screen with create/join buttons |
| `view-create` | Create game form |
| `view-join` | Join game form |
| `view-lobby` | Game lobby |
| `view-night` | Night phase (turn or waiting) |
| `view-day` | Day phase with stats |
| `view-voting` | Voting interface |
| `view-vote-results` | Voting results |
| `view-gameover` | Game over screen |
| `view-gm` | GM dashboard |

## CSS Classes

### Role Colors
- `.werewolf` - Red (#dc2626)
- `.seer` - Green (#10b981)
- `.villager` - Blue (#3b82f6)
- `.hunter` - Orange (#f59e0b)
- `.cupid` - Pink (#ec4899)

### Component Classes
- `.prob-bar` - Full probability bar
- `.mini-bar` - Small inline bar
- `.vote-option` - Voting button
- `.vote-option.selected` - Selected vote
- `.your-row` - Highlighted table row
- `.dead-row` - Dead player row

## Event Flow

### Game Creation
```
btnCreateGame click
→ showView('create')
→ formCreate submit
→ App.createGame(hostName)
→ API POST /api/games
→ GameState update
→ SocketManager.connect()
→ showView('lobby')
```

### Night Turn
```
socket 'your_turn' event
→ NightPhase.showYourTurn(data)
→ User performs actions
→ btnEndTurn click
→ SocketManager.endTurn()
→ socket 'turn_ended' event
→ NightPhase.showWaiting()
```

### Voting
```
socket 'voting_started' event
→ Voting.show()
→ User clicks player button
→ Voting.selectVote(player)
→ btnConfirmVote click
→ SocketManager.vote() + confirmVote()
→ socket 'vote_progress' updates
→ socket 'voting_ended' event
→ Voting.showResults(data)
```

## Local Storage

Keys (prefixed with `qw_`):
- `session` - Game session data for reconnection
- `soundEnabled` - Sound preference

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (responsive design)
- Requires JavaScript enabled
- Requires WebSocket support
