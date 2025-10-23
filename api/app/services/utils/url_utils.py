import asyncio
import random
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime
from firecrawl import AsyncFirecrawl
import httpx
from app.config import settings

# See https://docs.firecrawl.dev/sdks/python#async-class
firecrawl = AsyncFirecrawl(api_key=settings.firecrawl_api_key)
async def scrape_url(url: str, formats: list[str] = ['summary'], timeout: int = 20*1000):
    scrape_result = await firecrawl.scrape(url, formats=formats, timeout=timeout)
    return scrape_result


# ##########################################################
# The code below doesn't actually work well due to anti-scraping measures
# ##########################################################

def _normalize_url(url: str) -> str:
    u = url.strip()
    if not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    return u

def _parse_retry_after(value: str) -> float:
    try:
        value = value.strip()
        if value.isdigit():
            return max(0.0, float(value))
        dt = parsedate_to_datetime(value)
        return max(0.0, (dt - dt.now(dt.tzinfo)).total_seconds())
    except Exception:
        return 0.0

async def _probe_once(
    client: httpx.AsyncClient,
    url: str,
    connect_timeout: float,
    read_timeout: float,
) -> Dict:
    timeout = httpx.Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=read_timeout,
        pool=connect_timeout,
    )

    # Stream to avoid downloading the body
    try:
        async with client.stream("GET", url, follow_redirects=True, timeout=timeout) as resp:
            status = resp.status_code
            final_url = str(resp.url)
            headers = dict(resp.headers)
        return {"status": status, "final_url": final_url, "headers": headers, "error": None}
    except httpx.TimeoutException as e:
        return {"status": None, "final_url": url, "headers": {}, "error": "timeout"}
    except httpx.HTTPError as e:
        return {"status": None, "final_url": url, "headers": {}, "error": "network_error"}

async def check_url_validity_async(
    url: str,
    *,
    require_status: int = 200,
    max_attempts: int = 3,
    connect_timeout: float = 3.0,
    read_timeout: float = 5.0,
    total_time_limit: float = 8.0,
    backoff_base: float = 0.5,
    backoff_max_sleep: float = 2.0,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict:
    """
    Minimal 'X-like' URL validity check:
      - Follows redirects; inspects final response code.
      - Only counts as valid if status == require_status (default 200).
      - If not 200 or on transient error, retries briefly with backoff.
      - No JS rendering or special headers (will yield occasional false negatives).
    Returns:
      {
        'input_url', 'final_url', 'status', 'valid',
        'attempts', 'elapsed_ms', 'reason'
      }
    """
    import time
    input_url = url
    url = _normalize_url(url)
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(http2=True)  # HTTP/2 helps with some CDNs, harmless otherwise
    start = time.time()
    attempts = 0
    last = {"status": None, "final_url": url, "headers": {}, "error": None}
    reason = "network_error"

    try:
        while attempts < max_attempts and (time.time() - start) < total_time_limit:
            attempts += 1
            last = await _probe_once(client, url, connect_timeout, read_timeout)
            status = last["status"]
            url = last["final_url"]  # follow next attempts at the resolved URL
            if status == require_status:
                reason = "ok"
                break

            # Respect Retry-After for 429/503 etc., but keep it short
            retry_after = 0.0
            if status in (429, 503) and "Retry-After" in last["headers"]:
                retry_after = _parse_retry_after(last["headers"]["Retry-After"])

            sleep_s = max(
                retry_after,
                min(backoff_base * (2 ** (attempts - 1)) + random.uniform(0, 0.1), backoff_max_sleep)
            )
            # Ensure total time limit
            remaining = total_time_limit - (time.time() - start)
            if remaining <= 0:
                break
            await asyncio.sleep(min(sleep_s, max(0.0, remaining)))

            reason = (
                "non_200" if status is not None else last["error"] or "network_error"
            )

        elapsed_ms = round((time.time() - start) * 1000.0, 1)
        return {
            "input_url": input_url,
            "final_url": last["final_url"],
            "status": last["status"],
            "valid": last["status"] == require_status,
            "attempts": attempts,
            "elapsed_ms": elapsed_ms,
            "reason": reason if last["status"] != require_status else "ok",
        }
    finally:
        if own_client:
            await client.aclose()

async def check_urls_validity(
    urls: List[str],
    *,
    concurrency: int = 8,
    **kwargs,
) -> List[Dict]:
    """
    Run checks in parallel with a concurrency cap.
    kwargs are forwarded to check_url_validity_async (e.g., timeouts, attempts).
    """
    sem = asyncio.Semaphore(concurrency)
    results: List[Dict] = []
    async with httpx.AsyncClient(http2=True) as client:
        async def worker(u: str):
            async with sem:
                return await check_url_validity_async(u, client=client, **kwargs)

        tasks = [asyncio.create_task(worker(u)) for u in urls]
        for t in asyncio.as_completed(tasks):
            results.append(await t)
    # Preserve input order
    mapping = {r['input_url']: r for r in results}
    return [mapping[u] for u in urls]
