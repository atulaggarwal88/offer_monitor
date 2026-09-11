"""
Agno Web Search Agent with Firecrawl Integration

This module is responsible solely for defining and initializing the Agno AI Agent
and executing deal extraction tasks using Firecrawl tools.
"""

import os
import json
import structlog
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import List

# Fix google.genai.types import issue in recent google-genai versions for Agno
try:
    import google.genai.types
    if not hasattr(google.genai.types, "FileSearch"):
        google.genai.types.FileSearch = None
except Exception:
    pass

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.firecrawl import FirecrawlTools

from models import DealItem, DealList

logger = structlog.get_logger()


def create_agno_agent(model_id: str = "gemini-3.6-flash") -> Agent:
    """Initializes and returns an Agno Agent configured with Gemini and Firecrawl tools."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    if not firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable is not set.")

    agent = Agent(
        model=Gemini(
            id=model_id,
            api_key=google_api_key,
            timeout=90.0,
            retries=3,
            delay_between_retries=2,
            exponential_backoff=True,
        ),
        tools=[FirecrawlTools(api_key=firecrawl_api_key)],
        output_schema=DealList,
        instructions=[
            "You are an expert web scraping, deal monitoring, and research agent.",
            "Use FirecrawlTools to scrape the specified web URL.",
            "Extract only active and non-expired deals.",
            "Always output a structured DealList object containing all extracted deal items."
        ],
        markdown=True
    )
    return agent


def extract_deals_for_target(agent: Agent, target_name: str, url: str, prompt: str, timeout_seconds: int = 120) -> List[DealItem]:
    """Executes the agent to extract structured deal items for a single target with a timeout."""
    logger.info("Agent starting deal extraction", name=target_name, url=url, timeout=timeout_seconds)
    full_prompt = f"Target Name: {target_name}\nURL to scrape: {url}\nTask Prompt: {prompt}"
    
    deals: List[DealItem] = []

    def _run_agent():
        return agent.run(full_prompt)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_agent)
            response = future.result(timeout=timeout_seconds)

        content = getattr(response, "content", None)

        if isinstance(content, DealList):
            for d in content.deals:
                d.target_name = target_name
                deals.append(d)
        elif isinstance(content, str):
            # Fallback JSON parsing if content returned as markdown text string
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content.split("```")[1].split("```")[0].strip()
            try:
                parsed = json.loads(cleaned_content)
                if isinstance(parsed, dict) and "deals" in parsed:
                    for d in parsed["deals"]:
                        d["target_name"] = target_name
                        deals.append(DealItem(**d))
            except Exception:
                logger.warning("Failed to parse text response into JSON", name=target_name)

        logger.info("Agent completed extraction", name=target_name, deals_found=len(deals))

    except FutureTimeoutError:
        logger.error("Agent execution timed out", name=target_name, timeout_seconds=timeout_seconds)
    except Exception as e:
        logger.error("Error during agent execution", name=target_name, error=str(e))

    return deals

