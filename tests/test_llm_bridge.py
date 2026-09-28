# -*- coding: utf-8 -*-
"""llm_bridge 契约测试：v0.2 接口桩的行为用测试钉死。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clause_scope.extractor import extract
from clause_scope.llm_bridge import classify_llm, llm_assisted_extract

CONTRACT = (
    "第一条 保密义务\n乙方对在合作期间知悉的商业秘密负有保密义务，不得对外披露。\n"
    "第二条 其他\n本条用于兜底表述。\n"
)


def _fake_ok(clause):
    return "confidentiality", "medium", "正文出现保密义务与不得披露表述"


class TestClassifyLlmContract(unittest.TestCase):
    def test_no_fn_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            classify_llm({"title": "", "body": "x"}, None)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            classify_llm({"title": "", "body": "x"},
                         lambda c: ("not_a_category", "low", "理由"))

    def test_missing_rationale_rejected(self):
        with self.assertRaises(ValueError):
            classify_llm({"title": "", "body": "x"},
                         lambda c: ("liability", "low", "  "))

    def test_wrong_arity_rejected(self):
        with self.assertRaises(ValueError):
            classify_llm({"title": "", "body": "x"}, lambda c: ("liability", "low"))

    def test_valid_return_carries_llm_marker_and_rationale(self):
        cat, conf, by, rationale = classify_llm({"title": "", "body": "x"}, _fake_ok)
        self.assertEqual((cat, conf, by), ("confidentiality", "medium", "llm"))
        self.assertIn("保密", rationale)


class TestLlmAssistedExtract(unittest.TestCase):
    def test_llm_only_touches_rule_fallback(self):
        clauses = extract(CONTRACT)
        self.assertTrue(any(c["matched_by"] == "fallback" for c in clauses),
                        "夹具应至少有一条规则 fallback 条款")
        calls = []

        def spy(clause):
            calls.append(clause["index"])
            return _fake_ok(clause)

        out = llm_assisted_extract(CONTRACT, spy)
        fallback_idx = {c["index"] for c in clauses if c["matched_by"] == "fallback"}
        self.assertEqual(set(calls), fallback_idx, "LLM 只允许补判规则 fallback 条款")
        for before, after in zip(clauses, out):
            self.assertEqual(before["span"], after["span"],
                             "span 是硬约束，LLM 补判不得改动")
            self.assertEqual(before["index"], after["index"])
            if before["matched_by"] == "fallback":
                self.assertEqual(after["matched_by"], "llm")
                self.assertEqual(after["category"], "confidentiality")
                self.assertIn("rationale", after)
            else:
                self.assertEqual((before["category"], before["matched_by"]),
                                 (after["category"], after["matched_by"]))
                self.assertNotIn("rationale", after)


if __name__ == "__main__":
    unittest.main()
