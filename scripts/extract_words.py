import glob
import json
import os
import re

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS_DIR = os.path.join(ROOT, "words")
DATA_DIR = os.path.join(ROOT, "data")

# rank may contain commas: 1,000  5,001
LINE_RE = re.compile(r"^(\d{1,3}(?:,\d{3})*)\s+([A-Za-z][A-Za-z'\-.]*)\s+\d")
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")


def main() -> None:
    pdfs = sorted(glob.glob(os.path.join(WORDS_DIR, "*.pdf")))
    all_words = []
    seen = set()
    dups = []

    for pdf_path in pdfs:
        with pdfplumber.open(pdf_path) as doc:
            for page in doc.pages:
                text = page.extract_text() or ""
                for raw in text.splitlines():
                    line = raw.strip()
                    match = LINE_RE.match(line)
                    if not match:
                        continue
                    rank = int(match.group(1).replace(",", ""))
                    word = match.group(2)
                    if rank in seen:
                        dups.append({"rank": rank, "word": word})
                        continue
                    seen.add(rank)
                    all_words.append({"rank": rank, "word": word})

    all_words.sort(key=lambda item: item["rank"])
    max_rank = all_words[-1]["rank"] if all_words else 0
    missing = [n for n in range(1, max_rank + 1) if n not in seen]
    weird = [item for item in all_words if not WORD_RE.fullmatch(item["word"])]

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "words.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {out_path}")
    print(f"total={len(all_words)} min={all_words[0]} max={all_words[-1]}")
    print(f"missing={len(missing)} {missing[:30]}")
    print(f"dups={len(dups)} {dups[:10]}")
    print(f"weird={len(weird)} {weird[:20]}")


if __name__ == "__main__":
    main()
