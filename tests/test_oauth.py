from pathlib import Path
from urllib.parse import parse_qs, urlparse

from seomind.google_oauth import GoogleOAuth
from seomind.storage import LocalStorage


def credentials():
    return {
        "web": {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def test_credentials_and_authorization_url(tmp_path: Path):
    store = LocalStorage(tmp_path)
    store.save_google_credentials(GoogleOAuth.validate_credentials(credentials()))
    oauth = GoogleOAuth(store)
    url = oauth.authorization_url()
    query = parse_qs(urlparse(url).query)
    assert query["client_id"][0] == "client-id.apps.googleusercontent.com"
    assert query["scope"][0].endswith("webmasters.readonly")
    assert query["access_type"][0] == "offline"
    assert store.oauth_state_path.exists()
