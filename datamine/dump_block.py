"""Extract top-level class blocks from il2cpp_dump.json by brace matching.

Usage: python dump_block.py <ClassName> [--methods-only] [--fields-only]
ClassName without quotes, e.g. app.EnemyReportDef
"""
import sys

GAME_DIR = os.environ.get('MHWILDS_GAME', r'D:\Program Files (x86)\Steam\steamapps\common\MonsterHunterWilds')
DUMP = os.path.join(GAME_DIR, 'il2cpp_dump.json')


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
        obj = json.loads('{' + block + '}')
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
