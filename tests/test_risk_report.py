# -*- coding: utf-8 -*-
"""风险规则与报告单测：构造条款清单直接驱动（不经抽取层，聚焦规则本身）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clause_scope.report import to_json, to_report
from clause_scope.risk_rules import analyze_risks


def _clause(idx, cat, text, title=""):
    return {"index": idx, "title": title, "category": cat, "confidence": "high",
            "matched_by": "title", "span": {"start": 0, "end": len(text)}, "text": text}


GOOD = [
    _clause(1, "parties", "甲方乙方向就数据分析服务达成合作。", "合同标的"),
    _clause(2, "price", "服务费 50 万元，甲方应支付。", "价款与支付"),
    _clause(3, "liability", "任何一方违约的，应向守约方支付违约金。", "违约责任"),
    _clause(4, "dispute", "争议协商不成的，提交合同签订地人民法院诉讼解决。", "争议解决"),
]

MISSING_BOTH = [_clause(1, "parties", "甲方乙方合作。", "合同标的")]

ONE_SIDE = [
    _clause(1, "liability", "甲方违约的，甲方应支付违约金。", "违约责任"),
    _clause(2, "term_termination", "乙方可任意解除本合同，无需甲方同意。", "合同解除"),
    _clause(3, "dispute", "争议提交有管辖权的人民法院处理。", "争议解决"),
]


class MissingTest(unittest.TestCase):
    def test_complete_contract_no_missing(self):
        findings = [f for f in analyze_risks(GOOD) if f["rule_id"].startswith("MISSING")]
        self.assertEqual(findings, [])

    def test_missing_liability_is_P0(self):
        findings = [f for f in analyze_risks([GOOD[0]]) if f["rule_id"] == "MISSING_LIABILITY"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "P0")
        self.assertIsNone(findings[0]["evidence"])


class ImbalanceTest(unittest.TestCase):
    def test_one_side_release_detected(self):
        findings = [f for f in analyze_risks(ONE_SIDE) if f["rule_id"] == "ONE_SIDE_RELEASE"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "P1")
        self.assertIn("乙", findings[0]["message"])

    def test_balanced_not_flagged(self):
        findings = [f for f in analyze_risks(GOOD) if f["rule_id"] == "ONE_SIDE_RELEASE"]
        self.assertEqual(findings, [])


class VagueTest(unittest.TestCase):
    def test_vague_jurisdiction_detected(self):
        findings = [f for f in analyze_risks(ONE_SIDE) if f["rule_id"] == "VAGUE_JURISDICTION"]
        self.assertEqual(len(findings), 1)

    def test_specific_jurisdiction_not_flagged(self):
        findings = [f for f in analyze_risks(GOOD) if f["rule_id"] == "VAGUE_JURISDICTION"]
        self.assertEqual(findings, [])


class ReportTest(unittest.TestCase):
    def test_report_contains_findings_and_disclaimer(self):
        clauses = GOOD + [ONE_SIDE[2]]
        findings = analyze_risks(clauses)
        report = to_report("合同全文…", clauses, findings)
        self.assertIn("风险发现", report)
        self.assertIn("不构成法律意见", report)
        for f in findings:
            self.assertIn(f["rule_id"], report)

    def test_json_roundtrip(self):
        import json
        data = json.loads(to_json("全文", GOOD, analyze_risks(GOOD)))
        self.assertEqual(data["clause_count"], 4)
        for c in data["clauses"]:
            self.assertIn("span", c)


if __name__ == "__main__":
    unittest.main()
