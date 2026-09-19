"""Weapon-type icons: crop white glyphs from the map/equipment atlas.

Reads (from $MHRESEARCH):
  atlas_png/tex000201_1_IMLM4.png   map/equipment atlas (100px grid, 20 cols)
Writes:
  $MHRESEARCH/icons_weapons/*.png   staged crops (14 files)
  $MHRESEARCH/weapon_iconmap.json   name -> {cell, file, wtype}
  <repo>/data/icons/weapons/*.png   dataset copies (game assets: private repo only)

Cell map: row 16 cols 6-19 hold the 14 white weapon glyphs, each
visually identified by its silhouette (zoom-verified). Atlas order is
NOT WeaponDef.TYPE order (artists laid out SnS/GS and Lance/Hammer
pairs swapped); wtype below pins each glyph to its TYPE value:
  LONG_SWORD 0 = Great Sword, SHORT_SWORD 1 = Sword & Shield,
  TWIN_SWORD 2 = Dual Blades, TACHI 3 = Long Sword, HAMMER 4,
  WHISTLE 5 = Hunting Horn, LANCE 6, GUN_LANCE 7, SLASH_AXE 8 =
  Switch Axe, CHARGE_AXE 9 = Charge Blade, ROD 10 = Insect Glaive,
  BOW 11, HEAVY_BOWGUN 12, LIGHT_BOWGUN 13.
Glyphs ship white (the game tints them), full 100x100 cells for uniform
UI geometry. Row 7's colored octagons are equipment-category tabs, not
weapon types, and are intentionally left out.
Requires: Pillow (pip install pillow).
"""
import json
import os
import shutil

from PIL import Image

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ATLAS = os.path.join(HERE, 'atlas_png', 'tex000201_1_IMLM4.png')
STAGE = os.path.join(HERE, 'icons_weapons')

CELL = 100
COLS = 20

# name -> ((row, col), WeaponDef.TYPE value)
CELLS = {
    'sword_shield': ((16, 6), 1),
    'great_sword': ((16, 7), 0),
    'long_sword': ((16, 8), 3),
    'dual_blades': ((16, 9), 2),
    'lance': ((16, 10), 6),
    'gunlance': ((16, 11), 7),
    'hammer': ((16, 12), 4),
    'hunting_horn': ((16, 13), 5),
    'switch_axe': ((16, 14), 8),
    'charge_blade': ((16, 15), 9),
    'insect_glaive': ((16, 16), 10),
    'bow': ((16, 17), 11),
    'heavy_bowgun': ((16, 18), 12),
    'light_bowgun': ((16, 19), 13),
}


def main():
    atl = Image.open(ATLAS).convert('RGBA')
    assert atl.size[0] >= COLS * CELL, f'unexpected atlas size {atl.size}'
    os.makedirs(STAGE, exist_ok=True)
    dest = os.path.join(REPO, 'data', 'icons', 'weapons')
    os.makedirs(dest, exist_ok=True)
    iconmap = {}
    for name, ((r, c), wtype) in sorted(CELLS.items()):
        crop = atl.crop((c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL))
        bbox = crop.getchannel('A').getbbox()
        assert bbox is not None, f'empty cell for {name} r{r}c{c}'
        fn = f'{name}.png'
        crop.save(os.path.join(STAGE, fn))
        shutil.copy2(os.path.join(STAGE, fn), os.path.join(dest, fn))
        iconmap[name] = {'cell': [r, c], 'file': f'weapons/{fn}',
                         'wtype': wtype, 'bbox': list(bbox)}
    json.dump(iconmap, open(os.path.join(HERE, 'weapon_iconmap.json'), 'w'),
              indent=1)
    print(f'cropped {len(iconmap)} icons -> {dest}')


if __name__ == '__main__':
    main()
