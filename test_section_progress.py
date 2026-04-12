"""Quick test: verify section progress callbacks fire during LLM rendering."""
import time

events = []
def cb(ev):
    events.append(ev)
    etype = ev.get("type", "")
    section = ev.get("section", "")
    step = ev.get("step", "")
    total = ev.get("total", "")
    mode = ev.get("mode", "")
    print(f"  [{etype}] section={section} step={step}/{total} mode={mode}")

from src.core.config_manager import config
from src.core.llm_provider import create_llm_provider
from src.data.synthetic_companies import ALL_COMPANIES
company_store = dict(ALL_COMPANIES)
from src.engines.cam_fact_builder import build_cam_fact_pack

p = create_llm_provider(config.get_active_llm_provider())
print(f"Provider: {p.name if hasattr(p, 'name') else type(p)}")

cd = company_store.get("INFY001")
print("Building fact pack...")
fp = build_cam_fact_pack(cd)
print(f"Fact pack built, keys: {len(fp)}")

from src.engines.cam_llm_renderer import render_cam_with_llm
ns = config.get_narrative_settings()
print(f"Starting render_cam_with_llm (mode={ns.get('mode')})...")
t0 = time.time()
cam = render_cam_with_llm(
    fp, p,
    temperature=ns.get("temperature", 0.1),
    max_tokens_per_section=ns.get("max_tokens_per_section", 2500),
    on_section_progress=cb,
)
t1 = time.time()
print(f"\nDone in {t1-t0:.1f}s")
print(f"Total events: {len(events)}")
print(f"CAM length: {len(cam)} chars")
