"""Extract per-part hitzones from EmParamParts files -> validation printout.

Usage: python meat_extract.py [EmDirName] [variant]
  e.g. python meat_extract.py Em0001 00
Resolves cParts -> PARTS_TYPE + cMeat states via guids, compares vs Kiranico.
"""
import json
import os
import tempfile
import struct
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
from dump_block import extract  # noqa: E402
from rsz_classscan import build_map, instances_of  # noqa: E402
from rsz_read import parse_instances, resolve_refs  # noqa: E402

ROOT = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign', 'Enemy')
LAYOUTS = os.path.join(HERE, 'layouts_parts.json')

CLASSES = [
    'app.user_data.EmParamParts',
    'app.user_data.EmParamParts.cParts',
    'app.user_data.EmParamParts.cMeat',
    'app.user_data.EmParamParts.cVital',
    'app.user_data.EmParamParts.cWeakPoint',
    'app.user_data.EmParamParts.cScarPoint',
    'app.user_data.EmParamParts.cPartsBreak',
    'app.user_data.EmParamParts.cMultiParts',
    'app.user_data.EmParamParts.LegendaryScarNumData',
    'app.EnemyDef.PARTS_TYPE_Serializable',
    'app.EnemyDef.MULTI_PARTS_PRIORITY_CONDITION_TYPEBit_Serializable',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cParts>',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cMeat>',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cMultiParts>',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cPartsBreak>',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cWeakPoint>',
    'ace.cInstanceGuidArray`1<app.user_data.EmParamParts.cScarPoint>',
]

MEAT_KEYS = ['_Slash', '_Blow', '_Shot', '_Fire', '_Water', '_Thunder', '_Ice', '_Dragon', '_Stun']
STATES = ['_MeatGuidNormal', '_MeatGuidBreak', '_MeatGuidCustom1', '_MeatGuidCustom2',
          '_MeatGuidCustom3', '_MeatGuidCustom4', '_MeatGuidCustom5']
EMPTY = '00' * 16


def load_layouts():
    if os.path.exists(LAYOUTS):
        return json.load(open(LAYOUTS, encoding='utf-8'))
    out = {}
    for n in CLASSES:
        block = extract(n)
        if block is None:
            print(f'LAYOUT MISSING: {n}')
            continue
        out[n] = json.loads('{' + block.rstrip().rstrip(',') + '}')[n].get('RSZ')
    json.dump(out, open(LAYOUTS, 'w', encoding='utf-8'))
    print(f'layouts cached: {len(out)} classes')
    return out


def parse_parts_file(path, layouts, mmap):
    raw = open(path, 'rb').read()
    base = raw.find(b'RSZ\x00')
    _, _, n_obj, n_inst, _, _, inst_off, data_off, _ = struct.unpack_from('<IIIiIIQQQ', raw, base)
    eps = struct.unpack_from(f'<{n_obj}I', raw, base + 48)
    insts = [struct.unpack_from('<I', raw, base + inst_off + 8 * i)[0] for i in range(n_inst)]
    objs, end = parse_instances(raw, base, data_off, insts, layouts, mmap, verbose=False)
    # entry points are 1-based into non-null objs
    root = resolve_refs(objs, [objs[e] for e in eps])[0]
    return root, end, len(raw)


def main():
    em = sys.argv[1] if len(sys.argv) > 1 else 'Em0001'
    var = sys.argv[2] if len(sys.argv) > 2 else '00'
    num = em[2:]
    path = os.path.join(ROOT, em, var, 'Data', f'{em}_{var}_Param_Parts.user.3')
    print('loading layouts...')
    layouts = load_layouts()
    print('building murmur map...')
    mmap = build_map()
    enums = json.load(open(os.path.join(HERE, 'parts_enums.json'), encoding='utf-16'))
    pnames = json.load(open(os.path.join(HERE, 'part_names.json'), encoding='utf-8'))
    rod = {v: k for k, v in enums['app.Hit.ROD_EXTRACT'].items()}

    def pname(v):
        return pnames.get(str(v), f'PART<{v}>')
    print(f'parsing {path}')
    root, end, total = parse_parts_file(path, layouts, mmap)
    print(f'data end=0x{end:X} filelen=0x{total:X} (match={end == total})')
    meats = {m['_InstanceGuid']: m for m in root['_MeatArray']['_DataArray']}
    print(f'parts={len(root["_PartsArray"]["_DataArray"])} meats={len(meats)} '
          f'weak={len(root["_WeakPointArray"]["_DataArray"])} scars={len(root["_ScarPointArray"]["_DataArray"])}')
    by_guid = {}
    for p in root['_PartsArray']['_DataArray']:
        by_guid[p['_InstanceGuid']] = p
        pt = pname(p['_PartsType']['_Value'])
        print(f'--- {pt} (rod={rod.get(p["_RodExtract"], p["_RodExtract"])})')
        for s in STATES:
            g = p[s]
            if g == EMPTY:
                continue
            m = meats.get(g)
            if m is None:
                print(f'    {s}: GUID-DANGLING {g[:8]}')
                continue
            vals = ' '.join(f'{k[1:]}={m[k]}' for k in MEAT_KEYS)
            print(f'    {s}: {vals}')
    for w in root['_WeakPointArray']['_DataArray']:
        m = meats.get(w['_MeatGuid'])
        link = by_guid.get(w['_LinkPartsGuid'], {})
        pt = pname((link.get('_PartsType') or {}).get('_Value', '?')) if link else '?'
        vals = ' '.join(f'{k[1:]}={m[k]}' for k in MEAT_KEYS) if m else 'DANGLING'
        print(f'WEAKPOINT -> {pt}: {vals}')
    for s in root['_ScarPointArray']['_DataArray']:
        m = meats.get(s['_MeatGuid'])
        link = by_guid.get(s['_LinkPartsGuid'], {})
        pt = pname((link.get('_PartsType') or {}).get('_Value', '?')) if link else '?'
        vals = ' '.join(f'{k[1:]}={m[k]}' for k in MEAT_KEYS) if m else 'DANGLING'
        print(f'SCAR[{s["_Num"]}] -> {pt}: {vals}')


if __name__ == '__main__':
    main()
