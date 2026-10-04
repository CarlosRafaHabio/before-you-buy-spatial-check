"""Authoritative deterministic presentation, not an LLM approval channel."""
from .engine import evaluate


def format_result(request: object, trusted_evidence: object) -> str:
    # Re-evaluate from inputs. Never accept an LLM-supplied 'result/status'.
    result = evaluate(request, trusted_evidence)
    lines = [result["status"], f"Produto: {result['item_identity'] or 'não identificado'}",
             f"Achados: {len(result['findings'])}; pendências: {len(result['blockers'])}."]
    for issue in result["findings"] + result["blockers"]:
        lines.append(f"- {issue['code']} — {issue['field']}: {issue['message']}")
    for check in result["checks"]:
        if "actual_cm" in check:
            lines.append(f"- {check['id']}: distância livre {check['actual_cm']} cm; "
                         f"requisito explícito {check['required_cm']} cm.")
    lines.append("Conclusão restrita aos dados fornecidos e aos testes 2D executados. "
                 "Não garante compra, circulação, altura, montagem, segurança ou conformidade normativa.")
    return "\n".join(lines)
