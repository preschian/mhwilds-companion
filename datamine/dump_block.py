"""Extract top-level class blocks from il2cpp_dump.json by brace matching.

Usage: python dump_block.py <ClassName> [--methods-only] [--fields-only]
ClassName without quotes, e.g. app.EnemyReportDef
"""
import json
import os
import sys
import tempfile

GAME_DIR = os.environ.get('MHWILDS_GAME', r'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds')
DUMP = os.path.join(GAME_DIR, 'il2cpp_dump.json')
RESEARCH = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
LAYOUT_CACHE = os.path.join(RESEARCH, 'rsz_layouts.json')
PARENT_CACHE = os.path.join(RESEARCH, 'rsz_parents.json')
_cache = None
_parents = None


def get_parent(name):
    """Base class name from the dump ('parent' field), cached."""
    global _parents
    if _parents is None:
        try:
            with open(PARENT_CACHE, encoding='utf-8') as f:
                _parents = json.load(f)
        except Exception:
            _parents = {}
    if name not in _parents:
        b = extract(name)
        _parents[name] = (json.loads('{' + b.rstrip().rstrip(',') + '}')[name].get('parent')
                          if b else None)
        try:
            with open(PARENT_CACHE, 'w', encoding='utf-8') as f:
                json.dump(_parents, f)
        except Exception:
            pass
    return _parents[name]


def is_derived(actual, expected):
    """True if actual == expected or inherits from it (dump parents)."""
    seen = set()
    while actual and actual not in seen:
        if actual == expected:
            return True
        seen.add(actual)
        actual = get_parent(actual)
    return False


def get_rsz(name):
    """RSZ field list for a class, via persistent cache (None if absent)."""
    global _cache
    if _cache is None:
        try:
            with open(LAYOUT_CACHE, encoding='utf-8') as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    if name not in _cache:
        b = extract(name)
        _cache[name] = json.loads('{' + b.rstrip().rstrip(',') + '}')[name].get('RSZ') if b else None
        try:
            with open(LAYOUT_CACHE, 'w', encoding='utf-8') as f:
                json.dump(_cache, f)
        except Exception:
            pass
    return _cache[name]


def extract(name):
    key = f'    "{name}": {{'
    with open(DUMP, 'r', encoding='utf-8') as f:
        # Stream until key found (keys are sorted? no — linear scan).
        while True:
            line = f.readline()
            if not line:
                return None
            if line.rstrip('\r\n') == key:
                break
        depth = 1
        out = [line]
        while depth > 0:
            line = f.readline()
            if not line:
                break
            # Count braces outside strings (good enough: no braces inside string values here).
            in_str, esc = False, False
            for ch in line:
                if esc:
                    esc = False
                    continue
                if ch == '\\':
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if not in_str:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
            out.append(line)
        return ''.join(out)


def main():
    name = sys.argv[1]
    block = extract(name)
    if block is None:
        print(f'NOT FOUND: {name}')
        return
    if '--methods-only' in sys.argv or '--fields-only' in sys.argv:
        import json
        obj = json.loads('{' + block.rstrip().rstrip(',') + '}')
        cls = obj[name]
        section = 'methods' if '--methods-only' in sys.argv else 'fields'
        print(f'== {name} :: {section} ({len(cls.get(section, {}))}) ==')
        for k in cls.get(section, {}):
            print(f'  {k}')
    else:
        print(block[:12000])
        if len(block) > 12000:
            print(f'... [truncated, total {len(block)} chars]')


if __name__ == '__main__':
    main()
