import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "words.json")
OUT_DIR = os.path.join(ROOT, "data", "chunks")
CHUNK = 50


def pad4(n: int) -> str:
    return f"{n:04d}"


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        words = json.load(f)

    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for start_idx in range(0, len(words), CHUNK):
        chunk = words[start_idx : start_idx + CHUNK]
        start = chunk[0]["rank"]
        stop = chunk[-1]["rank"]
        path = os.path.join(OUT_DIR, f"{pad4(start)}-{pad4(stop)}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
            f.write("\n")
        count += 1

    print(f"wrote {count} chunk files to {OUT_DIR}")


if __name__ == "__main__":
    main()
