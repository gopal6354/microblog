from conftest import login
from admin_panel.services.admin_service import soft_delete_user
from models import Blog, Comment, Notification
from models.notification import NotificationType
from models.user import User


def make_blog(db, user, content="hello"):
    blog = Blog(user_id=user.id, content=content)
    db.add(blog)
    db.commit()
    return blog


def test_comment_notifies_post_owner(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    blog = make_blog(db, alice)
    login(client, "bob")

    client.post(f"/blog/{blog.id}/comment", data={"content": "nice post"})

    notification = db.query(Notification).one()
    assert notification.recipient_id == alice.id
    assert notification.actor_id == bob.id
    assert notification.type == NotificationType.COMMENT


def test_commenting_on_own_post_does_not_notify(client, db, make_user):
    alice = make_user("alice")
    blog = make_blog(db, alice)
    login(client, "alice")

    client.post(f"/blog/{blog.id}/comment", data={"content": "me again"})

    assert db.query(Notification).count() == 0


def test_deleting_comment_removes_notification(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    blog = make_blog(db, alice)
    login(client, "bob")
    client.post(f"/blog/{blog.id}/comment", data={"content": "oops"})
    comment = db.query(Comment).one()

    client.post(f"/comment/{comment.id}/delete")

    db.expire_all()
    assert db.query(Notification).count() == 0


def test_follow_notifies_and_unfollow_removes_it(client, db, make_user):
    make_user("alice")
    bob = make_user("bob")
    login(client, "alice")

    client.post(f"/user/{bob.id}/follow")
    assert db.query(Notification).one().type == NotificationType.FOLLOW

    client.post(f"/user/{bob.id}/follow")
    db.expire_all()
    assert db.query(Notification).count() == 0


def test_sidebar_badge_and_page_marks_read(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    login(client, "bob")
    client.post(f"/user/{alice.id}/follow")

    login(client, "alice")
    assert "notification-badge" in client.get("/").text

    page = client.get("/notifications")
    assert "started following you" in page.text
    assert 'href="/profile/bob"' in page.text
    assert "notification-badge" not in page.text

    db.expire_all()
    assert db.query(Notification).one().is_read is True
    assert "notification-badge" not in client.get("/").text


def test_suspended_actor_notifications_are_hidden(client, db, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    login(client, "bob")
    client.post(f"/user/{alice.id}/follow")
    soft_delete_user(db.get(User, bob.id))
    db.commit()

    login(client, "alice")
    page = client.get("/notifications")

    assert "started following you" not in page.text
    assert "notification-badge" not in page.text


def test_notifications_require_login(client):
    response = client.get("/notifications")

    assert response.headers["location"] == "/login"
