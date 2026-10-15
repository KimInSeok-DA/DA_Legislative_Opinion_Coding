"""법안 후보별 의견 성격을 작은 표본으로 확인한다(법안 고르기용).

법안마다: 의견 목록 첫 페이지(번호 내림차순 100건)로 최대 의견 번호·제목 반복도,
의견 번호 무작위 N건의 본문으로 비공개·짧은 의견·같은 본문 비율을 본다.
본문·제목은 저장하지 않고 집계만 data/raw/bill_candidates.csv에 남긴다.
"""
import random
import sys
from collections import Counter

import pandas as pd
from bs4 import BeautifulSoup

from common import PAL, RAW, csrf_token, fetch

LIST = PAL + "/napal/lgsltpa/lgsltpaOpn/list.do?lgsltPaId={}&searchConClosed=1"
DETAIL = PAL + "/napal/lgsltpa/lgsltpaOpn/findOneLgsltpaOpnById.json"
SHORT = 20  # 이 글자 수 미만이면 짧은 의견


def probe(bill_no: str, pid: str, n: int, rng: random.Random) -> dict:
    url = LIST.format(pid)
    token = csrf_token(fetch("GET", url).text)
    html = fetch("POST", url, data={"_csrf": token, "pageIndex": 1, "pageUnit": 100,
                                     "sortCol": "OPN_NO", "sortGbn": "DESC", "searchConRng": 0}).text
    soup = BeautifulSoup(html, "html.parser")
    total = int(soup.select_one(".board_count strong").get_text(strip=True).replace(",", ""))
    nos = [int(tr.td.get_text(strip=True)) for tr in soup.select("tr[id^=opnList_]")]
    titles = [tr.select_one("a.board_subject").get_text(strip=True) for tr in soup.select("tr[id^=opnList_]")]

    max_no = max(nos)
    bodies, hidden, missing = [], 0, 0
    for no in rng.sample(range(1, max_no + 1), n):
        j = fetch("POST", DETAIL, data={"lgsltPaId": pid, "opnNo": no},
                  headers={"X-CSRF-TOKEN": token, "requestAJAX": "true"}).json()
        res = j.get("result")
        if not res:
            missing += 1
        elif res.get("delYn") == "1":
            hidden += 1
        else:
            bodies.append(" ".join((res.get("cn") or "").split()))
        del j, res  # 작성자·연락처 필드는 쓰지 않고 버린다
    top_body = Counter(bodies).most_common(1)[0][1] if bodies else 0
    return {
        "BILL_NO": bill_no, "list_total": total, "max_opn_no": max_no,
        "page_no_gap": (nos[0] - nos[-1] + 1) - len(nos),  # 첫 페이지 안 번호 빈칸
        "title_distinct_100": len(set(titles)),
        "title_top_share": Counter(titles).most_common(1)[0][1] / len(titles),
        "sample_n": n, "hidden": hidden, "missing": missing,
        "body_distinct": len(set(bodies)), "body_top_share": round(top_body / max(len(bodies), 1), 2),
        "short_share": round(sum(len(b) < SHORT for b in bodies) / max(len(bodies), 1), 2),
        "median_len": int(pd.Series([len(b) for b in bodies]).median()) if bodies else 0,
    }


def main(bill_nos: list[str], n: int):
    counts = pd.read_csv(RAW / "site_bill_counts.csv", dtype={"BILL_NO": str}).set_index("BILL_NO")
    rng = random.Random(20261015)
    out = []
    for b in bill_nos:
        r = probe(b, counts.loc[b, "lgsltPaId"], n, rng)
        out.append(r)
        print(r)
    pd.DataFrame(out).to_csv(RAW / "bill_candidates.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main(sys.argv[2:], int(sys.argv[1]))
