"""
Tests for the catalogue publishing service.

Tests:
- Deterministic catalogue generation
- Language variant collapsing (content_group)
- Season 0 trailer handling
- Section grouping
- Publish run recording
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from collections import defaultdict

import pytest
from app.services.publish_service import _build_catalogue


class MockStorage:
    """Mock storage for testing."""
    def get_public_url(self, key):
        return f"/storage/{key}"


class MockArtwork:
    def __init__(self, artwork_type, storage_key):
        self.artwork_type = artwork_type
        self.storage_key = storage_key


class MockEpisode:
    def __init__(self, title, duration, content_group, language, is_published=True, artworks=None):
        self.id = uuid.uuid4()
        self.title = title
        self.duration = duration
        self.content_group = content_group
        self.language = language
        self.is_published = is_published
        self.artworks = artworks or []


class MockSeason:
    def __init__(self, season_number, episodes=None):
        self.id = uuid.uuid4()
        self.season_number = season_number
        self.episodes = episodes or []


class MockShow:
    def __init__(self, title, synopsis, category, section, seasons=None, artworks=None):
        self.id = uuid.uuid4()
        self.title = title
        self.synopsis = synopsis
        self.category = category
        self.section = section
        self.seasons = seasons or []
        self.artworks = artworks or []
        self.is_published = True


class TestCatalogueBuilding:

    def test_language_variant_collapsing(self):
        """Episodes with same content_group should collapse into one with multiple languages."""
        ep_en = MockEpisode("Episode 1", 2700, "ep1", "en")
        ep_hi = MockEpisode("Episode 1", 2700, "ep1", "hi")
        season = MockSeason(1, [ep_en, ep_hi])
        show = MockShow("Test Show", "Synopsis", "Drama", "Heroes", [season])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "test-run", datetime.now(timezone.utc))

        episodes = catalogue["sections"][0]["shows"][0]["seasons"][0]["episodes"]
        assert len(episodes) == 1  # Collapsed to one
        assert sorted(episodes[0]["languages"]) == ["en", "hi"]

    def test_season_0_becomes_trailers(self):
        """Season 0 episodes should appear as trailers, not regular seasons."""
        trailer = MockEpisode("Trailer", 120, "trailer-1", "en")
        regular = MockEpisode("Episode 1", 2700, "ep1", "en")
        season_0 = MockSeason(0, [trailer])
        season_1 = MockSeason(1, [regular])
        show = MockShow("Test Show", "Synopsis", "Drama", "Heroes", [season_0, season_1])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "test-run", datetime.now(timezone.utc))

        show_data = catalogue["sections"][0]["shows"][0]
        # Should have trailers
        assert "trailers" in show_data
        assert len(show_data["trailers"]) == 1
        assert show_data["trailers"][0]["title"] == "Trailer"
        # Regular seasons should not include season 0
        assert all(s["number"] != 0 for s in show_data["seasons"])
        assert len(show_data["seasons"]) == 1
        assert show_data["seasons"][0]["number"] == 1

    def test_deterministic_ordering(self):
        """Running build twice with same data should produce identical output."""
        ep1 = MockEpisode("B Episode", 2700, "ep-b", "en")
        ep2 = MockEpisode("A Episode", 2700, "ep-a", "en")
        season = MockSeason(1, [ep1, ep2])
        show_b = MockShow("B Show", "Synopsis B", "Comedy", "Trending", [season])

        ep3 = MockEpisode("C Episode", 2700, "ep-c", "en")
        season2 = MockSeason(1, [ep3])
        show_a = MockShow("A Show", "Synopsis A", "Drama", "Heroes", [season2])

        storage = MockStorage()
        now = datetime(2024, 1, 1, tzinfo=timezone.utc)

        cat1 = _build_catalogue([show_b, show_a], storage, "run1", now)
        cat2 = _build_catalogue([show_a, show_b], storage, "run1", now)

        # Same structure regardless of input order
        json1 = json.dumps(cat1, sort_keys=True, default=str)
        json2 = json.dumps(cat2, sort_keys=True, default=str)
        assert json1 == json2

    def test_section_grouping(self):
        """Shows should be grouped by section."""
        show1 = MockShow("Show A", "Syn", "Drama", "Heroes")
        show2 = MockShow("Show B", "Syn", "Comedy", "Trending")
        show3 = MockShow("Show C", "Syn", "Action", "Heroes")

        storage = MockStorage()
        catalogue = _build_catalogue([show1, show2, show3], storage, "run", datetime.now(timezone.utc))

        section_names = [s["name"] for s in catalogue["sections"]]
        assert "Heroes" in section_names
        assert "Trending" in section_names

        heroes = next(s for s in catalogue["sections"] if s["name"] == "Heroes")
        assert len(heroes["shows"]) == 2

    def test_unpublished_episodes_excluded(self):
        """Unpublished episodes should not appear in the catalogue."""
        pub_ep = MockEpisode("Published", 2700, "ep1", "en", is_published=True)
        unpub_ep = MockEpisode("Unpublished", 2700, "ep2", "en", is_published=False)
        season = MockSeason(1, [pub_ep, unpub_ep])
        show = MockShow("Test", "Syn", "Drama", "Heroes", [season])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "run", datetime.now(timezone.utc))

        episodes = catalogue["sections"][0]["shows"][0]["seasons"][0]["episodes"]
        assert len(episodes) == 1
        assert episodes[0]["title"] == "Published"

    def test_episodes_with_no_duration_excluded(self):
        """Episodes without duration should be excluded from catalogue."""
        valid_ep = MockEpisode("Valid", 2700, "ep1", "en")
        no_dur = MockEpisode("No Duration", None, "ep2", "en")
        neg_dur = MockEpisode("Negative", -300, "ep3", "en")
        season = MockSeason(1, [valid_ep, no_dur, neg_dur])
        show = MockShow("Test", "Syn", "Drama", "Heroes", [season])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "run", datetime.now(timezone.utc))

        episodes = catalogue["sections"][0]["shows"][0]["seasons"][0]["episodes"]
        assert len(episodes) == 1
        assert episodes[0]["title"] == "Valid"

    def test_whitespace_stripped_from_titles(self):
        """Leading/trailing whitespace should be stripped from titles."""
        ep = MockEpisode("  Spaced Title  ", 2700, "ep1", "en")
        season = MockSeason(1, [ep])
        show = MockShow("  Show Name  ", "Syn", "Drama", "Heroes", [season])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "run", datetime.now(timezone.utc))

        assert catalogue["sections"][0]["shows"][0]["title"] == "Show Name"
        assert catalogue["sections"][0]["shows"][0]["seasons"][0]["episodes"][0]["title"] == "Spaced Title"

    def test_empty_catalogue(self):
        """Building with no shows should produce empty sections."""
        storage = MockStorage()
        catalogue = _build_catalogue([], storage, "run", datetime.now(timezone.utc))
        assert catalogue["sections"] == []

    def test_three_language_variants(self):
        """Three language variants of same episode should collapse properly."""
        ep_en = MockEpisode("Ep 1", 2700, "ep1", "en")
        ep_hi = MockEpisode("Ep 1", 2700, "ep1", "hi")
        ep_ta = MockEpisode("Ep 1", 2700, "ep1", "ta")
        season = MockSeason(1, [ep_en, ep_hi, ep_ta])
        show = MockShow("Test", "Syn", "Drama", "Heroes", [season])

        storage = MockStorage()
        catalogue = _build_catalogue([show], storage, "run", datetime.now(timezone.utc))

        episodes = catalogue["sections"][0]["shows"][0]["seasons"][0]["episodes"]
        assert len(episodes) == 1
        assert episodes[0]["languages"] == ["en", "hi", "ta"]
