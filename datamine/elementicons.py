"""Element/status icons: crop labeled cells from the ailment atlas.

Reads (from $MHRESEARCH):
  atlas_png/tex000201_2_IMLM4.png   ailment/buff atlas (100px grid, 20 cols)
Writes:
  $MHRESEARCH/icons_elements/*.png  staged crops (22 files)
  $MHRESEARCH/element_iconmap.json  name -> {cell, file}
  <repo>/data/icons/elements/*.png  dataset copies (game assets: private repo only)

Cell map (row, col), visually identified from the atlas:
  Row 0 holds the elements in WeaponDef.ATTR order (1 Fire .. 5 Dragon,
  matching RecoAttributeBit bit order) followed by the status icons.
  Row 2 holds element-res shields in the same element order, paired
  single/double up-arrow (Res Up Lv1/Lv2).
Requires: Pillow (pip install pillow).
"""
import json
import os
import shutil

from PIL import Image

HERE = os.environ.get('MHRESEARCH', os.path.join(__import__('tempfile').gettempdir(), 'mhwilds-research'))
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ATLAS = os.path.join(HERE, 'atlas_png', 'tex000201_2_IMLM4.png')
STAGE = os.path.join(HERE, 'icons_elements')

CELL = 100
COLS = 20

# name -> (row, col)
CELLS = {
    # Elements (row 0, ATTR order).
    'fire': (0, 0),
    'water': (0, 1),
    'thunder': (0, 2),
    'ice': (0, 3),
    'dragon': (0, 4),
    # Statuses (row 0).
    'poison': (0, 5),
    'frenzy': (0, 6),
    'paralysis': (0, 7),
    'stun': (0, 8),
    'sleep': (0, 9),
    'blast': (0, 10),
    'bleeding': (0, 11),
    # Element-res shields (row 2, single/double up-arrow pairs).
    'res_fire_1': (2, 8),
    'res_fire_2': (2, 9),
    'res_water_1': (2, 10),
    'res_water_2': (2, 11),
    'res_thunder_1': (2, 12),
    'res_thunder_2': (2, 13),
    'res_ice_1': (2, 14),
    'res_ice_2': (2, 15),
    'res_dragon_1': (2, 16),
    'res_dragon_2': (2, 17),
}


def main():
    atl = Image.open(ATLAS).convert('RGBA')
    assert atl.size[0] >= COLS * CELL, f'unexpected atlas size {atl.size}'
    os.makedirs(STAGE, exist_ok=True)
    dest = os.path.join(REPO, 'data', 'icons', 'elements')
    os.makedirs(dest, exist_ok=True)
    iconmap = {}
    for name, (r, c) in sorted(CELLS.items()):
        # Full 100x100 cells: the set needs uniform geometry for UI use
        # (unlike item glyphs, which ship as tight alpha-bbox crops).
        crop = atl.crop((c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL))
        bbox = crop.getchannel('A').getbbox()
        assert bbox is not None, f'empty cell for {name} r{r}c{c}'
        fn = f'{name}.png'
        crop.save(os.path.join(STAGE, fn))
        shutil.copy2(os.path.join(STAGE, fn), os.path.join(dest, fn))
        iconmap[name] = {'cell': [r, c], 'file': f'elements/{fn}',
                         'bbox': list(bbox)}
    json.dump(iconmap, open(os.path.join(HERE, 'element_iconmap.json'), 'w'),
              indent=1)
    print(f'cropped {len(iconmap)} icons -> {dest}')


if __name__ == '__main__':
    main()
