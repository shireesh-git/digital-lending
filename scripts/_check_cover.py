import pdfplumber
pdf = pdfplumber.open('output/test_rupee_fix.pdf')
p = pdf.pages[0]
text = p.extract_text() or ""
print("Full cover page text:")
print(text)
print(f"\nTotal chars: {len(p.chars)}")
# Check if INDIAN BANK is in chars
for c in sorted(p.chars, key=lambda c: (c['top'], c['x0']))[:10]:
    print(f"  y={c['top']:.1f} x={c['x0']:.1f} char='{c['text']}' size={c['size']:.1f}")
pdf.close()
