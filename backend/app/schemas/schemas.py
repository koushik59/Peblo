"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    name: str
    role: str


# --- Artwork ---
class ArtworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    artwork_type: str
    storage_key: str
    original_filename: str
    content_type: str
    width: int
    height: int
    file_size: int
    url: Optional[str] = None
    created_at: datetime


# --- Episode ---
class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    duration: Optional[int] = None
    content_group: str = Field(..., min_length=1, max_length=200)
    language: str = Field(..., min_length=2, max_length=10)
    is_published: bool = False


class EpisodeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    duration: Optional[int] = None
    content_group: Optional[str] = Field(None, min_length=1, max_length=200)
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    is_published: Optional[bool] = None


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    season_id: UUID
    title: str
    duration: Optional[int]
    content_group: str
    language: str
    is_published: bool
    artworks: List[ArtworkResponse] = []
    created_at: datetime
    updated_at: datetime


# --- Season ---
class SeasonCreate(BaseModel):
    season_number: int = Field(..., ge=0)


class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    show_id: UUID
    season_number: int
    episodes: List[EpisodeResponse] = []
    created_at: datetime


# --- Show ---
class ShowCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    synopsis: Optional[str] = ""
    category: Optional[str] = None
    section: Optional[str] = None
    is_published: bool = False


class ShowUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    synopsis: Optional[str] = None
    category: Optional[str] = None
    section: Optional[str] = None
    is_published: Optional[bool] = None


class ShowListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    synopsis: Optional[str]
    category: Optional[str]
    section: Optional[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime
    artworks: List[ArtworkResponse] = []


class ShowDetailResponse(ShowListResponse):
    seasons: List[SeasonResponse] = []


# --- Pagination ---
class PaginatedResponse(BaseModel):
    items: List = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


# --- Validation Report ---
class ValidationIssue(BaseModel):
    severity: str  # "error" (blocks publish) or "warning"
    entity_type: str  # "show", "episode", "artwork"
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    field: Optional[str] = None
    message: str
    how_to_fix: str


class ValidationReport(BaseModel):
    has_blockers: bool
    issues: List[ValidationIssue]
    summary: dict


# --- Publish ---
class PublishRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    published_by: str
    published_at: datetime
    status: str
    show_count: int
    episode_count: int
    catalogue_version: Optional[str]
    content_hash: Optional[str]
    error_message: Optional[str]
    details: Optional[dict]


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    database: str
    storage: str
    version: str = "1.0.0"
