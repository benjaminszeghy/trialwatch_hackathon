# TrialWatch Legal Tripwire: India — laws and scores

First build · 9 October 2026 · rubric 0.1

**These are provisional statute-as-written review indices.** They use AI-assisted analyst coding, have not been independently legally validated, and are not probabilities that a law or prosecution is abusive. Higher scores mean more flags under the explicit rubric below.

Historical IPC and current BNS provisions are separate. Continuing special acts form a third panel. Judicial interpretations and observed court evidence are displayed separately from the numerical index.

The selected BNS provisions commenced on 1 July 2024 under the [official commencement notification](https://www.mha.gov.in/sites/default/files/BhartiyaNyayaSanhita_24022024.pdf). The linked IPC baseline is historical and subject to savings; this is not a claim that all later amendments, state variations or decisions have been exhaustively audited.

## Score tables

The six numbers in the profile are: expression reach · evaluative language · explicit mental-state gap · expression-safeguard gap · arrest/bail exposure · imprisonment severity. Each runs from 0 to 2. Raw totals are out of 12; the 0–100 display is a rounded rescaling, not additional precision.

### Historical IPC — repealed code, subject to savings

| Provision | Raw /12 | Score /100 | Six-component profile | Weight band* | Parent metadata CNRs† | PDFs selected† |
|---|---:|---:|---|---|---:|---:|
| IPC 124A — sedition (historical; 2022 abeyance order) | 11 | **92** | 2 / 2 / 2 / 1 / 2 / 2 | 88.1–95.1 | 2 | 2 |
| IPC 153A(1)(a)-(b) — promoting enmity | 11 | **92** | 2 / 2 / 2 / 2 / 2 / 1 | 88.1–95.2 | 27 | 6 |
| IPC 295A — deliberate malicious religious insult | 8 | **67** | 2 / 1 / 0 / 2 / 2 / 1 | 59.2–73.9 | 26 | 6 |
| IPC 505(1) — statements conducing to public mischief | 8 | **67** | 2 / 2 / 1 / 1 / 1 / 1 | 61.9–71.4 | 22 | 6 |
| IPC 505(2) — enmity from false/rumour reports | 9 | **75** | 2 / 2 / 1 / 1 / 2 / 1 | 70.1–80.0 | 22 | 6 |
| IPC 499/500 — criminal defamation | 4 | **33** | 2 / 1 / 1 / 0 / 0 / 0 | 26.1–40.8 | 137 | 8 |
| IPC 186 — obstructing public functions | 4 | **33** | 0 / 1 / 1 / 2 / 0 / 0 | 26.2–40.7 | 13 | 4 |

### Current BNS baseline — selected provisions commenced 1 July 2024

| Provision | Raw /12 | Score /100 | Six-component profile | Weight band* | Parent metadata CNRs† | PDFs selected† |
|---|---:|---:|---|---|---:|---:|
| BNS 152 — sovereignty, unity and integrity | 10 | **83** | 2 / 2 / 1 / 1 / 2 / 2 | 78.7–87.9 | 4 | 4 |
| BNS 196(1)(a)-(b) — promoting enmity | 11 | **92** | 2 / 2 / 2 / 2 / 2 / 1 | 88.1–95.2 | 14 | 6 |
| BNS 299 — deliberate malicious religious insult | 8 | **67** | 2 / 1 / 0 / 2 / 2 / 1 | 59.2–73.9 | 14 | 4 |
| BNS 353(1) — statements conducing to public mischief | 8 | **67** | 2 / 2 / 1 / 1 / 1 / 1 | 61.9–71.4 | 21 | 7 |
| BNS 353(2) — enmity from false/rumour reports | 9 | **75** | 2 / 2 / 1 / 1 / 2 / 1 | 70.1–80.0 | 21 | 7 |
| BNS 356(1)-(2) — criminal defamation | 4 | **33** | 2 / 1 / 1 / 0 / 0 / 0 | 26.1–40.8 | 64 | 7 |
| BNS 221 — obstructing public functions | 4 | **33** | 0 / 1 / 1 / 2 / 0 / 0 | 26.2–40.7 | 12 | 4 |

### Continuing special statutes — selected central text

| Provision | Raw /12 | Score /100 | Six-component profile | Weight band* | Parent metadata CNRs† | PDFs selected† |
|---|---:|---:|---|---|---:|---:|
| UAPA 13 with 2(o) — unlawful activities | 10 | **83** | 2 / 2 / 1 / 2 / 2 / 1 | 78.6–88.0 | 10 | 5 |
| IT Act 67 — electronic obscenity (first conviction) | 8 | **67** | 2 / 2 / 2 / 0 / 1 / 1 | 59.3–74.0 | 87 | 5 |
| Official Secrets Act 3 — defence/code publication branch | 10 | **83** | 1 / 2 / 1 / 2 / 2 / 2 | 78.5–88.0 | 2 | 2 |
| Official Secrets Act 5 — wrongful communication | 9 | **75** | 1 / 2 / 1 / 2 / 2 / 1 | 70.0–80.0 | 2 | 2 |

**Alternative scenarios:** OSA 3 other-case publication branch (three-year maximum) is **9/12 → 75/100**; IT 67 subsequent conviction (five-year maximum, different bail classification) is **9/12 → 75/100**. These are declared branch changes, not additional independent laws.

**IT Act 66A: no score.** Struck down in its entirety in *Shreya Singhal* (2015). There are 16 parent-metadata matches and 4 selected PDFs. These are verification leads; a metadata listing does not prove a fresh/illegal charge.

\* Weight bands are the 5th–95th percentiles when each weight varies from 0.5 to 1.5. They measure assumption sensitivity, not uncertainty about real-world abuse.

† Counts refer to overlapping **CNR proceedings**, not independent cases. 505(1)/505(2) and 353(1)/353(2) share unresolved parent metadata counts; do not add these rows. IPC 499/500 uses a union, not a sum. The metadata contains verified Act errors, so these counts do not enter the score.

## What the requested datasets actually contributed

The [High Court dataset](https://registry.opendata.aws/indian-high-court-judgments/) supplied 106,408 case-detail rows from four Bombay High Court bench partitions. Joining selected offence metadata to 2024–2025 order records produced a 387-CNR retrieval frame. The deterministic law-stratified union selected **55 PDFs / 168 pages**, including 28 one-page orders. All selected PDFs were downloaded and text-extracted.

The [Supreme Court dataset](https://registry.opendata.aws/indian-supreme-court-judgments/) supplied metadata from 12 selected years (8,551 rows inspected) and **9 purposively selected judgments** for doctrine. Two clearly labeled official SCI supplements cover the 2022 sedition order and current BNS interpretation. Statutory and procedural components require the linked official Act/schedule text; court outcome frequency is not a substitute for that text.

The evidence layer contains **13 curated review items**, including 5 reviewed High Court proceedings. The rest have lexical retrieval candidates, not reviewed findings. The two element matrices are demonstrations, not independently annotated gold data.

Selection: SHA-256 of CNR within each parent-law metadata stratum, up to four per stratum, then union across strata. For each CNR, use the latest final order available within the fixed window, otherwise the latest order. This selects final/interim document type, not a desired outcome. Named Act controls the preliminary IPC/BNS identity; order date never supplies the code. FIR/offence date and operative text still require verification.

## Important findings from the PDF review

- **kedar-nath**: The Court limited application to disorder/public peace through violence. Broad bare text is not the complete operative legal standard. [PDF p.41](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=1962/english/S_1962_2_769_812_EN.pdf#page=41)
- **manzar**: Mens rea, context and the whole publication matter. Isolated hostile words cannot replace the legal elements. [PDF p.10](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2007/english/2007_4_907_917_EN.pdf#page=10)
- **ramji-lal**: The Court distinguished deliberate malicious insult from unwitting/careless insult and upheld the challenged provision. [PDF p.8](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=1957/english/1957_1_860_868_EN.pdf#page=8)
- **shreya-singhal**: Section 66A was struck down in its entirety. It is excluded from the index. [PDF p.112](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2015/english/2015_5_963_1074_EN.pdf#page=112)
- **subramanian-swamy**: Criminal defamation has a complaint/summons safeguard, and judicial process should not enable vendetta. This does not make every defamation complaint legitimate or abusive. [PDF p.152](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2016/english/2016_3_865_1017_EN.pdf#page=152)
- **thwaha**: The 43D(5) Chapters IV/VI bail restriction does not apply to section 13 alone. Do not assign all UAPA bail rules to every UAPA charge. [PDF p.35](https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2021/english/2021_8_797_834_EN.pdf#page=35)
- **imran-current-bns**: Current BNS 196 has a judicial mens rea requirement and contextual/reasonable-person safeguards. The absence of an explicit fault word in clause (a) is not absence of a legal fault requirement. This official SCI supplement was not selected from the AWS sample. [PDF p.40](https://api.sci.gov.in/supremecourt/2025/3511/3511_2025_4_1501_60508_Judgement_28-Mar-2025.pdf#page=40)
- **124a-2022-stay**: The May 2022 order kept pending 124A proceedings in abeyance; historical scoring is not permission to apply the repealed code to new conduct. [PDF p.4](https://api.sci.gov.in/supremecourt/2021/14059/14059_2021_1_301_35891_Order_11-May-2022.pdf#page=4)
- **hc-act-conflict**: Metadata labels a 2020 IPC prosecution as BNS. The opening operative narrative specifies IPC; BNS 152/353 metadata hits are not counted as verified BNS charges. [PDF p.1](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_233100030432025_10.pdf#page=1)
- **hc-farah-deeba**: The operative narrative confirms BNS 152, 196 and parent 353 in a WhatsApp-comment FIR. The Court refused quashing; this outcome is not a label of legitimacy. The 353 subsection is not resolved. [PDF p.2](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_230800032572025_2.pdf#page=2), [PDF p.10](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_230800032572025_2.pdf#page=10)
- **hc-linked-bail-proceeding**: A different CNR covers anticipatory bail for the SAME Kalepadal CR/FIR 178 of 2025. These are two proceedings from one identified prosecution family, not two independent criminal cases. [PDF p.1](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_233200019322025_2.pdf#page=1), [PDF p.1](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_233200019322025_2.pdf#page=1)
- **hc-bail-not-fir-quashing**: A lower-court bail-refusal order was quashed and bail granted for prolonged incarceration. The FIR/prosecution was not quashed. Multiple IPC, explosives and UAPA charges are bundled, so delay is not attributed to section 13 alone. [PDF p.2](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_231000010172025_5.pdf#page=2), [PDF p.6](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_231000010172025_5.pdf#page=6)
- **hc-defamation-not-confirmed**: Metadata lists BNS 356(2). The opening order instead concerns sexual-offence/POCSO and IT charges. This excerpt does not establish a defamation charge; the metadata hit remains unverified, not a negative finding. [PDF p.1](https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=2025/court=27_1/bench=newas/orders_2025_233100006252025_5.pdf#page=1)

The two Farah Deeba CNRs link to the same identified Kalepadal FIR 178/2025. This is a concrete reason to avoid treating unique CNRs as independent prosecutions. FIR-family linkage remains incomplete for the rest of the sample.

## Rubric and arithmetic

`raw total = sum of six ratings; display score = round(100 × raw total / 12)`

The ratings and equal weights are declared analyst assumptions, not fitted from quashing, bail, conviction or volume. Missing criteria would yield no point score. Invalidated 66A is excluded. The selected publication/communication limbs and penalty scenarios are stated in each law note.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Reach into expression | No express publication, words, or communication limb. | Communication limb confined to a defined class of protected official information. | Words, publication, or expressive content are an express route to liability. |
| Evaluative trigger language | Concrete conduct and object; no evaluative expression or harm trigger identified. | Evaluative trigger bounded by a specified object, such as reputation, religious insult, or obstruction of official functions. | Open political, group-affective, morality, or national-security terms, including potential harm rather than a specified completed injury. |
| Explicit mental-state gap | A specific deliberate/malicious harmful purpose is expressly required in the selected limb. | Knowledge, reason to believe, voluntariness, a purpose presumption, or mixed intent/effect routes; no specific malicious purpose required throughout. | No express mental-state qualifier in the selected expression limb. This is a TEXT feature, not a claim of strict liability. |
| Express expression-safeguard gap | Several express criticism/reporting exceptions or a broad public-good/art/learning exception in the linked text. | A conditional lawful-criticism or reasonable-belief/good-faith exception. | No general criticism, reporting, or public-interest exception identified in the selected provision/linked definition. |
| Arrest/bail exposure | Non-cognizable AND bailable under the linked central schedule. | Cognizable OR non-bailable, but not both. | Cognizable AND non-bailable, or a specific statutory anticipatory-bail bar. |
| Maximum imprisonment | Maximum up to and including two years. | Maximum greater than two and up to seven years. | Maximum greater than seven years, life imprisonment, or death. |

The mental-state component measures words present in the statutory clause. It does **not** assert strict liability. In particular, the high bare-text score for IPC 153A/BNS 196 must be read alongside the Court’s intent/context requirements. Judicial safeguards are not converted to invented numeric deductions in this build. General constitutional protections, complaint gates, sanction requirements, fines, charge bundling and enforcement conduct are not fully represented by six numbers.

Arrest classification is not a prediction that arrest will occur; non-bailable does not mean bail is impossible. CrPC/BNSS central schedules and special-act overrides are used. State amendments and later legal-version changes need a separate audit before operational use.

### Weight and rank sensitivity

10,000 seeded runs use independent Uniform(0.5,1.5) criterion weights, normalized by their sum. Each criterion is also omitted in turn. Rank bands are within each panel and retain ties. The Monte Carlo bands do not cover coding disagreements or source-version errors.

| Provision | Baseline rank range (ties) | Rank envelope over weight runs | Leave-one-out score min–max |
|---|---|---|---|
| IPC 124A — sedition (historical; 2022 abeyance order) | 1–2 | 1–2 | 90.0–100.0 |
| IPC 153A(1)(a)-(b) — promoting enmity | 1–2 | 1–2 | 90.0–100.0 |
| IPC 295A — deliberate malicious religious insult | 4–5 | 3–5 | 60.0–80.0 |
| IPC 505(1) — statements conducing to public mischief | 4–5 | 4–5 | 60.0–70.0 |
| IPC 505(2) — enmity from false/rumour reports | 3–3 | 3–4 | 70.0–80.0 |
| IPC 499/500 — criminal defamation | 6–7 | 6–7 | 20.0–40.0 |
| IPC 186 — obstructing public functions | 6–7 | 6–7 | 20.0–40.0 |
| BNS 152 — sovereignty, unity and integrity | 2–2 | 1–2 | 80.0–90.0 |
| BNS 196(1)(a)-(b) — promoting enmity | 1–1 | 1–2 | 90.0–100.0 |
| BNS 299 — deliberate malicious religious insult | 4–5 | 3–5 | 60.0–80.0 |
| BNS 353(1) — statements conducing to public mischief | 4–5 | 4–5 | 60.0–70.0 |
| BNS 353(2) — enmity from false/rumour reports | 3–3 | 3–4 | 70.0–80.0 |
| BNS 356(1)-(2) — criminal defamation | 6–7 | 6–7 | 20.0–40.0 |
| BNS 221 — obstructing public functions | 6–7 | 6–7 | 20.0–40.0 |
| UAPA 13 with 2(o) — unlawful activities | 1–2 | 1–2 | 80.0–90.0 |
| IT Act 67 — electronic obscenity (first conviction) | 4–4 | 2–4 | 60.0–80.0 |
| Official Secrets Act 3 — defence/code publication branch | 1–2 | 1–3 | 80.0–90.0 |
| Official Secrets Act 5 — wrongful communication | 3–3 | 3–4 | 70.0–80.0 |

Descriptive component correlations in this 18-row catalog: expression reach/evaluative language **r=0.354**; custody/imprisonment **r=0.8**. Related IPC/BNS profiles are not independent observations. These correlations flag potential double counting, not evidence that either criterion causes abuse. The full matrix and every omitted-criterion result are in `law-scores.json`.

## Per-law coding and sources

### IPC 124A — sedition (historical; 2022 abeyance order)

**11/12 → 92/100.** Historical text only. The 11 May 2022 Supreme Court order kept 124A proceedings in abeyance and restrained fresh use; this is not an active offence recommendation. BNS 152 is a related provision with different wording, not a one-to-one renumbering.

- **Reach into expression: 2** — Words, signs and representations are expressly covered.
- **Evaluative trigger language: 2** — Hatred, contempt and disaffection against the government are broad affective/political triggers.
- **Explicit mental-state gap: 2** — No express mental-state qualifier in the operative textual trigger; Kedar Nath judicial limitations are separate.
- **Express expression-safeguard gap: 1** — Explanations protect disapprobation seeking lawful alteration without the specified prohibited effects.
- **Arrest/bail exposure: 2** — CrPC central schedule: cognizable and non-bailable.
- **Maximum imprisonment: 2** — Maximum life imprisonment.

Official text: [IPC 124A, PDF pp. 55, 56](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 124A, PDF pp. 198](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 153A(1)(a)-(b) — promoting enmity

**11/12 → 92/100.** Expression/maintenance-of-harmony clauses only; drill/force clause (c) is outside the selected textual lens. Supreme Court intent/context safeguards are material.

- **Reach into expression: 2** — The words/representation limb expressly reaches expressive content.
- **Evaluative trigger language: 2** — Disharmony, enmity, hatred, ill-will and likely disturbance are evaluative group/public-order triggers.
- **Explicit mental-state gap: 2** — Clauses (1)(a)-(b) have no express intent qualifier in the text. Supreme Court mens rea requirements are displayed separately.
- **Express expression-safeguard gap: 2** — No express general public-interest or reporting exception in these clauses; judicial and constitutional safeguards remain relevant.
- **Arrest/bail exposure: 2** — The central procedural schedule classifies the offence as cognizable and non-bailable.
- **Maximum imprisonment: 1** — Three years ordinarily; five for the specified worship setting. Both are in the >2 to 7 band.

Official text: [IPC 153A, PDF pp. 66, 67](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 153A, PDF pp. 199](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 295A — deliberate malicious religious insult

**8/12 → 67/100.** 

- **Reach into expression: 2** — Insult through words or representation is an express route to liability.
- **Evaluative trigger language: 1** — The evaluative trigger is bounded by insult to a class's religion/religious beliefs.
- **Explicit mental-state gap: 0** — Deliberate AND malicious intention to outrage religious feelings is expressly required.
- **Express expression-safeguard gap: 2** — No general reporting/public-interest exception identified; the specific mens rea is coded in its own component.
- **Arrest/bail exposure: 2** — Cognizable and non-bailable in the central schedule.
- **Maximum imprisonment: 1** — Maximum three years.

Official text: [IPC 295A, PDF pp. 130](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 295A, PDF pp. 210](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 505(1) — statements conducing to public mischief

**8/12 → 67/100.** Metadata often records only 505; that does not identify this subsection. State amendments are not coded in this pilot.

- **Reach into expression: 2** — Making, publishing or circulating a statement, rumour or report is an express route to liability.
- **Evaluative trigger language: 2** — Fear/alarm, group enmity, public tranquillity and likelihood formulations are evaluative triggers.
- **Explicit mental-state gap: 1** — The text contains intent OR likely-effect alternatives; judicial mental-state requirements must be considered separately.
- **Express expression-safeguard gap: 1** — Reasonable grounds for believing truth plus good faith and absence of the specified intent provide a conditional exception.
- **Arrest/bail exposure: 1** — Non-cognizable but non-bailable under the central schedule.
- **Maximum imprisonment: 1** — Maximum three years in this subsection; the separate worship-setting variant of subsection (2) has five years.

Official text: [IPC 505(1), exception, PDF pp. 223, 224](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 505 first row, PDF pp. 223](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 505(2) — enmity from false/rumour reports

**9/12 → 75/100.** The same parent metadata denominator as 505(1) is displayed, not an independently confirmed subsection count.

- **Reach into expression: 2** — Making, publishing or circulating a statement, rumour or report is an express route to liability.
- **Evaluative trigger language: 2** — Fear/alarm, group enmity, public tranquillity and likelihood formulations are evaluative triggers.
- **Explicit mental-state gap: 1** — The text contains intent OR likely-effect alternatives; judicial mental-state requirements must be considered separately.
- **Express expression-safeguard gap: 1** — Reasonable grounds for believing truth plus good faith and absence of the specified intent provide a conditional exception.
- **Arrest/bail exposure: 2** — Cognizable and non-bailable under the central schedule.
- **Maximum imprisonment: 1** — Maximum three years in this subsection; the separate worship-setting variant of subsection (2) has five years.

Official text: [IPC 505(2)-(3), exception, PDF pp. 224](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 505 second row, PDF pp. 223](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 499/500 — criminal defamation

**4/12 → 33/100.** Definition (499) and punishment (500) form one row. Metadata counts use the UNION of CNR records, avoiding double counting.

- **Reach into expression: 2** — Making/publishing an imputation through words or representation expressly reaches expression.
- **Evaluative trigger language: 1** — Reputational harm is evaluative, but Explanation 4 specifies forms of lowered estimation.
- **Explicit mental-state gap: 1** — Intending harm, knowledge, OR reason to believe are express alternatives.
- **Express expression-safeguard gap: 0** — Ten exceptions include truth PLUS public good, good-faith opinion on public conduct, and substantially true court reports; truth alone is not universal immunity.
- **Arrest/bail exposure: 0** — The central schedule makes criminal defamation non-cognizable and bailable.
- **Maximum imprisonment: 0** — Maximum two years; BNS also permits community service.

Official text: [IPC 499 exceptions and 500, PDF pp. 218, 219, 220, 221](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 500, PDF pp. 222](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IPC 186 — obstructing public functions

**4/12 → 33/100.** CrPC 195 complaint gate should also be reviewed. A lower textual score does not rule out retaliatory application or charge bundling.

- **Reach into expression: 0** — No independent words/publication limb; prosecution requires obstruction of official functions.
- **Evaluative trigger language: 1** — Obstruction is evaluative, but tied to a public servant discharging public functions.
- **Explicit mental-state gap: 1** — Voluntarily is an express qualifier, not a specific malicious-expression purpose.
- **Express expression-safeguard gap: 2** — No general reporting/public-interest exception in this provision. Complaint/cognizance gates are additional safeguards outside this component.
- **Arrest/bail exposure: 0** — Non-cognizable and bailable under the central schedule.
- **Maximum imprisonment: 0** — Maximum three months.

Official text: [IPC 186, PDF pp. 83](https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf); [CRPC First Schedule: 186, PDF pp. 201, 202](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### BNS 152 — sovereignty, unity and integrity

**10/12 → 83/100.** BNS baseline commenced 1 July 2024. Related subject matter to 124A, but different prohibited conduct, fault words and fixed-term alternative.

- **Reach into expression: 2** — Words, signs, visible representation and electronic communication are expressly covered, along with other conduct.
- **Evaluative trigger language: 2** — Subversive activities, separatist feelings and endangering unity/integrity have evaluative breadth.
- **Explicit mental-state gap: 1** — Purposely OR knowingly is explicit; it is stronger textual specification than IPC 124A, but not a malicious-purpose-only threshold.
- **Express expression-safeguard gap: 1** — Explanation protects lawful-change criticism without exciting the specified activities.
- **Arrest/bail exposure: 2** — BNSS schedule: cognizable and non-bailable.
- **Maximum imprisonment: 2** — Maximum life imprisonment; alternative fixed term up to seven years.

Official text: [BNS 152, PDF pp. 60](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 152, PDF pp. 168](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 196(1)(a)-(b) — promoting enmity

**11/12 → 92/100.** Explicit electronic-communication wording. Current Supreme Court safeguards in Imran Pratapgadhi (2025) are separately recorded; identical index components do not imply identical law.

- **Reach into expression: 2** — The words/representation limb expressly reaches expressive content.
- **Evaluative trigger language: 2** — Disharmony, enmity, hatred, ill-will and likely disturbance are evaluative group/public-order triggers.
- **Explicit mental-state gap: 2** — Clauses (1)(a)-(b) have no express intent qualifier in the text. Supreme Court mens rea requirements are displayed separately.
- **Express expression-safeguard gap: 2** — No express general public-interest or reporting exception in these clauses; judicial and constitutional safeguards remain relevant.
- **Arrest/bail exposure: 2** — The central procedural schedule classifies the offence as cognizable and non-bailable.
- **Maximum imprisonment: 1** — Three years ordinarily; five for the specified worship setting. Both are in the >2 to 7 band.

Official text: [BNS 196, PDF pp. 68](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 196, PDF pp. 171, 172](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 299 — deliberate malicious religious insult

**8/12 → 67/100.** Explicit electronic-means wording. Judicial construction must be checked independently from the IPC mapping.

- **Reach into expression: 2** — Insult through words or representation is an express route to liability.
- **Evaluative trigger language: 1** — The evaluative trigger is bounded by insult to a class's religion/religious beliefs.
- **Explicit mental-state gap: 0** — Deliberate AND malicious intention to outrage religious feelings is expressly required.
- **Express expression-safeguard gap: 2** — No general reporting/public-interest exception identified; the specific mens rea is coded in its own component.
- **Arrest/bail exposure: 2** — Cognizable and non-bailable in the central schedule.
- **Maximum imprisonment: 1** — Maximum three years.

Official text: [BNS 299, PDF pp. 87](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 299, PDF pp. 181](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 353(1) — statements conducing to public mischief

**8/12 → 67/100.** The text expressly adds false information and electronic means; parent metadata does not resolve the subsection.

- **Reach into expression: 2** — Making, publishing or circulating a statement, rumour or report is an express route to liability.
- **Evaluative trigger language: 2** — Fear/alarm, group enmity, public tranquillity and likelihood formulations are evaluative triggers.
- **Explicit mental-state gap: 1** — The text contains intent OR likely-effect alternatives; judicial mental-state requirements must be considered separately.
- **Express expression-safeguard gap: 1** — Reasonable grounds for believing truth plus good faith and absence of the specified intent provide a conditional exception.
- **Arrest/bail exposure: 1** — Non-cognizable but non-bailable under the BNSS schedule.
- **Maximum imprisonment: 1** — Maximum three years in this subsection; the separate worship-setting variant of subsection (2) has five years.

Official text: [BNS 353(1), exception, PDF pp. 107](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 353(1), PDF pp. 188](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 353(2) — enmity from false/rumour reports

**9/12 → 75/100.** Parent metadata overlap is retained explicitly. No IPC-to-BNS frequency trend is inferred.

- **Reach into expression: 2** — Making, publishing or circulating a statement, rumour or report is an express route to liability.
- **Evaluative trigger language: 2** — Fear/alarm, group enmity, public tranquillity and likelihood formulations are evaluative triggers.
- **Explicit mental-state gap: 1** — The text contains intent OR likely-effect alternatives; judicial mental-state requirements must be considered separately.
- **Express expression-safeguard gap: 1** — Reasonable grounds for believing truth plus good faith and absence of the specified intent provide a conditional exception.
- **Arrest/bail exposure: 2** — Cognizable and non-bailable under the BNSS schedule.
- **Maximum imprisonment: 1** — Maximum three years in this subsection; the separate worship-setting variant of subsection (2) has five years.

Official text: [BNS 353(2)-(3), exception, PDF pp. 107](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 353(2), PDF pp. 188](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 356(1)-(2) — criminal defamation

**4/12 → 33/100.** The score is for the definition and direct defamation offence; printing/selling variants are not separately rated. Community service is available.

- **Reach into expression: 2** — Making/publishing an imputation through words or representation expressly reaches expression.
- **Evaluative trigger language: 1** — Reputational harm is evaluative, but Explanation 4 specifies forms of lowered estimation.
- **Explicit mental-state gap: 1** — Intending harm, knowledge, OR reason to believe are express alternatives.
- **Express expression-safeguard gap: 0** — Ten exceptions include truth PLUS public good, good-faith opinion on public conduct, and substantially true court reports; truth alone is not universal immunity.
- **Arrest/bail exposure: 0** — The central schedule makes criminal defamation non-cognizable and bailable.
- **Maximum imprisonment: 0** — Maximum two years; BNS also permits community service.

Official text: [BNS 356 definition, exceptions, punishment, PDF pp. 108, 109, 110](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 356(2), PDF pp. 188](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### BNS 221 — obstructing public functions

**4/12 → 33/100.** Fine increases to INR 2,500 in the linked text; the six-criterion rubric does not measure fines. BNSS 215 complaint gate is outside the six components.

- **Reach into expression: 0** — No independent words/publication limb; prosecution requires obstruction of official functions.
- **Evaluative trigger language: 1** — Obstruction is evaluative, but tied to a public servant discharging public functions.
- **Explicit mental-state gap: 1** — Voluntarily is an express qualifier, not a specific malicious-expression purpose.
- **Express expression-safeguard gap: 2** — No general reporting/public-interest exception in this provision. Complaint/cognizance gates are additional safeguards outside this component.
- **Arrest/bail exposure: 0** — Non-cognizable and bailable under the central schedule.
- **Maximum imprisonment: 0** — Maximum three months.

Official text: [BNS 221, PDF pp. 73](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf); [BNSS First Schedule: 221, PDF pp. 174](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### UAPA 13 with 2(o) — unlawful activities

**10/12 → 83/100.** Do not import the Chapters IV/VI prima-facie-true bail embargo into section 13 alone. Bundled terrorism charges create distinct exposure.

- **Reach into expression: 2** — Definition expressly includes spoken/written words; section 13 includes advocacy/advice/incitement.
- **Evaluative trigger language: 2** — Disaffection, questioning sovereignty, and supporting secession claims are broad political triggers.
- **Explicit mental-state gap: 1** — Definition has mixed intention/support/effect routes; this textual coding does not displace judicial fault requirements.
- **Express expression-safeguard gap: 2** — Section 13(3) excludes authorized treaty/negotiation activity, not general journalism or public-interest speech.
- **Arrest/bail exposure: 2** — Cognizable; seven-year limb is non-bailable under the other-laws schedule; 43D(4) excludes anticipatory bail. 43D(5) is NOT applicable to section 13 alone.
- **Maximum imprisonment: 1** — Section 13(1) maximum seven years; subsection (2) five.

Official text: [UAPA 2(o), 13, 14, 43D(4)-(5), PDF pp. 6, 10, 11, 20, 21](https://www.mha.gov.in/sites/default/files/A1967-37_0.pdf); [CRPC First Schedule II, PDF pp. 223](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf).

### IT Act 67 — electronic obscenity (first conviction)

**8/12 → 67/100.** First-conviction baseline. Repeated-conviction scenario would change custody from 1 to 2, increasing the total by one point. 67A/67B are separate offences and excluded from metadata matching.

- **Reach into expression: 2** — Electronic publishing/transmission is an express route to liability.
- **Evaluative trigger language: 2** — Lascivious/prurient/deprave-or-corrupt formulations are evaluative morality triggers.
- **Explicit mental-state gap: 2** — No express fault word in section 67's operative text; this does not assert that courts dispense with mens rea.
- **Express expression-safeguard gap: 0** — The proviso following 67B expressly extends public-good/science/literature/art/learning and heritage/religious exceptions to section 67.
- **Arrest/bail exposure: 1** — 77B: a three-year offence is cognizable and bailable. Subsequent-conviction five-year exposure is a different scenario.
- **Maximum imprisonment: 1** — First conviction maximum three years; subsequent conviction five years (same penalty band but different custody component).

Official text: [IT 67; proviso after 67B; 77B, PDF pp. 25, 26, 30](https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf).

### Official Secrets Act 3 — defence/code publication branch

**10/12 → 83/100.** This row explicitly rates the fourteen-year defence/code branch in the information/publication lens; physical-entry conduct is not independently scored. The other-case three-year branch has penalty rating 1, a separate 9/12 (75/100) scenario.

- **Reach into expression: 1** — Publication/communication concerns a specified class of protected official/security information.
- **Evaluative trigger language: 2** — Useful to an enemy, prejudicial purpose, and security/integrity/friendly-relations terms are broad evaluative triggers.
- **Explicit mental-state gap: 1** — Prejudicial purpose is required, but subsection (2) permits purpose inferences/presumptions from circumstances/conduct/known character.
- **Express expression-safeguard gap: 2** — No general journalism/public-interest publication defence in this section; lawful authority is a separate limitation.
- **Arrest/bail exposure: 2** — Three/fourteen-year alternatives are cognizable and non-bailable under the central other-laws classification.
- **Maximum imprisonment: 2** — Maximum fourteen years for specified defence/code cases; three in other cases.

Official text: [OSA 3(1)(c), 3(2), PDF pp. 3, 4](https://www.mha.gov.in/sites/default/files/2022-10/OSA1923_02092022%5B1%5D.pdf); [CRPC First Schedule II, PDF pp. 223](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf); [BNSS First Schedule II, PDF pp. 189](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

### Official Secrets Act 5 — wrongful communication

**9/12 → 75/100.** Communication, retention, receipt and care limbs differ. A whole-section profile cannot decide whether any particular reporter satisfies an offence.

- **Reach into expression: 1** — Communication/receipt is limited to the specified official/confidential/security information categories.
- **Evaluative trigger language: 2** — Protected-information categories extend to entrusted information and potential security/foreign-relations harm.
- **Explicit mental-state gap: 1** — Mixed wilful/knowing/reason-to-believe routes and reasonable-care or retention limbs require separate conduct-level review.
- **Express expression-safeguard gap: 2** — Authorized communication, a court, or state-interest duty is recognized, but no general public-interest journalism defence is identified.
- **Arrest/bail exposure: 2** — Three-year maximum is cognizable and non-bailable in the central other-laws schedule.
- **Maximum imprisonment: 1** — Maximum three years under subsection (4).

Official text: [OSA 5(1)-(4), PDF pp. 5, 6](https://www.mha.gov.in/sites/default/files/2022-10/OSA1923_02092022%5B1%5D.pdf); [CRPC First Schedule II, PDF pp. 223](https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf); [BNSS First Schedule II, PDF pp. 189](https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf).

## Element-matrix examples and remaining validation

Each cell separates specific recorded facts, merely formulaic allegation (only when the allegation record is sufficiently complete), explicit judicial absence, and an unavailable/unassessed record. Evidence source type is separate. No numerical Charge–Conduct Distance is emitted before the element definitions and coding are reviewed.

| Example | Element | State |
|---|---|---|
| patricia-elements | expressive act | specific facts recorded |
| patricia-elements | intention to promote class/community hatred | court explicitly finds absent |
| patricia-elements | incitement to community violence | court explicitly finds absent |
| farah-elements | communication | specific facts recorded |
| farah-elements | purpose/knowledge tied to a specified prohibited activity | not assessed in this pilot |
| farah-elements | secession/rebellion/subversive activity or specified danger | not assessed in this pilot |

Completed: data access, Act-bound section normalization, deterministic sampling, PDF extraction, verified-span evidence storage, editable scoring, weight/rank sensitivity and code tests. **No classifier was trained, no expert agreement statistic or model accuracy was measured, and no expert pairwise ordering was obtained.** Those results must not be fabricated from this small curated layer.

Next validation: have legal teammates independently code the profiles and the 2–3-law element pilot, preserve disagreements, test relevance/field extraction on held-out case families, and compare ordering against independent expert pairs. Include source and time holdouts once labels exist. The current corpus is a selected High Court sample and cannot estimate population abuse prevalence, journalist targeting probability, or IPC-to-BNS causal changes.

Claude reviewed the design and final proposed profiles in the existing authorized chat. Its final audit checked arithmetic and requested an explicit OSA 3 penalty-branch label and a visible historical 124A flag; both are incorporated. Claude expressly did not re-read the statutes in that final audit, so this is not independent expert legal validation. The implementation separately checked the linked text and schedules. See `claude-score-review.png`.

## Deliverables

- `law-scores.json`: all profiles, arithmetic, denominators, sources and sensitivity.
- `court-evidence.json`: verified review spans, two element examples, 55-document HC index and nine AWS SC documents.
- `corpus-summary.json`: scope, units and selection.
- `source-manifest.json`: source URLs and cached-file SHA-256 hashes where available.
- `trialwatch-pilot.zip`: code, offline text snapshot and reports; public PDF source links remain in the manifest.

Dataset attribution: Indian High Court Judgments and Indian Supreme Court Judgments datasets, maintained by Dattam Labs and contributors, distributed through the AWS Registry of Open Data; see their registry pages and repositories for the stated CC BY 4.0 license. Government statutes and supplemental Supreme Court documents are separately attributed by direct source URL. All legal judgments in this report are provisional research interpretations.
