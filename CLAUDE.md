# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil Breakout Trading Bot (윌리엄 오닐 돌파매매 봇) — a signal notifier for **Korean stocks only** that detects breakout patterns (CAN SLIM style), sends Telegram alerts, and tracks "virtual" positions with stop-loss / take-profit / max-holding-days exits. It does not place real orders.

**Stack:** Python 3.12+, pykrx (KRX market data), Telegram Bot API (raw `requests`), JSON files or PostgreSQL over an SSH tunnel. Code comments, log output, and Telegram messages are in Korean — keep new user-facing strings in Korean.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # set TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

python -m kr_oneil_simple                 # main bot loop (same as `run`)
python -m kr_oneil_simple scan            # one-off scan (still sends Telegram alerts and writes positions)
python -m kr_oneil_simple backtest --start 2024-01-01 --end 2024-12-31 --capital 100000000

# Diagnostics for "why didn't a signal fire?" (run from repo root, see scripts/README.md)
python scripts/check_realtime_data.py      # does pykrx return today's bar intraday?
python scripts/check_signal_conditions.py  # per-ticker pass/fail of each pivot condition right now
python scripts/check_backtest_signals.py   # dates in the last 3 weeks where signals should have fired

black src/ && ruff check src/ && mypy src/
```

**Tests:** there is no `tests/` directory yet. `pyproject.toml` sets `testpaths = ["tests"]` and `--cov=oneil_breakout` (an old package name; the real package is `kr_oneil_simple`). Fix the `--cov` target when you add tests. To run a single test: `pytest tests/test_x.py::test_name`.

## Architecture

`BreakoutDetector` (`bot/detector.py`) is the orchestrator: it owns the `TelegramClient`, `WatchlistManager`, `PositionManager`, and the scan loop.

### Scan flow (`_scan_stocks`)

For each watchlist ticker:
1. Skip if a position is already open (`has_position`).
2. Skip if a signal was already recorded today (`has_signal_today`). This prevents duplicate alerts.
3. `analyze_stock()` → pattern detection on ~`ANALYSIS_PERIOD_DAYS` of pykrx OHLCV.
4. On a signal: `record_signal()` **first**, then `positions.add()`. Only if the add succeeds: `mark_position_opened()` and send the Telegram alert.

Keep this ordering when changing the flow. Recent fixes (duplicate notifications, `position_opened` tracking) depend on it.

### Pattern detection: live bot vs. backtest differ

- The **live bot uses only the pivot breakout** (`patterns/pivot.detect_pivot_breakout`). `patterns/cup_handle.py` and `patterns/base.py` are exported but **not used by the bot**.
- `BacktestEngine` runs cup, pivot, and base. Pivot is shared through `detect_pivot_breakout_at_index`. Cup-and-handle and base breakout are **separate inline copies inside `backtest/engine.py` with hard-coded thresholds**, so they ignore `PatternSettings` / `.env`. Pattern tuning has to be applied in both places, or the copies need to be unified.
- The backtest CLI uses only the first 20 watchlist tickers from settings (not `watchlist.json`) and writes CSVs to `output/` at the repo root.

### Storage: `PositionManager` facade

`positions/manager.py` defines `BasePositionManager` (ABC holding the exit-condition math) with two implementations, `JsonPositionManager` (`positions.json` + `signals.json` in the CWD) and `DatabasePositionManager` (`database/connection.py`, psycopg2 over `sshtunnel`). `PositionManager` picks one based on `USE_DATABASE` and delegates every call to it. A new position operation has to be added to the ABC, both implementations, and the facade.

When serializing signal dicts to JSON/DB, cast numpy scalars (`int64`/`float64`) to Python types first. This has caused bugs before.

### Watchlist

`WatchlistManager` loads `watchlist.json` when it exists. In that case `KR_WATCH_LIST` from `.env` is only the initial default and gets ignored. `/add` and `/remove` edit the JSON file.

### Threading

- Main thread: `run()` → `run_smart_scan()` every `SCAN_INTERVAL` seconds. Outside market hours it only runs `check_positions()`.
- Daemon thread: Telegram long-polling (`start_command_listener`, 2s loop) → `process_command()`.
- `/scan` makes `process_command` return the sentinel `'SCAN_KR'`, and the listener then starts a daemon thread running `_execute_scan_in_thread()`, guarded by `scan_lock` + `is_scanning`. The scheduled scan only checks `is_scanning` and skips its cycle when a manual scan is running.

### Market hours

`market/status.get_market_status()` treats **08:00–17:00 on weekdays, using the host's local clock** (`datetime.now()`, no timezone) as "open". User-facing messages say 09:00–15:30. The host must run in KST, and Korean public holidays are not handled.

## Adding features

- **Telegram command:** add a branch in `BreakoutDetector.process_command()` and update `_get_help_message()`.
- **Live pattern:** add `detect_*()` in `patterns/`, call it from `BreakoutDetector.analyze_stock()`. The returned signal dict needs at least `current_price` and `pattern`.
- **Config option:** add a field to the relevant dataclass in `config/settings.py`, read it in `load_settings()` via `_get_env_float/_int/_list`, and document it in `.env.example`.
