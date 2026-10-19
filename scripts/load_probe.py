"""Bounded read-only HTTP benchmark for isolated loopback staging, no credentials or writes."""

import argparse
import json
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    url = urlsplit(options.url)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or url.username
        or url.query
        or url.fragment
        or url.path not in {"/", "/entdecken/"}
    ):
        parser.error(
            "Only public read-only loopback staging endpoints, without redirects or secrets."
        )
    if not 1 <= options.requests <= 500 or not 1 <= options.concurrency <= 20:
        parser.error("Bounded to 500 reads and 20 parallel clients.")

    def read(_):
        start = perf_counter()
        try:
            with build_opener(NoRedirect).open(
                Request(options.url, headers={"User-Agent": "Deelvo-isolated-load-probe"}),
                timeout=30,
            ) as response:
                response.read(2 * 1024 * 1024)
                status = response.status
        except Exception:
            status = 0
        return (perf_counter() - start) * 1000, status

    start = perf_counter()
    with ThreadPoolExecutor(max_workers=options.concurrency) as pool:
        rows = list(pool.map(read, range(options.requests)))
    timings = sorted(r[0] for r in rows)
    report = dict(
        requests=len(rows),
        concurrency=options.concurrency,
        errors=sum(s != 200 for _, s in rows),
        p50_ms=round(statistics.median(timings), 2),
        p95_ms=round(timings[math.ceil(0.95 * len(timings)) - 1], 2),
        max_ms=round(max(timings), 2),
        elapsed_seconds=round(perf_counter() - start, 3),
        scope="Synthetic loopback catalog only; no production, private/API or hardware guarantee.",
    )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if report["errors"]:
        raise SystemExit("HTTP errors during isolated load probe")


if __name__ == "__main__":
    main()
