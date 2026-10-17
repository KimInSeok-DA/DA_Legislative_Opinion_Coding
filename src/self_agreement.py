"""사람 자기 일치도(9단계, 의사결정 1017_01). 평가용 50건을 LLM 결과 없이 다시 단 라벨과 비교한다.

세 쌍: 원래 라벨 ↔ 다시 단 라벨(사람 자기 일치도), LLM ↔ 원래 라벨(주 지표), LLM ↔ 다시 단 라벨
- 다시 단 라벨로 원래 라벨을 고치지 않는다
- 집계는 outputs/self_agreement.csv(공개 가능), 건별 비교는 원문이 있어 outputs/raw/

실행: python src/self_agreement.py [--model sonnet --codebook v2]
"""
import argparse
from datetime import datetime

import pandas as pd

from agreement import LABELS, OUT, TOPICS, scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--codebook", default="v2")
    args = ap.parse_args()

    read = lambda name: pd.read_csv(LABELS / name, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    first = read("review_sheet.csv")  # 평가용은 고친 적 없음
    second = read("recheck_sheet.csv").merge(read("recheck_key.csv"), on="id")
    llm = pd.read_json(OUT / "raw" / f"sample_{args.model}_{args.codebook}.jsonl", lines=True, dtype={"id": str})
    df = (second[["review_id", "stance", "topic", "memo"]].rename(columns={"review_id": "id"})
          .merge(first[["id", "bill", "text", "stance", "topic", "memo"]], on="id", suffixes=("_2", "_1"))
          .merge(llm[["id", "stance", "topic", "confidence"]].rename(columns={"stance": "stance_m", "topic": "topic_m"}),
                 on="id"))
    assert len(df) == 50 and (df.stance_2 != "").all() and (df.topic_2 != "").all()

    pairs = {"사람1-사람2": ("1", "2"), "LLM-사람1": ("m", "1"), "LLM-사람2": ("m", "2")}
    rows = []
    for name, (a, b) in pairs.items():
        ra, rb = df[f"topic_{a}"], df[f"topic_{b}"]
        reason = (df.topic_1 != "no_reason") if "1" in (a, b) else (df.topic_2 != "no_reason")
        for measure, (x, y) in {"stance": (df[f"stance_{a}"], df[f"stance_{b}"]), "topic": (ra, rb),
                                "topic_excl_no_reason": (ra[reason], rb[reason])}.items():
            rows.append({"pair": name, "measure": measure, **scores(x, y)})
    out = pd.DataFrame(rows).assign(run_at=datetime.now().isoformat(timespec="seconds"),
                                    model=args.model, codebook=args.codebook)
    out.to_csv(OUT / "self_agreement.csv", index=False, encoding="utf-8-sig")
    print(out.pivot(index="measure", columns="pair", values=["accuracy", "kappa"]).to_string())

    print("\n주제 혼동표(행=사람1, 열=사람2)")
    print(pd.crosstab(pd.Categorical(df.topic_1, TOPICS), pd.Categorical(df.topic_2, TOPICS))
          .loc[lambda t: t.sum(axis=1) > 0, lambda t: t.sum(axis=0) > 0].to_string())
    same12, same_m1, same_m2 = (df.topic_1 == df.topic_2), (df.topic_m == df.topic_1), (df.topic_m == df.topic_2)
    print(f"\n주제: 셋 다 같음 {(same12 & same_m1).sum()}, 사람끼리만 같음 {(same12 & ~same_m1).sum()}, "
          f"LLM이 사람1과만 {(same_m1 & ~same12).sum()}, LLM이 사람2와만 {(same_m2 & ~same12).sum()}, "
          f"셋 다 다름 {(~same12 & ~same_m1 & ~same_m2).sum()}")
    df.to_csv(OUT / "raw" / "self_agreement_items.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
