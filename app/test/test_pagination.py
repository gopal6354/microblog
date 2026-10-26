from conftest import login
from models import Blog, Follow
from models.user import RoleChoice


def make_blogs(db, user, count):
    db.add_all(Blog(user_id=user.id, content=f"post-{i:02d}") for i in range(count))
    db.commit()


def test_public_profile_posts_are_paginated(client, db, make_user):
    alice = make_user("alice")
    make_blogs(db, alice, 12)

    first = client.get("/profile/alice").text
    second = client.get("/profile/alice?page=2").text

    assert "post-11" in first and "post-02" in first
    assert "post-01" not in first
    assert "post-01" in second and "post-00" in second
    assert "post-11" not in second
    assert 'aria-label="Pagination"' in first


def test_out_of_range_page_shows_last_page(client, db, make_user):
    alice = make_user("alice")
    make_blogs(db, alice, 12)

    assert "post-00" in client.get("/profile/alice?page=99").text


def test_no_pagination_nav_for_single_page(client, db, make_user):
    alice = make_user("alice")
    make_blogs(db, alice, 3)

    assert 'aria-label="Pagination"' not in client.get("/profile/alice").text


def test_profile_post_count_uses_total(client, db, make_user):
    alice = make_user("alice")
    make_blogs(db, alice, 12)
    login(client, "alice")

    page = client.get("/user-blogs?tab=posts").text

    assert "<strong>12</strong>" in page
    # page links keep the active tab
    assert "tab=posts&amp;page=2" in page


def test_follow_list_is_paginated(client, db, make_user):
    bob = make_user("bob")
    for i in range(22):
        follower = make_user(f"fan{i:02d}")
        db.add(Follow(follower_id=follower.id, followed_id=bob.id))
    db.commit()

    first = client.get("/profile/bob/followers").text
    second = client.get("/profile/bob/followers?page=2").text

    assert first.count('class="follow-item"') == 20
    assert second.count('class="follow-item"') == 2


def test_admin_users_page_is_paginated(client, make_user):
    make_user("root", role=RoleChoice.SUPER_ADMIN)
    for i in range(12):
        make_user(f"user{i:02d}")
    login(client, "root")

    first = client.get("/admin/users").text
    second = client.get("/admin/users?page=2").text

    assert first.count("@example.com") == 10
    assert second.count("@example.com") == 2


def test_paginated_pages_render(client, make_user):
    make_user("root", role=RoleChoice.SUPER_ADMIN)
    make_user("alice")
    login(client, "root")
    for url in ["/admin/blogs", "/admin/reports", "/admin/activation-requests"]:
        assert client.get(f"{url}?page=3").status_code == 200

    login(client, "alice")
    assert client.get("/notifications?page=2").status_code == 200
