from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "replacement_char": "\ufffd",
    "mojibake": "|".join([
        "\u00c3\u0192",
        "\u00c3\u201a",
        "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u201e\u00a2",
        "\u00c3\u00a2\u00e2\u201a\u00ac\u00c5\u201c",
        "\u00c3\u00a2\u00e2\u201a\u00ac\u00c2",
        "\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u0153",
        "\u00ef\u00bf\u00bd",
    ]),
    "zero_width": r"[\u200b\u200c\u200d\ufeff]",
    "control_char": r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
    "markdown_double_heading": r"^# #",
    "markdown_heading_without_space": r"^#{1,6}[^#\s]",
}
PROFESSIONAL_FILES = ["README.md", "docs", "slides"]


def iter_files():
    names = ["README.md", "AGENTS.md"]
    for name in names:
        path = ROOT / name
        if path.exists():
            yield path
    for folder in ["docs", "slides", "app", "src", "tests", "scripts"]:
        for path in (ROOT / folder).glob("**/*"):
            if path.suffix in [".md", ".py"]:
                yield path


def code_fence_balanced(text):
    return text.count("```") % 2 == 0


def audit():
    issues = []
    files = list(iter_files())
    for path in files:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            issues.append((path, 1, "bom", "Remover BOM."))
        text = raw.decode("utf-8")
        rel = str(path.relative_to(ROOT))
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                issues.append((path, lineno, "trailing_space", "Remover espaços no fim da linha."))
            if path.suffix == ".md" and "\t" in line:
                issues.append((path, lineno, "tab_markdown", "Trocar tab por espaços."))
            if path.suffix == ".md" and len(line) > 420:
                issues.append((path, lineno, "long_markdown_line", "Quebrar linha longa."))
            if path.suffix == ".md" and re.search(r"https?://[^\s)]+", line) and "](" not in line and "http" in line:
                issues.append((path, lineno, "plain_link", "Usar link markdown."))
            for name, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    issues.append((path, lineno, name, "Corrigir caractere ou heading."))
            if any(rel.startswith(p) for p in PROFESSIONAL_FILES) and re.search(r"[\U0001F300-\U0001FAFF]", line):
                issues.append((path, lineno, "emoji", "Remover emoji em documentação profissional."))
        if path.suffix == ".md" and not code_fence_balanced(text):
            issues.append((path, 1, "unclosed_code_fence", "Fechar bloco de código markdown."))
    report = ["# Text Quality Audit Report", "", f"Arquivos analisados: {len(files)}", ""]
    if issues:
        report.append("| Arquivo | Linha | Tipo | Sugestão |")
        report.append("|---|---:|---|---|")
        for path, line, kind, suggestion in issues:
            report.append(f"| {path.relative_to(ROOT)} | {line} | {kind} | {suggestion} |")
        report.append("")
        report.append("Status final: reprovado")
    else:
        report.append("Nenhum problema encontrado.")
        report.append("")
        report.append("Status final: aprovado")
    out = ROOT / "docs" / "text_quality_audit_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    return issues


if __name__ == "__main__":
    issues = audit()
    print(f"Auditoria textual: {len(issues)} problemas")
    sys.exit(1 if issues else 0)
