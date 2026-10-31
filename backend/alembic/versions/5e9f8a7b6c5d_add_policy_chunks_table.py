"""add_policy_chunks_table

Revision ID: 5e9f8a7b6c5d
Revises: 438edf1ac68f
Create Date: 2026-10-09 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '5e9f8a7b6c5d'
down_revision = '438edf1ac68f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create policy_chunks table
    op.create_table(
        'policy_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('part_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unit_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('document', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False, server_default='policy_pdf'),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('chapter', sa.String(), nullable=True),
        sa.Column('section', sa.String(), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('version_number', sa.String(), nullable=True),
        sa.Column('institution', sa.String(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('applicability_json', sa.String(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('file_hash', sa.String(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_version_id'], ['policy_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_policy_chunks_policy_id', 'policy_chunks', ['policy_id'], unique=False)
    op.create_index('ix_policy_chunks_policy_version_id', 'policy_chunks', ['policy_version_id'], unique=False)
    op.create_index('ix_policy_chunks_institution', 'policy_chunks', ['institution'], unique=False)
    op.create_index('ix_policy_chunks_jurisdiction', 'policy_chunks', ['jurisdiction'], unique=False)

    # HNSW vector similarity index for pgvector
    op.execute("CREATE INDEX IF NOT EXISTS ix_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_embedding;")
    op.drop_index('ix_policy_chunks_jurisdiction', table_name='policy_chunks')
    op.drop_index('ix_policy_chunks_institution', table_name='policy_chunks')
    op.drop_index('ix_policy_chunks_policy_version_id', table_name='policy_chunks')
    op.drop_index('ix_policy_chunks_policy_id', table_name='policy_chunks')
    op.drop_table('policy_chunks')
