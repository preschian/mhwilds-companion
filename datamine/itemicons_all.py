"""Item icons: parse icon fields + palette, crop glyphs/badges from atlases.

Reads (from $MHRESEARCH):
  reward_merged/.../Common/Item/itemData.user.3   item catalog (_IconType/_IconColor/_AddIconType)
  gui_merged/.../AddIconData.user.3               badge table (_AddIcon -> pos/seq/pattern)
  gui_merged/.../colorPreset.gcp.2                tint palette (ABGR)
  atlas_png/tex000201_0_IMLM4.png                 base-glyph atlas (100px grid, 20 cols)
  atlas_png/tex000201_20_IMLM4.png                badge sheet (64px grid, 8 cols)
Writes: icons_items/*.png + item_iconmap.json

Mapping (derived from game files, visually verified ~70/77 glyphs):
  base cell = max(0, IconType - 1), row-major. IconType 0 falls back to cell 0
  (broken-shard glyph; e.g. Damaged/Rusted Weapon Shard).
  tint = ColorPreset.TYPE value -> gcp entry slot 0 (all item colors 0..21
  have identical slots; game multiplies the white glyph by it).
  badge cell: AddIcon pattern -> sheet cell, overwhelmingly pattern+1, with
  explicit semantic matches for the 5 item-used badges (see PATTERN_CELL).
Requires: Pillow (pip install pillow).
"""
import glob
import json
import os
import struct
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_block import extract  # noqa: E402
from rsz_classscan import build_map  # noqa: E402
from rsz_read import parse_instances, resolve_refs  # noqa: E402
from PIL import Image  # noqa: E402

RROOT = os.path.join(HERE, 'reward_merged', 'natives', 'STM', 'GameDesign')
GROOT = os.path.join(HERE, 'gui_merged', 'natives', 'STM')
OUT = os.path.join(HERE, 'icons_items')

# Badge pattern -> tex000201_20 cell. pat+1 holds for ~35/40 entries; the five
# item-used badges are pinned by semantic match (only padlock/gauntlet/etc.).
PATTERN_CELL = {0: 0, 2: 2, 29: 30, 36: 37, 37: 38}
ADD_NAMES = {0: 'none', 1: 'shell_lv1', 8: 'wish_item', 31: 'lock',
             38: 'for_armor', 40: 'equip_tempered'}
ADD_POS = {0: 'LT', 1: 'RT', 2: 'LB', 3: 'RB', 4: 'CT'}


def enum_map(name):
    block = extract(name)
    obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
    fields = obj[name].get('fields') or {}
    return {k: v.get('default') for k, v in fields.items()
            if isinstance(v, dict) and 'default' in v}


def parse_user(path, classes):
    layouts = {}
    for n in classes:
        b = extract(n)
        if b is None:
            raise SystemExit(f'LAYOUT MISSING: {n}')
        layouts[n] = json.loads('{' + b.rstrip().rstrip(',') + '}')[n].get('RSZ')
    mmap = build_map()
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    _, _, n_obj, n_inst, _, _, inst_off, data_off, _ = struct.unpack_from('<IIIiIIQQQ', raw, base)
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    insts = [struct.unpack_from('<I', raw, base + inst_off + 8 * i)[0] for i in range(n_inst)]
    objs, end = parse_instances(raw, base, data_off, insts, layouts, mmap)
    assert end == len(raw), f'{path}: end 0x{end:X} != len 0x{len(raw):X}'
    return resolve_refs(objs, [objs[e - 1] for e in eps])[0]


def abgr(u):
    return '#%02X%02X%02X' % (u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF)


def tight(im):
    bbox = im.getchannel('A').getbbox()
    return im.crop(bbox) if bbox else im


def main():
    os.makedirs(OUT, exist_ok=True)
    ctypes = enum_map('app.ColorPreset.TYPE')
    cname = {v: k for k, v in ctypes.items()}

    # Palette.
    gcp = glob.glob(os.path.join(GROOT, 'GUI', 'colorPreset.gcp.2'))[0]
    raw = open(gcp, 'rb').read()
    assert raw[4:8] == b'GCPR', 'bad gcp magic'
    n = struct.unpack_from('<I', raw, 8)[0]
    pal = {}
    for i in range(n):
        slots = struct.unpack_from('<4I', raw, 12 + 40 * i + 4)
        pal[i] = {'name': cname.get(i), 'rgba': abgr(slots[0]), 'slots': [abgr(s) for s in slots]}
    print(f'palette: {len(pal)} entries')

    # Item catalog icon fields.
    iroot = parse_user(os.path.join(RROOT, 'Common', 'Item', 'itemData.user.3'),
                       ['app.user_data.ItemData', 'app.user_data.ItemData.cData'])
    vals = iroot['_Values']['_DataArray'] if isinstance(iroot.get('_Values'), dict) else iroot['_Values']
    fields = {}
    for c in vals:
        fields[c['_ItemId']] = {'icon': c['_IconType'], 'add': c['_AddIconType'],
                                'color': c['_IconColor'], 'equip': c['_EquipIcon']}
    print(f'items: {len(fields)}')

    # Badge table.
    aroot = parse_user(os.path.join(GROOT, 'GameDesign', 'GUI', 'Common', '_UserData', 'AddIconData.user.3'),
                       ['app.user_data.cGUIAddIconData', 'app.user_data.cGUIAddIconData.Data'])
    addtab = {e['_AddIcon']: e for e in aroot['Values']}
    print(f'addicon entries: {len(addtab)}')

    used_colors = {v['color'] for v in fields.values()}
    for i in sorted(used_colors):
        s = pal[i]['slots']
        if len(set(s)) != 1:
            print(f'WARN color {i} ({pal[i]["name"]}) slots differ: {s}')

    # Crop glyphs.
    atl = Image.open(os.path.join(HERE, 'atlas_png', 'tex000201_0_IMLM4.png')).convert('RGBA')
    cells = {}
    for ic in sorted({v['icon'] for v in fields.values()}):
        cell = max(0, ic - 1)
        cx, cy = cell % 20, cell // 20
        t = tight(atl.crop((cx * 100, cy * 100, (cx + 1) * 100, (cy + 1) * 100)))
        fn = f'itemglyph_{ic:03d}.png'
        t.save(os.path.join(OUT, fn))
        cells[ic] = {'cell': cell, 'glyph': fn}
        if min(t.size) < 4:
            print(f'WARN near-empty glyph for icon {ic}')

    # Crop used badges.
    bimg = Image.open(os.path.join(HERE, 'atlas_png', 'tex000201_20_IMLM4.png')).convert('RGBA')
    badges = {}
    for add in sorted({v['add'] for v in fields.values()} - {0}):
        e = addtab[add]
        pat = e['_PatternNo']
        cell = PATTERN_CELL.get(pat, pat + 1)
        cx, cy = cell % 8, cell // 8
        t = tight(bimg.crop((cx * 64, cy * 64, (cx + 1) * 64, (cy + 1) * 64)))
        fn = f'itemadd_{ADD_NAMES.get(add, f"add{add}")}.png'
        t.save(os.path.join(OUT, fn))
        badges[add] = {'glyph': fn, 'pos': ADD_POS[e['_AddPosition']],
                       'pattern': pat, 'cell': cell}
    print('badges:', {k: v['glyph'] for k, v in badges.items()})

    out = {}
    for iid, v in fields.items():
        b = badges.get(v['add'])
        out[iid] = {'icon': v['icon'], 'glyph': cells[v['icon']]['glyph'],
                    'cell': cells[v['icon']]['cell'], 'color': v['color'],
                    'colorName': pal[v['color']]['name'], 'tint': pal[v['color']]['rgba'],
                    'badge': b['glyph'] if b else None, 'badgePos': b['pos'] if b else None,
                    'equip': v['equip']}
    json.dump({'palette': {k: {'name': p['name'], 'rgba': p['rgba']} for k, p in pal.items()},
               'badges': badges, 'items': out},
              open(os.path.join(HERE, 'item_iconmap.json'), 'w'), indent=0)
    print(f'mapped: {len(out)} items, {len(os.listdir(OUT))} pngs')


if __name__ == '__main__':
    main()
