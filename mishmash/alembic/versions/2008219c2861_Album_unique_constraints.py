"""Album unique constraints

Revision ID: 2008219c2861
Revises: 74df8fa5a35f
Create Date: 2019-02-09 20:58:43.822325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2008219c2861'
down_revision = '74df8fa5a35f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.alter_column('metadata_format', existing_type=sa.VARCHAR(length=7),
                              nullable=False)


def downgrade():
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.alter_column('metadata_format', existing_type=sa.VARCHAR(length=7),
                              nullable=True)
