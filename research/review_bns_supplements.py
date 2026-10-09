"""Independent text checks of the official candidates Claude identified."""
import json, re
from data_access import ROOT

DIR = ROOT / 'outputs' / 'bns-training-starter' / 'supplements'
CHECKS = [
    ('imran-pratapgarhi-2025', 40, 'mens rea will have to be read into Section 196 of the BNS',
     'court interpretation', ['196'], 'Interpretation benchmark; keep judicial reasoning separate from allegations.'),
    ('pawan-khera-2026', 2,
     'under Sections 175, 3(5), 3(6), 318, 336(4), 337, 338, 340, 341(1), 351(1), 352, 353, 356, and 61(2) of Bharatiya Nyaya Sanhita, 2023',
     'court account of FIR charges', ['353', '356'], 'FIR 04/2026, Crime Branch Police Station, Guwahati; politician speaking at press conferences, not presumed journalist.'),
    ('ranveer-allahbadia-2025', 1,
     'FIR No. 5 of 2025 registered under Sections 79, 196, 296, 299 of the Bharatiya Nyaya Sanhita, 2023',
     'court account of FIR charges in interim order', ['196', '299'], 'Thane FIR 5/2025; Guwahati FIR 3/2025 is another FIR connected to the same episode. Do not treat all proceedings as independent train/test observations.'),
    ('ruchika-mitra-2026', 1,
     'offence s under Sections 126(2)/61(2)/356(2)/351(2)/3(5) of Bharatiya Nyaya Sanhita (BNS), 2023',
     'court account of FIR charges', ['356(2)'], 'Maurya Enclave FIR 224/2025; private school dispute. Private nature is not automatically absence of expression or absence of abuse.'),
    ('vombatkere-bns-152-challenge-2025', 1,
     'declaring Section 152 of the Bharatiya Nyaya Sanhita, 2023 as void and inoperative',
     'office report recording relief sought', [], 'Constitutional challenge; this is a requested declaration, not a ruling striking down BNS 152 and not a personal charge case.'),
    ('ashish-dave-2026', 2,
     'under Sections 308(2), 318(4) and 351(2) of the Bharatiya Nyaya Sanhita, 2023',
     'court account of FIR charges', [], 'BNS case outside the six targets; court describes a Channel Head. Useful for examining the limits of a speech-section-only retrieval strategy.')
]

def main():
    manifest = {r['document_id']: r for r in json.loads((DIR / 'manifest.json').read_text())}
    results = []
    for id, page, query, role, targets, note in CHECKS:
        pages = json.loads((DIR / (id + '.pages.json')).read_text())
        text = next(p['text'] for p in pages if p['page'] == page)
        normalized = re.sub(r'\s+', ' ', text).strip()
        start = normalized.find(query)
        assert start >= 0, (id, page, query)
        results.append({'document_id': id, 'source_url': manifest[id]['source_url'],
            'pdf_sha256': manifest[id]['pdf_sha256'], 'page': page, 'quote': query,
            'normalized_char_start': start, 'normalized_char_end': start + len(query),
            'source_type': role, 'text_confirmed_target_sections': targets,
            'note': note, 'review_status': 'Codex text check of Claude candidate; human/legal validation pending',
            'human_gold_label': None, 'in_bombay_denominator': False})
    (DIR / 'reviewed-evidence.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print('Checked', len(results), 'official documents; 3 additional target-charge documents, 1 interpretation reference, 2 other references.')

if __name__ == '__main__': main()
