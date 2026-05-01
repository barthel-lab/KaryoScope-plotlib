# Migrating an existing script to karyoplot

This guide walks through replacing the duplicated patterns in a typical KaryoScope plotting script with `karyoplot` imports.

## 1. Font registration

**Before:**
```python
import matplotlib.font_manager as fm
from pathlib import Path

FONT_DIR = Path.home() / "Documents" / "Barthel-Custom-Powerpoint-Theme" / "fonts"
if FONT_DIR.exists():
    for font_file in FONT_DIR.glob("BasicSans-*.otf"):
        fm.fontManager.addfont(str(font_file))
    for font_file in FONT_DIR.glob("Bicyclette-*.otf"):
        fm.fontManager.addfont(str(font_file))
```

**After:**
```python
from karyoplot.core import fonts
fonts.register_fonts()
```

## 2. Color file loading

**Before:**
```python
colors = {}
with open(color_file) as f:
    for line in f:
        feat, hex_color = line.strip().split('\t')
        colors[feat] = hex_color
```

**After:**
```python
from karyoplot.core import colors
palette = colors.load_palette(color_file)
```

## 3. Chromosome sort

**Before:**
```python
def chrom_sort_key(c):
    c = c.replace('chr', '')
    if c == 'X': return 23
    if c == 'Y': return 24
    if c == 'M': return 25
    return int(c)
```

**After:**
```python
from karyoplot.core import chromosomes
sorted_chroms = sorted(chrom_list, key=chromosomes.chrom_sort_key)
```

## 4. Pixel-to-coordinate scaling

**Before:**
```python
pixels_per_pos = 4 / 1_000_000  # 4 px per Mb (full genome)
def pos_to_y(pos):
    return initial_y + floor(pos * pixels_per_pos)
```

**After:**
```python
from karyoplot.core.coords import PixelScale
scale = PixelScale(mode="full")  # or "subtelomere" / "centromere"
y = scale.pos_to_pixel(pos)
```

## 5. BED file loading

**Before:**
```python
import gzip
opener = gzip.open if path.endswith('.gz') else open
with opener(path, 'rt') as f:
    for line in f:
        chrom, start, end, name = line.strip().split('\t')[:4]
        ...
```

**After:**
```python
from karyoplot.core import io
df = io.load_bed(path, featureset="repeat")  # auto-detects gzip
```

## 6. SVG → PNG conversion

**Before:**
```python
import subprocess
subprocess.run(['rsvg-convert', '-z', '4', '-f', 'png',
                '-o', png_path, svg_path], check=True)
```

**After:**
```python
from karyoplot.svg import export
export.svg_to_png(svg_path, scale=4)
```

## See also

- `karyoplot/core/` for the full backend-agnostic API
- `karyoplot/svg/` for drawsvg helpers
- `karyoplot/mpl/` for matplotlib helpers
