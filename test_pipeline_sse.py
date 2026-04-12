"""Test SSE pipeline to verify DataIngestionAgent has real work."""
import http.client, json, sys

url = '/api/cases/BMFG001/run-stream'
conn = http.client.HTTPConnection('localhost', 8000, timeout=600)
conn.request('GET', url)
r = conn.getresponse()
events = []
buffer = ''
while True:
    chunk = r.read(1024)
    if not chunk:
        break
    buffer += chunk.decode('utf-8', errors='replace')
    while '\n' in buffer:
        line, buffer = buffer.split('\n', 1)
        line = line.strip()
        if not line or line.startswith(':'):
            continue
        if line.startswith('data: '):
            data = json.loads(line[6:])
        t = data.get('type')
        if t == 'info':
            msg = data.get('message', '')
            print(f'  INFO: {msg}')
        elif t == 'agent_start':
            agent = data.get('agent', '')
            desc = data.get('description', '')
            step = data.get('step', '')
            total = data.get('total', '')
            print(f'  AGENT START [{step}/{total}]: {agent} - {desc}')
        elif t == 'agent_complete':
            agent = data.get('agent', '')
            status = data.get('status', '')
            dur = data.get('duration_ms', 0)
            print(f'  AGENT DONE  [{data.get("step","")}/{data.get("total","")}]: {agent} - {status} - {dur}ms')
        elif t == 'section_start':
            title = data.get('title', data.get('section', ''))
            print(f'    SECTION START: {title} [{data.get("step","")}/{data.get("total","")}]')
        elif t == 'section_complete':
            title = data.get('title', data.get('section', ''))
            mode = data.get('mode', '')
            print(f'    SECTION DONE:  {title} [{data.get("step","")}/{data.get("total","")}] mode={mode}')
        elif t == 'done':
            rec = data.get('recommendation', '')
            grade = data.get('risk_grade', '')
            score = data.get('composite_score', '')
            mode = data.get('narrative_mode', '')
            print(f'  PIPELINE DONE: rec={rec}, grade={grade}, score={score}, mode={mode}')
            break
        elif t == 'error':
            msg = data.get('message', '')
            print(f'  ERROR: {msg}')
            break
        events.append(data)
        sys.stdout.flush()

conn.close()
print(f'\nTotal events: {len(events)}')

# Check data_ingestion timing
for e in events:
    if e.get('type') == 'agent_complete' and e.get('agent') == 'data_ingestion':
        dur = e.get('duration_ms', 0)
        print(f'data_ingestion duration: {dur}ms')
        if dur > 100:
            print('SUCCESS: DataIngestionAgent is now doing real work!')
        else:
            print('WARNING: DataIngestionAgent still too fast')
