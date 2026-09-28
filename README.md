English · [简体中文](./README.zh-CN.md)

# clause-scope · Deterministic Clause Extraction & Risk Flagging

Turn a full contract text into a **clause inventory + risk findings**, with every result **traceable back to the source text**. v0.1 is a **deterministic rule engine** — every classification and risk finding is explainable, testable, and reproducible, with **no LLM involved**.

**Current version v0.1: rule engine + evaluation on fictional labeled samples. Evaluation on a real-contract corpus is on the roadmap and outside the current claims.**

## The problem

The first step of contract review is not "giving advice" — it is establishing **what the contract contains, and what it is missing**:

- Which clause number each of the 8+ key clause types (price, delivery, confidentiality, liability for breach, dispute resolution, …) sits at, and what the original text says;
- **Missing mandatory clauses** (a contract without a liability-for-breach clause carries a risk anyone can sense, legal training or not);
- **Rights imbalance** (termination / liquidated-damages clauses binding only one party) and **vague wording** (e.g. "the people's court with jurisdiction" without locking down the connecting point);
- Every risk finding must carry source-text evidence or an explicit "missing" tag — **flags without evidence are not emitted**.

## Scope (what this deliberately does not do)

- **A rule engine is not an LLM**: classification relies on strong title signals plus body keyword voting; complex phrasing (e.g. an implicit liability clause titled "compensation for losses" standing in for "liability for breach") may be missed. LLM-assisted classification belongs to v0.2; the interface is already reserved (`classify_llm`).
- **The samples are fictional**: the current evaluation is based on 3 fully fictional labeled contracts (25 clauses) and validates rule behavior only. The acceptance gate for real contracts (≥30 contracts, field accuracy ≥85%) will **not be pre-filled with numbers** before the corpus is in place.
- **Not legal advice**: the output is an auxiliary checklist for verification; human judgment cannot be skipped.

## How it works

```
Contract text ──extractor──> clause inventory (numbered segmentation + classification + span offsets)
                   │           · Title pattern = strong signal (direct classification)
                   │           · Body-wide voting across all categories, ≥2 = weak signal
                   │           · No numbered structure → whole-document single-clause fallback (content is never silently dropped)
                   ▼
             risk_rules (three tiers of findings, sorted by severity)
             ├── MISSING   mandatory category absent (liability for breach = P0)
             ├── IMBALANCE termination right granted to one side only / one-way liquidated damages
             └── VAGUE     jurisdiction without a locked connecting point, etc.
                   ▼
             report (Markdown / JSON, each finding carries a source excerpt for back-reference)
```

Key design decisions:

- **Span back-referencing is a hard constraint**: all extractor output carries original-text offsets, and the report layer emits the source excerpt alongside every finding;
- **Termination rights are assessed across clauses**: for text such as "Party B may terminate at any time … without Party A's consent", where both parties appear inside one clause, the judgment is based on who is granted the termination right and whether the other side holds a symmetric right — not on counting how many parties are mentioned.

## Install & usage

- **Dependencies**: Python 3 only — the v0.1 rule engine uses nothing beyond the Python standard library (zero third-party dependencies, see `requirements.txt`). Tests verified on Python 3.13.
- **Analyze a contract** (writes a Markdown + JSON report):

```bash
python scripts/analyze.py contracts/sample_contract.txt --out data/report
# 条款：8 ｜ 发现：2（P0 0 / P1 1 / P2 1）
# (Clauses: 8 | Findings: 2 (P0 0 / P1 1 / P2 1))
```

- **Reproduce the evaluation**: `python scripts/run_eval.py` (gold labels: `sample_data/labels.json`; report: `docs/eval_report.md`)
- **Run the unit tests** (18 cases): `python -m unittest discover -s tests`

## Evaluation (real numbers, not fabricated; the samples are fictional contracts)

| Metric | Result |
|---|---|
| Clause classification accuracy | 100.0% (25/25) |
| Span traceability validity | 100.0% (25/25) |
| Risk detection rate (recall) | 100.0% (4/4) |
| Risk-flagging precision | **80.0% (4/5)** |

Full evaluation report with per-sample results: [docs/eval_report.md](docs/eval_report.md).

- The **known source of false positives** behind the sub-perfect precision: conditional termination rights (e.g. "Party A may terminate") are counted as one-sided termination; the finer distinction between "termination with conditions" and "termination at will" belongs to v0.2 — noted in both the rules and the report.

## Roadmap

- **v0.2**: LLM-assisted classification (rule results serve as the prior; low-confidence clauses go to the model for review) + finer rules separating conditional from at-will termination + labeled evaluation on real contracts (≥30 contracts)
- **v0.3**: chain with [statute-rag](https://github.com/1438388098-glitch/statute-rag) — risk findings automatically feed "statutory basis" retrieval; preference-library comparison (baselines for own-side-position clauses)

## License

[MIT](LICENSE)
