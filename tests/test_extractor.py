# -*- coding: utf-8 -*-
"""extractor 单测：切分、分类、span 回跳。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clause_scope.extractor import classify_clause, extract, split_clauses
from clause_scope.schema import cn_to_int

CONTRACT = """服务合同

甲方：某某科技有限公司
乙方：某某咨询工作室

第一条　合同标的
乙方向甲方提供数据分析咨询服务，具体范围以附件一为准。

第二条　价款与支付
服务费总计人民币 50 万元（不含税）。甲方应于合同签订后 10 个工作日内支付 50%。

第三条　交付与验收
乙方应于 2026 年 12 月 31 日前交付全部成果，甲方应在收到后 5 个工作日内完成验收。

第四条　保密
双方对在合作过程中知悉的对方商业秘密负有保密义务，保密期限为合同终止后三年。

第五条　违约责任
任何一方违约的，应向守约方支付合同总额 20% 的违约金。

第六条　争议解决
因本合同引起的争议，双方协商解决；协商不成的，提交合同签订地人民法院诉讼解决。
"""


class SplitClausesTest(unittest.TestCase):
    def test_split_count_and_titles(self):
        clauses = split_clauses(CONTRACT)
        self.assertEqual(len(clauses), 6)
        self.assertEqual(clauses[0]["title"], "合同标的")
        self.assertEqual(clauses[4]["title"], "违约责任")

    def test_span_roundtrip(self):
        clauses = split_clauses(CONTRACT)
        for c in clauses:
            snippet = CONTRACT[c["start"]:c["end"]]
            # span 内必须包含本条标题（或正文首行）
            self.assertTrue(
                c["title"] in snippet or c["body"][:10] in snippet,
                "span 无法回跳：index=%s" % c["index"],
            )

    def test_no_numbered_structure_falls_back_to_whole(self):
        text = "甲方与乙方经友好协商，就合作事宜达成如下口头式短文合同，没有编号条款。"
        clauses = split_clauses(text)
        self.assertEqual(len(clauses), 1)
        self.assertEqual(clauses[0]["index"], 0)


class ClassifyTest(unittest.TestCase):
    def _clause(self, title, body):
        return {"index": 1, "title": title, "body": body}

    def test_title_signal_strong(self):
        cat, conf, by = classify_clause(self._clause("违约责任", "甲方应按时付款。"))
        self.assertEqual((cat, conf, by), ("liability", "high", "title"))

    def test_body_signal_fallback(self):
        cat, conf, by = classify_clause(self._clause(
            "", "双方应妥善保管对方提供的资料，不得向第三方披露，违反保密义务的承担相应责任。"))
        self.assertEqual((cat, "low", "body")[0], "confidentiality")

    def test_unmatched_goes_to_misc(self):
        cat, conf, by = classify_clause(self._clause("", "本合同一式两份。"))
        self.assertEqual(cat, "misc")

    def test_all_categories_valid(self):
        titles = ["合同标的", "价款", "验收", "保密", "违约责任", "管辖", "解除", "不可抗力",
                  "知识产权", "通知与送达"]
        for i, t in enumerate(titles):
            cat, _c, _m = classify_clause({"index": i + 1, "title": t, "body": "内容。"})
            self.assertNotEqual(cat, "misc", "标题「%s」应命中分类" % t)


class ExtractTest(unittest.TestCase):
    def test_full_pipeline_categories(self):
        result = extract(CONTRACT)
        cats = {r["category"] for r in result}
        for expected in ("parties", "price", "delivery", "confidentiality",
                         "liability", "dispute"):
            self.assertIn(expected, cats)

    def test_every_result_has_span_and_text(self):
        for r in extract(CONTRACT):
            self.assertIn("span", r)
            self.assertTrue(r["text"].strip())
            self.assertLessEqual(r["span"]["start"], r["span"]["end"])


class CnNumTest(unittest.TestCase):
    def test_common(self):
        for s, v in [("一", 1), ("十", 10), ("十二", 12), ("二十", 20), ("二十五", 25), ("3", 3)]:
            self.assertEqual(cn_to_int(s), v)
        self.assertIsNone(cn_to_int("甲"))


if __name__ == "__main__":
    unittest.main()
