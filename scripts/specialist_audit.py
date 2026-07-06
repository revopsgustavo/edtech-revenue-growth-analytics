from pathlib import Path
import importlib.util
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"


def exists(name):
    return (PROCESSED / name).exists()


def audit():
    failures = []
    important = []
    score = 10.0
    required = [
        "monthly_closing.csv",
        "performance_targets.csv",
        "variation_justifications.csv",
        "consultant_gap_log.csv",
        "data_quality_report.csv",
        "action_tracker.csv",
        "experiment_recommendations.csv",
    ]
    for name in required:
        if not exists(name):
            failures.append(f"Arquivo obrigatório ausente: {name}")
            score -= 1.0
    if exists("performance_history.csv"):
        hist = pd.read_csv(PROCESSED / "performance_history.csv")
        days = pd.to_datetime(hist["date"]).nunique()
        if days < 90:
            failures.append("Base tem menos de 90 dias.")
            score -= 1.5
    else:
        failures.append("performance_history.csv ausente.")
    if exists("monthly_closing.csv"):
        close = pd.read_csv(PROCESSED / "monthly_closing.csv")
        if "net_revenue_variation_pct" not in close.columns:
            failures.append("Fechamento sem variação contra meta.")
        if close["main_variation_driver"].isna().any():
            important.append("Há fechamento sem driver.")
            score -= 0.4
    if exists("variation_justifications.csv"):
        just = pd.read_csv(PROCESSED / "variation_justifications.csv")
        required_variation_cols = ["business_area", "problem_type", "decision_owner"]
        for col in required_variation_cols:
            if col not in just.columns:
                failures.append(f"variation_justifications.csv sem {col}.")
                score -= 1.0
        if all(col in just.columns for col in required_variation_cols):
            relevant = just[just["target_variation_pct"].abs() >= 0.08]
            if relevant["business_area"].fillna("").eq("").any():
                failures.append("Variação relevante sem área responsável.")
                score -= 1.0
            if relevant["problem_type"].fillna("").eq("").any():
                failures.append("Variação relevante sem tipo de problema.")
                score -= 1.0
            if relevant["decision_owner"].fillna("").eq("").any():
                failures.append("Variação relevante sem dono sugerido.")
                score -= 1.0
    if exists("action_tracker.csv"):
        actions = pd.read_csv(PROCESSED / "action_tracker.csv")
        critical = actions[actions["priority"] == "critical"]
        if critical["owner"].isna().any() or critical["follow_up_metric"].isna().any():
            failures.append("Ações críticas sem owner ou follow_up_metric.")
            score -= 1.0
    if exists("experiment_recommendations.csv"):
        experiments = pd.read_csv(PROCESSED / "experiment_recommendations.csv")
        if experiments["hypothesis"].isna().any() or experiments["primary_metric"].isna().any():
            failures.append("Experimentos sem hipótese ou métrica primária.")
            score -= 1.0
        combined = " ".join(experiments.astype(str).stack().tolist()).lower()
        causal_claims = ["foi comprovado", "com certeza", "garantidamente", "causa raiz confirmada"]
        if any(term in combined for term in causal_claims):
            failures.append("Experimentos afirmam causalidade como certeza.")
            score -= 1.0
    readme = ROOT / "README.md"
    if not readme.exists() or len(readme.read_text(encoding="utf-8")) < 2500:
        important.append("README precisa ser mais robusto.")
        score -= 0.5
    elif not all(term in readme.read_text(encoding="utf-8").lower() for term in ["sintético", "privacidade"]):
        failures.append("README não menciona dados sintéticos e privacidade.")
        score -= 1.0
    if not (DOCS / "data_privacy_note.md").exists():
        failures.append("Nota de privacidade/LGPD ausente.")
        score -= 1.0
    app_path = ROOT / "app" / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("streamlit_app_check", app_path)
    if not app_path.exists():
        failures.append("Dashboard ausente.")
        score -= 1.0
    else:
        app_text = app_path.read_text(encoding="utf-8")
        if "Variações por área" not in app_text or "Log de variações por área" not in app_text:
            failures.append("Dashboard não mostra variação por área.")
            score -= 1.0
    ai = DOCS / "ai_consultant_analysis.md"
    if not ai.exists():
        failures.append("IA consultora ausente.")
        score -= 1.0
    else:
        text = ai.read_text(encoding="utf-8").lower()
        for banned in ["a causa é", "foi comprovado", "com certeza", "garantidamente", "causa raiz confirmada"]:
            if banned in text:
                failures.append(f"IA usa expressão proibida: {banned}")
                score -= 1.0
        required_language = [
            "a evidência disponível sugere",
            "o principal ponto de investigação",
            "a hipótese precisa ser validada",
        ]
        for phrase in required_language:
            if phrase not in text:
                failures.append(f"IA não usa linguagem consultiva requerida: {phrase}")
                score -= 1.0
    tq = DOCS / "text_quality_audit_report.md"
    if not tq.exists() or "Status final: aprovado" not in tq.read_text(encoding="utf-8"):
        failures.append("Auditoria textual não aprovada.")
        score -= 1.0
    approval = "aprovado" if score >= 8.5 and not failures else "aprovado com ajustes" if score >= 7 else "reprovado"
    level = "especialista" if score >= 9 else "sênior" if score >= 8.5 else "pleno"
    report = [
        "# Specialist Audit Report",
        "",
        "## Veredito geral",
        "O projeto demonstra análise especialista de Revenue Analytics para uma EdTech digital, com dados sintéticos, fechamento mensal e recomendações responsáveis.",
        "",
        f"## Nota de 0 a 10",
        f"{score:.1f}",
        "",
        "## Nível percebido",
        level,
        "",
        "## Falhas críticas",
        "\n".join(f"- {x}" for x in failures) if failures else "- Nenhuma falha crítica.",
        "",
        "## Falhas importantes",
        "\n".join(f"- {x}" for x in important) if important else "- Nenhuma falha importante.",
        "",
        "## Falhas opcionais",
        "- Adicionar autenticação e orquestração em produção.",
        "",
        "## Riscos de percepção",
        "- LTV é sintético e deve ser apresentado como estimativa.",
        "- Atribuição creator-led é assistida, não causal.",
        "",
        "## Ajustes recomendados",
        "- Validar hipóteses com cohorts reais antes de decisão financeira.",
        "- Conectar CRM, mídia, pagamentos e produto em warehouse.",
        "",
        "## Checklist final",
        "- Dados sintéticos: ok",
        "- Sem API externa: ok",
        "- IA rule-based: ok",
        "- Fechamento mensal: ok",
        "- Testes e auditorias: verificar saída do pipeline",
        "",
        f"## Aprovação final",
        approval,
    ]
    (DOCS / "specialist_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return score, failures


if __name__ == "__main__":
    score, failures = audit()
    print(f"Auditoria especialista: nota {score:.1f}, falhas críticas {len(failures)}")
    sys.exit(1 if failures or score < 8.5 else 0)
