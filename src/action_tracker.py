from datetime import timedelta
import pandas as pd

try:
    from .utils import read_csv, save_csv, DOCS
except ImportError:
    from utils import read_csv, save_csv, DOCS

PRIORITIES = {"critical", "high", "medium", "low"}
STATUSES = {"not_started", "in_progress", "done", "blocked"}


def priority_from_gap(severity):
    if severity == "high":
        return "critical"
    if severity == "medium":
        return "high"
    return "medium"


def status_from_priority(priority):
    if priority == "critical":
        return "in_progress"
    if priority == "high":
        return "not_started"
    return "not_started"


def build_gap_actions(gaps, start_date):
    rows = []
    for _, gap in gaps.iterrows():
        priority = priority_from_gap(gap["severity"])
        due_days = 7 if priority == "critical" else 14 if priority == "high" else 30
        rows.append({
            "action_id": f"act_{len(rows) + 1:04d}",
            "month": "",
            "business_area": gap.get("business_area", gap["area"]),
            "problem_type": gap.get("problem_type", gap["metric"]),
            "recommended_action": gap["recommended_action"],
            "owner": gap.get("decision_owner", gap["owner"]),
            "priority": priority,
            "due_date": (start_date + timedelta(days=due_days)).date().isoformat(),
            "expected_impact": gap["expected_impact"],
            "follow_up_metric": gap["follow_up_metric"],
            "status": status_from_priority(priority),
        })
    return rows


def build_variation_actions(justifications, start_id, start_date):
    rows = []
    relevant = justifications[justifications["target_variation_pct"].abs() >= 0.08].copy()
    for _, item in relevant.iterrows():
        priority = "high" if abs(item["target_variation_pct"]) >= 0.15 else "medium"
        due_days = 10 if priority == "high" else 21
        rows.append({
            "action_id": f"act_{start_id + len(rows):04d}",
            "month": item["month"],
            "business_area": item.get("business_area", item["owner"]),
            "problem_type": item.get("problem_type", item["metric"]),
            "recommended_action": item["action_taken"],
            "owner": item.get("decision_owner", item["owner"]),
            "priority": priority,
            "due_date": (start_date + timedelta(days=due_days)).date().isoformat(),
            "expected_impact": f"Reduzir gap de {item['metric']} no próximo fechamento.",
            "follow_up_metric": item["follow_up_metric"],
            "status": "not_started",
        })
    return rows


def write_summary(actions):
    critical = actions[actions["priority"] == "critical"]
    by_area = actions["business_area"].value_counts()
    by_status = actions["status"].value_counts()
    metrics = sorted(actions["follow_up_metric"].dropna().unique())
    lines = [
        "# Resumo do Plano de Ação",
        "",
        "## Resumo das ações",
        f"Foram geradas {len(actions)} ações mensuráveis a partir dos gaps consultivos e das variações relevantes de fechamento.",
        "",
        "## Ações críticas",
    ]
    if critical.empty:
        lines.append("- Nenhuma ação crítica aberta.")
    else:
        for _, row in critical.iterrows():
            lines.append(f"- {row.action_id}: {row.recommended_action} Responsável: {row.owner}. Métrica: {row.follow_up_metric}.")
    lines += ["", "## Ações por área"]
    lines += [f"- {area}: {count}" for area, count in by_area.items()]
    lines += ["", "## Ações por status"]
    lines += [f"- {status}: {count}" for status, count in by_status.items()]
    lines += ["", "## Métricas de acompanhamento"]
    lines += [f"- {metric}" for metric in metrics]
    lines += [
        "",
        "## Próximos passos recomendados",
        "- Executar ações críticas nos próximos 7 dias.",
        "- Revisar ações high no ritual semanal de Growth, Sales Ops e Revenue Governance.",
        "- Validar impacto por métrica no próximo fechamento mensal.",
    ]
    (DOCS / "action_tracker_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_action_tracker():
    gaps = read_csv("consultant_gap_log.csv")
    justifications = read_csv("variation_justifications.csv")
    start_date = pd.Timestamp.today().normalize()
    rows = build_gap_actions(gaps, start_date)
    rows.extend(build_variation_actions(justifications, len(rows) + 1, start_date))
    actions = pd.DataFrame(rows)
    actions = actions.drop_duplicates(subset=["business_area", "problem_type", "recommended_action"])
    save_csv(actions, "action_tracker.csv")
    write_summary(actions)
    return actions


if __name__ == "__main__":
    result = generate_action_tracker()
    print(f"Action tracker gerado: {len(result)} ações")
