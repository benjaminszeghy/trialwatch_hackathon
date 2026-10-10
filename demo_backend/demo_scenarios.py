"""Explicitly fictional scenarios in an independent database; never training data."""
from datetime import timedelta
from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from .core import Config
from .feedback import contexts
from .relevance import DEFAULTS, RelevanceInput, save, today

SCENARIOS = [
    ('Urgent counsel gap', '152', dict(counsel='unavailable',interpretation='unavailable',defence_access='restricted',custody='yes',opening_status='ready',openings=['legal_support']),
     'A fictional reporter faces proceedings over a published investigation. Counsel and interpretation are unavailable; defence access is restricted. The reporter is in custody. A legal-support review route is available.'),
    ('Monitoring opportunity', '196', dict(counsel='unavailable',interpretation='unavailable',defence_access='restricted',opening_status='to_arrange',openings=['monitoring']),
     'A fictional reporter faces proceedings over an article. Counsel, interpretation and defence access are missing. The reporter is not in custody. A trial-monitoring route could be arranged.'),
    ('Limited support access', '353', dict(counsel='limited',interpretation='limited',opening_status='to_arrange',openings=['monitoring']),
     'A fictional reporter faces proceedings over a broadcast. Counsel and interpretation have access gaps. Defence access is adequate. A monitoring route could be arranged.'),
    ('Support already available', '356', dict(opening_status='to_arrange',openings=['advocacy']),
     'A fictional reporter faces defamation proceedings. Counsel and defence access are available; interpretation is not required. There is no known immediate threat. An evidence-review route could be arranged.'),
    ('Subsection needs verification', '196', dict(counsel='limited',interpretation='limited',opening_status='to_arrange',openings=['monitoring']),
     'A fictional reporter is associated with BNS 196(1)(c). This subsection has no applicable score in the pilot. Support access is limited. Verify the charge before applying a law profile.'),
    ('Completed support review', '299', dict(case_stage='completed',workflow_status='closed',close_reason='Fictional scenario: support review completed and no unresolved actionable need remains.'),
     'A fictional reporter had proceedings over a publication. The support review is completed, with no unresolved counsel, language, defence, timing or safety needs. The fictional review has been closed with a reason.'),
]


def config(directory):
    return Config(state_dir=directory,court='demo',court_name='Fictional demo scenarios',benches=['demo'])


def pdf(text):
    writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    import textwrap
    lines=[]
    for paragraph in text.split('\n'):
        lines.extend(textwrap.wrap(paragraph,78) or [''])
    content='BT /F1 11 Tf 45 790 Td 16 TL\n'
    for line in lines:
        escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        content+='('+escaped+') Tj T*\n'
    stream=DecodedStreamObject();stream.set_data((content+'ET').encode('latin-1'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=BytesIO();writer.write(out);return out.getvalue()


def seed(store, *, reset=False):
    if reset:
        # This helper receives only the independently mounted sandbox store.
        with store.db() as db:
            for table in ('case_reviews','case_review_events','case_fit_reviews','case_fit_review_events','case_relevance','case_relevance_events','case_fit_features'):
                db.execute('DELETE FROM '+table)
    for i,(title,section,changes,description) in enumerate(SCENARIOS,1):
        cnr=f'DEMO-{i:03d}'
        with store.db() as db:
            exists=db.execute('SELECT 1 FROM cases WHERE cnr=?',(cnr,)).fetchone()
        if exists and not reset:continue
        subsection='196(1)(c)' if i==5 else '353(1)' if section=='353' else section
        store.case(cnr,'Demo - '+title,'Fictional scenarios','demo',[section],{'synthetic_demo':True,'training_eligible':False,'acts':[{'act':'Bharatiya Nyaya Sanhita','section':subsection}]})
        if i==3:description='The applicant published a broadcast. '+description
        body=f'FICTIONAL DEMO - NOT A COURT ORDER\n\n{title}\nSynthetic charge: Section {subsection} of the Bharatiya Nyaya Sanhita (BNS).\n\n{description}\n\nPrescribed example facts only. No real person, court or finding of misuse. Review answers start blank. Use Reset examples to restore the sandbox.'
        identifier,_=store.document(cnr,cnr,today().isoformat(),'https://example.invalid/trialwatch-demo/'+cnr+'.pdf',{'synthetic_demo':True})
        store.save_pdf(identifier,pdf(body),[{'page':1,'text':body}])
        if i==3:continue  # Demonstrate automatic fit + feedback, without prefilled human votes.
        facts=DEFAULTS|{'journalist_nexus':'confirmed','case_stage':'ongoing','counsel':'available','interpretation':'not_required','defence_access':'adequate','custody':'no','immediate_threat':'no','deadline_status':'none','opening_status':'none','evidence_note':'Prescribed fictional demonstration scenario. These are synthetic example facts, not observations from a real case.'}|changes
        with store.db() as db:
            version=contexts(db)[cnr]['evidence_version']
        save(store,cnr,RelevanceInput(**facts,expected_revision=0,evidence_version=version))
