let meta = #{
    name: "vocab-md",
    description: "PDF 단어 목록으로 한글 뜻과 예문 마크다운을 구간별로 병렬 생성",
    when_to_use: "필수 영어단어 PDF에서 뽑은 rank/word 목록으로 vocab/*.md 를 만들 때",
    phases: [
        #{ title: "Generate", detail: "50단어씩 마크다운 파일 병렬 작성" },
        #{ title: "Retry", detail: "실패한 구간만 다시 작성" },
        #{ title: "Verify", detail: "파일 수와 뜻/예문 누락 확인" },
    ],
};

let gen_schema = #{
    "type": "object",
    "required": ["path", "expected", "written", "ok"],
    "properties": #{
        "path": #{ "type": "string" },
        "expected": #{ "type": "integer" },
        "written": #{ "type": "integer" },
        "ok": #{ "type": "boolean" },
        "error": #{ "type": "string" },
    },
};

let verify_schema = #{
    "type": "object",
    "required": ["files", "entries", "ok", "notes"],
    "properties": #{
        "files": #{ "type": "integer" },
        "entries": #{ "type": "integer" },
        "missing_files": #{ "type": "array", "items": #{ "type": "string" } },
        "ok": #{ "type": "boolean" },
        "notes": #{ "type": "string" },
    },
};

fn pad4(n) {
    let s = n.to_string();
    let nlen = s.len();
    if nlen == 1 { return "000" + s; }
    if nlen == 2 { return "00" + s; }
    if nlen == 3 { return "0" + s; }
    s
}

fn chunk_rel(start, stop) {
    "vocab/" + pad4(start) + "-" + pad4(stop) + ".md"
}

fn gen_prompt(root, start, stop, expected, rel) {
    let json_path = root + "/data/chunks/" + pad4(start) + "-" + pad4(stop) + ".json";
    let out_path = root + "/" + rel;
    let p = "";
    p += "You are generating Korean vocabulary markdown for an English word-study site.\n";
    p += "You MUST use tools. Do not answer from memory for the word list.\n\n";
    p += "1. Use read_file to open " + json_path + " (a small JSON array of {rank, word}).\n";
    p += "2. Use every object in that file, in rank order. Ranks are " + start.to_string();
    p += " through " + stop.to_string() + " inclusive.\n";
    p += "3. You must find exactly " + expected.to_string() + " words. If the count differs, set ok=false and explain.\n";
    p += "4. Use the write tool to create " + out_path + " (overwrite if it exists). Parent dirs are fine.\n";
    p += "5. After writing, grep or read_file that same path and count headings that start with '## '.\n";
    p += "6. If the heading count is not " + expected.to_string() + ", fix the file and re-count before you finish.\n\n";
    p += "File format, nothing else:\n\n";
    p += "# 필수 영어단어 " + start.to_string() + "–" + stop.to_string() + "\n\n";
    p += "## {rank}. {word}\n\n";
    p += "- 뜻: {Korean meaning}\n";
    p += "- 예문: {one English sentence}\n\n";
    p += "Blank line between entries. Keep rank and word spelling exactly as in the JSON.\n\n";
    p += "Meaning rules:\n";
    p += "- Korean only, concise, 1-3 most common learner senses.\n";
    p += "- Separate senses with a comma or a semicolon.\n";
    p += "- For function words (the, of, a, to, be), write a short usage gloss, not a grammar essay.\n\n";
    p += "Example rules:\n";
    p += "- Exactly one natural English sentence per word, about 8-16 words.\n";
    p += "- The sentence must use this word in its common sense.\n";
    p += "- Everyday English, not a dictionary quotation.\n";
    p += "- Do not add a Korean translation of the example.\n\n";
    p += "Do not write any other files. Do not skip ranks. Do not add extra sections.\n";
    p += "Return path=" + rel + ", expected=" + expected.to_string();
    p += ", written=heading count, ok=true only when written equals expected.\n";
    p
}

fn verify_prompt(root, file_count, entry_count) {
    let p = "";
    p += "Verify vocabulary markdown under " + root + "/vocab.\n";
    p += "You MUST use tools (list_dir, grep, read_file). Do not guess.\n\n";
    p += "Expected: " + file_count.to_string() + " markdown files named like 0001-0050.md, ";
    p += "and " + entry_count.to_string() + " entries total.\n";
    p += "Ignore README.md if present.\n\n";
    p += "1. list_dir on " + root + "/vocab\n";
    p += "2. grep for ^##  in those .md files and count entries\n";
    p += "3. grep for 뜻: and 예문: and confirm every ## entry has both\n";
    p += "4. Spot-read 2-3 files to confirm the format\n\n";
    p += "ok=true only if file count (excluding README) equals " + file_count.to_string();
    p += " AND entry count equals " + entry_count.to_string();
    p += " AND every entry has both 뜻 and 예문.\n";
    p += "Put short evidence in notes. List missing filenames in missing_files.\n";
    p
}

let root = "C:/dev/english";
let chunk_size = 50;
let max_rank = 6000;
if args != () {
    if args.root != () { root = args.root; }
    if args.chunk_size != () { chunk_size = args.chunk_size; }
    if args.max_rank != () { max_rank = args.max_rank; }
}
if chunk_size < 1 || max_rank < 1 {
    pause("verification", "Pass positive args.chunk_size and args.max_rank.");
}
if chunk_size != 50 {
    pause("verification", "chunk_size must be 50 to match data/chunks JSON files.");
}

let n_chunks = (max_rank + chunk_size - 1) / chunk_size;
log("root=" + root + " max_rank=" + max_rank.to_string() + " chunks=" + n_chunks.to_string());

let chunks = [];
for i in 0..n_chunks {
    let start = i * chunk_size + 1;
    let stop = start + chunk_size - 1;
    if stop > max_rank { stop = max_rank; }
    let expected = stop - start + 1;
    chunks.push(#{
        start: start,
        stop: stop,
        expected: expected,
        rel: chunk_rel(start, stop),
    });
}

phase("Generate");
let jobs = [];
for c in chunks {
    jobs.push(#{
        prompt: gen_prompt(root, c.start, c.stop, c.expected, c.rel),
        label: "gen:" + pad4(c.start) + "-" + pad4(c.stop),
        capability_mode: "read-write",
        output_schema: gen_schema,
    });
}
let results = parallel(jobs);

let failed = [];
let ok_count = 0;
let idx = 0;
for r in results {
    let c = chunks[idx];
    let good = false;
    if r != () && r.success && r.output != () {
        if r.output.ok == true && r.output.written != () {
            if r.output.written == c.expected { good = true; }
        }
    }
    if good {
        ok_count += 1;
    } else {
        failed.push(c);
    }
    idx += 1;
}
log(ok_count.to_string() + "/" + chunks.len().to_string() + " chunks succeeded");

const MAX_RETRY = 40;
if failed.len() > 0 {
    let retry_list = [];
    let overflow = [];
    let n = 0;
    for c in failed {
        if n < MAX_RETRY {
            retry_list.push(c);
        } else {
            overflow.push(c);
        }
        n += 1;
    }
    if overflow.len() > 0 {
        log("retry capped at 40, overflow=" + overflow.len().to_string());
    }
    let b = budget();
    if b.remaining < retry_list.len() + 1 {
        log("skip retry; remaining budget " + b.remaining.to_string());
    } else {
        phase("Retry");
        let rjobs = [];
        for c in retry_list {
            rjobs.push(#{
                prompt: gen_prompt(root, c.start, c.stop, c.expected, c.rel),
                label: "retry:" + pad4(c.start) + "-" + pad4(c.stop),
                capability_mode: "read-write",
                output_schema: gen_schema,
            });
        }
        let rres = parallel(rjobs);
        let j = 0;
        let still = [];
        for r in rres {
            let c = retry_list[j];
            let good = false;
            if r != () && r.success && r.output != () {
                if r.output.ok == true && r.output.written != () {
                    if r.output.written == c.expected { good = true; }
                }
            }
            if good {
                ok_count += 1;
            } else {
                still.push(c);
            }
            j += 1;
        }
        failed = [];
        for c in still { failed.push(c); }
        for c in overflow { failed.push(c); }
        log("after retry ok=" + ok_count.to_string() + " still_failed=" + failed.len().to_string());
    }
}

phase("Verify");
let v = agent(
    verify_prompt(root, chunks.len(), max_rank),
    #{
        label: "verify-vocab",
        capability_mode: "read-only",
        output_schema: verify_schema,
    },
);

let verify_ok = false;
let verify_notes = "";
let files = 0;
let entries = 0;
if v != () && v.success && v.output != () {
    if v.output.ok == true { verify_ok = true; }
    if v.output.notes != () { verify_notes = v.output.notes; }
    if v.output.files != () { files = v.output.files; }
    if v.output.entries != () { entries = v.output.entries; }
}

let failed_rels = [];
for c in failed {
    if c.rel != () { failed_rels.push(c.rel); }
}

let summary = "";
summary += "ok_chunks=" + ok_count.to_string() + "/" + chunks.len().to_string();
summary += " verify_ok=" + verify_ok.to_string();
summary += " files=" + files.to_string();
summary += " entries=" + entries.to_string();
log(summary);

let report = summary + "\n" + verify_notes;
let report_path = write_scratch_file("vocab-md-report.md", report);

complete(#{
    summary: summary,
    report: report_path,
    ok_chunks: ok_count,
    total_chunks: chunks.len(),
    failed: failed_rels,
    verify_ok: verify_ok,
    files: files,
    entries: entries,
});
