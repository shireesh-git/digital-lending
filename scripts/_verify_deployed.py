import pdfplumber

pdf = pdfplumber.open(r'c:\Working\pncr001_cam_v2.pdf')
print(f"Pages: {len(pdf.pages)}")

# Check cover page (page 1)
p1 = pdf.pages[0]
text1 = p1.extract_text() or ""
print("\n--- COVER PAGE ---")
print(text1[:600])

# Count junk characters across all pages
total_rupee = 0
total_square = 0
total_rs = 0
for i, page in enumerate(pdf.pages):
    t = page.extract_text() or ""
    total_rupee += t.count("\u20b9")  # ₹
    total_square += t.count("\u25a0") # ■
    total_rs += t.count("Rs.")

print(f"\n--- SYMBOL CHECK ---")
print(f"₹ (U+20B9): {total_rupee}")
print(f"■ (U+25A0): {total_square}")
print(f"Rs.: {total_rs}")

# Check for text overlap on cover by looking at char positions
chars = sorted(p1.chars, key=lambda c: (c['top'], c['x0']))
# Find INDIAN BANK and Corporate Banking Division y positions  
bank_y = None
div_y = None
for c in chars:
    if c['text'] == 'I' and c['size'] > 20 and bank_y is None:
        bank_y = c['top']
    if c['text'] == 'C' and c['size'] == 11.0 and div_y is None:
        # "Corporate"
        div_y = c['top']
        
if bank_y and div_y:
    gap = div_y - bank_y
    print(f"\nINDIAN BANK y={bank_y:.1f}, Corporate Division y={div_y:.1f}")
    print(f"Gap: {gap:.1f}pt ({gap/2.835:.1f}mm) — {'OK' if gap > 30 else 'OVERLAP RISK'}")

pdf.close()
