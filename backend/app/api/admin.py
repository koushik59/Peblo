"""Admin routes for shows, seasons, episodes, artwork, validation, and publishing."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.show import Show
from app.models.season import Season
from app.models.episode import Episode
from app.models.artwork import Artwork
from app.models.user import User
from app.models.publish_run import PublishRun
from app.auth.dependencies import get_current_user, require_role
from app.schemas.schemas import (
    ShowCreate, ShowUpdate, ShowListResponse, ShowDetailResponse,
    SeasonCreate, SeasonResponse,
    EpisodeCreate, EpisodeUpdate, EpisodeResponse,
    ArtworkResponse,
    PaginatedResponse,
    ValidationReport,
    PublishRunResponse,
)
from app.services.artwork_service import validate_artwork
from app.services.validation_service import generate_validation_report
from app.services.publish_service import publish_catalogue
from app.storage import get_storage

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Shows ---

@router.get("/shows", response_model=PaginatedResponse)
async def list_shows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = None,
    section: Optional[str] = None,
    category: Optional[str] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Show).options(selectinload(Show.artworks))
    count_query = select(func.count(Show.id))

    if q:
        query = query.where(Show.title.ilike(f"%{q}%"))
        count_query = count_query.where(Show.title.ilike(f"%{q}%"))
    if section:
        query = query.where(Show.section == section)
        count_query = count_query.where(Show.section == section)
    if category:
        query = query.where(Show.category == category)
        count_query = count_query.where(Show.category == category)
    if is_published is not None:
        query = query.where(Show.is_published == is_published)
        count_query = count_query.where(Show.is_published == is_published)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Show.title).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    shows = result.scalars().all()

    items = []
    storage = get_storage()
    for show in shows:
        show_dict = ShowListResponse.model_validate(show).model_dump()
        for art in show_dict.get("artworks", []):
            art["url"] = storage.get_public_url(art["storage_key"])
        items.append(show_dict)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.post("/shows", response_model=ShowListResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    body: ShowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    show = Show(
        title=body.title.strip(),
        synopsis=body.synopsis or "",
        category=body.category,
        section=body.section,
        is_published=body.is_published,
    )
    db.add(show)
    await db.flush()
    await db.refresh(show, attribute_names=["artworks"])
    return ShowListResponse.model_validate(show)


@router.get("/shows/{show_id}", response_model=ShowDetailResponse)
async def get_show(
    show_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Show)
        .where(Show.id == show_id)
        .options(
            selectinload(Show.seasons).selectinload(Season.episodes).selectinload(Episode.artworks),
            selectinload(Show.artworks),
        )
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    response = ShowDetailResponse.model_validate(show)
    storage = get_storage()
    # Add URLs to artworks
    response_dict = response.model_dump()
    for art in response_dict.get("artworks", []):
        art["url"] = storage.get_public_url(art["storage_key"])
    for season in response_dict.get("seasons", []):
        for ep in season.get("episodes", []):
            for art in ep.get("artworks", []):
                art["url"] = storage.get_public_url(art["storage_key"])
    return response_dict


@router.patch("/shows/{show_id}", response_model=ShowListResponse)
async def update_show(
    show_id: uuid.UUID,
    body: ShowUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Show).where(Show.id == show_id).options(selectinload(Show.artworks))
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    update_data = body.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()

    for key, value in update_data.items():
        setattr(show, key, value)

    await db.flush()
    await db.refresh(show, attribute_names=["artworks"])
    return ShowListResponse.model_validate(show)


@router.delete("/shows/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_show(
    show_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    await db.delete(show)
    await db.flush()


# --- Seasons ---

@router.get("/shows/{show_id}/seasons", response_model=list[SeasonResponse])
async def list_seasons(
    show_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Season)
        .where(Season.show_id == show_id)
        .options(selectinload(Season.episodes).selectinload(Episode.artworks))
        .order_by(Season.season_number)
    )
    seasons = result.scalars().all()
    storage = get_storage()
    response = []
    for s in seasons:
        s_dict = SeasonResponse.model_validate(s).model_dump()
        for ep in s_dict.get("episodes", []):
            for art in ep.get("artworks", []):
                art["url"] = storage.get_public_url(art["storage_key"])
        response.append(s_dict)
    return response


@router.post("/shows/{show_id}/seasons", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: uuid.UUID,
    body: SeasonCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify show exists
    show_result = await db.execute(select(Show).where(Show.id == show_id))
    if not show_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Show not found")

    # Check for duplicate season number
    existing = await db.execute(
        select(Season).where(Season.show_id == show_id, Season.season_number == body.season_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Season {body.season_number} already exists for this show")

    season = Season(show_id=show_id, season_number=body.season_number)
    db.add(season)
    await db.flush()
    await db.refresh(season, attribute_names=["episodes"])
    return SeasonResponse.model_validate(season)


# --- Episodes ---

@router.get("/seasons/{season_id}/episodes", response_model=list[EpisodeResponse])
async def list_episodes(
    season_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Episode)
        .where(Episode.season_id == season_id)
        .options(selectinload(Episode.artworks))
        .order_by(Episode.title)
    )
    episodes = result.scalars().all()
    storage = get_storage()
    response = []
    for ep in episodes:
        ep_dict = EpisodeResponse.model_validate(ep).model_dump()
        for art in ep_dict.get("artworks", []):
            art["url"] = storage.get_public_url(art["storage_key"])
        response.append(ep_dict)
    return response


@router.post("/seasons/{season_id}/episodes", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    season_id: uuid.UUID,
    body: EpisodeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify season exists
    season_result = await db.execute(select(Season).where(Season.id == season_id))
    if not season_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Season not found")

    # Check content_group+language uniqueness
    existing = await db.execute(
        select(Episode).where(
            Episode.content_group == body.content_group,
            Episode.language == body.language,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"An episode with content_group '{body.content_group}' and language '{body.language}' already exists."
        )

    episode = Episode(
        season_id=season_id,
        title=body.title.strip(),
        duration=body.duration,
        content_group=body.content_group,
        language=body.language,
        is_published=body.is_published,
    )
    db.add(episode)
    await db.flush()
    await db.refresh(episode, attribute_names=["artworks"])
    return EpisodeResponse.model_validate(episode)


@router.patch("/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: uuid.UUID,
    body: EpisodeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Episode).where(Episode.id == episode_id).options(selectinload(Episode.artworks))
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    update_data = body.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()

    # Check content_group+language uniqueness if either is being changed
    new_cg = update_data.get("content_group", episode.content_group)
    new_lang = update_data.get("language", episode.language)
    if new_cg != episode.content_group or new_lang != episode.language:
        existing = await db.execute(
            select(Episode).where(
                Episode.content_group == new_cg,
                Episode.language == new_lang,
                Episode.id != episode_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"An episode with content_group '{new_cg}' and language '{new_lang}' already exists."
            )

    for key, value in update_data.items():
        setattr(episode, key, value)

    await db.flush()
    await db.refresh(episode, attribute_names=["artworks"])
    return EpisodeResponse.model_validate(episode)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    await db.delete(episode)
    await db.flush()


# --- Artwork Upload ---

@router.post("/shows/{show_id}/artwork", response_model=ArtworkResponse)
async def upload_show_artwork(
    show_id: uuid.UUID,
    artwork_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify show exists
    show_result = await db.execute(select(Show).where(Show.id == show_id))
    if not show_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Show not found")

    file_data = await file.read()
    is_valid, error_msg, dimensions = validate_artwork(
        file_data, file.content_type, artwork_type, file.filename
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Delete existing artwork of same type for this show
    existing = await db.execute(
        select(Artwork).where(Artwork.show_id == show_id, Artwork.artwork_type == artwork_type)
    )
    old = existing.scalar_one_or_none()
    if old:
        storage = get_storage()
        await storage.delete(old.storage_key)
        await db.delete(old)

    # Store new artwork
    storage = get_storage()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    storage_key = f"artwork/shows/{show_id}/{artwork_type}.{ext}"
    await storage.put(storage_key, file_data, file.content_type)

    artwork = Artwork(
        show_id=show_id,
        artwork_type=artwork_type,
        storage_key=storage_key,
        original_filename=file.filename,
        content_type=file.content_type,
        width=dimensions[0],
        height=dimensions[1],
        file_size=len(file_data),
    )
    db.add(artwork)
    await db.flush()

    response = ArtworkResponse.model_validate(artwork)
    response.url = storage.get_public_url(storage_key)
    return response


@router.post("/episodes/{episode_id}/artwork", response_model=ArtworkResponse)
async def upload_episode_artwork(
    episode_id: uuid.UUID,
    artwork_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify episode exists
    ep_result = await db.execute(select(Episode).where(Episode.id == episode_id))
    if not ep_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Episode not found")

    file_data = await file.read()
    is_valid, error_msg, dimensions = validate_artwork(
        file_data, file.content_type, artwork_type, file.filename
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Delete existing artwork of same type for this episode
    existing = await db.execute(
        select(Artwork).where(Artwork.episode_id == episode_id, Artwork.artwork_type == artwork_type)
    )
    old = existing.scalar_one_or_none()
    if old:
        storage = get_storage()
        await storage.delete(old.storage_key)
        await db.delete(old)

    storage = get_storage()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    storage_key = f"artwork/episodes/{episode_id}/{artwork_type}.{ext}"
    await storage.put(storage_key, file_data, file.content_type)

    artwork = Artwork(
        episode_id=episode_id,
        artwork_type=artwork_type,
        storage_key=storage_key,
        original_filename=file.filename,
        content_type=file.content_type,
        width=dimensions[0],
        height=dimensions[1],
        file_size=len(file_data),
    )
    db.add(artwork)
    await db.flush()

    response = ArtworkResponse.model_validate(artwork)
    response.url = storage.get_public_url(storage_key)
    return response


# --- Validation Report ---

@router.get("/validation-report", response_model=ValidationReport)
async def get_validation_report(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await generate_validation_report(db)


# --- Publishing ---

@router.post("/catalog/publish", response_model=PublishRunResponse)
async def publish(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """Publish the catalogue. Requires admin role."""
    storage = get_storage()
    run = await publish_catalogue(db, storage, user.email, user.name)
    return PublishRunResponse.model_validate(run)


@router.get("/publish-runs", response_model=list[PublishRunResponse])
async def list_publish_runs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PublishRun).order_by(PublishRun.published_at.desc()).limit(50)
    )
    return [PublishRunResponse.model_validate(r) for r in result.scalars().all()]
