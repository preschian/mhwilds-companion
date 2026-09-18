"""Finalize companion dataset: add category + icon filename, write repo JSON.

Usage: python finalize.py
Reads TEMP monsters.json + icons dir, writes repo data/monsters.json.
"""
import json
import os
import tempfile
import shutil

HERE = os.environ.get('MHRESEARCH', os.path.join(tempfile.gettempdir(), 'mhwilds-research'))
REPO = os.environ.get('MHREPO', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICONS = os.path.join(HERE, 'icons_png')


def category(em):
    n = int(em[2:])
    if em == 'EM1062':
        return 'debug'
    if em == 'EM0165':
        return 'gag'
    if n >= 5000:
        return 'endemic'
    if 1000 <= n < 2000:
        return 'small'
    return 'large'


def main():
    monsters = json.load(open(os.path.join(HERE, 'monsters.json'), encoding='utf-8'))
    have = {f.lower() for f in os.listdir(ICONS)}
    missing = []
    for m in monsters:
        m['category'] = category(m['em'])
        num = m['em'][2:]
        icon = f"tex_emicon_em{num}_{m['variant']}_0_imlm4.png"
        if icon in have:
            m['icon'] = icon.replace('tex_emicon_', 'tex_EmIcon_').replace('_imlm4', '_IMLM4')
            # restore exact case from disk
            for f in os.listdir(ICONS):
                if f.lower() == icon:
                    m['icon'] = f
                    break
        else:
            m['icon'] = None
            missing.append(f"{m['em']}_{m['variant']} {m['name']}")
    out = os.path.join(REPO, 'data', 'monsters.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(monsters, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'wrote {out} ({len(monsters)} entries)')
    print('missing icons:')
    for x in missing:
        print(f'  {x}')
    # Copy PNGs into repo (gitignored build artifacts).
    dest = os.path.join(REPO, 'data', 'icons')
    os.makedirs(dest, exist_ok=True)
    n = 0
    for f in os.listdir(ICONS):
        if f.endswith('.png'):
            shutil.copy2(os.path.join(ICONS, f), os.path.join(dest, f))
            n += 1
    print(f'copied {n} pngs to {dest}')


if __name__ == '__main__':
    main()
