#!/usr/bin/env python3
"""Fetch the current official PC installer URL from the bilibili game center API.

The endpoint requires a Referer header from the game center page, otherwise it
returns 403. No authentication is involved.
"""
import json
import sys
import urllib.request

API = "https://line3-h5-pc-api.biligame.com/game/detail/gameinfo?game_base_id=105667"
HEADERS = {
    "Referer": "https://www.biligame.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


def main() -> int:
    req = urllib.request.Request(API, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001 - surface any network/parse failure
        print(f"请求失败: {exc}", file=sys.stderr)
        return 1

    link = data.get("data", {}).get("pc_download_link")
    if not link:
        print("响应中没有 pc_download_link，接口可能已变更", file=sys.stderr)
        return 1

    print(link)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
