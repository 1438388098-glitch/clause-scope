# -*- coding: utf-8 -*-
"""评测：三份虚构标注合同上的分类准确率 / span 回跳率 / 风险检出率。

用法：python scripts/run_eval.py  →  输出对比并写 docs/eval_report.md
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from clause_scope.extractor import extract
from clause_scope.risk_rules import analyze_risks

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with io.open(os.path.join(ROOT, "sample_data", "labels.json"), encoding="utf-8") as f:
        labels = json.load(f)["contracts"]

    total_clauses = correct = span_ok = 0
    risk_hits = risk_total = found_total = 0
    per_contract = []
    for path, gold in labels.items():
        full = os.path.join(ROOT, path)
        with io.open(full, encoding="utf-8") as f:
            text = f.read()
        clauses = extract(text)
        findings = analyze_risks(clauses)

        got_cats = {str(c["index"]): c["category"] for c in clauses}
        ok = sum(1 for idx, cat in gold["clause_categories"].items()
                 if got_cats.get(idx) == cat)
        total_clauses += len(gold["clause_categories"])
        correct += ok

        for c in clauses:
            snippet = " ".join(text[c["span"]["start"]:c["span"]["end"]].split())
            # span 回跳有效性：片段中能找到条款号或标题
            heads = [u"第%s条" % n for n in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]]
            span_ok += 1 if (any(h in snippet for h in heads) or c["title"] in snippet) else 0

        found = {f["rule_id"] for f in findings}
        expected = set(gold["expected_findings"])
        risk_total += len(expected)
        risk_hits += len(expected & found)
        found_total += len(found)

        per_contract.append({
            "path": path, "clauses": len(clauses),
            "cat_correct": "%d/%d" % (ok, len(gold["clause_categories"])),
            "findings": sorted(found),
        })

    cat_acc = correct / float(total_clauses) * 100
    span_rate = span_ok / float(total_clauses) * 100
    risk_recall = risk_hits / float(risk_total) * 100 if risk_total else 100.0
    risk_precision = risk_hits / float(found_total) * 100 if found_total else 0.0

    lines = []
    lines.append("# clause-scope 评测报告（虚构标注样例）")
    lines.append("")
    lines.append("| 指标 | 结果 |")
    lines.append("|---|---|")
    lines.append("| 条款分类准确率 | %.1f%%（%d/%d） |" % (cat_acc, correct, total_clauses))
    lines.append("| span 回跳有效率 | %.1f%%（%d/%d） |" % (span_rate, span_ok, total_clauses))
    lines.append("| 风险检出率（召回） | %.1f%%（%d/%d） |" % (risk_recall, risk_hits, risk_total))
    lines.append("| 风险提示精确率 | %.1f%%（%d/%d；已知假阳性来源：条件解除权（如「甲方有权解除」）会被计为单方解除，区别于「任意解除」的细分属 v0.2） |" % (
        risk_precision, risk_hits, found_total))
    lines.append("")
    lines.append("> 样本为 %d 份**完全虚构**的演示合同（%d 个条款），仅验证规则引擎行为；" % (
        len(labels), total_clauses))
    lines.append("> 真实合同（≥30 份、字段准确率 ≥85% 验收门）待语料到位后另行评测。")
    lines.append("")
    for pc in per_contract:
        lines.append("- %s：%s 条款分类正确，检出 %s" % (pc["path"], pc["cat_correct"], "、".join(pc["findings"]) or "无"))

    report = "\n".join(lines)
    print(report)
    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    with io.open(os.path.join(out_dir, "eval_report.md"), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("\n报告已写入 docs/eval_report.md")


if __name__ == "__main__":
    main()
