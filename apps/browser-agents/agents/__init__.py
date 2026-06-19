"""
Route task names to the correct agent function.
"""
from typing import Any, Dict


TASK_MAP = {
    "browse_test": "agents.social:browse_test",
    "tiktok_post": "agents.social:tiktok_post",
    "instagram_post": "agents.social:instagram_post",
    "twitter_post": "agents.social:twitter_post",
    "pph_submit": "agents.proposals:pph_submit",
    "scrape_leads": "agents.scraper:scrape_leads",
    "refresh_token": "agents.oauth:refresh_token",
}


async def run_task(task: str, params: Dict[str, Any]) -> dict:
    if task not in TASK_MAP:
        raise ValueError(f"Unknown task: {task}. Available: {list(TASK_MAP.keys())}")

    module_path, fn_name = TASK_MAP[task].split(":")
    import importlib
    mod = importlib.import_module(module_path)
    fn = getattr(mod, fn_name)
    return await fn(params)
