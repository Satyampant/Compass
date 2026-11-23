"""Google sign-in for a desktop app: loopback redirect with PKCE, refresh token in the Keychain.

Run once:  uv run python -m app.modules.integrations.google sign-in
"""

import base64
import hashlib
import http.server
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser

import httpx
import keyring

from app.kernel import config

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# Read every calendar; write only to calendars this app created.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.app.created",
]
KEYCHAIN_SERVICE = "compass"
KEYCHAIN_USER = "google_refresh_token"


class NotConnected(RuntimeError):
    """No usable Google sign-in: never signed in, or the token was revoked."""


def client() -> tuple[str, str]:
    """The desktop OAuth client from secrets.env."""
    cid, secret = config.secret("GOOGLE_CLIENT_ID"), config.secret("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        raise NotConnected("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not set")
    return cid, secret


def refresh_token() -> str | None:
    return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_USER)


def save_refresh_token(token: str) -> None:
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_USER, token)


def forget() -> None:
    """Remove the stored sign-in."""
    if refresh_token():
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_USER)


class Tokens:
    """Access tokens from the stored refresh token, refreshed shortly before they expire."""

    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=30)
        self.access: str | None = None
        self.expires = 0.0

    def get(self) -> str:
        if self.access and time.time() < self.expires - 60:
            return self.access
        token = refresh_token()
        if not token:
            raise NotConnected("not signed in to Google")
        cid, secret = client()
        r = self.http.post(
            TOKEN_URL,
            data={
                "client_id": cid,
                "client_secret": secret,
                "refresh_token": token,
                "grant_type": "refresh_token",
            },
        )
        if r.status_code in (400, 401):
            raise NotConnected(f"Google refused the refresh token: {r.json().get('error')}")
        r.raise_for_status()
        body = r.json()
        self.access, self.expires = body["access_token"], time.time() + body["expires_in"]
        return self.access


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def sign_in() -> None:
    """Open the browser, receive the code on a loopback port and keep the refresh token."""
    cid, secret = client()
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(16)
    got: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            got.update(query)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Compass is signed in to Google. You can close this tab.")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    params = {
        "client_id": cid,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print(f"Opening the browser to sign in. If it does not open, visit:\n{url}")
    webbrowser.open(url)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join()
    server.server_close()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"Sign-in failed: {got.get('error', 'no code returned')}")
    r = httpx.post(
        TOKEN_URL,
        data={
            "client_id": cid,
            "client_secret": secret,
            "code": got["code"],
            "code_verifier": verifier,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    r.raise_for_status()
    save_refresh_token(r.json()["refresh_token"])
    print("Signed in. The refresh token is in the macOS Keychain.")


if __name__ == "__main__":
    if sys.argv[1:] == ["sign-in"]:
        sign_in()
    elif sys.argv[1:] == ["sign-out"]:
        forget()
        print("Signed out.")
    else:
        sys.exit("usage: python -m app.modules.integrations.google sign-in | sign-out")
