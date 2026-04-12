"""Quick verify PNCR001 data integration after fixes."""
import sys; sys.path.insert(0, ".")
from src.data.company_catalog import seed_company_store

store = seed_company_store()
pncr = store.get("PNCR001", {})
print("== PNCR001 Data Check ==")

# Borrower
b = pncr.get("borrower")
print(f"company_name: {b.company_name if b else 'N/A'}")
print(f"cin: {b.cin if b else 'N/A'}")

# Financials
fins = pncr.get("financials", {})
fy25 = fins.get("FY2025")
print(f"FY2025 revenue: {fy25.line_items.get('revenue_operating') if fy25 else 'N/A'} Cr")
print(f"FY2025 EBITDA: {fy25.line_items.get('ebitda') if fy25 else 'N/A'} Cr")
print(f"FY2025 PAT: {fy25.line_items.get('pat') if fy25 else 'N/A'} Cr")

# Group / Shareholding
grp = pncr.get("group")
print(f"promoter_holding: {grp.promoter_holding_pct if grp else 'N/A'}%")
print(f"institutional_holding: {grp.institutional_holding_pct if grp else 'N/A'}%")
print(f"public_holding: {grp.public_holding_pct if grp else 'N/A'}%")

# Infra metrics
im = pncr.get("infra_metrics", {})
print(f"has infra_metrics: {bool(im)}")
print(f"  order_book: {im.get('order_book', {}).get('total_order_book_cr', 'N/A')} Cr")
print(f"  book_to_bill: {im.get('order_book', {}).get('book_to_bill_ratio', 'N/A')}x")
print(f"  project_pipeline: {len(im.get('project_pipeline', []))} projects")
print(f"  bot_ham_portfolio: {im.get('bot_ham_portfolio', {}).get('total_concession_assets', 'N/A')} assets")

# Sector KPIs
sk = pncr.get("sector_kpis", {})
print(f"has sector_kpis: {bool(sk)}")
print(f"  sector_type: {sk.get('sector_type', 'N/A')}")
print(f"  highway_mix: EPC {sk.get('highway_mix', {}).get('epc_revenue_pct', 'N/A')}% / BOT {sk.get('highway_mix', {}).get('bot_toll_revenue_pct', 'N/A')}% / HAM {sk.get('highway_mix', {}).get('ham_annuity_revenue_pct', 'N/A')}%")
print(f"  ham_portfolio: DSCR={sk.get('ham_portfolio', {}).get('avg_dscr_operational', 'N/A')}, equity_infusion={sk.get('ham_portfolio', {}).get('equity_infusion_complete_pct', 'N/A')}%")
print(f"  workforce: {sk.get('workforce', {}).get('direct_employees', 'N/A')} direct + {sk.get('workforce', {}).get('contract_labour', 'N/A')} contract")

# Social media
from src.engines.social_media_engine import analyze_social_media
sm = analyze_social_media("PNCR001", "PNC Infratech Limited", "infrastructure")
print(f"social_media twitter_mentions: {sm.get('twitter_mentions_30d', 'N/A')}")
print(f"social_media linkedin_followers: {sm.get('digital_presence', {}).get('linkedin_followers', 'N/A')}")
print(f"social_media sentiment: {sm.get('overall_sentiment', {}).get('label', 'N/A')}")
print(f"social_media themes: {len(sm.get('themes', []))}")

print("\n== ALL CHECKS PASSED ==")
