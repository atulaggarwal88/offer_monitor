"""
Offer Monitor Main Orchestrator

This script serves as the entry point for monitoring deal targets configured in config.yaml.
It orchestrates the process by:
1. Loading configuration (config.yaml).
2. Initializing the Agno AI Agent with specified Gemini model.
3. Iterating through targets to scrape & extract deal items via agno_agent.py (with timeouts).
4. Sending notifications (Slack / File log) via notifier.py (including heartbeats & error alerts).
"""

import os
import sys
import yaml
import structlog
from dotenv import load_dotenv

# Force working directory to be the script's directory (helpful for launchd daemons)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Load environment variables from .env
load_dotenv()

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

from agno_agent import create_agno_agent, extract_deals_for_target
from notifier import notify_deals, send_slack_heartbeat, send_slack_error

CONFIG_FILE = "config.yaml"


def load_config(filepath: str) -> dict:
    """Loads configuration from YAML file."""
    if not os.path.exists(filepath):
        logger.error("Configuration file not found", path=filepath)
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to parse configuration file", path=filepath, error=str(e))
        return {}


def main():
    logger.info("Starting Offer Monitor...")

    # 1. Load configuration
    config = load_config(CONFIG_FILE)
    targets = config.get("targets", [])
    notifiers_config = config.get("notifiers", {})
    model_id = config.get("model_id", "gemini-3.6-flash")
    slack_cfg = notifiers_config.get("slack", {})
    webhook_url = slack_cfg.get("webhook_url") or os.getenv("SLACK_WEBHOOK_URL")

    if not targets:
        logger.warning("No targets found in config.yaml. Exiting.")
        return

    # 2. Initialize Agno Agent
    logger.info("Initializing Agno Web Search Agent...", model_id=model_id)
    try:
        agent = create_agno_agent(model_id=model_id)
    except Exception as e:
        err_msg = f"Failed to initialize Agno Agent: {e}"
        logger.error(err_msg)
        if webhook_url:
            send_slack_error(webhook_url, err_msg)
        return

    # 3. Iterate targets and extract deals
    all_deals = []
    failed_targets = []
    for target in targets:
        name = target.get("name", "Unknown Target")
        url = target.get("url", "")
        prompt = target.get("prompt", "")

        logger.info("Processing target", name=name, url=url)
        try:
            deals = extract_deals_for_target(agent, target_name=name, url=url, prompt=prompt, timeout_seconds=120)
            if deals:
                print(f"\n🎉 Found {len(deals)} active deal(s) for [{name}]:")
                for deal in deals:
                    print(f"  • {deal.title} - {deal.link}")

                notify_deals(deals, notifiers_config)
                all_deals.extend(deals)
            else:
                print(f"No active deals found for [{name}].")
        except Exception as e:
            logger.error("Error processing target", name=name, error=str(e))
            failed_targets.append(name)

    logger.info("Scan finished successfully", total_deals_found=len(all_deals), failed_targets=len(failed_targets))

    # 4. Dispatch Heartbeat summary to Slack if enabled
    if slack_cfg.get("send_heartbeat", True) and webhook_url:
        status_text = f"Scan finished: *{len(all_deals)} deal(s)* found across *{len(targets)} target(s)*."
        if failed_targets:
            status_text += f"\n⚠️ *{len(failed_targets)} target(s) failed:* {', '.join(failed_targets)}"
        send_slack_heartbeat(webhook_url, status_text)


if __name__ == "__main__":
    main()

