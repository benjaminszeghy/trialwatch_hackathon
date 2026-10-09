"""Profile an NJDG CSV exported by the user-facing portal.

Read-only with respect to the source CSV. This script makes no web requests.
It retains original headers/values and does not infer charges or journalist status.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def profile(path, limit=20):
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    # NJDG/DataTables exports may put a report title above the tabular header.
    lines = text.splitlines(keepends=True)
    header_index = next((i for i, line in enumerate(lines)
                         if any('cnr' in cell.lower() for cell in next(csv.reader([line])))), None)
    if header_index is None:
        raise ValueError('No CNR header found. This may be an aggregate report, not a case export.')
    reader = csv.DictReader(lines[header_index:])
    headers = reader.fieldnames
    cnr_column = next(h for h in headers if 'cnr' in h.lower())
    rows = [dict(row) for row in reader if any(value for value in row.values())]
    identifiers = [re.sub(r'\s+', '', row.get(cnr_column, '') or '').upper() for row in rows]
    valid = [bool(re.fullmatch(r'[A-Z]{4}[0-9]{12}', identifier)) for identifier in identifiers]
    frequencies = Counter(identifier for identifier, ok in zip(identifiers, valid) if ok)
    sample = [{ 'cnr': identifier, 'source_row': i + 1, 'raw_fields': row }
              for i, (row, identifier, ok) in enumerate(zip(rows, identifiers, valid)) if ok][:limit]
    return {
        'source_file': path.name,
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'raw_headers': headers,
        'export_row_count': len(rows),
        'valid_cnr_row_count': sum(valid),
        'invalid_cnr_source_rows': [i + 1 for i, ok in enumerate(valid) if not ok],
        'duplicate_cnrs': {key: count for key, count in frequencies.items() if count > 1},
        'populated_by_column': {h: sum(bool((row.get(h) or '').strip()) for row in rows) for h in headers},
        'sample_selection': f'First {limit} rows with valid CNRs in export order. Convenience sample.',
        'sample': sample,
        'interpretation': 'CNR identifies a court proceeding. It does not by itself identify an underlying FIR family. Empty fields remain unknown. No law score or journalist label is assigned.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = profile(args.csv, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'sample'}, ensure_ascii=False, indent=2))
