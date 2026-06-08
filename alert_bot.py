"""
Telegram Alert Bot
Monitors a data source (CSV/API/webhook) and sends formatted Telegram alerts
when conditions are met. Demonstrates bot-building + scheduling + API integration.
Portfolio Project #3.
"""
import httpx
import argparse
import json
import time
import csv
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Alert:
    title: str
    message: str
    severity: str = "info"  # info, warning, critical
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SEVERITY_EMOJI = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}


def format_telegram_message(alert: Alert) -> str:
    emoji = SEVERITY_EMOJI.get(alert.severity, "ℹ️")
    return (
        f"{emoji} *{alert.title}*\n\n"
        f"{alert.message}\n\n"
        f"`{alert.timestamp}`"
    )


def send_telegram(bot_token: str, chat_id: str, alert: Alert) -> bool:
    """Send a formatted alert to Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": format_telegram_message(alert),
        "parse_mode": "Markdown",
    }
    try:
        r = httpx.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"  [SENT] {alert.severity.upper()}: {alert.title}")
            return True
        else:
            print(f"  [FAIL] {r.status_code}: {r.text[:100]}")
            return False
    except httpx.HTTPError as e:
        print(f"  [FAIL] {e}")
        return False


# ─── MONITORS ────────────────────────────────────────────────────────────────────

def monitor_csv(filepath: str, rules: list[dict]) -> list[Alert]:
    """Check CSV file against threshold rules."""
    alerts = []
    path = Path(filepath)
    if not path.exists():
        return [Alert("File Missing", f"{filepath} not found", "critical")]

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for rule in rules:
                col = rule["column"]
                if col not in row:
                    continue
                try:
                    value = float(row[col].replace(",", ""))
                except (ValueError, AttributeError):
                    continue

                if rule["operator"] == ">" and value > rule["threshold"]:
                    alerts.append(Alert(
                        title=rule.get("title", f"{col} threshold exceeded"),
                        message=f"{col} = {value:,.2f} (threshold: {rule['operator']} {rule['threshold']:,.2f})\nRow: {row.get(rule.get('label_col', col), '')}",
                        severity=rule.get("severity", "warning"),
                    ))
                elif rule["operator"] == "<" and value < rule["threshold"]:
                    alerts.append(Alert(
                        title=rule.get("title", f"{col} below threshold"),
                        message=f"{col} = {value:,.2f} (threshold: {rule['operator']} {rule['threshold']:,.2f})\nRow: {row.get(rule.get('label_col', col), '')}",
                        severity=rule.get("severity", "warning"),
                    ))
    return alerts


def monitor_api(url: str, rules: list[dict]) -> list[Alert]:
    """Check a JSON API endpoint against rules."""
    alerts = []
    try:
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [Alert("API Unreachable", f"{url}\nError: {e}", "critical")]

    for rule in rules:
        field = rule["field"]
        # Support nested fields with dot notation
        value = data
        for key in field.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)]
            else:
                value = None
                break

        if value is None:
            continue

        try:
            value = float(value)
        except (ValueError, TypeError):
            continue

        triggered = False
        if rule["operator"] == ">" and value > rule["threshold"]:
            triggered = True
        elif rule["operator"] == "<" and value < rule["threshold"]:
            triggered = True

        if triggered:
            alerts.append(Alert(
                title=rule.get("title", f"{field} alert"),
                message=f"{field} = {value:,.2f} (threshold: {rule['operator']} {rule['threshold']:,.2f})",
                severity=rule.get("severity", "warning"),
            ))
    return alerts


# ─── MAIN ────────────────────────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        print(f"Error: {config_path} not found")
        raise SystemExit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def run_once(config: dict, dry_run=False):
    """Run all monitors once and send alerts."""
    bot_token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    monitors = config.get("monitors", [])
    all_alerts = []

    for mon in monitors:
        mon_type = mon["type"]
        print(f"\nChecking: {mon.get('name', mon_type)}")

        if mon_type == "csv":
            alerts = monitor_csv(mon["path"], mon["rules"])
        elif mon_type == "api":
            alerts = monitor_api(mon["url"], mon["rules"])
        else:
            print(f"  Unknown monitor type: {mon_type}")
            continue

        all_alerts.extend(alerts)

    print(f"\nAlerts triggered: {len(all_alerts)}")
    for alert in all_alerts:
        if dry_run:
            print(f"  [DRY RUN] {alert.severity.upper()}: {alert.title}")
            print(f"            {alert.message}")
        else:
            if not bot_token or not chat_id:
                print(f"  [SKIP] No bot_token/chat_id configured")
                print(f"         {alert.severity.upper()}: {alert.title} - {alert.message}")
            else:
                send_telegram(bot_token, chat_id, alert)

    return all_alerts


def run_loop(config: dict, interval: int, dry_run=False):
    """Run monitors in a loop with interval."""
    print(f"Starting monitor loop (every {interval}s). Ctrl+C to stop.\n")
    while True:
        print(f"--- {datetime.now().strftime('%H:%M:%S')} ---")
        run_once(config, dry_run)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Monitor data sources and send Telegram alerts.")
    parser.add_argument("config", help="Path to config JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Print alerts without sending")
    parser.add_argument("--loop", type=int, default=0, help="Run every N seconds (0 = run once)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.loop > 0:
        run_loop(config, args.loop, args.dry_run)
    else:
        run_once(config, args.dry_run)


if __name__ == "__main__":
    main()
