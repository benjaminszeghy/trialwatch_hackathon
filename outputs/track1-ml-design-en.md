# TrialWatch Legal Tripwire: India — Phase 1 Machine Learning Design

Discussion date: October 9, 2026. Based on the team's latest Project Context.

**Status:** Proposed design. No actual Parquet or PDF samples have yet been obtained and inspected in this work; no model has been trained, and no evaluation results are available. The sample sizes and experimental scope below are suggested targets.

**Your core deliverable: turn historical High Court documents into structured research data with traceable evidence and clearly defined statistical measures, providing a basis for provision-level scoring.**

This phase investigates which measurable features should serve as warning signals when a legal provision is invoked. Live case discovery, procedural alerts, and TrialWatch review priorities come later. Keep four outputs separate: structural characteristics of the provision, historical evidence of its use, case-specific procedural signals, and monitoring priority.

## 1. Where machine learning fits

| Stage | Method | Output |
| --- | --- | --- |
| Retrieve candidate documents | Rules using provision numbers and statute names; semantic retrieval as a supplement | Verifiable candidate documents and the passages that matched |
| Identify the provision's role | Extraction into a fixed schema; optionally test a small classifier once labels are available | Charge in the current case, cited precedent, other discussion, or unclear |
| Extract alleged conduct and judicial reasoning | A pretrained model extracts fields into a schema; code checks quotations; humans review the results | Alleged conduct, identity/expression nexus, proceeding type, disposition, and reasons |
| Compare charges with alleged conduct | Legal team members confirm statutory elements; the model retrieves and organizes corresponding passages | A matrix connecting elements, prosecution allegations, judicial findings, and information gaps |
| Analyze patterns across cases and develop scoring | Deduplication, denominator definitions, stratified statistics, expert rubrics, and weight sensitivity analysis | Provision profiles and historical evidence tables with sample counts |

For the first version, prioritize extraction and passage retrieval. Whether to train a separate classifier depends on the quantity and quality of human labels. A large document collection does not itself provide a gold standard for a provision's susceptibility to misuse.

## 2. Confirm the units of analysis and actual fields

The AWS registry describes an open data project providing High Court documents sourced from eCourts, along with JSON and Parquet metadata. This is a processed open dataset.

The standard Athena table lists fields such as court, title, description, judge, pdf_link, cnr, registration date, decision date, and disposal nature. It does not include a full-text field. The description field should not be treated as the complete judgment. The original project also describes richer case-details tables for some mobile-source data; the fields and coverage for the selected courts still need to be inspected.

Distinguish three units:

- **Document:** an individual judgment or order, stored with a stable document key.
- **High Court proceeding:** a bail application, quashing application, or another proceeding, linked using CNR and proceeding information where possible.
- **Underlying criminal case family:** one FIR or alleged incident can generate several proceedings and orders. CNR alone may not connect all related proceedings.

A provision mentioned in a precedent does not establish that the current defendant was charged under it. Multiple orders in one case must not automatically be counted as multiple criminal cases.

Fix the retrieval and sampling protocol by **provision × court × period**. After identifying provisions actually invoked in the current case, include all eligible documents or randomly sample within the defined scope. Selecting documents only through concern or outcome terms such as “quashing” or “abuse,” then presenting the resulting proportions as typical behavior of the provision, would distort the analysis. Such terms can support a separate targeted case study, with that sample reported separately.

Sources: [AWS registry](https://registry.opendata.aws/indian-high-court-judgments/), [metadata schema](https://github.com/vanga/indian-high-court-judgments/blob/main/opendata/tutorials/ATHENA.md), and [original dataset documentation](https://github.com/vanga/indian-high-court-judgments/blob/main/opendata/docs/dataset.md). These observations come from the project documentation; actual data rows have not yet been inspected.

## 3. Proposed minimum extraction schema

| Field group | Required information |
| --- | --- |
| Source and version | document_id, CNR/case-family key, court, decision date, source URL, and text version |
| Legal provision | Statute/section, applicable version, whether it is a current charge or only a citation, and supporting text |
| People and conduct | Journalism/expression nexus, alleged conduct, and the person's role; explicitly mark unknown information |
| Proceeding | Bail / anticipatory bail / quashing / other; the specific relief sought |
| Disposition | Granted / denied / partial / procedural / pending / unclear; identify what the decision concerns |
| Reasons | Missing statutory elements, insufficient mens rea, vague allegations, procedural issues, settlement, other, or not stated; allow multiple labels |
| Attribution | Prosecution allegation, applicant's argument, judicial finding, cited precedent, or another source |
| Evidence anchors | Exact quotation, page number or character offsets, and the field supported |
| Dates and missing information | Available FIR, application, and detention dates; the meaning of each date; unavailable information |

Finding the quotation in the source text is only the first check. Human review must also establish whether it supports the extracted field and whose statement it represents. For example, an applicant's allegation of “abuse of process” must not automatically be recorded as a judicial finding.

## 4. A verifiable approach to Charge–Conduct Distance

Start by reporting statutory-element alignment, without producing a single distance score.

| Statutory element | Specific allegation in this case | Court's assessment | Evidence status |
| --- | --- | --- | --- |
| Conduct element confirmed by the legal team | The conduct alleged by the prosecution, quoted from the source | The court's discussion of this element | Addressed / not addressed / unclear |
| Confirmed mental-state element | Allegations concerning intention or knowledge | The court's assessment of the relevant issue | Addressed / not addressed / unclear |
| Required result or connection | Alleged harm, obstruction, or another required result | Whether the court identifies a missing element or insufficient connection | Addressed / not addressed / unclear |

An explicit judicial finding that an element is missing can be extracted as a historical indicator. If the material does not address an element, retain an unknown value. Store prosecution allegations, established facts, and judicial findings separately.

Claude's final feedback highlighted a useful distinction: clearly documented boilerplate allegations should not all be treated as missing information. Preserve this signal through two separate dimensions:

- **Allegation content:** specific factual allegations; repetition of statutory language only; sufficiently assessable material that supplies no corresponding facts; or insufficient material. Use “no corresponding facts supplied” only when quotation coverage and legal review support that assessment. An omission from a short excerpt is insufficient.
- **Court assessment:** explicitly finds the element satisfied; explicitly finds it insufficient; does not address the element; or unclear. Specific factual allegations can still be found insufficient by a court, so these dimensions should not be collapsed into one mutually exclusive label.

Store the supporting text and its coverage for every assessment. If an element-based proportion is calculated later, include only clearly assessable elements in the denominator. Separately report the number of assessable elements divided by the total applicable elements. When coverage is low, do not produce a single distance score for comparison.

Semantic embeddings can help locate passages; they cannot establish whether legal elements are satisfied. For example, if a journalist covering a protest is charged with obstructing an official, a semantic difference between “reporting” and “obstruction” still requires checking whether additional specific obstructive conduct was alleged.

## 5. Begin provision-level scoring with two tables

**Structural profile:** legal team members confirm the provision's version, scope, clarity, mental-state requirements, defenses, penalties, and exposure to coercive procedures. Each criterion needs explicit scoring anchors and supporting authority.

**Historical observation table:** present deduplicated sample counts, expression nexus, application types, dispositions, and judicial reasons, with explicit denominators and missing-data information.

Present these separately initially; combining them into a score can be a later experiment. With only 8–12 candidate provisions, numerous orders do not justify claiming that reliable provision-level weights can be learned.

If a 0–100 score is eventually used, it is an index derived from a published rubric, rather than the percentage probability that a provision is being misused. Expert agreement and ranking stability assess reproducibility; they do not, by themselves, establish predictive validity in practice.

Define historical measures as follows:

- **Frequency:** the number of distinct cases or proceedings found within the stated coverage and eligibility rules.
- **Quashing outcomes:** dispositions among relevant quashing applications with interpretable decisions; distinguish complete relief, partial relief, and procedural dispositions.
- **Bail outcomes:** results for the relevant application type; report ordinary and anticipatory bail separately.
- **Charge multiplicity:** the actual set of charges in a case, without counting repeated mentions across documents.
- **Duration:** clearly defined start and end dates. The interval between High Court registration and decision does not directly represent the entire criminal process or time in detention.

For each measure, state whether the denominator is case families or distinct applications. Link and report repeat applications. When comparing provisions, show both case counts and application counts, and check whether a few cases with many applications dominate the results. Preserve the last date on which the case's status is known. Failure to locate a later order does not establish that a case remains unresolved today. For proceedings without an observed conclusion, report the observed duration through the last evidence date. Analyzing completed proceedings alone may understate the duration of proceedings that remain unresolved for long periods.

Public High Court documents form a selected sample. Observed quashing or bail proportions cannot directly be extrapolated into a misuse rate across all prosecutions. Where possible, comparisons between journalism/expression-related cases and other cases should match provision, court, period, application type, and conduct category. Preserve unresolved proceedings as unresolved rather than treating them as unsuccessful outcomes.

## 6. Two priority experiments

**Model experiment: verifiable field extraction.**

Begin with 2–3 provisions from the candidate list and a small number of courts, then expand toward the team's planned 8–12 provisions. Freeze a manually annotated test set in advance, with splits made by case family. Compare statute/keyword rules with model extraction into a fixed schema. Evaluate provision role, proceeding and disposition classification, reason classification, source support, attribution errors, and treatment of unknown information. Double-annotate a subset and record the reasons for disagreements.

Report precision, recall, and F1 separately for classification fields. For source support and attribution accuracy, report manually verified numerators and denominators. Report inter-annotator agreement separately from model performance. Method comparisons must use the same test material, input scope, and evaluation metric. Element-classification κ and semantic-ranking Spearman correlation cannot be compared directly to establish which method is better. If comparing case-level rankings, use a common human ranking reference and the same ranking metric.

**Scoring experiment: expert agreement and sensitivity.**

Ask legal team members to score provisions independently using the same materials and conduct a limited number of pairwise comparisons. Vary plausible weights and exclude different court or period subsets to examine ranking stability. Identify provisions whose rankings depend strongly on particular assumptions. Historical outcomes describe patterns of use; they should not automatically become training labels for a provision's “true risk.”

Report only measured numerators, denominators, and error examples. These experiments validate extraction and the basis for scoring. A later early-warning evaluation will require historical replay using only information available at each relevant time.

## 7. Responsibilities and deliverables

**Your responsibilities:** the schema and annotation guide, extraction methods and baselines, case-family linkage rules, statistical definitions, evaluation, and scoring sensitivity experiments.

**Legal team responsibilities:** candidate provisions, applicable versions and IPC/BNS relationships, statutory elements, scoring anchors, and review of key judicial reasoning. Cross-version relationships must be checked against the texts and their applicability dates; they should not be assumed to be simple renumbering.

**Data team responsibilities:** usable metadata samples, corresponding document text, stable sources, and dates.

First-version deliverables: a structured extraction table, a provision-level historical evidence table, a human review report, and a scoring experiment description. Before data is available, deliver the interfaces and annotation specifications. Once data is available, evaluate under the frozen protocol.

## 8. Discussion with Claude

Three rounds of discussion were completed in the Claude conversation specified by the user, and the actual responses were read. The latest scope was explicitly historical provision-level research.

Shared recommendations: a fixed schema with source evidence; separation of current charges from cited precedents; statutory-element matrices; explicit historical denominators; legal review of scoring rubrics; and two experiments covering extraction evaluation and weight sensitivity. Start with 2–3 provisions. Approximately 60 manually annotated gold-standard documents is an adjustable target.

I proposed two revisions to Claude's recommendations, which it accepted in the final round: do not treat an element's absence from the available material as a mismatch, and do not directly compare values from different evaluation metrics. Claude added that clearly documented boilerplate allegations should be distinguished from missing information. This design implements that distinction through allegation content, court assessment, and evidence coverage.

The discussion produced design recommendations, without generating new model results or legal findings. Final-response screenshot: [Claude discussion record](/Users/zhangkai/Documents/Codex/2026-10-09/wo/outputs/claude-ml-discussion.png).
