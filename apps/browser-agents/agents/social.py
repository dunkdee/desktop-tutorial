"""
Social media browser agents — TikTok, Instagram, Twitter.
All agents log in via real browser to avoid API token issues.
"""
import os
from typing import Any, Dict

from browser_use import Agent
from langchain_anthropic import ChatAnthropic
from playwright.async_api import async_playwright

from memory import get_context, log_result

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20251001")


def _llm():
    return ChatAnthropic(
        model_name=_MODEL,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )


async def browse_test(params: Dict[str, Any]) -> dict:
    """Smoke test — open google.com and return the page title."""
    agent = Agent(
        task="Go to https://www.google.com and return the page title.",
        llm=_llm(),
    )
    result = await agent.run()
    return {"success": True, "result": str(result)}


async def tiktok_post(params: Dict[str, Any]) -> dict:
    """
    Log in to TikTok and post a video.
    params: { video_path, caption, username (opt), password (opt) }
    """
    username = params.get("username") or os.getenv("TIKTOK_USERNAME", "")
    password = params.get("password") or os.getenv("TIKTOK_PASSWORD", "")
    video_path = params.get("video_path", "")
    caption = params.get("caption", "#dominionhealing #sovereignty #abundance")

    if not username or not password:
        return {"success": False, "error": "TIKTOK_USERNAME/PASSWORD not set"}

    past = get_context("tiktok_post")

    task = f"""
You are posting a video to TikTok.

Credentials: username="{username}", password="{password}"
Video file path: {video_path if video_path else "find the most recently created .mp4 in /app/content/"}
Caption: {caption}

{past}

Steps:
1. Go to https://www.tiktok.com/login
2. Log in with the provided credentials
3. Navigate to the upload page (https://www.tiktok.com/upload)
4. Upload the video file
5. Add the caption
6. Click Post
7. Confirm the post succeeded and return the video URL if available

If you encounter a CAPTCHA or 2FA, report the exact screen you see so the user can handle it.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "success" in str(result).lower() or "posted" in str(result).lower()
        log_result("tiktok_post", success, str(result)[:300])
        return {"success": success, "result": str(result)}
    except Exception as e:
        log_result("tiktok_post", False, str(e))
        return {"success": False, "error": str(e)}


async def instagram_post(params: Dict[str, Any]) -> dict:
    """
    Log in to Instagram and post an image or video.
    params: { media_path, caption, username (opt), password (opt) }
    """
    username = params.get("username") or os.getenv("INSTAGRAM_USERNAME", "")
    password = params.get("password") or os.getenv("INSTAGRAM_PASSWORD", "")
    media_path = params.get("media_path", "")
    caption = params.get("caption", "#dominionhealing #sovereignty")

    if not username or not password:
        return {"success": False, "error": "INSTAGRAM_USERNAME/PASSWORD not set"}

    past = get_context("instagram_post")

    task = f"""
You are posting to Instagram.

Credentials: username="{username}", password="{password}"
Media path: {media_path if media_path else "find the most recent image in /app/content/"}
Caption: {caption}

{past}

Steps:
1. Go to https://www.instagram.com/accounts/login/
2. Log in with credentials
3. Click the + (New Post) button
4. Upload the media file
5. Write the caption
6. Share the post
7. Return the post URL if available

Report any CAPTCHA or suspicious activity screens immediately.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "success" in str(result).lower() or "shared" in str(result).lower()
        log_result("instagram_post", success, str(result)[:300])
        return {"success": success, "result": str(result)}
    except Exception as e:
        log_result("instagram_post", False, str(e))
        return {"success": False, "error": str(e)}


async def twitter_post(params: Dict[str, Any]) -> dict:
    """
    Log in to Twitter/X and post a tweet.
    params: { text, media_path (opt), username (opt), password (opt) }
    """
    username = params.get("username") or os.getenv("TWITTER_USERNAME", "")
    password = params.get("password") or os.getenv("TWITTER_PASSWORD", "")
    text = params.get("text", "")
    media_path = params.get("media_path", "")

    if not username or not password:
        return {"success": False, "error": "TWITTER_USERNAME/PASSWORD not set"}
    if not text:
        return {"success": False, "error": "tweet text required"}

    past = get_context("twitter_post")

    task = f"""
You are posting a tweet on Twitter/X.

Credentials: username="{username}", password="{password}"
Tweet text: {text}
{"Media to attach: " + media_path if media_path else ""}

{past}

Steps:
1. Go to https://twitter.com/i/flow/login
2. Log in with credentials
3. Click the compose tweet button
4. Type the tweet text
5. {"Attach the media file" if media_path else ""}
6. Click Post/Tweet
7. Return the tweet URL

Report any verification screens immediately.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "success" in str(result).lower() or "posted" in str(result).lower()
        log_result("twitter_post", success, str(result)[:300])
        return {"success": success, "result": str(result)}
    except Exception as e:
        log_result("twitter_post", False, str(e))
        return {"success": False, "error": str(e)}
