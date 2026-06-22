from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(user_agent: str) -> requests.Session:
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1.2,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset({"GET"}))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
    })
    return session


def dns_info(url: str) -> dict:
    host = urlsplit(url).hostname or ""
    result = {"hostname": host}
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        result["addresses"] = sorted({item[4][0] for item in infos})
    except OSError as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def is_html(text: str) -> bool:
    sample = text[:2000].lower()
    return "<html" in sample or "<!doctype html" in sample or "<table" in sample


def fetch_requests(session: requests.Session, url: str, timeout: int) -> tuple[str, str]:
    parts = urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}/"
    try:
        warmup = session.get(root, timeout=timeout)
        print(f"[requests] warm-up HTTP {warmup.status_code}")
    except requests.RequestException as exc:
        print(f"[requests] warm-up failed: {exc}")
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    if not is_html(response.text):
        raise RuntimeError("response does not look like HTML")
    return response.text, response.url


def fetch_curl(url: str, user_agent: str, timeout: int) -> tuple[str, str]:
    command = [
        "curl", "--fail", "--location", "--compressed", "--silent", "--show-error",
        "--connect-timeout", str(min(timeout, 15)), "--max-time", str(timeout),
        "--retry", "3", "--retry-delay", "2", "--user-agent", user_agent,
        "--write-out", "\n__FINAL_URL__:%{url_effective}", url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl exit code {result.returncode}")
    marker = "\n__FINAL_URL__:"
    html, final_url = result.stdout.rsplit(marker, 1) if marker in result.stdout else (result.stdout, url)
    if not is_html(html):
        raise RuntimeError("curl response does not look like HTML")
    return html, final_url.strip()


def acquire(urls: list[str], user_agent: str, timeout: int, delay: float,
            diagnostics_dir: str | Path) -> tuple[str, str]:
    session = build_session(user_agent)
    report = {"attempts": []}
    directory = Path(diagnostics_dir)
    directory.mkdir(parents=True, exist_ok=True)

    for url in urls:
        dns = dns_info(url)
        print(f"[dns] {json.dumps(dns, ensure_ascii=False)}")
        time.sleep(delay)
        for name, fn in (
            ("requests-session", lambda: fetch_requests(session, url, timeout)),
            ("curl", lambda: fetch_curl(url, user_agent, timeout)),
        ):
            try:
                html, final_url = fn()
                report["attempts"].append({"url": url, "method": name, "result": "success", "final_url": final_url, "dns": dns})
                (directory / "diagnostics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                (directory / "last-response.html").write_text(html, encoding="utf-8")
                print(f"[{name}] success: {len(html.encode('utf-8'))} bytes")
                return html, final_url
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                print(f"[{name}] failed: {message}")
                report["attempts"].append({"url": url, "method": name, "result": "failed", "error": message, "dns": dns})

    (directory / "diagnostics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    raise RuntimeError("all acquisition methods failed")
