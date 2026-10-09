"""Normalize saved, user-verified NJDG detail text with source-span evidence."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse(capture):
    text = capture['raw_text']
    evidence = {}

    def field(name, pattern):
        match = re.search(pattern, text)
        if not match:
            return None
        value = match.group(1).strip()
        evidence[name] = {'text': value, 'start': match.start(1), 'end': match.end(1)}
        assert text[match.start(1):match.end(1)].strip() == value
        return value

    def iso_date(value, fmt):
        return datetime.strptime(value, fmt).date().isoformat() if value else None

    cnr_raw = field('cnr_raw', r'CNR Number\s*:\s*([A-Z]{4}\d{2}-\d{6}-\d{4})')
    cnr = cnr_raw.replace('-', '') if cnr_raw else None
    filing_date_raw = field('filing_date', r'Filing Date:\s*(\d{2}-\d{2}-\d{4})')
    registration_date_raw = field('registration_date', r'Registration Date:\s*(\d{2}-\d{2}-\d{4})')
    hearing_date_raw = field('next_date', r'Next Hearing Date\s*:\s*([^\n]+)')
    if hearing_date_raw:
        hearing_date_raw = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', hearing_date_raw)
    stage = field('stage', r'Stage of Case\s*:\s*([^\n]+)')
    act_block = field('act_sections', r'Under Act\(s\)\tUnder Section\(s\)\n([\s\S]*?)\nSubordinate Court Information')
    fir_block = re.search(r'FIR Details\n([\s\S]*?)\nHistory of Case Hearing', text)
    fir_text = fir_block.group(1) if fir_block else ''
    police_match = re.search(r'Police Station:\s*([^\n]+)', fir_text)
    number_match = re.search(r'FIR Number:\s*(\d+)', fir_text)
    year_match = re.search(r'Year:\s*(\d{4})', fir_text)
    for name, match in [('police_station', police_match), ('fir_number', number_match), ('fir_year', year_match)]:
        if match:
            start = fir_block.start(1) + match.start(1)
            end = fir_block.start(1) + match.end(1)
            evidence[name] = {'text': match.group(1).strip(), 'start': start, 'end': end}
    document_urls = [link['href'] for link in capture['links'] if (link.get('href') or '').lower().split('?')[0].endswith('.pdf')]
    return {
        'case_label': capture['case_label'],
        'cnr': cnr, 'cnr_raw': cnr_raw,
        'filing_date': iso_date(filing_date_raw, '%d-%m-%Y'),
        'registration_date': iso_date(registration_date_raw, '%d-%m-%Y'),
        'next_date': iso_date(hearing_date_raw, '%d %B %Y'),
        'case_status': None,
        'stage': stage,
        'purpose': None,
        'act_sections': act_block.replace('\t', ': ') if act_block else None,
        'police_station': police_match.group(1).strip() if police_match else None,
        'fir_number': number_match.group(1) if number_match else None,
        'fir_year': int(year_match.group(1)) if year_match else None,
        'document_urls': document_urls,
        'document_link_observation': 'No judgment/order download link was visible in this inspected detail view.' if not document_urls else 'PDF links observed.',
        'journalist_status': 'unknown',
        'source_url': capture['source_url'],
        'collected_at': capture['collected_at'],
        'source_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'evidence': evidence,
        'notes': 'Dates normalized from the displayed labels. Stage is preserved verbatim. No pending/disposed label, journalist identity, custody status, or law score is inferred.'
    }


if __name__ == '__main__':
    captures = json.loads((ROOT / 'outputs/njdg-raw-details.json').read_text())
    results = [parse(capture) for capture in captures]
    (ROOT / 'outputs/njdg-observed-details.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'details_parsed': len(results), 'cnrs': [r['cnr'] for r in results]}, indent=2))
