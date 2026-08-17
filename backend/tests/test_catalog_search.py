"""
Unit tests for Catalogue Search logic.

Tests:
- Search by show title
- Search by episode title
- Search by category
- Filter by category
- Filter by language (including multi-language variants)
- Filter by section
- Composition of multiple filters simultaneously
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.api.catalog import search_catalogue

MOCK_CATALOGUE = {
    "version": "test-v1",
    "published_at": "2026-08-15T12:00:00Z",
    "sections": [
        {
            "name": "Heroes",
            "shows": [
                {
                    "id": "show-1",
                    "title": "The Great Adventure",
                    "category": "Drama",
                    "poster": "/storage/poster1.jpg",
                    "banner": "/storage/banner1.jpg",
                    "thumbnail": "/storage/thumb1.jpg",
                    "seasons": [
                        {
                            "number": 1,
                            "episodes": [
                                {
                                    "id": "ep-1",
                                    "title": "The Beginning",
                                    "duration": 2700,
                                    "languages": ["en", "hi"],
                                },
                                {
                                    "id": "ep-2",
                                    "title": "Into the Wild",
                                    "duration": 2850,
                                    "languages": ["en"],
                                }
                            ]
                        }
                    ],
                    "trailers": [
                        {
                            "id": "tr-1",
                            "title": "Official Trailer",
                            "duration": 120,
                            "language": "en"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Trending",
            "shows": [
                {
                    "id": "show-2",
                    "title": "Comedy Central Hour",
                    "category": "Comedy",
                    "poster": "/storage/poster2.jpg",
                    "banner": "/storage/banner2.jpg",
                    "thumbnail": "/storage/thumb2.jpg",
                    "seasons": [
                        {
                            "number": 1,
                            "episodes": [
                                {
                                    "id": "ep-3",
                                    "title": "The Roast",
                                    "duration": 1800,
                                    "languages": ["en", "hi"],
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


class TestCatalogSearch:

    @pytest.mark.asyncio
    async def test_search_by_show_title(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            res = await search_catalogue(q="Adventure")
            assert res["total"] == 1
            assert res["results"][0]["show"]["title"] == "The Great Adventure"

    @pytest.mark.asyncio
    async def test_search_by_episode_title(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            res = await search_catalogue(q="Roast")
            assert res["total"] == 1
            assert res["results"][0]["show"]["title"] == "Comedy Central Hour"

    @pytest.mark.asyncio
    async def test_filter_by_category(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            res = await search_catalogue(category="Comedy")
            assert res["total"] == 1
            assert res["results"][0]["show"]["title"] == "Comedy Central Hour"

    @pytest.mark.asyncio
    async def test_filter_by_language(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            res = await search_catalogue(language="hi")
            # Both shows have hindi audio
            assert res["total"] == 2

            res_ta = await search_catalogue(language="ta")
            assert res_ta["total"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_section(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            res = await search_catalogue(section="Trending")
            assert res["total"] == 1
            assert res["results"][0]["show"]["title"] == "Comedy Central Hour"

    @pytest.mark.asyncio
    async def test_filter_composition(self):
        with patch("app.api.catalog._load_catalogue", AsyncMock(return_value=MOCK_CATALOGUE)):
            # Compose category=Drama and language=hi
            res = await search_catalogue(category="Drama", language="hi")
            assert res["total"] == 1
            assert res["results"][0]["show"]["title"] == "The Great Adventure"

            # Compose category=Comedy and section=Heroes (contradictory -> 0 results)
            res_none = await search_catalogue(category="Comedy", section="Heroes")
            assert res_none["total"] == 0
