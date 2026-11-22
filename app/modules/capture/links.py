"""Find, normalise and hash links so the same page is recognised however it is shared."""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
TRACKING = {"fbclid", "gclid", "igshid", "si", "mc_cid", "mc_eid", "ref", "ref_src", "feature"}


def extract(text: str) -> tuple[str | None, str]:
    """The first link in the text, and the text around it."""
    match = URL_RE.search(text)
    if not match:
        return None, text.strip()
    url = match.group(0).rstrip(".,;:!?)]}>'\"")
    rest = (text[: match.start()] + " " + text[match.start() + len(url) :]).strip()
    return url, " ".join(rest.split())


def normalize(url: str) -> str:
    """A canonical form: https, no www, no tracking parameters, fragment or trailing slash."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING
    ]
    if host == "youtu.be" and path:
        host, query, path = "youtube.com", [("v", path.lstrip("/"))], "/watch"
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))


def url_hash(url: str) -> str:
    """Hash of the normalised link."""
    return hashlib.sha256(normalize(url).encode()).hexdigest()


def source_type(url: str) -> str:
    """A guess at what kind of thing the link points to."""
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    path = urlsplit(url).path.lower()
    if host in {"youtube.com", "youtu.be", "m.youtube.com", "vimeo.com"}:
        return "video"
    if host in {"open.spotify.com", "podcasts.apple.com"}:
        return "podcast"
    if host == "github.com":
        return "repo"
    if host in {"arxiv.org"} or path.endswith(".pdf"):
        return "paper"
    if host in {"x.com", "twitter.com"}:
        return "thread"
    return "article"
