"""
External metadata enrichment.

TV shows  → TVMaze   (free, no API key, 20 req/10 s)
Movies    → TMDB     (free API key required: set TMDB_API_KEY in .env)

Both functions return None on any failure so callers can fall back gracefully.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

_TVMAZE_SEARCH = "https://api.tvmaze.com/singlesearch/shows"
_TMDB_SEARCH = "https://api.themoviedb.org/3/search/movie"


async def lookup_show(title: str) -> dict | None:
    """
    Search TVMaze for a TV show by title.
    Returns {"title": str, "year": int | None} or None.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_TVMAZE_SEARCH, params={"q": title})
            if resp.status_code != 200:
                return None
            data = resp.json()
            year: int | None = None
            if data.get("premiered"):
                year = int(data["premiered"][:4])
            return {"title": data["name"], "year": year}
    except Exception as exc:
        log.debug("TVMaze lookup failed for %r: %s", title, exc)
        return None


async def lookup_movie(title: str, year: int | None) -> dict | None:
    """
    Search TMDB for a movie by title (and optionally year).
    Returns {"title": str, "year": int | None} or None.
    No-ops silently when TMDB_API_KEY is not configured.
    """
    if not settings.tmdb_api_key:
        return None
    try:
        params: dict[str, str | int] = {
            "api_key": settings.tmdb_api_key,
            "query": title,
        }
        if year:
            params["year"] = year
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_TMDB_SEARCH, params=params)
            if resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            if not results:
                return None
            top = results[0]
            release_year: int | None = None
            if top.get("release_date"):
                release_year = int(top["release_date"][:4])
            return {"title": top["title"], "year": release_year}
    except Exception as exc:
        log.debug("TMDB lookup failed for %r: %s", title, exc)
        return None
