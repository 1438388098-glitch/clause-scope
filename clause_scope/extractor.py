# -*- coding: utf-8 -*-
"""条款抽取规则引擎：把合同全文切分为编号条款，并给每条分类、定位原文 span。

v0.1 是**确定性规则引擎**（标题模式优先、正文模式兜底），不是 LLM 抽取——
每一条判定都可解释、可测试；LLM 辅助抽取属 v0.2（接口预留 classify_llm）。

span 语义：所有输出都带 (char_start, char_end) 在**原始合同文本**上的偏移，
上层报告据此回跳原文——「原文 span 回跳」是硬约束。
"""
import re

from clause_scope.schema import CATEGORIES, CLAUSE_HEADING_RE, VALID_CATEGORIES


def split_clauses(text):
    """把合同全文切成条款列表。

    返回 [{"index": 序号, "title": 标题或空, "body": 正文, "start": 起始偏移,
           "end": 结束偏移}]；start/end 为原始文本上的字符偏移（含标题行）。
    无法识别编号结构的合同返回单个全文条款（index=0，title 空）——宁可
    整段兜底，也不静默丢内容。
    """
    lines = text.split("\n")
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1  # +1 为换行符

    heads = []
    for i, line in enumerate(lines):
        m = CLAUSE_HEADING_RE.match(line)
        if m:
            heads.append({"line": i, "title": (m.group(2) or "").strip(),
                          "start": offsets[i]})

    if len(heads) < 2:
        return [{"index": 0, "title": "", "body": text,
                 "start": 0, "end": len(text)}]

    clauses = []
    for j, h in enumerate(heads):
        end_line = heads[j + 1]["line"] if j + 1 < len(heads) else len(lines)
        body = "\n".join(lines[h["line"] + 1:end_line])
        start = h["start"]
        end = offsets[end_line - 1] + len(lines[end_line - 1]) if end_line > h["line"] + 1 else start + len(lines[h["line"]])
        if end_line == len(lines):
            end = len(text)
        clauses.append({
            "index": j + 1,
            "title": h["title"],
            "body": body.strip(),
            "start": start,
            "end": end,
        })
    return clauses


def classify_clause(clause):
    """对单个条款分类。返回 (category, confidence, matched_by)。

    - 标题命中关键词 → (类别, "high", "title")；
    - 正文按「全类别计票、最高票且 ≥2」归类 → (类别, "low", "body")；
      （不采用「单命中短文本即归类」：『提供』『通知』这类通用词会抢走分类）
    - 都不命中 → ("misc", "low", "fallback")。
    """
    title = clause.get("title", "")
    body = clause.get("body", "")
    if title:
        for cat, (_name, title_pats, _body_pats) in CATEGORIES.items():
            if cat == "misc":
                continue
            for pat in title_pats:
                if pat in title:
                    return cat, "high", "title"
    best_cat, best_hits = None, 0
    for cat, (_name, _title_pats, body_pats) in CATEGORIES.items():
        if cat == "misc":
            continue
        hits = sum(body.count(pat) for pat in body_pats)
        if hits > best_hits:
            best_cat, best_hits = cat, hits
    if best_hits >= 2:
        return best_cat, "low", "body"
    return "misc", "low", "fallback"


def extract(text):
    """主入口：合同全文 → 结构化条款列表（含分类与 span）。"""
    clauses = split_clauses(text)
    out = []
    for c in clauses:
        cat, confidence, matched_by = classify_clause(c)
        out.append({
            "index": c["index"],
            "title": c["title"],
            "category": cat,
            "confidence": confidence,
            "matched_by": matched_by,
            "span": {"start": c["start"], "end": c["end"]},
            "text": (c["title"] + "\n" + c["body"]).strip() if c["title"] else c["body"],
        })
    return out
