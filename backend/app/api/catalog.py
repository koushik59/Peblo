"""
Public catalogue routes for the viewer.

These endpoints serve the published catalogue and search functionality.
They do NOT require authentication — the viewer is a public-facing app.
They do NOT access admin-only data or endpoints.
"""
import json
from typing import Optional, Annotated

from fastapi import APIRouter, Query, HTTPException
from app.storage import get_storage

router = APIRouter(prefix="/catalog", tags=["catalog"])


async def _load_catalogue() -> dict:
    """Load the current published catalogue from storage."""
    storage = get_storage()
    data = await storage.get("catalogue/current_catalogue.json")
    if not data:
        return {"version": "none", "published_at": None, "sections": []}
    return json.loads(data.decode("utf-8"))


@router.get("")
async def get_catalogue():
    """Return the full published catalogue."""
    return await _load_catalogue()


@router.get("/search")
async def search_catalogue(
    q: Annotated[Optional[str], Query(description="Search query matching show/episode titles and categories")] = None,
    category: Annotated[Optional[str], Query(description="Filter by category")] = None,
    language: Annotated[Optional[str], Query(description="Filter by language")] = None,
    section: Annotated[Optional[str], Query(description="Filter by section")] = None,
):
    """
    Search the published catalogue.

    Searches show titles, episode titles, and categories.
    Filters compose (AND logic): specifying both category and language
    returns only shows matching both criteria.

    Scale note: This searches the in-memory catalogue JSON, which is
    sufficient for small-to-medium catalogues (~1000 shows). For larger
    catalogues, consider PostgreSQL full-text search or Elasticsearch.
    """
    catalogue = await _load_catalogue()
    results = []

    # Clean inputs
    q_str = str(q).strip().lower() if q and isinstance(q, str) and str(q).strip() else None
    cat_str = str(category).strip().lower() if category and isinstance(category, str) and str(category).strip() else None
    lang_str = str(language).strip().lower() if language and isinstance(language, str) and str(language).strip() else None
    sec_str = str(section).strip().lower() if section and isinstance(section, str) and str(section).strip() else None

    for s in catalogue.get("sections", []):
        sec_name = s.get("name", "")
        # Section filter
        if sec_str and sec_name.lower() != sec_str:
            continue

        for show in s.get("shows", []):
            show_title = show.get("title", "")
            show_category = show.get("category", "")

            # Category filter
            if cat_str and show_category.lower() != cat_str:
                continue

            # Language filter - check if any episode or trailer has the language
            if lang_str:
                has_lang = False
                for season in show.get("seasons", []):
                    for ep in season.get("episodes", []):
                        ep_langs = [l.lower() for l in ep.get("languages", [])]
                        if lang_str in ep_langs:
                            has_lang = True
                            break
                    if has_lang:
                        break
                if not has_lang:
                    for trailer in show.get("trailers", []):
                        if trailer.get("language", "").lower() == lang_str:
                            has_lang = True
                            break
                if not has_lang:
                    continue

            # Text search
            if q_str:
                match = False
                # Match show title
                if q_str in show_title.lower():
                    match = True
                # Match category
                elif q_str in show_category.lower():
                    match = True
                # Match episode titles
                else:
                    for season in show.get("seasons", []):
                        for ep in season.get("episodes", []):
                            if q_str in ep.get("title", "").lower():
                                match = True
                                break
                        if match:
                            break
                if not match:
                    continue

            results.append({
                "show": show,
                "section": sec_name,
            })

    return {
        "query": q,
        "filters": {"category": category, "language": language, "section": section},
        "results": results,
        "total": len(results),
    }
