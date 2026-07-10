# Quantum Werewolf Web

A real-time multiplayer web application for playing Quantum Werewolf online.

## Features

- **Real-time multiplayer** via WebSockets
- **Quantum mechanics** - all players exist in superposition of roles
- **Anonymous stats display** - see probabilities without knowing identities
- **Game Master controls** - skip turns, force actions, manage game flow
- **Mobile-friendly** dark theme interface
- **Optional sound notifications**

## Quick Start

### Local Development

1. Install Python dependencies:
```bash
cd server
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

3. Open http://localhost:8000 in your browser

### Playing a Game

1. **Create a game**: One player creates a game and becomes the host/Game Master
2. **Share the code**: Give the 6-letter game code to other players
3. **Join**: Other players join via the game code
4. **Configure deck**: The GM can adjust roles (werewolves, seer, etc.)
5. **Start**: GM starts the game when everyone is ready
6. **Night phase**: Each player takes their turn privately
7. **Day phase**: View anonymous stats and vote
8. **Repeat** until victory!

### Voice Chat

The game is designed for players to communicate via voice chat (Discord, etc.). The website only handles game mechanics and stats.

## Deployment

### Render.com (Recommended)

1. Fork this repository
2. Connect to Render.com
3. Create a new Web Service using the `render.yaml` configuration
4. Deploy!

### Docker

```bash
docker build -t quantum-werewolf .
docker run -p 8000:8000 quantum-werewolf
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `PUBLIC_HOST` | Public hostname for URLs | `localhost:8000` |
| `USE_HTTPS` | Use HTTPS in generated URLs | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

## Game Rules

### Roles

- **Werewolf**: Attack villagers at night. Win when all non-werewolves are dead.
- **Seer**: Observe one player per night to collapse their role superposition.
- **Hunter**: When you die, you may kill another player.
- **Cupid**: On the first night, pair two players as lovers (they win if only they survive).
- **Villager**: No special powers. Win when all werewolves are dead.

### Quantum Mechanics

Unlike traditional Werewolf, players aren't assigned fixed roles. Instead:

1. **Superposition**: Each player exists in all possible role assignments simultaneously
2. **Probability**: You only see probabilities of having each role
3. **Measurement**: Seer observations and deaths collapse the wavefunction
4. **Uncertainty**: Until observed, anything is possible!

### Game Flow

1. **Night**: Each player acts in turn (seer observes, werewolves attack)
2. **Day**: Deaths announced, view anonymous stats table
3. **Voting**: Vote to lynch a player (optional)
4. **Repeat** until win condition met

## Project Structure

```
web/
├── server/
│   ├── main.py              # FastAPI server
│   ├── game_adapter.py      # Wraps backend.Game
│   ├── game_manager.py      # Manages active games
│   ├── models.py            # Pydantic models
│   ├── websocket_manager.py # Socket.IO handlers
│   └── requirements.txt
├── static/
│   ├── index.html           # Single-page app
│   ├── css/style.css        # Dark theme
│   └── js/
│       ├── app.js           # Main application
│       ├── socket.js        # WebSocket client
│       ├── utils.js         # Utilities
│       └── components/      # UI components
├── Dockerfile
├── render.yaml
└── README.md
```

## Tech Stack

- **Backend**: FastAPI + Python-SocketIO
- **Frontend**: Vanilla JavaScript + Socket.IO Client
- **Styling**: Custom CSS with dark theme
- **Game Logic**: `quantumwerewolf/backend.py`

## Contributing

Contributions welcome! Please open an issue first to discuss changes.

## License

Same license as the parent Quantum Werewolf project.
