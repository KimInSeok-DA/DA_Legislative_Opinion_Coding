"""고른 법안의 「제안이유 및 주요내용」을 국회입법예고 법안 페이지에서 읽는다(코드북의 법안 맥락용).

- 법안 페이지(bills.csv의 LINK_URL)는 data/raw/bill_pages/에 저장하고, 있으면 다시 부르지 않는다
- 결과는 화면에만 보여 준다. 코드북에는 요약해서 출처와 함께 쓴다
"""
import pandas as pd
from bs4 import BeautifulSoup

from collect_opinions import BILLS
from common import RAW, fetch

PAGES = RAW / "bill_pages"


def summary(bill_no: str, url: str) -> str:
    path = PAGES / f"{bill_no}.html"
    if not path.exists():
        PAGES.mkdir(parents=True, exist_ok=True)
        path.write_text(fetch("GET", url).text, encoding="utf-8")
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    h4 = next(t for t in soup.select("h4") if "제안이유" in t.get_text())
    return h4.find_next_sibling("div").get_text("\n", strip=True)


def main():
    bills = pd.read_csv(RAW / "bills.csv", dtype=str, encoding="utf-8-sig").set_index("BILL_NO")
    for no in BILLS:
        b = bills.loc[no]
        print(f"\n===== {no} {b.BILL_NAME} ({b.PROPOSER}, {b.CURR_COMMITTEE}, 예고 종료 {b.NOTI_ED_DT}) =====")
        print(summary(no, b.LINK_URL))


if __name__ == "__main__":
    main()
