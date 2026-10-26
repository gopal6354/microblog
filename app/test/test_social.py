from conftest import login
from admin_panel.services.admin_service import soft_delete_user
from echohub.services.social_service import MAX_COMMENT_LENGTH
from models import Blog, Comment, Follow
from models.user import User


def make_blog(db, user, content="hello"):
    blog = Blog(user_id=user.id, content=content)
    db.add(blog)
    db.commit()
    return blog


def test_register_accepts_eight_character_password(client, db):
    client.post(
        "/register",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password": "12345678",
            "confirm_password": "12345678",
        },
    )

    assert db.query(User).filter_by(username="bob").first() is not None


def test_register_rejects_seven_character_password(client, db):
    response = client.post(
        "/register",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password": "1234567",
            "confirm_password": "1234567",
        },
    )

    assert response.headers["location"] == "/register"
    assert db.query(User).filter_by(username="bob").first() is None


def test_comment_is_saved_and_escaped(client, db, make_user):
    alice = make_user("alice")
    blog = make_blog(db, alice)
    login(client, "alice")

    response = client.post(
        f"/blog/{blog.id}/comment", data={"content": "<script>x</script>"}
    )

    data = response.json()
    assert data["comment_count"] == 1
    assert "<script>" not in data["comment_html"]
    assert "&lt;script&gt;" in data["comment_html"]
    assert db.query(Comment).count() == 1
    assert "&lt;script&gt;" in client.get("/").text


def test_comment_requires_login(client, db, make_user):
    blog = make_blog(db, make_user("alice"))

    response = client.post(f"/blog/{blog.id}/comment", data={"content": "hi"})

    assert response.status_code == 401
    assert db.query(Comment).count() == 0


def test_comment_rejects_blank_and_too_long(client, db, make_user):
    blog = make_blog(db, make_user("alice"))
    login(client, "alice")

    blank = client.post(f"/blog/{blog.id}/comment", data={"content": "   "})
    too_long = client.post(
        f"/blog/{blog.id}/comment", data={"content": "a" * (MAX_COMMENT_LENGTH + 1)}
    )

    assert blank.status_code == too_long.status_code == 400
    assert db.query(Comment).count() == 0


def test_comment_on_hidden_blog_returns_404(client, db, make_user):
    alice = make_user("alice")
    blog = Blog(user_id=alice.id, content="hidden", is_hidden=True)
    db.add(blog)
    db.commit()
    login(client, "alice")

    response = client.post(f"/blog/{blog.id}/comment", data={"content": "hi"})

    assert response.status_code == 404


def test_only_comment_author_can_delete_comment(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    make_user("carol")
    blog = make_blog(db, alice)
    comment = Comment(user_id=bob.id, blog_id=blog.id, content="nice")
    db.add(comment)
    db.commit()

    # neither a stranger nor the post owner can delete someone else's comment
    for username in ("carol", "alice"):
        login(client, username)
        assert client.post(f"/comment/{comment.id}/delete").status_code == 403
    assert 'class="comment-delete-btn"' not in client.get("/").text

    login(client, "bob")
    assert 'class="comment-delete-btn"' in client.get("/").text
    response = client.post(f"/comment/{comment.id}/delete")

    assert response.json() == {"success": True, "comment_count": 0}
    assert db.query(Comment).count() == 0


def test_follow_toggles(client, db, make_user):
    make_user("alice")
    bob = make_user("bob")
    login(client, "alice")

    first = client.post(f"/user/{bob.id}/follow").json()
    second = client.post(f"/user/{bob.id}/follow").json()

    assert first == {
        "success": True,
        "following": True,
        "requested": False,
        "follower_count": 1,
    }
    assert second == {
        "success": True,
        "following": False,
        "requested": False,
        "follower_count": 0,
    }
    assert db.query(Follow).count() == 0


def test_cannot_follow_self_or_suspended_user(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    soft_delete_user(bob)
    db.commit()
    login(client, "alice")

    assert client.post(f"/user/{alice.id}/follow").status_code == 400
    assert client.post(f"/user/{bob.id}/follow").status_code == 404
    assert db.query(Follow).count() == 0


def test_profile_shows_follow_counts(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    db.add(Follow(follower_id=alice.id, followed_id=bob.id))
    db.commit()
    login(client, "alice")

    profile = client.get("/profile/bob")
    followers = client.get("/profile/bob/followers")

    assert profile.status_code == 200
    assert 'data-follower-count-for="%d">1<' % bob.id in profile.text
    assert "Following" in profile.text
    assert "@alice" in followers.text


def test_own_profile_redirects_to_user_blogs(client, make_user):
    make_user("alice")
    login(client, "alice")

    response = client.get("/profile/alice")

    assert response.headers["location"] == "/user-blogs"


def test_unknown_profile_redirects_home(client):
    response = client.get("/profile/nobody")

    assert response.headers["location"] == "/"


def test_home_suggests_only_unfollowed_users(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    make_user("carol")
    db.add(Follow(follower_id=alice.id, followed_id=bob.id))
    db.commit()
    login(client, "alice")

    sidebar = client.get("/").text.split("Who to Follow")[1]

    assert "@carol" in sidebar
    assert "@bob" not in sidebar
    assert "@alice" not in sidebar
