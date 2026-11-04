# Streamside Notes — local CSV repair

Quote after reviewing a redacted sample and expected output. Local delivery only.
The offer is repaired CSV output, a reusable Python standard-library CLI and a
JSON exception report. Confirm scope, quote and delivery timing before work begins.
UTF-8 (BOM allowed), commas and identical ordered headers are required. Exact
processed-row deduplication preserves first occurrence. Trimming is explicit;
no fuzzy matching, automatic columns or blank filling. Invalid files are rejected
without partial success, and existing files are never overwritten.

AI-assisted work; customers confirm rights and accuracy. No commercial results
are guaranteed. No verified online payment integration, customers, orders or income.
Quote-bound USDC requests and read-only verification are implemented locally; real mainnet integration has not been exercised.
No service is promised before payment is accepted under an explicitly agreed
arrangement; no existing online checkout or receipt is claimed. Do not send money
or payment information through public issues.

## Sample review and privacy

The [public inquiry form](https://github.com/renfengxing/streamside-notes/issues/new/choose)
accepts public non-sensitive summaries. Every issue is public.
Share only a non-sensitive summary, never personal details, credentials or private
CSV data. Do not upload customer files or link private files. Agree a private channel before providing redacted samples and expected
output. An inquiry is not an order or payment.
GitHub is source/sample display, not evidence of customer acquisition.

## Synthetic CSV before and after

Duplicate rows, surrounding field whitespace and inconsistent columns can cause
repeated manual cleanup. This synthetic example is not customer work.
With explicit `--trim-fields`, merge these inputs (the second permits a UTF-8 BOM):

synthetic-a.csv:
```csv
id,name
1," Ada "
2,Bob
```

synthetic-b.csv:
```csv
id,name
1,Ada
3,
```

Expected output:
```csv
id,name
1,Ada
2,Bob
3,
```

The JSON report records 4 input records, 3 output records and 1 duplicate,
with source locations. Empty values remain empty. A mismatched header or a row
such as `4` under `id,name` produces an explicit error report and no repaired
output. No input file is overwritten. The local source CLI `csv_repair.py --demo`
generates synthetic inputs, expected/actual output and success/error reports in
a new directory. See [CSV usage guide](CSV_USAGE.md) for runnable commands.

## Original outdoor samples

Visit [Streamside Notes](https://streamside-notes.sandybloom18.chatgpt.site) or read the [service details](https://streamside-notes.sandybloom18.chatgpt.site/service.html). The [printable checklist](samples/outing-checklist.html)
and [original SVG](assets/outing-plan.svg) remain original demonstrations,
not customer work or professional safety advice. The outdoor sample uses editable HTML
and one revision is an example of the former layout scope, not the CSV offer.
Keep articles, assets, samples and style.css together when previewing offline.

The [MIT license](LICENSE) covers original project samples; customer-provided or
third-party material retains its own rights. Source account: renfengxing.

## Current purchase workflow

Public non-sensitive summary → agree private channel → redacted sample and expected output → scope, fixed quote, timing and explicit acceptance → operator payment request → customer confirms in own wallet → manual signature read-only finalized verification → CSV, reusable script and JSON exception report → delivery acceptance. Without confirmed quote payment stays disabled; demo cannot pay. No real mainnet receipt is evidenced.

[Published renfengxing source](https://github.com/renfengxing/streamside-notes) · [CSV_USAGE](CSV_USAGE.md) · [Payment request](https://streamside-notes.sandybloom18.chatgpt.site/pay.html).
