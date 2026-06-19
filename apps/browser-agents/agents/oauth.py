"""
OAuth token refresh agent — handles browser-based OAuth flows and writes new tokens to .env.
"""
import os
import re
from typing import Any, Dict

import httpx
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

from memory import get_context, log_result

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20251001")
BABY_API = os.getenv("BABY_API_URL", "http://baby-api:8080")


def _llm():
    return ChatAnthropic(
        model_name=_MODEL,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )


async def refresh_token(params: Dict[str, Any]) -> dict:
    """
    Refresh OAuth tokens for a service via browser flow.
    params: { service: "tiktok" | "instagram" | "twitter" | "all" }
    """
    service = params.get("service", "all")
    results = {}

    services_to_refresh = (
        ["tiktok", "instagram", "twitter"]
        if service == "all"
        else [service]
    )

    for svc in services_to_refresh:
        result = await _refresh_one(svc, params)
        results[svc] = result

    return {"success": all(r.get("success") for r in results.values()), "results": results}


async def _refresh_one(service: str, params: dict) -> dict:
    past = get_context(f"refresh_{service}")

    handlers = {
        "tiktok": _refresh_tiktok,
        "instagram": _refresh_instagram,
        "twitter": _refresh_twitter,
    }

    fn = handlers.get(service)
    if not fn:
        return {"success": False, "error": f"No refresh handler for {service}"}

    return await fn(params, past)


async def _refresh_tiktok(params: dict, past: str) -> dict:
    client_key = os.getenv("TIKTOK_CLIENT_ID") or os.getenv("TIKTOK_CLIENT_KEY", "")
    redirect_uri = os.getenv("TIKTOK_REDIRECT_URI", "https://dominionhealing.org/tiktok/callback")

    task = f"""
You need to refresh/obtain a TikTok access token via OAuth.

Client Key: {client_key}
Redirect URI: {redirect_uri}

{past}

Steps:
1. Navigate to: https://www.tiktok.com/v2/auth/authorize/?client_key={client_key}&response_type=code&scope=user.info.basic,video.upload&redirect_uri={redirect_uri}
2. Log in if needed (credentials from environment: TIKTOK_USERNAME/PASSWORD)
3. Authorize the app
4. After redirect, capture the "code" parameter from the URL
5. Return the authorization code so it can be exchanged for an access token

Report the exact URL you land on after authorization so we can extract the code.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        code = _extract_code(str(result))
        if code:
            token = await _exchange_tiktok_code(code, client_key, redirect_uri)
            if token:
                await _update_env("TIKTOK_ACCESS_TOKEN", token)
                log_result("refresh_tiktok", True, "Token refreshed successfully")
                return {"success": True, "token_updated": True}
        log_result("refresh_tiktok", False, f"Could not extract code: {str(result)[:200]}")
        return {"success": False, "result": str(result)}
    except Exception as e:
        log_result("refresh_tiktok", False, str(e))
        return {"success": False, "error": str(e)}


async def _refresh_instagram(params: dict, past: str) -> dict:
    username = os.getenv("INSTAGRAM_USERNAME", "")
    password = os.getenv("INSTAGRAM_PASSWORD", "")

    task = f"""
You need to log into Instagram and verify the account is accessible.

Credentials: username="{username}", password="{password}"

{past}

Steps:
1. Navigate to https://www.instagram.com/accounts/login/
2. Log in with credentials
3. Once logged in, navigate to your profile
4. Extract any session cookies or access tokens from the browser storage
5. Return the session data

Note: Instagram's official API requires app review. We're checking if the browser session is active.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "logged" in str(result).lower() or "profile" in str(result).lower()
        log_result("refresh_instagram", success, str(result)[:200])
        return {"success": success, "result": str(result)[:300]}
    except Exception as e:
        log_result("refresh_instagram", False, str(e))
        return {"success": False, "error": str(e)}


async def _refresh_twitter(params: dict, past: str) -> dict:
    username = os.getenv("TWITTER_USERNAME", "")
    password = os.getenv("TWITTER_PASSWORD", "")
    client_id = os.getenv("TWITTER_CLIENT_ID", "")

    task = f"""
You need to refresh/verify a Twitter OAuth 2.0 token.

Twitter username: {username}
Password: {password}
Client ID: {client_id if client_id else "(not set — just verify login works)"}

{past}

Steps:
1. Navigate to https://twitter.com/login
2. Log in with credentials
3. Verify you can see the home feed
4. If a client_id is provided, navigate to the developer OAuth flow:
   https://twitter.com/i/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri=https://dominionhealing.org/twitter/callback&scope=tweet.read+tweet.write+users.read&state=state&code_challenge=challenge&code_challenge_method=plain
5. Return the authorization code or confirm login success

Report exact URL and any error messages.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        success = "success" in str(result).lower() or "logged" in str(result).lower()
        log_result("refresh_twitter", success, str(result)[:200])
        return {"success": success, "result": str(result)[:300]}
    except Exception as e:
        log_result("refresh_twitter", False, str(e))
        return {"success": False, "error": str(e)}


def _extract_code(text: str) -> str:
    match = re.search(r'code[=:]\s*([A-Za-z0-9_\-]+)', text)
    return match.group(1) if match else ""


async def _exchange_tiktok_code(code: str, client_key: str, redirect_uri: str) -> str:
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            data = resp.json()
            return data.get("access_token", "")
    except Exception:
        return ""


async def _update_env(key: str, value: str):
    """Write a new env var to the VM .env via baby-api."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BABY_API}/env/set",
                json={"key": key, "value": value},
            )
    except Exception:
        pass
