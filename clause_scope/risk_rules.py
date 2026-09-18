# -*- coding: utf-8 -*-
"""风险规则库：把抽取出的条款变成可解释的风险发现。

三级发现：
- MISSING  必备类别缺失（合同里根本没这一类条款）
- IMBALANCE 权利失衡（如任意解除权/违约金只约束一方）
- VAGUE    表述含糊（如争议解决未约定具体管辖地）

每条发现都带：severity（P0/P1/P2）、rule_id、说明、以及 evidence
（原文 span 或「缺失」标注）——没有依据的风险提示不输出。
"""
from clause_scope.schema import REQUIRED_CATEGORIES
from clause_scope.schema import CATEGORIES

# 单方解除/单方违约金的常见表述（用于权利失衡检测）
PENALTY_PAT = "违约金"
PENALTY_DIRECTION_PAT = "(甲|乙)方.{0,12}应.{0,10}支付.{0,10}违约金"
JURISDICTION_VAGUE_PAT = "有管辖权的人民法院"


def _span(clause):
    return {"start": clause["span"]["start"], "end": clause["span"]["end"],
            "index": clause["index"]}


def check_missing(clauses):
    """必备类别缺失检测。"""
    present = {c["category"] for c in clauses}
    findings = []
    for cat in REQUIRED_CATEGORIES:
        if cat not in present:
            findings.append({
                "severity": "P0" if cat == "liability" else "P1",
                "rule_id": "MISSING_" + cat.upper(),
                "message": u"合同未包含「%s」类条款" % CATEGORIES[cat][0],
                "evidence": None,
            })
    return findings


def _release_holders(text):
    """识别条款中被授予解除权的一方（甲方/乙方）。返回 set，如 {"乙"}。

    匹配「X方 …(任意解除|随时解除|无需…即可解除|有权解除)」；
    「任何一方有权解除」不含具体甲/乙，不计入任何一方。
    """
    import re
    holders = set()
    for m in re.finditer(r"(甲|乙)方[^。；\n]{0,10}?(任意解除|随时解除|无需[^。；\n]{0,8}即可解除|有权解除)", text):
        holders.add(m.group(1))
    return holders


def check_imbalance(clauses):
    """权利失衡检测：解除权是否只授予一方；违约金是否只约束一方。"""
    import re
    findings = []

    # 跨条款统计解除权归属（在 term_termination 类条款里找授予权利的一方）
    release = {}
    release_clauses = []
    for c in clauses:
        if c["category"] != "term_termination":
            continue
        holders = _release_holders(c["text"])
        for h in holders:
            release[h] = release.get(h, 0) + 1
            release_clauses.append(c)
    if len(release) == 1:
        side = next(iter(release))
        other = "甲" if side == "乙" else "乙"
        c = release_clauses[0]
        findings.append({
            "severity": "P1",
            "rule_id": "ONE_SIDE_RELEASE",
            "message": u"解除权仅授予%s方（未见%s方的对等解除权），权利义务失衡" % (side, other),
            "evidence": _span(c),
        })

    for c in clauses:
        if c["category"] != "liability":
            continue
        text = c["text"]
        if PENALTY_PAT in text and "双方" not in text:
            directed = re.findall(PENALTY_DIRECTION_PAT, text)
            if directed and len(set(directed)) == 1:
                findings.append({
                    "severity": "P2",
                    "rule_id": "ONE_SIDE_PENALTY",
                    "message": u"违约金条款仅约束%s方，建议核对是否双向对等" % "/".join(sorted(set(directed))),
                    "evidence": _span(c),
                })
    return findings


def check_vague(clauses):
    """表述含糊检测。"""
    import re
    findings = []
    for c in clauses:
        if c["category"] != "dispute":
            continue
        if "仲裁" not in c["text"] and re.search(JURISDICTION_VAGUE_PAT, c["text"]) \
                and not re.search(r"(甲|乙)方住所地|合同签订地|原告住所地|被告住所地|特定地点", c["text"]):
            findings.append({
                "severity": "P2",
                "rule_id": "VAGUE_JURISDICTION",
                "message": u"争议解决仅约定「有管辖权的人民法院」，未锁定连接点（住所地/签订地等）",
                "evidence": _span(c),
            })
    return findings


def analyze_risks(clauses):
    """主入口：条款列表 → 风险发现列表（按严重度排序）。"""
    findings = []
    findings.extend(check_missing(clauses))
    findings.extend(check_imbalance(clauses))
    findings.extend(check_vague(clauses))
    order = {"P0": 0, "P1": 1, "P2": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["rule_id"]))
    return findings
