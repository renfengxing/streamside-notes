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
Solana native USDC is a proposal awaiting actual integration verification.
No service is promised before payment is accepted under an explicitly agreed
arrangement; no existing online checkout or receipt is claimed. Do not send money
or payment information through public issues.

## Sample review and privacy

The intended [public inquiry form](https://github.com/renfengxing/streamside-notes/issues/new/choose)
is a draft local entry; its availability is not verified. Every issue is public.
Share only a non-sensitive summary, never personal details, credentials or private
CSV data. Do not upload customer files or link private files. Agree a private channel before providing redacted samples and expected
output. An inquiry is not an order or payment. No external publication is performed.
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
a new directory; this display is not a claim that the public bundle includes the CLI.

## Original outdoor samples

The [site reference](https://streamside-notes.sandybloom18.chatgpt.site) is not
verified here. Local [service details](service.html), [printable checklist](samples/outing-checklist.html)
and [original SVG](assets/outing-plan.svg) remain original demonstrations,
not customer work or professional safety advice. The outdoor sample uses editable HTML
and one revision is an example of the former layout scope, not the CSV offer.
Keep articles, assets, samples and style.css together when previewing offline.

The [MIT license](LICENSE) covers original project samples; customer-provided or
third-party material retains its own rights. Source account: renfengxing.

## Channel rules — pending owner review

Promotion budget: zero. No Connects purchase, registration, paid promotion or
new paid service. External publication requires explicit owner authorization.
Before any proposed post on GitHub, Upwork or another channel, record the exact
channel, current official rule URLs, review date and reviewer, and verify rules
for AI-assisted content, automation/bots, self-promotion, links and commercial
services, plus required disclosures and listing fields. Current rules and channel
approval have not been verified. If any applicable rule remains unverified, do
not publish. Authorization alone does not establish platform permission.
Never enter channels that prohibit AI or bots. No unsolicited bulk direct messages
or bulk email. Do not claim approved listings, reach, leads, sales or income.
GitHub source/sample display is not customer acquisition. This is a draft only;
no publication, account action or outreach is performed by this task.
