"""수집 결과 대조: 법안별 표본 수 = 저장 수, 중복 0, 개인정보 패턴 0, 저장 필드 확인.

집계(본문 없음)만 outputs/collection_summary.csv로 저장한다.
"""
import json

import pandas as pd

from collect_opinions import BILLS, KEEP, OUT, SAMPLE_N
from common import ROOT
from pii import count

ALLOWED = set(KEEP) | {"inst_yn", "status", "pii_removed", "BILL_NO", "list_total"}
SHORT = 20  # 의사결정 1015_01 잠정 기준


def main():
    rows = [json.loads(line) for line in OUT.open(encoding="utf-8")]
    df = pd.DataFrame(rows)
    extra = set(df.columns) - ALLOWED
    dup = df.duplicated(["lgsltPaId", "opnNo"]).sum()
    pii_left = sum(count((r.get("sj") or "") + " " + (r.get("cn") or "")) for r in rows)
    print(f"저장 {len(df)}건 / 목표 {len(BILLS) * SAMPLE_N} | 중복 {dup} | 허용 밖 필드 {sorted(extra) or 0} | "
          f"남은 개인정보 패턴 {pii_left} | 저장 전 지운 패턴 {df.pii_removed.sum()}")

    ok = df[df.status == "ok"].copy()
    ok["len"] = ok.cn.fillna("").str.split().str.join(" ").str.len()
    s = df.groupby("BILL_NO").agg(list_total=("list_total", "first"), saved=("opnNo", "size"),
                                  ok=("status", lambda x: (x == "ok").sum()),
                                  hidden=("status", lambda x: (x == "hidden").sum()),
                                  missing=("status", lambda x: (x == "missing").sum()),
                                  inst=("inst_yn", lambda x: (x == "Y").sum()))
    s["len_ge20"] = ok[ok.len >= SHORT].groupby("BILL_NO").size()
    s["len_median"] = ok.groupby("BILL_NO").len.median()
    s["body_top_share"] = ok.groupby("BILL_NO").cn.agg(lambda x: x.value_counts().iloc[0] / len(x)).round(3)
    s = s.reindex(BILLS).fillna(0)
    print(s.to_string())
    out = ROOT / "outputs" / "collection_summary.csv"
    s.to_csv(out, encoding="utf-8-sig")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
