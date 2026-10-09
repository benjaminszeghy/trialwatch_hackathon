"""Conservative Act-bound section matching; a metadata hit is not a charge finding."""
import re

TARGETS = {
    'IPC': ['124A', '153A', '295A', '505', '499', '500', '186'],
    'BNS': ['152', '196', '299', '353', '356', '221'],
    'UAPA': ['13'], 'IT': ['66A', '67'], 'OSA': ['3', '5'],
}

def act_family(name):
    name = re.sub(r'[^A-Z0-9 ]', ' ', str(name).upper())
    name = re.sub(r'\s+', ' ', name).strip()
    families = []
    for key, words in {
        'IPC': ['INDIAN PENAL CODE', 'I P C', 'IPC'],
        'BNS': ['BHARATIYA NYAYA SANHITA', 'BNS'],
        'UAPA': ['UNLAWFUL ACTIVIT', 'UAPA'],
        'IT': ['INFORMATION TECHNOLOGY', 'IT ACT'],
        'OSA': ['OFFICIAL SECRETS', 'OFFICIAL SECRET ACT'],
    }.items():
        if any((w in name if w=='UNLAWFUL ACTIVIT' else
                re.search(r'(?<![A-Z0-9])'+re.escape(w)+r'(?![A-Z0-9])',name))
               for w in words): families.append(key)
    return families[0] if len(families) == 1 else None

def normalized_sections(text):
    """153-A/153 A/153(A) -> 153A; 67(b) -> 67B, not section 67."""
    text = str(text).upper()
    text = re.sub(r'(\d)\s*\(\s*([A-Z])\s*\)', r'\1\2', text)
    text = re.sub(r'(\d)\s*[- ]\s*([A-Z])\b', r'\1\2', text)
    return text

def has_section(text, section):
    return bool(re.search(r'(?<![A-Z0-9])' + re.escape(section.upper()) +
                          r'(?![A-Z0-9])', normalized_sections(text)))

def metadata_hits(acts):
    hits = set()
    for row in acts or []:
        if not isinstance(row, dict): continue
        family = act_family(row.get('act', ''))
        if family:
            for section in TARGETS[family]:
                if has_section(row.get('section', ''), section):
                    hits.add(f'{family}:{section}')
    return sorted(hits)
