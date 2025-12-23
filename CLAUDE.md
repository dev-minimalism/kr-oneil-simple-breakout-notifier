# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil Breakout Trading Bot (윌리엄 오닐 돌파매매 봇) - An automated trading signal detection system for **Korean stocks only** that identifies chart breakout patterns (Cup-and-Handle, Pivot Point Breakout, Base Breakout) using the CAN SLIM strategy framework.

**Stack:** Python 3.12+, pykrx (Korean stocks), Telegram Bot API, PostgreSQL (optional)

## Common Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure (copy and edit .env)
cp .env.example .env
# Edit .env with your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID

# Run the main trading bot
python -m kr_oneil_simple

# Run single scan
python -m kr_oneil_simple scan

# Run backtests
python -m kr_oneil_simple backtest --capital 100000000
python -m kr_oneil_simple backtest --start 2024-01-01 --end 2024-12-31

# Dev tools (if installed with pip install -e ".[dev]")
pytest                    # Run tests
black src/                # Format code
ruff check src/           # Lint
mypy src/                 # Type check
```

## Architecture

### Package Structure (`src/kr_oneil_simple/`)

```
src/kr_oneil_simple/
├── __init__.py          # Package exports
├── __main__.py          # CLI entry point
├── bot/detector.py      # BreakoutDetector - main bot class
├── backtest/engine.py   # BacktestEngine - backtesting
├── config/settings.py   # Settings dataclasses + load_settings()
├── data/kr_stock.py     # pykrx wrapper for Korean stocks
├── database/            # PostgreSQL via SSH tunnel (optional)
│   ├── connection.py    # SSH tunnel + psycopg2 connection
│   └── models.py        # Position, Signal, PositionStatus models
├── patterns/
│   ├── pivot.py         # Pivot breakout detection
│   ├── cup_handle.py    # Cup-and-handle pattern
│   └── base.py          # Base breakout pattern
├── positions/manager.py # Position tracking with stop-loss/take-profit
├── watchlist/manager.py # Dynamic watchlist with JSON persistence
├── market/status.py     # Korean market hours check
└── telegram/
    ├── client.py        # Telegram API client
    └── formatter.py     # Message formatting
```

### Core Components

**BreakoutDetector** (`bot/detector.py`): Main bot orchestrating scans, position tracking, and Telegram commands
- `run()`: Main loop with scan interval
- `run_scan()`: On-demand scan
- `process_command()`: Telegram command handler
- `check_positions()`: Periodic P&L check with auto stop-loss/take-profit

**BacktestEngine** (`backtest/engine.py`): Historical strategy testing
- `run_backtest()`: Single ticker backtest
- `run_portfolio_backtest()`: Multi-ticker with position limits
- `calculate_performance()`: Returns win rate, CAGR, pattern stats

**Settings** (`config/settings.py`): Dataclass-based config loaded from `.env` file via python-dotenv

### Data Flow

```
Telegram Commands → BreakoutDetector.process_command()
                         ↓
              Data Retrieval (kr_stock.py via pykrx)
                         ↓
              Pattern Detection (patterns/pivot.py)
                         ↓
         Signal? → Yes → PositionManager.add() + Telegram alert
                   No  → Log & skip
                         ↓
         Periodic check_positions() (stop-loss/take-profit/expiry)
```

### Configuration

Settings are loaded from `.env` file (copy `.env.example` to `.env`).

**Key settings:**
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` - Bot credentials (required)
- `SCAN_INTERVAL` - Scan interval in seconds (default: 1800)
- `KR_WATCH_LIST` - Comma-separated stock codes
- `VOLUME_SURGE_MIN` - Pivot breakout volume threshold (default: 50%)
- `STOP_LOSS_PERCENT` - Stop loss percentage (default: -7.5%)

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/scan` | Trigger market scan |
| `/add [CODE]`, `/remove [CODE]` | Manage watchlist |
| `/list` | Show watchlist |
| `/positions` | Show holdings with P&L |
| `/close [CODE]` | Close position manually |
| `/trades` | Recent trade history (last 15) |
| `/stats` | Trading statistics (win rate, returns) |
| `/status` | Market hours status |
| `/help` | Show all commands |

## Threading Model

- Main thread: Scan loop (interval from `SCAN_INTERVAL`) + position checks
- Background daemon: Telegram polling (2-sec interval via `start_command_listener()`)
- Manual `/scan` commands spawn daemon threads
- `scan_lock` mutex prevents concurrent scans

## Adding New Features

- **Telegram command:** Add case to `BreakoutDetector.process_command()` in `bot/detector.py`
- **New pattern:** Create `detect_*()` in `patterns/`, integrate in `BreakoutDetector.analyze_stock()`
- **Config option:** Add to `Settings` dataclass in `config/settings.py`, load in `load_settings()`
- **Backtest pattern:** Add detection method to `BacktestEngine`, call in `run_backtest()`

## Storage

Positions and signals can be stored in either:
- **JSON files** (default): `positions.json`, `watchlist.json` in working directory
- **PostgreSQL** (optional): Set `USE_DATABASE=true` in `.env`, requires SSH tunnel config for remote DB