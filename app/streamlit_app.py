import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from action_tracker import generate_action_tracker
from ai_consultant import generate_analysis
from consultant_gap_finder import find_gaps
from data_quality import run_quality_checks
from experiment_recommendations import generate_experiments
from generate_data import main as generate_synthetic_data
from lead_scoring import apply_lead_scoring
from metrics import summarize_channel_performance
from monthly_closing import main as generate_monthly_closing
from reports import generate_reports
from utils import PROCESSED, brl, br_multiple, br_number, br_pct, safe_div

st.set_page_config(page_title="EdTech Revenue Growth Analytics", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        font-size: clamp(1.25rem, 1.7vw, 1.8rem);
        white-space: normal;
        overflow: visible;
        line-height: 1.15;
    }
    [data-testid="stMetricLabel"] {
        white-space: normal;
    }
    .block-container {
        padding-top: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("EdTech Revenue Growth Analytics")
st.caption("Dashboard executivo para análise de funil, eficiência de canais, CAC, LTV/CAC, conversão e oportunidades de receita.")


@st.cache_data
def load_data():
    required_files = {
        "performance_history.csv",
        "monthly_closing.csv",
        "consultant_gap_log.csv",
        "action_tracker.csv",
        "experiment_recommendations.csv",
        "variation_justifications.csv",
        "leads.csv",
        "funnel_events.csv",
        "campaigns.csv",
        "free_class_events.csv",
        "content_events.csv",
        "students.csv",
        "student_activation.csv",
        "learning_engagement.csv",
        "expansion_opportunities.csv",
    }
    missing_files = [name for name in required_files if not (PROCESSED / name).exists()]
    if missing_files:
        generate_synthetic_data()
        apply_lead_scoring()
        generate_monthly_closing()
        run_quality_checks()
        find_gaps()
        generate_action_tracker()
        generate_experiments()
        generate_analysis()
        generate_reports()
    return {file.stem: pd.read_csv(file) for file in PROCESSED.glob("*.csv")}


def chart(fig, height=420):
    fig.update_layout(height=height, margin=dict(l=28, r=24, t=66, b=48), legend_title_text="")
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    st.plotly_chart(fig, use_container_width=True)


def kpi_card(container, label, value):
    container.markdown(
        f"""
        <div style="border:1px solid rgba(255,255,255,.08); border-radius:8px; padding:14px 16px; min-height:92px; background:rgba(255,255,255,.03);">
            <div style="font-size:.86rem; opacity:.82; margin-bottom:8px;">{label}</div>
            <div style="font-size:clamp(1.25rem,1.65vw,1.75rem); font-weight:650; line-height:1.15; overflow-wrap:anywhere;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def executive_block(item, title):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        cols = st.columns(2)
        cols[0].markdown(f"**Diagnóstico:** {display_term(item.get('problem_type', item.get('metric', '')))}")
        cols[0].markdown(f"**Evidência:** {display_term(item.get('evidence', ''))}")
        cols[0].markdown(f"**Hipótese:** {display_term(item.get('likely_hypothesis', item.get('hypothesis', '')))}")
        cols[1].markdown(f"**Recomendação:** {display_term(item.get('recommended_action', ''))}")
        cols[1].markdown(f"**Área responsável:** {display_term(item.get('decision_owner', item.get('owner', '')))}")
        cols[1].markdown(f"**Métrica de acompanhamento:** {display_term(item.get('follow_up_metric', item.get('primary_metric', '')))}")


def consultant_priority_block(title, diagnosis, impact, recommendation, owner):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        cols = st.columns(2)
        cols[0].markdown(f"**Diagnóstico:** {diagnosis}")
        cols[0].markdown(f"**Impacto:** {impact}")
        cols[1].markdown(f"**Recomendação:** {recommendation}")
        cols[1].markdown(f"**Área responsável:** {owner}")


def action_priority_block(item, title):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        cols = st.columns(2)
        cols[0].markdown(f"**Tipo de problema:** {display_term(item.get('problem_type', ''))}")
        cols[0].markdown(f"**Impacto esperado:** {display_term(item.get('expected_impact', ''))}")
        cols[0].markdown(f"**Prioridade:** {display_term(item.get('priority', ''))}")
        cols[1].markdown(f"**Ação recomendada:** {display_term(item.get('recommended_action', ''))}")
        cols[1].markdown(f"**Responsável:** {display_term(item.get('owner', ''))}")
        cols[1].markdown(f"**Status:** {display_term(item.get('status', ''))}")


def first_existing_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def score_band(value):
    if pd.isna(value):
        return "Sem score"
    value = float(value)
    if value <= 20:
        return "0–20"
    if value <= 40:
        return "21–40"
    if value <= 60:
        return "41–60"
    if value <= 80:
        return "61–80"
    return "81–100"


def build_funnel_view(stages):
    rows = []
    lead_volume = next(iter(stages.values()), 0)
    previous_volume = None
    non_sequential = False
    for stage, volume in stages.items():
        if previous_volume is None:
            conversion = 1
            dropoff = 0
        else:
            conversion = safe_div(volume, previous_volume)
            if conversion > 1:
                non_sequential = True
            conversion = min(conversion, 1)
            dropoff = max(1 - conversion, 0)
        rows.append(
            {
                "Etapa": stage,
                "Volume": volume,
                "Conversão etapa anterior": conversion,
                "Drop-off etapa anterior": dropoff,
                "Conversão acumulada vs Lead": min(safe_div(volume, lead_volume), 1),
            }
        )
        previous_volume = volume
    return pd.DataFrame(rows), non_sequential


def format_funnel_table(df):
    view = df.copy()
    view["Volume"] = view["Volume"].map(lambda value: br_number(value, 0))
    for col in ["Conversão etapa anterior", "Drop-off etapa anterior", "Conversão acumulada vs Lead"]:
        view[col] = view[col].map(br_pct)
    return view


def value_fmt(metric, value):
    if metric in {"net_revenue", "spend", "cac", "cpl", "expansion_revenue"}:
        return brl(value)
    if metric in {"roi", "roas", "activation_rate", "retention_proxy"}:
        return br_pct(value)
    if metric == "ltv_cac":
        return br_multiple(value)
    return br_number(value, 2)


def format_table(df, money_cols=None, pct_cols=None, number_cols=None, multiple_cols=None, rename=None):
    view = df.copy()
    for col in money_cols or []:
        if col in view.columns:
            view[col] = view[col].map(brl)
    for col in pct_cols or []:
        if col in view.columns:
            view[col] = view[col].map(br_pct)
    for col in number_cols or []:
        if col in view.columns:
            view[col] = view[col].map(lambda value: br_number(value, 0))
    for col in multiple_cols or []:
        if col in view.columns:
            view[col] = view[col].map(format_br_multiple)
    if rename:
        view = view.rename(columns=rename)
    return translate_dataframe(view)


def br_plot_value(value, kind=None):
    if kind == "money":
        return brl(value)
    if kind == "pct":
        return br_pct(value)
    if kind == "multiple":
        return br_multiple(value, 2)
    if kind == "number":
        return br_number(value, 0)
    return str(value)


def numeric_axis_values(fig, axis):
    values = []
    for trace in fig.data:
        raw_values = getattr(trace, axis, None)
        if raw_values is None:
            continue
        for value in raw_values:
            if isinstance(value, (int, float)) and not pd.isna(value):
                values.append(float(value))
    return values


def apply_axis_ticks(fig, axis_name, kind):
    if kind is None:
        return
    values = numeric_axis_values(fig, axis_name)
    if not values:
        return
    low, high = min(values), max(values)
    if low == high:
        ticks = [low]
    else:
        step_count = 4
        ticks = [low + (high - low) * i / step_count for i in range(step_count + 1)]
    ticktext = [br_plot_value(value, kind) for value in ticks]
    if axis_name == "x":
        fig.update_xaxes(tickmode="array", tickvals=ticks, ticktext=ticktext)
    else:
        fig.update_yaxes(tickmode="array", tickvals=ticks, ticktext=ticktext)


def apply_hover_template(fig, x_kind=None, y_kind=None):
    for trace in fig.data:
        raw_x = getattr(trace, "x", None)
        raw_y = getattr(trace, "y", None)
        x_values = list(raw_x) if raw_x is not None else []
        y_values = list(raw_y) if raw_y is not None else []
        if not x_values or not y_values or len(x_values) != len(y_values):
            continue
        formatted = [
            [br_plot_value(x, x_kind) if x_kind else str(x), br_plot_value(y, y_kind) if y_kind else str(y)]
            for x, y in zip(x_values, y_values)
        ]
        trace.customdata = formatted
        trace.hovertemplate = "%{customdata[0]}<br>%{customdata[1]}<extra>%{fullData.name}</extra>"


def executive_chart(fig, height=420, x_kind=None, y_kind=None):
    apply_axis_ticks(fig, "x", x_kind)
    apply_axis_ticks(fig, "y", y_kind)
    apply_hover_template(fig, x_kind=x_kind, y_kind=y_kind)
    if any(getattr(trace, "type", "") in {"bar", "histogram"} for trace in fig.data):
        fig.update_yaxes(rangemode="tozero")
    chart(fig, height=height)


FRIENDLY_NAMES = {
    "action_id": "ID da ação",
    "actual_value": "Realizado",
    "analyst_justification": "Justificativa",
    "area": "Área",
    "business_area": "Área de negócio",
    "business_context": "Contexto de negócio",
    "cac": "CAC",
    "campaign_id": "ID da campanha",
    "campaign_name": "Campanha",
    "channel": "Canal",
    "click_rate": "Taxa de clique",
    "closing_status": "Status do fechamento",
    "conversion": "Conversão",
    "cpl": "CPL",
    "created_at": "Criado em",
    "current_value": "Valor atual",
    "decision_owner": "Responsável pela decisão",
    "detected_driver": "Driver detectado",
    "dropoff": "Drop-off",
    "due_date": "Prazo",
    "engagement_rate": "Taxa de engajamento",
    "engagement_score": "Score de engajamento",
    "enrollments": "Matrículas",
    "escalation_level": "Nível de escalonamento",
    "evidence": "Evidência",
    "expected_impact": "Impacto esperado",
    "expected_value": "Valor esperado",
    "experiment_id": "ID do experimento",
    "experiment_name": "Experimento",
    "experiment_type": "Tipo de experimento",
    "expansion_revenue": "Receita de expansão",
    "follow_up_metric": "Métrica de acompanhamento",
    "gap_id": "ID do gap",
    "hypothesis": "Hipótese",
    "justification_id": "ID da justificativa",
    "leads": "Leads",
    "likely_hypothesis": "Hipótese provável",
    "ltv_cac": "LTV/CAC",
    "metric": "Métrica",
    "minimum_success_criteria": "Critério mínimo de sucesso",
    "missing_evidence": "Evidência ausente",
    "mom_variation_abs": "Variação abs. vs mês anterior",
    "mom_variation_pct": "Variação % vs mês anterior",
    "month": "Mês",
    "net_revenue": "Receita líquida",
    "owner": "Responsável",
    "previous_month_value": "Valor mês anterior",
    "primary_metric": "Métrica primária",
    "priority": "Prioridade",
    "problem_type": "Tipo de problema",
    "recommended_action": "Ação recomendada",
    "recommended_review_meeting": "Ritual sugerido",
    "responsible_team": "Time responsável",
    "retention_proxy": "Proxy de retenção",
    "risk": "Risco",
    "roas": "ROAS",
    "roi": "ROI",
    "secondary_metric": "Métrica secundária",
    "severity": "Severidade",
    "spend": "Investimento",
    "status": "Status",
    "target_segment": "Segmento-alvo",
    "target_value": "Meta",
    "target_variation_abs": "Variação absoluta",
    "target_variation_pct": "Variação contra meta",
    "urgency": "Urgência",
    "validation_question": "Pergunta de validação",
}

COLUMN_LABELS = {
    "Investmento": "Investimento",
    "investment": "Investimento",
    "Investment": "Investimento",
    "investimento": "Investimento",
    "Investimento": "Investimento",
    "Leads": "Leads",
    "leads": "Leads",
    "mqls": "MQLs",
    "MQLs": "MQLs",
    "enrollments": "Matrículas",
    "Matrículas": "Matrículas",
    "net_revenue": "Receita líquida",
    "Receita líquida": "Receita líquida",
    "expected_ltv": "LTV esperado",
    "activation_rate": "Taxa de ativação",
    "engagement_score": "Pontuação de engajamento",
    "retention_proxy": "Indicador de retenção",
    "expansion_revenue": "Receita de expansão",
    "CPL": "CPL",
    "cpl": "CPL",
    "CAC": "CAC",
    "cac": "CAC",
    "ROI": "ROI",
    "roi": "ROI",
    "ROAS": "ROAS",
    "roas": "ROAS",
    "LTV/CAC": "LTV/CAC",
    "ltv_cac": "LTV/CAC",
    "channel": "Canal",
    "channel_display": "Canal",
    "Canal": "Canal",
}

METRIC_OPTIONS = [
    "net_revenue",
    "spend",
    "leads",
    "enrollments",
    "cac",
    "cpl",
    "roi",
    "roas",
    "ltv_cac",
    "activation_rate",
    "engagement_score",
    "retention_proxy",
    "expansion_revenue",
]

FRIENDLY_NAMES["activation_rate"] = "Taxa de ativação"

TERM_TRANSLATIONS = {
    "critical": "crítica",
    "high": "alta",
    "medium": "média",
    "low": "baixa",
    "open": "aberta",
    "not_started": "não iniciada",
    "in_progress": "em andamento",
    "proposed": "proposta",
    "behind": "abaixo da meta",
    "ahead": "acima da meta",
    "lead to enrollment": "lead para matrícula",
    "show-up rate": "taxa de presença",
    "show-up": "presença",
    "activation rate": "taxa de ativação",
    "retention proxy": "proxy de retenção",
    "expansion revenue": "receita de expansão",
    "activation in 7 days": "ativação em 7 dias",
    "activation_rate": "taxa de ativação",
    "engagement_score": "score de engajamento",
    "retention_proxy": "proxy de retenção",
    "net_revenue": "receita líquida",
    "spend": "investimento",
    "actual_value": "realizado",
    "target_value": "meta",
    "target_variation_pct": "variação contra meta",
    "target_miss": "Meta não atingida",
    "acquisition_efficiency": "Eficiência de aquisição",
    "event_attendance": "Presença em aula gratuita",
    "funnel_conversion": "Conversão final em matrícula",
    "sales_sla": "SLA comercial",
    "campaign_roi": "ROI de campanhas",
    "content_performance": "Performance de conteúdo",
    "activation_gap": "Gap de ativação",
    "engagement_gap": "Gap de engajamento",
    "retention_risk": "Risco de retenção",
    "expansion_opportunity": "Oportunidade de expansão",
    "crm_reactivation": "Reativação CRM",
    "data_quality": "Qualidade de dados",
    "pricing_discount": "Preço e desconto",
    "margin_pressure": "Pressão de margem",
    "mixed_driver": "Driver multifuncional",
    "Sales Ops": "Operações Comerciais",
    "Mixed / Cross-functional": "Misto / Multifuncional",
    "Sales / Growth": "Comercial / Growth",
    "Sales / SDR Team": "Comercial / SDR",
    "SDR Team": "Time de SDR",
    "CRM / Lifecycle": "CRM / Ciclo de vida",
    "Creator / Influencer": "Criadores / Influenciadores",
    "Finance / Revenue + Paid Media": "Finanças / Receita + Mídia paga",
    "Growth / Paid Media": "Growth / Mídia paga",
    "Revenue / Growth": "Receita / Growth",
    "Data Engineering / Analytics": "Engenharia de Dados / Analytics",
    "Content / Events": "Conteúdo / Eventos",
    "Líder de Sales Ops": "Líder de Operações Comerciais",
    "Growth Ops": "Operações de Growth",
    "Data Governance": "Governança de Dados",
    "Data Lead": "Líder de Dados",
    "CPL vs conversion": "CPL vs conversão",
    "CRM-assisted enrollment": "matrícula assistida por CRM",
    "conversion_to_enrollment": "Conversão em matrícula",
    "revenue_vs_cac": "Receita vs CAC",
    "quality_variance": "Variação de qualidade",
    "leads_vs_enrollments": "Leads vs matrículas",
    "trial_scheduled_to_attended": "Aula agendada vs presença",
    "free_class_attendance": "Presença em aula gratuita",
    "data_completeness": "Completude dos dados",
    "P1 SLA": "SLA P1",
    "data completeness": "completude de dados",
    "free class attendance": "presença em aula gratuita",
    "leads vs enrollments": "leads vs matrículas",
    "quality variance": "variação de qualidade",
    "revenue vs CAC": "receita vs CAC",
    "trial scheduled to attended": "aula agendada vs presença",
    "Revenue Leadership": "Liderança de Receita",
    "Revenue Governance": "Governança de Receita",
    "Expected Expansion Revenue": "Receita esperada de expansão",
    "Expected Revenue": "Receita esperada",
    "Gross Revenue": "Receita bruta",
    "Net Revenue": "Receita líquida",
    "Revenue": "Receita",
    "Paid Search": "Busca paga",
    "Paid Social": "Social pago",
    "Organic Search": "Busca orgânica",
    "Organic Social": "Social orgânico",
    "Referral": "Indicação",
    "Creator-led Content": "Conteúdo com criadores",
    "Free Classes / Events": "Aulas gratuitas / eventos",
    "Direct": "Direto",
    "Email": "E-mail",
    "YouTube": "YouTube",
    "Instagram": "Instagram",
    "TikTok": "TikTok",
    "Influencer": "Influenciadores",
    "Creators": "Criadores",
    "Creator": "Criador",
    "Paid Media": "Mídia paga",
    "Organic / Content": "Orgânico / Conteúdo",
    "Data Engineering": "Engenharia de Dados",
    "Customer Experience": "Experiência do Cliente",
    "Commercial": "Comercial",
    "Lifecycle": "Ciclo de vida",
    "Content": "Conteúdo",
    "Events": "Eventos",
    "Data": "Dados",
    "Analytics": "Analytics",
    "CX": "CX",
    "Marketing": "Marketing",
    "WhatsApp": "WhatsApp",
    "Product": "Produto",
    "Product / CX": "Produto / CX",
    "CX / Student Success": "CX / Sucesso do Aluno",
    "Data / Tracking": "Dados / Tracking",
    "Finance / Revenue": "Finanças / Receita",
    "Marketing + Sales + CX": "Marketing + Comercial + CX",
    "Growth": "Growth",
    "Sales": "Comercial",
    "Campaigns": "Campanhas",
    "Campaign": "Campanha",
    "Spend": "Investimento",
    "Investment": "Investimento",
    "Enrollments": "Matrículas",
    "Qualified Leads": "Leads qualificados",
    "Leads": "Leads",
    "Conversion Rate": "Taxa de conversão",
    "Conversion": "Conversão",
    "Cost per Lead": "Custo por lead",
    "Cost": "Custo",
    "Channel Group": "Grupo de canal",
    "Channel": "Canal",
    "Source": "Origem",
    "Medium": "Mídia",
    "Intent": "Intenção",
    "Show-up": "Presença",
    "Attendance": "Presença",
    "Free Class": "Aula gratuita",
    "Trial Scheduled": "Trial agendado",
    "Trial": "Aula experimental",
    "Activated Enrollment": "Matrícula ativada",
    "Activation": "Ativação",
    "Retention": "Retenção",
    "Churn": "Churn",
    "Upsell": "Upsell",
    "Expansion": "Expansão",
    "High": "Alta",
    "Medium": "Média",
    "Low": "Baixa",
    "Open": "Aberto",
    "In Progress": "Em andamento",
    "Done": "Concluído",
    "Blocked": "Bloqueado",
    "Critical": "Crítico",
    "Warning": "Atenção",
    "Opportunity": "Oportunidade",
    "Risk": "Risco",
    "Monthly Business Review": "Ritual mensal de receita",
    "Weekly Sales Pipeline Review": "Ritual semanal de pipeline comercial",
    "Sales Ops SLA Review": "Ritual de SLA comercial",
    "Growth Weekly": "Ritual semanal de Growth",
    "Product and CX Review": "Ritual de Produto e CX",
    "CX Health Review": "Ritual de saúde da base",
    "Retention Review": "Ritual de retenção",
    "Revenue Expansion Review": "Ritual de expansão de receita",
    "Data Quality Review": "Ritual de qualidade de dados",
    "Click rate": "taxa de clique",
    "click rate": "taxa de clique",
}


def display_term(value):
    if pd.isna(value):
        return ""
    text = str(value)
    exact = TERM_TRANSLATIONS.get(text)
    if exact:
        return exact
    translated = text
    for source, target in TERM_TRANSLATIONS.items():
        translated = translated.replace(source, target)
    if translated != text:
        return translated
    if "_" in text:
        cleaned = text.replace("_", " ").title()
        for source, target in TERM_TRANSLATIONS.items():
            cleaned = cleaned.replace(source, target)
        return cleaned
    return translated


def translate_series(series):
    return series.apply(display_term)


def rename_display_columns(df):
    out = df.copy()
    out.columns = [COLUMN_LABELS.get(col, display_term(col)) for col in out.columns]
    return out


def format_brl(value):
    if pd.isna(value):
        return ""
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_br_int(value):
    if pd.isna(value):
        return ""
    return f"{int(round(float(value))):,}".replace(",", ".")


def format_br_pct(value):
    if pd.isna(value):
        return ""
    value = float(value)
    if abs(value) <= 1:
        value = value * 100
    return f"{value:.1f}%".replace(".", ",")


def format_br_decimal(value, casas=1):
    if pd.isna(value):
        return ""
    return f"{float(value):.{casas}f}".replace(".", ",")


def format_br_score(value):
    if pd.isna(value):
        return ""
    return f"{float(value):.1f}".replace(".", ",")


def format_br_multiple(value):
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}x".replace(".", ",")


def format_channel_table(df):
    out = df.copy()
    replicated_cols = ["activation_rate", "retention_proxy", "expected_ltv", "expansion_revenue"]
    for col in replicated_cols:
        if col in out.columns and out[col].nunique(dropna=True) <= 1:
            out = out.drop(columns=[col])

    preferred_order = [
        "channel_display",
        "spend",
        "leads",
        "mqls",
        "enrollments",
        "net_revenue",
        "expected_ltv",
        "engagement_score",
        "expansion_revenue",
        "cpl",
        "cac",
        "roi",
        "roas",
        "ltv_cac",
    ]
    ordered_cols = [col for col in preferred_order if col in out.columns]
    out = out[ordered_cols + [col for col in out.columns if col not in ordered_cols]]
    out = rename_display_columns(out)

    currency_cols = ["Investimento", "Receita líquida", "LTV esperado", "Receita de expansão", "CPL", "CAC"]
    int_cols = ["Leads", "MQLs", "Matrículas"]
    pct_cols = ["Taxa de ativação", "Indicador de retenção", "ROI"]
    score_cols = ["Pontuação de engajamento"]
    multiple_cols = ["LTV/CAC", "ROAS"]

    for col in currency_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_brl)
    for col in int_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_br_int)
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_br_pct)
    for col in score_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_br_score)
    for col in multiple_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_br_multiple)
    return out


def render_table_with_left_align(df, left_align_cols=None, height=None):
    left_align_cols = left_align_cols or []
    valid_cols = [col for col in left_align_cols if col in df.columns]
    styler = df.style
    if valid_cols:
        styler = styler.set_properties(subset=valid_cols, **{"text-align": "left"})
    st.dataframe(styler, use_container_width=True, hide_index=True, height=height)


def sorted_display_options(series):
    return sorted(series.dropna().unique(), key=lambda value: display_term(value))


def translate_dataframe(df):
    view = df.copy()
    for col in view.select_dtypes(include=["object"]).columns:
        view[col] = view[col].map(display_term)
    return view


def friendly_name(name):
    return FRIENDLY_NAMES.get(name, str(name).replace("_", " ").title())


def rename_friendly(df):
    return translate_dataframe(df.rename(columns={col: friendly_name(col) for col in df.columns}))


def format_metric_series(df, metric_col="metric"):
    view = df.copy()
    if metric_col in view.columns:
        view[metric_col] = view[metric_col].map(friendly_name)
    return translate_dataframe(view)


def format_variation_table(df):
    view = format_metric_series(df.copy())
    for col in ["actual_value", "target_value", "target_variation_abs", "previous_month_value", "mom_variation_abs"]:
        if col in view.columns:
            view[col] = [value_fmt(metric, value) for metric, value in zip(df["metric"], view[col])]
    for col in ["target_variation_pct", "mom_variation_pct"]:
        if col in view.columns:
            view[col] = view[col].map(br_pct)
    return rename_friendly(view)


def format_closing_history(df, metric):
    view = df[["month", f"{metric}_target", f"{metric}_actual", f"{metric}_variation_abs", f"{metric}_variation_pct"]].copy()
    view[f"{metric}_target"] = view[f"{metric}_target"].map(lambda value: value_fmt(metric, value))
    view[f"{metric}_actual"] = view[f"{metric}_actual"].map(lambda value: value_fmt(metric, value))
    view[f"{metric}_variation_abs"] = view[f"{metric}_variation_abs"].map(lambda value: value_fmt(metric, value))
    view[f"{metric}_variation_pct"] = view[f"{metric}_variation_pct"].map(br_pct)
    return view.rename(
        columns={
            "month": "Mês",
            f"{metric}_target": "Meta",
            f"{metric}_actual": "Realizado",
            f"{metric}_variation_abs": "Variação absoluta",
            f"{metric}_variation_pct": "Variação contra meta",
        }
    )


def build_monthly_fallback(month, metric, row):
    return pd.DataFrame(
        [
            {
                "justification_id": f"fallback_{month}_{metric}",
                "month": month,
                "metric": metric,
                "business_area": "Revenue Leadership",
                "problem_type": "Variação do mês sem justificativa detalhada cadastrada.",
                "actual_value": row[f"{metric}_actual"],
                "target_value": row[f"{metric}_target"],
                "target_variation_abs": row[f"{metric}_variation_abs"],
                "target_variation_pct": row[f"{metric}_variation_pct"],
                "detected_driver": "Variação do mês sem justificativa detalhada cadastrada.",
                "analyst_justification": "Variação do mês sem justificativa detalhada cadastrada.",
                "action_taken": "Registrar causa raiz, responsável e plano de ação no fechamento mensal.",
                "decision_owner": "Revenue Leadership",
                "responsible_team": "Revenue Leadership",
                "recommended_review_meeting": "Monthly Business Review",
                "follow_up_metric": metric,
                "status": "Pendente de detalhamento",
            }
        ]
    )


data = load_data()
history = data["performance_history"]
closing = data["monthly_closing"]
gaps = data.get("consultant_gap_log", pd.DataFrame())
actions = data.get("action_tracker", pd.DataFrame())
experiments = data.get("experiment_recommendations", pd.DataFrame())
leads = data["leads"]
funnel = data["funnel_events"]
campaigns = data["campaigns"]
events = data["free_class_events"]
content = data["content_events"]
students = data["students"]
activation = data["student_activation"]
engagement = data["learning_engagement"]
expansion = data["expansion_opportunities"]

selected_page = st.sidebar.radio(
    "Página",
    [
        "Visão executiva",
        "Funil e conversão",
        "Canais e CAC/LTV",
        "Campanhas e criadores",
        "Fechamento mensal",
        "Consultor rule-based",
        "Apêndice analítico",
    ],
)

page_map = {
    "Funil e conversão": "Diagnóstico do funil",
    "Canais e CAC/LTV": "Performance por canal",
    "Fechamento mensal": "Histórico e fechamento mensal",
}
page = page_map.get(selected_page, selected_page)
if selected_page == "Campanhas e criadores":
    page = st.sidebar.radio("Análise", ["ROI de campanhas", "Criadores e aulas gratuitas"])
if selected_page == "Apêndice analítico":
    page = st.sidebar.radio("Análise", ["Insights de segmentação", "Priorização de leads", "Produto e retenção"])

if page == "Visão executiva":
    total_revenue = history.net_revenue.sum()
    total_spend = history.spend.sum()
    enrollments = history.enrollments.sum()
    cac = safe_div(total_spend, enrollments)
    ltv_cac = safe_div(history.expected_ltv.sum() / max(enrollments, 1), cac)

    st.info(
        "A operação tem tração de receita, mas parte do investimento está concentrada em canais que geram volume sem eficiência final. "
        "A recomendação é rebalancear mídia por CAC, LTV/CAC e conversão em matrícula ativada."
    )
    d1, d2, d3, d4 = st.columns(4)
    kpi_card(d1, "O que aconteceu?", "Receita próxima da meta, com pressão de eficiência em ciclos específicos.")
    kpi_card(d2, "Por que importa?", "Volume sem matrícula aumenta CAC, consome verba e reduz produtividade comercial.")
    kpi_card(d3, "Decisão recomendada", "Rebalancear investimento por receita qualificada, CAC, LTV/CAC e conversão final.")
    kpi_card(d4, "Quem age?", "Marketing, Comercial, CRM, Produto, CX e Liderança de Receita.")
    st.divider()

    cols = st.columns(4)
    kpi_card(cols[0], "Receita líquida", brl(total_revenue))
    kpi_card(cols[1], "Investimento", brl(total_spend))
    kpi_card(cols[2], "CAC", brl(cac))
    kpi_card(cols[3], "LTV/CAC", br_multiple(ltv_cac, 2))
    cols = st.columns(4)
    kpi_card(cols[0], "Payback", f"{br_number(history.payback_months.replace([float('inf')], 0).mean(), 1)} meses")
    kpi_card(cols[1], "Matrículas", br_number(enrollments, 0))
    kpi_card(cols[2], "ROI", br_pct(safe_div(total_revenue - total_spend, total_spend)))
    kpi_card(cols[3], "Atingimento da receita", br_pct(safe_div(closing.net_revenue_actual.sum(), closing.net_revenue_target.sum())))

    st.subheader("Alertas e recomendações")
    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "Risco", "Social pago concentra volume, mas opera com CAC acima dos canais de intenção.")
    kpi_card(c2, "Oportunidade", "Indicação apresenta LTV/CAC superior e baixo investimento relativo.")
    kpi_card(c3, "Ação recomendada", "Rebalancear verba e aplicar SLA P1 para leads com maior propensão à matrícula.")
    executive_revenue = closing[["month", "net_revenue_actual", "net_revenue_target"]].rename(
        columns={"month": "Mês", "net_revenue_actual": "Realizado", "net_revenue_target": "Meta"}
    )
    executive_chart(px.line(executive_revenue, x="Mês", y=["Realizado", "Meta"], title="Receita líquida: meta vs realizado", labels={"value": "Receita líquida", "variable": "Série"}), y_kind="money")

elif page == "Diagnóstico do funil":
    free_class_stages = {
        "Lead": funnel.lead_date.notna().sum(),
        "Inscrição aula": funnel.free_class_registration_date.notna().sum(),
        "Presença": funnel.attendance_date.notna().sum(),
        "Oferta": funnel.offer_date.notna().sum(),
        "Matrícula": funnel.enrollment_date.notna().sum(),
        "Ativação": funnel.activation_date.notna().sum(),
    }
    sales_stages = {
        "Lead": funnel.lead_date.notna().sum(),
        "MQL": funnel.mql_date.notna().sum(),
        "Contato": funnel.sales_contact_date.notna().sum(),
        "Trial agendado": funnel.trial_class_date.notna().sum(),
        "Matrícula": funnel.enrollment_date.notna().sum(),
        "Ativação": funnel.activation_date.notna().sum(),
    }
    free_class_df, free_class_non_sequential = build_funnel_view(free_class_stages)
    sales_df, sales_non_sequential = build_funnel_view(sales_stages)
    if free_class_non_sequential or sales_non_sequential:
        st.warning("Etapas não sequenciais detectadas. Revise a composição do funil.")

    st.subheader("Funil de conversão por jornada")
    st.caption(
        "A leitura foi separada por jornada para evitar mistura entre qualificação comercial e participação em aula gratuita. "
        "Isso torna os gargalos de conversão mais claros e acionáveis."
    )
    cols = st.columns(4)
    kpi_card(cols[0], "Leads", br_number(free_class_stages["Lead"], 0))
    kpi_card(cols[1], "Matrículas", br_number(free_class_stages["Matrícula"], 0))
    kpi_card(cols[2], "Lead para matrícula", br_pct(safe_div(free_class_stages["Matrícula"], free_class_stages["Lead"])))
    kpi_card(cols[3], "Ativação pós-matrícula", br_pct(safe_div(free_class_stages["Ativação"], free_class_stages["Matrícula"])))

    st.subheader("Jornada de aula gratuita")
    free_class_fig = px.funnel(free_class_df, x="Volume", y="Etapa", title="Jornada de aula gratuita: volume por etapa", labels={"Volume": "Volume", "Etapa": "Etapa"})
    free_class_fig.update_traces(text=free_class_df["Volume"].map(format_br_int), texttemplate="%{text}", textposition="inside")
    executive_chart(free_class_fig, x_kind="number")
    st.dataframe(format_funnel_table(free_class_df), use_container_width=True, hide_index=True)

    st.subheader("Jornada comercial")
    sales_fig = px.funnel(sales_df, x="Volume", y="Etapa", title="Jornada comercial: volume por etapa", labels={"Volume": "Volume", "Etapa": "Etapa"})
    sales_fig.update_traces(text=sales_df["Volume"].map(format_br_int), texttemplate="%{text}", textposition="inside")
    executive_chart(sales_fig, x_kind="number")
    st.dataframe(format_funnel_table(sales_df), use_container_width=True, hide_index=True)
    st.info("Gargalos prioritários: inscrição para presença em aula gratuita e avanço comercial entre MQL, contato e trial agendado.")

elif page == "Performance por canal":
    channels = summarize_channel_performance(history)
    channels["channel_display"] = translate_series(channels["channel"])
    best_ltv = channels.sort_values("ltv_cac", ascending=False).iloc[0]
    best_revenue = channels.sort_values("net_revenue", ascending=False).iloc[0]
    low_cac = channels[channels.enrollments > 0].sort_values("cac", ascending=True).iloc[0]
    cols = st.columns(3)
    kpi_card(cols[0], "Maior receita", f"{best_revenue.channel_display}<br>{brl(best_revenue.net_revenue)}")
    kpi_card(cols[1], "Melhor LTV/CAC", f"{best_ltv.channel_display}<br>{br_multiple(best_ltv.ltv_cac, 2)}")
    kpi_card(cols[2], "Menor CAC", f"{low_cac.channel_display}<br>{brl(low_cac.cac)}")
    executive_chart(px.bar(channels, x="channel_display", y="net_revenue", color="ltv_cac", title="Receita líquida e LTV/CAC por canal", labels={"channel_display": "Canal", "net_revenue": "Receita líquida", "ltv_cac": "LTV/CAC"}), y_kind="money")
    executive_chart(px.scatter(channels, x="cac", y="net_revenue", size="leads", color="channel_display", title="Receita vs CAC", labels={"cac": "CAC", "net_revenue": "Receita líquida", "leads": "Leads", "channel_display": "Canal"}), x_kind="money", y_kind="money")
    channel_table = channels.drop(columns=["channel"]).sort_values("ltv_cac", ascending=False)
    st.dataframe(
        format_channel_table(channel_table),
        use_container_width=True,
        hide_index=True,
    )

elif page == "ROI de campanhas":
    camp = history.groupby("campaign_id", as_index=False).agg(
        spend=("spend", "sum"),
        leads=("leads", "sum"),
        enrollments=("enrollments", "sum"),
        net_revenue=("net_revenue", "sum"),
    )
    camp = camp.merge(campaigns[["campaign_id", "campaign_name", "channel"]], on="campaign_id", how="left")
    camp["channel_display"] = translate_series(camp["channel"])
    camp["campaign_display"] = camp["campaign_id"].map(display_term)
    camp["cpl"] = camp.spend / camp.leads.replace(0, pd.NA)
    camp["cac"] = camp.spend / camp.enrollments.replace(0, pd.NA)
    camp["roi"] = (camp.net_revenue - camp.spend) / camp.spend.replace(0, pd.NA)
    camp["roas"] = camp.net_revenue / camp.spend.replace(0, pd.NA)
    cpl_threshold = camp["cpl"].quantile(0.35)
    cac_threshold = camp["cac"].quantile(0.65)
    bad_quality = camp[(camp["cpl"] <= cpl_threshold) & (camp["cac"] >= cac_threshold)].sort_values("cac", ascending=False)
    scale_gap = camp[camp.enrollments > 0].sort_values(["cac", "spend"]).head(10)
    cols = st.columns(3)
    kpi_card(cols[0], "Campanhas avaliadas", br_number(len(camp), 0))
    kpi_card(cols[1], "Receita total", brl(camp.net_revenue.sum()))
    kpi_card(cols[2], "ROI médio", br_pct(camp.roi.mean()))
    executive_chart(px.scatter(camp, x="spend", y="net_revenue", color="channel_display", size="leads", hover_name="campaign_name", title="Investimento vs receita por campanha", labels={"spend": "Investimento", "net_revenue": "Receita líquida", "channel_display": "Canal", "leads": "Leads"}), x_kind="money", y_kind="money")
    table_cols = ["campaign_display", "campaign_name", "channel_display", "spend", "leads", "enrollments", "net_revenue", "cpl", "cac", "roi", "roas"]
    rename_campaign = {"campaign_display": "ID", "campaign_name": "Campanha", "channel_display": "Canal", "spend": "Investimento", "leads": "Leads", "enrollments": "Matrículas", "net_revenue": "Receita líquida", "cpl": "CPL", "cac": "CAC", "roi": "ROI", "roas": "ROAS"}
    st.subheader("Campanhas com CPL bom e CAC ruim")
    st.dataframe(format_table(bad_quality[table_cols].head(10), money_cols=["spend", "net_revenue", "cpl", "cac"], pct_cols=["roi"], multiple_cols=["roas"], rename=rename_campaign), use_container_width=True)
    st.subheader("Campanhas com CAC bom e escala baixa")
    scale_gap_table = format_table(scale_gap[table_cols], money_cols=["spend", "net_revenue", "cpl", "cac"], pct_cols=["roi"], multiple_cols=["roas"], rename=rename_campaign)
    render_table_with_left_align(scale_gap_table, left_align_cols=["Investimento", "Leads"])

elif page == "Criadores e aulas gratuitas":
    content["engagement_rate"] = (content.likes + content.comments + content.shares) / content.views.replace(0, pd.NA)
    content["click_rate"] = content.clicks / content.views.replace(0, pd.NA)
    creator_summary = content.groupby("creator_id", as_index=False).agg(leads=("leads_generated", "sum"), views=("views", "sum"), engagement_rate=("engagement_rate", "mean"), click_rate=("click_rate", "mean")).sort_values("leads", ascending=False).head(12)
    creator_summary["creator_display"] = creator_summary["creator_id"].map(display_term)
    events_view = events.assign(
        revenue_per_attendee=events.revenue_generated / events.attendees.replace(0, pd.NA),
        event_conversion=events.enrollments / events.attendees.replace(0, pd.NA),
    )
    cols = st.columns(4)
    kpi_card(cols[0], "Leads por criadores", br_number(content.leads_generated.sum(), 0))
    kpi_card(cols[1], "Presença média", br_pct(events.show_up_rate.mean()))
    kpi_card(cols[2], "Receita de eventos", brl(events.revenue_generated.sum()))
    kpi_card(cols[3], "Receita por participante", brl(events_view.revenue_per_attendee.mean()))
    executive_chart(px.bar(creator_summary, x="creator_display", y="leads", title="Criadores por geração de leads", labels={"creator_display": "Criador", "leads": "Leads"}), y_kind="number")
    executive_chart(px.bar(events, x="event_name", y="show_up_rate", color="revenue_generated", title="Taxa de presença e receita por aula gratuita", labels={"event_name": "Aula gratuita", "show_up_rate": "Taxa de presença", "revenue_generated": "Receita"}), height=500, y_kind="pct")
    st.subheader("Performance de criadores")
    st.dataframe(format_table(creator_summary.drop(columns=["creator_id"]), pct_cols=["engagement_rate", "click_rate"], number_cols=["leads", "views"], rename={"creator_display": "Criador", "leads": "Leads", "views": "Visualizações", "engagement_rate": "Engajamento", "click_rate": "Taxa de clique"}), use_container_width=True)
    st.subheader("Performance de aulas gratuitas")
    free_class_table = format_table(events_view, money_cols=["revenue_generated", "revenue_per_attendee"], pct_cols=["show_up_rate", "event_conversion"], number_cols=["registrations", "attendees", "enrollments"], rename={"event_id": "ID", "event_name": "Evento", "language_interest": "Idioma", "event_date": "Data", "registrations": "Inscrições", "attendees": "Presentes", "show_up_rate": "Taxa de presença", "offer_presented": "Ofertas", "enrollments": "Matrículas", "revenue_generated": "Receita", "revenue_per_attendee": "Receita por participante", "event_conversion": "Conversão do evento"})
    render_table_with_left_align(free_class_table, left_align_cols=["Ofertas"])

elif page == "Insights de segmentação":
    seg = leads.merge(funnel[["lead_id", "enrollment_date"]], on="lead_id", how="left")
    lang = seg.groupby("language_interest", as_index=False).agg(leads=("lead_id", "count"), enrollments=("enrollment_date", lambda s: s.notna().sum()))
    lang["conversion"] = lang.enrollments / lang.leads
    goal = seg.groupby("stated_goal", as_index=False).agg(leads=("lead_id", "count"), enrollments=("enrollment_date", lambda s: s.notna().sum()))
    goal["conversion"] = goal.enrollments / goal.leads
    executive_chart(px.bar(lang, x="language_interest", y="conversion", title="Conversão por idioma de interesse", labels={"language_interest": "Idioma", "conversion": "Conversão"}), y_kind="pct")
    executive_chart(px.bar(goal, x="stated_goal", y="conversion", title="Conversão por objetivo declarado", labels={"stated_goal": "Objetivo declarado", "conversion": "Conversão"}), height=500, y_kind="pct")
    st.info("Segmentos com maior intenção e baixo investimento devem entrar no próximo ciclo de priorização.")

elif page == "Priorização de leads":
    dist = leads.priority_tier.value_counts().reset_index()
    dist.columns = ["tier", "leads"]
    p1 = leads[leads.priority_tier == "P1"]
    cols = st.columns(4)
    kpi_card(cols[0], "Leads P1", br_number(len(p1), 0))
    kpi_card(cols[1], "SLA mediano P1", f"{br_number(p1.first_response_minutes.median(), 0)} min")
    kpi_card(cols[2], "Score médio", br_number(leads.lead_score.mean(), 1))
    kpi_card(cols[3], "Leads com responsável", br_pct(leads.assigned_to_sales.notna().mean()))
    chart(px.pie(dist, names="tier", values="leads", title="Distribuição de leads por prioridade"))
    tier = leads.merge(funnel[["lead_id", "enrollment_date"]], on="lead_id", how="left").groupby("priority_tier", as_index=False).agg(
        leads=("lead_id", "count"),
        conversion=("enrollment_date", lambda s: s.notna().mean()),
        sla=("first_response_minutes", "median"),
    )
    st.dataframe(format_table(tier, pct_cols=["conversion"], number_cols=["leads", "sla"], rename={"priority_tier": "Tier", "leads": "Leads", "conversion": "Conversão", "sla": "SLA mediano (min)"}), use_container_width=True)
    st.success("Recomendação: P1 deve ter SLA de 15 minutos, roteamento automático e cadência WhatsApp.")

elif page == "Produto e retenção":
    cols = st.columns(4)
    kpi_card(cols[0], "Taxa de ativação", br_pct((activation.activation_status == "activated").mean()))
    kpi_card(cols[1], "Tempo até primeira aula", f"{br_number(activation.days_to_first_class.mean(), 1)} dias")
    kpi_card(cols[2], "Score de engajamento", br_number(engagement.engagement_score.mean(), 1))
    kpi_card(cols[3], "Risco de churn", br_number(students.churn_risk_score.mean(), 1))
    executive_chart(px.histogram(activation, x="classes_watched_7d", title="Ativação em 7 dias: aulas assistidas", labels={"classes_watched_7d": "Aulas assistidas em 7 dias"}), x_kind="number")
    st.subheader("Expansão: receita esperada por faixa de score")
    st.caption("A priorização fica mais clara por faixas: scores altos devem concentrar maior potencial médio ou maior volume financeiro. A leitura executiva é por grupo, não por ponto individual.")
    score_col = first_existing_column(expansion, ["upsell_score", "score_upsell", "expansion_score", "score"])
    revenue_col = first_existing_column(expansion, ["expected_expansion_revenue", "expansion_expected_revenue", "expected_revenue", "receita_expansao_esperada"])
    if score_col is None or revenue_col is None:
        st.info("Dados de score e receita esperada não disponíveis para esta visualização.")
    else:
        band_order = ["0–20", "21–40", "41–60", "61–80", "81–100"]
        band_rank = {band: index for index, band in enumerate(band_order)}
        expansion_view = expansion[[score_col, revenue_col]].copy()
        expansion_view["Faixa de score"] = expansion_view[score_col].map(score_band)
        band_summary = (
            expansion_view.groupby("Faixa de score", as_index=False)
            .agg(
                Oportunidades=(revenue_col, "size"),
                **{
                    "Receita esperada total": (revenue_col, "sum"),
                    "Receita esperada média": (revenue_col, "mean"),
                    "Score médio": (score_col, "mean"),
                },
            )
            .assign(_rank=lambda df: df["Faixa de score"].map(band_rank).fillna(len(band_order)))
            .sort_values("_rank")
            .drop(columns="_rank")
        )
        if band_summary.empty:
            st.info("Dados de score e receita esperada não disponíveis para esta visualização.")
        else:
            chart_view = band_summary.copy()
            chart_view["Oportunidades formatadas"] = chart_view["Oportunidades"].map(lambda value: br_number(value, 0))
            chart_view["Receita total formatada"] = chart_view["Receita esperada total"].map(brl)
            chart_view["Receita média formatada"] = chart_view["Receita esperada média"].map(brl)
            chart_view["Score médio formatado"] = chart_view["Score médio"].map(lambda value: br_number(value, 1))
            fig = px.bar(
                chart_view,
                x="Faixa de score",
                y="Receita esperada total",
                custom_data=["Oportunidades formatadas", "Receita total formatada", "Receita média formatada", "Score médio formatado"],
                title="Receita esperada total por faixa de score",
                labels={"Faixa de score": "Faixa de score", "Receita esperada total": "Receita esperada total"},
            )
            fig.update_traces(
                hovertemplate=(
                    "Faixa de score: %{x}<br>"
                    "Oportunidades: %{customdata[0]}<br>"
                    "Receita esperada total: %{customdata[1]}<br>"
                    "Receita esperada média: %{customdata[2]}<br>"
                    "Score médio: %{customdata[3]}<extra></extra>"
                )
            )
            fig.update_yaxes(rangemode="tozero")
            apply_axis_ticks(fig, "y", "money")
            chart(fig)
            table_view = band_summary.copy()
            table_view["Oportunidades"] = table_view["Oportunidades"].map(lambda value: br_number(value, 0))
            table_view["Receita esperada total"] = table_view["Receita esperada total"].map(brl)
            table_view["Receita esperada média"] = table_view["Receita esperada média"].map(brl)
            table_view["Score médio"] = table_view["Score médio"].map(lambda value: br_number(value, 1))
            st.dataframe(
                table_view[["Faixa de score", "Oportunidades", "Receita esperada total", "Receita esperada média", "Score médio"]],
                use_container_width=True,
                hide_index=True,
            )
            total_band = band_summary.sort_values("Receita esperada total", ascending=False).iloc[0]["Faixa de score"]
            average_band = band_summary.sort_values("Receita esperada média", ascending=False).iloc[0]["Faixa de score"]
            st.info(
                f"Maior potencial financeiro total: {total_band}. "
                f"Maior potencial médio por oportunidade: {average_band}. "
                "Recomendação: priorizar cadência comercial e CRM para faixas com maior potencial financeiro, validando elegibilidade antes da abordagem."
            )

elif page == "Histórico e fechamento mensal":
    just = data["variation_justifications"]
    closing_months = sorted(closing.month.dropna().unique())
    justification_months = set(just.month.dropna().unique())
    common_months = [item for item in closing_months if item in justification_months]
    default_month = common_months[-1] if common_months else closing_months[-1]
    month = st.sidebar.selectbox("Selecionar mês", closing_months, index=closing_months.index(default_month))
    metric_label = st.sidebar.selectbox("Métrica principal", [friendly_name(item) for item in METRIC_OPTIONS])
    metric = METRIC_OPTIONS[[friendly_name(item) for item in METRIC_OPTIONS].index(metric_label)]
    area_filter = st.sidebar.multiselect("Área", sorted_display_options(just.business_area), format_func=display_term, placeholder="Selecionar opções")
    problem_filter = st.sidebar.multiselect("Tipo de problema", sorted_display_options(just.problem_type), format_func=display_term, placeholder="Selecionar opções")
    team_filter = st.sidebar.multiselect("Time responsável", sorted_display_options(just.responsible_team), format_func=display_term, placeholder="Selecionar opções")
    variation_view = just.copy()
    if area_filter:
        variation_view = variation_view[variation_view.business_area.isin(area_filter)]
    if problem_filter:
        variation_view = variation_view[variation_view.problem_type.isin(problem_filter)]
    if team_filter:
        variation_view = variation_view[variation_view.responsible_team.isin(team_filter)]

    row = closing[closing.month == month].iloc[0]
    month_variations = just[just.month == month]
    fallback_variation = build_monthly_fallback(month, metric, row)
    principal_cause = fallback_variation.iloc[0].problem_type if month_variations.empty else display_term(row.main_variation_driver)
    st.subheader("Resultado do mês")
    st.caption(f"Mês analisado: {month} | Métrica analisada: {friendly_name(metric)}")
    c = st.columns(4)
    kpi_card(c[0], "Meta do mês", value_fmt(metric, row[f"{metric}_target"]))
    kpi_card(c[1], "Realizado", value_fmt(metric, row[f"{metric}_actual"]))
    kpi_card(c[2], "Variação vs meta", value_fmt(metric, row[f"{metric}_variation_abs"]))
    kpi_card(c[3], "Status", display_term(row.target_status))
    with st.container(border=True):
        st.markdown(f"**Resumo do fechamento — {month}**")
        st.markdown(f"**Indicador:** {friendly_name(metric)}")
        st.markdown(f"**Realizado:** {value_fmt(metric, row[f'{metric}_actual'])}")
        st.markdown(f"**Meta:** {value_fmt(metric, row[f'{metric}_target'])}")
        st.markdown(f"**Variação vs meta:** {format_br_pct(row[f'{metric}_variation_pct'])}")
        st.markdown(f"**Principal causa:** {principal_cause}")

    st.divider()
    st.subheader("Diagnóstico da variação")
    current_variations = variation_view[variation_view.month == month]
    if month_variations.empty:
        main_variation = fallback_variation.iloc[0]
        d = st.columns(4)
        kpi_card(d[0], "Área responsável", display_term(main_variation.business_area))
        kpi_card(d[1], "Principal causa", display_term(main_variation.problem_type))
        kpi_card(d[2], "Próxima ação", display_term(main_variation.action_taken))
        kpi_card(d[3], "Status", display_term(main_variation.status))
    elif current_variations.empty:
        st.warning("Nenhuma justificativa encontrada para os filtros selecionados.")
    else:
        main_variation = current_variations.iloc[current_variations["target_variation_pct"].abs().argmax()]
        d = st.columns(4)
        kpi_card(d[0], "Área responsável", display_term(main_variation.business_area))
        kpi_card(d[1], "Principal causa", display_term(main_variation.problem_type))
        kpi_card(d[2], "Próxima ação", display_term(main_variation.action_taken))
        kpi_card(d[3], "Status", display_term(row.target_status))

    st.subheader("Próxima ação e justificativa")
    if month_variations.empty:
        show = fallback_variation
    else:
        show = variation_view[(variation_view.month == month) & (variation_view.metric == metric)]
        if show.empty:
            show = current_variations.head(1)
    if show.empty:
        st.warning("Nenhuma próxima ação encontrada para a métrica e filtros selecionados.")
    else:
        st.dataframe(
            format_variation_table(
                show[
                    [
                        "month",
                        "metric",
                        "business_area",
                        "problem_type",
                        "actual_value",
                        "target_value",
                        "target_variation_abs",
                        "target_variation_pct",
                        "analyst_justification",
                        "action_taken",
                        "decision_owner",
                        "recommended_review_meeting",
                        "follow_up_metric",
                    ]
                ]
            ),
            use_container_width=True,
        )

    st.divider()
    st.subheader("Histórico")
    st.dataframe(format_closing_history(closing, metric), use_container_width=True)
    metric_history = closing[["month", f"{metric}_actual", f"{metric}_target"]].rename(
        columns={"month": "Mês", f"{metric}_actual": "Realizado", f"{metric}_target": "Meta"}
    )
    metric_kind = "money" if metric in {"net_revenue", "spend", "cac", "cpl", "expansion_revenue"} else "pct" if metric in {"roi", "roas", "activation_rate", "retention_proxy"} else "number"
    executive_chart(px.line(metric_history, x="Mês", y=["Realizado", "Meta"], title=f"{friendly_name(metric)}: meta vs realizado", labels={"value": friendly_name(metric), "variable": "Série"}), y_kind=metric_kind)
    executive_chart(px.bar(closing, x="month", y=f"{metric}_variation_pct", title="Variação percentual contra meta", labels={"month": "Mês", f"{metric}_variation_pct": "Variação contra meta"}), y_kind="pct")
    executive_chart(px.bar(closing, x="month", y="revenue_mom_variation_pct", title="Variação de receita contra mês anterior", labels={"month": "Mês", "revenue_mom_variation_pct": "Variação vs mês anterior"}), y_kind="pct")
    e1, e2 = st.columns(2)
    with e1:
        executive_chart(px.line(closing, x="month", y="cac_actual", title="CAC ao longo do tempo", labels={"month": "Mês", "cac_actual": "CAC"}), y_kind="money")
    with e2:
        executive_chart(px.line(closing, x="month", y="net_revenue_actual", title="Receita líquida ao longo do tempo", labels={"month": "Mês", "net_revenue_actual": "Receita líquida"}), y_kind="money")

    st.divider()
    st.subheader("Log de variações")
    log_view = fallback_variation.copy() if month_variations.empty else variation_view[variation_view.month == month].copy()
    st.subheader("Variações por área e tipo de problema")
    if log_view.empty:
        st.warning("Nenhuma variação encontrada para os filtros selecionados.")
    else:
        area_summary = translate_dataframe(log_view).groupby("business_area", as_index=False).agg(variations=("justification_id", "count"), target_gap=("target_variation_abs", "sum"))
        problem_summary = translate_dataframe(log_view).groupby("problem_type", as_index=False).agg(problems=("justification_id", "count"))
        g1, g2 = st.columns(2)
        g1.plotly_chart(px.bar(area_summary, x="business_area", y="variations", title="Variações por área", labels={"business_area": "Área de negócio", "variations": "Variações"}), use_container_width=True)
        g2.plotly_chart(px.bar(problem_summary, x="problem_type", y="problems", title="Problemas por tipo", labels={"problem_type": "Tipo de problema", "problems": "Ocorrências"}), use_container_width=True)
    st.subheader("Log de variações por área")
    if log_view.empty:
        st.warning("Nenhum registro para exibir nos filtros selecionados.")
    else:
        st.dataframe(
            format_variation_table(
                log_view[
                    [
                        "month",
                        "metric",
                        "business_area",
                        "problem_type",
                        "actual_value",
                        "target_value",
                        "target_variation_pct",
                        "detected_driver",
                        "analyst_justification",
                        "decision_owner",
                        "follow_up_metric",
                    ]
                ]
            ),
            use_container_width=True,
        )

elif page == "Consultor rule-based":
    st.caption("Leitura consultiva rule-based com dados sintéticos. Não usa modelo externo nem afirma causa raiz.")
    st.subheader("Gaps priorizados")
    if gaps.empty:
        st.info("Execute `python src/consultant_gap_finder.py` para gerar os gaps priorizados.")
    else:
        executive_priorities = [
            {
                "title": "Prioridade 1 — Eficiência de aquisição",
                "diagnosis": "Canais de aquisição geram volume, mas parte opera com pressão de CAC e menor eficiência final.",
                "impact": "Verba concentrada em canais com menor conversão em matrícula reduz produtividade comercial.",
                "recommendation": "Rebalancear investimento por CAC, LTV/CAC e conversão final.",
                "owner": "Marketing, Comercial e CRM.",
            },
            {
                "title": "Prioridade 2 — Presença em aula gratuita",
                "diagnosis": "Queda ou dispersão de presença em aula gratuita reduz intenção e avanço no funil.",
                "impact": "Menor presença compromete conversão final e aumenta custo por matrícula.",
                "recommendation": "Otimizar lembretes, cadência CRM e SLA para leads inscritos.",
                "owner": "CRM, Produto e CX.",
            },
            {
                "title": "Prioridade 3 — Conversão final em matrícula",
                "diagnosis": "Existe perda entre intenção demonstrada e matrícula ativada.",
                "impact": "Volume captado não se transforma integralmente em receita.",
                "recommendation": "Priorizar leads com maior propensão, revisar abordagem comercial e acompanhar matrícula ativada.",
                "owner": "Comercial, CRM e Liderança de Receita.",
            },
        ]
        for item in executive_priorities:
            consultant_priority_block(item["title"], item["diagnosis"], item["impact"], item["recommendation"], item["owner"])
        area_filter = st.multiselect("Filtrar área do gap", sorted_display_options(gaps.business_area), format_func=display_term, placeholder="Selecionar opções")
        severity_filter = st.multiselect("Filtrar severidade", sorted(gaps.severity.dropna().unique()), format_func=display_term, placeholder="Selecionar opções")
        gap_view = gaps.copy()
        if area_filter:
            gap_view = gap_view[gap_view.business_area.isin(area_filter)]
        if severity_filter:
            gap_view = gap_view[gap_view.severity.isin(severity_filter)]
        gap_cols = [
            "business_area",
            "metric",
            "severity",
            "evidence",
            "likely_hypothesis",
            "recommended_action",
            "decision_owner",
            "follow_up_metric",
        ]
        with st.expander("Detalhe dos gaps priorizados"):
            st.dataframe(format_metric_series(gap_view[gap_cols]).rename(columns={col: friendly_name(col) for col in gap_cols}), use_container_width=True)

    st.subheader("Plano de ação")
    if actions.empty:
        st.info("Execute `python src/action_tracker.py` para gerar o plano de ações.")
    else:
        c1, c2, c3 = st.columns(3)
        kpi_card(c1, "Total de ações", br_number(len(actions), 0))
        kpi_card(c2, "Ações críticas", br_number(int((actions.priority == "critical").sum()), 0))
        kpi_card(c3, "Responsáveis", br_number(actions.owner.nunique(), 0))
        area_filter = st.multiselect("Filtrar área", sorted_display_options(actions.business_area), format_func=display_term, placeholder="Selecionar opções")
        owner_filter = st.multiselect("Filtrar responsável", sorted_display_options(actions.owner), format_func=display_term, placeholder="Selecionar opções")
        status_filter = st.multiselect("Filtrar status", sorted(actions.status.dropna().unique()), format_func=display_term, placeholder="Selecionar opções")
        priority_filter = st.multiselect("Filtrar prioridade", sorted(actions.priority.dropna().unique()), format_func=display_term, placeholder="Selecionar opções")
        action_view = actions.copy()
        if area_filter:
            action_view = action_view[action_view.business_area.isin(area_filter)]
        if owner_filter:
            action_view = action_view[action_view.owner.isin(owner_filter)]
        if status_filter:
            action_view = action_view[action_view.status.isin(status_filter)]
        if priority_filter:
            action_view = action_view[action_view.priority.isin(priority_filter)]
        for idx, item in action_view.head(2).iterrows():
            action_priority_block(item, f"Ação prioritária {idx + 1}")
        tab_area, tab_priority, tab_status = st.tabs(["Por área", "Por prioridade", "Por status"])
        with tab_area:
            executive_chart(px.bar(translate_dataframe(actions), x="business_area", title="Ações por área", labels={"business_area": "Área de negócio"}), y_kind="number")
        with tab_priority:
            action_priority = translate_dataframe(actions.copy())
            executive_chart(px.histogram(action_priority, x="priority", title="Ações por prioridade", labels={"priority": "Prioridade"}), y_kind="number")
        with tab_status:
            action_status = translate_dataframe(actions.copy())
            executive_chart(px.histogram(action_status, x="status", title="Ações por status", labels={"status": "Status"}), y_kind="number")
        action_cols = ["recommended_action", "owner", "priority", "expected_impact", "status", "follow_up_metric"]
        with st.expander("Detalhe do plano de ação"):
            st.dataframe(rename_friendly(action_view[action_cols]), use_container_width=True)

    st.subheader("Recomendações de experimentos")
    if experiments.empty:
        st.info("Execute `python src/experiment_recommendations.py` para gerar recomendações de experimentos.")
    else:
        c1, c2, c3 = st.columns(3)
        kpi_card(c1, "Experimentos propostos", br_number(len(experiments), 0))
        kpi_card(c2, "Tipos de teste", br_number(experiments.experiment_type.nunique(), 0))
        kpi_card(c3, "Responsáveis", br_number(experiments.owner.nunique(), 0))
        tab_area, tab_type, tab_status = st.tabs(["Por área", "Por tipo", "Por status"])
        with tab_area:
            executive_chart(px.bar(translate_dataframe(experiments), x="business_area", title="Experimentos por área", labels={"business_area": "Área de negócio"}), y_kind="number")
        with tab_type:
            executive_chart(px.histogram(experiments, x="experiment_type", title="Experimentos por tipo", labels={"experiment_type": "Tipo de experimento"}), y_kind="number")
        with tab_status:
            experiment_status = translate_dataframe(experiments.copy())
            executive_chart(px.histogram(experiment_status, x="status", title="Experimentos por status", labels={"status": "Status"}), y_kind="number")
        experiment_cols = ["hypothesis", "primary_metric", "minimum_success_criteria", "owner", "risk", "status"]
        with st.expander("Detalhe dos experimentos"):
            st.dataframe(rename_friendly(experiments[experiment_cols]), use_container_width=True)

    st.subheader("Análise consultiva rule-based")
    path = ROOT / "docs" / "ai_consultant_analysis.md"
    if path.exists():
        analysis_text = path.read_text(encoding="utf-8")
        analysis_text = analysis_text.replace("# AI Consultant Analysis", "# Análise consultiva rule-based")
        analysis_text = analysis_text.replace("## Historical Performance and Monthly Variation", "## Histórico de performance e variação mensal")
        analysis_text = analysis_text.replace("## Target vs Actual Closing", "## Fechamento: meta vs realizado")
        analysis_text = analysis_text.replace("## Business Area Diagnosis", "## Diagnóstico por área de negócio")
        analysis_text = display_term(analysis_text)
        st.markdown(analysis_text)
    else:
        st.markdown("Execute `python src/ai_consultant.py`.")
