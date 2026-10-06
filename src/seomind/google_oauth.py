from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from seomind.config import settings
from seomind.storage import LocalStorage, storage

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
DEFAULT_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuth:
    def __init__(self, store: LocalStorage = storage) -> None:
        self.store = store

    def _client(self) -> dict[str, Any]:
        raw = self.store.get_google_credentials()
        if not raw:
            raise GoogleOAuthError("Google OAuth credentials are not configured.")
        cfg = raw.get("web") or raw.get("installed")
        if not isinstance(cfg, dict):
            raise GoogleOAuthError("Invalid Google OAuth JSON: expected 'web' or 'installed'.")
        if not cfg.get("client_id") or not cfg.get("client_secret"):
            raise GoogleOAuthError("Google OAuth JSON is missing client_id/client_secret.")
        return cfg

    @staticmethod
    def validate_credentials(raw: dict[str, Any]) -> dict[str, Any]:
        cfg = raw.get("web") or raw.get("installed")
        if not isinstance(cfg, dict):
            raise GoogleOAuthError("OAuth JSON must contain a 'web' or 'installed' object.")
        if not isinstance(cfg.get("client_id"), str) or not cfg.get("client_id"):
            raise GoogleOAuthError("OAuth JSON does not contain a valid client_id.")
        if not isinstance(cfg.get("client_secret"), str) or not cfg.get("client_secret"):
            raise GoogleOAuthError("OAuth JSON does not contain a valid client_secret.")
        return raw

    def authorization_url(self) -> str:
        cfg = self._client()
        state = secrets.token_urlsafe(32)
        self.store.save_oauth_state(state)
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return f"{cfg.get('auth_uri', DEFAULT_AUTH_URI)}?{urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> dict[str, Any]:
        if not self.store.consume_oauth_state(state):
            raise GoogleOAuthError("OAuth state validation failed. Start the connection again.")
        cfg = self._client()
        data = {
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": settings.oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(cfg.get("token_uri", DEFAULT_TOKEN_URI), data=data)
        if response.is_error:
            raise GoogleOAuthError(f"Token exchange failed: {response.text[:500]}")
        token = response.json()
        token["obtained_at"] = datetime.now(UTC).isoformat()
        if token.get("expires_in"):
            token["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=int(token["expires_in"]))
            ).isoformat()
        self.store.save_google_token(token)
        return token

    async def access_token(self) -> str:
        token = self.store.get_google_token()
        if not token or not token.get("access_token"):
            raise GoogleOAuthError("Google account is not connected.")

        expires_at = token.get("expires_at")
        if expires_at:
            try:
                expires = datetime.fromisoformat(str(expires_at))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=UTC)
                if expires > datetime.now(UTC) + timedelta(seconds=60):
                    return str(token["access_token"])
            except ValueError:
                pass
        else:
            return str(token["access_token"])

        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise GoogleOAuthError("Google access token expired and no refresh token is available.")

        cfg = self._client()
        data = {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(cfg.get("token_uri", DEFAULT_TOKEN_URI), data=data)
        if response.is_error:
            raise GoogleOAuthError(f"Token refresh failed: {response.text[:500]}")
        refreshed = response.json()
        refreshed["refresh_token"] = refresh_token
        refreshed["obtained_at"] = datetime.now(UTC).isoformat()
        if refreshed.get("expires_in"):
            refreshed["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=int(refreshed["expires_in"]))
            ).isoformat()
        self.store.save_google_token(refreshed)
        return str(refreshed["access_token"])


google_oauth = GoogleOAuth()
