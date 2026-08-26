"""One-shot import: vocab/*.md -> english.word

Local:
  C:\\dev\\english\\back\\.venv\\Scripts\\python.exe scripts\\import_words.py

EC2 (SSH tunnel to auto-postgres):
  C:\\dev\\english\\back\\.venv\\Scripts\\python.exe scripts\\import_words.py --ec2
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
VOCAB_DIR = ROOT / "vocab"
ENV_FILE = ROOT / ".env"
PEM = ROOT / "aws" / "test-keypair.pem"

HEAD_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
MEANING_RE = re.compile(r"^-\s*뜻:\s*(.+?)\s*$")
EXAMPLE_RE = re.compile(r"^-\s*예문:\s*(.+?)\s*$")
EXAMPLE_KO_RE = re.compile(r"^-\s*예문번역:\s*(.+?)\s*$")

Row = tuple[int, str, str, str, str]

DDL = """
CREATE SCHEMA IF NOT EXISTS english;
CREATE TABLE IF NOT EXISTS english.word (
    rank INTEGER PRIMARY KEY,
    word TEXT NOT NULL,
    meaning TEXT NOT NULL,
    example TEXT NOT NULL,
    example_ko TEXT NOT NULL
);
ALTER TABLE english.word ADD COLUMN IF NOT EXISTS example_ko TEXT NOT NULL DEFAULT '';
"""

UPSERT = """
INSERT INTO english.word (rank, word, meaning, example, example_ko)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (rank) DO UPDATE
SET word = EXCLUDED.word,
    meaning = EXCLUDED.meaning,
    example = EXCLUDED.example,
    example_ko = EXCLUDED.example_ko;
"""


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def parse_vocab(vocab_dir: Path) -> list[Row]:
    files = sorted(vocab_dir.glob("*.md"))
    if not files:
        raise SystemExit(f"no markdown files in {vocab_dir}")

    by_rank: dict[int, Row] = {}
    errors: list[str] = []

    for path in files:
        rank: int | None = None
        word: str | None = None
        meaning: str | None = None
        example: str | None = None
        example_ko: str | None = None

        def flush() -> None:
            nonlocal rank, word, meaning, example, example_ko
            if rank is None:
                return
            if not word or not meaning or not example or not example_ko:
                errors.append(f"{path.name}: incomplete rank {rank}")
            elif rank in by_rank:
                errors.append(f"{path.name}: duplicate rank {rank}")
            else:
                by_rank[rank] = (rank, word, meaning, example, example_ko)
            rank = word = meaning = example = example_ko = None

        for line in path.read_text(encoding="utf-8").splitlines():
            head = HEAD_RE.match(line)
            if head:
                flush()
                rank = int(head.group(1))
                word = head.group(2).strip()
                continue
            if rank is None:
                continue
            meaning_match = MEANING_RE.match(line)
            if meaning_match:
                meaning = meaning_match.group(1).strip()
                continue
            example_match = EXAMPLE_RE.match(line)
            if example_match:
                example = example_match.group(1).strip()
                continue
            example_ko_match = EXAMPLE_KO_RE.match(line)
            if example_ko_match:
                example_ko = example_ko_match.group(1).strip()

        flush()

    if errors:
        preview = "\n".join(errors[:20])
        raise SystemExit(f"parse errors ({len(errors)}):\n{preview}")

    rows = [by_rank[n] for n in sorted(by_rank)]
    expected = list(range(1, 6001))
    got = [row[0] for row in rows]
    if got != expected:
        missing = [n for n in expected if n not in by_rank]
        raise SystemExit(f"expected ranks 1-6000, got {len(rows)}; missing {missing[:20]}")
    empty = [row[0] for row in rows if not row[1] or not row[2] or not row[3] or not row[4]]
    if empty:
        raise SystemExit(f"empty fields at ranks {empty[:20]}")
    return rows


def connect(env: dict[str, str], host: str, port: int) -> psycopg.Connection:
    return psycopg.connect(
        host=host,
        port=port,
        user=env["PGUSER"],
        password=env["PGPASSWORD"],
        dbname=env["PGDATABASE"],
        row_factory=dict_row,
    )


def import_rows(conn: psycopg.Connection, rows: list[Row]) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(UPSERT, rows)
    conn.commit()


def verify(conn: psycopg.Connection, rows: list[Row]) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM english.word")
        count = cur.fetchone()["n"]
        cur.execute("SELECT MIN(rank) AS mn, MAX(rank) AS mx FROM english.word")
        span = cur.fetchone()
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM english.word
            WHERE word = '' OR meaning = '' OR example = '' OR example_ko = ''
            """
        )
        empty = cur.fetchone()["n"]
        cur.execute(
            """
            SELECT rank, word, meaning, example, example_ko
            FROM english.word
            WHERE rank IN (1, 1000, 3001, 6000)
            ORDER BY rank
            """
        )
        samples = cur.fetchall()

    print(f"db count={count} min={span['mn']} max={span['mx']} empty={empty}")
    if count != 6000 or span["mn"] != 1 or span["mx"] != 6000 or empty != 0:
        raise SystemExit("verification failed: count/range/empty")

    parsed = {row[0]: row for row in rows}
    for sample in samples:
        expected = parsed[sample["rank"]]
        got = (
            sample["rank"],
            sample["word"],
            sample["meaning"],
            sample["example"],
            sample["example_ko"],
        )
        if got != expected:
            raise SystemExit(f"sample mismatch rank {sample['rank']}: {got!r} != {expected!r}")
        print(f"  ok {sample['rank']}. {sample['word']} / {sample['meaning']}")
    print("verify ok")


def wait_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise SystemExit(f"tunnel did not open on {host}:{port}")


def tighten_pem(pem: Path) -> None:
    if os.name != "nt":
        os.chmod(pem, 0o600)
        return
    user = os.environ["USERNAME"]
    subprocess.run(["icacls", str(pem), "/inheritance:r"], check=True, capture_output=True)
    subprocess.run(
        ["icacls", str(pem), "/grant:r", f"{user}:R"],
        check=True,
        capture_output=True,
    )


def ssh_tunnel(env: dict[str, str], local_port: int) -> subprocess.Popen:
    host = env["EC2_HOST"]
    user = env.get("EC2_USER", "ubuntu")
    if not PEM.exists():
        raise SystemExit(f"missing PEM: {PEM}")
    tighten_pem(PEM)
    cmd = [
        "ssh",
        "-i",
        str(PEM),
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ExitOnForwardFailure=yes",
        "-N",
        "-L",
        f"127.0.0.1:{local_port}:127.0.0.1:5432",
        f"{user}@{host}",
    ]
    proc = subprocess.Popen(cmd)
    try:
        wait_port("127.0.0.1", local_port)
    except Exception:
        proc.terminate()
        raise
    return proc


def main() -> None:
    parser = argparse.ArgumentParser(description="Import vocab markdown into english.word")
    parser.add_argument("--ec2", action="store_true", help="import via SSH tunnel to EC2 postgres")
    parser.add_argument("--tunnel-port", type=int, default=15432)
    args = parser.parse_args()

    if not ENV_FILE.exists():
        raise SystemExit(f"missing {ENV_FILE}")

    env = load_env(ENV_FILE)
    rows = parse_vocab(VOCAB_DIR)
    print(f"parsed {len(rows)} words from {VOCAB_DIR}")

    if args.ec2:
        print(f"tunnel {env.get('EC2_HOST')} -> 127.0.0.1:{args.tunnel_port}")
        proc = ssh_tunnel(env, args.tunnel_port)
        host, port = "127.0.0.1", args.tunnel_port
    else:
        proc = None
        host, port = env.get("PGHOST", "127.0.0.1"), int(env.get("PGPORT", "5432"))

    try:
        with connect(env, host, port) as conn:
            print(f"connected {env['PGUSER']}@{host}:{port}/{env['PGDATABASE']}")
            import_rows(conn, rows)
            verify(conn, rows)
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
