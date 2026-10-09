import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const folder = 'outputs/bns-training-starter';
const workbook = Workbook.create();
const specs = [
  ['case-candidates', 'BNS case candidates'],
  ['annotation-template', 'First annotation batch'],
];
const exported = [];
for (const [stem, sheetName] of specs) {
  const data = JSON.parse(await fs.readFile(`${folder}/${stem}.json`, 'utf8'));
  const headers = Object.keys(data[0]);
  const sheet = workbook.worksheets.add(sheetName);
  const values = [headers, ...data.map(row => headers.map(header => row[header] ?? null))];
  const range = sheet.getRangeByIndexes(0, 0, values.length, headers.length);
  range.values = values;
  range.format.font = { name: 'Arial', size: 10 };
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = { fill: '#24364B', font: { name: 'Arial', bold: true, color: '#FFFFFF' } };
  exported.push({ stem, sheet, range, count: data.length });
}
const data = JSON.parse(await fs.readFile(`${folder}/case-candidates.json`, 'utf8'));
const previewSheet = workbook.worksheets.add('Preview');
previewSheet.showGridLines = false;
previewSheet.getRange('A1:E9').values = [
  ['CNR proceeding', 'BNS metadata', 'BNS in charge passage', 'Review status', 'Max pages'],
  ...data.slice(0, 8).map(row => [row.cnr, row.metadata_bns_targets, row.text_confirmed_bns_targets,
    row.text_confirmed_bns_targets ? 'AI text check; human pending' : row.review_status, row.maximum_document_pages])
];
previewSheet.getRange('A1:E9').format = { font: { name: 'Arial', size: 11 }, rowHeight: 38 };
previewSheet.getRange('A1:E1').format = { fill: '#24364B', font: { name: 'Arial', bold: true, color: '#FFFFFF' }, rowHeight: 46 };
previewSheet.getRange('A1:A9').format.columnWidth = 27;
previewSheet.getRange('B1:C9').format.columnWidth = 28;
previewSheet.getRange('D1:D9').format.columnWidth = 40;
previewSheet.getRange('E1:E9').format.columnWidth = 14;
workbook.recalculate();
const escape = value => {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
for (const item of exported) {
  const grid = item.range.values;
  assert.equal(grid.length, item.count + 1);
  await fs.writeFile(`${folder}/${item.stem}.csv`, '\uFEFF' + grid.map(row => row.map(escape).join(',')).join('\r\n') + '\r\n');
}
const preview = await workbook.render({sheetName:previewSheet.name,range:'A1:E9',scale:1,format:'png'});
await fs.writeFile(`${folder}/case-preview.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({outputs:exported.map(({stem,count}) => ({file:`${folder}/${stem}.csv`,rows:count})),preview:previewSheet.getRange('A1:E3').values}));
