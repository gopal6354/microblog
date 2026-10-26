from conftest import login
from admin_panel.services.admin_service import (
    activation_status_update,
    soft_delete_user,
)
from models import Blog, Report
from models.activation_request import AccountActivation, ActivationRequestStatus
from models.user import User


def test_suspended_user_token_is_rejected(client, db, make_user):
    alice = make_user("alice")
    login(client, "alice")

    soft_delete_user(db.get(User, alice.id))
    db.commit()

    response = client.get("/create-blog")
    assert response.headers["location"] == "/login"


def test_approving_activation_restores_user(db, make_user):
    alice = make_user("alice")
    soft_delete_user(alice)
    activation = AccountActivation(user_id=alice.id, email=alice.email, message="hi")
    db.add(activation)
    db.commit()

    success, _ = activation_status_update(activation, ActivationRequestStatus.APPROVED)
    db.commit()

    assert success
    assert alice.is_deleted is False


def test_rejected_user_can_request_activation_again(db, make_user):
    alice = make_user("alice")
    db.add(
        AccountActivation(
            user_id=alice.id,
            email=alice.email,
            message="first",
            status=ActivationRequestStatus.REJECTED,
        )
    )
    db.add(AccountActivation(user_id=alice.id, email=alice.email, message="second"))
    db.commit()

    assert db.query(AccountActivation).count() == 2


def test_upload_rejects_disallowed_file_type(client, db, make_user):
    make_user("alice")
    login(client, "alice")

    response = client.post(
        "/create-blog",
        data={"content": "hello"},
        files={"image": ("evil.html", b"<script>alert(1)</script>", "text/html")},
    )

    assert response.headers["location"] == "/create-blog"
    assert db.query(Blog).count() == 0


def test_bio_is_html_escaped(client, make_user):
    make_user("alice", bio="<script>alert(1)</script>")
    login(client, "alice")

    response = client.get("/user-profile")

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_profile_rejects_taken_username(client, db, make_user):
    alice = make_user("alice")
    make_user("bob")
    login(client, "alice")

    response = client.post("/profile-edit", data={"username": "bob"})

    assert response.headers["location"] == "/profile-edit"
    db.expire_all()
    assert db.get(User, alice.id).username == "alice"


def test_like_missing_blog_returns_404(client, make_user):
    make_user("alice")
    login(client, "alice")

    response = client.post("/blog/999/like")

    assert response.status_code == 404


def test_cannot_report_own_blog(client, db, make_user):
    alice = make_user("alice")
    blog = Blog(user_id=alice.id, content="mine")
    db.add(blog)
    db.commit()
    login(client, "alice")

    client.post("/report/blog", data={"blog_id": blog.id, "reason": "Spam"})

    assert db.query(Report).count() == 0
