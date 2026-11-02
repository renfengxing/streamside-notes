# Local CSV repair and merge

Local delivery only. Quote after reviewing a redacted sample and expected output; agree a fixed quote, scope and delivery timing before work begins. An inquiry is not an order. The three deliveries are repaired CSV result files, a reusable Python standard-library CLI (`csv_repair.py`), and a JSON exception report. This is a service hypothesis: no verified customers, online checkout or income. Solana native USDC is only a proposal awaiting integration verification, not an available payment method.

## Run the synthetic demonstration offline

Use Python 3 with the standard library; no installation or network is needed. From the project root, run the following commands. `demo` must not already exist. To try this in a fresh temporary directory, copy `csv_repair.py` and this README there first.

```sh
python3 -B csv_repair.py --demo demo
python3 -B csv_repair.py demo/synthetic-a.csv demo/synthetic-b.csv --output preserved.csv --report preserved-report.json
python3 -B csv_repair.py demo/synthetic-a.csv demo/synthetic-b.csv --trim-fields --output trimmed.csv --report trimmed-report.json
```

`demo/actual.csv` must equal `demo/expected.csv`; `demo/report.json` must equal `demo/expected-report.json`. The demo explicitly enables trimming: four input records become three, with one duplicate. `preserved.csv` has four records because ` Ada ` and `Ada` differ; `trimmed.csv` equals `demo/expected.csv`. The empty name stays empty. All examples are synthetic, never customer results. `demo/SYNTHETIC.txt` identifies them. `demo/error-report.json` equals `demo/expected-error-report.json`, reporting the short row in `demo/synthetic-invalid.csv`; no `demo/invalid-output.csv` is produced.

For your own files, replace the input paths and choose new output and report paths:

```sh
python3 -B csv_repair.py a.csv b.csv --output merged.csv --report report.json
```

## Supported format and exact rules

UTF-8 (optional BOM), comma-separated CSV only, with identical ordered headers. Quoted commas, escaped double quotes, multiline fields and CRLF input are supported; output uses LF. Header-only files are accepted. Excel workbooks, other encodings and other delimiters require separate scope confirmation and are not supported by this CLI.

Defaults to preserving values, including leading/trailing whitespace and blank values. `--trim-fields` explicitly applies Python `str.strip()` to value edges before deduplication, not headers or internal whitespace; use only after customer confirmation. Exact processed full-row deduplication preserves first occurrence in input order. No fuzzy matching, automatic column filling, blank filling or type conversion.

Rejects blank/duplicate headers, mismatched header names/order, wrong field counts, malformed CSV and invalid UTF-8. Validation failure writes a JSON error report without partial CSV output and exits nonzero with stderr diagnostics. Success reports include counts, kept/duplicate records and first-occurrence references. Source record numbers include the header; line is the ending physical CSV line, including multiline records. Reports may contain source paths: review them before sharing.

Existing inputs and targets are never overwritten. Output and report must be distinct and cannot alias inputs; existing targets (including symbolic links) are refused. Parent directories must exist. Path conflicts or unwritable report destinations may prevent report creation; stderr and nonzero exit remain the diagnostic. Use fresh paths for every run, including failures.

## Sample review, privacy and AI assistance

AI-assisted work requires customer confirmation of rights, accurate input interpretation, expected changes, scope and final results. Review a redacted sample and expected output before a fixed quote. Never post customer original data, confidential data or personal or payment information in public issues. Agree a private transfer method before sharing even redacted samples; none is provided by this local version. No secure storage, retention period or delivery interval is promised. Inspect the script and run locally with synthetic data first.

## Historical original demonstrations

Open `site/index.html` offline. The original outdoor articles, cited sources, original SVG diagrams and printable `site/samples/outing-checklist.html` remain historical original demonstrations, not customer cases or CSV delivery evidence. Keep the HTML, `site/style.css` and `site/assets/` together for offline use and browser printing.

[renfengxing source reference](https://github.com/renfengxing/streamside-notes) is an unverified display reference, not a verified live service entry or acquisition evidence. No publication, account access, external sending or transaction is performed here. See `operations/handoff.md` for the fixed checks.
