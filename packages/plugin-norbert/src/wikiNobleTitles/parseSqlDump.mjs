import fs from 'node:fs';

/**
 * Minimal mysqldump INSERT-statement parser, local to this package.
 *
 * The sibling `authoritypacks` repo ships a fuller `parseSqlDump.mjs` that
 * `matchWikiNorbert.mjs` imports for the wiki-review pipeline, but that repo
 * is not always checked out alongside `plugins` (e.g. release builds run
 * standalone). This module covers the one thing the canonical `person_nt`
 * export needs — reading a single table's `INSERT INTO ... VALUES (...);`
 * statement — without depending on that sibling checkout.
 */

/** Extracts the raw "(...),(...),..." tuple-list text of one table's INSERT statement. */
export function extractInsertValuesText(sqlText, tableName) {
  const marker = `INSERT INTO \`${tableName}\` VALUES `;
  const start = sqlText.indexOf(marker);
  if (start === -1) return null;
  const valuesStart = start + marker.length;
  let depth = 0;
  let inString = false;
  let i = valuesStart;
  for (; i < sqlText.length; i++) {
    const c = sqlText[i];
    if (inString) {
      if (c === '\\') { i++; continue; }
      if (c === "'") inString = false;
      continue;
    }
    if (c === "'") { inString = true; continue; }
    else if (c === '(') depth++;
    else if (c === ')') depth--;
    else if (c === ';' && depth === 0) break;
  }
  return sqlText.slice(valuesStart, i);
}

/** Splits a "(...),(...),..." tuple-list string into raw per-tuple content strings. */
export function splitTuples(valuesText) {
  const tuples = [];
  let depth = 0;
  let inString = false;
  let cur = '';
  for (let i = 0; i < valuesText.length; i++) {
    const c = valuesText[i];
    if (inString) {
      cur += c;
      if (c === '\\') { i++; cur += valuesText[i] ?? ''; continue; }
      if (c === "'") inString = false;
      continue;
    }
    if (c === "'") { inString = true; cur += c; continue; }
    if (c === '(') {
      depth++;
      if (depth === 1) { cur = ''; continue; }
    }
    if (c === ')') {
      depth--;
      if (depth === 0) { tuples.push(cur); continue; }
    }
    if (depth >= 1) cur += c;
  }
  return tuples;
}

function unescapeMysqlString(raw) {
  const inner = raw.slice(1, -1);
  let out = '';
  for (let i = 0; i < inner.length; i++) {
    const c = inner[i];
    if (c === '\\') {
      const next = inner[i + 1];
      i++;
      switch (next) {
        case 'n': out += '\n'; break;
        case 't': out += '\t'; break;
        case 'r': out += '\r'; break;
        case '0': out += '\0'; break;
        case '\\': out += '\\'; break;
        case "'": out += "'"; break;
        case '"': out += '"'; break;
        default: out += next ?? '';
      }
      continue;
    }
    out += c;
  }
  return out;
}

function coerceField(raw) {
  const trimmed = raw.trim();
  if (trimmed === 'NULL') return null;
  if (trimmed.startsWith("'") && trimmed.endsWith("'")) return unescapeMysqlString(trimmed);
  if (trimmed.startsWith('_binary ')) return trimmed.slice('_binary '.length);
  if (/^-?\d+$/.test(trimmed)) return Number(trimmed);
  if (/^-?\d+\.\d+$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}

/** Splits one tuple's raw contents into fields (top-level commas only), then coerces types. */
export function parseTupleFields(tupleText) {
  const fields = [];
  let depth = 0;
  let inString = false;
  let cur = '';
  for (let i = 0; i < tupleText.length; i++) {
    const c = tupleText[i];
    if (inString) {
      if (c === '\\') { cur += c + (tupleText[i + 1] ?? ''); i++; continue; }
      if (c === "'") { inString = false; cur += c; continue; }
      cur += c;
      continue;
    }
    if (c === "'") { inString = true; cur += c; continue; }
    if (c === '(') depth++;
    if (c === ')') depth--;
    if (c === ',' && depth === 0) { fields.push(cur); cur = ''; continue; }
    cur += c;
  }
  fields.push(cur);
  return fields.map(coerceField);
}

/** Loads every row of one table from a mysqldump `.sql` file as an array of field arrays. */
export function loadTableRows(sqlPath, tableName) {
  const sqlText = fs.readFileSync(sqlPath, 'utf8');
  const valuesText = extractInsertValuesText(sqlText, tableName);
  if (valuesText == null) return [];
  return splitTuples(valuesText).map(parseTupleFields);
}
