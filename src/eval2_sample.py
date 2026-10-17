"""새 평가 표본 50건(의사결정 1017_02). 코드북 v3를 아직 아무도 보지 않은 의견으로 평가하려고 뽑는다.

- 처음 표본(1015_04)과 같은 방법: route=llm 고유 텍스트의 같은 문안 묶음에서, 코드북을 만들 때 읽은 묶음과
  이미 표본으로 쓴 100묶음(개선용·평가용)을 빼고, 법안별 12·13묶음 × 묶음당 1건
- 시트에는 LLM 결과 칸이 없다. 의견 번호·묶음은 key 파일에만
결과(비공개): data/labels/eval2_sheet.csv(E001～E050), data/labels/eval2_key.csv
"""
import random

import pandas as pd

from clean import CLEAN
from codebook_read import read_sample
from dedup import group_ids
from review_sample import BILL_NAMES, LABEL_COLS, LABELS

SEED = 20261017
PER_BILL = {"2214785": 12, "2218197": 13, "2211676": 12, "2208271": 13}


def main():
    df = pd.read_csv(CLEAN, dtype={"BILL_NO": str}, encoding="utf-8-sig")
    u = df[df.route == "llm"].drop_duplicates(["BILL_NO", "text"]).reset_index(drop=True)
    u["group"] = group_ids(u)  # review_sample.py와 같은 입력·같은 함수라 묶음 번호가 같다
    u["group_opinions"] = u.groupby("group").dup_n.transform("sum")

    key = pd.read_csv(LABELS / "review_key.csv", dtype=str, encoding="utf-8-sig")
    used = set(key.loc[key.side == "llm", "group"])
    read_groups = set(u.merge(read_sample()[["BILL_NO", "text"]], on=["BILL_NO", "text"]).group)
    # 묶음 번호가 처음 표본 때와 같은지 확인: 쓴 묶음마다 key의 텍스트가 그 묶음에 들어 있어야 한다
    sampled = key[key.side == "llm"].merge(u[["BILL_NO", "opnNo", "group"]].astype(str), on=["BILL_NO", "opnNo"],
                                           how="left", suffixes=("", "_now"))
    assert (sampled.group == sampled.group_now).all(), "묶음 번호가 처음 표본과 다르다"
    pool = u[~u.group.isin(read_groups | used)]

    rng = random.Random(SEED)
    picks = []
    for bill, n in PER_BILL.items():
        for gid in rng.sample(sorted(pool[pool.BILL_NO == bill].group.unique()), n):
            members = pool[pool.group == gid]
            picks.append(members.iloc[rng.randrange(len(members))].to_dict())
    s = pd.DataFrame(picks).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s["id"] = [f"E{i:03d}" for i in range(1, len(s) + 1)]
    s["bill"] = s.BILL_NO.map(BILL_NAMES)
    s[["id", "bill", "text"]].assign(**{c: "" for c in LABEL_COLS}).to_csv(
        LABELS / "eval2_sheet.csv", index=False, encoding="utf-8-sig")
    s[["id", "BILL_NO", "opnNo", "text_len", "dup_n", "group", "group_opinions"]].to_csv(
        LABELS / "eval2_key.csv", index=False, encoding="utf-8-sig")
    print(f"남은 묶음 {pool.group.nunique()}(읽은 {len(read_groups)}·쓴 {len(used)} 제외) → {len(s)}건")
    print(s.bill.value_counts().to_string())


if __name__ == "__main__":
    main()
