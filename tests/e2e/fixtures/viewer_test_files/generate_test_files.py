#!/usr/bin/env python3
"""Generate minimal valid test files for every workspace viewer format.

Run once to create the fixture set, or re-run to regenerate.
All binary files are minimal valid specimens — no external dependencies needed.
"""

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).parent


def write(name: str, data: bytes | str) -> None:
    path = OUT / name
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)
    print(f"  {name} ({path.stat().st_size} bytes)")


# ── Text formats ─────────────────────────────────────────────────────
def gen_text():
    write("sample.txt", "Hello, Workspace Viewer!\nThis is a plain text file.\n")
    write("sample.py", 'def greet():\n    return "Hello from sample.py"\n')
    write(
        "sample.md",
        "# Sample Markdown\n\nThis is **bold** and *italic*.\n\n- Item 1\n- Item 2\n",
    )
    write("sample.json", '{\n  "name": "test",\n  "value": 42\n}\n')
    write(
        "sample.tex",
        "\\documentclass{article}\n\\begin{document}\nHello \\LaTeX.\n\\end{document}\n",
    )


# ── CSV / TSV ────────────────────────────────────────────────────────
def gen_csv():
    write("sample.csv", "name,value,category\nalpha,1.0,A\nbeta,2.5,B\ngamma,3.7,A\n")
    write(
        "sample.tsv",
        "name\tvalue\tcategory\nalpha\t1.0\tA\nbeta\t2.5\tB\ngamma\t3.7\tA\n",
    )


# ── Mermaid ──────────────────────────────────────────────────────────
def gen_mermaid():
    write(
        "sample.mmd",
        "graph TD\n    A[Start] --> B{Decision}\n    B -->|Yes| C[OK]\n    B -->|No| D[Retry]\n",
    )


# ── PNG (minimal 1×1 red pixel) ─────────────────────────────────────
def gen_png():
    def _chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return (
            struct.pack(">I", len(data))
            + c
            + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\x00\x00")  # filter=none, R=255, G=0, B=0
    idat = _chunk(b"IDAT", raw)
    iend = _chunk(b"IEND", b"")
    write("sample.png", sig + ihdr + idat + iend)


# ── SVG ──────────────────────────────────────────────────────────────
def gen_svg():
    write(
        "sample.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
        '  <circle cx="50" cy="50" r="40" fill="#4a90d9" stroke="#2c5f8a" stroke-width="3"/>\n'
        '  <text x="50" y="55" text-anchor="middle" fill="white" font-size="14">SVG</text>\n'
        "</svg>\n",
    )


# ── PDF (minimal valid) ─────────────────────────────────────────────
def gen_pdf():
    # Minimal valid PDF with one page showing "Hello PDF"
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    stream = b"BT /F1 16 Tf 20 50 Td (Hello PDF) Tj ET"
    objects.append(
        f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    body = b""
    offsets = []
    header = b"%PDF-1.4\n"
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)

    xref_pos = pos
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()

    write("sample.pdf", header + body + xref + trailer)


# ── MP3 (minimal valid — single silent MPEG frame) ──────────────────
def gen_mp3():
    # MPEG1 Layer3, 128kbps, 44100Hz, stereo — one silent frame = 417 bytes
    header = bytes([0xFF, 0xFB, 0x90, 0x00])  # sync + MPEG1/Layer3/128k/44100/stereo
    padding = b"\x00" * 413  # silent frame payload
    write("sample.mp3", header + padding)


# ── MP4 (minimal valid — ftyp + moov + mdat) ────────────────────────
def gen_mp4():
    def box(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload) + 8) + tag + payload

    ftyp = box(b"ftyp", b"isom\x00\x00\x00\x00isom")
    # Minimal moov with mvhd
    mvhd = box(b"mvhd", b"\x00" * 100)  # version 0 mvhd
    moov = box(b"moov", mvhd)
    mdat = box(b"mdat", b"\x00" * 8)
    write("sample.mp4", ftyp + moov + mdat)


# ── WAV (minimal valid — 1 sample of silence) ───────────────────────
def gen_wav():
    # PCM 16-bit mono 44100Hz, 1 sample
    data = struct.pack("<h", 0)
    fmt_chunk = struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, 44100, 88200, 2, 16)
    data_chunk = struct.pack("<4sI", b"data", len(data)) + data
    riff_size = 4 + len(fmt_chunk) + len(data_chunk)
    header = struct.pack("<4sI4s", b"RIFF", riff_size, b"WAVE")
    write("sample.wav", header + fmt_chunk + data_chunk)


def main():
    print("Generating test files:")
    gen_text()
    gen_csv()
    gen_mermaid()
    gen_png()
    gen_svg()
    gen_pdf()
    gen_mp3()
    gen_mp4()
    gen_wav()
    print("Done.")


if __name__ == "__main__":
    main()
