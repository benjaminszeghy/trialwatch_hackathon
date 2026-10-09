import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const source = JSON.parse(await fs.readFile('outputs/law-scores.json', 'utf8'));
const headers = ['law_id', 'law', 'version_group', 'score_100', 'raw_score_12', 'legal_status', 'alternative_scenarios', 'notes', 'as_of'];
const rows = source.laws.map(law => [
  law.id,
  law.name,
  law.era,
  law.score_100 ?? null,
  law.raw_total ?? null,
  law.status,
  (law.alternative_scenarios ?? []).map(scenario => `${scenario.name}: ${scenario.score_100}/100. ${scenario.note ?? ''}`).join(' '),
  law.notes ?? '',
  source.as_of,
]);

const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Law scores');
const grid = sheet.getRange(`A1:I${rows.length + 1}`);
grid.values = [headers, ...rows];
sheet.showGridLines = false;
grid.format.font = { name: 'Arial', size: 10 };
grid.format.rowHeight = 24;
sheet.getRange('A1:I1').format = { fill: '#24364B', font: { name: 'Arial', bold: true, color: '#FFFFFF' } };
sheet.getRange(`D2:E${rows.length + 1}`).setNumberFormat('0');
sheet.getRange('A1:A20').format.columnWidth = 18;
sheet.getRange('B1:B20').format.columnWidth = 85;
sheet.getRange('C1:C20').format.columnWidth = 18;
sheet.getRange('D1:E20').format.columnWidth = 18;
workbook.recalculate();

const values = grid.values;
assert.equal(values.length, source.laws.length + 1);
for (let i = 0; i < source.laws.length; i++) {
  assert.equal(values[i + 1][0], source.laws[i].id);
  assert.equal(values[i + 1][3], source.laws[i].score_100 ?? null);
  assert.equal(values[i + 1][4], source.laws[i].raw_total ?? null);
}
assert.equal(values.find(row => row[0] === 'IT-66A')[3], null);

console.log((await workbook.inspect({ kind: 'region', sheetId: sheet.name, range: 'A1:E5', maxChars: 1800, tableMaxRows: 5, tableMaxCols: 5 })).ndjson);
const preview = await workbook.render({ sheetName: sheet.name, range: 'A1:E20', scale: 1, format: 'png' });
await fs.writeFile('/private/tmp/law-scores-csv-preview.png', new Uint8Array(await preview.arrayBuffer()));

const escapeField = value => {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csv = '\uFEFF' + values.map(row => row.map(escapeField).join(',')).join('\r\n') + '\r\n';
await fs.writeFile('outputs/law-scores.csv', csv, 'utf8');
console.log(JSON.stringify({ path: 'outputs/law-scores.csv', law_rows: rows.length, scored_rows: rows.filter(row => row[3] !== null).length, bytes: Buffer.byteLength(csv) }));
