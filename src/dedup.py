"""같은 문안 변형 묶기(의사결정 1015_04).

공백·기호를 뺀 텍스트를 3글자씩 잘라 조각 집합을 만들고, 같은 법안 안에서
조각 자카드 유사도(겹치는 조각 ÷ 둘 중 하나라도 가진 조각)가 THRESHOLD 이상인 쌍을 잇는다.
A~B, B~C가 이어지면 A·B·C가 한 묶음이다.
"""
import itertools
import re

import pandas as pd

THRESHOLD = 0.6
N = 3


def grams(text: str) -> set[str]:
    s = re.sub(r"[^0-9A-Za-z가-힣]", "", text)
    return {s[i:i + N] for i in range(max(1, len(s) - N + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b)


def group_ids(df: pd.DataFrame) -> pd.Series:
    """df(BILL_NO, text; 고유 텍스트) → 묶음 번호 '의안번호-대표행'. 인덱스는 df와 같다."""
    out = {}
    for bill, g in df.groupby("BILL_NO"):
        idx = list(g.index)
        gs = {i: grams(df.at[i, "text"]) for i in idx}
        parent = {i: i for i in idx}

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i, j in itertools.combinations(idx, 2):
            if jaccard(gs[i], gs[j]) >= THRESHOLD:
                parent[root(i)] = root(j)
        out.update({i: f"{bill}-{root(i)}" for i in idx})
    return pd.Series(out)
