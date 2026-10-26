from datetime import datetime, timedelta

from conftest import login, PASSWORD
from models import Blog, Block, Bookmark, Comment, Follow, FollowRequest, Notification
from models.notification import NotificationType
from utils.security import verify_password


def make_blog(db, user, content="hello", **fields):
    blog = Blog(user_id=user.id, content=content, **fields)
    db.add(blog)
    db.commit()
    return blog


def post(client, content, **fields):
    return client.post("/create-blog", data={"content": content, **fields})


# search


def test_search_finds_posts_and_people(client, db, make_user):
    alice = make_user("alice", full_name="Alice Liddell")
    make_blog(db, alice, "learning fastapi today")
    make_blog(db, alice, "something else")

    posts = client.get("/search?q=FastAPI").text
    people = client.get("/search?q=liddell&tab=people").text

    assert "learning fastapi today" in posts
    assert "something else" not in posts
    assert "@alice" in people


def test_search_treats_wildcards_literally(client, db, make_user):
    alice = make_user("alice")
    make_blog(db, alice, "nothing special")

    assert "nothing special" not in client.get("/search?q=%25").text


def test_search_for_hashtag_redirects_to_tag(client):
    response = client.get("/search?q=%23Python")

    assert response.headers["location"] == "/tag/python"


# hashtags


def test_hashtags_are_saved_linked_and_trending(client, db, make_user):
    make_user("alice")
    login(client, "alice")

    post(client, "Loving #Python and #FastAPI")

    blog = db.query(Blog).one()
    assert sorted(t.name for t in blog.tags) == ["fastapi", "python"]
    tag_page = client.get("/tag/python").text
    assert "Loving" in tag_page
    assert 'href="/tag/python"' in tag_page
    assert "#python" in client.get("/").text  # trending sidebar


def test_hashtag_links_are_escaped(client, db, make_user):
    alice = make_user("alice")
    make_blog(db, alice, "<b>#tag</b>")

    html = client.get("/").text

    assert "&lt;b&gt;" in html
    assert "<b>#tag" not in html


# bookmarks


def test_bookmark_toggles_and_lists(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    blog = make_blog(db, alice, "save me")
    login(client, "bob")

    first = client.post(f"/blog/{blog.id}/bookmark").json()
    page = client.get("/bookmarks").text
    second = client.post(f"/blog/{blog.id}/bookmark").json()

    assert first["bookmarked"] is True
    assert "save me" in page
    assert second["bookmarked"] is False
    assert db.query(Bookmark).count() == 0


# comment editing


def test_comment_can_be_edited_by_author_only(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    blog = make_blog(db, alice)
    comment = Comment(user_id=alice.id, blog_id=blog.id, content="old")
    db.add(comment)
    db.commit()

    login(client, "bob")
    forbidden = client.post(f"/comment/{comment.id}/edit", data={"content": "hacked"})
    login(client, "alice")
    edited = client.post(f"/comment/{comment.id}/edit", data={"content": "new"}).json()

    db.refresh(comment)
    assert forbidden.status_code == 403
    assert edited == {"success": True, "content": "new", "edited": True}
    assert comment.content == "new" and comment.updated_at is not None


# change password


def test_change_password_keeps_session_and_revokes_others(client, db, make_user):
    alice = make_user("alice")
    login(client, "alice")
    old_cookie = client.cookies.get("access_token")

    response = client.post(
        "/settings/password",
        data={
            "current_password": PASSWORD,
            "new_password": "brand-new-pass",
            "confirm_password": "brand-new-pass",
        },
    )

    db.refresh(alice)
    assert response.headers["location"] == "/settings"
    assert verify_password("brand-new-pass", alice.hashed_password)
    assert client.get("/settings").status_code == 200
    client.cookies.set("access_token", old_cookie)
    assert client.get("/settings").status_code == 401


def test_change_password_requires_current_password(client, db, make_user):
    alice = make_user("alice")
    login(client, "alice")

    client.post(
        "/settings/password",
        data={
            "current_password": "wrong-password",
            "new_password": "brand-new-pass",
            "confirm_password": "brand-new-pass",
        },
    )

    db.refresh(alice)
    assert verify_password(PASSWORD, alice.hashed_password)


# following feed


def test_following_feed_only_shows_followed_and_own_posts(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    carol = make_user("carol")
    db.add(Follow(follower_id=alice.id, followed_id=bob.id))
    db.commit()
    make_blog(db, alice, "alice post")
    make_blog(db, bob, "bob post")
    make_blog(db, carol, "carol post")
    login(client, "alice")

    following = client.get("/?feed=following").text
    for_you = client.get("/").text

    assert "alice post" in following and "bob post" in following
    assert "carol post" not in following
    assert "carol post" in for_you


def test_home_feed_is_paginated(client, db, make_user):
    alice = make_user("alice")
    for i in range(12):
        make_blog(db, alice, f"post number {i:02d}")

    first = client.get("/").text
    second = client.get("/?page=2").text

    assert "post number 11" in first and "post number 01" not in first
    assert "post number 01" in second


# comment replies


def test_reply_attaches_to_top_level_and_notifies(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    make_user("carol")
    blog = make_blog(db, alice)
    top = Comment(user_id=bob.id, blog_id=blog.id, content="top")
    db.add(top)
    db.commit()
    reply = Comment(
        user_id=alice.id, blog_id=blog.id, content="reply", parent_id=top.id
    )
    db.add(reply)
    db.commit()
    login(client, "carol")

    data = client.post(
        f"/blog/{blog.id}/comment", data={"content": "nested", "parent_id": reply.id}
    ).json()

    nested = db.query(Comment).filter_by(content="nested").one()
    assert nested.parent_id == top.id
    assert data["parent_id"] == top.id
    assert data["comment_count"] == 3
    types = {(n.recipient_id, n.type) for n in db.query(Notification).all()}
    assert (bob.id, NotificationType.REPLY) in types
    assert (alice.id, NotificationType.COMMENT) in types


def test_reply_rejects_comment_from_other_post(client, db, make_user):
    alice = make_user("alice")
    blog = make_blog(db, alice)
    other = make_blog(db, alice)
    comment = Comment(user_id=alice.id, blog_id=other.id, content="x")
    db.add(comment)
    db.commit()
    login(client, "alice")

    response = client.post(
        f"/blog/{blog.id}/comment", data={"content": "hi", "parent_id": comment.id}
    )

    assert response.status_code == 404


# mentions


def test_mentions_notify_and_link(client, db, make_user):
    make_user("alice")
    bob = make_user("bob")
    login(client, "alice")

    post(client, "hey @bob and @alice and @nobody")

    notifications = db.query(Notification).all()
    assert [(n.recipient_id, n.type) for n in notifications] == [
        (bob.id, NotificationType.MENTION)
    ]
    assert 'href="/profile/bob"' in client.get("/").text


def test_editing_post_only_notifies_new_mentions(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    make_user("carol")
    login(client, "alice")
    post(client, "hi @bob")
    blog = db.query(Blog).one()

    client.post(f"/user-blog/{blog.id}/edit", data={"content": "hi @bob and @carol"})

    assert db.query(Notification).filter_by(type=NotificationType.MENTION).count() == 2
    assert alice.id not in {n.recipient_id for n in db.query(Notification).all()}


# reposts


def test_repost_toggles_and_notifies(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    blog = make_blog(db, alice, "original")
    login(client, "bob")

    first = client.post(f"/blog/{blog.id}/repost").json()
    feed = client.get("/").text
    second = client.post(f"/blog/{blog.id}/repost").json()

    assert first == {"success": True, "reposted": True, "repost_count": 1}
    assert "reposted" in feed
    assert second == {"success": True, "reposted": False, "repost_count": 0}
    assert db.query(Notification).count() == 0  # removed with the repost


def test_cannot_repost_own_or_private_post(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob", is_private=True)
    db.add(Follow(follower_id=alice.id, followed_id=bob.id))
    db.commit()
    own = make_blog(db, alice)
    private = make_blog(db, bob)
    login(client, "alice")

    assert client.post(f"/blog/{own.id}/repost").status_code == 400
    assert client.post(f"/blog/{private.id}/repost").status_code == 403


def test_quote_post(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    blog = make_blog(db, alice, "original words")
    login(client, "bob")

    post(client, "my take", quote_of=blog.id)

    quote = db.query(Blog).filter_by(content="my take").one()
    assert quote.repost_of_id == blog.id
    page = client.get(f"/post/{quote.id}").text
    assert "my take" in page and "original words" in page
    assert db.query(Notification).filter_by(type=NotificationType.REPOST).count() == 1


def test_deleting_original_removes_reposts(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    blog = make_blog(db, alice)
    make_blog(db, bob, "", repost_of_id=blog.id)
    login(client, "alice")

    client.post(f"/user-blog/{blog.id}/delete")

    assert db.query(Blog).count() == 0


# block & mute


def test_block_hides_content_both_ways_and_removes_follows(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    db.add_all(
        [
            Follow(follower_id=alice.id, followed_id=bob.id),
            Follow(follower_id=bob.id, followed_id=alice.id),
        ]
    )
    db.commit()
    alice_post = make_blog(db, alice, "alice words")
    make_blog(db, bob, "bob words")

    login(client, "alice")
    client.post(f"/user/{bob.id}/block")
    alice_feed = client.get("/").text

    login(client, "bob")
    bob_feed = client.get("/").text
    profile = client.get("/profile/alice")
    comment = client.post(f"/blog/{alice_post.id}/comment", data={"content": "hi"})
    follow = client.post(f"/user/{alice.id}/follow")

    assert "bob words" not in alice_feed
    assert "alice words" not in bob_feed
    assert db.query(Follow).count() == 0
    assert profile.headers["location"] == "/"
    assert comment.status_code == 404
    assert follow.status_code == 403


def test_unblock(client, db, make_user):
    make_user("alice")
    bob = make_user("bob")
    login(client, "alice")

    client.post(f"/user/{bob.id}/block")
    client.post(f"/user/{bob.id}/block", data={"next": "/settings"})

    assert db.query(Block).count() == 0


def test_mute_hides_feed_and_notifications_but_not_profile(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    blog = make_blog(db, alice)
    make_blog(db, bob, "bob words")
    db.add(
        Notification(
            recipient_id=alice.id,
            actor_id=bob.id,
            type=NotificationType.MENTION,
            blog_id=blog.id,
        )
    )
    db.commit()
    login(client, "alice")

    client.post(f"/user/{bob.id}/mute")

    assert "bob words" not in client.get("/").text
    assert "bob words" in client.get("/profile/bob").text
    assert "mentioned you" not in client.get("/notifications").text


# private accounts


def test_private_account_follow_request_flow(client, db, make_user):
    alice = make_user("alice", is_private=True)
    bob = make_user("bob")
    make_blog(db, alice, "secret post")

    login(client, "bob")
    assert "secret post" not in client.get("/").text
    assert "This account is private" in client.get("/profile/alice").text
    requested = client.post(f"/user/{alice.id}/follow").json()
    assert requested["requested"] is True and requested["following"] is False

    login(client, "alice")
    assert "wants to follow you" in client.get("/notifications").text
    follow_request = db.query(FollowRequest).one()
    client.post(f"/follow-requests/{follow_request.id}/approve")

    login(client, "bob")
    assert (
        db.query(Follow).filter_by(follower_id=bob.id, followed_id=alice.id).count()
        == 1
    )
    assert "secret post" in client.get("/").text


def test_going_public_approves_pending_requests(client, db, make_user):
    alice = make_user("alice", is_private=True)
    bob = make_user("bob")
    db.add(FollowRequest(requester_id=bob.id, target_id=alice.id))
    db.commit()
    login(client, "alice")

    client.post("/settings/privacy", data={})

    db.refresh(alice)
    assert alice.is_private is False
    assert db.query(FollowRequest).count() == 0
    assert db.query(Follow).count() == 1


def test_private_follow_list_is_hidden(client, make_user):
    make_user("alice", is_private=True)

    response = client.get("/profile/alice/followers")

    assert response.headers["location"] == "/profile/alice"


# drafts & scheduled posts


def test_draft_is_hidden_until_published(client, db, make_user):
    make_user("alice")
    make_user("bob")
    login(client, "alice")

    post(client, "draft for @bob", action="draft")
    blog = db.query(Blog).one()
    assert blog.is_draft
    assert "draft for" not in client.get("/").text
    assert "draft for" in client.get("/user-blogs?tab=drafts").text
    assert db.query(Notification).count() == 0

    client.post(f"/user-blog/{blog.id}/publish")

    assert "draft for" in client.get("/").text
    assert db.query(Notification).count() == 1


def test_scheduled_post_and_its_notifications_wait(client, db, make_user):
    make_user("alice")
    bob = make_user("bob")
    login(client, "alice")
    when = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

    post(client, "later @bob", scheduled_at=when, tz_offset=0)

    blog = db.query(Blog).one()
    assert blog.is_scheduled
    assert "later" not in client.get("/").text
    assert "later" in client.get("/user-blogs?tab=scheduled").text

    login(client, "bob")
    assert "mentioned you" not in client.get("/notifications").text

    # once it goes live, both the post and the mention appear
    blog.published_at = datetime.utcnow() - timedelta(minutes=1)
    db.query(Notification).update({"created_at": blog.published_at})
    db.commit()
    assert "later" in client.get("/").text
    assert db.query(Notification).filter_by(recipient_id=bob.id).count() == 1


def test_schedule_in_past_is_rejected(client, db, make_user):
    make_user("alice")
    login(client, "alice")

    response = post(client, "too late", scheduled_at="2000-01-01T10:00", tz_offset=0)

    assert response.headers["location"] == "/create-blog"
    assert db.query(Blog).count() == 0
