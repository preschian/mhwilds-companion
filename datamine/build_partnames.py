"""Build part-type-id -> English name map from EnemyPartsTypeName.msg.

Usage: python build_partnames.py   (reads merged msg, writes part_names.json)
"""
import json
import os
import tempfile
import re
import sys

HERE = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
sys.path.insert(0, HERE)
from msg_parse import parse  # noqa: E402

MSG = os.path.join(HERE, 'extract_full', 'merged', 'natives', 'STM', 'GameDesign',
                   'Text', 'Excel_Data', 'EnemyPartsTypeName.msg.23')

r = parse(MSG)
eng = r['langs'].index(1)
out = {}
for e in r['entries']:
    m = re.fullmatch(r'EnemyPartsTypeName_(ROT_|EXP_)?(m?)(\d+)', e['name'])
    if not m or not e['refs'][eng]:
        continue
    prefix, neg, num = m.groups()
    ident = -int(num) if neg else int(num)
    key = f'{ident}'
    if prefix:
        key = f'{prefix}{ident}'
    out[key] = e['refs'][eng]
json.dump(out, open(os.path.join(HERE, 'part_names.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'wrote part_names.json with {len(out)} entries')
for k in sorted(out)[:15]:
    print(f'  {k} => {out[k]}')
