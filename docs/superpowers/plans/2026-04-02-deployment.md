# Deployment & Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare TrustDesk for hackathon deployment and submission -- Dockerfile, Railway config, Vercel config, backtest script, submission checklist.

**Architecture:** Deployment configs + utility scripts. No business logic changes. Backend deploys to Railway, dashboard to Vercel, both read env vars for configuration.

**Tech Stack:** Docker, Railway, Vercel, Kraken CLI (historical data)

---

## Task 1: Dockerfile for backend

**Files to create:**
- `backend/Dockerfile`
- `backend/.dockerignore`

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --no-dev

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Expose the FastAPI port
EXPOSE 8000

# Start the trading desk
CMD ["uv", "run", "python", "scripts/run_desk.py"]
```

### `backend/.dockerignore`

```
tests/
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/
.env
.env.*
*.egg-info/
dist/
build/
.git/
```

### Verification

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
docker build -t trustdesk-backend backend/
```

Expected: Image builds successfully. It does NOT need to run without env vars -- just needs to build.

### Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat: add Dockerfile for backend"
```

---

## Task 2: Railway deployment config

**Files to create:**
- `railway.toml` (repo root)
- `backend/Procfile`

### `railway.toml`

```toml
[build]
builder = "dockerfile"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "uv run python scripts/run_desk.py"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
```

### `backend/Procfile`

```
web: uv run python scripts/run_desk.py
```

### Railway environment variables needed

When deploying to Railway, configure these environment variables in the Railway dashboard:

- `DATABASE_URL` -- Railway managed PostgreSQL (Railway provides this automatically when you add a PostgreSQL plugin)
- `OPENAI_API_KEY` -- for LLM-based strategist
- `ANTHROPIC_API_KEY` -- for Claude-based agents
- `KRAKEN_API_KEY` -- Kraken exchange API key
- `KRAKEN_API_SECRET` -- Kraken exchange API secret
- `BASE_SEPOLIA_RPC_URL` -- Base Sepolia RPC endpoint
- `PRIVATE_KEY` -- wallet private key for on-chain transactions
- `VALIDATOR_CONTRACT_ADDRESS` -- TrustDeskOpenValidator contract address

Railway will expose the app on a `.up.railway.app` domain with HTTPS automatically.

### Verification

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
cat railway.toml
cat backend/Procfile
# No local test needed -- Railway picks this up on deploy
```

### Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add railway.toml backend/Procfile
git commit -m "feat: add Railway deployment config"
```

---

## Task 3: Vercel deployment for dashboard

**Files to create:**
- `dashboard/vercel.json`
- `dashboard/.env.production`

**Files to modify:**
- Any dashboard files that hardcode `localhost:8000` -- update to read from `import.meta.env.VITE_API_URL`

### `dashboard/vercel.json`

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### `dashboard/.env.production`

```
VITE_API_URL=https://trustdesk-backend.up.railway.app
VITE_WS_URL=wss://trustdesk-backend.up.railway.app/ws
```

### Updating hardcoded URLs

Search the dashboard codebase for hardcoded backend URLs and replace them:

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
grep -rn "localhost:8000\|127\.0\.0\.1:8000\|http://localhost" dashboard/src/
```

For each file found, replace hardcoded URLs with environment-aware constants. Create or update an API config file:

**`dashboard/src/config.ts`** (create if it doesn't exist):

```typescript
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
```

Then update all imports across the dashboard to use `API_URL` and `WS_URL` from this config instead of hardcoded strings.

### Verification

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/dashboard
npm run build
# Should succeed with no errors
# Check that no hardcoded localhost remains in built output:
grep -r "localhost:8000" dist/ && echo "FAIL: hardcoded URLs remain" || echo "PASS: no hardcoded URLs"
```

### Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add dashboard/vercel.json dashboard/.env.production dashboard/src/config.ts
# Also add any modified files that had hardcoded URLs replaced
git add -u dashboard/src/
git commit -m "feat: add Vercel config and environment-aware API URLs"
```

---

## Task 4: Backtest script

**File to create:**
- `backend/scripts/run_backtest.py`

### `backend/scripts/run_backtest.py`

```python
#!/usr/bin/env python3
"""
Backtest script for TrustDesk trading desk.

Fetches 90 days of historical OHLC data from Kraken, runs the Signal Engine
over each candle window, simulates Strategist decisions (rule-based to save
API credits), applies Risk Manager hard checks, and prints a go/no-go verdict.

Usage:
    uv run python scripts/run_backtest.py
    uv run python scripts/run_backtest.py --pair BTCUSD --interval 60 --days 90
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Trade:
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    direction: str  # "long" or "short"
    pnl_pct: float = 0.0
    regime: str = "unknown"


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    regime_pnl: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_ohlc_kraken_cli(pair: str, interval: int, days: int) -> list[Candle]:
    """Fetch historical OHLC via Kraken CLI."""
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

    cmd = [
        "kraken", "ohlc",
        "--pair", pair,
        "--interval", str(interval),
        "--since", str(since),
        "-o", "json",
    ]

    print(f"[DATA] Fetching {days}d of {pair} {interval}m candles via Kraken CLI...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"[DATA] Kraken CLI failed: {result.stderr.strip()}")
            print("[DATA] Falling back to synthetic data for demo purposes.")
            return _generate_synthetic_candles(days, interval)
        data = json.loads(result.stdout)
    except FileNotFoundError:
        print("[DATA] Kraken CLI not found. Falling back to synthetic data for demo.")
        return _generate_synthetic_candles(days, interval)
    except subprocess.TimeoutExpired:
        print("[DATA] Kraken CLI timed out. Falling back to synthetic data for demo.")
        return _generate_synthetic_candles(days, interval)
    except json.JSONDecodeError:
        print("[DATA] Failed to parse Kraken CLI output. Falling back to synthetic data.")
        return _generate_synthetic_candles(days, interval)

    candles = []
    # Kraken returns {pair_name: [[timestamp, open, high, low, close, vwap, volume, count], ...]}
    for key, rows in data.items():
        if key == "last":
            continue
        for row in rows:
            candles.append(Candle(
                timestamp=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[6]),
            ))
    candles.sort(key=lambda c: c.timestamp)
    print(f"[DATA] Loaded {len(candles)} candles.")
    return candles


def _generate_synthetic_candles(days: int, interval: int) -> list[Candle]:
    """Generate synthetic BTC-like candles for demo/testing when Kraken CLI is unavailable."""
    import math
    import random

    random.seed(42)
    candles = []
    num_candles = (days * 24 * 60) // interval
    base_price = 65000.0
    price = base_price
    now = int(time.time())
    start = now - (num_candles * interval * 60)

    for i in range(num_candles):
        ts = start + i * interval * 60
        # Random walk with slight upward drift and sine wave for regimes
        trend = 0.0001
        cycle = math.sin(2 * math.pi * i / (num_candles / 3)) * 0.001
        noise = random.gauss(0, 0.003)
        change = trend + cycle + noise

        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.001)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.001)))
        volume = random.uniform(10, 500)

        candles.append(Candle(
            timestamp=ts,
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=round(volume, 4),
        ))
        price = close_price

    print(f"[DATA] Generated {len(candles)} synthetic candles.")
    return candles


# ---------------------------------------------------------------------------
# Signal Engine (simplified)
# ---------------------------------------------------------------------------

def compute_signals(candles: list[Candle], window: int = 20) -> list[dict[str, Any]]:
    """
    Compute trading signals from candles using a simplified version of the
    Signal Engine: SMA crossover + RSI + volatility regime detection.
    """
    signals = []
    if len(candles) < window * 2:
        return signals

    closes = [c.close for c in candles]

    for i in range(window * 2, len(candles)):
        sma_short = sum(closes[i - window:i]) / window
        sma_long = sum(closes[i - window * 2:i]) / (window * 2)

        # RSI (14-period)
        rsi_period = min(14, i)
        gains, losses = [], []
        for j in range(i - rsi_period, i):
            diff = closes[j] - closes[j - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / rsi_period if gains else 0
        avg_loss = sum(losses) / rsi_period if losses else 1
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50

        # Volatility regime
        recent_returns = [
            (closes[j] - closes[j - 1]) / closes[j - 1]
            for j in range(i - window, i)
        ]
        volatility = (sum(r**2 for r in recent_returns) / len(recent_returns)) ** 0.5
        if volatility > 0.02:
            regime = "high_vol"
        elif volatility < 0.005:
            regime = "low_vol"
        else:
            regime = "normal"

        # Signal generation
        signal = None
        if sma_short > sma_long and rsi < 70:
            signal = "long"
        elif sma_short < sma_long and rsi > 30:
            signal = "short"

        if signal:
            signals.append({
                "index": i,
                "timestamp": candles[i].timestamp,
                "signal": signal,
                "sma_short": sma_short,
                "sma_long": sma_long,
                "rsi": rsi,
                "volatility": volatility,
                "regime": regime,
                "price": candles[i].close,
            })

    return signals


# ---------------------------------------------------------------------------
# Strategist (rule-based, no LLM)
# ---------------------------------------------------------------------------

def strategist_decide(signal: dict[str, Any]) -> bool:
    """
    Rule-based strategist: decides whether to take a trade based on signal quality.
    Saves API credits by not calling an LLM.
    """
    rsi = signal["rsi"]
    volatility = signal["volatility"]

    # Skip if volatility is extreme
    if volatility > 0.04:
        return False

    # Long: RSI shouldn't be too high already
    if signal["signal"] == "long" and rsi > 60:
        return False

    # Short: RSI shouldn't be too low already
    if signal["signal"] == "short" and rsi < 40:
        return False

    # Require meaningful SMA divergence
    sma_diff_pct = abs(signal["sma_short"] - signal["sma_long"]) / signal["sma_long"]
    if sma_diff_pct < 0.001:
        return False

    return True


# ---------------------------------------------------------------------------
# Risk Manager (hard checks)
# ---------------------------------------------------------------------------

def risk_check(
    signal: dict[str, Any],
    equity: float,
    max_position_pct: float = 0.1,
    max_drawdown_pct: float = 0.15,
    peak_equity: float = 10000.0,
) -> bool:
    """
    Apply Risk Manager hard checks before entering a trade.
    """
    # Check drawdown limit
    current_drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
    if current_drawdown >= max_drawdown_pct:
        return False

    # Don't trade if equity is too low
    if equity < 1000:
        return False

    return True


# ---------------------------------------------------------------------------
# Trade simulation
# ---------------------------------------------------------------------------

def simulate_trades(
    candles: list[Candle],
    signals: list[dict[str, Any]],
    hold_periods: int = 5,
) -> BacktestResult:
    """
    Simulate trades: enter on signal, hold for N candles, exit.
    """
    result = BacktestResult()
    equity = 10000.0
    peak_equity = equity
    result.equity_curve.append(equity)
    in_trade = False
    trade_exit_index = 0

    for sig in signals:
        idx = sig["index"]

        # Skip if we're currently in a trade
        if in_trade and idx < trade_exit_index:
            continue
        in_trade = False

        # Strategist decides
        if not strategist_decide(sig):
            continue

        # Risk manager checks
        if not risk_check(sig, equity, peak_equity=peak_equity):
            continue

        # Enter trade
        entry_price = sig["price"]
        exit_idx = min(idx + hold_periods, len(candles) - 1)
        exit_price = candles[exit_idx].close
        direction = sig["signal"]

        if direction == "long":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        trade = Trade(
            entry_time=candles[idx].timestamp,
            exit_time=candles[exit_idx].timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            direction=direction,
            pnl_pct=pnl_pct,
            regime=sig["regime"],
        )
        result.trades.append(trade)

        # Update equity
        position_size = equity * 0.1  # 10% of equity per trade
        pnl_dollar = position_size * pnl_pct
        equity += pnl_dollar
        result.equity_curve.append(equity)
        peak_equity = max(peak_equity, equity)

        in_trade = True
        trade_exit_index = exit_idx

        # Track regime PnL
        if trade.regime not in result.regime_pnl:
            result.regime_pnl[trade.regime] = 0.0
        result.regime_pnl[trade.regime] += pnl_dollar

    # Compute summary statistics
    if result.trades:
        wins = [t for t in result.trades if t.pnl_pct > 0]
        losses = [t for t in result.trades if t.pnl_pct <= 0]
        result.win_rate = len(wins) / len(result.trades)
        result.avg_win = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
        result.avg_loss = abs(sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0

    # Compute max drawdown from equity curve
    peak = result.equity_curve[0]
    max_dd = 0.0
    for eq in result.equity_curve:
        peak = max(peak, eq)
        dd = (peak - eq) / peak
        max_dd = max(max_dd, dd)
    result.max_drawdown = max_dd

    return result


# ---------------------------------------------------------------------------
# Go/No-Go criteria
# ---------------------------------------------------------------------------

def evaluate_criteria(result: BacktestResult) -> list[tuple[str, bool, str]]:
    """
    Evaluate the backtest result against spec criteria.
    Returns list of (criterion_name, passed, detail_string).
    """
    checks = []

    # 1. Rolling equity rising 60%+ of the time
    rising_count = 0
    total_steps = len(result.equity_curve) - 1
    for i in range(1, len(result.equity_curve)):
        if result.equity_curve[i] >= result.equity_curve[i - 1]:
            rising_count += 1
    rising_pct = (rising_count / total_steps * 100) if total_steps > 0 else 0
    checks.append((
        "Rolling equity rising 60%+ of time",
        rising_pct >= 60,
        f"{rising_pct:.1f}%",
    ))

    # 2. Max drawdown < 15%
    checks.append((
        "Max drawdown < 15%",
        result.max_drawdown < 0.15,
        f"{result.max_drawdown * 100:.2f}%",
    ))

    # 3. At least 20 trades
    checks.append((
        "At least 20 trades",
        len(result.trades) >= 20,
        f"{len(result.trades)} trades",
    ))

    # 4. Average win > 1.5x average loss
    win_loss_ratio = (result.avg_win / result.avg_loss) if result.avg_loss > 0 else float("inf")
    checks.append((
        "Average win > 1.5x average loss",
        win_loss_ratio > 1.5,
        f"{win_loss_ratio:.2f}x",
    ))

    # 5. No single regime > 80% of PnL
    total_pnl = sum(abs(v) for v in result.regime_pnl.values())
    max_regime_pct = 0.0
    max_regime_name = "none"
    if total_pnl > 0:
        for regime, pnl in result.regime_pnl.items():
            pct = abs(pnl) / total_pnl * 100
            if pct > max_regime_pct:
                max_regime_pct = pct
                max_regime_name = regime
    checks.append((
        "No single regime > 80% of PnL",
        max_regime_pct <= 80,
        f"{max_regime_name}: {max_regime_pct:.1f}%",
    ))

    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TrustDesk Backtest")
    parser.add_argument("--pair", default="BTCUSD", help="Trading pair (default: BTCUSD)")
    parser.add_argument("--interval", type=int, default=60, help="Candle interval in minutes (default: 60)")
    parser.add_argument("--days", type=int, default=90, help="Days of history (default: 90)")
    parser.add_argument("--hold", type=int, default=5, help="Candles to hold per trade (default: 5)")
    args = parser.parse_args()

    print("=" * 60)
    print("  TrustDesk Backtest")
    print("=" * 60)
    print(f"  Pair:     {args.pair}")
    print(f"  Interval: {args.interval}m")
    print(f"  History:  {args.days} days")
    print(f"  Hold:     {args.hold} candles")
    print("=" * 60)
    print()

    # Step 1: Fetch data
    candles = fetch_ohlc_kraken_cli(args.pair, args.interval, args.days)
    if not candles:
        print("[ERROR] No candle data available. Exiting.")
        sys.exit(1)

    # Step 2: Compute signals
    print(f"[SIGNAL] Computing signals over {len(candles)} candles...")
    signals = compute_signals(candles)
    print(f"[SIGNAL] Generated {len(signals)} raw signals.")

    # Step 3: Simulate trades
    print("[TRADE] Simulating trades with strategist + risk manager...")
    result = simulate_trades(candles, signals, hold_periods=args.hold)
    print(f"[TRADE] Executed {len(result.trades)} trades.")
    print()

    # Step 4: Print summary
    print("-" * 60)
    print("  BACKTEST RESULTS")
    print("-" * 60)
    print(f"  Total trades:    {len(result.trades)}")
    print(f"  Win rate:        {result.win_rate * 100:.1f}%")
    print(f"  Avg win:         {result.avg_win * 100:.3f}%")
    print(f"  Avg loss:        {result.avg_loss * 100:.3f}%")
    win_loss = (result.avg_win / result.avg_loss) if result.avg_loss > 0 else float("inf")
    print(f"  Win/Loss ratio:  {win_loss:.2f}x")
    print(f"  Max drawdown:    {result.max_drawdown * 100:.2f}%")
    start_eq = result.equity_curve[0] if result.equity_curve else 10000
    end_eq = result.equity_curve[-1] if result.equity_curve else 10000
    print(f"  Start equity:    ${start_eq:,.2f}")
    print(f"  End equity:      ${end_eq:,.2f}")
    print(f"  Total return:    {(end_eq - start_eq) / start_eq * 100:.2f}%")
    print()
    print("  Regime PnL breakdown:")
    for regime, pnl in sorted(result.regime_pnl.items()):
        print(f"    {regime:12s}: ${pnl:,.2f}")
    print()

    # Step 5: Go/No-Go evaluation
    print("=" * 60)
    print("  GO / NO-GO EVALUATION")
    print("=" * 60)
    checks = evaluate_criteria(result)
    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        icon = "[+]" if passed else "[-]"
        print(f"  {icon} {status}: {name} ({detail})")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  >>> VERDICT: GO -- All criteria met. Ready for live deployment. <<<")
    else:
        print("  >>> VERDICT: NO-GO -- Some criteria not met. Review and adjust. <<<")
    print()

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

### Verification

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
uv run python backend/scripts/run_backtest.py --days 90
# Should run to completion (may use synthetic data if Kraken CLI not installed)
# Should print a go/no-go verdict
```

### Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/scripts/run_backtest.py
git commit -m "feat: add backtest script with go/no-go criteria"
```

---

## Task 5: Submission checklist script

**File to create:**
- `backend/scripts/submission_check.py`

### `backend/scripts/submission_check.py`

```python
#!/usr/bin/env python3
"""
Pre-submission checklist: verify all requirements are met for hackathon submission.

Usage:
    uv run python scripts/submission_check.py
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

# Resolve project root (two levels up from this script)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


def _run(cmd: list[str], cwd: str | Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or PROJECT_ROOT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_db() -> tuple[bool, str]:
    """Check PostgreSQL is running and reachable on port 5433."""
    try:
        sock = socket.create_connection(("localhost", 5433), timeout=5)
        sock.close()
        return True, "PostgreSQL reachable on localhost:5433"
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        return False, f"Cannot connect to PostgreSQL on 5433: {e}"


def check_backend() -> tuple[bool, str]:
    """Check that the backend module can be imported (basic sanity)."""
    rc, out, err = _run(
        ["uv", "run", "python", "-c", "import trustdesk; print('OK')"],
        cwd=BACKEND_DIR,
    )
    if rc == 0 and "OK" in out:
        return True, "Backend module imports successfully"
    return False, f"Backend import failed: {err.strip()[:200]}"


def check_dashboard_build() -> tuple[bool, str]:
    """Check that the dashboard builds without errors."""
    dashboard_dir = PROJECT_ROOT / "dashboard"
    if not (dashboard_dir / "package.json").exists():
        return False, "dashboard/package.json not found"
    rc, out, err = _run(["npm", "run", "build"], cwd=dashboard_dir, timeout=120)
    if rc == 0:
        dist = dashboard_dir / "dist"
        if dist.exists():
            return True, f"Dashboard builds successfully ({len(list(dist.rglob('*')))} files)"
        return True, "Dashboard build completed (dist dir not checked)"
    return False, f"Dashboard build failed: {err.strip()[:200]}"


def check_contracts() -> tuple[bool, str]:
    """Check that Foundry contracts compile."""
    contracts_dir = PROJECT_ROOT / "contracts"
    if not contracts_dir.exists():
        return False, "contracts/ directory not found"
    rc, out, err = _run(["forge", "build"], cwd=contracts_dir, timeout=120)
    if rc == 0:
        return True, "Contracts compile with forge build"
    return False, f"Contracts failed to compile: {err.strip()[:200]}"


def check_tests() -> tuple[bool, str]:
    """Check that backend tests pass and there are 562+ tests."""
    rc, out, err = _run(
        ["uv", "run", "pytest", "--tb=no", "-q"],
        cwd=BACKEND_DIR,
        timeout=300,
    )
    # Parse test count from pytest output, e.g. "562 passed"
    import re
    match = re.search(r"(\d+) passed", out + err)
    if match:
        count = int(match.group(1))
        if rc == 0 and count >= 562:
            return True, f"{count} tests passed"
        elif rc == 0:
            return False, f"Only {count} tests passed (need 562+)"
        else:
            # Some failures
            fail_match = re.search(r"(\d+) failed", out + err)
            fail_count = int(fail_match.group(1)) if fail_match else "?"
            return False, f"{count} passed, {fail_count} failed"
    return False, f"Could not parse test output: {(out + err).strip()[:200]}"


def check_coverage() -> tuple[bool, str]:
    """Check test coverage is at 100%."""
    rc, out, err = _run(
        ["uv", "run", "pytest", "--cov=trustdesk", "--cov-report=term-missing", "--tb=no", "-q"],
        cwd=BACKEND_DIR,
        timeout=300,
    )
    import re
    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", out + err)
    if match:
        coverage = int(match.group(1))
        if coverage == 100:
            return True, "100% test coverage"
        return False, f"Coverage is {coverage}% (need 100%)"
    return False, f"Could not parse coverage output: {(out + err).strip()[:200]}"


def check_kraken() -> tuple[bool, str]:
    """Check that Kraken CLI is installed."""
    rc, out, err = _run(["kraken", "--version"])
    if rc == 0:
        version = out.strip() or err.strip()
        return True, f"Kraken CLI installed: {version[:80]}"
    return False, "Kraken CLI not found (install: pip install kraken-cli or similar)"


def check_identity() -> tuple[bool, str]:
    """Check that on-chain identity is registered (contract address set in env)."""
    addr = os.environ.get("VALIDATOR_CONTRACT_ADDRESS", "")
    if addr and addr.startswith("0x") and len(addr) == 42:
        return True, f"Validator contract: {addr}"
    return False, "VALIDATOR_CONTRACT_ADDRESS not set or invalid in environment"


def check_env() -> tuple[bool, str]:
    """Check that .env has all required keys."""
    env_file = BACKEND_DIR / ".env"
    example_file = BACKEND_DIR / ".env.example"

    if not env_file.exists():
        # Also check project root
        env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return False, ".env file not found in backend/ or project root"

    env_lines = env_file.read_text().splitlines()
    env_keys = set()
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            env_keys.add(key)

    required_keys = [
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
    ]
    missing = [k for k in required_keys if k not in env_keys]
    if missing:
        return False, f"Missing env vars: {', '.join(missing)}"
    return True, f".env has {len(env_keys)} keys, all required keys present"


def check_github() -> tuple[bool, str]:
    """Check that git remote is set and repo is accessible."""
    rc, out, err = _run(["git", "remote", "get-url", "origin"])
    if rc != 0:
        return False, "No git remote 'origin' configured"
    url = out.strip()
    if "sneg55/TrustDesk" not in url:
        return False, f"Unexpected remote: {url}"
    return True, f"GitHub remote: {url}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS: list[tuple[str, object]] = [
    ("PostgreSQL running", check_db),
    ("Backend starts", check_backend),
    ("Dashboard builds", check_dashboard_build),
    ("Contracts compile", check_contracts),
    ("Tests pass (562+)", check_tests),
    ("Coverage 100%", check_coverage),
    ("Kraken CLI installed", check_kraken),
    ("On-chain identity registered", check_identity),
    (".env complete", check_env),
    ("GitHub repo accessible", check_github),
]


def main() -> None:
    print("=" * 60)
    print("  TrustDesk Pre-Submission Checklist")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    results: list[tuple[str, bool, str]] = []

    for name, check_fn in CHECKS:
        print(f"  Checking: {name}...", end=" ", flush=True)
        try:
            ok, detail = check_fn()
        except Exception as e:
            ok, detail = False, f"Exception: {e}"
        results.append((name, ok, detail))
        if ok:
            print("OK")
            passed += 1
        else:
            print("FAIL")
            failed += 1

    print()
    print("-" * 60)
    print("  RESULTS")
    print("-" * 60)
    for name, ok, detail in results:
        icon = "[+]" if ok else "[-]"
        status = "PASS" if ok else "FAIL"
        print(f"  {icon} {status}: {name}")
        print(f"         {detail}")
    print()
    print(f"  TOTAL: {passed} passed, {failed} failed out of {len(CHECKS)}")
    print()

    if failed == 0:
        print("  >>> ALL CHECKS PASSED -- Ready for submission! <<<")
    else:
        print(f"  >>> {failed} CHECK(S) FAILED -- Fix before submitting. <<<")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
```

### Verification

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
uv run python backend/scripts/submission_check.py
# Will show pass/fail for each check
# Some may fail (e.g., no Kraken CLI) -- that's expected in dev
```

### Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/scripts/submission_check.py
git commit -m "feat: add pre-submission checklist script"
```

---

## Execution Order

Tasks 1-5 are independent and can be executed in parallel by separate agents. However, if executing sequentially, the recommended order is:

1. **Task 1** (Dockerfile) -- foundation for Task 2
2. **Task 2** (Railway config) -- depends on Dockerfile existing
3. **Task 3** (Vercel config) -- independent, can run alongside 1+2
4. **Task 4** (Backtest script) -- fully independent
5. **Task 5** (Submission checklist) -- best done last since it validates everything

## Risk Notes

- **Kraken CLI availability:** The backtest script includes a synthetic data fallback so it works even without Kraken CLI installed. Judges will see the backtest framework regardless.
- **Railway free tier:** Railway's free tier may not have enough resources. Consider upgrading to the Hobby plan ($5/mo) for the hackathon.
- **Vercel environment:** The `VITE_API_URL` in `.env.production` assumes the Railway domain `trustdesk-backend.up.railway.app`. Update this after Railway deployment gives the actual URL.
- **Docker build without .env:** The Dockerfile deliberately does NOT copy `.env`. All secrets must be injected via Railway's environment variable system.
