"""server_default migration for tempfs 

Revision ID: f981aaae1ed6
Revises: 0ba004466179
Create Date: 2026-04-07 20:15:46.921988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f981aaae1ed6'
down_revision: Union[str, Sequence[str], None] = '0ba004466179'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # temp_file
    op.alter_column(
        'temp_file', 'file_id',
        server_default=sa.func.gen_random_uuid(),
    )
    op.alter_column(
        'temp_file', 'is_compressed',
        server_default='false',
    )
    op.alter_column(
        'temp_file', 'created_at',
        server_default=sa.func.now(),
    )
 
    # expired_file
    op.alter_column(
        'expired_file', 'is_compressed',
        server_default='false',
    )
    op.alter_column(
        'expired_file', 'deleted_at',
        server_default=sa.func.now(),
    )
 
 
def downgrade() -> None:
    op.alter_column('temp_file',    'file_id',       server_default=None)
    op.alter_column('temp_file',    'is_compressed',  server_default=None)
    op.alter_column('temp_file',    'created_at',     server_default=None)
    op.alter_column('expired_file', 'is_compressed',  server_default=None)
    op.alter_column('expired_file', 'deleted_at',     server_default=None)