"""Tests for the auth middleware."""

from __future__ import annotations

from whaleclaw.config.schema import AuthConfig
from whaleclaw.gateway.middleware import create_jwt, verify_jwt


class TestJWT:
    def test_create_and_verify(self) -> None:
        cfg = AuthConfig(jwt_secret="test-secret", jwt_expire_hours=1)
        token = create_jwt(cfg)
        assert verify_jwt(cfg, token)

    def test_invalid_token(self) -> None:
        cfg = AuthConfig(jwt_secret="test-secret")
        assert not verify_jwt(cfg, "invalid.token.here")

    def test_wrong_secret(self) -> None:
        cfg1 = AuthConfig(jwt_secret="secret-1")
        cfg2 = AuthConfig(jwt_secret="secret-2")
        token = create_jwt(cfg1)
        assert not verify_jwt(cfg2, token)

    def test_expired_token(self) -> None:
        cfg = AuthConfig(jwt_secret="test", jwt_expire_hours=0)
        token = create_jwt(cfg)
        assert not verify_jwt(cfg, token)
