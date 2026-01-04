# Pizza Index Tracker Bot

An automated betting bot that monitors the **Pizza Index** OSINT indicator and places bets on Polymarket prediction markets.

## Overview

The Pizza Index is an informal indicator based on surges in pizza orders near key US government sites (e.g., the Pentagon). This bot:

1. **Monitors** pizza popularity data via [PizzINT.watch](https://www.pizzint.watch)
2. **Detects** anomalous surges that may indicate imminent government/military action
3. **Tracks** high-win-rate traders on Polymarket for confirmation
4. **Places** automated bets with built-in risk management

## Status

- **Phase 1**: Project Setup & Configuration - COMPLETE
- **Phase 2**: Monitoring Module - IN PROGRESS
- **Phase 3**: Analysis Module - PENDING
- **Phase 4**: Decision Engine - PENDING
- **Phase 5**: Execution Module - PENDING
- **Phase 6**: Storage & Logging - PENDING
- **Phase 7**: Notifications - PENDING
- **Phase 8**: Docker Deployment - PENDING

## Installation

### Prerequisites

- Python 3.12+
- Docker (optional, for containerized deployment)

### Local Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd pizza-index-better
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment template:
```bash
cp .env.example .env
```

4. Edit `.env` with your configuration:
```env
SIMULATION_MODE=true
POLL_INTERVAL_MINUTES=5
STRATEGY=hybrid
```

5. Run the bot:
```bash
python -m app.main
```

### Docker Setup

```bash
# Build and run
cd docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Configuration

Configuration is managed via environment variables (see `.env.example`) or `config/settings.yaml`.

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `SIMULATION_MODE` | `true` | Run in paper trading mode |
| `STRATEGY` | `hybrid` | aggressive, conservative, or hybrid |
| `POLL_INTERVAL_MINUTES` | `5` | How often to check for signals |
| `MAX_BET_SIZE_USD` | `100.0` | Maximum single bet size |
| `CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence to act |

## Project Structure

```
pizza-index-better/
├── app/                    # Application code
│   ├── config.py           # Configuration management
│   ├── main.py             # Entry point
│   ├── monitoring/         # Pizza Index monitoring
│   ├── analysis/           # Trader tracking & analysis
│   ├── decision/           # Trading decisions
│   ├── execution/          # Order execution
│   ├── storage/            # Database layer
│   └── notifications/      # Alerts & notifications
├── config/                 # Configuration files
├── docker/                 # Docker deployment
├── docs/                   # Implementation documentation
├── data/                   # Runtime data (gitignored)
├── logs/                   # Application logs (gitignored)
└── tests/                  # Test suite
```

## Documentation

Detailed implementation documentation is available in the `docs/` folder:

- **[PHASES_SUMMARY.md](docs/PHASES_SUMMARY.md)** - Quick reference for all phases
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** - Detailed implementation guide

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Project Setup & Configuration | ✅ Complete |
| 2 | Monitoring Module | 📋 TODO |
| 3 | Analysis Module | 📋 TODO |
| 4 | Decision Engine & Risk Management | 📋 TODO |
| 5 | Execution Module | 📋 TODO |
| 6 | Storage & Logging | 📋 TODO |
| 7 | Notifications & Scheduling | 📋 TODO |
| 8 | Docker Deployment | 📋 TODO |

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black app/
ruff check app/
```

## Safety

- **Always start in simulation mode** before live trading
- Never commit private keys or wallet addresses
- The Pizza Index has a ~30% false positive rate
- Use position sizing and stop losses to manage risk

## License

MIT

## Disclaimer

This bot is for educational and informational purposes only. Trading prediction markets involves significant risk. Past performance of the Pizza Index does not guarantee future results.