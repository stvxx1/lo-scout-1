"""Profile portraits: pick the right URL, escape it, and fail visibly.

Three things about the source data drive this module:

* Freeones serves portraits through a **signed** imgproxy URL
  (``/photo/<id>/.../fit-in/350x466/...``). Rewriting ``350x466`` to anything
  larger returns **403**, so the scraped URL is used verbatim and the browser
  is never asked for a variant we are not allowed to have.
* Names are arbitrary text. Interpolating one straight into ``alt="..."``
  terminates the attribute as soon as it contains a quote, and the image then
  silently fails to render -- so every value here goes through
  :func:`html.escape`.
* Any host can 404 tomorrow. A failed load hides the ``<img>`` and reveals a
  tinted initials tile instead of a broken-image icon.

Nothing here imports Streamlit, so it stays testable offline.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import re
from typing import List, Optional
from urllib.parse import urlparse

from paths import thumbs_dir

#: Portrait aspect used by the cards (Freeones serves exactly this size).
PORTRAIT_SIZE = (350, 466)

#: Refuse to inline anything bigger than this as a data-URI.
MAX_INLINE_BYTES = 60_000

_ALLOWED_SCHEMES = ("https", "http")
_SRCSET_ENTRY = re.compile(r"\s*,\s*")
_WORD_SPLIT = re.compile(r"[^\w]+")
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def normalize_image_url(url: str) -> str:
    """Return an absolute http(s) URL, or ``""`` for anything unusable.

    Rejects empty strings, placeholders (``data:``) and script URLs, and
    upgrades protocol-relative ``//cdn/...`` references to https.
    """
    url = (url or "").strip()
    if not url or url.startswith("data:"):
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        return ""
    return url


def pick_largest_srcset(srcset: str) -> str:
    """Return the widest candidate from a ``srcset`` attribute (or ``""``)."""
    best_url, best_weight = "", -1.0
    for entry in _SRCSET_ENTRY.split(srcset or ""):
        parts = entry.strip().split()
        if not parts:
            continue
        candidate, weight = parts[0], 0.0
        if len(parts) > 1:
            descriptor = parts[1].lower()
            try:
                if descriptor.endswith("w"):
                    weight = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    # Density descriptors: scale so 2x outranks 1x.
                    weight = float(descriptor[:-1]) * 1000
            except ValueError:
                weight = 0.0
        if weight > best_weight:
            best_url, best_weight = candidate, weight
    return normalize_image_url(best_url)


def initials(name: str) -> str:
    """Return up to two initials for the fallback tile."""
    words: List[str] = [word for word in _WORD_SPLIT.split(name or "") if word]
    letters = "".join(word[0] for word in words[:2]).upper()
    return letters or "?"


def avatar_tint(name: str) -> str:
    """Return a stable background colour so placeholder tiles stay distinct."""
    digest = hashlib.sha1((name or "").encode("utf-8")).digest()
    return f"hsl({digest[0] * 360 // 256}, 42%, 20%)"

def portrait_html(name: str, url: str = "", fallback_url: str = "") -> str:
    """Return the ``<img>`` (plus its fallback tile) for a card's image box.

    The tile is always rendered *behind* the image, so a failed load degrades
    to initials with no layout shift and no broken-image icon.
    """
    safe_name = html.escape(name or "", quote=True)
    source = normalize_image_url(url) or normalize_image_url(fallback_url)

    tile = (
        f'<div class="img-fallback" aria-hidden="true" style="--tint: {avatar_tint(name)}">'
        f"<span>{html.escape(initials(name))}</span></div>"
    )
    if not source:
        return tile

    width, height = PORTRAIT_SIZE
    return (
        f"{tile}"
        f'<img src="{html.escape(source, quote=True)}" alt="{safe_name}" '
        f'width="{width}" height="{height}" loading="lazy" decoding="async" '
        f'referrerpolicy="no-referrer" '
        f"""onerror="this.classList.add('img-broken')">"""
    )


def cached_portrait(url: str, size: tuple = PORTRAIT_SIZE, timeout: int = 20) -> Optional[bytes]:
    """Download a portrait, downscale it, and cache the JPEG on disk.

    Only used for fallback sources (StashDB hands out multi-megabyte
    originals), so the result is a small JPEG suitable for inlining.
    """
    url = normalize_image_url(url)
    if not url:
        return None

    cache_path = thumbs_dir() / f"{hashlib.sha1(url.encode('utf-8')).hexdigest()}.jpg"
    if cache_path.exists():
        return cache_path.read_bytes()

    raw = _download(url, timeout=timeout)
    if not raw:
        return None

    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow ships with Streamlit
        return raw

    try:
        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
        image.thumbnail(size, Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=82, optimize=True)
        data = buffer.getvalue()
    except Exception:
        return None

    cache_path.write_bytes(data)
    return data


def to_data_uri(data: bytes, mime: str = "image/jpeg") -> str:
    """Inline image bytes as a ``data:`` URI (empty string when too large)."""
    if not data or len(data) > MAX_INLINE_BYTES:
        return ""
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _download(url: str, timeout: int = 20) -> bytes:
    """Fetch raw bytes, returning ``b""`` on any failure."""
    try:
        import requests
    except ImportError:  # pragma: no cover
        return b""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT, "Accept": "image/*"},
        )
        response.raise_for_status()
        return response.content
    except Exception:
        return b""
