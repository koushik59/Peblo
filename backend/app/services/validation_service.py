"""
Validation report service.

Scans all shows, seasons, and episodes in the database and identifies
issues that would block publishing. Returns a structured report that
the CMS can display to content editors.
"""
import json
from pathlib import Path
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.artwork import Artwork
from app.schemas.schemas import ValidationIssue, ValidationReport

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

REFERENCE_PATH = _find_file("reference.json")

VALID_LANGUAGES = {"en", "hi", "ta", "te", "kn"}


def _load_reference():
    if REFERENCE_PATH.exists():
        with open(REFERENCE_PATH) as f:
            return json.load(f)
    return {"sections": ["featured", "series", "minisodes", "songs"],
            "categories": ["adventure", "folk", "friendship", "india", "language", "learning", "maths", "music", "nature", "reading", "science", "singalong", "stories", "travel", "values"],
            "languages": ["en", "hi", "ta", "te", "kn"]}


async def generate_validation_report(db: AsyncSession) -> ValidationReport:
    """Generate a comprehensive validation report for all content."""
    ref = _load_reference()
    valid_categories = set(ref.get("categories", []))
    valid_sections = set(ref.get("sections", []))
    issues: List[ValidationIssue] = []

    # Load all shows with seasons, episodes, and artwork
    result = await db.execute(
        select(Show)
        .options(
            selectinload(Show.seasons)
            .selectinload(Season.episodes)
            .selectinload(Episode.artworks),
            selectinload(Show.artworks),
        )
    )
    shows = result.scalars().all()

    show_errors = 0
    episode_errors = 0
    artwork_warnings = 0
    content_group_seen = {}  # track (content_group, language) duplicates

    for show in shows:
        # Check show-level issues
        if not show.title or not show.title.strip():
            issues.append(ValidationIssue(
                severity="error", entity_type="show", entity_id=str(show.id),
                entity_name=show.title or "(untitled)",
                field="title", message="Show has no title.",
                how_to_fix="Add a title in the show editor."
            ))
            show_errors += 1

        if show.title and show.title != show.title.strip():
            issues.append(ValidationIssue(
                severity="warning", entity_type="show", entity_id=str(show.id),
                entity_name=show.title,
                field="title",
                message=f"Show title has leading/trailing whitespace: '{show.title}'.",
                how_to_fix="Edit the show and remove extra spaces from the title."
            ))

        if not show.section or not show.section.strip():
            issues.append(ValidationIssue(
                severity="error", entity_type="show", entity_id=str(show.id),
                entity_name=show.title,
                field="section", message="Show has no section assigned.",
                how_to_fix="Edit the show and select a section (e.g. 'featured', 'series')."
            ))
            show_errors += 1

        if show.section and show.section.strip() and show.section not in valid_sections:
            issues.append(ValidationIssue(
                severity="warning", entity_type="show", entity_id=str(show.id),
                entity_name=show.title,
                field="section",
                message=f"Section '{show.section}' is not in the standard list: {', '.join(sorted(valid_sections))}.",
                how_to_fix="Edit the show and choose a recognized section."
            ))

        if not show.synopsis or not show.synopsis.strip():
            issues.append(ValidationIssue(
                severity="warning", entity_type="show", entity_id=str(show.id),
                entity_name=show.title,
                field="synopsis", message="Show has an empty synopsis.",
                how_to_fix="Add a description in the show editor."
            ))

        if show.category and show.category not in valid_categories:
            issues.append(ValidationIssue(
                severity="warning", entity_type="show", entity_id=str(show.id),
                entity_name=show.title,
                field="category",
                message=f"Category '{show.category}' is not recognized. Valid categories: {', '.join(sorted(valid_categories))}.",
                how_to_fix="Edit the show and choose a valid category."
            ))

        # Check show artwork
        show_artwork_types = {a.artwork_type for a in show.artworks}
        for needed in ["poster", "banner", "thumbnail"]:
            if needed not in show_artwork_types:
                issues.append(ValidationIssue(
                    severity="error", entity_type="show", entity_id=str(show.id),
                    entity_name=show.title,
                    field="artwork",
                    message=f"Show is missing {needed} artwork.",
                    how_to_fix=f"Upload a {needed} image in the show editor."
                ))
                show_errors += 1

        # Check episodes
        for season in show.seasons:
            for ep_idx, episode in enumerate(season.episodes, 1):
                ep_label = f"'{episode.title}' (S{season.season_number})"

                if episode.title and episode.title != episode.title.strip():
                    issues.append(ValidationIssue(
                        severity="warning", entity_type="episode", entity_id=str(episode.id),
                        entity_name=ep_label,
                        field="title",
                        message=f"Episode title has leading/trailing whitespace: '{episode.title}'.",
                        how_to_fix="Edit the episode and remove extra spaces from the title."
                    ))

                if episode.duration is None:
                    issues.append(ValidationIssue(
                        severity="error", entity_type="episode", entity_id=str(episode.id),
                        entity_name=ep_label,
                        field="duration",
                        message=f"Episode {ep_label} has no duration set.",
                        how_to_fix="Edit the episode and enter the duration in seconds."
                    ))
                    episode_errors += 1
                elif episode.duration <= 0:
                    issues.append(ValidationIssue(
                        severity="error", entity_type="episode", entity_id=str(episode.id),
                        entity_name=ep_label,
                        field="duration",
                        message=f"Episode {ep_label} has invalid duration: {episode.duration}s.",
                        how_to_fix="Edit the episode and enter a positive duration in seconds."
                    ))
                    episode_errors += 1

                if episode.language not in VALID_LANGUAGES:
                    issues.append(ValidationIssue(
                        severity="error", entity_type="episode", entity_id=str(episode.id),
                        entity_name=ep_label,
                        field="language",
                        message=f"Episode {ep_label} has unrecognized language code: '{episode.language}'. "
                                f"Valid codes: {', '.join(sorted(VALID_LANGUAGES))}.",
                        how_to_fix="Edit the episode and select a supported language."
                    ))
                    episode_errors += 1

                # Track content_group+language for duplicates
                cg_key = (episode.content_group, episode.language)
                if cg_key in content_group_seen:
                    other_id = content_group_seen[cg_key]
                    issues.append(ValidationIssue(
                        severity="error", entity_type="episode", entity_id=str(episode.id),
                        entity_name=ep_label,
                        field="content_group",
                        message=f"Duplicate (content_group, language) combination: "
                                f"'{episode.content_group}' + '{episode.language}'. "
                                f"Another episode already uses this combination.",
                        how_to_fix="Change the content_group or language of one of the duplicate episodes."
                    ))
                    episode_errors += 1
                else:
                    content_group_seen[cg_key] = str(episode.id)

                # Check episode artwork
                ep_artwork_types = {a.artwork_type for a in episode.artworks}
                if season.season_number == 0:
                    needed_ep_art = ["thumbnail"]
                else:
                    needed_ep_art = ["banner", "poster", "thumbnail"]
                missing_ep_art = [t for t in needed_ep_art if t not in ep_artwork_types]
                if missing_ep_art:
                    display_name = f'"{show.title}" S{season.season_number}E{ep_idx} "{episode.title}" ({episode.language})'
                    issues.append(ValidationIssue(
                        severity="error",
                        entity_type="episode",
                        entity_id=str(episode.id),
                        entity_name=display_name,
                        field="artwork",
                        message=f'{display_name} is missing artwork: {", ".join(sorted(missing_ep_art))}. Upload it before publishing.',
                        how_to_fix=f"Upload {', '.join(sorted(missing_ep_art))} artwork before publishing.",
                    ))
                    episode_errors += 1

    has_blockers = show_errors > 0 or episode_errors > 0
    summary = {
        "total_shows": len(shows),
        "show_errors": show_errors,
        "episode_errors": episode_errors,
        "artwork_warnings": artwork_warnings,
        "total_issues": len(issues),
        "blocking_issues": sum(1 for i in issues if i.severity == "error"),
        "warning_issues": sum(1 for i in issues if i.severity == "warning"),
    }

    return ValidationReport(has_blockers=has_blockers, issues=issues, summary=summary)
