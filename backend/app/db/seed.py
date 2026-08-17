"""
Database seeding script.

Seeds:
1. Development users (admin, editor) with bcrypt-hashed passwords
2. Shows, seasons, and episodes from seed_shows.json (supports both flat and hierarchical formats)
3. Generates sample artwork images for seeded shows and episodes
4. Auto-publishes the catalogue so the Viewer is populated on startup

Runs idempotently — checks if data already exists before inserting.
"""
import json
import io
import uuid
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.artwork import Artwork
from app.auth.dependencies import hash_password
from app.storage.local import LocalStorage
from app.core.config import settings


def _find_file(filename: str) -> Path:
    candidates = [
        Path(filename),
        Path("/" + filename),
        Path("/app") / filename,
        Path(__file__).parent.parent.parent / filename,
        Path(__file__).parent.parent.parent.parent / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(filename)


SEED_PATH = _find_file("seed_shows.json")


def _generate_solid_jpeg(width: int, height: int, color: tuple = (100, 100, 200)) -> bytes:
    """Generate a minimal valid JPEG image for seeding."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return buf.getvalue()


async def run_seed(db: AsyncSession):
    """Seed the database with development data if empty."""

    # Check if already seeded
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return  # Already seeded

    print("[INFO] Seeding database...")

    # 1. Create users
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        role="admin",
        name="Admin User",
    )
    editor = User(
        email="editor@example.com",
        hashed_password=hash_password("editor123"),
        role="editor",
        name="Editor User",
    )
    db.add_all([admin, editor])
    await db.flush()
    print("  [OK] Users created")

    # 2. Load seed shows
    if not SEED_PATH.exists():
        print(f"  [WARN] seed_shows.json not found at {SEED_PATH}, skipping content seed")
        await db.commit()
        return

    with open(SEED_PATH) as f:
        seed_data = json.load(f)

    storage = LocalStorage(settings.storage_path)
    content_groups_seen = set()

    # Determine format: Flat list of episodes vs Hierarchical list of shows
    is_flat_format = isinstance(seed_data, list) and len(seed_data) > 0 and ("show_title" in seed_data[0] or "slug" in seed_data[0])

    if is_flat_format:
        # Group by show
        shows_grouped = defaultdict(lambda: {"metadata": {}, "seasons": defaultdict(list)})
        for entry in seed_data:
            slug = entry.get("slug") or entry.get("show_title", "untitled").lower().replace(" ", "-")
            if not shows_grouped[slug]["metadata"]:
                categories = entry.get("categories", [])
                primary_category = categories[0] if isinstance(categories, list) and categories else entry.get("category", "")
                shows_grouped[slug]["metadata"] = {
                    "title": entry.get("show_title", entry.get("title", "")),
                    "synopsis": entry.get("synopsis", ""),
                    "category": primary_category,
                    "section": entry.get("section", ""),
                }
            season_num = entry.get("season_number", 1)
            shows_grouped[slug]["seasons"][season_num].append({
                "title": entry.get("episode_title", entry.get("title", "")),
                "duration": entry.get("duration_seconds", entry.get("duration")),
                "content_group": entry.get("content_group", ""),
                "language": entry.get("language", "en"),
            })

        show_items = []
        for slug, sdata in shows_grouped.items():
            seasons_list = []
            for snum in sorted(sdata["seasons"].keys()):
                seasons_list.append({
                    "season_number": snum,
                    "episodes": sdata["seasons"][snum],
                })
            show_items.append({
                **sdata["metadata"],
                "seasons": seasons_list,
            })
    else:
        show_items = seed_data

    artwork_palette = [
        (80, 120, 180),
        (180, 100, 120),
        (100, 160, 120),
        (160, 140, 80),
        (140, 100, 180),
        (100, 160, 180),
        (180, 140, 100),
    ]

    for idx, show_data in enumerate(show_items):
        show = Show(
            title=show_data["title"],
            synopsis=show_data.get("synopsis", ""),
            category=show_data.get("category"),
            section=show_data.get("section") or None,
            is_published=True,  # Seed as published
        )
        db.add(show)
        await db.flush()

        base_color = artwork_palette[idx % len(artwork_palette)]

        # Generate show artwork (poster, banner, thumbnail)
        show_artwork_specs = [
            ("poster", 600, 900, base_color),
            ("banner", 1280, 720, (max(0, base_color[0] - 20), max(0, base_color[1] - 20), max(0, base_color[2] - 20))),
            ("thumbnail", 640, 360, (min(255, base_color[0] + 20), min(255, base_color[1] + 20), min(255, base_color[2] + 20))),
        ]
        for art_type, w, h, color in show_artwork_specs:
            img_data = _generate_solid_jpeg(w, h, color)
            key = f"artwork/shows/{show.id}/{art_type}.jpg"
            await storage.put(key, img_data, "image/jpeg")
            artwork = Artwork(
                show_id=show.id,
                artwork_type=art_type,
                storage_key=key,
                original_filename=f"{art_type}.jpg",
                content_type="image/jpeg",
                width=w,
                height=h,
                file_size=len(img_data),
            )
            db.add(artwork)

        # Seasons and episodes
        for season_data in show_data.get("seasons", []):
            season = Season(
                show_id=show.id,
                season_number=season_data["season_number"],
            )
            db.add(season)
            await db.flush()

            for ep_data in season_data.get("episodes", []):
                cg_key = (ep_data["content_group"], ep_data["language"])

                # Skip duplicates in seed data
                if cg_key in content_groups_seen:
                    print(f"  [WARN] Skipping duplicate (content_group, language): {cg_key}")
                    continue
                content_groups_seen.add(cg_key)

                episode = Episode(
                    season_id=season.id,
                    title=ep_data["title"],
                    duration=ep_data.get("duration"),
                    content_group=ep_data["content_group"],
                    language=ep_data["language"],
                    is_published=True,  # Seed as published
                )
                db.add(episode)
                await db.flush()

                # Generate episode artwork (poster, banner, thumbnail)
                ep_artwork_specs = [
                    ("poster", 600, 900, base_color),
                    ("banner", 1280, 720, base_color),
                    ("thumbnail", 640, 360, base_color),
                ]
                for art_type, w, h, color in ep_artwork_specs:
                    ep_img_data = _generate_solid_jpeg(w, h, color)
                    ep_key = f"artwork/episodes/{episode.id}/{art_type}.jpg"
                    await storage.put(ep_key, ep_img_data, "image/jpeg")
                    ep_art = Artwork(
                        episode_id=episode.id,
                        artwork_type=art_type,
                        storage_key=ep_key,
                        original_filename=f"{art_type}.jpg",
                        content_type="image/jpeg",
                        width=w,
                        height=h,
                        file_size=len(ep_img_data),
                    )
                    db.add(ep_art)

        await db.flush()

    await db.commit()
    print(f"  [OK] Seeded {len(show_items)} shows")

    # 3. Auto-publish catalogue so the Viewer has content on startup
    try:
        from app.services.publish_service import publish_catalogue
        run = await publish_catalogue(
            db=db,
            storage=storage,
            publisher_email="admin@example.com",
            publisher_name="Admin User",
        )
        await db.commit()
        if run.status == "success":
            print(f"  [OK] Auto-published catalogue ({run.show_count} shows, {run.episode_count} episodes)")
        else:
            print(f"  [WARN] Auto-publish failed: {run.error_message}")
    except Exception as e:
        print(f"  [ERROR] Auto-publish error: {e}")

    print("[INFO] Seeding complete!")
