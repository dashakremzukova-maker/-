#!/usr/bin/env python3
"""Натальная карта стиля — сборщик персонального стайлбука.

  python3 natal_card.py parse "клиенты/Имя Фамилия"   → client.json + проверка.md
  python3 natal_card.py build "клиенты/Имя Фамилия"   → готово/Натальная карта стиля — Имя Фамилия.pdf

Путь к клиентке можно дать относительно папки «натальная карта стиля» (из config.json) или полный.
Вёрстка, CSS, размеры и ссылки взяты 1 в 1 из «образец/build_образец.py».
"""
import hashlib, html, io, json, math, os, re, sys, tempfile, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'config.json').read_text(encoding='utf-8'))
ROOT = Path(os.path.expanduser(CONFIG['drive_path']))
FONTS = HERE / 'fonts'
IMG_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', ''}


# ─────────────────────────── нестрогое чтение ───────────────────────────

def norm(s):
    s = unicodedata.normalize('NFC', s).lower().replace('ё', 'е')
    return re.sub(r'\s+', ' ', s).strip()

def stem(s):
    """«образы типажи» = «образы типаж», «направление стиля» = «направления стиля»."""
    out = []
    for w in norm(s).split(' '):
        while len(w) > 3 and w[-1] in 'аеиоуыэюяйь':
            w = w[:-1]
        out.append(w)
    return ' '.join(out)

ALIASES = {'вверх': 'верх', 'верхи': 'верх', 'низы': 'низ'}

def same_name(a, b):
    a, b = norm(a), norm(b)
    a, b = ALIASES.get(a, a), ALIASES.get(b, b)
    return stem(a) == stem(b)

def find_dir(parent, name):
    if not parent or not parent.is_dir():
        return None
    for d in sorted(parent.iterdir()):
        if d.is_dir() and same_name(d.name, name):
            return d
    return None

def natural_key(p):
    s = norm(Path(p).stem if Path(p).suffix.lower() in IMG_EXT else Path(p).name)
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]

def list_images(folder):
    """Все картинки папки, по имени файла. Файлы без расширения проверяем по содержимому."""
    if not folder or not folder.is_dir():
        return []
    out = []
    for f in folder.iterdir():
        if not f.is_file() or f.name.startswith('.') or f.suffix.lower() not in IMG_EXT:
            continue
        if f.suffix == '' and not is_image(f):
            continue
        out.append(f)
    return sorted(out, key=natural_key)

def is_image(f):
    try:
        open_image(f)
        return True
    except Exception:
        return False

def open_image(f):
    from PIL import Image, ImageOps
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    im = Image.open(f)
    im = ImageOps.exif_transpose(im)
    return im.convert('RGB')


# ─────────────────────────── справка.docx ───────────────────────────

SECTIONS = [  # ключ раздела, слова в заголовке
    ('client', ['клиентка', 'запрос']), ('spheres', ['сферы']), ('type', ['типаж']),
    ('color', ['цвет']), ('figure', ['фигура']), ('style', ['стил', 'направлен']),
    ('wardrobe', ['формула', 'гардероб']), ('details', ['детали']), ('hair', ['волосы']),
    ('shopping', ['покуп']), ('cheat', ['шпаргалка']),
]
FIELDS = {  # раздел → (ключ, варианты начала строки, тип)
    'client': [('name', ['имя, фамилия', 'имя и фамилия', 'имя'], 't'), ('age', ['возраст'], 't'),
               ('height', ['рост'], 't'), ('params', ['параметры'], 't'),
               ('size', ['размер одежды'], 't'), ('shoe', ['размер обуви'], 't'),
               ('request', ['запрос'], 't'), ('result', ['критерий результата', 'критерий', 'как поймем'], 't')],
    'spheres': [('wardrobe_for', ['под что собираем гардероб', 'под что собираем'], 't')],
    'type': [('name', ['название'], 't'), ('desc', ['краткое описание', 'описание'], 't'),
             ('recs', ['рекомендации'], 'l')],
    'color': [('temp', ['температура'], 't'), ('contrast', ['контраст'], 't'),
              ('summary', ['общий вывод', 'вывод'], 't')],
    'figure': [('fig_type', ['тип фигуры'], 't'), ('build', ['тип телосложения', 'телосложение'], 't'),
               ('lines', ['тип линий', 'линии'], 't'),
               ('wish', ['основные пожелания', 'пожелания'], 't'),
               ('recs', ['рекомендации', 'стилистические приемы', 'приемы'], 'l')],
    'wardrobe': [('Верхняя одежда', ['верхняя одежда'], 't'), ('Верх', ['верх'], 't'), ('Низ', ['низ'], 't'),
                 ('Платья', ['платья', 'платье'], 't'), ('Обувь', ['обувь'], 't'), ('Сумки', ['сумки'], 't'),
                 ('_look', ['пример образа'], 'x'), ('_look_desc', ['описание'], 'x'),
                 ('_look_items', ['состав образа'], 'x')],
    'details': [('Фактуры', ['фактуры'], 't'), ('Украшения', ['украшения'], 't')],
    'hair': [('Стрижка', ['стрижка'], 't'), ('Цвет волос', ['цвет волос'], 't')],
    'shopping': [('budget', ['бюджет'], 't'), ('first', ['сначала'], 't'), ('then', ['потом'], 't'),
                 ('optional', ['по желанию'], 't'), ('where', ['где покупать'], 't')],
}

def clean_value(v):
    v = re.sub(r'\[[^\]]*\]', '', v)          # подсказки в [скобках]
    v = re.sub(r'\s+', ' ', v).strip()
    v = v.strip(' ;').strip()
    return v

def cap(s):
    s = clean_value(s)
    s = re.sub(r'^[-–—•*]\s*', '', s)
    s = re.sub(r'^\d+[.)]\s*', '', s)
    return s[:1].upper() + s[1:] if s else s

def split_label(line, variants):
    """«Основные пожелания – …», «Название:Классик», «Верх (блузы…): …» → значение или None."""
    m = re.search(r':|\s[–—-]\s', line)
    label, value = (line[:m.start()], line[m.end():]) if m else (line, '')
    nl = norm(re.sub(r'\([^)]*\)', '', label))
    for v in sorted(variants, key=len, reverse=True):
        if nl == v or nl.startswith(v + ' ') or (m and nl.startswith(v)):
            return value
    return None

def read_docx(path):
    import docx
    doc = docx.Document(str(path))
    return [p.text for p in doc.paragraphs]

def parse_spravka(path):
    raw = {k: {} for k, _ in SECTIONS}
    raw['style'] = {'dirs': []}
    raw['spheres'] = {'items': []}
    raw['cheat'] = {'rules': []}
    sec, cur_field, cur_kind = None, None, None
    for line in read_docx(path):
        t = line.strip()
        if not t:
            continue
        n = norm(t)
        m = re.match(r'^\d+\s*[.)]\s*(.+)$', t)
        if m and re.sub(r'\([^)]*\)', '', m.group(1)).upper() == re.sub(r'\([^)]*\)', '', m.group(1)) and len(m.group(1)) > 3:   # заголовок раздела
            head = norm(m.group(1))
            sec = next((k for k, words in SECTIONS if any(w in head for w in words)), None)
            cur_field, cur_kind = None, None
            continue
        if sec is None or n.startswith('(фото') or n.startswith('(') and 'фото' in n:
            continue
        if re.fullmatch(r'\[.*\]', t):
            continue
        if sec == 'cheat':
            v = cap(t)
            if v:
                raw['cheat']['rules'].append(v)
            continue
        if sec == 'spheres':
            mm = re.match(r'^(.+?)(\([^)]*\))?\s*[:–—-]\s*(\d+)\s*%?\s*$', t)
            if mm and not n.startswith('под что'):
                raw['spheres']['items'].append([cap(mm.group(1)), int(mm.group(3))])
                continue
        if sec == 'style':
            mm = re.match(r'^направлени[ея]\s*(\d)\s*[:–—-]?\s*(.*)$', n)
            if mm:
                rest = clean_value(t[t.lower().find(mm.group(1)) + 1:].lstrip(' :–—-'))
                d = {'name': '', 'desc': ''}
                if rest:
                    parts = re.split(r'\s*:\s*', rest, maxsplit=1)
                    d['name'] = clean_value(parts[0])
                    d['desc'] = clean_value(parts[1]) if len(parts) > 1 else ''
                raw['style']['dirs'].append(d)
                cur_field = None
                continue
            for key, var in (('name', ['название']), ('desc', ['описание'])):
                v = split_label(t, var)
                if v is not None and raw['style']['dirs']:
                    raw['style']['dirs'][-1][key] = clean_value(v)
                    break
            continue
        matched = False
        for key, variants, kind in FIELDS.get(sec, []):
            v = split_label(t, variants)
            if v is None:
                continue
            matched = True
            cur_field, cur_kind = key, kind
            if kind == 'l':
                raw[sec][key] = []
                if clean_value(v):
                    raw[sec][key].append(cap(v))
            elif kind == 't':
                raw[sec][key] = clean_value(v)
            break
        if matched:
            continue
        if cur_kind == 'l':                      # пункт списка, даже без «-»
            v = cap(t)
            if v:
                raw[sec][cur_field].append(v)
        elif cur_kind == 't' and cur_field:      # продолжение текста на новой строке
            v = clean_value(t)
            if v:
                raw[sec][cur_field] = (raw[sec][cur_field] + ' ' + v).strip()
    raw['style']['dirs'] = [d for d in raw['style']['dirs'] if d['name'] or d['desc']]
    for k in list(raw):
        for f in list(raw[k]):
            if f.startswith('_'):
                del raw[k][f]
    return raw


# ─────────────────────────── фото клиентки ───────────────────────────

FORMULA = ['Верх', 'Низ', 'Платья', 'Верхняя одежда', 'Обувь', 'Сумки', 'Фактуры', 'Украшения']

def scan_photos(cdir):
    ph = {}
    ph['цвета'] = list_images(find_dir(cdir, 'цвета'))
    ph['типаж'] = list_images(find_dir(cdir, 'образы типаж'))
    ph['фигура'] = list_images(find_dir(cdir, 'образы фигура'))
    sd = find_dir(cdir, 'направления стиля')
    ph['направления'] = [list_images(find_dir(sd, f'направление {i}')) for i in (1, 2, 3)]
    fd, dd = find_dir(cdir, 'формула гардероба'), find_dir(cdir, 'детали')
    ph['формула'] = {}
    for name in FORMULA:
        parent = dd if name in ('Фактуры', 'Украшения') else fd
        ph['формула'][name] = list_images(find_dir(parent, name))
    ph['фото'] = list_images(find_dir(cdir, 'фото'))
    return ph

def all_photo_entries(ph):
    for key in ('цвета', 'типаж', 'фигура', 'фото'):
        for f in ph[key]:
            yield key, f
    for i, lst in enumerate(ph['направления']):
        for f in lst:
            yield f'направление {i + 1}', f
    for name, lst in ph['формула'].items():
        for f in lst:
            yield f'формула/{name}', f

def dhash(im, size=8):
    g = im.convert('L').resize((size + 1, size))
    px = list(g.tobytes())
    return sum(1 << i for i in range(size * size)
               if px[(i // size) * (size + 1) + i % size] > px[(i // size) * (size + 1) + i % size + 1])


# ─────────────────────────── parse ───────────────────────────

def client_dir(arg):
    p = Path(arg).expanduser()
    if not p.is_absolute():
        p = ROOT / p
    if not p.is_dir():
        sys.exit(f'Нет папки: {p}')
    return p

def find_spravka(cdir):
    docs = [f for f in cdir.iterdir() if f.suffix.lower() == '.docx' and 'справка' in norm(f.name)
            and not f.name.startswith('~$')]
    if docs:
        return sorted(docs, key=lambda f: f.stat().st_mtime)[-1]
    if [f for f in cdir.iterdir() if f.suffix.lower() == '.gdoc']:
        sys.exit('Справка есть только как Google Doc (.gdoc). Скачай её: Файл → Скачать → Microsoft Word (.docx) '
                 'в папку клиентки и запусти снова.')
    sys.exit('В папке клиентки нет справки .docx (файл с «справка» в названии).')

def draft_card(raw):
    """Черновик текстов карты = данные справки как есть. Простой язык и сокращение делает Claude."""
    c, f, w, s = raw['client'], raw['figure'], raw['wardrobe'], raw['shopping']
    items = lambda v: [cap(x) for x in re.split(r'\s*[,;]\s*', v or '') if cap(x)]
    return {
        'request': c.get('request', ''), 'result': c.get('result', ''),
        'spheres': raw['spheres']['items'], 'wardrobe_for': raw['spheres'].get('wardrobe_for', ''),
        'type_name': raw['type'].get('name', ''), 'type_desc': raw['type'].get('desc', ''),
        'type_recs': raw['type'].get('recs', []),
        'temp': raw['color'].get('temp', ''), 'contrast': raw['color'].get('contrast', ''),
        'temp_pos': None, 'contrast_pos': None,
        'colors': {'База': [], 'Акценты': []}, 'color_sum': raw['color'].get('summary', ''),
        'silhouette': f.get('fig_type', ''), 'build': f.get('build', ''), 'lines': f.get('lines', ''),
        'wish': f.get('wish', ''), 'fig_recs': f.get('recs', [])[:5],
        'dirs': raw['style']['dirs'],
        'formula': {k: cap((w | raw['details']).get(k, '')) for k in FORMULA},
        'hair': {k: v for k, v in raw['hair'].items() if v},
        'budget': s.get('budget', ''), 'first': items(s.get('first')), 'then': items(s.get('then')),
        'optional': items(s.get('optional')), 'where': s.get('where', ''),
        'rules': raw['cheat']['rules'][:5],
    }

def cmd_parse(arg, force=False):
    cdir = client_dir(arg)
    sp = find_spravka(cdir)
    raw = parse_spravka(sp)
    name = raw['client'].get('name') or cdir.name
    out = cdir / 'client.json'
    data = json.loads(out.read_text(encoding='utf-8')) if out.exists() else {}
    if force or 'card' not in data:
        data['card'] = draft_card(raw)
        data['status'] = 'черновик'
        data.setdefault('name_gen', '')
    data['name'] = name
    data['raw'] = raw
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    report = check_table(cdir, sp, raw)
    (cdir / 'проверка.md').write_text(report, encoding='utf-8')
    print(report)
    print(f'\n→ {out}\n→ {cdir / "проверка.md"}')

def check_table(cdir, sp, raw):
    ph = scan_photos(cdir)
    L = [f'# Проверка — {raw["client"].get("name") or cdir.name}', '', f'Справка: `{sp.name}`', '',
         '## Что распознано', '', '| Раздел | Поле | Значение |', '|---|---|---|']
    names = {'client': 'Клиентка', 'spheres': 'Сферы', 'type': 'Типаж', 'color': 'Цвет', 'figure': 'Фигура',
             'style': 'Стиль', 'wardrobe': 'Гардероб', 'details': 'Детали', 'hair': 'Волосы',
             'shopping': 'Покупки', 'cheat': 'Шпаргалка'}
    empty = []
    for sec, title in names.items():
        fields = [k for k, _, kind in FIELDS.get(sec, []) if kind != 'x']
        if sec == 'spheres':
            for n, v in raw[sec]['items']:
                L.append(f'| {title} | {n} | {v}% |')
            fields = ['wardrobe_for']
        if sec == 'style':
            for i, d in enumerate(raw[sec]['dirs']):
                L.append(f'| {title} | Направление {i + 1} | **{d["name"]}** — {d["desc"]} |')
            continue
        if sec == 'cheat':
            for i, r in enumerate(raw[sec]['rules']):
                L.append(f'| {title} | Правило {i + 1} | {r} |')
            if not raw[sec]['rules']:
                empty.append(f'{title}: пусто — 5 правил соберу сам')
            continue
        for k in fields:
            v = raw[sec].get(k)
            if isinstance(v, list):
                v = '<br>'.join(f'• {x}' for x in v)
            if v:
                L.append(f'| {title} | {k} | {v} |')
            else:
                empty.append(f'{title} → {k}')
    L += ['', '## Пустые поля (в карту не попадут)', ''] + [f'- {e}' for e in empty]

    L += ['', '## Фото', '', '| Раздел | Кол-во | Файлы |', '|---|---|---|']
    rows = [('цвета', ph['цвета']), ('образы типаж', ph['типаж']), ('образы фигура', ph['фигура'])]
    rows += [(f'направление {i + 1}', l) for i, l in enumerate(ph['направления'])]
    rows += [(f'формула / {k}', l) for k, l in ph['формула'].items()] + [('фото', ph['фото'])]
    for n, lst in rows:
        L.append(f'| {n} | {len(lst)} | {", ".join(f.name for f in lst) or "—"} |')

    small, hashes = [], []
    for key, f in all_photo_entries(ph):
        try:
            im = open_image(f)
        except Exception as e:
            small.append(f'{key}/{f.name}: не открывается ({e})')
            continue
        lim = 1000 if key.startswith('направление') else 800
        if min(im.size) < lim:
            small.append(f'{key}/{f.name}: {im.size[0]}×{im.size[1]} (меньше {lim} px)')
        hashes.append((key, f, dhash(im)))
    dups = [f'{a[0]}/{a[1].name} ≈ {b[0]}/{b[1].name}'
            for i, a in enumerate(hashes) for b in hashes[i + 1:]
            if a[0] != b[0] and bin(a[2] ^ b[2]).count('1') <= 4]
    L += ['', '## Маленькие картинки', ''] + ([f'- {s}' for s in small] or ['- нет'])
    L += ['', '## Одинаковые картинки в разных разделах', ''] + ([f'- {d}' for d in dups] or ['- нет'])
    return '\n'.join(L) + '\n'


# ─────────────────────────── build ───────────────────────────

def e(s):
    return html.escape(str(s))

def plural_looks(n):
    if n % 10 == 1 and n % 100 != 11:
        return f'{n} образ'
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f'{n} образа'
    return f'{n} образов'

class Images:
    """Сжимает фото в JPEG во временной папке, чтобы PDF был лёгким."""
    def __init__(self, tmp):
        self.tmp, self.cache, self.sizes = Path(tmp), {}, {}

    def __call__(self, f, max_side=1400, q=82):
        key = (str(f), max_side)
        if key not in self.cache:
            im = open_image(f)
            im.thumbnail((max_side, max_side))
            out = self.tmp / (hashlib.md5(str(key).encode()).hexdigest() + '.jpg')
            im.save(out, 'JPEG', quality=q, optimize=True, progressive=True)
            self.cache[key], self.sizes[key] = out.as_uri(), im.size
        return self.cache[key]

    def size(self, f, max_side=1400):
        self(f, max_side)
        return self.sizes[(str(f), max_side)]

def find_bg(name):
    d = ROOT / 'оформление'
    for f in sorted(d.iterdir()) if d.is_dir() else []:
        if f.is_file() and same_name(Path(f.name).stem, name):
            return f
    return None

def css():
    F = FONTS.as_uri()
    return f'''
@font-face{{font-family:PF;font-weight:700;src:url({F}/playfair-display-cyrillic-700-normal.woff2)}}
@font-face{{font-family:PF;font-weight:700;src:url({F}/playfair-display-latin-700-normal.woff2);unicode-range:U+0000-00FF}}
@font-face{{font-family:PF;font-weight:400;font-style:italic;src:url({F}/playfair-display-cyrillic-400-italic.woff2)}}
@font-face{{font-family:PF;font-weight:400;font-style:italic;src:url({F}/playfair-display-latin-400-italic.woff2);unicode-range:U+0000-00FF}}
@font-face{{font-family:MR;font-weight:400;src:url({F}/manrope-cyrillic-400-normal.woff2)}}
@font-face{{font-family:MR;font-weight:400;src:url({F}/manrope-latin-400-normal.woff2);unicode-range:U+0000-00FF,U+20BD}}
@font-face{{font-family:MR;font-weight:600;src:url({F}/manrope-cyrillic-600-normal.woff2)}}
@font-face{{font-family:MR;font-weight:600;src:url({F}/manrope-latin-600-normal.woff2);unicode-range:U+0000-00FF}}
@page{{size:1080px 1920px;margin:0}}
*{{box-sizing:border-box}}
body{{margin:0}}
.p{{width:1080px;height:1920px;position:relative;overflow:hidden;page-break-after:always;font-family:MR;font-size:32px;line-height:1.5}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:center}}
.c{{position:absolute;inset:0;padding:120px 90px;display:flex;flex-direction:column}}
.L{{background:#F4EFE8;color:#151515}} .L .k{{color:#6B4A35}} .L i.a{{color:#A8201A}}
.D{{background:#360204;color:#F3E9E4}} .D .k{{color:#C9A9A6}} .D i.a{{color:#E7B7B0}}
.k{{font:600 24px MR;letter-spacing:.22em;text-transform:uppercase}}
h1{{font:700 140px/1 PF;margin:0}} h1 i{{font:italic 400 140px/1 PF}}
h2{{font:700 92px/1.05 PF;margin:22px 0 44px}} h2 i{{font:italic 400 92px/1.05 PF}}
h3{{font:600 24px MR;letter-spacing:.2em;text-transform:uppercase;margin:0 0 12px;color:#6B4A35}}
.D h3{{color:#C9A9A6}}
.q{{font:italic 400 48px/1.3 PF;margin:0 0 34px}}
.card{{background:rgba(244,239,232,.86);border-radius:28px;padding:48px 50px}}
.D .card{{background:rgba(54,2,4,.55)}}
ul{{margin:0;padding:0;list-style:none}} li{{padding:0 0 18px 40px;position:relative}}
li:before{{content:"";position:absolute;left:0;top:22px;width:18px;height:2px;background:#A8201A}}
.D li:before{{background:#E7B7B0}}
.grid{{display:grid;gap:24px}}
.ph{{border-radius:22px;overflow:hidden;background:#e8e0d6}}
.ph img{{width:100%;height:100%;object-fit:cover;object-position:50% 20%;display:block}}
.num{{font:700 30px PF;color:#A8201A;margin-right:18px}}
'''

def scale(label, val, left, right, pos):
    return f'''<div style="margin-bottom:34px"><div style="display:flex;justify-content:space-between"><h3>{label}</h3><b>{e(val)}</b></div>
<div style="position:relative;height:14px;border-radius:7px;background:linear-gradient(90deg,#9FB4C9,#E8DDD0,#C89A6B);margin:14px 0 10px"><span style="position:absolute;left:{pos}%;top:-11px;width:36px;height:36px;border-radius:50%;background:#151515;border:5px solid #F4EFE8;transform:translateX(-50%)"></span></div>
<div style="display:flex;justify-content:space-between;font-size:24px;color:#6B4A35"><span>{left}</span><span>{right}</span></div></div>'''

def auto_pos(text, words):
    n = norm(text)
    for w, p in words:
        if w in n:
            return p
    return 50

TEMP_POS = [('ближе к холод', 38), ('ближе к тепл', 62), ('холод', 15), ('тепл', 85), ('нейтрал', 50)]
CONTRAST_POS = [('выше средн', 72), ('ниже средн', 30), ('высок', 88), ('низк', 12), ('средн', 50)]

def cmd_build(arg):
    cdir = client_dir(arg)
    data = json.loads((cdir / 'client.json').read_text(encoding='utf-8'))
    if data.get('status') != 'утверждено':
        print('⚠ client.json ещё не утверждён (status ≠ «утверждено») — собираю всё равно.')
    D, name = data['card'], data['name']
    ph = scan_photos(cdir)
    tmp = tempfile.TemporaryDirectory()
    im = Images(tmp.name)
    pages, section = [], [0]

    def page(kind, bg, op, body, anchor=''):
        f = find_bg(bg)
        bgd = f'<div class="bg" style="background-image:url(\'{im(f, 1400, 78)}\');opacity:{op}"></div>' if f else ''
        pages.append(f'<div class="p {kind}">{bgd}<div class="c">{anchor}{body}</div></div>')

    def LAB(t):
        section[0] += 1
        return f'<div class="k">{section[0]:02d} · {t}</div>'

    def pic(f, h, extra='', side=1400):
        return f'<div class="ph" style="height:{h}px"><img src="{im(f, side)}"{extra}></div>'

    # 1 обложка
    gen = data.get('name_gen')
    lab = f'<div class="k" style="color:#E7B7B0;margin-bottom:40px">для {e(gen)}</div>' if gen else ''
    page('D', 'Обложка', .55, f'''<div style="margin-top:auto;padding-bottom:80px">{lab}
<h1>Натальная карта <i class="a">стиля</i></h1>
<div style="margin-top:50px;color:#D9C4BF">{e(CONFIG["stylist"])}</div></div>''')

    # 2 запрос + неделя
    blocks = ''
    if D.get('request') or D.get('result'):
        inner = f'<p class="q" style="font-size:44px">«{e(D["request"])}»</p>' if D.get('request') else ''
        if D.get('result'):
            inner += f'<h3>Как поймём, что получилось</h3><p class="q" style="font-size:40px;margin:0">«{e(D["result"])}»</p>'
        else:
            inner = inner.replace('class="q" style="font-size:44px"', 'class="q" style="font-size:44px;margin:0"')
        blocks += f'<div class="card">{inner}</div>'
    sph = [(n, v) for n, v in D.get('spheres', []) if v]
    if sph or D.get('wardrobe_for'):
        wk = ''
        if sph:
            cols = ['#360204', '#A8201A', '#6B4A35', '#C9A9A6', '#8A6A5A']
            cx = cy = 190; r = 175; ang = -90; paths = ''
            tot = sum(v for _, v in sph)
            for i, (n, v) in enumerate(sph):
                a2 = ang + v * 360 / tot
                x1, y1 = cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))
                x2, y2 = cx + r * math.cos(math.radians(a2)), cy + r * math.sin(math.radians(a2))
                if v >= tot:
                    paths += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{cols[i % 5]}"/>'
                else:
                    paths += (f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {1 if a2 - ang > 180 else 0} 1 '
                              f'{x2:.1f},{y2:.1f} Z" fill="{cols[i % 5]}" stroke="#F4EFE8" stroke-width="5"/>')
                ang = a2
            leg = ''.join(f'<div style="display:flex;align-items:center;margin-bottom:16px"><span style="width:24px;height:24px;border-radius:50%;background:{cols[i % 5]};margin-right:16px;flex:none"></span><span style="flex:1">{e(n)}</span><b style="font:700 40px PF">{v}%</b></div>' for i, (n, v) in enumerate(sph))
            wk = f'<div style="display:flex;gap:40px;align-items:center;margin-top:10px"><svg width="380" height="380" viewBox="0 0 380 380">{paths}<circle cx="190" cy="190" r="85" fill="#F4EFE8"/></svg><div style="flex:1">{leg}</div></div>'
        wf = f'<p style="margin:{20 if wk else 0}px 0 0"><b>Собираем гардероб:</b> {e(D["wardrobe_for"])}</p>' if D.get('wardrobe_for') else ''
        h3 = '<h3>Твоя неделя</h3>' if wk else ''
        blocks += f'<div class="card" style="margin-top:{28 if blocks else 0}px">{h3}{wk}{wf}</div>'
    if blocks:
        page('L', 'Знакомство', .3, f'{LAB("Знакомство")}<h2>Твой <i class="a">запрос</i></h2>{blocks}')

    # 3 типаж
    if D.get('type_name') or D.get('type_desc') or D.get('type_recs') or ph['типаж']:
        title = f'Твой типаж — <i class="a">{e(D["type_name"])}</i>' if D.get('type_name') else 'Твой <i class="a">типаж</i>'
        inner = ''
        if D.get('type_desc'):
            inner += f'<p style="margin:0 0 {30 if D.get("type_recs") else 0}px">{e(D["type_desc"])}</p>'
        if D.get('type_recs'):
            inner += '<ul>' + ''.join(f'<li>{e(x)}</li>' for x in D['type_recs']) + '</ul>'
        body = f'<div class="card">{inner}</div>' if inner else ''
        tp = ph['типаж'][:2]
        if tp:
            body += f'<div class="grid" style="grid-template-columns:repeat({len(tp)},1fr);margin-top:{28 if body else 0}px">' + ''.join(pic(f, 560) for f in tp) + '</div>'
        page('D', 'Типаж', .45, f'{LAB("Типаж")}<h2>{title}</h2>{body}')

    # 4 цвета + 5 коллаж
    SW = [(t, arr) for t, arr in D.get('colors', {}).items() if arr]
    color_lab = None
    if D.get('temp') or D.get('contrast') or SW or D.get('color_sum'):
        color_lab = LAB('Цвет')
        body = ''
        sc = ''
        if D.get('temp'):
            sc += scale('Температура', D['temp'], 'холодная', 'тёплая', D.get('temp_pos') or auto_pos(D['temp'], TEMP_POS))
        if D.get('contrast'):
            sc += scale('Контраст', D['contrast'], 'низкий', 'высокий', D.get('contrast_pos') or auto_pos(D['contrast'], CONTRAST_POS))
        if sc:
            body += f'<div class="card" style="background:#F4EFE8">{sc}</div>'
        if SW:
            def circles(title, arr):
                it = ''.join(f'<div style="text-align:center;width:170px"><div style="width:140px;height:140px;border-radius:50%;background:{c};margin:0 auto 14px;border:1px solid rgba(0,0,0,.12);box-shadow:0 6px 18px rgba(0,0,0,.08)"></div><div style="font-size:24px;line-height:1.25">{e(n)}</div></div>' for n, c in arr)
                return f'<h3>{e(title)}</h3><div style="display:flex;gap:24px;margin:10px 0 30px;flex-wrap:wrap">{it}</div>'
            body += f'<div class="card" style="margin-top:{28 if body else 0}px;background:#F4EFE8">{"".join(circles(t, a) for t, a in SW)}</div>'
        if D.get('color_sum'):
            body += f'<div class="card" style="margin-top:{28 if body else 0}px;background:#F4EFE8"><p class="q" style="margin:0;font-size:42px">{e(D["color_sum"])}</p></div>'
        page('L', 'Цвет', .3, f'{color_lab}<h2>Твои <i class="a">цвета</i></h2>{body}')
    if ph['цвета']:
        if color_lab is None:
            color_lab = LAB('Цвет')
        page('L', 'Цвет', .3, f'{color_lab}<h2>Цвета <i class="a">на примерах</i></h2>{collage(ph["цвета"], im)}')

    # 6 фигура + 7 образы
    fig_lab = None
    rows = [(t, v) for t, v in (('Силуэт', D.get('silhouette')), ('Телосложение', D.get('build')), ('Линии', D.get('lines'))) if v]
    if rows or D.get('wish') or D.get('fig_recs'):
        fig_lab = LAB('Фигура')
        body = ''
        if rows or D.get('wish'):
            bl = ''.join(f'<div style="padding:16px 0;border-bottom:1px solid rgba(0,0,0,.12)"><h3>{a}</h3><p style="margin:0">{e(b)}</p></div>' for a, b in rows)
            wq = f'<p class="q" style="margin:{26 if bl else 0}px 0 0;font-size:38px">«{e(D["wish"])}»</p>' if D.get('wish') else ''
            body += f'<div class="card" style="padding:30px 50px">{bl}{wq}</div>'
        if D.get('fig_recs'):
            lis = ''.join(f'<li>{e(x)}</li>' for x in D['fig_recs'][:5])
            body += f'<div class="card" style="margin-top:{28 if body else 0}px"><h3>Что работает на тебя</h3><ul style="margin-top:14px">{lis}</ul></div>'
        page('L', 'Фигура', .3, f'{fig_lab}<h2>Твоя <i class="a">фигура</i></h2>{body}')
    if ph['фигура']:
        if fig_lab is None:
            fig_lab = LAB('Фигура')
        fp = ph['фигура'][:4]
        cols = 1 if len(fp) == 1 else 2
        h = 1300 if len(fp) == 1 else (1000 if len(fp) == 2 else 600)
        grid = f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">' + ''.join(pic(f, h) for f in fp) + '</div>'
        page('L', 'Образы', .3, f'{fig_lab}<h2>Примеры образов <i class="a">для твоей фигуры</i></h2>{grid}')

    # 8 направления
    dirs = []
    for i in range(3):
        d = D.get('dirs', [])[i] if i < len(D.get('dirs', [])) else {}
        imgs = ph['направления'][i]
        if d.get('name') or d.get('desc') or imgs:
            dirs.append((i + 1, d.get('name', ''), d.get('desc', ''), imgs))
    if dirs:
        rows = ''
        for n, nm, desc, imgs in dirs:
            photo = ''
            if imgs:
                photo = f'<div class="ph" style="width:300px;height:400px;flex:none;position:relative"><img src="{im(imgs[0])}"><span style="position:absolute;right:14px;bottom:14px;background:rgba(21,21,21,.72);color:#fff;font:600 22px MR;padding:8px 16px;border-radius:30px">{plural_looks(len(imgs))}</span></div>'
            txt = f'<div class="k" style="margin-bottom:8px">Направление {n}</div>'
            if nm:
                txt += f'<p style="font:italic 400 58px/1.1 PF;color:#A8201A;margin:0 0 14px">{e(nm)}</p>'
            if desc:
                txt += f'<p style="margin:0 0 14px">{e(desc)}</p>'
            if imgs:
                txt += '<span style="font:600 24px MR;color:#A8201A">Смотреть образы →</span>'
            card = f'<div class="card" style="display:flex;gap:34px;align-items:center;padding:26px 30px;margin-bottom:24px">{photo}<div>{txt}</div></div>'
            rows += f'<a href="#dir{n}" style="text-decoration:none;color:inherit;display:block">{card}</a>' if imgs else card
        page('L', 'Стиль', .3, f'{LAB("Стиль")}<h2 style="font-size:78px;margin-bottom:34px">Твои <i class="a" style="font-size:78px">направления стиля</i></h2>{rows}', anchor='<a id="styles"></a>')

    # 9 формула гардероба
    tiles = []
    for nm in FORMULA:
        t = (D.get('formula') or {}).get(nm, '')
        imgs = ph['формула'][nm]
        if t or imgs:
            tiles.append((nm, t, imgs[0] if imgs else None))
    if tiles:
        def tile(n, t, f):
            p = f'<div class="ph" style="height:330px;margin-bottom:14px"><img src="{im(f, 900)}" style="object-position:50% 35%"></div>' if f else ''
            tx = f'<p style="margin:0;font-size:25px;line-height:1.35">{e(t)}</p>' if t else ''
            return f'<div>{p}<h3 style="margin-bottom:6px;font-size:21px">{n}</h3>{tx}</div>'
        page('L', 'Формула гардероба', .3, f'''{LAB("Гардероб")}<h2 style="margin-bottom:30px">Формула <i class="a">гардероба</i></h2>
<div class="card" style="padding:36px 32px"><div class="grid" style="grid-template-columns:repeat(4,1fr);gap:36px 20px">{"".join(tile(*x) for x in tiles)}</div></div>''')

    # волосы (если заполнены)
    hair = {k: v for k, v in (D.get('hair') or {}).items() if v}
    if hair:
        bl = ''.join(f'<div style="padding:16px 0;border-bottom:1px solid rgba(0,0,0,.12)"><h3>{e(k)}</h3><p style="margin:0">{e(v)}</p></div>' for k, v in hair.items())
        page('L', 'Волосы', .3, f'{LAB("Волосы")}<h2>Твои <i class="a">волосы</i></h2><div class="card" style="padding:30px 50px">{bl}</div>')

    # 10 покупки
    def chk(t, arr):
        return f'<h3 style="margin-top:30px">{t}</h3>' + ''.join(f'<div style="display:flex;align-items:center;margin:12px 0"><span style="width:32px;height:32px;border:2px solid #6B4A35;border-radius:8px;margin-right:20px;flex:none"></span>{e(x)}</div>' for x in arr)
    lists = [(t, D.get(k) or []) for t, k in (('Сначала', 'first'), ('Потом', 'then'), ('По желанию', 'optional'))]
    lists = [(t, a) for t, a in lists if a]
    if D.get('budget') or lists or D.get('where'):
        body = ''
        if D.get('budget'):
            body += f'<div style="display:flex;justify-content:space-between;align-items:baseline"><h3>Бюджет</h3><b style="font:700 56px PF">{e(D["budget"])}</b></div>'
        body += ''.join(chk(t, a) for t, a in lists)
        if D.get('where'):
            body += f'<h3 style="margin-top:30px">Где покупать</h3><p style="margin:0">{e(D["where"])}</p>'
        body = body.replace('<h3 style="margin-top:30px">', '<h3>', 1) if not D.get('budget') else body
        page('L', 'Список покупок', .3, f'{LAB("Покупки")}<h2>Список <i class="a">покупок</i></h2><div class="card">{body}</div>')

    # 11 шпаргалка
    rules = D.get('rules') or []
    if rules or SW or dirs:
        body = ''
        if rules:
            rl = ''.join(f'<div style="display:flex;margin-bottom:22px"><span class="num">{i + 1}</span><span>{e(x)}</span></div>' for i, x in enumerate(rules[:5]))
            body += f'<h2 style="margin-bottom:26px">{len(rules[:5])} правил <i class="a">твоего стиля</i></h2><div class="card" style="background:rgba(244,239,232,.95);padding:40px 46px">{rl}</div>'
        if SW:
            sw = ''.join(f'<div style="text-align:center;width:150px"><div style="width:110px;height:110px;border-radius:50%;background:{c};margin:0 auto 10px;border:1px solid rgba(0,0,0,.12)"></div><div style="font-size:21px;line-height:1.2">{e(n)}</div></div>' for _, arr in SW for n, c in arr)
            body += f'<div class="card" style="margin-top:22px;background:rgba(244,239,232,.95);padding:36px 46px"><h3>Твои цвета</h3><div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:14px">{sw}</div></div>'
        dn = [(n, nm) for n, nm, _, _ in dirs if nm]
        if dn:
            dl = ''.join(f'<div style="display:flex;align-items:baseline;margin-bottom:8px"><span class="num" style="font-size:26px">{n:02d}</span><span style="font:700 44px PF">{e(nm)}</span></div>' for n, nm in dn)
            body += f'<div class="card" style="margin-top:22px;background:rgba(244,239,232,.95);padding:36px 46px"><h3>Твои направления</h3>{dl}</div>'
        cam = '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/></svg>'
        page('L', 'Шпаргалка', .2, f'''<div style="display:flex;justify-content:space-between;align-items:center"><div class="k">Шпаргалка</div>
<div style="display:flex;align-items:center;gap:14px;background:#A8201A;color:#fff;padding:16px 30px;border-radius:60px;font:600 28px MR;box-shadow:0 8px 22px rgba(168,32,26,.35)">{cam}Сделай скриншот</div></div>{body}''')

    # 12 финал
    tg = CONFIG['telegram'].lstrip('@')
    page('D', 'Финал', .55, f'''<div style="margin-top:auto;padding-bottom:80px"><h1>Спасибо<i class="a">!</i></h1>
<p style="margin:50px 0 40px;font-size:36px">Эта карта — твоя опора при покупках и сборах. Сохрани шпаргалку в своём телефоне.</p>
<div class="k" style="color:#E7B7B0;margin-bottom:14px">Следующий шаг</div><p style="margin:0 0 50px">Разбор гардероба или совместный шопинг</p>
<a href="https://t.me/{tg}" style="display:inline-block;padding:26px 44px;border:2px solid #E7B7B0;border-radius:60px;color:#F3E9E4;text-decoration:none;font-weight:600">Написать в Telegram · @{e(tg)}</a>
<div style="margin-top:40px;color:#D9C4BF">{e(CONFIG["stylist"])}</div></div>''')

    # 13–15 галереи направлений
    for n, nm, _, imgs in dirs:
        if not imgs:
            continue
        P = lambda f, h: pic(f, h, side=1800)
        if len(imgs) >= 3:
            grid = f'<div class="grid" style="grid-template-columns:1.25fr 1fr;gap:22px"><div>{P(imgs[0], 1400)}</div><div class="grid" style="gap:22px">{P(imgs[1], 689)}{P(imgs[2], 689)}</div></div>'
        else:
            grid = f'<div class="grid" style="grid-template-columns:repeat({len(imgs)},1fr)">' + ''.join(P(f, 1400) for f in imgs) + '</div>'
        back = '<a href="#styles" style="font:600 26px MR;color:#fff;background:#A8201A;padding:14px 28px;border-radius:60px;text-decoration:none">← к направлениям</a>'
        title = f'<i class="a">{e(nm)}</i>' if nm else f'Направление <i class="a">{n}</i>'
        page('L', 'Стиль', .3, f'''<div style="display:flex;justify-content:space-between;align-items:center"><div class="k">Направление {n}</div>{back}</div>
<h2 style="margin-bottom:30px">{title}</h2>{grid}''', anchor=f'<a id="dir{n}"></a>')

    html_doc = f'<html><head><meta charset="utf-8"><style>{css()}</style></head><body>{"".join(pages)}</body></html>'
    out_dir = find_dir(cdir, 'готово') or (cdir / 'готово')
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f'Натальная карта стиля — {name}.pdf'
    hp = Path(tmp.name) / 'card.html'
    hp.write_text(html_doc, encoding='utf-8')
    render_pdf(hp, out)
    verify(out, len(pages), [n for n, _, _, imgs in dirs if imgs])
    tmp.cleanup()

def collage(files, im, W=900, avail=1480, colw=310, ov=80):
    cols = [files[0::3], files[1::3], files[2::3]]
    offs = [0, 110, 40]
    def heights(cw):
        return [offs[ci] + sum(int(cw * im.size(f)[1] / im.size(f)[0]) - ov for f in col) + ov
                for ci, col in enumerate(cols) if col]
    while max(heights(colw)) > avail and colw > 200:
        colw -= 10
    xs = [0, (W - colw) // 2, W - colw]
    out, n = '', 0
    for ci, col in enumerate(cols):
        y = offs[ci]
        for f in col:
            w, h = im.size(f)
            hh = int(colw * h / w)
            rot = [-2.5, 1.8, -1.2, 2.4][n % 4]; n += 1
            out += f'<img src="{im(f)}" style="position:absolute;left:{xs[ci]}px;top:{y}px;width:{colw}px;height:{hh}px;object-fit:cover;border:10px solid #fff;border-radius:6px;box-shadow:0 14px 34px rgba(0,0,0,.22);transform:rotate({rot}deg);z-index:{n}">'
            y += hh - ov
    return f'<div style="position:relative;width:{W}px;height:{avail}px">{out}</div>'

def render_pdf(html_path, out):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = CONFIG.get('chromium_path')
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page()
        pg.goto(html_path.as_uri(), wait_until='networkidle')
        pg.evaluate('document.fonts.ready')
        pg.pdf(path=str(out), width='1080px', height='1920px', print_background=True)
        b.close()

def verify(pdf, n_pages, gallery_dirs):
    import pymupdf
    doc = pymupdf.open(str(pdf))
    mb = pdf.stat().st_size / 1e6
    internal = sum(1 for pg in doc for l in pg.get_links() if l.get('kind') in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED))
    external = [l.get('uri') for pg in doc for l in pg.get_links() if l.get('kind') == pymupdf.LINK_URI]
    print(f'✓ {pdf}\n  страниц: {doc.page_count} (ожидалось {n_pages}), размер: {mb:.1f} МБ'
          f'{"  ⚠ больше 15 МБ" if mb > 15 else ""}')
    print(f'  внутренних ссылок: {internal} (ожидалось {2 * len(gallery_dirs)}), внешние: {external}')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('parse', 'build'):
        sys.exit(__doc__)
    if sys.argv[1] == 'parse':
        cmd_parse(sys.argv[2], force='--force' in sys.argv)
    else:
        cmd_build(sys.argv[2])
