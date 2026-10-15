"""검수 표본을 뽑고 사람이 직접 라벨을 달 시트를 만든다(7단계, 의사결정 1015_04).

- LLM 쪽: route=llm 고유 텍스트를 같은 문안 묶음으로 묶고(src/dedup.py),
  코드북을 만들 때 읽은 100건이 속한 묶음은 통째로 뺀 뒤, 법안별 25묶음 × 묶음당 1건 = 100건
  → 법안마다 개선용/평가용 반씩(13·12를 법안마다 번갈아 합계 50/50)
- 규칙 쪽: route=rule 고유 텍스트에서 법안별 5건 = 20건(1015_02 바꾸는 조건 확인용)
- 시트에는 LLM 결과 칸이 없다. 개선/평가 구분과 원래 의견 번호는 key 파일에만 둔다
결과(모두 data/labels/, 비공개): review_sheet.csv, rule_sheet.csv, review_key.csv
         data/interim/groups.csv(LLM 쪽 모든 의견의 묶음 번호, 9단계 가중 일치율용)
"""
import random

import pandas as pd

from clean import CLEAN
from codebook_read import read_sample
from common import ROOT
from dedup import group_ids

SEED = 20261015
PER_BILL, RULE_PER_BILL = 25, 5
BILL_NAMES = {"2214785": "국가보안법 폐지", "2218197": "소득세법", "2211676": "공인중개사법", "2208271": "정보통신망법"}
LABELS = ROOT / "data" / "labels"
LABEL_COLS = ["stance", "topic", "memo"]  # 찬반(pro/con/unknown), 주제(코드북 3절), 메모


def main():
    df = pd.read_csv(CLEAN, dtype={"BILL_NO": str}, encoding="utf-8-sig")
    llm = df[df.route == "llm"]
    u = llm.drop_duplicates(["BILL_NO", "text"]).reset_index(drop=True)
    u["group"] = group_ids(u)
    u["group_opinions"] = u.groupby("group").dup_n.transform("sum")  # 묶음에 든 의견 수(같은 텍스트 반복 포함)

    # LLM 쪽 모든 의견(1,270)에 묶음 번호
    groups = llm.merge(u[["BILL_NO", "text", "group", "group_opinions"]], on=["BILL_NO", "text"])
    groups[["BILL_NO", "opnNo", "group", "group_opinions"]].to_csv(
        ROOT / "data" / "interim" / "groups.csv", index=False, encoding="utf-8-sig")

    read = read_sample()
    read_groups = set(u.merge(read[["BILL_NO", "text"]], on=["BILL_NO", "text"]).group)
    pool = u[~u.group.isin(read_groups)]

    rng = random.Random(SEED)
    picks = []
    for k, bill in enumerate(BILL_NAMES):
        gids = sorted(pool[pool.BILL_NO == bill].group.unique())
        chosen = rng.sample(gids, PER_BILL)
        n_dev = 13 if k % 2 == 0 else 12
        for j, gid in enumerate(chosen):
            members = pool[pool.group == gid]
            row = members.iloc[rng.randrange(len(members))]
            picks.append({**row.to_dict(), "split": "dev" if j < n_dev else "eval", "side": "llm"})

    rule = df[df.route == "rule"].drop_duplicates(["BILL_NO", "text"])
    for bill in BILL_NAMES:
        r = rule[rule.BILL_NO == bill]
        for i in rng.sample(range(len(r)), RULE_PER_BILL):
            picks.append({**r.iloc[i].to_dict(), "split": "rule", "side": "rule", "group": "", "group_opinions": r.iloc[i].dup_n})

    s = pd.DataFrame(picks)
    s = s.sample(frac=1, random_state=SEED).reset_index(drop=True)  # 시트 순서는 법안·개선/평가가 섞이게
    s["bill"] = s.BILL_NO.map(BILL_NAMES)
    LABELS.mkdir(parents=True, exist_ok=True)
    for side, name, prefix in [("llm", "review_sheet.csv", "R"), ("rule", "rule_sheet.csv", "S")]:
        part = s[s.side == side].copy()
        part["id"] = [f"{prefix}{i:03d}" for i in range(1, len(part) + 1)]
        s.loc[part.index, "id"] = part.id
        part[["id", "bill", "text"]].assign(**{c: "" for c in LABEL_COLS}).to_csv(
            LABELS / name, index=False, encoding="utf-8-sig")
    s[["id", "side", "split", "BILL_NO", "opnNo", "text_len", "dup_n", "group", "group_opinions"]].to_csv(
        LABELS / "review_key.csv", index=False, encoding="utf-8-sig")

    print(f"LLM 쪽 고유 {len(u)}, 묶음 {u.group.nunique()} | 읽은 100건의 묶음 {len(read_groups)}개(텍스트 "
          f"{u.group.isin(read_groups).sum()}) 제외 → 남은 묶음 {pool.group.nunique()}")
    print(s.groupby(["BILL_NO", "split"]).size().unstack(fill_value=0).to_string())
    print(f"→ {LABELS}")


if __name__ == "__main__":
    main()
