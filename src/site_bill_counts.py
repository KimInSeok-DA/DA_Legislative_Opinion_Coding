"""국회입법예고 「종료된 입법예고」 목록을 의견 수 내림차순으로 받아 법안별 의견 수를 얻는다.

Open API 목록에는 의견 수가 없어서 사이트 목록을 쓴다(10-15 확인).
결과: data/raw/site_bill_counts.csv (BILL_NO, lgsltPaId, committee, opn_cnt, rank)
"""
import re
import sys

import pandas as pd
from bs4 import BeautifulSoup

from common import PAL, RAW, csrf_token, fetch

URL = PAL + "/napal/lgsltpa/lgsltpaDone/list.do?searchConClosed=1&menuNo=1100027"
AGE = 22
PAGE_UNIT = 100


def parse(html: str) -> list[dict]:
    rows = []
    for tr in BeautifulSoup(html, "html.parser").select("table")[0].select("tbody tr"):
        td = tr.find_all("td", recursive=False)
        link = tr.select_one("a.board_subject")
        if len(td) < 8 or not link:
            continue
        rows.append({
            "BILL_NO": td[0].get_text(strip=True),
            "lgsltPaId": re.search(r"lgsltPaId=(\w+)", link["href"]).group(1),
            "committee": td[3].get_text(strip=True),
            "opn_cnt": int(td[7].get_text(strip=True).replace(",", "")),
        })
    return rows


def main(pages: int):
    token = csrf_token(fetch("GET", URL).text)
    rows = []
    for page in range(1, pages + 1):
        data = {"_csrf": token, "pageIndex": page, "pageUnit": PAGE_UNIT,
                "sortCol": "OPN_CNT", "sortGbn": "DESC", "fromAge": AGE, "toAge": AGE}
        rows += parse(fetch("POST", URL, data=data).text)
    df = pd.DataFrame(rows)
    df["rank"] = range(1, len(df) + 1)
    df.to_csv(RAW / "site_bill_counts.csv", index=False, encoding="utf-8-sig")
    print(f"{len(df)}개 법안 저장, 의견 수 {df.opn_cnt.max():,}～{df.opn_cnt.min():,}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
