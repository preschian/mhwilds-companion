"""Dump enum member maps {member: value} from il2cpp_dump.json fields.

Usage: python enum_dump.py <EnumClass> [...]  (prints JSON)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_block import extract  # noqa: E402

out = {}
for name in sys.argv[1:]:
    block = extract(name)
    obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
    fields = obj[name].get('fields') or {}
    out[name] = {k: v.get('default') for k, v in fields.items() if isinstance(v, dict) and 'default' in v}
print(json.dumps(out, indent=1))
