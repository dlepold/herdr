"""Render the smoke test's plain terminal captures as a comparison image.

Usage: python3 render-demo.py CAPTURE_DIRECTORY OUTPUT.png
Requires Pillow and the DejaVu Sans Mono font.
"""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

captures = Path(sys.argv[1])
output = Path(sys.argv[2])
font_root = Path('/usr/share/fonts/truetype/dejavu')
font = ImageFont.truetype(str(font_root / 'DejaVuSansMono.ttf'), 20)
bold = ImageFont.truetype(str(font_root / 'DejaVuSansMono-Bold.ttf'), 20)
caption = ImageFont.truetype(str(font_root / 'DejaVuSans.ttf'), 15)
image = Image.new('RGB', (768, 632), '#11111b')
draw = ImageDraw.Draw(image)
for x, label, filename in [
    (24, 'Counts off', 'smoke-demo-before.txt'),
    (400, 'Counts on (default)', 'smoke-demo-after.txt'),
]:
    draw.text((x, 18), label, font=bold, fill='#cdd6f4')
    draw.rounded_rectangle((x, 53, x + 344, 578), radius=8, fill='#1e1e2e', outline='#45475a')
    lines = (captures / filename).read_text().splitlines()[:21]
    for index, line in enumerate(lines):
        text = line[:25].rstrip()
        heading = text.startswith((' spaces', ' agents'))
        draw.text((x + 16, 66 + index * 24), text,
                  font=bold if heading else font,
                  fill='#9399b2' if heading else '#cdd6f4')
draw.text((24, 596), 'Rendered from isolated live terminal captures. Sample agent uses test metadata.',
          font=caption, fill='#a6adc8')
image.save(output)
