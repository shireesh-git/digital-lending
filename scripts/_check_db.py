import sqlite3, json
conn = sqlite3.connect('runtime-db/cam_platform.sqlite3')
c = conn.cursor()
c.execute('SELECT entity_id, company_name, payload_json FROM companies WHERE entity_id=?', ('PNCR001',))
row = c.fetchone()
if row:
    payload = json.loads(row[2])
    print(f"entity_id={row[0]}, name={row[1]}")
    print(f"data_provider: {payload.get('data_provider')}")
    b = payload.get('borrower', {})
    print(f"borrower.cin: {b.get('cin')}")
    print(f"borrower.company_name: {b.get('company_name')}")
    print(f"borrower.subsector: {b.get('subsector')}")
else:
    print('PNCR001 not in DB')
