#!/usr/bin/env node
// Генерирует иллюстрации-заглушки для демо-клиентки (вместо реальных фото).
//   node tools/make-demo-photos.js clients/Вера_Соколова/photos
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const out = process.argv[2] || path.join(__dirname, '..', 'clients', 'Вера_Соколова', 'photos');
fs.mkdirSync(out, { recursive: true });

// Простые силуэты вещей (viewBox 0 0 200 260)
const G = {
  coat: 'M70 20 L130 20 L160 50 L175 240 L25 240 L40 50 Z M100 20 L100 240',
  trench: 'M72 18 L128 18 L162 52 L180 245 L20 245 L38 52 Z M100 18 L88 120 M100 18 L112 120 M40 130 L160 130',
  shirt: 'M65 30 L100 45 L135 30 L175 60 L160 95 L145 85 L145 225 L55 225 L55 85 L40 95 L25 60 Z M100 45 L100 225',
  knit: 'M60 35 Q100 55 140 35 L180 70 L165 200 L150 110 L150 225 L50 225 L50 110 L35 200 L20 70 Z',
  trousers: 'M55 20 L145 20 L160 245 L112 245 L100 90 L88 245 L40 245 Z',
  jeans: 'M58 20 L142 20 L150 245 L108 245 L100 95 L92 245 L50 245 Z',
  skirt: 'M65 30 L135 30 L175 235 L25 235 Z',
  dress: 'M75 20 L125 20 L135 70 L120 110 L170 245 L30 245 L80 110 L65 70 Z',
  blazer: 'M68 22 L132 22 L165 55 L170 230 L30 230 L35 55 Z M100 22 L85 140 L100 230 M100 22 L115 140',
  bag: 'M40 110 L160 110 L170 230 L30 230 Z M70 110 Q100 40 130 110',
  shoes: 'M20 190 L80 150 L110 175 L180 185 L185 215 L20 215 Z',
  boots: 'M70 30 L120 30 L125 180 L180 200 L180 235 L65 235 Z',
  earrings: 'M70 60 A18 18 0 1 0 70.1 60 M130 60 A18 18 0 1 0 130.1 60 M70 96 L70 170 M130 96 L130 170 M70 190 A20 20 0 1 0 70.1 190 M130 190 A20 20 0 1 0 130.1 190',
  belt: 'M10 120 L190 120 L190 150 L10 150 Z M85 112 L115 112 L115 158 L85 158 Z',
  scarf: 'M40 30 L160 30 L150 120 L120 245 L95 245 L110 120 L50 120 Z',
};

const scenes = {
  // лица и фигура
  'face.jpg': { w: 1200, h: 1500, bg: 'linear-gradient(160deg,#EDE3D8,#CDB8A4)', person: 'face', label: 'портрет' },
  'face_window.jpg': { w: 1200, h: 1200, bg: 'linear-gradient(120deg,#F4EEE6 0%,#D8C6B3 70%)', person: 'face', label: 'лицо у окна' },
  'full.jpg': { w: 900, h: 2000, bg: 'linear-gradient(180deg,#EFE7DD,#D6C5B4)', person: 'full', label: 'полный рост' },
  // референсы типажа
  'ref_1.jpg': { w: 1000, h: 1400, bg: '#E7DCCF', items: [['trench', '#B89A7A']], label: 'референс' },
  'ref_2.jpg': { w: 1000, h: 1400, bg: '#D9CFC4', items: [['dress', '#5B4034']], label: 'референс' },
  'ref_3.jpg': { w: 1000, h: 1400, bg: '#EFE9E2', items: [['blazer', '#2A2624']], label: 'референс' },
  // схемы цвета
  'scheme_mono.jpg': { w: 900, h: 700, bg: '#EAE0D5', items: [['knit', '#A98468'], ['trousers', '#7B5A45']], label: 'монохром' },
  'scheme_analog.jpg': { w: 900, h: 700, bg: '#EFE8E0', items: [['shirt', '#C9A47E'], ['skirt', '#8E5A3C']], label: 'аналоговая' },
  'scheme_compl.jpg': { w: 900, h: 700, bg: '#F1ECE6', items: [['knit', '#3F5B6B'], ['trousers', '#B98B63']], label: 'комплементарная' },
  // приёмы коррекции
  'tech_1.jpg': { w: 600, h: 760, bg: '#EDE5DB', items: [['belt', '#5B4034']], label: 'пояс' },
  'tech_2.jpg': { w: 600, h: 760, bg: '#EDE5DB', items: [['blazer', '#2A2624']], label: 'V-вырез' },
  'tech_3.jpg': { w: 600, h: 760, bg: '#EDE5DB', items: [['trousers', '#B89A7A']], label: 'высокая посадка' },
  'tech_4.jpg': { w: 600, h: 760, bg: '#EDE5DB', items: [['skirt', '#7B5A45']], label: 'миди' },
  // мудборд
  'mood_1.jpg': { w: 900, h: 1100, bg: 'linear-gradient(150deg,#D9C7B3,#A7866B)', texture: 'lines', label: 'фактура' },
  'mood_2.jpg': { w: 900, h: 1100, bg: '#EFE8DF', items: [['coat', '#1E1B1A']], label: 'мудборд' },
  'mood_3.jpg': { w: 900, h: 1100, bg: 'linear-gradient(200deg,#2B2523,#5B4034)', texture: 'dots', label: 'настроение' },
  'mood_4.jpg': { w: 900, h: 1100, bg: '#E6DACC', items: [['boots', '#2A2624']], label: 'мудборд' },
  'mood_5.jpg': { w: 900, h: 1100, bg: 'linear-gradient(170deg,#F2EDE7,#DCCDBD)', items: [['shirt', '#FFFFFF']], label: 'мудборд' },
  'mood_6.jpg': { w: 900, h: 1100, bg: '#B3201F', texture: 'rings', label: 'акцент' },
  // капсула
  'cap_1.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['trench', '#B89A7A']], label: 'тренч' },
  'cap_2.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['blazer', '#2A2624']], label: 'жакет' },
  'cap_3.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['shirt', '#FFFFFF']], label: 'рубашка' },
  'cap_4.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['knit', '#A98468']], label: 'джемпер' },
  'cap_5.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['trousers', '#5B4034']], label: 'брюки' },
  'cap_6.jpg': { w: 800, h: 800, bg: '#EFE8DF', items: [['jeans', '#3E4B5C']], label: 'джинсы' },
  // образы
  'look_work_1.jpg': { w: 900, h: 1200, bg: '#E9E1D7', items: [['blazer', '#2A2624'], ['trousers', '#B89A7A']], label: 'работа' },
  'look_work_2.jpg': { w: 900, h: 1200, bg: '#E9E1D7', items: [['bag', '#5B4034'], ['shoes', '#1E1B1A']], label: 'работа' },
  'look_weekend_1.jpg': { w: 900, h: 1200, bg: '#EEE6DC', items: [['knit', '#A98468'], ['jeans', '#3E4B5C']], label: 'выходные' },
  'look_weekend_2.jpg': { w: 900, h: 1200, bg: '#EEE6DC', items: [['boots', '#5B4034']], label: 'выходные' },
  'look_evening.jpg': { w: 900, h: 1200, bg: '#2B2523', items: [['dress', '#B3201F'], ['earrings', '#C9A46A']], label: 'вечер' },
  'look_event_1.jpg': { w: 900, h: 1200, bg: '#E6DACC', items: [['dress', '#7B5A45']], label: 'событие' },
  'look_event_2.jpg': { w: 900, h: 1200, bg: '#E6DACC', items: [['earrings', '#C9A46A'], ['bag', '#1E1B1A']], label: 'событие' },
  'look_travel.jpg': { w: 900, h: 1200, bg: '#EDE5DB', items: [['trench', '#B89A7A'], ['shirt', '#FFFFFF']], label: 'поездка' },
  'look_office_2.jpg': { w: 900, h: 1200, bg: '#E9E1D7', items: [['knit', '#5B4034'], ['skirt', '#2A2624']], label: 'работа' },
  // детали, волосы
  'details_1.jpg': { w: 900, h: 900, bg: '#EDE5DB', items: [['earrings', '#C9A46A']], label: 'украшения' },
  'details_2.jpg': { w: 900, h: 900, bg: '#E3D6C8', items: [['scarf', '#8E5A3C']], label: 'платок' },
  'details_3.jpg': { w: 900, h: 900, bg: '#EDE5DB', items: [['belt', '#1E1B1A']], label: 'ремень' },
  'hair.jpg': { w: 1000, h: 1200, bg: 'linear-gradient(160deg,#EDE3D8,#C9B29C)', person: 'face', label: 'волосы' },
};

function svgItems(items) {
  const n = items.length;
  return items.map(([g, col], i) => {
    const stroke = col.toUpperCase() === '#FFFFFF' ? '#CDBBA8' : 'rgba(0,0,0,.18)';
    const x = n === 1 ? 15 : 5 + i * (90 / n);
    const w = n === 1 ? 70 : 90 / n;
    return `<svg viewBox="0 0 200 260" style="position:absolute;left:${x}%;top:12%;width:${w}%;height:76%"><path d="${G[g]}" fill="${col}" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/></svg>`;
  }).join('');
}

function person(kind) {
  if (kind === 'face') {
    return `<svg viewBox="0 0 400 500" style="position:absolute;left:10%;top:8%;width:80%;height:92%">
      <path d="M90 250 Q80 90 200 80 Q320 90 310 250 L330 420 Q260 380 250 330 L150 330 Q140 380 70 420 Z" fill="#6B4632"/>
      <ellipse cx="200" cy="230" rx="88" ry="112" fill="#E9C9AE"/>
      <path d="M112 200 Q130 110 200 110 Q275 112 290 205 Q250 150 200 150 Q150 150 112 200 Z" fill="#6B4632"/>
      <path d="M150 340 L250 340 L260 400 Q200 420 140 400 Z" fill="#E9C9AE"/>
      <path d="M60 500 Q70 400 150 390 Q200 420 250 390 Q330 400 340 500 Z" fill="#2A2624"/>
    </svg>`;
  }
  return `<svg viewBox="0 0 200 480" style="position:absolute;left:22%;top:5%;width:56%;height:92%">
    <circle cx="100" cy="45" r="28" fill="#E9C9AE"/><path d="M72 40 Q75 10 100 12 Q128 12 130 42 Q115 25 100 26 Q85 26 72 40 Z" fill="#6B4632"/>
    <path d="M88 72 L112 72 L112 84 L88 84 Z" fill="#E9C9AE"/>
    <path d="M60 88 Q100 78 140 88 L150 150 Q128 190 132 225 L68 225 Q72 190 50 150 Z" fill="#F7F2EB" stroke="#CDBBA8"/>
    <path d="M68 225 L132 225 L140 460 L108 460 L100 270 L92 460 L60 460 Z" fill="#2A2624"/>
  </svg>`;
}

function texture(t) {
  if (t === 'lines') return `<div style="position:absolute;inset:0;background:repeating-linear-gradient(115deg,rgba(255,255,255,.18) 0 6px,transparent 6px 22px)"></div>`;
  if (t === 'dots') return `<div style="position:absolute;inset:0;background:radial-gradient(circle,rgba(233,223,211,.35) 3px,transparent 4px) 0 0/40px 40px"></div>`;
  return `<svg viewBox="0 0 100 100" style="position:absolute;inset:10%"><g fill="none" stroke="rgba(247,242,235,.6)"><circle cx="50" cy="50" r="45"/><circle cx="50" cy="50" r="30" stroke-dasharray="1 3"/><circle cx="50" cy="50" r="15"/></g><circle cx="95" cy="50" r="2.5" fill="#F7F2EB"/></svg>`;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [file, s] of Object.entries(scenes)) {
    await page.setViewportSize({ width: s.w, height: s.h });
    const dark = /#2|#1|#B3/.test(s.bg.slice(0, 3)) || s.bg.includes('#2B2523');
    await page.setContent(`<html><body style="margin:0"><div style="position:relative;width:${s.w}px;height:${s.h}px;background:${s.bg};overflow:hidden;font-family:Arial">
      ${s.person ? person(s.person) : ''}${s.items ? svgItems(s.items) : ''}${s.texture ? texture(s.texture) : ''}
      <div style="position:absolute;left:4%;bottom:3%;font-size:${Math.round(s.w / 32)}px;letter-spacing:.2em;text-transform:uppercase;color:${dark ? 'rgba(247,242,235,.7)' : 'rgba(0,0,0,.35)'}">демо · ${s.label}</div>
    </div></body></html>`);
    await page.screenshot({ path: path.join(out, file), type: 'jpeg', quality: 90 });
  }
  await browser.close();
  console.log(`Сгенерировано ${Object.keys(scenes).length} фото в ${out}`);
})();
