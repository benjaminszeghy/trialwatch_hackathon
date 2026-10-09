"""Export TrialWatch case matches to an Excel workbook with review-ready columns.

Uses artifact_tool. One row is one provision mention in a source document,
not necessarily a criminal charge, defendant, or distinct court case.
"""
from __future__ import annotations
import csv
from pathlib import Path
from artifact_tool import Workbook, SpreadsheetFile

ROOT = Path(__file__).resolve().parents[1]
LAW_CSV = ROOT / 'data' / 'law_scores.csv'

# Explicitly separate machine-observed, manually verified, and unknown fields.
HEADERS = [
    'document_id','source_url','retrieved_at_utc','document_title','sha256',
    'law_id','law_label','law_score_100','law_status','matched_excerpt',
    'speech_term_hits','requires_human_review','review_note','text_file',
    'court','case_number','judgment_date','case_stage','defendant_name',
    'defendant_role','journalism_nexus','alleged_conduct','charge_verified',
    'charge_conduct_distance','pretrial_detention','bail_status',
    'lawyer_access','procedural_concern','disposition','quashing_reason',
    'judicial_criticism','source_evidence_quote','source_page_or_para',
    'reviewer','review_status','notes'
]
MANUAL_FIELDS = HEADERS[14:]
DATA_DICTIONARY = [
 ('document_id','Auto','SHA-256-derived ID of extracted document text; not a court case ID'),
 ('source_url','Auto','URL where the document was fetched; verify against authoritative source'),
 ('retrieved_at_utc','Auto','UTC retrieval timestamp'),
 ('document_title','Auto','HTML title or document-type placeholder'),
 ('sha256','Auto','Full text SHA-256 for duplicate detection'),
 ('law_id','Auto (candidate)','Statutory provision mentioned in text; NOT a verified charge'),
 ('law_label','Auto','Label from team-supplied scoring table'),
 ('law_score_100','Auto (team rubric)','Structural law score, not a case-specific abuse probability'),
 ('law_status','Auto','Current/continuing/invalid status from supplied rubric'),
 ('matched_excerpt','Auto','Short text around first provision mention; not proof of charge'),
 ('speech_term_hits','Auto (weak signal)','Keyword mentions only; not proof defendant is journalist'),
 ('requires_human_review','Auto','True for each provision match'),
 ('review_note','Auto','Warning and required verification'),
 ('text_file','Auto','Relative path to locally saved extracted text'),
 ('court','Manual','Name of adjudicating court'),
 ('case_number','Manual','Court docket/case number; verify source'),
 ('judgment_date','Manual','Decision date; distinct from alleged conduct or arrest date'),
 ('case_stage','Manual','e.g. FIR, bail, quashing, trial, appeal'),
 ('defendant_name','Manual','Person/entity named; handle personal data responsibly'),
 ('defendant_role','Manual','Journalist / activist / other / unknown; source-backed'),
 ('journalism_nexus','Manual','Yes / No / Unknown; basis for connection to reporting/expression'),
 ('alleged_conduct','Manual','Neutral summary of alleged acts with supporting citation'),
 ('charge_verified','Manual','Yes / No / Unknown; court document confirms actual charge'),
 ('charge_conduct_distance','Manual','Low / Medium / High / Unknown; reviewer-assessed mismatch'),
 ('pretrial_detention','Manual','Yes / No / Unknown; timing and evidence in notes'),
 ('bail_status','Manual','Granted / Denied / Pending / Unknown / N/A'),
 ('lawyer_access','Manual','Yes / No / Unknown; lack of documentation is Unknown'),
 ('procedural_concern','Manual','Documented concern / None documented / Unknown; no inference from silence'),
 ('disposition','Manual','Outcome and stage; not equivalent to proof of abuse'),
 ('quashing_reason','Manual','Specific court reasoning if quashed'),
 ('judicial_criticism','Manual','Relevant court language with quote and source'),
 ('source_evidence_quote','Manual','Verbatim short quote grounding manual coding'),
 ('source_page_or_para','Manual','Page/paragraph/section supporting evidence'),
 ('reviewer','Manual','Reviewer initials or team member'),
 ('review_status','Manual','Not reviewed / In review / Verified / Needs follow-up'),
 ('notes','Manual','Uncertainty, contradictions, caveats')
]

def _col_letter(n):
    s=''
    while n:
        n,rem=divmod(n-1,26)
        s=chr(65+rem)+s
    return s

def _style_header(sh, ncols, last_row=1):
    sh.get_range(f'A1:{_col_letter(ncols)}1').format = {
        'fill':'#17324D','font':{'bold':True,'color':'#FFFFFF'},
        'row_height':34,'wrap_text':True,'vertical_alignment':'center'
    }
    sh.freeze_panes.freeze_rows(1)
    sh.get_range(f'A1:{_col_letter(ncols)}{max(last_row,2)}').format.column_width=19

def export_excel(rows: list[dict], errors: list[dict], destination: Path, scores_path: Path = LAW_CSV):
    wb=Workbook.create()
    cases=wb.worksheets.add('Case Matches')
    matrix=[HEADERS]+[[r.get(h,'') if h not in MANUAL_FIELDS else '' for h in HEADERS] for r in rows]
    cases.get_range_by_indexes(0,0,len(matrix),len(HEADERS)).values=matrix
    _style_header(cases,len(HEADERS),len(matrix))
    for col in ['B','J','M','V','AG','AJ']:
        cases.get_range(f'{col}:{col}').format.column_width=42
    cases.get_range('H:H').format.column_width=15
    cases.get_range('I:I').format.column_width=25
    if rows:
        cases.tables.add(f'A1:{_col_letter(len(HEADERS))}{len(matrix)}',True,'CaseMatches')
        cases.get_range(f'H2:H{len(matrix)}').conditional_formats.add_data_bar({'color':'#4F83B8','gradient':True})
    law=wb.worksheets.add('Law Scores')
    with scores_path.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        cols=list(reader.fieldnames)
        score_rows=list(reader)
    law.get_range_by_indexes(0,0,len(score_rows)+1,len(cols)).values=[cols]+[[int(r[c]) if c in ('score','total_points') and r[c] else r[c] for c in cols] for r in score_rows]
    _style_header(law,len(cols),len(score_rows)+1)
    law.get_range('B:B').format.column_width=48
    law.get_range('F:F').format.column_width=32
    law.get_range('G:G').format.column_width=76
    law.tables.add(f'A1:G{len(score_rows)+1}',True,'LawScores')
    dd=wb.worksheets.add('Field Guide')
    dd.get_range_by_indexes(0,0,len(DATA_DICTIONARY)+1,3).values=[['Column','Source','Meaning / review rule']]+[list(r) for r in DATA_DICTIONARY]
    _style_header(dd,3,len(DATA_DICTIONARY)+1)
    dd.get_range('A:A').format.column_width=30
    dd.get_range('B:B').format.column_width=23
    dd.get_range('C:C').format.column_width=105
    dd.tables.add(f'A1:C{len(DATA_DICTIONARY)+1}',True,'FieldGuide')
    es=wb.worksheets.add('Fetch Errors')
    es.get_range_by_indexes(0,0,len(errors)+1,2).values=[['source_url','error']]+[[r.get('source_url',''),r.get('error','')] for r in errors]
    _style_header(es,2,len(errors)+1)
    es.get_range('A:A').format.column_width=60
    es.get_range('B:B').format.column_width=80
    readme=wb.worksheets.add('START HERE')
    info=[
      ['TRIALWATCH / JIWON SCRAPER','HOW TO USE'],
      ['Case Matches','One row = document + provision mention, NOT a confirmed prosecution'],
      ['Law Scores','Team-supplied 0-100 structural rubric; no validation of legal merits'],
      ['Manual review','Columns court through notes are intentionally blank; cite sources before filling'],
      ['Unknown ≠ No','Missing facts must remain blank or Unknown; do not infer innocence/guilt or violations'],
      ['IT-66A','Invalidated provision: flag for historical/contextual review; no active-law score'],
      ['Sources','Use public HTTPS URLs and comply with site terms, robots policies and rate limits'],
      ['Coverage','URL-list ingestion only; not a comprehensive court index or real-time monitoring'],
      ['Judgment bias','Court judgments reflect selected litigated matters; not prosecution prevalence'],
      ['Scoring','Do not sort solely by structural law score as a proxy for individual case risk'],
    ]
    readme.get_range_by_indexes(0,0,len(info),2).values=info
    _style_header(readme,2,len(info))
    readme.get_range('A:A').format.column_width=27
    readme.get_range('B:B').format.column_width=110
    destination.parent.mkdir(parents=True,exist_ok=True)
    SpreadsheetFile.export_xlsx(wb).save(str(destination))
    return destination
