#!/usr/bin/env python3
"""Switch the Genshin CN client channel and launch the matching launcher.

The game keeps a single ``config.ini`` in its install directory, so the official
and bilibili launchers cannot both be "correct" at the same time. Whichever
launcher starts while the config still holds the other channel prints a
transient ``Not match region`` dialog before recovering.

This script rewrites the channel fields (and ``plugin_sdk_version``) to the
requested channel, then starts the corresponding launcher.

Examples:
    python switch_channel.py official
    python switch_channel.py bilibili
    python switch_channel.py official --dry-run
    python switch_channel.py bilibili \\
        --game-config "D:\\Games\\Genshin Impact Game\\config.ini" \\
        --bilibili-launcher "D:\\GenshinBili\\launcher.exe"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Defaults match a typical layout; override with the CLI flags if yours differs.
DEFAULT_GAME_CONFIG = Path(r"E:\miHoYo Launcher\games\Genshin Impact Game\config.ini")
DEFAULT_OFFICIAL = Path(r"E:\miHoYo Launcher\launcher.exe")
DEFAULT_BILIBILI = Path(r"E:\smm-dshconversation\bili-launcher\launcher.exe")

# channel / sub_channel / cps are read from each launcher's own config.ini.
# plugin_sdk_version is written by the bilibili launcher during its initial
# setup; the official channel does not need it.
PROFILES = {
    "official": {"channel": "1", "sub_channel": "1", "cps": "hyp_mihoyo", "sdk": None},
    "bilibili": {"channel": "14", "sub_channel": "0", "cps": "bilibili", "sdk": "5.0.4"},
}


def rewrite(text: str, profile: dict) -> str:
    """Return ``text`` with the channel keys replaced in place."""
    out: list[str] = []
    had_sdk = False
    for line in text.splitlines(keepends=True):
        key = line.split("=", 1)[0].strip()
        if key == "channel":
            out.append(f"channel={profile['channel']}\n")
        elif key == "sub_channel":
            out.append(f"sub_channel={profile['sub_channel']}\n")
        elif key == "cps":
            out.append(f"cps={profile['cps']}\n")
        elif key == "plugin_sdk_version":
            had_sdk = True
            if profile["sdk"]:
                out.append(f"plugin_sdk_version={profile['sdk']}\n")
        else:
            out.append(line)
    if profile["sdk"] and not had_sdk:
        out.append(f"plugin_sdk_version={profile['sdk']}\n")
    return "".join(out)


def kill_stale_launchers() -> None:
    """清理"没有窗口"的残留启动器进程。

    米哈游启动器用单实例锁：如果上一次异常退出留下了一个没有窗口的
    HYP.exe，新启动的实例会把请求转给它然后自己退出，表现就是"点了没反应"。
    这里只清理确实没有可见窗口的进程，正常开着的启动器不受影响。
    """
    if sys.platform != "win32":
        return

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    def has_visible_window(pid: int) -> bool:
        hits: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd):
                owner = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if owner.value == pid:
                    hits.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        return bool(hits)

    try:
        listing = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq HYP.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:  # noqa: BLE001 - best effort only
        return

    for line in listing.stdout.splitlines():
        fields = [field.strip('"') for field in line.split('","')]
        if len(fields) < 2 or not fields[0].lower().startswith("hyp"):
            continue
        try:
            pid = int(fields[1])
        except ValueError:
            continue
        if not has_visible_window(pid):
            print(f"清理无窗口的残留启动器进程 pid={pid}")
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("mode", choices=sorted(PROFILES), help="目标渠道")
    ap.add_argument("--game-config", type=Path, default=DEFAULT_GAME_CONFIG,
                    help=f"游戏 config.ini 路径（默认: {DEFAULT_GAME_CONFIG}）")
    ap.add_argument("--official-launcher", type=Path, default=DEFAULT_OFFICIAL,
                    help=f"官服启动器路径（默认: {DEFAULT_OFFICIAL}）")
    ap.add_argument("--bilibili-launcher", type=Path, default=DEFAULT_BILIBILI,
                    help=f"B服启动器路径（默认: {DEFAULT_BILIBILI}）")
    ap.add_argument("--dry-run", action="store_true", help="只打印结果，不写盘、不启动")
    ap.add_argument("--no-launch", action="store_true", help="只改配置，不启动启动器")
    args = ap.parse_args()

    cfg = args.game_config
    if not cfg.is_file():
        print(f"找不到游戏配置: {cfg}", file=sys.stderr)
        return 1

    profile = PROFILES[args.mode]
    with open(cfg, "r", encoding="utf-8", newline="") as f:
        old = f.read()
    new = rewrite(old, profile)

    if args.dry_run:
        print(new)
        return 0

    if new != old:
        with open(cfg, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        print(f"config.ini -> {args.mode}")
    else:
        print(f"config.ini 已是 {args.mode}，无需修改")

    if args.no_launch:
        return 0

    launcher = args.official_launcher if args.mode == "official" else args.bilibili_launcher
    if not launcher.is_file():
        print(f"找不到启动器: {launcher}", file=sys.stderr)
        return 1
    print(f"starting {launcher.name} ...")
    kill_stale_launchers()
    subprocess.Popen([str(launcher)], cwd=str(launcher.parent))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
