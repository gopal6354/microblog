from conftest import PASSWORD, login
from models.user import User
from utils.otp_service import MAX_OTP_ATTEMPTS
from utils.security import verify_password


NEW_PASSWORD = "brand-new-password-123"


def get_otp(db, user):
    db.expire_all()
    return db.get(User, user.id).otp


def test_login_hides_whether_account_exists(client, make_user):
    make_user("alice")

    unknown = login(client, "nobody")
    wrong_password = login(client, "alice", "wrong-password")

    assert unknown.headers["location"] == wrong_password.headers["location"] == "/login"


def test_login_sets_cookie(client, make_user):
    make_user("alice")

    response = login(client, "alice")

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "access_token" in response.cookies


def test_password_reset_flow(client, db, make_user):
    alice = make_user("alice")

    client.post("/forget-password", data={"email": alice.email})
    client.post("/verify-reset-otp", data={"otp": get_otp(db, alice)})
    response = client.post(
        "/reset-password",
        data={"password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )

    assert response.headers["location"] == "/login"
    db.expire_all()
    assert verify_password(NEW_PASSWORD, db.get(User, alice.id).hashed_password)


def test_reset_verification_cannot_be_reused_for_another_account(client, db, make_user):
    attacker = make_user("attacker")
    victim = make_user("victim")

    client.post("/forget-password", data={"email": attacker.email})
    client.post("/verify-reset-otp", data={"otp": get_otp(db, attacker)})

    # switch the reset session to the victim without knowing the victim's OTP
    client.post("/forget-password", data={"email": victim.email})
    response = client.post(
        "/reset-password",
        data={"password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )

    assert response.headers["location"] == "/forget-password"
    db.expire_all()
    assert verify_password(PASSWORD, db.get(User, victim.id).hashed_password)


def test_forget_password_hides_whether_account_exists(client):
    response = client.post("/forget-password", data={"email": "nobody@example.com"})

    assert response.headers["location"] == "/verify-reset-otp"


def test_otp_invalidated_after_too_many_wrong_attempts(client, db, make_user):
    alice = make_user("alice")
    client.post("/forget-password", data={"email": alice.email})
    otp = get_otp(db, alice)
    wrong = "000000" if otp != "000000" else "111111"

    for _ in range(MAX_OTP_ATTEMPTS):
        client.post("/verify-reset-otp", data={"otp": wrong})

    assert get_otp(db, alice) is None
    response = client.post("/verify-reset-otp", data={"otp": otp})
    assert response.headers["location"] == "/forget-password"


def test_register_rejects_short_password(client, db):
    response = client.post(
        "/register",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password": "short",
            "confirm_password": "short",
        },
    )

    assert response.headers["location"] == "/register"
    assert db.query(User).filter_by(username="bob").first() is None
