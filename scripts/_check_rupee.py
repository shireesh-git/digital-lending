import sqlite3, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db = sqlite3.connect('runtime-db/cam_platform.sqlite3')
db.row_factory = sqlite3.Row
tables = [t['name'] for t in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

# Look for CAM markdown in any likely table
for tbl in tables:
    cols = [c[1] for c in db.execute(f"PRAGMA table_info({tbl})").fetchall()]
    for col in cols:
        if 'cam' in col.lower() or 'markdown' in col.lower() or 'narrative' in col.lower():
            print(f"Found column: {tbl}.{col}")
            row = db.execute(f"SELECT {col} FROM {tbl} LIMIT 1").fetchone()
            if row and row[0]:
                text = str(row[0])
                print(f"  Length: {len(text)}")
                print(f"  Rupee chars (U+20B9): {text.count(chr(0x20B9))}")
                print(f"  Black squares (U+25A0): {text.count(chr(0x25A0))}")
                # Show first line with amount
                for line in text.split('\n')[:50]:
                    if 'Amount' in line or '1,500' in line or '1500' in line:
                        print(f"  Cover line: {repr(line)}")
                        break

db.close()
