"""
check_health.py

Re-runs the same health-status rules from the IDComply case study,
compares against the last saved result, and posts to Slack only when
something actually changed. This is the script GitHub Actions runs on
a schedule.
"""

import json
import os
import sys
import csv
import requests

HISTORY_FILE = "status_history.json"
DATA_FILE = "health.csv"  # same shape as the original health data export

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def compute_status(review_rate, trend_pp):
    """Same rule-based logic already built into the dashboard.
    Kept here as plain, explicit thresholds, not a hidden formula,
    so it can be checked automatically."""
    if trend_pp < -5 or review_rate > 0.10:
        return "red"
    if review_rate > 0.065 or trend_pp < -1:
        return "amber"
    return "green"


def load_current_data():
    """Reads the same kind of CSV export the dashboard is built from."""
    rows = []
    with open(DATA_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "customer": row["customer"],
                "review_rate": float(row["review_rate"]),
                "trend_pp": float(row["trend_pp"]),
            })
    return rows


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE) as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def post_to_slack(message):
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL set, skipping Slack post. Message would have been:")
        print(message)
        return
    resp = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    resp.raise_for_status()


def main():
    current_rows = load_current_data()
    history = load_history()

    changes = []
    new_history = {}

    for row in current_rows:
        customer = row["customer"]
        new_status = compute_status(row["review_rate"], row["trend_pp"])
        old_status = history.get(customer)

        new_history[customer] = new_status

        if old_status is None:
            continue  # first time seeing this customer, nothing to compare yet
        if new_status != old_status:
            changes.append((customer, old_status, new_status))

    save_history(new_history)

    if not changes:
        print("No status changes this run.")
        return

    lines = ["*IDComply Customer Health — status change detected*"]
    for customer, old, new in changes:
        arrow = "\u2192"
        lines.append(f"\u2022 *{customer}*: {old.upper()} {arrow} {new.upper()}")
    message = "\n".join(lines)

    post_to_slack(message)
    print(f"Posted {len(changes)} change(s) to Slack.")


if __name__ == "__main__":
    sys.exit(main())
