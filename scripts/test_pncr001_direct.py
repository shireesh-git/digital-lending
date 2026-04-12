"""Direct pipeline test — same code as the API route."""
import sys, os, traceback, asyncio, logging
logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.company_catalog import seed_company_store
from src.core.llm_provider import create_llm_provider
from src.agents.super_agent import SuperAgent
from src.core.config_manager import config

company_store = seed_company_store()
extraction_store = {}
etb_store = {}

entity_id = "PNCR001"
cd = company_store.get(entity_id)
if not cd:
    print("PNCR001 NOT in company_store!")
    sys.exit(1)

print(f"Company data_provider: {cd.get('data_provider')}")
print(f"Starting pipeline for {entity_id}...")

stores = {"extraction": extraction_store, "etb": etb_store}

try:
    llm = create_llm_provider(config.get_active_llm_provider())
    print(f"LLM provider: {llm}")
    sa = SuperAgent(llm_provider=llm)
    print("SuperAgent created, executing pipeline...")
    ctx = sa.execute_pipeline(cd, None, stores)
    print(f"Pipeline completed! Context keys: {list(ctx.keys()) if isinstance(ctx, dict) else type(ctx)}")
except Exception as e:
    print(f"\n\nPIPELINE ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
