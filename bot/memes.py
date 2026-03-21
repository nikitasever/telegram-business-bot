"""Fetch memes from free APIs."""

import logging
import random

import aiohttp

logger = logging.getLogger(__name__)

# Imgflip popular meme templates with IDs
MEME_TEMPLATES = {
    "waiting": "89370399",       # Ill Just Wait Here
    "success": "61544",          # Success Kid
    "confused": "101288",        # Third World Skeptical Kid
    "fine": "55311130",          # This Is Fine
    "thinking": "217743513",     # UNO Draw 25 Cards
    "surprised": "27813981",     # Hide the Pain Harold
    "sad": "61539",             # First World Problems
    "angry": "97984",           # Disaster Girl
    "happy": "61520",           # Futurama Fry
    "awkward": "100777631",     # Is This A Pigeon
    "smart": "247375501",       # Buff Doge vs Cheems
    "money": "135256802",       # Epic Handshake
    "lazy": "196652226",        # Spongebob Ight Imma Head Out
    "fear": "252600902",        # Always Has Been
    "work": "93895088",         # Expanding Brain
    "love": "188390779",        # Woman Yelling At Cat
    "pain": "259237855",        # Crying Cat
    "vibe": "322841258",        # Anakin Padme 4 Panel
    "ok": "181913649",          # Drake Hotline Bling
    "what": "124822590",        # Left Exit 12 Off Ramp
    "bruh": "259680400",        # Megamind no bitches
    "relax": "224015000",       # Bernie I Am Once Again Asking
    "lol": "438680",           # Batman Slapping Robin
}


async def fetch_meme_url(query: str) -> str | None:
    """Get a meme image URL based on the query/topic."""
    try:
        # Try to match a known template
        query_lower = query.lower().strip()
        template_id = MEME_TEMPLATES.get(query_lower)

        if template_id:
            # Use Imgflip API to get template image
            url = f"https://imgflip.com/s/meme/{template_id}.jpg"
            # Just return the direct image URL
            return f"https://i.imgflip.com/{template_id}.jpg"

        # Fallback: fetch random meme from meme-api
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://meme-api.com/gimme",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    meme_url = data.get("url")
                    if meme_url:
                        logger.info("Fetched meme: %s", meme_url)
                        return meme_url

        return None
    except Exception as e:
        logger.warning("Failed to fetch meme: %s", e)
        return None


async def download_meme(url: str) -> bytes | None:
    """Download meme image bytes from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    logger.info("Downloaded meme: %d bytes", len(data))
                    return data
        return None
    except Exception as e:
        logger.warning("Failed to download meme: %s", e)
        return None
