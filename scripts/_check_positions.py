import pdfplumber
pdf = pdfplumber.open('output/test_rupee_fix.pdf')
p = pdf.pages[0]
chars = p.chars
# Group chars by y position (top)
lines = {}
for c in chars:
    y = round(c['top'], 0)
    if y not in lines:
        lines[y] = []
    lines[y].append(c)

# Print lines sorted by y position
for y in sorted(lines.keys()):
    text = ''.join(c['text'] for c in sorted(lines[y], key=lambda c: c['x0']))
    size = lines[y][0]['size']
    print(f"y={y:6.0f}  size={size:5.1f}  text={text[:60]}")

pdf.close()
