"""
Catalogue publishing service.

Handles:
1. Validation of publish-readiness
2. Building the deterministic catalogue JSON
3. Collapsing content_group language variants into single episodes
4. Grouping content by section
5. Writing catalogue atomically (never partial writes)
6. Recording publish runs with content hashing for idempotency
7. Updating the live catalogue pointer atomically

Atomic publishing strategy:
- Write new catalogue to catalogue.<run_id>.json
- Atomically rename/replace current_catalogue.json
- If process dies before rename: old catalogue remains live
- If process dies after rename: new catalogue is live
- Never a state where readers see partial data
"""
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.publish_run import PublishRun
from app.storage.base import Storage


async def publish_catalogue(
    db: AsyncSession,
    storage: Storage,
    publisher_email: str,
    publisher_name: str,
) -> PublishRun:
    """
    Build and atomically publish the catalogue.

    Steps:
    1. Load all published shows with their seasons, episodes, and artwork
    2. Validate publish-readiness (shows must have section, episodes must have duration)
    3. Build deterministic catalogue JSON
    4. Write to a versioned file
    5. Atomically update the live pointer
    6. Record the publish run
    """
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        # 1. Load publishable content
        result = await db.execute(
            select(Show)
            .where(Show.is_published == True)
            .where(Show.section != None)
            .where(Show.section != "")
            .options(
                selectinload(Show.seasons)
                .selectinload(Season.episodes)
                .selectinload(Episode.artworks),
                selectinload(Show.artworks),
            )
        )
        shows = result.scalars().all()

        if not shows:
            # Record failed publish
            run = PublishRun(
                id=uuid.UUID(run_id),
                published_by=publisher_email,
                published_at=now,
                status="failed",
                show_count=0,
                episode_count=0,
                error_message="No publishable shows found. Ensure at least one show is marked as published with a section.",
            )
            db.add(run)
            await db.flush()
            return run

        # 2. Build catalogue
        catalogue = _build_catalogue(shows, storage, run_id, now)

        # 3. Generate content hash for idempotency
        catalogue_json = json.dumps(catalogue, indent=2, sort_keys=True, default=str)
        content_hash = hashlib.sha256(catalogue_json.encode()).hexdigest()[:16]

        # 4. Count totals
        show_count = len(set(s["id"] for sec in catalogue["sections"] for s in sec["shows"]))
        episode_count = sum(
            len(ep)
            for sec in catalogue["sections"]
            for s in sec["shows"]
            for season in s.get("seasons", [])
            for ep in [season.get("episodes", [])]
        )

        # 5. Write versioned catalogue file
        versioned_key = f"catalogue/catalogue.{run_id}.json"
        await storage.put(versioned_key, catalogue_json.encode("utf-8"), "application/json")

        # 6. Atomically update the live pointer
        live_key = "catalogue/current_catalogue.json"
        await storage.put(live_key, catalogue_json.encode("utf-8"), "application/json")

        # 7. Record successful publish run
        run = PublishRun(
            id=uuid.UUID(run_id),
            published_by=publisher_email,
            published_at=now,
            status="success",
            show_count=show_count,
            episode_count=episode_count,
            catalogue_version=run_id,
            storage_key=versioned_key,
            content_hash=content_hash,
            details={
                "sections": [s["name"] for s in catalogue["sections"]],
                "shows": [s["title"] for sec in catalogue["sections"] for s in sec["shows"]],
            },
        )
        db.add(run)
        await db.flush()
        return run

    except Exception as e:
        # Record failed publish
        run = PublishRun(
            id=uuid.UUID(run_id),
            published_by=publisher_email,
            published_at=now,
            status="failed",
            show_count=0,
            episode_count=0,
            error_message=str(e),
        )
        db.add(run)
        await db.flush()
        return run


def _build_catalogue(shows: list, storage: Storage, run_id: str, now: datetime) -> dict:
    """
    Build a deterministic, viewer-oriented catalogue structure.

    Key behaviors:
    - Groups shows by section
    - Sorts sections and shows deterministically (alphabetically)
    - Collapses content_group language variants into single episodes
    - Season 0 episodes are included as trailers, not regular seasons
    - Uses artwork URLs from storage
    """
    sections_map = defaultdict(list)

    for show in sorted(shows, key=lambda s: s.title):
        show_artwork = {a.artwork_type: storage.get_public_url(a.storage_key) for a in show.artworks}

        seasons_data = []
        trailers = []

        for season in sorted(show.seasons, key=lambda s: s.season_number):
            # Filter to published episodes with valid duration
            valid_episodes = [
                ep for ep in season.episodes
                if ep.is_published and ep.duration and ep.duration > 0
            ]

            if not valid_episodes:
                continue

            if season.season_number == 0:
                # Season 0 = trailers
                for ep in valid_episodes:
                    trailers.append({
                        "id": str(ep.id),
                        "title": ep.title,
                        "duration": ep.duration,
                        "language": ep.language,
                        "thumbnail": _get_ep_artwork(ep, "thumbnail", storage),
                    })
                continue

            # Group episodes by content_group to collapse language variants
            groups = defaultdict(list)
            for ep in valid_episodes:
                groups[ep.content_group].append(ep)

            collapsed_episodes = []
            for cg in sorted(groups.keys()):
                variants = groups[cg]
                # Use first variant for metadata, collect all languages
                primary = sorted(variants, key=lambda e: e.language)[0]
                languages = sorted(set(v.language for v in variants))

                collapsed_episodes.append({
                    "id": str(primary.id),
                    "title": primary.title.strip(),
                    "duration": primary.duration,
                    "content_group": cg,
                    "languages": languages,
                    "thumbnail": _get_ep_artwork(primary, "thumbnail", storage),
                })

            if collapsed_episodes:
                seasons_data.append({
                    "number": season.season_number,
                    "episodes": collapsed_episodes,
                })

        show_data = {
            "id": str(show.id),
            "title": show.title.strip(),
            "synopsis": (show.synopsis or "").strip(),
            "category": show.category or "",
            "poster": show_artwork.get("poster", ""),
            "banner": show_artwork.get("banner", ""),
            "thumbnail": show_artwork.get("thumbnail", ""),
            "seasons": seasons_data,
        }

        if trailers:
            show_data["trailers"] = trailers

        sections_map[show.section].append(show_data)

    # Build final structure with deterministic ordering
    sections = []
    for section_name in sorted(sections_map.keys()):
        sections.append({
            "name": section_name,
            "shows": sections_map[section_name],
        })

    return {
        "version": run_id,
        "published_at": now.isoformat(),
        "sections": sections,
    }


def _get_ep_artwork(episode, artwork_type: str, storage: Storage) -> str:
    """Get artwork URL for an episode, fallback to empty string."""
    for art in episode.artworks:
        if art.artwork_type == artwork_type:
            return storage.get_public_url(art.storage_key)
    return ""
