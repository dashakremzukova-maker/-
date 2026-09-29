// Общие функции для import.js и export.js.

// ---------- Имя клиента ----------

// «Анна Морозова, 34» → { full: "Анна Морозова", first: "Анна", folder: "Анна_Морозова" }
function parseName(q1) {
  const raw = String(q1 || '').split(/[,;\n(]|\d/)[0].trim();
  const words = raw.split(/\s+/).filter(Boolean).slice(0, 3);
  const full = words.join(' ');
  return {
    full,
    first: words[0] || '',
    folder: words.join('_').replace(/[\\/:*?"<>|]/g, '') || '',
  };
}

// ---------- Обхваты и тип фигуры ----------

function num(s) {
  const n = parseFloat(String(s).replace(',', '.'));
  return Number.isFinite(n) ? n : null;
}

// Ответ на в.14 в свободной форме: «грудь 92, талия 70, бёдра 98» или «92-70-98».
function parseMeasurements(text) {
  const t = String(text || '').toLowerCase().replace(/ё/g, 'е');
  if (!t.trim()) return {};
  const pick = (re) => {
    const m = t.match(re);
    return m ? num(m[1]) : null;
  };
  const res = {
    shoulders: pick(/плеч\D{0,12}(\d+(?:[.,]\d+)?)/),
    bust: pick(/груд\D{0,12}(\d+(?:[.,]\d+)?)/),
    waist: pick(/тали\D{0,12}(\d+(?:[.,]\d+)?)/),
    hips: pick(/бедр\D{0,12}(\d+(?:[.,]\d+)?)/),
  };
  if (res.bust == null && res.waist == null && res.hips == null) {
    const nums = (t.match(/\d+(?:[.,]\d+)?/g) || []).map(num).filter((n) => n >= 40 && n <= 200);
    if (nums.length >= 3) [res.bust, res.waist, res.hips] = nums;
  }
  for (const k of Object.keys(res)) if (res[k] == null) delete res[k];
  return res;
}

const SILHOUETTES = {
  X: 'песочные часы',
  A: 'груша',
  H: 'прямоугольник',
  Y: 'перевёрнутый треугольник',
  O: 'яблоко',
};

// Подсказка по обхватам (правило из ТЗ):
// — верх (плечи, если есть, иначе грудь) и бёдра отличаются больше чем на 5 % → Y или A;
// — верх и бёдра в пределах 5 %, талия уже бёдер на 25 % и больше → X;
// — талия почти не отличается от груди/бёдер (≥ 95 % меньшего) → O;
// — остальное → H.
function figureHint(m) {
  if (!m) return null;
  const upper = num(m.shoulders) || num(m.bust);
  const hips = num(m.hips);
  const waist = num(m.waist);
  if (!upper || !hips) return null;
  const diff = (upper - hips) / hips;
  let type;
  if (waist && waist >= 0.95 * Math.min(upper, hips)) type = 'O';
  else if (diff > 0.05) type = 'Y';
  else if (diff < -0.05) type = 'A';
  else if (waist && waist <= hips * 0.75) type = 'X';
  else type = 'H';
  const parts = [
    m.shoulders && `плечи ${m.shoulders}`,
    m.bust && `грудь ${m.bust}`,
    m.waist && `талия ${m.waist}`,
    m.hips && `бёдра ${m.hips}`,
  ].filter(Boolean);
  return { type, name: SILHOUETTES[type], text: `${type} — ${SILHOUETTES[type]} (${parts.join(' / ')})` };
}

// ---------- Часы по сферам (в.9) ----------

// «работа — 45, дом и семья 20 ч; спорт: 4» → [{name:"Работа", hours:45}, …]
function parseHours(text) {
  const out = [];
  for (const seg of String(text || '').split(/[,;\n]+/)) {
    const m = seg.match(/(\d+(?:[.,]\d+)?)/);
    if (!m) continue;
    const name = seg
      .replace(m[0], '')
      .replace(/\b(ч|час(а|ов)?|ч\.)\b/gi, '')
      .replace(/[—–\-:=~≈]/g, ' ')
      .replace(/(в неделю|в нед\.?|\/нед\.?|около|примерно)/gi, '')
      .replace(/\s+/g, ' ')
      .trim();
    const hours = num(m[1]);
    if (name && hours > 0) out.push({ name: name[0].toUpperCase() + name.slice(1), hours });
  }
  return out;
}

// ---------- Пустая заготовка раздела "stylist" ----------

function emptyStylist() {
  return {
    meta: { client_name: '', date: '', stylist_name: '', cover_photo: '' },
    request: { goal: '', success: '', plans: '' },
    lifestyle: {
      spheres: [{ name: '', hours: '' }],
      events: [{ date: '', title: '' }],
      wardrobe_for: '',
    },
    typage: { name: '', yin_yang: '', keywords: ['', '', ''], lines: ['', '', ''], photos: [''] },
    color: {
      type_name: '',
      temperature: '',
      contrast: '',
      chroma: '',
      face_photo: '',
      face: [{ name: '', hex: '' }],
      base: [{ name: '', hex: '' }],
      accents: [{ name: '', hex: '' }],
      metal: '',
      schemes: [{ type: '', colors: [''], text: '', photo: '' }],
    },
    figure: {
      silhouette: '',
      silhouette_hint: '',
      measurements: { shoulders: '', bust: '', waist: '', hips: '' },
      height: '',
      build: '',
      accent: '',
      lengths: { skirt: '', trousers: '', coat: '', sleeve: '' },
      open_closed: '',
      techniques: [{ title: '', text: '', photo: '' }],
      photo: '',
    },
    inner_code: {
      archetype_main: { name: '', text: '' },
      archetype_second: { name: '', text: '' },
      psychotype: { name: '', values: '', avoids: '', comfort: '' },
    },
    style: { main: '', accent: '', formula: '', adjectives: ['', '', ''], moodboard: [''] },
    wardrobe: {
      base_pct: '',
      accent_pct: '',
      rule: '',
      shoes: [''],
      outerwear: [''],
      bags: [''],
      capsule: { title: '', items: [''], photos: [''] },
    },
    looks: [{ sphere: '', title: '', why: '', photos: [''] }],
    details: { accessories: '', jewelry: '', prints: '', textures: '', photos: [''] },
    not_yours: [{ instead: '', try: '' }],
    hair_makeup: { haircut: '', hair_color: '', makeup: '', photo: '' },
    shopping: {
      checklist: ['', '', '', '', ''],
      first: [''],
      later: [''],
      optional: [''],
      budget: '',
      where: [''],
    },
    cheatsheet: { rules: [''], swatches: [''], looks: [''] },
    final: { next_step: '', message: '', contacts: [{ label: '', value: '' }] },
  };
}

// Глубокое слияние: значения из src поверх заготовки (для профиля стилиста).
function merge(base, src) {
  if (Array.isArray(base) || Array.isArray(src)) return src !== undefined ? src : base;
  if (base && typeof base === 'object' && src && typeof src === 'object') {
    const out = { ...base };
    for (const k of Object.keys(src)) out[k] = merge(base[k], src[k]);
    return out;
  }
  return src !== undefined && src !== '' ? src : base;
}

module.exports = { parseName, parseMeasurements, figureHint, parseHours, emptyStylist, merge, SILHOUETTES };
