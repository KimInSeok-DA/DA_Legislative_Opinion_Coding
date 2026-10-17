"""전체 결과 합치기(10단계). 공개 의견 1,843건 모두에 찬반·주제를 붙여 SQLite와 집계표로 낸다.

- 15자 이상(route=llm): LLM 전체 분류 결과(outputs/raw/all_sonnet_v3.jsonl)를 같은 법안·같은 텍스트 의견 모두에 붙인다
- 15자 미만(route=rule): 주제는 규칙으로 no_reason(1015_02). 찬반은 낱말 규칙(stance_rule) — 규칙 쪽 20건 사람 라벨로 확인
- SQLite(data/interim/coding.db, 원문이 있어 비공개): opinions, human_labels, agreement, llm_runs
- 공개 집계: outputs/topic_by_bill.csv, outputs/stance_by_bill.csv(건수만)

실행: python src/build_db.py
"""
import sqlite3

import pandas as pd

from clean import CLEAN
from common import ROOT
from review_sample import BILL_NAMES

OUT = ROOT / "outputs"
LABELS = ROOT / "data" / "labels"
DB = ROOT / "data" / "interim" / "coding.db"
LLM = OUT / "raw" / "all_sonnet_v3.jsonl"


def stance_rule(text: str) -> str:
    """짧은 의견의 찬반. '반대'(오타 '반다'·'반닥' 포함)가 있으면 반대, 없고 찬성·동의가 있으면 찬성.
    국가보안법 폐지안에서 '폐지 반대'도 '반대'라 그대로 반대가 된다(코드북 2절)."""
    if any(w in text for w in ("반대", "반다", "반닥")):
        return "con"
    if any(w in text for w in ("찬성", "동의", "찬송")):
        return "pro"
    return "unknown"


def main():
    df = pd.read_csv(CLEAN, dtype={"BILL_NO": str, "opnNo": str}, encoding="utf-8-sig")
    df["bill"] = df.BILL_NO.map(BILL_NAMES)

    # 규칙 쪽 찬반 확인: 사람 라벨 20건
    rule_sheet = pd.read_csv(LABELS / "rule_sheet.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    hit = (rule_sheet.text.map(stance_rule) == rule_sheet.stance)
    print(f"찬반 낱말 규칙 vs 사람(규칙 쪽 20건): {hit.sum()}/{len(hit)}")

    # LLM 쪽: 고유 텍스트 id(법안번호_처음 의견 번호) → 같은 텍스트의 모든 의견
    llm = pd.read_json(LLM, lines=True, dtype={"id": str})
    first = df[df.route == "llm"].drop_duplicates(["BILL_NO", "text"]).assign(id=lambda d: d.BILL_NO + "_" + d.opnNo)
    llm = llm.merge(first[["id", "BILL_NO", "text"]], on="id")
    assert len(llm) == len(first), "전체 분류가 끝나지 않았다"
    lside = df[df.route == "llm"].merge(llm[["BILL_NO", "text", "stance", "topic", "confidence", "evidence"]],
                                        on=["BILL_NO", "text"])
    rside = df[df.route == "rule"].assign(stance=lambda d: d.text.map(stance_rule), topic="no_reason",
                                          confidence="rule", evidence="")
    ops = pd.concat([lside, rside], ignore_index=True)
    groups = pd.read_csv(ROOT / "data" / "interim" / "groups.csv", dtype=str, encoding="utf-8-sig")
    ops = ops.merge(groups[["BILL_NO", "opnNo", "group"]], on=["BILL_NO", "opnNo"], how="left")
    assert len(ops) == len(df)
    cols = ["BILL_NO", "bill", "opnNo", "opnRgDt", "route", "text", "text_len", "dup_n", "group",
            "stance", "topic", "confidence", "evidence"]
    ops = ops[cols].sort_values(["BILL_NO", "opnNo"], key=lambda s: s.astype(int) if s.name == "opnNo" else s)

    # 사람 라벨(검수 표본·새 평가 표본)과 의견 번호 연결
    human = []
    for sheet, key, split_col in [("review_sheet", "review_key", "split"), ("eval2_sheet", "eval2_key", None)]:
        s = pd.read_csv(LABELS / f"{sheet}.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
        k = pd.read_csv(LABELS / f"{key}.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
        s = s.merge(k[["id", "BILL_NO", "opnNo"] + ([split_col] if split_col else [])], on="id")
        human.append(s.assign(split=s[split_col] if split_col else "eval2"))
    human = pd.concat(human)[["id", "split", "BILL_NO", "opnNo", "stance", "topic", "memo"]]

    DB.unlink(missing_ok=True)
    with sqlite3.connect(DB) as con:
        ops.to_sql("opinions", con, index=False)
        human.to_sql("human_labels", con, index=False)
        pd.read_csv(OUT / "agreement.csv", encoding="utf-8-sig").to_sql("agreement", con, index=False)
        pd.read_csv(OUT / "llm_runs.csv", encoding="utf-8-sig").to_sql("llm_runs", con, index=False)

    # 공개 집계(건수·비율만)
    t = ops.groupby(["bill", "topic"]).size().rename("n").reset_index()
    t["share"] = (t.n / t.groupby("bill").n.transform("sum")).round(3)
    t.to_csv(OUT / "topic_by_bill.csv", index=False, encoding="utf-8-sig")
    st = ops.groupby(["bill", "stance"]).size().rename("n").reset_index()
    st["share"] = (st.n / st.groupby("bill").n.transform("sum")).round(3)
    st.to_csv(OUT / "stance_by_bill.csv", index=False, encoding="utf-8-sig")

    print(f"의견 {len(ops)}건(LLM {len(lside)}, 규칙 {len(rside)}) → {DB}")
    print(ops.pivot_table(index="topic", columns="bill", values="opnNo", aggfunc="count", fill_value=0,
                          margins=True).to_string())
    print(ops.pivot_table(index="stance", columns="bill", values="opnNo", aggfunc="count", fill_value=0,
                          margins=True).to_string())
    print("규칙 쪽 찬반 불명:", (rside.stance == "unknown").sum())


if __name__ == "__main__":
    main()
