"""Print compact RSZ field tables (and enum values) from il2cpp_dump.json.

Usage: python dump_rsz.py <ClassName> [...]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_block import extract  # noqa: E402


def show(name):
    block = extract(name)
    if block is None:
        print(f'NOT FOUND: {name}')
        return
    obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
    cls = obj[name]
    print(f'===== {name} =====')
    rsz = cls.get('RSZ') or []
    if rsz:
        for f in rsz:
            arr = '[]' if f.get('array') else ''
            print(f"  {f.get('offset_from_fieldptr'):>6} {str(f.get('size')):>5} a{f.get('align')} "
                  f"{f.get('code') or f.get('type')}{arr}  {f.get('potential_name')}")
    else:
        print('  (no RSZ section)')
    fields = cls.get('fields') or {}
    if fields and not rsz:
        for k, v in list(fields.items())[:40]:
            print(f'  field {k}: {str(v)[:100]}')


if __name__ == '__main__':
    full = '--full' in sys.argv
    names = [n for n in sys.argv[1:] if not n.startswith('--')]
    if full:
        import dump_block
        allrsz = {}
        for n in names:
            block = dump_block.extract(n)
            obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
            allrsz[n] = obj[n].get('RSZ')
        print(json.dumps(allrsz, indent=1))
    else:
        for n in names:
            show(n)
