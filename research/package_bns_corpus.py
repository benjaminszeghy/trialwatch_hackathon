"""Package annotation files, PDFs and a reproducible acquisition snapshot."""
from data_access import ROOT, CACHE
from pathlib import Path
import json, shutil, zipfile, hashlib

OUT = ROOT / 'outputs' / 'bns-training-starter'

def main():
    docs = json.loads((OUT / 'acquisition-manifest.json').read_text())
    pdfdir = OUT / 'pdfs'
    pdfdir.mkdir(exist_ok=True)
    for d in docs:
        if d['retrieval_status'] == 'success':
            dst = pdfdir / (d['document_id'] + '.pdf')
            shutil.copyfile(ROOT / d['pdf_path'], dst)
            assert hashlib.sha256(dst.read_bytes()).hexdigest() == d['pdf_sha256']
    bundle = ROOT / 'outputs' / 'bns-training-starter.zip'
    written = set()
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        def add(path, archive_path):
            if archive_path not in written:
                z.write(path, archive_path)
                written.add(archive_path)
        for path in sorted(OUT.rglob('*')):
            if path.is_file(): add(path, path.relative_to(OUT).as_posix())
        code = ['data_access.py', 'acquire_bns.py', 'bns_review_seeds.py', 'build_bns_corpus.py',
                'acquire_bns_supplements.py', 'review_bns_supplements.py', 'test_bns_corpus.py', 'requirements.txt']
        for name in code: add(ROOT / 'research' / name, 'pipeline/research/' + name)
        # Keep the original project-relative paths under pipeline so the Python
        # builder and tests can run without network requests.
        frame = ROOT / 'work' / 'bns-corpus' / 'retrieval_frame.json'
        add(frame, 'pipeline/work/court-data/hc_sampling_frame.json')
        for name in ['documents.json', 'retrieval_frame.json', 'acquisition_summary.json']:
            add(ROOT / 'work' / 'bns-corpus' / name, 'pipeline/work/bns-corpus/' + name)
        for d in docs:
            add(ROOT / d['pdf_path'], 'pipeline/' + d['pdf_path'])
            add(ROOT / d['pages_path'], 'pipeline/' + d['pages_path'])
        metadata = sorted((CACHE / 'indian-high-court-judgments' / 'metadata' / 'parquet').glob('year=*/court=27_1/bench=*/metadata-mobile.parquet'))
        for path in metadata:
            if any('year=' + str(y) in str(path) for y in [2024, 2025]):
                add(path, 'pipeline/' + path.relative_to(ROOT).as_posix())
        for name in ['case-candidates.csv', 'annotation-template.csv']:
            add(OUT / name, 'pipeline/outputs/bns-training-starter/' + name)
        guide = '''# Runnable Python snapshot\n\nFrom this `pipeline` directory, install the pinned Python requirements in your own environment if needed. The acquisition inputs are a fixed Bombay metadata snapshot, not a fresh all-India mirror.\n\n```sh\npython3 research/build_bns_corpus.py\npython3 -m unittest discover -s research -p test_bns_corpus.py -v\n```\n\nThese two commands read the included PDFs and page-text snapshot and require no network. The builder writes new JSON/JSONL outputs into `outputs/bns-training-starter`. The included CSVs were exported from the same build in the original workspace; the Python tests check the CSV structure and blank human fields.\n\n`research/acquire_bns.py` replays acquisition from the included fixed metadata frame. Existing PDFs are cached. A new/download-missing run needs public HTTPS access, uses two concurrent workers, and performs no CAPTCHA solving. `acquire_bns_supplements.py` handles separately labeled official-source references. Metadata and outcome counts are not trained abuse labels.\n'''
        z.writestr('pipeline/README.md', guide)
    with zipfile.ZipFile(bundle) as z:
        assert z.testzip() is None
        assert len([name for name in z.namelist() if name.startswith('pdfs/') and name.endswith('.pdf')]) == 177
        assert 'annotation-template.csv' in z.namelist()
        assert 'supplements/reviewed-evidence.json' in z.namelist()
    print(json.dumps({'archive': str(bundle), 'bytes': bundle.stat().st_size,
                      'hc_pdf_files': 177, 'hc_unique_pdf_hashes': 174, 'official_supplements': 6}))

if __name__ == '__main__': main()
