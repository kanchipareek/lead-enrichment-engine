import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lead_enrichment.db"

conn = sqlite3.connect(DB)
print(f"{'config':<20}{'n':>4}{'TP':>4}{'FP':>4}{'FN':>4}{'TN':>4}{'prec':>7}{'recall':>8}")
for cfg, thr in conn.execute("SELECT config_name, threshold FROM icp_thresholds ORDER BY config_name"):
    rows = conn.execute(
        "SELECT score, human_label FROM scoring_eval WHERE config_name=? AND human_label IS NOT NULL",
        (cfg,)).fetchall()
    tp = fp = fn = tn = 0
    for score, lab in rows:
        qualified = score >= thr
        yes = (lab == "yes")
        if qualified and yes:
            tp += 1
        elif qualified and not yes:
            fp += 1
        elif not qualified and yes:
            fn += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    print(f"{cfg:<20}{n:>4}{tp:>4}{fp:>4}{fn:>4}{tn:>4}{prec:>7.2f}{rec:>8.2f}")

print("\ndisagreements (config verdict vs your label):")
any_d = False
for cfg, thr, cid, name, score, lab in conn.execute("""
    SELECT se.config_name, t.threshold, se.company_id, co.name, se.score, se.human_label
    FROM scoring_eval se
    JOIN companies co ON co.id = se.company_id
    JOIN icp_thresholds t ON t.config_name = se.config_name
    WHERE se.human_label IS NOT NULL
    ORDER BY se.config_name, se.score DESC"""):
    qualified = score >= thr
    yes = (lab == "yes")
    if qualified != yes:
        any_d = True
        kind = "qualified, but you said no (false positive)" if qualified else "missed a real fit (false negative)"
        print(f"  [{cfg}] {name} (score {int(score)}) - {kind}")
if not any_d:
    print("  none - the config agrees with every label in the sample")
