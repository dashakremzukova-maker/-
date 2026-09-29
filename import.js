#!/usr/bin/env node
// Импорт анкеты из CSV-выгрузки Google-таблицы «Анкета клиента — ответы».
//
//   node import.js answers.csv --row 5
//
// --row — номер строки так, как он виден в Google-таблице (строка 1 — заголовки).
// Создаёт clients/<Имя_Фамилия>/client.json и пустую папку photos/.
// Если client.json уже есть — обновляется только "anketa", выводы стилиста не трогаются.

const fs = require('fs');
const path = require('path');
const { parseName, parseMeasurements, figureHint, parseHours, emptyStylist, merge } = require('./lib/shared');

const QUESTIONS = 37;

function parseCSV(text) {
  text = text.replace(/^﻿/, '');
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function usage(msg) {
  if (msg) console.error(`Ошибка: ${msg}\n`);
  console.error('Использование: node import.js answers.csv --row 5');
  process.exit(1);
}

const args = process.argv.slice(2);
const csvPath = args.find((a) => !a.startsWith('--') && args[args.indexOf(a) - 1] !== '--row');
const rowIdx = args.indexOf('--row');
const rowNum = rowIdx >= 0 ? parseInt(args[rowIdx + 1], 10) : NaN;
if (!csvPath) usage('не указан CSV-файл');
if (!fs.existsSync(csvPath)) usage(`файл не найден: ${csvPath}`);
if (!Number.isInteger(rowNum) || rowNum < 2) usage('укажите --row N (N ≥ 2, строка 1 — заголовки)');

const rows = parseCSV(fs.readFileSync(csvPath, 'utf8'));
const header = rows[0] || [];
const record = rows[rowNum - 1];
if (!record || record.every((c) => !c.trim())) usage(`в таблице нет строки ${rowNum} (всего строк: ${rows.length})`);

// Столбцы, чей заголовок начинается с «N.» → qN
const anketa = {};
for (let q = 1; q <= QUESTIONS; q++) anketa[`q${q}`] = '';
header.forEach((h, i) => {
  const m = String(h).trim().match(/^(\d{1,2})\s*[.)]/);
  if (!m) return;
  const q = +m[1];
  if (q >= 1 && q <= QUESTIONS) anketa[`q${q}`] = String(record[i] ?? '').trim();
});
const found = header.filter((h) => /^\s*\d{1,2}\s*[.)]/.test(h)).length;
if (!found) usage('в заголовках не найдено столбцов вида «1. …», «2. …»');

const name = parseName(anketa.q1);
if (!name.folder) usage('в ответе на вопрос 1 нет имени');

const dir = path.join(__dirname, 'clients', name.folder);
const file = path.join(dir, 'client.json');
fs.mkdirSync(path.join(dir, 'photos'), { recursive: true });

let client;
if (fs.existsSync(file)) {
  client = JSON.parse(fs.readFileSync(file, 'utf8'));
  client.anketa = anketa;
  console.log(`client.json уже был — обновлена только анкета, раздел "stylist" сохранён.`);
} else {
  let stylist = emptyStylist();
  // Постоянные данные стилиста (имя, контакты) — из stylist-profile.json, если он есть.
  const profilePath = path.join(__dirname, 'stylist-profile.json');
  if (fs.existsSync(profilePath)) stylist = merge(stylist, JSON.parse(fs.readFileSync(profilePath, 'utf8')));
  stylist.meta.client_name = name.full;

  // Подсказки, которые стилист проверяет и правит.
  const m = parseMeasurements(anketa.q14);
  Object.assign(stylist.figure.measurements, m);
  const hint = figureHint(m);
  if (hint) stylist.figure.silhouette_hint = hint.text;
  const hours = parseHours(anketa.q9);
  if (hours.length) stylist.lifestyle.spheres = hours;

  client = { mode: 'FULL', anketa, stylist };
}

fs.writeFileSync(file, JSON.stringify(client, null, 2) + '\n');
const filled = Object.values(anketa).filter(Boolean).length;
console.log(`Готово: ${path.relative(process.cwd(), file)}`);
console.log(`Ответов в анкете: ${filled} из ${QUESTIONS}.`);
if (client.stylist.figure?.silhouette_hint) console.log(`Подсказка по фигуре: ${client.stylist.figure.silhouette_hint}`);
console.log(`Фото клиента кладите в ${path.relative(process.cwd(), path.join(dir, 'photos'))}/`);
