let meta = #{
    name: "example-ko",
    description: "예문 한글 번역을 vocab 마크다운에 넣고 DB/API/화면에 반영",
    when_to_use: "영어 예문의 한글 번역(example_ko)을 데이터와 DB에 추가할 때",
    phases: [
        #{ title: "Schema", detail: "컬럼, import, API, 테스트, 카드 표시" },
        #{ title: "Translate", detail: "vocab 50단어씩 예문번역 병렬 작성" },
        #{ title: "Retry", detail: "실패한 구간만 다시 작성" },
        #{ title: "Import", detail: "로컬과 EC2 english.word 갱신" },
        #{ title: "Verify", detail: "마크다운과 DB 샘플 확인" },
    ],
};

let ok_schema = #{
    "type": "object",
    "required": ["ok", "notes"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "notes": #{ "type": "string" },
        "files": #{ "type": "array", "items": #{ "type": "string" } },
    },
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

let import_schema = #{
    "type": "object",
    "required": ["ok", "local_ok", "ec2_ok", "notes"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "local_ok": #{ "type": "boolean" },
        "ec2_ok": #{ "type": "boolean" },
        "notes": #{ "type": "string" },
    },
};

let verify_schema = #{
    "type": "object",
    "required": ["ok", "files", "entries", "with_ko", "notes"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "files": #{ "type": "integer" },
        "entries": #{ "type": "integer" },
        "with_ko": #{ "type": "integer" },
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

fn schema_prompt(root) {
    let p = "";
    p += "Add Korean example translations (example_ko) to the english vocab app at " + root + ".\n";
    p += "You MUST use tools (read_file, search_replace, grep). Do not answer from memory.\n\n";
    p += "Product rules: runtime learning API reads Postgres english.word only, never vocab/ or PDF.\n";
    p += "Source for import is vocab/*.md. Do not create raw SQL tables that disagree with SQLAlchemy models.\n";
    p += "After API changes, update back/tests. Dates stay Asia/Seoul. Commit messages if you commit must be Korean — do not commit unless asked.\n\n";
    p += "1) Markdown convention in vocab/*.md, after the existing 예문 line:\n";
    p += "   - 예문번역: {Korean translation of that English sentence}\n\n";
    p += "2) back/app/models.py Word: add example_ko Text nullable=False.\n";
    p += "3) back/app/schemas.py WordOut: add example_ko: str.\n";
    p += "4) scripts/import_words.py:\n";
    p += "   - Parse 예문번역 with a regex like 뜻/예문.\n";
    p += "   - DDL must CREATE TABLE with example_ko TEXT NOT NULL.\n";
    p += "   - Also ALTER TABLE english.word ADD COLUMN IF NOT EXISTS example_ko TEXT NOT NULL DEFAULT '';\n";
    p += "     because create_all will not add columns to an existing table.\n";
    p += "   - UPSERT include example_ko. parse_vocab tuples become (rank, word, meaning, example, example_ko).\n";
    p += "   - Require every rank 1-6000 to have non-empty example_ko.\n";
    p += "   - verify() must check example_ko is not empty and sample ranks match including example_ko.\n";
    p += "5) back/tests/conftest.py Word() construction: add example_ko=f\"예{i}\".\n";
    p += "6) back/tests/test_today.py: assert body[\"new\"][0][\"example_ko\"] == \"예1\".\n";
    p += "7) front/types/api.ts WordOut: example_ko: string.\n";
    p += "8) front/components/WordCard.vue: under the English example, show example_ko as a Korean line\n";
    p += "   (class example-ko, smaller, not italic English). Do not highlight Korean.\n";
    p += "9) README.md DB table word: mention example_ko.\n";
    p += "10) Run tests: " + root + "/back/.venv/Scripts/python.exe -m pytest -q with cwd " + root + "/back.\n\n";
    p += "Do not translate all 6000 vocab files in this step. Do not docker build. Do not commit.\n";
    p += "ok=true only if pytest passed and the files above contain example_ko / 예문번역 parser.\n";
    p += "List edited files in files. Put evidence in notes.\n";
    p
}

fn translate_prompt(root, start, stop, expected, rel) {
    let out_path = root + "/" + rel;
    let p = "";
    p += "Add Korean translations of English example sentences in existing vocab markdown.\n";
    p += "You MUST use tools. Read the file before editing. Do not invent ranks or English examples.\n\n";
    p += "1. read_file " + out_path + "\n";
    p += "2. Ranks " + start.to_string() + " through " + stop.to_string() + " inclusive, exactly ";
    p += expected.to_string() + " entries.\n";
    p += "3. For every ## entry, keep rank, word, 뜻, 예문 EXACTLY as they are.\n";
    p += "4. Add or replace a line immediately after 예문:\n";
    p += "   - 예문번역: {natural Korean translation of that 예문}\n";
    p += "5. write the full file back to " + out_path + " (overwrite).\n";
    p += "6. grep that file for 예문번역: and count. If count is not " + expected.to_string();
    p += ", fix and re-count before finishing.\n\n";
    p += "Translation rules:\n";
    p += "- Translate the English 예문 sentence, not the 뜻 gloss.\n";
    p += "- Natural Korean, same meaning, everyday tone.\n";
    p += "- One line, no quotes around the whole sentence unless the English has them.\n";
    p += "- Do not leave 예문번역 empty. Do not add extra sections.\n";
    p += "- Do not edit other files.\n\n";
    p += "Return path=" + rel + ", expected=" + expected.to_string();
    p += ", written=count of 예문번역 lines, ok=true only when written equals expected.\n";
    p
}

fn import_prompt(root) {
    let py = root + "/back/.venv/Scripts/python.exe";
    let p = "";
    p += "Import vocab markdown including 예문번역 into Postgres. You MUST use tools.\n";
    p += "Working tree is " + root + ".\n\n";
    p += "1. Confirm scripts/import_words.py parses 예문번역 and upserts example_ko.\n";
    p += "   If not, fix it first (ALTER TABLE ADD COLUMN IF NOT EXISTS example_ko).\n";
    p += "2. Local import:\n";
    p += "   " + py + " " + root + "/scripts/import_words.py\n";
    p += "   cwd can be " + root + ". This uses .env PGHOST 127.0.0.1.\n";
    p += "3. If local import succeeds, also run with --ec2 (SSH tunnel to auto-postgres).\n";
    p += "4. Do not print passwords. Do not commit. Do not docker build.\n\n";
    p += "ok=true only if local verify passed AND ec2 verify passed.\n";
    p += "local_ok/ec2_ok booleans. notes = short command outcomes, no secrets.\n";
    p
}

fn verify_prompt(root, file_count, entry_count) {
    let p = "";
    p += "Verify example Korean translations under " + root + ".\n";
    p += "You MUST use tools (list_dir, grep, read_file). Do not guess.\n\n";
    p += "1. Count vocab/*.md files (exclude README). Expected " + file_count.to_string() + ".\n";
    p += "2. grep ^##  for entry count. Expected " + entry_count.to_string() + ".\n";
    p += "3. grep 예문번역: count. Expected " + entry_count.to_string() + ".\n";
    p += "4. Spot-read vocab/0001-0050.md and vocab/5951-6000.md: each entry has 뜻, 예문, 예문번역.\n";
    p += "5. If you can, query or read import output; otherwise note that DB check is import-phase.\n\n";
    p += "ok=true only if files, entries, and 예문번역 counts all match expected.\n";
    p += "with_ko = 예문번역 count. notes = short evidence.\n";
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
    pause("verification", "chunk_size must be 50 to match vocab/*.md files.");
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

phase("Schema");
let schema = agent(
    schema_prompt(root),
    #{
        label: "schema-example-ko",
        capability_mode: "all",
        output_schema: ok_schema,
    },
);
let schema_ok = false;
let schema_notes = "";
if schema != () && schema.success && schema.output != () {
    if schema.output.ok == true { schema_ok = true; }
    if schema.output.notes != () { schema_notes = schema.output.notes; }
}
log("schema_ok=" + schema_ok.to_string());

phase("Translate");
let jobs = [];
for c in chunks {
    jobs.push(#{
        prompt: translate_prompt(root, c.start, c.stop, c.expected, c.rel),
        label: "ko:" + pad4(c.start) + "-" + pad4(c.stop),
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
log(ok_count.to_string() + "/" + chunks.len().to_string() + " chunks translated");

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
    if b.remaining < retry_list.len() + 2 {
        log("skip retry; remaining budget " + b.remaining.to_string());
    } else {
        phase("Retry");
        let rjobs = [];
        for c in retry_list {
            rjobs.push(#{
                prompt: translate_prompt(root, c.start, c.stop, c.expected, c.rel),
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

phase("Import");
let imported = agent(
    import_prompt(root),
    #{
        label: "import-example-ko",
        capability_mode: "all",
        output_schema: import_schema,
    },
);
let import_ok = false;
let local_ok = false;
let ec2_ok = false;
let import_notes = "";
if imported != () && imported.success && imported.output != () {
    if imported.output.ok == true { import_ok = true; }
    if imported.output.local_ok == true { local_ok = true; }
    if imported.output.ec2_ok == true { ec2_ok = true; }
    if imported.output.notes != () { import_notes = imported.output.notes; }
}
log("import_ok=" + import_ok.to_string() + " local=" + local_ok.to_string() + " ec2=" + ec2_ok.to_string());

phase("Verify");
let v = agent(
    verify_prompt(root, chunks.len(), max_rank),
    #{
        label: "verify-example-ko",
        capability_mode: "read-only",
        output_schema: verify_schema,
    },
);
let verify_ok = false;
let verify_notes = "";
let files = 0;
let entries = 0;
let with_ko = 0;
if v != () && v.success && v.output != () {
    if v.output.ok == true { verify_ok = true; }
    if v.output.notes != () { verify_notes = v.output.notes; }
    if v.output.files != () { files = v.output.files; }
    if v.output.entries != () { entries = v.output.entries; }
    if v.output.with_ko != () { with_ko = v.output.with_ko; }
}

let failed_rels = [];
for c in failed {
    if c.rel != () { failed_rels.push(c.rel); }
}

let summary = "";
summary += "schema_ok=" + schema_ok.to_string();
summary += " ok_chunks=" + ok_count.to_string() + "/" + chunks.len().to_string();
summary += " import_ok=" + import_ok.to_string();
summary += " verify_ok=" + verify_ok.to_string();
summary += " with_ko=" + with_ko.to_string();
log(summary);

let report = summary + "\n\n# schema\n" + schema_notes + "\n\n# import\n" + import_notes + "\n\n# verify\n" + verify_notes;
let report_path = write_scratch_file("example-ko-report.md", report);

complete(#{
    summary: summary,
    report: report_path,
    schema_ok: schema_ok,
    ok_chunks: ok_count,
    total_chunks: chunks.len(),
    failed: failed_rels,
    import_ok: import_ok,
    local_ok: local_ok,
    ec2_ok: ec2_ok,
    verify_ok: verify_ok,
    files: files,
    entries: entries,
    with_ko: with_ko,
});
