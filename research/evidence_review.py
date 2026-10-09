"""Small, explicitly curated evidence layer with exact-span provenance checks.

This is AI-assisted research annotation, not independent expert gold data.
No unreviewed keyword match is promoted to a judicial finding.
"""
import json
import re
from pathlib import Path
from data_access import ROOT, CACHE

def norm(text):
    return re.sub(r'\s+',' ',text).strip()

def quote(document, page, text, source_type='court reasoning'):
    pages=json.loads((ROOT/document['pages_json']).read_text())
    actual=next(p['text'] for p in pages if p['page']==page)
    if norm(text) not in norm(actual):
        raise ValueError(f'Unsupported evidence span: {document.get("case_id",document.get("cnr"))}, p{page}: {text}')
    return {'url':document['source_url'],'local_pages':document['pages_json'],
            'pdf_page':page,'quote':text,'source_type':source_type}

def supplemental(name,url):
    return {'pages_json':str((CACHE/f'supplemental/{name}.pages.json').relative_to(ROOT)),
            'source_url':url,'case_id':name}

def reviews():
    sc={d['case_id']:d for d in json.loads((CACHE/'sc_documents.json').read_text())}
    hc={d['cnr']:d for d in json.loads((CACHE/'hc_documents.json').read_text())}
    entries=[]
    def entry(identifier,laws,summary,evidence,kind='doctrine',**extra):
        entries.append({'id':identifier,'laws':laws,'kind':kind,'summary':summary,
            'evidence':evidence,'review_status':'AI-assisted analyst review; expert check pending',**extra})

    entry('kedar-nath',['IPC-124A'],
        'The Court limited application to disorder/public peace through violence. Broad bare text is not the complete operative legal standard.',
        [quote(sc['1962 INSC 17'],41,'limit their application to acts involving intention or tendency to create disorder')])
    entry('manzar',['IPC-153A'],
        'Mens rea, context and the whole publication matter. Isolated hostile words cannot replace the legal elements.',
        [quote(sc['2007 INSC 378'],10,'gist of the offence is the intention to promote feelings of enmity or hatred')])
    entry('ramji-lal',['IPC-295A'],
        'The Court distinguished deliberate malicious insult from unwitting/careless insult and upheld the challenged provision.',
        [quote(sc['1957 INSC 32'],8,'It only punishes the aggravated form of insult to religion')])
    entry('shreya-singhal',['IT-66A'],
        'Section 66A was struck down in its entirety. It is excluded from the index.',
        [quote(sc['2015 INSC 257'],112,'struck down in its entirety being violative of Article')])
    entry('subramanian-swamy',['IPC-499-500'],
        'Criminal defamation has a complaint/summons safeguard, and judicial process should not enable vendetta. This does not make every defamation complaint legitimate or abusive.',
        [quote(sc['2016 INSC 427'],152,'judicial process should not be an instrument of oppression or needless harassment.')])
    entry('thwaha',['UAPA-13'],
        'The 43D(5) Chapters IV/VI bail restriction does not apply to section 13 alone. Do not assign all UAPA bail rules to every UAPA charge.',
        [quote(sc['2021 INSC 688'],35,'sub-section (5) of Section 43D is not applicable to the offence under Section 13.')])

    imran=supplemental('imran-2025','https://api.sci.gov.in/supremecourt/2025/3511/3511_2025_4_1501_60508_Judgement_28-Mar-2025.pdf')
    entry('imran-current-bns',['BNS-196','BNS-299'],
        'Current BNS 196 has a judicial mens rea requirement and contextual/reasonable-person safeguards. The absence of an explicit fault word in clause (a) is not absence of a legal fault requirement. This official SCI supplement was not selected from the AWS sample.',
        [quote(imran,40,'Hence, mens rea will have to be read into Section 196 of the BNS')],
        dataset_origin='supplemental official Supreme Court PDF')
    stay=supplemental('vombatkere-2022','https://api.sci.gov.in/supremecourt/2021/14059/14059_2021_1_301_35891_Order_11-May-2022.pdf')
    entry('124a-2022-stay',['IPC-124A'],
        'The May 2022 order kept pending 124A proceedings in abeyance; historical scoring is not permission to apply the repealed code to new conduct.',
        [quote(stay,4,'All pending trials, appeals and proceedings with respect to the charge framed under Section 124A of IPC be kept in abeyance.')],
        dataset_origin='supplemental official Supreme Court PDF')

    # Metadata conflict is checked against the operative charge narrative, not a precedent mention.
    d=hc['HCBM010407652025']
    entry('hc-act-conflict',['BNS-152','BNS-353-1','BNS-353-2','IPC-505-2'],
        'Metadata labels a 2020 IPC prosecution as BNS. The opening operative narrative specifies IPC; BNS 152/353 metadata hits are not counted as verified BNS charges.',
        [quote(d,1,"Indian Penal Code, 1860 (‘ IPC’)",'court account of charges')],
        kind='metadata conflict',cnr=d['cnr'],excluded_metadata_hits=['BNS:152','BNS:353'],
        verified_charge_laws=['IPC-505-2'])
    d=hc['HCBM010319502025']
    entry('hc-farah-deeba',['BNS-152','BNS-196','BNS-353-1','BNS-353-2'],
        'The operative narrative confirms BNS 152, 196 and parent 353 in a WhatsApp-comment FIR. The Court refused quashing; this outcome is not a label of legitimacy. The 353 subsection is not resolved.',
        [quote(d,2,'offences punishable under Sections 152, 196, 197, 352 and 353 of the Bharatiya Nyay Sanhita, 2023', 'court account of charges'),
         quote(d,10,'present Petition stands dismissed.')],kind='charge/procedure example',cnr=d['cnr'],
        verified_charge_laws=['BNS-152','BNS-196'],verified_parent_hits=['BNS:353'],
        case_family_key='Pune|Kalepadal|178|2025')
    d=hc['HCBM010375472025']
    entry('hc-linked-bail-proceeding',['BNS-152','BNS-196','BNS-353-1','BNS-353-2'],
        'A different CNR covers anticipatory bail for the SAME Kalepadal CR/FIR 178 of 2025. These are two proceedings from one identified prosecution family, not two independent criminal cases.',
        [quote(d,1,'CR No.178 of 2025, registered at Kalepadal Police Station', 'court account of charges'),
         quote(d,1,'Sections 152, 196, 197, 352, and 353 of the Bharatiya Nyaya Sanhita, 2023', 'court account of charges')],
        kind='case family link',cnr=d['cnr'],verified_charge_laws=['BNS-152','BNS-196'],
        verified_parent_hits=['BNS:353'],case_family_key='Pune|Kalepadal|178|2025')
    d=hc['HCBM010024772025']
    entry('hc-bail-not-fir-quashing',['UAPA-13','IPC-153A'],
        'A lower-court bail-refusal order was quashed and bail granted for prolonged incarceration. The FIR/prosecution was not quashed. Multiple IPC, explosives and UAPA charges are bundled, so delay is not attributed to section 13 alone.',
        [quote(d,2,'Sections 10, 13, 15, 16, 18, 18-A, 18-B, 20 of the Unlawful Act ivities (Prevention) Act, 1967', 'court account of charges'),
         quote(d,6,'released on bail on the ground of prolong incarceration')],
        kind='procedure example',cnr=d['cnr'],verified_charge_laws=['UAPA-13','IPC-153A'])
    d=hc['HCBM010075992025']
    entry('hc-defamation-not-confirmed',['BNS-356'],
        'Metadata lists BNS 356(2). The opening order instead concerns sexual-offence/POCSO and IT charges. This excerpt does not establish a defamation charge; the metadata hit remains unverified, not a negative finding.',
        [quote(d,1,'offences punishable under Sections 64 and 64 (2) (m)', 'court account of charges')],
        kind='unverified metadata hit',cnr=d['cnr'],verified_charge_laws=[])

    # Small examples for the agreed element matrix. Unknown is never converted to missing elements.
    matrices=[
        {'id':'patricia-elements','law':'IPC-153A','origin':'Supreme Court doctrinal example, not High Court rate sample',
         'document_id':'2021 INSC 213','elements':[
            {'element':'expressive act','state':'specific facts recorded','source_type':'court account of allegations','evidence':quote(sc['2021 INSC 213'],11,'Facebook post dated 04.07.2020','court account of allegations')},
            {'element':'intention to promote class/community hatred','state':'court explicitly finds absent','source_type':'court reasoning','evidence':quote(sc['2021 INSC 213'],12,'there was no intention on the part of the Appellant to promote class/community hatred.')},
            {'element':'incitement to community violence','state':'court explicitly finds absent','source_type':'court reasoning','evidence':quote(sc['2021 INSC 213'],12,'there is no attempt ma de by the Appellant to incite people belonging to a community to indulge in any violence')},
         ],'ccd_numeric':None,'note':'Doctrinal elements need expert confirmation; findings remain separate from allegations. No composite distance is produced.'},
        {'id':'farah-elements','law':'BNS-152','origin':'selected HC document','cnr':'HCBM010319502025','elements':[
            {'element':'communication','state':'specific facts recorded','source_type':'court account of allegations','evidence':quote(hc['HCBM010319502025'],2,'A WhatsApp group was created','court account of allegations')},
            {'element':'purpose/knowledge tied to a specified prohibited activity','state':'not assessed in this pilot','source_type':None,'evidence':None},
            {'element':'secession/rebellion/subversive activity or specified danger','state':'not assessed in this pilot','source_type':None,'evidence':None},
         ],'ccd_numeric':None,'note':'A general statement that offences are made out does not resolve every element. No unknown state is counted as an absent element.'},
    ]
    return entries,matrices
