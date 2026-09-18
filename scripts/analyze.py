# -*- coding: utf-8 -*-
"""分析 CLI：合同文件 → 结构化报告（Markdown + JSON）。

用法：
  python scripts/analyze.py contracts/sample_contract.txt --out data/report
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from clause_scope.extractor import extract
from clause_scope.report import to_json, to_report
from clause_scope.risk_rules import analyze_risks

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="clause-scope 合同条款分析")
    parser.add_argument("contract", help="合同文本文件（UTF-8）")
    parser.add_argument("--out", default="data/report", help="输出前缀（生成 .md 与 .json）")
    args = parser.parse_args()

    with io.open(args.contract, "r", encoding="utf-8") as f:
        text = f.read()

    clauses = extract(text)
    findings = analyze_risks(clauses)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    md = to_report(text, clauses, findings)
    js = to_json(text, clauses, findings)
    with io.open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    with io.open(args.out + ".json", "w", encoding="utf-8") as f:
        f.write(js)

    print("条款：%d ｜ 发现：%d（P0 %d / P1 %d / P2 %d）" % (
        len(clauses), len(findings),
        sum(1 for x in findings if x["severity"] == "P0"),
        sum(1 for x in findings if x["severity"] == "P1"),
        sum(1 for x in findings if x["severity"] == "P2")))
    print("报告：", args.out + ".md / .json")


if __name__ == "__main__":
    main()
