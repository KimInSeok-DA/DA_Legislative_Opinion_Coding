"""고른 법안의 의견을 의견 번호 무작위 표본으로 받는다(의사결정 1015_01).

- 법안마다 의견 번호 1～N에서 SAMPLE_N건을 시드 고정으로 뽑는다(N = 사이트 목록 건수)
- 의견 1건 = 본문 요청 1번. 응답에서 KEEP 필드만 남기고 작성자·연락처 필드는 버린다
- 제목·본문의 개인정보 패턴은 저장 전에 지운다(src/pii.py)
- 한 건 받을 때마다 data/raw/opinions.jsonl에 추가 → 중단 후 다시 실행하면 받은 번호는 건너뛴다

사용: python src/collect_opinions.py [--limit K]   (K: 법안당 앞에서 K건만, 시험용)
"""
import argparse
import json
import random

import pandas as pd
from bs4 import BeautifulSoup

from common import PAL, RAW, csrf_token, fetch
from pii import scrub

BILLS = ["2214785", "2218197", "2211676", "2208271"]  # 의사결정 1015_01
SAMPLE_N = 500
SEED = 20261015
LIST = PAL + "/napal/lgsltpa/lgsltpaOpn/list.do?lgsltPaId={}&searchConClosed=1"
DETAIL = PAL + "/napal/lgsltpa/lgsltpaOpn/findOneLgsltpaOpnById.json"
KEEP = ["lgsltPaId", "opnNo", "sj", "cn", "opnRgDt", "opbYn", "delYn"]
OUT = RAW / "opinions.jsonl"


def sample_numbers(bill_no: str, total: int) -> list[int]:
    """법안마다 같은 결과가 나오는 무작위 번호. --limit은 이 목록의 앞부분만 쓴다."""
    return random.Random(f"{SEED}-{bill_no}").sample(range(1, total + 1), SAMPLE_N)


def open_bill(pid: str) -> tuple[str, int]:
    """의견 목록 페이지에서 (CSRF 토큰, 전체 의견 수)."""
    html = fetch("GET", LIST.format(pid)).text
    total = BeautifulSoup(html, "html.parser").select_one(".board_count strong").get_text(strip=True)
    return csrf_token(html), int(total.replace(",", ""))


def get_opinion(pid: str, no: int, token: str) -> dict:
    j = fetch("POST", DETAIL, data={"lgsltPaId": pid, "opnNo": no},
              headers={"X-CSRF-TOKEN": token, "requestAJAX": "true"}).json()
    res = j.get("result")
    if not res:
        return {"lgsltPaId": pid, "opnNo": no, "status": "missing", "pii_removed": 0}
    rec = {k: res.get(k) for k in KEEP}  # 허용 필드만. 나머지(작성자·연락처)는 여기서 버린다
    rec["inst_yn"] = "Y" if res.get("opnSbmInstNm") else "N"  # 기관 의견 여부만(기관명은 저장 안 함)
    removed = 0
    for k in ("sj", "cn"):
        rec[k], n = scrub(rec[k] or "")
        removed += n
    rec["status"] = "hidden" if rec["delYn"] == "1" else "ok"
    rec["pii_removed"] = removed
    return rec


def done_keys() -> set[tuple[str, int]]:
    if not OUT.exists():
        return set()
    with OUT.open(encoding="utf-8") as f:
        return {(r["lgsltPaId"], r["opnNo"]) for r in map(json.loads, f)}


def main(limit: int | None):
    counts = pd.read_csv(RAW / "site_bill_counts.csv", dtype={"BILL_NO": str}).set_index("BILL_NO")
    done = done_keys()
    with OUT.open("a", encoding="utf-8") as f:
        for bill in BILLS:
            pid = counts.loc[bill, "lgsltPaId"]
            token, total = open_bill(pid)
            nos = sample_numbers(bill, total)[:limit]
            todo = [n for n in nos if (pid, n) not in done]
            print(f"{bill}: 전체 {total:,}, 표본 {len(nos)}, 이미 받음 {len(nos) - len(todo)}, 받을 것 {len(todo)}")
            for i, no in enumerate(todo, 1):
                rec = get_opinion(pid, no, token)
                rec["BILL_NO"], rec["list_total"] = bill, total
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                if i % 100 == 0:
                    print(f"  {i}/{len(todo)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    main(ap.parse_args().limit)
