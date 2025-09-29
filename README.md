# Deriv Educational Trading Bot (Demo) #algotradingbot #tradingbot #deriv #websocket

An educational websocket bot for Deriv's API.

## Quick start

- Create a DEMO API token in your VRTC (virtual) account at Deriv.
- Then run:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DERIV_DEMO_TOKEN="<your_demo_token>"
python deriv_bot.py
```

## What it does
- Connects to Deriv websocket and authorizes with your demo token
- Requests a simple CALL proposal on Volatility 100 Index
- Buys with $1 stake and monitors the contract
- Auto-reconnects + resubscribes on disconnect
- Exits on profit target ($10) or stop loss (-$5)

## Configuration
- Edit these in `deriv_bot.py`:
  - `profit_target = 10`
  - `stop_loss = -5`
  - `position_size = 1`

## Safety
- Use DEMO tokens only. Never commit tokens to git.
- Token is read from `DERIV_DEMO_TOKEN` env var (no secrets in code).

## License
MIT
