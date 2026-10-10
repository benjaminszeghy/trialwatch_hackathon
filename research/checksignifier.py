#!/usr/bin/env python3
"""Conservative PDF-link intake, evidence-based triage, sorted Excel report.
Requires: pip install pypdf artifact-tool
JSON supports list or {'cases': [...]}; one object per PDF or case.
No AI claims are fabricated: optional evidence must be structured and source attributed.
"""
import argparse, hashlib, io, json, re, urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

PROCEDURAL = {
 'counsel_denied': ('Counsel denied or access obstructed', 22),
 'interpreter_denied': ('Necessary interpretation denied', 18),
 'unlawful_detention': ('Court-identified unlawful detention', 26),
 'bail_irregularity': ('Documented bail/procedure irregularity', 12),
 'notice_denied': ('Charges or hearing notice denied', 12),
 'disclosure_denied': ('Material disclosure denied', 10),
 'hearing_denied': ('Meaningful hearing denied', 12),
 'court_bias': ('Specific impartiality concern', 15),
 'coercion': ('Coercion or mistreatment evidence', 25),
 'delay_unexplained': ('Documented unjustified delay', 8),
 'retaliation': ('Evidence of retaliation for reporting', 15),
}
LEGAL = {
 'element_gap': ('Specific statutory element contested/missing', 18),
 'speech_nexus': ('Alleged conduct appears connected to reporting', 12),
 'court_concern': ('Court raises statutory/proportionality concern', 24),
 'charge_invalid': ('Possible invalid provision cited as actual charge', 30),
 'selective_enforcement': ('Specific evidence of selective enforcement', 14),
}
ALL = {'procedural': PROCEDURAL, 'legal': LEGAL}
HEADERS = ['Priority Rank','Priority Tier','Priority Score','Urgency Score','Procedural Signal Score','Legal Signal Score','Case ID','Case Name','Journalist Status','Case Status','Currently Detained','Next Hearing','Days to Hearing','Counsel Present','Counsel Access','Interpreter Needed','Interpreter Provided','Language Barrier','Charge Provisions','Law Structural Score (context only)','Procedural Red Flags','Legal Red Flags','Evidence / Attribution','Evidence Gaps','Recommended TrialWatch Action','PDF URL','PDF Fetch Status','PDF Pages','PDF Text Preview','Data Confidence','Assessment Limitations','All PDF URLs','PDF Extracted Text File','Tier Rationale','Evidence Review Status','Closure Reviewer','Closure Date','Closure Rationale','Closure Evidence Reference','Closure Decision','Closure Validation']

def load(path):
 text=Path(path).read_text(encoding='utf-8')
 try: obj=json.loads(text)
 except json.JSONDecodeError: obj=[json.loads(line) for line in text.splitlines() if line.strip()]
 if isinstance(obj,dict):
  for key in ('cases','results','documents','items'):
   if isinstance(obj.get(key),list): return obj[key]
  return [obj]
 if not isinstance(obj,list):raise ValueError('JSON must contain a list or an object with cases/results/documents/items')
 return obj

def norm(v):return str(v or '').strip().lower()
def val(record,*keys):
 for k in keys:
  if record.get(k) is not None:return record[k]
 return None

def pdf_urls(rec):
 """Collect all direct and nested PDF links from a Benny JSON record."""
 urls=[]
 def add(value):
  if isinstance(value,str) and value.startswith(('https://','http://')) and value not in urls:urls.append(value)
  elif isinstance(value,dict):
   for k in ('pdf_url','pdf_link','document_url','url','href','link'):add(value.get(k))
 for k in ('pdf_url','pdf_link','document_url','url','pdf_links','pdf_urls','documents','links','attachments'):
  v=rec.get(k)
  if isinstance(v,list):
   for item in v:add(item)
  else:add(v)
 return urls

def pdf_url(rec):
 urls=pdf_urls(rec)
 return urls[0] if urls else ''

def fetch_pdf(url,max_mb=15):
 if not url:return 'NO_URL',0,''
 if urlparse(url).scheme!='https':return 'BLOCKED_NON_HTTPS',0,''
 try:
  from pypdf import PdfReader
 except ImportError:return 'PYPDF_NOT_INSTALLED',0,''
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'TrialWatchResearch/1.0','Accept':'application/pdf'})
  with urllib.request.urlopen(req,timeout=15) as resp:
   if resp.headers.get('Content-Length') and int(resp.headers['Content-Length'])>max_mb*1024*1024:return 'TOO_LARGE',0,''
   blob=resp.read(max_mb*1024*1024+1)
  if len(blob)>max_mb*1024*1024:return 'TOO_LARGE',0,''
  if not blob.startswith(b'%PDF'):return 'NOT_PDF',0,''
  reader=PdfReader(io.BytesIO(blob)); pages=len(reader.pages)
  chunks=[]
  for p in reader.pages[:30]:
   try:chunks.append((p.extract_text() or '')[:30000])
   except Exception:chunks.append('')
  text='\n'.join(chunks)
  return ('OK' if text.strip() else 'SCANNED_PDF_OCR_NEEDED'),pages,text[:120000]
 except Exception as e:return 'FETCH_ERROR:'+type(e).__name__,0,''

def signals(rec,domain):
 """Only explicit evidence assertions with source quote and attribution count; no keyword inference."""
 evidence=rec.get('evidence',[])
 if not isinstance(evidence,list):evidence=[]
 out=[]
 for e in evidence:
  if not isinstance(e,dict) or e.get('domain')!=domain:continue
  key=e.get('element'); quote=e.get('quote'); source=e.get('source_url') or e.get('document_url') or rec.get('pdf_url')
  if key not in ALL[domain] or not isinstance(quote,str) or not quote.strip() or not source:continue
  if e.get('assessment') not in ('concern','court_concern','court_violation_found','alleged_concern'):continue
  out.append((key,e))
 return out

def days_until(v):
 try:return (date.fromisoformat(str(v)[:10])-date.today()).days
 except (ValueError,TypeError):return None

def closure_decision(rec):
 """Closure is an explicit human disposition, never a score-based inference."""
 review=rec.get('human_review')
 if not isinstance(review,dict):return False,'NOT_REQUESTED'
 if norm(review.get('decision')) not in ('close_no_further_action','closed_no_further_action'):
  return False,'NOT_REQUESTED'
 required=('reviewer','reviewed_at','rationale','evidence_reference')
 missing=[k for k in required if not isinstance(review.get(k),str) or not review[k].strip()]
 if missing:return False,'INVALID_CLOSURE_MISSING_'+','.join(missing)
 try:date.fromisoformat(review['reviewed_at'][:10])
 except ValueError:return False,'INVALID_CLOSURE_DATE'
 if norm(rec.get('immediate_safety_risk')) in ('yes','true','1'):
  return False,'BLOCKED_ACTIVE_SAFETY_RISK'
 if norm(val(rec,'currently_detained','detained')) in ('yes','true','1'):
  return False,'BLOCKED_ACTIVE_DETENTION'
 if any(isinstance(e,dict) and e.get('urgent_override') is True for e in (rec.get('evidence') or [])):
  return False,'BLOCKED_URGENT_FLAG'
 return True,'VALID_HUMAN_CLOSURE'

def assess(rec,fetch=False):
 url=pdf_url(rec)
 status,pages,content=fetch_pdf(url) if fetch else ('NOT_FETCHED',0,'')
 cid=str(val(rec,'case_id','id','cnr') or hashlib.sha256((url or json.dumps(rec,sort_keys=True,default=str)).encode()).hexdigest()[:12])
 pro=signals(rec,'procedural'); leg=signals(rec,'legal')
 proscore=min(100,sum(PROCEDURAL[k][1] for k,_ in {k:(k,e) for k,e in pro}.values()))
 legscore=min(100,sum(LEGAL[k][1] for k,_ in {k:(k,e) for k,e in leg}.values()))
 detained=norm(val(rec,'currently_detained','detained'))
 d=days_until(val(rec,'next_hearing','next_hearing_date'))
 urgency=0
 # Current custody / imminent hearing are operational triage signals, not legal findings.
 if detained in ('yes','true','1'):urgency+=40
 if d is not None and 0<=d<=2:urgency+=35
 elif d is not None and 3<=d<=7:urgency+=22
 elif d is not None and 8<=d<=14:urgency+=10
 if norm(rec.get('immediate_safety_risk')) in ('yes','true','1'):urgency+=35
 urgency=min(100,urgency)
 score=round(.45*urgency+.30*proscore+.25*legscore)
 # Three-tier operational classification; score thresholds are provisional.
 # Override requires both a serious situation and a cited, source-attributed record.
 override=any(e.get('urgent_override') is True and e.get('quote') and (e.get('source_url') or e.get('document_url') or url) for e in (rec.get('evidence') or []) if isinstance(e,dict))
 if score>=75 or override:tier='Tier 1 - URGENT'
 elif score>=45:tier='Tier 2 - HIGH'
 else:tier='Tier 3 - ROUTINE'
 closed,closure_validation=closure_decision(rec)
 if closed:tier='Tier 4 - CLOSED'
 rationale=('Evidence-supported urgent escalation; ' if override else '')+f'Urgency {urgency}/100, procedural {proscore}/100, legal {legscore}/100; composite {score}/100. ' + ('Immediate human review.' if tier.startswith('Tier 1') else 'Priority investigation.' if tier.startswith('Tier 2') else 'Case reviewed and closed; reopen if material new evidence emerges.' if closed else 'Routine monitoring and verify unknowns.')
 # Do not infer counsel or interpreter absence from missing PDF mentions.
 gaps=[]
 for field in ('journalist_status','currently_detained','next_hearing','counsel_present','counsel_access','interpreter_needed','interpreter_provided','language_barrier'):
  if val(rec,field) is None:gaps.append(field)
 if not pro and not leg:gaps.append('no_source_attributed_signal_evidence')
 if status=='SCANNED_PDF_OCR_NEEDED':gaps.append('OCR_required')
 if status.startswith('FETCH_ERROR'):gaps.append('PDF_unavailable')
 evidence_text=' | '.join(f"{e.get('speaker','unspecified')}: {str(e.get('quote',''))[:180]} ({e.get('source_url') or e.get('document_url') or url}, p.{e.get('page','?')})" for _,e in pro+leg)
 action=('Verify custody, upcoming hearing and contact counsel urgently' if tier.startswith('Tier 1') else 'Request case file, verify source quotations and procedural safeguards' if tier.startswith('Tier 2') else 'Verify journalist nexus, actual charges and missing evidence')
 if norm(rec.get('journalist_status')) not in ('confirmed','verified','yes') and not closed:action='Verify journalist status first; '+action
 if closed:action='No further action; archive decision and reopen if material new evidence emerges'
 elif closure_validation not in ('NOT_REQUESTED','VALID_HUMAN_CLOSURE'):action='CLOSURE NOT ACCEPTED ('+closure_validation+'); '+action
 provisions=val(rec,'provisions','charges','laws') or []
 if isinstance(provisions,list):provisions=', '.join(str(x) for x in provisions)
 row={'Priority Rank':0,'Priority Tier':tier,'Priority Score':score,'Urgency Score':urgency,'Procedural Signal Score':proscore,'Legal Signal Score':legscore,'Case ID':cid,'Case Name':str(val(rec,'case_name','title') or ''),'Journalist Status':str(rec.get('journalist_status','Unknown')),'Case Status':str(rec.get('case_status','Unknown')),'Currently Detained':str(val(rec,'currently_detained','detained') or 'Unknown'),'Next Hearing':str(val(rec,'next_hearing','next_hearing_date') or 'Unknown'),'Days to Hearing':d,'Counsel Present':str(rec.get('counsel_present','Unknown')),'Counsel Access':str(rec.get('counsel_access','Unknown')),'Interpreter Needed':str(rec.get('interpreter_needed','Unknown')),'Interpreter Provided':str(rec.get('interpreter_provided','Unknown')),'Language Barrier':str(rec.get('language_barrier','Unknown')),'Charge Provisions':str(provisions),'Law Structural Score (context only)':str(rec.get('structural_score','Not assessed')),'Procedural Red Flags':'; '.join(PROCEDURAL[k][0] for k,_ in pro),'Legal Red Flags':'; '.join(LEGAL[k][0] for k,_ in leg),'Evidence / Attribution':evidence_text,'Evidence Gaps':'; '.join(gaps),'Recommended TrialWatch Action':action,'PDF URL':url,'PDF Fetch Status':status,'PDF Pages':pages,'PDF Text Preview':content[:800].replace('\n',' '),'Data Confidence':'Evidence supplied, not independently verified' if pro or leg else 'Low - requires manual extraction','Assessment Limitations':'Triage heuristic only; no misuse probability or judicial finding. PDF text is not automatically interpreted.','All PDF URLs':' | '.join(pdf_urls(rec)),'PDF Extracted Text File':'','Tier Rationale':rationale,'Evidence Review Status':'Human-reviewed closure' if closed else 'Manual verification required' if pro or leg else 'No source-attributed concerns supplied; verify manually','Closure Reviewer':str((rec.get('human_review') or {}).get('reviewer','')) if isinstance(rec.get('human_review'),dict) else '', 'Closure Date':str((rec.get('human_review') or {}).get('reviewed_at','')) if isinstance(rec.get('human_review'),dict) else '', 'Closure Rationale':str((rec.get('human_review') or {}).get('rationale','')) if isinstance(rec.get('human_review'),dict) else '', 'Closure Evidence Reference':str((rec.get('human_review') or {}).get('evidence_reference','')) if isinstance(rec.get('human_review'),dict) else '', 'Closure Decision':str((rec.get('human_review') or {}).get('decision','')) if isinstance(rec.get('human_review'),dict) else '', 'Closure Validation':closure_validation}
 return row,pro,leg

def excel(rows, out):
 from openpyxl import Workbook
 from openpyxl.styles import Font, PatternFill, Alignment
 from openpyxl.utils import get_column_letter
 from openpyxl.worksheet.table import Table, TableStyleInfo
 wb = Workbook()
 sh = wb.active
 sh.title = 'Priority Queue'
 sh.append(HEADERS)
 for row in rows:
  sh.append([row.get(h, '') for h in HEADERS])
 sh.freeze_panes = 'A2'
 sh.sheet_view.showGridLines = False
 sh.row_dimensions[1].height = 32
 for cell in sh[1]:
  cell.fill = PatternFill('solid', fgColor='15324D')
  cell.font = Font(color='FFFFFF', bold=True)
  cell.alignment = Alignment(wrap_text=True, vertical='center')
 for col in range(1, len(HEADERS)+1):
  letter = get_column_letter(col)
  sh.column_dimensions[letter].width = 16 if col <= 6 else 24 if col <= 21 else 42
 sh.auto_filter.ref = sh.dimensions
 if rows:
  tab = Table(displayName='PriorityQueue', ref=f'A1:{get_column_letter(len(HEADERS))}{len(rows)+1}')
  tab.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
  sh.add_table(tab)
 guide = wb.create_sheet('Scoring Guide')
 info = [
  ['Field','Interpretation'],
  ['Priority','Operational queue, not a legal conclusion'],
  ['Urgency (45%)','Custody + upcoming hearing + immediate safety risk'],
  ['Procedural (30%)','Only explicitly sourced, attributed procedural concerns'],
  ['Legal (25%)','Only explicitly sourced, attributed legal concerns'],
  ['Tier 1','Composite >=75 or evidence-supported urgent override'],
  ['Tier 2','Composite 45-74'],
  ['Tier 3','Composite <45; Unknown does not mean compliant'],
  ['Tier 4','Only explicit documented human closure, never automatic from low score'],
  ['Closure fields','human_review.decision/reviewer/reviewed_at/rationale/evidence_reference'],
  ['Closure safeguards','Cannot close while current detention, immediate safety risk, or urgent flag is recorded'],
  ['Interpreter','Only a problem if needed and inadequate/denied; absence of mention is Unknown'],
  ['Counsel','Presence alone is not sufficient; assess access and effectiveness'],
  ['Delay','Elapsed days alone never proves procedural misuse'],
  ['Structural law scores','Context only, excluded from case priority'],
  ['Evidence','PDF link + quote + source + speaker; not independently authenticated'],
  ['Limitations','No NLP/LLM evidence extraction; scanned PDFs require OCR'],
  ['Escalation','urgent_override=true in evidence with source and quote; human confirmation needed']
 ]
 for entry in info: guide.append(entry)
 for cell in guide[1]:
  cell.fill = PatternFill('solid', fgColor='15324D')
  cell.font = Font(color='FFFFFF', bold=True)
 guide.column_dimensions['A'].width = 30
 guide.column_dimensions['B'].width = 95
 guide.freeze_panes = 'A2'
 wb.save(str(out))

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',default='outputs/checksignifier.xlsx');p.add_argument('--fetch-pdfs',action='store_true');a=p.parse_args()
 records=load(a.input); rows=[]
 target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
 text_dir=target.parent/'pdf_text'; text_dir.mkdir(parents=True,exist_ok=True)
 for rec in records:
  if not isinstance(rec,dict):continue
  row,_,_=assess(rec,False)
  urls=pdf_urls(rec)
  if a.fetch_pdfs:
   summaries=[]
   for i,url in enumerate(urls,1):
    status,pages,content=fetch_pdf(url)
    summaries.append(f'{i}:{status} ({pages} pages)')
    if content:
     file=text_dir/f"{re.sub(r'[^A-Za-z0-9_-]', '_',row['Case ID'])[:60]}_{i}.txt"
     file.write_text(content,encoding='utf-8')
     row['PDF Extracted Text File']+=str(file)+' | '
     if not row['PDF Text Preview']:row['PDF Text Preview']=content[:800].replace('\n',' ')
    row['PDF Pages']+=pages
   row['PDF Fetch Status']='; '.join(summaries) if summaries else 'NO_URL'
  rows.append(row)
 order={'Tier 1 - URGENT':0,'Tier 2 - HIGH':1,'Tier 3 - ROUTINE':2,'Tier 4 - CLOSED':3}
 rows.sort(key=lambda r:(order.get(r['Priority Tier'],9),-r['Priority Score'],-r['Urgency Score'],r['Case ID']))
 for i,r in enumerate(rows,1):r['Priority Rank']=i
 excel(rows,target)
 target.with_suffix('.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'Wrote {len(rows)} ranked cases to {target}')
if __name__=='__main__':main()
