"""
Notification dispatchers for Slack and File log outputs.
"""

import os
import json
import urllib.request
import structlog
from datetime import datetime
from typing import List, Union, Set
from models import DealItem

logger = structlog.get_logger()

SEEN_DEALS_FILE = "build/seen_deals.json"


def load_seen_deals(file_path: str = SEEN_DEALS_FILE) -> Set[str]:
    """Loads a set of previously seen deal links/identifiers."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.warning("Could not load seen deals file", error=str(e))
    return set()


def save_seen_deals(seen_set: Set[str], file_path: str = SEEN_DEALS_FILE) -> None:
    """Saves set of seen deal links/identifiers."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(list(seen_set), f, indent=2)
    except Exception as e:
        logger.error("Failed to save seen deals file", error=str(e))


def deal_to_dict(deal: Union[DealItem, dict]) -> dict:
    """Converts a DealItem model or dict into a standard dict."""
    if isinstance(deal, DealItem):
        return deal.model_dump()
    return deal


def send_slack_message(webhook_url: str, payload: dict) -> bool:
    """Helper to send JSON payload to a Slack Webhook URL."""
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            pass
        return True
    except Exception as e:
        logger.error("Failed to post message to Slack", error=str(e))
        return False


def send_slack_notification(webhook_url: str, deal: Union[DealItem, dict]) -> None:
    """Sends a formatted deal card directly to a Slack channel via Webhook."""
    deal_data = deal_to_dict(deal)
    payload = {
        "text": f"🚨 *New {deal_data['target_name']} Deal!*",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *New {deal_data['target_name']} Deal Found!*\n*<{deal_data['link']}|{deal_data['title']}>*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Votes:* 👍 {deal_data['votes']}"},
                    {"type": "mrkdwn", "text": f"*Coupon:* `{deal_data['coupon'] or 'None'}`"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Submitted: {deal_data['submitted']}"}
                ]
            }
        ]
    }
    if send_slack_message(webhook_url, payload):
        logger.info("Slack deal card sent successfully", title=deal_data.get("title"))


def send_slack_heartbeat(webhook_url: str, text: str) -> None:
    """Sends a heartbeat / scan status update to Slack."""
    payload = {
        "text": f"🔍 *Offer Monitor Status:* {text}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔍 *Offer Monitor Scan Update*\n{text}"
                }
            }
        ]
    }
    send_slack_message(webhook_url, payload)


def send_slack_error(webhook_url: str, error_text: str) -> None:
    """Sends an error alert to Slack."""
    payload = {
        "text": f"⚠️ *Offer Monitor Alert:* {error_text}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Offer Monitor Error Alert*\n{error_text}"
                }
            }
        ]
    }
    send_slack_message(webhook_url, payload)


def notify_deals(deals: List[Union[DealItem, dict]], config_notifiers: dict) -> None:
    """Dispatches notifications for a list of deals based on notifier settings in config."""
    if not deals:
        return

    deal_dicts = [deal_to_dict(d) for d in deals]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. File Notifier (Append to a markdown log file)
    file_cfg = config_notifiers.get("file", {})
    if file_cfg.get("enabled", True):
        output_path = file_cfg.get("output_path", "offers_log.md")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        write_header = not os.path.exists(output_path)
        with open(output_path, "a", encoding="utf-8") as f:
            if write_header:
                f.write("# Gift Card Deals Log\n\n")
            
            f.write(f"## Scan run at {now_str}\n\n")
            for deal in deal_dicts:
                f.write(f"- **[{deal['target_name']}] {deal['title']}**\n")
                f.write(f"  - **Link:** {deal['link']}\n")
                f.write(f"  - **Votes:** {deal['votes']} | **Coupon:** {deal['coupon'] or 'None'}\n")
                f.write(f"  - **Submitted:** {deal['submitted']}\n\n")

    # 2. Slack Notifier
    slack_cfg = config_notifiers.get("slack", {})
    if slack_cfg.get("enabled", True):
        webhook_url = slack_cfg.get("webhook_url") or os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            seen_deals = load_seen_deals()
            new_deals = [d for d in deal_dicts if d.get("link") not in seen_deals]
            
            for deal in new_deals:
                send_slack_notification(webhook_url, deal)
                if deal.get("link"):
                    seen_deals.add(deal.get("link"))
            
            save_seen_deals(seen_deals)
        else:
            logger.warning("Slack notification skipped: SLACK_WEBHOOK_URL is not set in environment or config.")

