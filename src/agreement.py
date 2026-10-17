"""LLM 분류와 사용자 라벨의 일치율(9단계). 찬반·주제를 따로 정확도·Cohen's κ·혼동표로 낸다.

- 주제는 세 가지로 본다: 전체 / 사람이 no_reason으로 단 의견을 뺀 것(쉬운 범주에 부풀려지지 않게) / 이유 있음·없음 두 갈래
- 묶음 크기 가중(같은 문안을 낸 의견 수로 가중): 실제 의견 비중에 가까운 보조 지표(1015_04)
- --split dev(개선용)·eval(평가용). 모델·코드북을 고를 때는 dev만 본다. eval은 코드북 v1·v2 비교 때만
- --split eval2: 새 평가 표본 50건(코드북 v3 평가용, 의사결정 1017_02)
- 집계는 outputs/agreement.csv(공개 가능), 어긋난 건 목록은 원문이 있어 outputs/raw/

실행: python src/agreement.py --model haiku --split dev
"""
import argparse
from datetime import datetime

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from common import ROOT

LABELS = ROOT / "data" / "labels"
OUT = ROOT / "outputs"
STANCES = ["pro", "con", "unknown"]
TOPICS = ["rights", "security", "burden", "fairness", "effect", "politics", "other", "no_reason", "unclear"]


def scores(h: pd.Series, m: pd.Series, w: pd.Series | None = None) -> dict:
    w = pd.Series(1.0, index=h.index) if w is None else w
    acc = float(((h == m) * w).sum() / w.sum())
    kappa = cohen_kappa_score(h, m, sample_weight=w) if h.nunique() > 1 or m.nunique() > 1 else float("nan")
    return {"n": len(h), "accuracy": round(acc, 3), "kappa": round(float(kappa), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--codebook", default="v1")
    ap.add_argument("--split", required=True, choices=["dev", "eval", "all", "eval2"])
    args = ap.parse_args()

    sheet, prefix = ("eval2", "eval2") if args.split == "eval2" else ("review", "sample")
    human = pd.read_csv(LABELS / f"{sheet}_sheet.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    key = pd.read_csv(LABELS / f"{sheet}_key.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    if args.split == "eval2":
        key["split"] = "eval2"
    llm = pd.read_json(OUT / "raw" / f"{prefix}_{args.model}_{args.codebook}.jsonl", lines=True, dtype={"id": str})
    df = (human.merge(key[["id", "split", "group_opinions"]], on="id")
          .merge(llm[["id", "stance", "topic", "confidence", "evidence"]], on="id", suffixes=("_h", "_m")))
    if args.split != "all":
        df = df[df.split == args.split]
    w = df.group_opinions.astype(float)

    reason = df.topic_h != "no_reason"
    has_reason = lambda s: s.ne("no_reason").map({True: "reason", False: "no_reason"})
    rows = {
        "stance": scores(df.stance_h, df.stance_m),
        "topic": scores(df.topic_h, df.topic_m),
        "topic_excl_no_reason": scores(df.topic_h[reason], df.topic_m[reason]),
        "reason_vs_no_reason": scores(has_reason(df.topic_h), has_reason(df.topic_m)),
        "stance_weighted": scores(df.stance_h, df.stance_m, w),
        "topic_weighted": scores(df.topic_h, df.topic_m, w),
    }
    # 개선용 라벨은 10-17에 사용자가 다시 읽고 13칸을 고쳤다(relabel_log.csv). 평가용 라벨은 고치지 않는다
    labels = "relabeled" if (LABELS / "relabel_log.csv").exists() and args.split in ("dev", "all") else "original"
    out = pd.DataFrame([{"run_at": datetime.now().isoformat(timespec="seconds"), "model": args.model,
                         "codebook": args.codebook, "split": args.split, "labels": labels, "measure": k, **v}
                        for k, v in rows.items()])
    path = OUT / "agreement.csv"
    out.to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")
    print(out[["measure", "n", "accuracy", "kappa"]].to_string(index=False))

    print("\n찬반 혼동표(행=사람, 열=LLM)")
    print(pd.crosstab(df.stance_h, df.stance_m).to_string())
    print("\n주제 혼동표(행=사람, 열=LLM)")
    print(pd.crosstab(pd.Categorical(df.topic_h, TOPICS), pd.Categorical(df.topic_m, TOPICS), dropna=False)
          .loc[lambda t: t.sum(axis=1) > 0, lambda t: t.sum(axis=0) > 0].to_string())
    print("\n확신도별 주제 정확도")
    print(df.assign(ok=df.topic_h == df.topic_m).groupby("confidence").ok.agg(["mean", "size"]).round(2).to_string())

    miss = df[(df.topic_h != df.topic_m) | (df.stance_h != df.stance_m)]
    miss[["id", "bill", "text", "stance_h", "stance_m", "topic_h", "topic_m", "confidence", "evidence", "memo"]].to_csv(
        OUT / "raw" / f"miss_{args.model}_{args.codebook}_{args.split}.csv", index=False, encoding="utf-8-sig")
    print(f"\n어긋난 건 {len(miss)}건 → outputs/raw/miss_{args.model}_{args.codebook}_{args.split}.csv")


if __name__ == "__main__":
    main()
