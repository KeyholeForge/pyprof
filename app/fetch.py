"""Downloading images from a URL (the `origin` service from docker-compose or another host).

This module WORKS from the start, but it deliberately contains the network
flaw F3 (TCP), in two parts:
  - F3a (exercises 12-13): a new httpx.AsyncClient() on every call.
  - F3b (exercise 13): fetch-batch downloads the URLs sequentially, not in parallel.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

from . import config, storage


async def fetch_one(url: str) -> dict:
    """Downloads a single image from `url` and saves it to local storage.

    NETWORK FLAW (F3a, exercises 12-13): we create a NEW `httpx.AsyncClient()`
    (the `async with` context manager) on EVERY call of this function, instead
    of reusing one session with a connection pool. Consequences (measured, origin
    with a 25 ms delay): every request opens a new TCP connection (203 connections
    for 203 requests in `/nginx_status`), pays for building the client and its
    SSLContext (~2.3 ms CPU) and takes about 2x longer than with a shared client
    (72 ms vs 34 ms).
    The fixed version (one `httpx.AsyncClient` in `app.state`, passed to
    `fetch_one(client, url)`): solutions/fetch_snippets.py.
    """
    async with httpx.AsyncClient() as client:  # F3a: a new client every time
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.content

    image_id = uuid.uuid4().hex
    suffix = Path(urlparse(url).path).suffix or ".jpg"
    dest = config.UPLOAD_DIR / f"{image_id}{suffix}"
    storage.save_bytes(dest, data)
    return {"id": image_id, "url": url, "size": len(data)}


async def fetch_batch(urls: list[str]) -> list[dict]:
    """Downloads a list of URLs and returns a list of results (success or error per URL).

    NETWORK FLAW (F3b, exercise 13): the URLs are downloaded SEQUENTIALLY in a
    `for` loop - every `await fetch_one(url)` waits for the previous one to
    finish. Time grows linearly with the number of URLs (8 URLs with a 25 ms
    origin delay: about 270 ms sequentially vs about 42 ms in parallel). The
    `await` wait is not visible in a sampling profile (no stack of a suspended
    coroutine) - measure the time.
    The fixed version (parallel downloads through `asyncio.gather` on a
    shared client): solutions/fetch_snippets.py.
    """
    results: list[dict] = []
    for url in urls:  # F3b: sequential - should be asyncio.gather(*...)
        try:
            results.append(await fetch_one(url))
        except httpx.HTTPError as exc:
            results.append({"url": url, "error": str(exc)})
    return results
