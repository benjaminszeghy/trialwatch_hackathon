"""Editable, analyst-proposed statutory coding. Not expert labels or learned weights.

Scores describe the linked statutory text, not the law after judicial interpretation.
The deliberately visible explanations make every subjective coding contestable.
"""

CRITERIA = [
    {'id':'speech_reach', 'label':'Reach into expression', 'anchors':[
        'No express publication, words, or communication limb.',
        'Communication limb confined to a defined class of protected official information.',
        'Words, publication, or expressive content are an express route to liability.']},
    {'id':'open_texture', 'label':'Evaluative trigger language', 'anchors':[
        'Concrete conduct and object; no evaluative expression or harm trigger identified.',
        'Evaluative trigger bounded by a specified object, such as reputation, religious insult, or obstruction of official functions.',
        'Open political, group-affective, morality, or national-security terms, including potential harm rather than a specified completed injury.']},
    {'id':'mental_state_gap', 'label':'Explicit mental-state gap', 'anchors':[
        'A specific deliberate/malicious harmful purpose is expressly required in the selected limb.',
        'Knowledge, reason to believe, voluntariness, a purpose presumption, or mixed intent/effect routes; no specific malicious purpose required throughout.',
        'No express mental-state qualifier in the selected expression limb. This is a TEXT feature, not a claim of strict liability.']},
    {'id':'safeguard_gap', 'label':'Express expression-safeguard gap', 'anchors':[
        'Several express criticism/reporting exceptions or a broad public-good/art/learning exception in the linked text.',
        'A conditional lawful-criticism or reasonable-belief/good-faith exception.',
        'No general criticism, reporting, or public-interest exception identified in the selected provision/linked definition.']},
    {'id':'custody', 'label':'Arrest/bail exposure', 'anchors':[
        'Non-cognizable AND bailable under the linked central schedule.',
        'Cognizable OR non-bailable, but not both.',
        'Cognizable AND non-bailable, or a specific statutory anticipatory-bail bar.']},
    {'id':'penalty', 'label':'Maximum imprisonment', 'anchors':[
        'Maximum up to and including two years.',
        'Maximum greater than two and up to seven years.',
        'Maximum greater than seven years, life imprisonment, or death.']},
]

SOURCES = {
    'ipc': {'url':'https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf', 'local':'statutes/ipc.json'},
    'bns': {'url':'https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf', 'local':'statutes/bns.json'},
    'uapa': {'url':'https://www.mha.gov.in/sites/default/files/A1967-37_0.pdf', 'local':'statutes/uapa.json'},
    'osa': {'url':'https://www.mha.gov.in/sites/default/files/2022-10/OSA1923_02092022%5B1%5D.pdf', 'local':'statutes/osa.json'},
    'it': {'url':'https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf', 'local':None, 'access':'Web tool PDF text verified; local download unavailable'},
    'crpc': {'url':'https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf', 'local':'statutes/crpc.json'},
    'bnss': {'url':'https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf', 'local':'statutes/bnss.json'},
    'commencement': {'url':'https://www.mha.gov.in/sites/default/files/BhartiyaNyayaSanhita_24022024.pdf', 'local':None},
}

def ref(source, pages, provisions):
    return {'source':source,'url':SOURCES[source]['url'],'pdf_pages':pages,'provisions':provisions}

def law(identifier, name, era, hits, ratings, reasons, refs, counterpart=None, notes='', max_years=None):
    assert len(ratings)==len(reasons)==len(CRITERIA)
    return {'id':identifier,'name':name,'era':era,'metadata_parent_hits':hits,
        'status':'historical/savings' if era=='IPC' else 'continuing statute' if era=='Other' else 'current BNS baseline',
        'counterpart':counterpart,'max_years':max_years,'notes':notes,
        'coding_status':'AI-assisted analyst proposal; no independent legal coding or outcome validation',
        'components':{c['id']:{'rating':v,'reason':why} for c,v,why in zip(CRITERIA,ratings,reasons)},
        'sources':refs}

ENMITY=[
    'The words/representation limb expressly reaches expressive content.',
    'Disharmony, enmity, hatred, ill-will and likely disturbance are evaluative group/public-order triggers.',
    'Clauses (1)(a)-(b) have no express intent qualifier in the text. Supreme Court mens rea requirements are displayed separately.',
    'No express general public-interest or reporting exception in these clauses; judicial and constitutional safeguards remain relevant.',
    'The central procedural schedule classifies the offence as cognizable and non-bailable.',
    'Three years ordinarily; five for the specified worship setting. Both are in the >2 to 7 band.',
]
RELIGION=[
    'Insult through words or representation is an express route to liability.',
    'The evaluative trigger is bounded by insult to a class\'s religion/religious beliefs.',
    'Deliberate AND malicious intention to outrage religious feelings is expressly required.',
    'No general reporting/public-interest exception identified; the specific mens rea is coded in its own component.',
    'Cognizable and non-bailable in the central schedule.',
    'Maximum three years.',
]
FALSE_STATEMENT=[
    'Making, publishing or circulating a statement, rumour or report is an express route to liability.',
    'Fear/alarm, group enmity, public tranquillity and likelihood formulations are evaluative triggers.',
    'The text contains intent OR likely-effect alternatives; judicial mental-state requirements must be considered separately.',
    'Reasonable grounds for believing truth plus good faith and absence of the specified intent provide a conditional exception.',
    '',
    'Maximum three years in this subsection; the separate worship-setting variant of subsection (2) has five years.',
]
DEFAMATION=[
    'Making/publishing an imputation through words or representation expressly reaches expression.',
    'Reputational harm is evaluative, but Explanation 4 specifies forms of lowered estimation.',
    'Intending harm, knowledge, OR reason to believe are express alternatives.',
    'Ten exceptions include truth PLUS public good, good-faith opinion on public conduct, and substantially true court reports; truth alone is not universal immunity.',
    'The central schedule makes criminal defamation non-cognizable and bailable.',
    'Maximum two years; BNS also permits community service.',
]
OBSTRUCTION=[
    'No independent words/publication limb; prosecution requires obstruction of official functions.',
    'Obstruction is evaluative, but tied to a public servant discharging public functions.',
    'Voluntarily is an express qualifier, not a specific malicious-expression purpose.',
    'No general reporting/public-interest exception in this provision. Complaint/cognizance gates are additional safeguards outside this component.',
    'Non-cognizable and bailable under the central schedule.',
    'Maximum three months.',
]

LAWS=[
 law('IPC-124A','IPC 124A — sedition (historical; 2022 abeyance order)','IPC',['IPC:124A'],[2,2,2,1,2,2],[
    'Words, signs and representations are expressly covered.',
    'Hatred, contempt and disaffection against the government are broad affective/political triggers.',
    'No express mental-state qualifier in the operative textual trigger; Kedar Nath judicial limitations are separate.',
    'Explanations protect disapprobation seeking lawful alteration without the specified prohibited effects.',
    'CrPC central schedule: cognizable and non-bailable.',
    'Maximum life imprisonment.'],
    [ref('ipc',[55,56],'124A'),ref('crpc',[198],'First Schedule: 124A')],
    'BNS-152','Historical text only. The 11 May 2022 Supreme Court order kept 124A proceedings in abeyance and restrained fresh use; this is not an active offence recommendation. BNS 152 is a related provision with different wording, not a one-to-one renumbering.', 'life'),
 law('IPC-153A','IPC 153A(1)(a)-(b) — promoting enmity','IPC',['IPC:153A'],[2,2,2,2,2,1],ENMITY,
    [ref('ipc',[66,67],'153A'),ref('crpc',[199],'First Schedule: 153A')],'BNS-196',
    'Expression/maintenance-of-harmony clauses only; drill/force clause (c) is outside the selected textual lens. Supreme Court intent/context safeguards are material.',5),
 law('IPC-295A','IPC 295A — deliberate malicious religious insult','IPC',['IPC:295A'],[2,1,0,2,2,1],RELIGION,
    [ref('ipc',[130],'295A'),ref('crpc',[210],'First Schedule: 295A')],'BNS-299',max_years=3),
 law('IPC-505-1','IPC 505(1) — statements conducing to public mischief','IPC',['IPC:505'],[2,2,1,1,1,1],
    FALSE_STATEMENT[:4]+['Non-cognizable but non-bailable under the central schedule.']+FALSE_STATEMENT[5:],
    [ref('ipc',[223,224],'505(1), exception'),ref('crpc',[223],'First Schedule: 505 first row')],
    'BNS-353-1','Metadata often records only 505; that does not identify this subsection. State amendments are not coded in this pilot.',3),
 law('IPC-505-2','IPC 505(2) — enmity from false/rumour reports','IPC',['IPC:505'],[2,2,1,1,2,1],
    FALSE_STATEMENT[:4]+['Cognizable and non-bailable under the central schedule.']+FALSE_STATEMENT[5:],
    [ref('ipc',[224],'505(2)-(3), exception'),ref('crpc',[223],'First Schedule: 505 second row')],
    'BNS-353-2','The same parent metadata denominator as 505(1) is displayed, not an independently confirmed subsection count.',5),
 law('IPC-499-500','IPC 499/500 — criminal defamation','IPC',['IPC:499','IPC:500'],[2,1,1,0,0,0],DEFAMATION,
    [ref('ipc',[218,219,220,221],'499 exceptions and 500'),ref('crpc',[222],'First Schedule: 500')],
    'BNS-356','Definition (499) and punishment (500) form one row. Metadata counts use the UNION of CNR records, avoiding double counting.',2),
 law('IPC-186','IPC 186 — obstructing public functions','IPC',['IPC:186'],[0,1,1,2,0,0],OBSTRUCTION,
    [ref('ipc',[83],'186'),ref('crpc',[201,202],'First Schedule: 186')],'BNS-221',
    'CrPC 195 complaint gate should also be reviewed. A lower textual score does not rule out retaliatory application or charge bundling.',0.25),
 law('BNS-152','BNS 152 — sovereignty, unity and integrity','BNS',['BNS:152'],[2,2,1,1,2,2],[
    'Words, signs, visible representation and electronic communication are expressly covered, along with other conduct.',
    'Subversive activities, separatist feelings and endangering unity/integrity have evaluative breadth.',
    'Purposely OR knowingly is explicit; it is stronger textual specification than IPC 124A, but not a malicious-purpose-only threshold.',
    'Explanation protects lawful-change criticism without exciting the specified activities.',
    'BNSS schedule: cognizable and non-bailable.',
    'Maximum life imprisonment; alternative fixed term up to seven years.'],
    [ref('bns',[60],'152'),ref('bnss',[168],'First Schedule: 152')],
    'IPC-124A','BNS baseline commenced 1 July 2024. Related subject matter to 124A, but different prohibited conduct, fault words and fixed-term alternative.', 'life'),
 law('BNS-196','BNS 196(1)(a)-(b) — promoting enmity','BNS',['BNS:196'],[2,2,2,2,2,1],ENMITY,
    [ref('bns',[68],'196'),ref('bnss',[171,172],'First Schedule: 196')],'IPC-153A',
    'Explicit electronic-communication wording. Current Supreme Court safeguards in Imran Pratapgadhi (2025) are separately recorded; identical index components do not imply identical law.',5),
 law('BNS-299','BNS 299 — deliberate malicious religious insult','BNS',['BNS:299'],[2,1,0,2,2,1],RELIGION,
    [ref('bns',[87],'299'),ref('bnss',[181],'First Schedule: 299')],'IPC-295A',
    'Explicit electronic-means wording. Judicial construction must be checked independently from the IPC mapping.',3),
 law('BNS-353-1','BNS 353(1) — statements conducing to public mischief','BNS',['BNS:353'],[2,2,1,1,1,1],
    FALSE_STATEMENT[:4]+['Non-cognizable but non-bailable under the BNSS schedule.']+FALSE_STATEMENT[5:],
    [ref('bns',[107],'353(1), exception'),ref('bnss',[188],'First Schedule: 353(1)')],
    'IPC-505-1','The text expressly adds false information and electronic means; parent metadata does not resolve the subsection.',3),
 law('BNS-353-2','BNS 353(2) — enmity from false/rumour reports','BNS',['BNS:353'],[2,2,1,1,2,1],
    FALSE_STATEMENT[:4]+['Cognizable and non-bailable under the BNSS schedule.']+FALSE_STATEMENT[5:],
    [ref('bns',[107],'353(2)-(3), exception'),ref('bnss',[188],'First Schedule: 353(2)')],
    'IPC-505-2','Parent metadata overlap is retained explicitly. No IPC-to-BNS frequency trend is inferred.',5),
 law('BNS-356','BNS 356(1)-(2) — criminal defamation','BNS',['BNS:356'],[2,1,1,0,0,0],DEFAMATION,
    [ref('bns',[108,109,110],'356 definition, exceptions, punishment'),ref('bnss',[188],'First Schedule: 356(2)')],
    'IPC-499-500','The score is for the definition and direct defamation offence; printing/selling variants are not separately rated. Community service is available.',2),
 law('BNS-221','BNS 221 — obstructing public functions','BNS',['BNS:221'],[0,1,1,2,0,0],OBSTRUCTION,
    [ref('bns',[73],'221'),ref('bnss',[174],'First Schedule: 221')],'IPC-186',
    'Fine increases to INR 2,500 in the linked text; the six-criterion rubric does not measure fines. BNSS 215 complaint gate is outside the six components.',0.25),
 law('UAPA-13','UAPA 13 with 2(o) — unlawful activities','Other',['UAPA:13'],[2,2,1,2,2,1],[
    'Definition expressly includes spoken/written words; section 13 includes advocacy/advice/incitement.',
    'Disaffection, questioning sovereignty, and supporting secession claims are broad political triggers.',
    'Definition has mixed intention/support/effect routes; this textual coding does not displace judicial fault requirements.',
    'Section 13(3) excludes authorized treaty/negotiation activity, not general journalism or public-interest speech.',
    'Cognizable; seven-year limb is non-bailable under the other-laws schedule; 43D(4) excludes anticipatory bail. 43D(5) is NOT applicable to section 13 alone.',
    'Section 13(1) maximum seven years; subsection (2) five.'],
    [ref('uapa',[6,10,11,20,21],'2(o), 13, 14, 43D(4)-(5)'),ref('crpc',[223],'First Schedule II')],
    notes='Do not import the Chapters IV/VI prima-facie-true bail embargo into section 13 alone. Bundled terrorism charges create distinct exposure.',max_years=7),
 law('IT-67','IT Act 67 — electronic obscenity (first conviction)','Other',['IT:67'],[2,2,2,0,1,1],[
    'Electronic publishing/transmission is an express route to liability.',
    'Lascivious/prurient/deprave-or-corrupt formulations are evaluative morality triggers.',
    'No express fault word in section 67\'s operative text; this does not assert that courts dispense with mens rea.',
    'The proviso following 67B expressly extends public-good/science/literature/art/learning and heritage/religious exceptions to section 67.',
    '77B: a three-year offence is cognizable and bailable. Subsequent-conviction five-year exposure is a different scenario.',
    'First conviction maximum three years; subsequent conviction five years (same penalty band but different custody component).'],
    [ref('it',[25,26,30],'67; proviso after 67B; 77B')],
    notes='First-conviction baseline. Repeated-conviction scenario would change custody from 1 to 2, increasing the total by one point. 67A/67B are separate offences and excluded from metadata matching.',max_years=3),
 law('OSA-3','Official Secrets Act 3 — defence/code publication branch','Other',['OSA:3'],[1,2,1,2,2,2],[
    'Publication/communication concerns a specified class of protected official/security information.',
    'Useful to an enemy, prejudicial purpose, and security/integrity/friendly-relations terms are broad evaluative triggers.',
    'Prejudicial purpose is required, but subsection (2) permits purpose inferences/presumptions from circumstances/conduct/known character.',
    'No general journalism/public-interest publication defence in this section; lawful authority is a separate limitation.',
    'Three/fourteen-year alternatives are cognizable and non-bailable under the central other-laws classification.',
    'Maximum fourteen years for specified defence/code cases; three in other cases.'],
    [ref('osa',[3,4],'3(1)(c), 3(2)'),ref('crpc',[223],'First Schedule II'),ref('bnss',[189],'First Schedule II')],
    notes='This row explicitly rates the fourteen-year defence/code branch in the information/publication lens; physical-entry conduct is not independently scored. The other-case three-year branch has penalty rating 1, a separate 9/12 (75/100) scenario.',max_years=14),
 law('OSA-5','Official Secrets Act 5 — wrongful communication','Other',['OSA:5'],[1,2,1,2,2,1],[
    'Communication/receipt is limited to the specified official/confidential/security information categories.',
    'Protected-information categories extend to entrusted information and potential security/foreign-relations harm.',
    'Mixed wilful/knowing/reason-to-believe routes and reasonable-care or retention limbs require separate conduct-level review.',
    'Authorized communication, a court, or state-interest duty is recognized, but no general public-interest journalism defence is identified.',
    'Three-year maximum is cognizable and non-bailable in the central other-laws schedule.',
    'Maximum three years under subsection (4).'],
    [ref('osa',[5,6],'5(1)-(4)'),ref('crpc',[223],'First Schedule II'),ref('bnss',[189],'First Schedule II')],
    notes='Communication, retention, receipt and care limbs differ. A whole-section profile cannot decide whether any particular reporter satisfies an offence.',max_years=3),
]

next(r for r in LAWS if r['id']=='OSA-3')['alternative_scenarios']=[{
    'name':'Other-case publication branch (not the specified defence/code branch)',
    'component_overrides':{'penalty':1},
    'note':'Three-year maximum; custody remains cognizable/non-bailable under the other-laws schedule.'}]
next(r for r in LAWS if r['id']=='IT-67')['alternative_scenarios']=[{
    'name':'Subsequent conviction', 'component_overrides':{'custody':2},
    'note':'Five-year maximum remains in penalty band 1; the three-year bailability override does not cover this scenario.'}]

INVALID = {'id':'IT-66A','name':'IT Act 66A — offensive messages',
    'era':'Invalid','status':'struck down in entirety, 24 March 2015',
    'metadata_parent_hits':['IT:66A'],'score_100':None,'raw_total':None,
    'notes':'Exclude from active scoring. A metadata listing is a verification lead, not proof of a fresh or unlawful charge. See Shreya Singhal, para 119(a).',
    'components':{},'sources':[ref('it',[24],'66A footnote')],
    'coding_status':'Legal-status flag; not assigned a structural score'}
