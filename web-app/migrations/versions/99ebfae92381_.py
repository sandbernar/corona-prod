"""empty message

Revision ID: 99ebfae92381
Revises: 83df3f8cb8b5
Create Date: 2020-06-04 12:51:26.037196

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99ebfae92381'
down_revision = '83df3f8cb8b5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('UserRole', sa.Column('can_access_users', sa.Boolean(), nullable=True))
    op.add_column('UserRole', sa.Column('can_export_users', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('UserRole', 'can_export_users')
    op.drop_column('UserRole', 'can_access_users')
    # ### end Alembic commands ###
