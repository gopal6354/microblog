"""add hashtags, bookmarks, replies, reposts, blocks, mutes, private accounts, drafts

Revision ID: b8d41f7e2c63
Revises: a7c3e9f15b24
Create Date: 2026-10-26 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8d41f7e2c63"
down_revision: Union[str, Sequence[str], None] = "a7c3e9f15b24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_NOTIFICATION_TYPES = ("REPLY", "MENTION", "REPOST", "FOLLOW_REQUEST")


def upgrade() -> None:
    """Upgrade schema."""

    # ALTER TYPE ... ADD VALUE can't run inside a transaction block
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for value in NEW_NOTIFICATION_TYPES:
                op.execute(
                    f"ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{value}'"
                )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "blog_tags",
        sa.Column("blog_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["blog_id"], ["blogs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("blog_id", "tag_id"),
    )
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("blog_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blog_id"], ["blogs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "blog_id", name="uq_user_blog_bookmark"),
    )
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blocker_id", sa.Integer(), nullable=False),
        sa.Column("blocked_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("blocker_id != blocked_id", name="ck_no_self_block"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),
    )
    op.create_table(
        "mutes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("muter_id", sa.Integer(), nullable=False),
        sa.Column("muted_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("muter_id != muted_id", name="ck_no_self_mute"),
        sa.ForeignKeyConstraint(["muter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muted_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("muter_id", "muted_id", name="uq_muter_muted"),
    )
    op.create_table(
        "follow_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("requester_id != target_id", name="ck_no_self_request"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "target_id", name="uq_requester_target"),
    )

    op.add_column(
        "users",
        sa.Column(
            "is_private", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )

    op.add_column("blogs", sa.Column("repost_of_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_blogs_repost_of_id_blogs",
        "blogs",
        "blogs",
        ["repost_of_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_blogs_repost_of_id", "blogs", ["repost_of_id"])
    op.add_column(
        "blogs",
        sa.Column("is_draft", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # existing posts were published when they were created
    op.add_column("blogs", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE blogs SET published_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
    )
    op.alter_column("blogs", "published_at", nullable=False)
    op.create_index("ix_blogs_published_at", "blogs", ["published_at"])

    op.add_column("comments", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_comments_parent_id_comments",
        "comments",
        "comments",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.add_column("comments", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.add_column(
        "notifications", sa.Column("follow_request_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_notifications_follow_request_id",
        "notifications",
        "follow_requests",
        ["follow_request_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""

    # notifications of the new types can't exist once the enum values are gone
    op.execute(
        "DELETE FROM notifications WHERE type IN ("
        + ", ".join(f"'{value}'" for value in NEW_NOTIFICATION_TYPES)
        + ")"
    )

    op.drop_constraint(
        "fk_notifications_follow_request_id", "notifications", type_="foreignkey"
    )
    op.drop_column("notifications", "follow_request_id")

    op.drop_column("comments", "updated_at")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_constraint("fk_comments_parent_id_comments", "comments", type_="foreignkey")
    op.drop_column("comments", "parent_id")

    op.drop_index("ix_blogs_published_at", table_name="blogs")
    op.drop_column("blogs", "published_at")
    op.drop_column("blogs", "is_draft")
    op.drop_index("ix_blogs_repost_of_id", table_name="blogs")
    op.drop_constraint("fk_blogs_repost_of_id_blogs", "blogs", type_="foreignkey")
    op.drop_column("blogs", "repost_of_id")

    op.drop_column("users", "is_private")

    op.drop_table("follow_requests")
    op.drop_table("mutes")
    op.drop_table("blocks")
    op.drop_table("bookmarks")
    op.drop_table("blog_tags")
    op.drop_table("tags")

    # postgres can't drop enum values, so rebuild the type without them
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE notificationtype RENAME TO notificationtype_old")
        op.execute("CREATE TYPE notificationtype AS ENUM ('COMMENT', 'FOLLOW')")
        op.execute(
            "ALTER TABLE notifications ALTER COLUMN type TYPE notificationtype "
            "USING type::text::notificationtype"
        )
        op.execute("DROP TYPE notificationtype_old")
