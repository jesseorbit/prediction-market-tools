# prediction-market-tools

Personal quant research notes + scratchpad code for **prediction-market analytics** and **automated trading experiments**.

This repo is **experiment-first**: small scripts, prototypes, and notes used to test trading ideas quickly.
Expect rough edges, frequent iteration, and non-production code.

---

## What’s inside

### `Arbitrage/` — Cross-venue arbitrage scanner
Scans and surfaces arbitrage opportunities across prediction-market venues:
- **Polymarket**
- **Kalshi**
- **Opinion** (Opinion Labs)

Typical flow:
1) Pull markets / prices / orderbooks  
2) Normalize + match markets across venues  
3) Compute spreads / edge candidates  
4) Log / export opportunities

---

### `PolyQuant/` — Real-time BTC 15m trading experiments
Real-time trading logic for **BTC 15-minute markets** (prediction markets).
Focus: execution loops, position management, and unwinding logic under time constraints.

Typical flow:
1) Stream prices / market state  
2) Trigger entries based on thresholds  
3) Manage average price + hedges/unwind  
4) Close/flatten near expiry and handle late-stage behavior

---

## Quick start

### 1) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
````

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, scripts commonly use: `requests`, `pandas`, `numpy`.

### 3) Configure (never commit secrets)

Use environment variables for API keys and private endpoints.

Example:

```bash
export POLYMARKET_API_KEY="..."
export KALSHI_API_KEY="..."
export OPINION_API_KEY="..."
```

---

## How to run

Because this repo contains multiple experiments, entry points vary by folder.

General pattern:

```bash
python path/to/script.py --help
```

Suggested entry points:

* `Arbitrage/` → run scanners and export candidate opportunities
* `PolyQuant/` → run real-time BTC 15m trading loop

> If you want, add a `README.md` inside each folder with the exact “run this script” command(s).

---

## Notes / Disclaimer

* Research sandbox, **not production trading code**
* No financial advice
* Never commit secrets

---

## License

Private / All rights reserved (unless a LICENSE file is added)

```
