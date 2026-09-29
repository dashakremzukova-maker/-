#!/usr/bin/env node
// Экспорт стайлбука в PDF (страницы 1080×1920).
//
//   node export.js clients/<имя>/client.json
//
// Необязательные флаги:
//   --mode full|short   переопределить режим из client.json
//   --out <файл.pdf>    куда сохранить (по умолчанию рядом с client.json)
//   --html              дополнительно сохранить автономный HTML для просмотра на телефоне

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { parseName, parseMeasurements, figureHint } = require('./lib/shared');

const MAX_BYTES = 15 * 1024 * 1024;
// Ступени сжатия: если PDF больше 15 МБ — пробуем следующую.
const STEPS = [
  { side: 1600, q: 0.82 },
  { side: 1400, q: 0.74 },
  { side: 1200, q: 0.66 },
  { side: 1000, q: 0.58 },
  { side: 850, q: 0.5 },
];
const IMG_RE = /\.(jpe?g|png|webp|gif|bmp|avif|heic|heif)$/i;

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

const jsonPath = process.argv.slice(2).find((a, i, all) => !a.startsWith('--') && !['--mode', '--out'].includes(all[i - 1]));
if (!jsonPath || !fs.existsSync(jsonPath)) {
  console.error('Использование: node export.js clients/<имя>/client.json [--mode short] [--out файл.pdf] [--html]');
  process.exit(1);
}

const client = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const S = client.stylist || {};
const A = client.anketa || {};
const dir = path.dirname(path.resolve(jsonPath));
const photoDir = path.join(dir, 'photos');
const mode = String(arg('--mode') || client.mode || 'FULL').toUpperCase() === 'SHORT' ? 'SHORT' : 'FULL';

// Имя для файла
const name = parseName((S.meta && S.meta.client_name) || A.q1);
const outPath = arg('--out') || path.join(dir, `Натальная_карта_стиля_${name.first || 'клиент'}.pdf`);

// Подсказка по фигуре: обхваты стилиста, иначе ответ на в.14
const meas = Object.fromEntries(Object.entries((S.figure && S.figure.measurements) || {}).filter(([, v]) => String(v).trim() !== ''));
const hint = figureHint(Object.keys(meas).length ? meas : parseMeasurements(A.q14));

// Все имена фото, упомянутые в "stylist"
function collectPhotos(v, acc = new Set()) {
  if (typeof v === 'string') { if (IMG_RE.test(v.trim())) acc.add(v.trim()); }
  else if (Array.isArray(v)) v.forEach((x) => collectPhotos(x, acc));
  else if (v && typeof v === 'object') Object.values(v).forEach((x) => collectPhotos(x, acc));
  return acc;
}
const photoNames = [...collectPhotos(S)];
const missing = photoNames.filter((n) => !fs.existsSync(path.join(photoDir, n)));
const present = photoNames.filter((n) => !missing.includes(n));

const MIME = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', gif: 'image/gif', bmp: 'image/bmp', avif: 'image/avif' };

async function compress(page, step) {
  const out = {};
  for (const n of present) {
    const ext = n.split('.').pop().toLowerCase();
    if (!MIME[ext]) { console.warn(`  ! ${n}: формат ${ext.toUpperCase()} браузер не читает — сохраните фото как JPG`); continue; }
    const b64 = fs.readFileSync(path.join(photoDir, n)).toString('base64');
    try {
      out[n] = await page.evaluate(async ({ url, side, q }) => {
        const blob = await (await fetch(url)).blob();
        const bmp = await createImageBitmap(blob); // учитывает поворот из EXIF
        const k = Math.min(1, side / Math.max(bmp.width, bmp.height));
        const c = document.createElement('canvas');
        c.width = Math.round(bmp.width * k);
        c.height = Math.round(bmp.height * k);
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(bmp, 0, 0, c.width, c.height);
        return c.toDataURL('image/jpeg', q);
      }, { url: `data:${MIME[ext]};base64,${b64}`, side: step.side, q: step.q });
    } catch (e) {
      console.warn(`  ! ${n}: не удалось прочитать файл (${e.message.split('\n')[0]})`);
    }
  }
  return out;
}

function buildHtml(photos, print) {
  const data = {
    client,
    mode,
    photos,
    print,
    derived: { name, figureHint: hint },
  };
  const tpl = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8');
  const json = JSON.stringify(data).replace(/</g, '\\u003c');
  return tpl.replace('/*__DATA__*/null', json);
}

(async () => {
  console.log(`Клиент: ${name.full || '—'} · режим ${mode}`);
  if (hint) console.log(`Подсказка по фигуре (по обхватам): ${hint.text}${S.figure && S.figure.silhouette ? ` · выбрано стилистом: ${S.figure.silhouette}` : ' · поле figure.silhouette пустое — в PDF пойдёт подсказка'}`);
  if (missing.length) console.warn(`Нет файлов в photos/: ${missing.join(', ')} — эти места пропущены.`);

  // Шрифты грузятся из Google Fonts; если в системе задан прокси — используем его.
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch(proxy ? { proxy: { server: proxy } } : {});
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  let size = Infinity;
  let result;
  let photos;
  for (const step of STEPS) {
    await page.goto('about:blank');
    photos = await compress(page, step);
    await page.setContent(buildHtml(photos, true), { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__READY__ === true, null, { timeout: 60000 });
    result = await page.evaluate(() => window.__RESULT__);
    const fontsOk = await page.evaluate(() => document.fonts.check('500 40px "Playfair Display"') && document.fonts.check('40px Manrope'));
    if (!fontsOk) console.warn('  ! Шрифты Google Fonts не загрузились (нет интернета?) — в PDF будут запасные шрифты.');
    await page.emulateMedia({ media: 'print' });
    await page.pdf({ path: outPath, width: '1080px', height: '1920px', printBackground: true, preferCSSPageSize: true });
    size = fs.statSync(outPath).size;
    if (size <= MAX_BYTES) break;
    console.log(`  PDF ${(size / 1048576).toFixed(1)} МБ > 15 МБ — сжимаю фото сильнее…`);
  }

  if (process.argv.includes('--html')) {
    const htmlPath = outPath.replace(/\.pdf$/i, '') + '.html';
    fs.writeFileSync(htmlPath, buildHtml(photos, false));
    console.log(`HTML для телефона: ${path.relative(process.cwd(), htmlPath)}`);
  }
  await browser.close();

  if (result.skipped.length) console.log(`Пропущены пустые страницы: ${result.skipped.join(', ')}`);
  (result.fit || []).forEach((w) => console.warn(`  ! ${w} — сократите текст, чтобы вернуть 100%`));
  console.log(`Страниц: ${result.pages.length} · ${(size / 1048576).toFixed(1)} МБ`);
  console.log(`Готово: ${path.relative(process.cwd(), outPath)}`);
  if (size > MAX_BYTES) { console.error('PDF всё ещё больше 15 МБ — уменьшите количество фото.'); process.exitCode = 2; }
})().catch((e) => { console.error(e); process.exit(1); });
