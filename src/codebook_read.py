"""코드북 v1을 만들 때 읽을 의견을 뽑아 화면에만 보여 준다(6단계, 의사결정 1015_03).

- route=llm 의견의 고유 텍스트를 법안마다 시드 고정으로 섞어 앞에서부터 쓴다
  1차(초안용) 법안당 N_DRAFT건, 2차(초안 점검용) 그다음 N_CHECK건
- 원문은 파일로 저장하지 않는다
- 7단계 검수 표본은 여기서 읽은 텍스트를 빼고 뽑는다(코드북을 만든 의견으로 평가하지 않기 위해)

사용: python src/codebook_read.py 1|2
"""
import sys

import pandas as pd

from clean import CLEAN

SEED = 20261015
N_DRAFT, N_CHECK = 15, 10


def read_sample() -> pd.DataFrame:
    """법안마다 고유 텍스트 N_DRAFT + N_CHECK건. round 1 = 초안용, 2 = 점검용."""
    df = pd.read_csv(CLEAN, dtype={"BILL_NO": str}, encoding="utf-8-sig")
    u = df[df.route == "llm"].drop_duplicates(["BILL_NO", "text"]).sample(frac=1, random_state=SEED)
    u["order"] = u.groupby("BILL_NO").cumcount()
    u = u[u.order < N_DRAFT + N_CHECK].copy()
    u["round"] = (u.order >= N_DRAFT).map({False: 1, True: 2})
    return u.sort_values(["BILL_NO", "order"])


def main():
    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    s = read_sample()
    for bill, g in s[s["round"] == rnd].groupby("BILL_NO"):
        print(f"\n===== {bill} ({rnd}차 {len(g)}건) =====")
        for r in g.itertuples():
            print(f"\n[{r.order + 1}] {r.text_len}자, 법안 안 같은 텍스트 {r.dup_n}건\n{r.text}")


if __name__ == "__main__":
    main()
