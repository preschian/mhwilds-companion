"""Finalize item icons into the repo dataset.

Reads TEMP icons_items/*.png + item_iconmap.json, writes:
  data/icons/items/*.png   (82 files, game assets: private repo only)
  data/item_palette.json   (ColorPreset.TYPE value -> {name, rgba})
  data/materials.json      (+icon per item: {glyph, tint, badge, badgePos})
"""
import json
import os
import shutil

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

m = json.load(open(os.path.join(HERE, 'item_iconmap.json'), encoding='utf-8'))
dest = os.path.join(REPO, 'data', 'icons', 'items')
os.makedirs(dest, exist_ok=True)
n = 0
for f in sorted(os.listdir(os.path.join(HERE, 'icons_items'))):
    if f.endswith('.png'):
        shutil.copy2(os.path.join(HERE, 'icons_items', f), os.path.join(dest, f))
        n += 1
print(f'copied {n} pngs')

json.dump(m['palette'], open(os.path.join(REPO, 'data', 'item_palette.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'palette: {len(m["palette"])} colors')

mats = json.load(open(os.path.join(REPO, 'data', 'materials.json'), encoding='utf-8'))
imap = m['items']
hit = miss = 0
for it in mats:
    v = imap.get(str(it['id']))
    if v is None:
        it['icon'] = None
        miss += 1
        continue
    it['icon'] = {'glyph': f"items/{v['glyph']}", 'tint': v['tint'],
                  'badge': f"items/{v['badge']}" if v['badge'] else None,
                  'badgePos': v['badgePos']}
    hit += 1
json.dump(mats, open(os.path.join(REPO, 'data', 'materials.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'materials: {hit} with icon, {miss} without')
