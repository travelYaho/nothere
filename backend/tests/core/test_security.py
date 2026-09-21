"""get_token_user 의 JWKS 로컬 검증/폴백 동작 테스트."""
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.security import HTTPAuthorizationCredentials

from app.core import security
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode

ISSUER = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"


@pytest.fixture
def signing_key():
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwks = MagicMock()
    jwks.get_signing_key_from_jwt.return_value = MagicMock(key=private_key.public_key())
    with patch.object(security, "_jwks_client", return_value=jwks):
        yield private_key


def _token(private_key, **overrides) -> str:
    claims = {
        "sub": str(uuid4()),
        "email": "user@example.com",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
        "user_metadata": {"nickname": "여행자"},
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": "k1"})


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_is_verified_without_calling_supabase(signing_key):
    sub = str(uuid4())
    with patch.object(security, "get_anon_client") as anon:
        user = security.get_token_user(_creds(_token(signing_key, sub=sub)))

    anon.assert_not_called()
    assert str(user.id) == sub
    assert user.email == "user@example.com"
    assert user.user_metadata == {"nickname": "여행자"}


def test_expired_token_raises_expired(signing_key):
    token = _token(signing_key, exp=int(time.time()) - 60)
    with pytest.raises(AppError) as exc_info:
        security.get_token_user(_creds(token))
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_EXPIRED


def test_token_issued_slightly_in_future_is_accepted(signing_key):
    """서버 시계가 Supabase 보다 몇 초 늦어도 막 발급된 토큰을 거부하지 않는다."""
    token = _token(signing_key, iat=int(time.time()) + 5)
    user = security.get_token_user(_creds(token))
    assert user.email == "user@example.com"


@pytest.mark.parametrize("override", [{"aud": "anon"}, {"iss": "https://evil.example/auth/v1"}])
def test_wrong_audience_or_issuer_is_invalid(signing_key, override):
    with pytest.raises(AppError) as exc_info:
        security.get_token_user(_creds(_token(signing_key, **override)))
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID


def test_token_signed_by_other_key_is_invalid(signing_key):
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(AppError) as exc_info:
        security.get_token_user(_creds(_token(other)))
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_INVALID


def test_hs256_token_falls_back_to_supabase():
    sub = uuid4()
    token = jwt.encode({"sub": str(sub)}, "legacy-secret-at-least-32-bytes-long!!", algorithm="HS256")
    fake_user = MagicMock(id=sub, email="legacy@example.com", user_metadata={}, identities=[])
    with patch.object(security, "get_anon_client") as anon:
        anon.return_value.auth.get_user.return_value = MagicMock(user=fake_user)
        user = security.get_token_user(_creds(token))

    anon.return_value.auth.get_user.assert_called_once_with(token)
    assert user.id == sub


def test_missing_token_raises_missing():
    with pytest.raises(AppError) as exc_info:
        security.get_token_user(None)
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_MISSING
