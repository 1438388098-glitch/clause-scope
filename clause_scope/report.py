# -*- coding: utf-8 -*-
"""报告生成：合同原文 + 条款清单 + 风险发现 → Markdown / JSON 报告。

风险发现的 evidence 带 span 时，报告同时输出原文摘录——
「每条发现都能回跳原文」从抽取层贯穿到报告层。
"""
import json

SEVERITY_LABEL = {"P0": "P0（阻断）", "P1": "P1（重要）", "P2": "P2（提示）"}


def _excerpt(text, span, width=60):
    start = max(0, span["start"])
    end = min(len(text), span["end"])
    snippet = " ".join(text[start:end].split())
    return snippet[:width] + ("…" if len(snippet) > width else "")


def to_report(text, clauses, findings):
    lines = []
    lines.append("# 合同条款分析报告")
    lines.append("")
    lines.append("条款总数：%d ｜ 风险发现：%d（P0 %d / P1 %d / P2 %d）" % (
        len(clauses), len(findings),
        sum(1 for f in findings if f["severity"] == "P0"),
        sum(1 for f in findings if f["severity"] == "P1"),
        sum(1 for f in findings if f["severity"] == "P2"),
    ))
    lines.append("")
    if findings:
        lines.append("## 风险发现（按严重度排序）")
        lines.append("")
        lines.append("| 严重度 | 规则 | 说明 | 依据 |")
        lines.append("|---|---|---|---|")
        for f in findings:
            if f["evidence"] and isinstance(f["evidence"], dict) and "start" in f["evidence"]:
                evidence = u"第%s条「%s」" % (f["evidence"]["index"], _excerpt(text, f["evidence"], 40))
            else:
                evidence = u"（缺失，全文未检出该类条款）"
            lines.append("| %s | %s | %s | %s |" % (
                SEVERITY_LABEL[f["severity"]], f["rule_id"], f["message"], evidence))
        lines.append("")
    lines.append("## 条款清单")
    lines.append("")
    lines.append("| 条款 | 标题 | 分类 | 置信度 | 分类依据 |")
    lines.append("|---|---|---|---|---|")
    for c in clauses:
        lines.append("| 第%d条 | %s | %s | %s | %s |" % (
            c["index"], c["title"] or "—", c["category"], c["confidence"], c["matched_by"]))
    lines.append("")
    lines.append("> 本报告由确定性规则引擎生成，仅辅助核查，不构成法律意见。")
    return "\n".join(lines)


def to_json(text, clauses, findings):
    return json.dumps({
        "clause_count": len(clauses),
        "finding_count": len(findings),
        "findings": findings,
        "clauses": [{"index": c["index"], "title": c["title"], "category": c["category"],
                     "confidence": c["confidence"], "span": c["span"],
                     "excerpt": _excerpt(text, c["span"], 80)} for c in clauses],
    }, ensure_ascii=False, indent=2)
