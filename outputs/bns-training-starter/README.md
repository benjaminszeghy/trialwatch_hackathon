# BNS case acquisition and annotation starter

Start with `case-candidates.csv` for the inventory and `annotation-template.csv` for the first **16 documents** to review. `documents.jsonl` supplies the extracted text. The ZIP contains PDFs under `pdfs/<document_id>.pdf`. Each document has a direct source URL and SHA-256 hash.

**To open the PDFs, use [the clickable document index](document-index.md).** It has one row per document with GitHub preview, download and original-source links. The case CSV's `source_urls` field can contain two URLs separated by a newline; copy one URL at a time. CSV quotation marks, backslashes and pasted `&#x20;` spacing are not part of a PDF URL. CSV cells do not guarantee clickable hyperlinks. `document-access-audit.json` records the saved-file checks and point-in-time live source checks.

## What was collected

The retrieval frame contains **107 CNR proceedings**, selected because their Act-bound metadata matched BNS **152, 196, 299, 353, 356 or 221**. These are provisional project targets, not all BNS offences. The source is the recorded Indian High Court Judgments AWS snapshot for four Bombay benches, joined to orders in the **2024–2025** window. It is a High Court sample, not all India or a journalist-only corpus.

For each CNR, the earliest and latest available distinct PDF in that window were requested, without selecting on the disposition. This produced **177 document records, 174 distinct PDF hashes and 500 PDF page records**. A common judgment may appear under multiple proceedings. Only **47** records contain at least three pages; a long document can still be merely a batch notice order. Conversely, a short order can explicitly identify charges.

The first text review covered **39 documents**. **30 CNRs** have a target BNS provision recorded in a charge/complaint narrative. These are AI-assisted research annotations, with exact page/character evidence; they are not independent expert gold labels. One CNR has a verified IPC/BNS metadata conflict, eight reviewed CNRs do not establish the target charge, and 68 remain at metadata-only review status. No human gold labels have been supplied.

| BNS parent provision | Metadata retrieval CNRs | CNRs with a text-grounded starting annotation |
|---|---:|---:|
| 152 | 4 | 2 |
| 196 | 14 | 5 |
| 299 | 14 | 1 |
| 353 | 21 | 6 |
| 356 | 64 | 18 |
| 221 | 12 | 3 |

Counts overlap across provisions. The two confirmed 152 proceedings are the same known Farah Deeba FIR. The third column reflects the limited review performed, not the final number of genuine matches or a law-use/abuse rate.

## What “BNS only” means

BNS is the substantive criminal code; BNSS governs criminal procedure. **BNSS 482/483/528 is not a BNS target charge.** BNS commenced on **1 July 2024**, with the commencement notification excepting section 106(2). Assigning the applicable substantive code also requires checking the alleged conduct, dates, statutory savings and actual record. A 2025 order may still concern an IPC prosecution. A law discussed as precedent or challenged constitutionally is not automatically a charge against a defendant.

The corpus records what the documents assert. It does not independently validate every transitional-law application. The offence/FIR date must be reviewed separately; the order year is not a substitute. Historical IPC judgments may later be useful as a separate interpretation/reference collection, while the current case collection remains BNS-focused.

## First useful ML task

**Extract the operative law and charge list, and return a supporting passage.** This is practical before attempting element-level conduct assessment. It catches the very errors found in this collection: BNS versus BNSS, an IPC prosecution mislabeled BNS, a section mentioned only in precedent, a request to register an FIR, and an order with no charge details.

The next extraction task is: **who is alleged to have done what, in which medium, and who states that account?** Keep allegations, defence submissions and judicial findings separate. Record the complete bundle of laws; do not attribute custody, bail or a quashing decision to one target section alone.

This collection does not provide abuse/legitimacy labels. A journalist identity, a speech-related allegation and a potential procedural concern are separate fields. Neither bail nor dismissal supplies an abuse label. The prior law-review scores also do not supply case labels.

## First annotation session

1. Have two teammates independently review the 16 starter documents. Open the source PDF, including enough surrounding text to identify the case and speaker. The AI seed is a suggestion to check; it is not an answer key.
2. Fill the blank `human_*` columns. Use the codebook below. Record exact page numbers and text quotations for charges and conduct. If the document does not contain enough material, explicitly choose `insufficient` or `unknown`.
3. Reconcile disagreements with a legal teammate; retain the two original annotations separately. For genuinely blind agreement measurement, hide `ai_seed_role`, `ai_text_confirmed_targets`, `seed_page` and `seed_quote` in a copy before the independent pass.
4. Confirm which CNRs share an FIR or connected dispute. Use `leakage_group_id` to keep known shared text/families together. All train/test splits are intentionally unassigned while family linkage is incomplete.
5. Evaluate a rule baseline and a fixed-schema pretrained extractor against the independently checked labels. Report law-role accuracy, section precision/recall and quotation support. A quotation occurring in the PDF does not by itself establish that it supports the proposed legal conclusion.

Do not fine-tune an abuse classifier on the AI seeds. The 16 documents are a first annotation batch, too small to claim general model accuracy. BNS 299 currently has only one text-confirmed proceeding in this review; more verified, independent material is needed for a useful per-law test set.

## Annotation codebook

| Field | Allowed values / instruction |
|---|---|
| `human_law_role` | `operative_charge_recorded`, `precedent_or_comparison_only`, `statute_challenge`, `registration_sought`, `insufficient`; also flag any `IPC_BNS_metadata_conflict` in notes |
| `human_bns_sections` | Exact BNS section/subsection strings supported by the operative narrative; distinguish parent-only `353` from `353(2)` |
| `human_fir_number`, `human_fir_date`, `human_police_station` | Number/year, ISO FIR date and police station from a supported passage; leave blank when unknown or when the proceeding concerns a private complaint without an FIR |
| `human_charge_bearer` | Identify the person/group whose charge is being described; do not assume the petitioner is the accused |
| `human_dispute_type` | For example public/political expression, employment, family, school, housing, alleged fraud, other, or unknown; this is context, not an abuse label |
| `human_document_type` | Notice/administrative order, interim reasoned order, final decision in this proceeding, other, or unknown; final bail/quashing disposal is not necessarily final trial disposal |
| `human_charge_evidence_page`, `...quote` | PDF page and exact passage binding the section to its Act and the relevant proceeding; use a second passage in notes when an Act name runs onto another page |
| `human_conduct_evidence_page`, `...quote` | Actual alleged behaviour, not copied statutory elements; note speaker/source: complaint account, defence submission, or court finding |
| `human_expression_nexus` | `direct_expression`, `mixed_expression_and_other_conduct`, `no_expression_described_in_reviewed_account`, `unknown`; absence in a short order means unknown |
| `human_journalist_status` | `confirmed_journalist`, `confirmed_other_role`, `unknown`; appearing in media, posting online or criticizing an official is not proof of journalism |
| `human_procedure_type` | `anticipatory_bail`, `regular_bail`, `quashing_request`, `private_complaint_process`, `preventive_notice`, `other`, `unknown` |
| `reviewer_id`, `reviewed_date` | Reviewer alias and ISO date; keep first-pass and reconciled copies distinguishable |

Also record **whose** charge is being described. Some proceedings involve proposed accused, complainants, several defendants, cross-FIRs or a challenge to preventive notices alongside a separate criminal FIR. CNR identifies a proceeding, not an independent prosecution.

For later element coding, use at least: `specific_facts_recorded`, `statutory_words_only_in_sufficiently_reproduced_allegation`, `court_explicitly_finds_element_absent`, `not_observable_from_document`. Do not turn document omissions into missing legal elements. Element definitions need legal review before numerical charge–conduct measures are used.

## Good starting examples

| Proceeding | Why useful |
|---|---|
| Farah Deeba: HCBM010319502025 / HCBM010375472025 | BNS 152/196/353, WhatsApp allegations; linked quashing and bail proceedings in one FIR |
| Ashraf Naseem Khan: HCBM070353582025 | BNS 353(1)(b)/353(2), social-media allegation; bail observations explicitly limited to bail |
| Dadasaheb Gorakh Chavan: HCBM010577982024 | BNS 356, criticism of an official in front of media; defence and judicial accounts must be separated |
| Bhalchandra Vijay Shinde: HCBM010482532025 | BNS 196(1)/299 explicitly recorded in a two-page notice order about a Facebook post |
| Jyoti Ramesh Balani: HCBM010523832025 | BNS 356(2), LinkedIn allegation; charge, conduct and disposition extractable |
| Sashidhar Jagdishan: HCBM010409232025 | BNS 356 private complaint; useful distinction between notice, cognizance and proposed accused |
| Chandrashekhar Bhimsen Naik: HCBM010565972025 | BNS 356(2) in a deepfake-advertisement FIR; arrest-safeguard challenge and original FIR identity need careful reading |
| Suraj Baliram Sake: HCBM030338522024 | BNS 221 with alleged detention of an official; contrasting conduct without an assumed abuse label |

## Files and reproducibility

- `case-candidates.csv`: all 107 proceedings, retrieval status, text-reviewed sections, links and missing values.
- `annotation-template.csv`: 16 starter documents, AI suggestions and blank human fields.
- `documents.jsonl`: 177 document records with raw and whitespace-normalized page text, provenance, grouping and blank human labels.
- `review-seeds.json`: 39 AI-assisted annotations with exact raw/normalized character spans.
- `acquisition-manifest.json`: attempted order URLs, downloaded hashes and selection metadata.
- `summary.json`: collection counts and limitations.
- `document-index.md`: clickable links to all 177 saved HC document records and six separate reference documents.
- `document-access-audit.json`: local PDF parsing, text/hash checks and timestamped live-source responses; this verifies access and snapshot integrity, not legal labels.
- `supplements/`: separately sourced official Supreme Court material and Claude’s review, when included; not part of the 107-CNR retrieval denominator.
- `pdfs/`: downloaded HC PDFs in the ZIP; filenames match `document_id`.

In the Codex workspace, acquisition is `research/acquire_bns.py`; offline construction is `research/build_bns_corpus.py`; CSV export is `export-bns-corpus.mjs`. Acquisition reuses the recorded Bombay metadata snapshot, and limits concurrent PDF requests to two. It does not automate CAPTCHA solving or query private eCourts endpoints. For a large expansion, use the dataset’s bulk tar/Parquet interfaces.

To rebuild the clickable index and audit saved copies, install the pinned Python requirements and run `python3 research/audit_bns_output.py`. Add `--live` to check each public source URL with two concurrent curl requests. Live checks retain normal TLS verification and never overwrite downloaded research PDFs. A source served as `binary/octet-stream` may download rather than display in a browser; the GitHub preview links provide another way to read it.

## Sources and attribution

Indian High Court Judgments, maintained by Dattam Labs and contributors, accessed 9 October 2026 through the public AWS data interface. Registry license: CC BY 4.0. The acquisition manifest identifies individual URLs and hashes. The snapshot was originally assembled earlier in this project; cached objects are not represented as newly refreshed metadata.

- [Indian High Court Judgments registry](https://registry.opendata.aws/indian-high-court-judgments/)
- [Dataset maintainer’s documentation](https://github.com/vanga/indian-high-court-judgments)
- [Indian Supreme Court Judgments registry](https://registry.opendata.aws/indian-supreme-court-judgments/)
- [Official BNS commencement notification](https://www.mha.gov.in/sites/default/files/BhartiyaNyayaSanhita_24022024.pdf)

This is an acquisition and annotation starter. It estimates no population abuse rate, no validated legal-risk score and no supervised abuse-model performance.

## Claude collaboration and separately verified supplements

Claude searched official court sources and reviewed the acquisition design. Codex then downloaded and checked the cited PDFs against their actual text. **Six official reference documents** are included under `supplements/` (108 additional pages), separate from the Bombay collection:

- Imran Pratapgarhi 2025: Supreme Court interpretation reference for BNS 196, retained from the earlier pilot.
- Pawan Khera 2026 INSC 437: FIR narrative records BNS 353/356 among a larger charge bundle; political press conferences.
- Ranveer Gautam Allahabadia, W.P.(Crl.) 83/2025, order of 18 February 2025: one FIR records BNS 196/299; several FIRs concern the same episode. It is an interim order.
- Ruchika Mitra, Delhi CRL.M.C. 347/2026: BNS 356(2) recorded in a school dispute. Settlement-based quashing supplies no abuse label.
- S.G. Vombatkere W.P.(C) 720/2025 office report: a constitutional challenge to BNS 152, not a charge case or a ruling on validity.
- Ashish Dave 2026 INSC 244: actual BNS charges outside the six targets, with a media-employment context; retained to illustrate possible retrieval omissions.

The supplemental manifest records direct official URLs and hashes. `reviewed-evidence.json` supplies checked quotations and page references. The three new target-charge documents are purposively selected supplements; do not add them to the AWS sampling denominator or silently distribute connected cases across train/test sets.

We explicitly corrected two review suggestions: private disputes/non-journalists are **not** automatic negative abuse labels, and the AI-reviewed 30 CNRs are **not** gold data before independent human review. Both points were confirmed with Claude. The collaboration note records the final agreed position.

## Message Kai can send to the team

“I have collected a BNS-focused court-document corpus for our ML work: 107 candidate CNR proceedings and 177 document records from the Bombay AWS snapshot. I have text-grounded starting annotations for 30 proceedings, with linked FIRs kept visible. I suggest that we first annotate operative law/charge identity and alleged conduct, then evaluate extraction. We do not yet have reliable abuse/legitimacy labels. Please confirm whether our target sections are BNS 152, 196, 299, 353, 356 and 221, and share your existing CNR/source lists so we can deduplicate.”
