#!/usr/bin/env python3
"""Extract the embedded 7z payload from the official installer.

The installer is a PE executable whose real content lives in a 7z archive
appended after the last PE section. We locate that archive, split it out,
and let 7-Zip unpack it into a working directory.

This script only reads files on your machine; it downloads nothing.
"""
import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SEVENZ_MAGIC = b"\x37\x7a\xbc\xaf\x27\x1c"


def pe_sections_end(data: bytes) -> int:
    """Return the byte offset just past the last PE section's raw data."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe : pe + 4] != b"PE\0\0":
        raise SystemExit("不是有效的 PE 文件")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    size_opt = struct.unpack_from("<H", data, pe + 20)[0]
    table = pe + 24 + size_opt
    end = 0
    for i in range(nsec):
        off = table + i * 40
        raw_size = struct.unpack_from("<I", data, off + 16)[0]
        raw_ptr = struct.unpack_from("<I", data, off + 20)[0]
        end = max(end, raw_ptr + raw_size)
    return end


def find_payload_offset(data: bytes) -> int:
    """Find the 7z header that follows the PE sections."""
    start = pe_sections_end(data)
    idx = data.find(SEVENZ_MAGIC, start)
    if idx < 0:  # fall back to a full scan in case the layout differs
        idx = data.find(SEVENZ_MAGIC)
    if idx < 0:
        raise SystemExit("未找到内嵌的 7z 数据，可能不是预期的安装器")
    return idx


def find_7z() -> str:
    for name in ("7z", "7za", "7z.exe"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    raise SystemExit("未找到 7-Zip，请先安装: https://www.7-zip.org/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("installer", help="下载好的安装器 exe")
    ap.add_argument("-o", "--out", default="bili-launcher", help="解压目标目录")
    ap.add_argument("--keep-payload", action="store_true", help="保留切出的 7z 文件")
    args = ap.parse_args()

    src = Path(args.installer)
    if not src.is_file():
        raise SystemExit(f"文件不存在: {src}")

    data = src.read_bytes()
    offset = find_payload_offset(data)
    print(f"payload offset = {offset}, size = {len(data) - offset}")

    payload = src.with_name(src.name + ".payload.7z")
    payload.write_bytes(data[offset:])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([find_7z(), "x", str(payload), f"-o{out}", "-y"], check=True)

    # The launcher entry point must sit one level above the version directory.
    for entry in out.iterdir():
        exe = entry / "launcher.exe"
        if entry.is_dir() and exe.is_file():
            shutil.copy2(exe, out / "launcher.exe")
            print(f"copied launcher.exe from {entry.name}/")
            break

    if not args.keep_payload:
        payload.unlink()

    print(f"done -> {out}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
