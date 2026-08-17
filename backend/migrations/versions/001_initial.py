"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='editor'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )

    # Shows
    op.create_table(
        'shows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('synopsis', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('is_published', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shows_title', 'shows', ['title'])
    op.create_index('ix_shows_section', 'shows', ['section'])
    op.create_index('ix_shows_category', 'shows', ['category'])
    op.create_index('ix_shows_is_published', 'shows', ['is_published'])

    # Seasons
    op.create_table(
        'seasons',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('show_id', sa.Uuid(), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['show_id'], ['shows.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('show_id', 'season_number', name='uq_show_season_number'),
    )

    # Episodes
    op.create_table(
        'episodes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('season_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('content_group', sa.String(200), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('is_published', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('content_group', 'language', name='uq_content_group_language'),
    )
    op.create_index('ix_episodes_title', 'episodes', ['title'])
    op.create_index('ix_episodes_content_group', 'episodes', ['content_group'])
    op.create_index('ix_episodes_language', 'episodes', ['language'])
    op.create_index('ix_episodes_season_id', 'episodes', ['season_id'])

    # Artworks
    op.create_table(
        'artworks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('show_id', sa.Uuid(), nullable=True),
        sa.Column('episode_id', sa.Uuid(), nullable=True),
        sa.Column('artwork_type', sa.String(20), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['show_id'], ['shows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_artworks_show_id', 'artworks', ['show_id'])
    op.create_index('ix_artworks_episode_id', 'artworks', ['episode_id'])
    op.create_index('ix_artworks_artwork_type', 'artworks', ['artwork_type'])

    # Publish Runs
    op.create_table(
        'publish_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('published_by', sa.String(255), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('show_count', sa.Integer(), server_default='0'),
        sa.Column('episode_count', sa.Integer(), server_default='0'),
        sa.Column('catalogue_version', sa.String(100), nullable=True),
        sa.Column('storage_key', sa.String(500), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('publish_runs')
    op.drop_table('artworks')
    op.drop_table('episodes')
    op.drop_table('seasons')
    op.drop_table('shows')
    op.drop_table('users')
