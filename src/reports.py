try:
    from .utils import DOCS, brl, br_number, read_csv
except ImportError:
    from utils import DOCS, brl, br_number, read_csv


def write_doc(name, title, body):
    (DOCS / name).write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def generate_reports():
    close = read_csv("monthly_closing.csv")
    gaps = read_csv("consultant_gap_log.csv")
    last = close.iloc[-1]
    high_gaps = len(gaps[gaps.severity == "high"])

    write_doc(
        "case_context.md",
        "Contexto do Case",
        """
EdTech fictícia de idiomas com modelo digital, creator-led growth, aulas gratuitas, CRM/WhatsApp, comunidade, assinatura e expansão por produtos premium. Todos os dados são sintéticos e demonstram análise executiva de Marketing Analytics e Revenue Analytics.
""",
    )

    write_doc(
        "executive_analysis.md",
        "Análise Executiva",
        f"""
## Resumo executivo
Os dados sugerem oportunidade de crescer receita com mais eficiência ao priorizar canais de maior intenção, corrigir gargalos de presença em eventos e reduzir atraso em leads P1.

## Principais achados
- Receita líquida no último mês: {brl(last.net_revenue_actual)}.
- CAC no último mês: {brl(last.cac_actual)}.
- Status de receita: {last.target_status}.
- Gaps críticos abertos: {br_number(high_gaps, 0)}.

## Riscos de receita
- Volume barato sem conversão.
- CAC pressionado em canal de escala.
- Onboarding abaixo da meta em parte do período.

## Decisões recomendadas
- Rebalancear verba para Paid Search, Referral, CRM e eventos com melhor show-up.
- Criar SLA P1 de 15 minutos.
- Medir receita assistida por creator e matrícula ativada.

## Responsáveis sugeridos
Head de Growth, Head Comercial, CRM Manager, Head de Produto e Data Governance.

## Impacto esperado
Melhor payback, menor desperdício comercial e maior previsibilidade no fechamento mensal.

## Métricas de acompanhamento
CAC, LTV/CAC, show-up rate, P1 SLA, lead to enrollment, activation rate e retention proxy.
""",
    )

    write_doc(
        "executive_memo.md",
        "Executive Memo",
        f"""
## Problema
A EdTech precisa crescer receita sem confundir volume barato de leads com aquisição eficiente de alunos ativados.

## Evidências
- Receita líquida no último mês: {brl(last.net_revenue_actual)}.
- CAC no último mês: {brl(last.cac_actual)}.
- Há {br_number(high_gaps, 0)} gaps críticos ou de alta severidade no log consultivo.

## Risco de negócio
Os dados sugerem risco de investir em canais que batem volume, mas pressionam CAC, payback e ativação.

## Decisão recomendada
Rebalancear verba para canais e segmentos com melhor LTV/CAC, enquanto Comercial aplica SLA P1 e CRM recupera leads quentes.

## Responsável
Head de Growth, Head Comercial e Revenue Governance.

## Métrica de acompanhamento
CAC por canal, LTV/CAC, lead para matrícula, activation rate e payback ajustado por margem.

## O que ainda falta validar
Margem real por plano, cohort de retenção de 60/90 dias, qualidade por SDR e atribuição assistida por creator.

## Recomendação final
Priorizar crescimento eficiente. A evidência disponível aponta para redistribuição gradual de investimento, com validação por cohort e leitura no próximo fechamento mensal.
""",
    )

    write_doc(
        "metrics_dictionary.md",
        "Dicionário de Métricas",
        """
| Métrica | Definição | Fórmula | Por que importa | Decisão suportada | Limitação |
|---|---|---|---|---|---|
| CAC | Custo por matrícula | spend / enrollments | Mede eficiência comercial | Rebalancear canal | Não inclui custo fixo |
| CPL | Custo por lead | spend / leads | Mede aquisição inicial | Otimizar campanha | Pode mascarar baixa qualidade |
| ROI | Retorno sobre investimento | (receita - spend) / spend | Mostra retorno líquido | Cortar ou escalar | Não substitui margem |
| ROAS | Receita por spend | receita / spend | Compara mídia | Escalar verba | Não mede payback |
| LTV/CAC | Valor esperado por CAC | expected_ltv / CAC | Mede qualidade da receita | Priorizar segmentos | LTV é estimado |
| Activation rate | Alunos ativados | ativados / matrículas | Sinal inicial de retenção | Melhorar onboarding | Não mede retenção longa |
| Retention proxy | Proxy de retenção | 1 - churn_risk_score médio | Antecipação de churn | Ação de CX | Não é churn real |
""",
    )

    write_doc(
        "business_rules.md",
        "Regras de Negócio",
        """
Lead scoring é rule-based de 0 a 100 e combina intenção, engajamento, qualidade do canal, idioma, objetivo declarado, interação CRM, presença em aula, urgência de atendimento e conversão histórica por segmento. Tiers: P1 >= 80, P2 >= 60, P3 >= 40 e nurture abaixo de 40.

Status de meta usa tolerância de 5%. Para receita, leads, ROI, ROAS, LTV/CAC, ativação e retenção, maior é melhor. Para CAC e CPL, menor é melhor. O fechamento mensal compara realizado contra meta e contra mês anterior, sempre tratando divisão por zero.
""",
    )

    write_doc(
        "production_flow.md",
        "Fluxo de Produção",
        """
Em produção, o fluxo integraria CRM, mídia paga, sales engagement, plataforma de pagamentos, LMS/produto, app, comunidade, data warehouse e BI. Cada fonte teria contrato de dados, chaves de identidade, atualização diária, camada de qualidade e modelos de atribuição auditáveis. A IA consultora continuaria rule-based para governança, com hipóteses e validações antes de qualquer afirmação executiva.

## Privacy and Governance in Production
Uma versão produtiva precisaria aplicar consentimento, minimização de dados, controle de acesso, mascaramento, retenção, auditoria e governança de tracking. As fontes deveriam ter documentação clara, responsáveis definidos, lineage básico e regras de uso revisadas periodicamente para reduzir risco operacional e regulatório.
""",
    )

    write_doc(
        "final_handoff_report.md",
        "Relatório Final de Entrega",
        """
Projeto entregue com dados sintéticos, pipeline Python, SQLite, dashboard Streamlit, fechamento mensal, camada de IA consultora rule-based, consultor de gaps, auditorias e testes. Limitações: não usa dados reais, não usa API externa, não estima causalidade e usa LTV sintético.

Próximos passos: conectar fontes reais, validar hipóteses com liderança, criar ownership por métrica e transformar recomendações em rituais de fechamento mensal.
""",
    )

    (DOCS.parent / "slides" / "executive_presentation.md").write_text(
        """# Apresentação Executiva

## 1. Contexto
EdTech digital de idiomas com crescimento por conteúdo, creators, eventos, CRM e vendas.

## 2. Problema
Volume de leads não garante receita eficiente nem aluno ativado.

## 3. O que foi analisado
Canais, campanhas, funil, CAC, LTV/CAC, ROI, ROAS, CRM, produto, retenção e fechamento mensal.

## 4. Principais achados
Paid Social escala volume; Search, Referral e CRM sugerem melhor qualidade de receita.

## 5. Target vs Actual
Fechamento compara meta, realizado, gap e driver provável.

## 6. Variações mensais
Eventos fortes explicam parte da receita; pressão de mídia explica parte do CAC.

## 7. Decisões recomendadas
Rebalancear verba, priorizar P1, otimizar show-up e medir matrícula ativada.

## 8. Plano de 30 dias
SLA P1, cadência CRM, teste de eventos e cohort por LTV/CAC.

## 9. Perguntas para liderança
Qual CAC limite? Qual segmento priorizar? Qual métrica define crescimento saudável?
""",
        encoding="utf-8",
    )
    print("Documentação executiva gerada")


if __name__ == "__main__":
    generate_reports()
