"""
Real estate lead scraper — county tax deed auctions, Craigslist, Zillow off-market.
Results saved to vault via baby-api.
"""
import json
import os
from typing import Any, Dict

import httpx
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

from memory import get_context, log_result

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6-20251001")
BABY_API = os.getenv("BABY_API_URL", "http://baby-api:8080")

DEFAULT_COUNTIES = os.getenv("SCRAPE_COUNTIES", "pinellas,hillsborough,pasco")
DEFAULT_LEAD_TYPE = os.getenv("SCRAPE_LEAD_TYPE", "tax_deed")


def _llm():
    return ChatAnthropic(
        model_name=_MODEL,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )


async def scrape_leads(params: Dict[str, Any]) -> dict:
    """
    Scrape real estate leads from county sites, Craigslist, or Zillow.
    params: { county, lead_type, source }
    """
    county = params.get("county") or DEFAULT_COUNTIES.split(",")[0]
    lead_type = params.get("lead_type") or DEFAULT_LEAD_TYPE
    source = params.get("source") or "county"

    past = get_context(f"scrape_{lead_type}")

    if source == "craigslist" or lead_type == "craigslist":
        return await _scrape_craigslist(params, past)
    else:
        return await _scrape_county(county, lead_type, past)


async def _scrape_county(county: str, lead_type: str, past: str) -> dict:
    county_sites = {
        "pinellas": "https://www.pinellascounty.org/tax_collector/tax_deeds.htm",
        "hillsborough": "https://www.hillstax.org/tax-deeds/",
        "pasco": "https://www.pascoclerk.com/tax-deeds",
        "polk": "https://www.polktaxes.com/TaxDeeds",
        "orange": "https://myorangeclerk.com/tax-deeds",
    }
    url = county_sites.get(county.lower(), f"https://www.google.com/search?q={county}+county+tax+deed+auction+{lead_type}")

    task = f"""
You are a real estate investor scraping {lead_type} leads from {county} county.

Target URL: {url}

{past}

Steps:
1. Navigate to the URL
2. Find the list of upcoming {lead_type} properties
3. For each property, extract:
   - Property address
   - Opening bid / assessed value
   - Auction date
   - Property type (residential, commercial, land)
   - Parcel ID if available
4. Return the data as a JSON list like:
   [{{ "address": "...", "bid": "$...", "auction_date": "...", "type": "...", "parcel": "..." }}]

Focus on residential properties under $200,000 opening bid.
Skip commercial and vacant land unless under $50,000.
Extract at least 10 properties if available.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        leads = _parse_leads(str(result))
        await _save_leads(leads, county, lead_type)
        log_result(f"scrape_{lead_type}", True, f"Found {len(leads)} leads in {county}")
        return {"success": True, "leads_found": len(leads), "sample": leads[:3]}
    except Exception as e:
        log_result(f"scrape_{lead_type}", False, str(e))
        return {"success": False, "error": str(e)}


async def _scrape_craigslist(params: Dict[str, Any], past: str) -> dict:
    city = params.get("city") or "tampa"
    max_price = params.get("max_price") or 150000
    min_beds = params.get("min_beds") or 2

    task = f"""
You are a real estate investor finding motivated seller deals on Craigslist.

URL: https://{city}.craigslist.org/search/rea?max_price={max_price}&min_bedrooms={min_beds}

{past}

Steps:
1. Navigate to the Craigslist real estate for sale section
2. Browse listings looking for signs of motivated sellers:
   - "Must sell", "below market", "as-is", "cash only", "estate sale"
   - Properties priced below market
   - Unusual circumstances (divorce, foreclosure, relocation)
3. For each promising listing, extract:
   - Title, price, address/neighborhood, bedrooms/baths
   - Contact info if visible
   - Key phrases from description
4. Return as JSON list with fields: title, price, neighborhood, contact, notes

Focus on listings posted in the last 7 days.
"""
    try:
        agent = Agent(task=task, llm=_llm())
        result = await agent.run()
        leads = _parse_leads(str(result))
        await _save_leads(leads, city, "craigslist")
        log_result("scrape_craigslist", True, f"Found {len(leads)} Craigslist leads")
        return {"success": True, "leads_found": len(leads), "sample": leads[:3]}
    except Exception as e:
        log_result("scrape_craigslist", False, str(e))
        return {"success": False, "error": str(e)}


def _parse_leads(result_str: str) -> list:
    import re
    try:
        match = re.search(r'\[.*\]', result_str, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return [{"raw": result_str[:500]}]


async def _save_leads(leads: list, source: str, lead_type: str):
    if not leads:
        return
    content = f"Source: {source} | Type: {lead_type} | Count: {len(leads)}\n\n"
    content += json.dumps(leads, indent=2)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BABY_API}/vault/research",
                json={
                    "title": f"RE Leads: {source} {lead_type}",
                    "content": content,
                    "agent": "scraper-agent",
                    "tags": ["real-estate", "leads", source, lead_type],
                },
            )
    except Exception:
        pass
