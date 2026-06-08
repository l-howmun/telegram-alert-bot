# Telegram Alert Bot

Monitors data sources (CSV files, APIs) against configurable rules and sends formatted Telegram alerts when thresholds are breached.

## Features
- **CSV monitoring** — Watch spreadsheets for threshold breaches (costs, usage, KPIs)
- **API monitoring** — Poll any JSON API and alert on conditions (prices, status)
- **Configurable rules** — JSON config with operators (`>`, `<`), severity levels, custom titles
- **Telegram delivery** — Formatted messages with severity emojis, timestamps
- **Loop mode** — Run continuously with configurable intervals
- **Dry-run mode** — Test rules without sending messages

## Usage

```bash
pip install -r requirements.txt

# Run once (dry-run to test)
python alert_bot.py config.example.json --dry-run

# Run once and send alerts
python alert_bot.py config.json

# Monitor every 60 seconds
python alert_bot.py config.json --loop 60
```

## Config Format

```json
{
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "monitors": [
    {
      "name": "Server Costs",
      "type": "csv",
      "path": "data/costs.csv",
      "rules": [
        {
          "column": "monthly_cost",
          "operator": ">",
          "threshold": 500,
          "severity": "critical",
          "title": "High cost alert",
          "label_col": "server_name"
        }
      ]
    },
    {
      "name": "BTC Price",
      "type": "api",
      "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
      "rules": [
        {
          "field": "bitcoin.usd",
          "operator": "<",
          "threshold": 50000,
          "severity": "critical",
          "title": "BTC crash alert"
        }
      ]
    }
  ]
}
```

## Sample Run

```
Checking: Server Costs

Checking: Bitcoin Price

Alerts triggered: 4
  [SENT] WARNING: High server cost detected
  [SENT] CRITICAL: CPU usage critical
  [SENT] WARNING: High server cost detected
  [SENT] CRITICAL: CPU usage critical
```

## Setup Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. `/newbot` → follow prompts → get bot token
3. Start a chat with your bot, send any message
4. Get chat_id: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Put token + chat_id in your config.json

## Tech
Python 3.10+ | httpx | Telegram Bot API
