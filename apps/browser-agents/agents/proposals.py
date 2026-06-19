"""
PeoplePerHour proposal agent — scans jobs, writes proposals with Claude, submits.
"""
import os
from typing import Any, Dict

from browser_use import Agent
from langchain_anthropic import ChatAnthropic

from memory import get_context, log_result

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20251001")
_MAX_PROPOSALS = int(os.getenv("PPH_MAX_PROPOSALS_PER_RUN", "3"))

PPH_CATEGORIES = os.getenv(
    "PPH_TARGET_CATEGORIES",
    "web-development,python,automation,ai-machine-learning,data-science"
)

PPH_MIN_BUDGET = int(os.getenv("PPH_MIN_BUDGET", "50"))
PPH_MAX_BUDGET = int(os.getenv("PPH_MAX_BUDGET", "2000"))


def _llm():
    return ChatAnthropic(
        model_name=_MODEL,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.3,
    )


async def pph_submit(params: Dict[str, Any]) -> dict:
    """
    Browse PeoplePerHour for relevant jobs and submit up to MAX_PROPOSALS proposals.
    params: { categories (opt), min_budget (opt), max_proposals (opt) }
    """
    username = params.get("username") or os.getenv("PPH_USERNAME", "")
    password = params.get("password") or os.getenv("PPH_PASSWORD", "")
    categories = params.get("categories") or PPH_CATEGORIES
    min_budget = params.get("min_budget") or PPH_MIN_BUDGET
    max_proposals = params.get("max_proposals") or _MAX_PROPOSALS

    if not username or not password:
        return {"success": False, "error": "PPH_USERNAME/PASSWORD not set"}

    past = get_context("pph_submit")

    task = f"""
You are a skilled freelancer submitting proposals on PeoplePerHour to win contracts.

Credentials: username="{username}", password="{password}"
Target categories: {categories}
Minimum budget: ${min_budget}
Maximum proposals to submit this run: {max_proposals}

{past}

Steps:
1. Go to https://www.peopleperhour.com/login and log in
2. Browse job listings in the target categories
3. Filter for jobs with budget >= ${min_budget}
4. For each suitable job (up to {max_proposals}):
   a. Read the full job description carefully
   b. Write a compelling, personalized proposal that:
      - Addresses the client's specific problem
      - Highlights relevant experience (Python, AI, automation, web development)
      - Shows understanding of their requirements
      - Includes a realistic timeline and approach
      - Is 150-250 words — not too long, not too short
   c. Set a competitive bid price
   d. Submit the proposal
5. Return a list of jobs applied to with titles and bid amounts

Prioritize jobs that match: AI/automation, Python scripting, data processing, web scraping,
real estate tech, business automation.

If you encounter a job that perfectly matches, write an especially detailed proposal.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "submitted" in str(result).lower() or "proposal" in str(result).lower()
        log_result("pph_submit", success, str(result)[:400], {"max_proposals": max_proposals})
        return {"success": success, "result": str(result), "proposals_attempted": max_proposals}
    except Exception as e:
        log_result("pph_submit", False, str(e))
        return {"success": False, "error": str(e)}
