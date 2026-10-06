import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "data" / "lead_enrichment.db")

print("qualified per config:")
for cfg, n in c.execute("SELECT config_name, COUNT(*) FROM qualified GROUP BY config_name"):
    print(f"  {cfg}: {n}")

print("\nscore spread per config:")
for cfg, lo, hi, avg in c.execute("SELECT config_name, MIN(score), MAX(score), ROUND(AVG(score),1) FROM company_scores GROUP BY config_name"):
    print(f"  {cfg}: min {lo}, max {hi}, avg {avg}")

print("\nFLIPS (qualified in exactly one config):")
for cid, nm, a, b in c.execute("""
    SELECT a.company_id, co.name, a.score, b.score
    FROM company_scores a
    JOIN company_scores b ON a.company_id=b.company_id
    JOIN companies co ON co.id=a.company_id
    WHERE a.config_name='generic_b2b_saas' AND b.config_name='devtools_ai_infra'
      AND (
        (a.company_id IN (SELECT company_id FROM qualified WHERE config_name='generic_b2b_saas'))
        <>
        (b.company_id IN (SELECT company_id FROM qualified WHERE config_name='devtools_ai_infra'))
      )
    ORDER BY a.company_id"""):
    print(f"  {nm:<28} SaaS={a:>4}  DevTools={b:>4}")

print("\nscore_breakdown sample (why a company scored what it did):")
for cid, nm, feat, w, v in c.execute("""
    SELECT s.company_id, co.name, cfg.feature, cfg.weight, ft.value
    FROM company_scores s
    JOIN companies co ON co.id=s.company_id
    JOIN icp_configs cfg ON cfg.config_name=s.config_name
    JOIN company_features ft ON ft.company_id=s.company_id AND ft.feature=cfg.feature
    WHERE s.config_name='devtools_ai_infra' AND ft.value=1
    ORDER BY s.score DESC LIMIT 12"""):
    print(f"  {nm:<22} +{int(w)} ({feat})")
