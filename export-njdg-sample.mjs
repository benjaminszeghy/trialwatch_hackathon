import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const captured = JSON.parse(await fs.readFile('outputs/njdg-observed-list.json', 'utf8'));
let details = [];
try { details = JSON.parse(await fs.readFile('outputs/njdg-observed-details.json', 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const byCase = new Map(details.map(item => [item.case_label, item]));
const headers = ['sample_row', 'state', 'district', 'court_establishment', 'case_type', 'case_number', 'case_year', 'cnr', 'cnr_raw', 'filing_date', 'registration_date', 'case_status', 'stage', 'purpose', 'next_date', 'act_sections', 'police_station', 'fir_number', 'fir_year', 'document_urls', 'journalist_status', 'source_view', 'collection_date', 'detail_review_status'];
const rows = captured.case_names.map((label, i) => {
  const parts = label.match(/^(.*?) \/ (\d+) \/ (\d{4})$/);
  assert.ok(parts, `Unexpected case label: ${label}`);
  const detail = byCase.get(label) ?? {};
  return [i + 1, captured.state, captured.district, captured.court_establishment,
    parts[1], parts[2], Number(parts[3]), detail.cnr ?? null,
    detail.cnr_raw ?? null, detail.filing_date ?? null,
    detail.registration_date ?? null, detail.case_status ?? null,
    detail.stage ?? null,
    detail.purpose ?? null, detail.next_date ?? null,
    detail.act_sections ?? null, detail.police_station ?? null,
    detail.fir_number ?? null, detail.fir_year ?? null,
    (detail.document_urls ?? []).join(' '),
    'unknown', captured.selection, captured.inspection_date,
    byCase.has(label) ? 'detail inspected' : 'list only; detail not inspected'];
});
assert.equal(rows.length, 25);
const workbook = Workbook.create();
const sheet = workbook.worksheets.add('NJDG sample');
const range = sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length);
range.values = [headers, ...rows];
sheet.showGridLines = false;
range.format.font = { name: 'Arial', size: 10 };
range.format.rowHeight = 24;
sheet.getRangeByIndexes(0, 0, 1, headers.length).format = { fill: '#24364B', font: { name: 'Arial', bold: true, color: '#FFFFFF' } };
sheet.getRange('A1:A26').format.columnWidth = 14;
sheet.getRange('B1:C26').format.columnWidth = 18;
sheet.getRange('D1:D26').format.columnWidth = 45;
sheet.getRange('E1:E26').format.columnWidth = 25;
sheet.getRange('F1:G26').format.columnWidth = 16;
sheet.getRange('G2:G26').setNumberFormat('0');
workbook.recalculate();
const values = range.values;
assert.equal(values.length, 26);
const escape = value => {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
await fs.writeFile('outputs/njdg-pune-case-sample.csv', '\uFEFF' + values.map(row => row.map(escape).join(',')).join('\r\n') + '\r\n');
const preview = await workbook.render({sheetName:sheet.name,range:'A1:G26',scale:1,format:'png'});
await fs.writeFile('/private/tmp/njdg-sample-preview.png', new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({rows:rows.length,inspected_details:details.length,output:'outputs/njdg-pune-case-sample.csv'}));
