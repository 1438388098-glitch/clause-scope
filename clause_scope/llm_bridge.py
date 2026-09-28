# -*- coding: utf-8 -*-
"""LLM 辅助分类接口（v0.2 桩）：规则引擎留出的唯一 LLM 挂载点。

设计约束（与 v0.1 的硬约束一致）：
- **span 不许动**：LLM 只对规则引擎判为 misc/fallback 的条款做「分类」，绝不
  重新切分条款——(start, end) 永远来自规则引擎，原文回跳不受模型影响。
- **模型是注入的**：本模块不绑定任何模型 SDK；调用方传入
  ``classify_fn(clause) -> (category, confidence, rationale)``。
  没有注入就明确报 NotImplementedError，不静默降级、不装作跑过模型。
- **输出必须可解释**：LLM 给出的每个分类都要求带 rationale，缺了就拒绝——
  「为什么归这类」和分类本身同样是一等输出。

真实模型接入步骤（v0.2 正式版待办）：实现一个 classify_fn 适配器 +
在 eval 报告里单列「LLM 补判命中率」。本桩先把契约与测试钉死。
"""
from clause_scope.schema import VALID_CATEGORIES

#: 规则引擎的这两个产出视为「规则没把握」，才允许 LLM 补判
RULE_FALLBACKS = ("misc",)


def classify_llm(clause, classify_fn):
    """对单个条款做 LLM 辅助分类（契约校验版）。

    参数
    ----
    clause : dict
        规则引擎的条款产物（含 title/body/start/end）。
    classify_fn : callable
        注入的模型适配器，签名 ``classify_fn(clause) -> (category,
        confidence, rationale)``；category 必须是合法类别，rationale
        必须是非空字符串。

    返回
    ----
    ``(category, confidence, "llm", rationale)``——第四位是模型给出的
    理由，供报告层留痕。

    异常
    ----
    NotImplementedError
        未注入 classify_fn 时（明确暴露「还没接模型」，不装跑过）。
    ValueError
        模型返回不合法（类别越界 / 缺 rationale / 返回元数不对）。
    """
    if classify_fn is None:
        raise NotImplementedError(
            "classify_llm 是 v0.2 接口桩：需注入 classify_fn（模型适配器）后使用；"
            "规则引擎请用 extractor.classify_clause")
    result = classify_fn(clause)
    if not (isinstance(result, (tuple, list)) and len(result) == 3):
        raise ValueError(
            f"classify_fn 须返回 (category, confidence, rationale)，实际: {result!r}")
    category, confidence, rationale = result
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"classify_fn 返回未知类别 {category!r}，合法值: {sorted(VALID_CATEGORIES)}")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("classify_fn 必须给出非空 rationale（可解释性硬约束）")
    return category, confidence, "llm", rationale


def llm_assisted_extract(text, classify_fn):
    """规则优先、LLM 只补空缺的抽取入口。

    先走规则引擎 ``extract``；仅对规则产出为 fallback（misc/low）的条款
    调用 ``classify_llm`` 补判。返回与规则引擎同构的条款列表，每条追加
    ``matched_by == "llm"`` 时附带的 ``rationale`` 字段；span 全部原样保留。
    """
    from clause_scope.extractor import extract

    clauses = extract(text)
    for clause in clauses:
        category = clause.get("category")
        matched_by = clause.get("matched_by")
        if category in RULE_FALLBACKS and matched_by == "fallback":
            new_cat, _conf, _by, rationale = classify_llm(clause, classify_fn)
            clause["category"] = new_cat
            clause["matched_by"] = "llm"
            clause["rationale"] = rationale
    return clauses
