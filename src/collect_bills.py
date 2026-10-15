"""열린국회정보 Open API로 입법예고 법안 목록(진행중·종료)을 받는다.

- 페이지 응답은 data/raw/api/에 그대로 저장하고, 있으면 다시 부르지 않는다
- 결과: data/raw/bills.csv (status: ongoing/closed)
"""
import json

import pandas as pd

from common import RAW, assembly_key, fetch

BASE = "https://open.assembly.go.kr/portal/openapi/"
SERVICES = {  # 서비스 코드 → 상태
    "nknalejkafmvgzmpt": "ongoing",  # 진행중 입법예고
    "nohgwtzsamojdozky": "closed",   # 종료된 입법예고
}
AGE = "22"
PAGE_SIZE = 1000
CACHE = RAW / "api"


def get_page(svc: str, page: int) -> dict:
    path = CACHE / f"{svc}_age{AGE}_p{page:03d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    params = {"KEY": assembly_key(), "Type": "json", "pIndex": page, "pSize": PAGE_SIZE, "AGE": AGE}
    data = fetch("GET", BASE + svc, params=params).json()
    if svc not in data:  # 오류 응답: {"RESULT": {...}}
        raise RuntimeError(f"{svc} p{page}: {data.get('RESULT')}")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def collect(svc: str) -> tuple[list[dict], int]:
    rows, page, total = [], 1, None
    while True:
        block = get_page(svc, page)[svc]
        total = block[0]["head"][0]["list_total_count"]
        rows += block[1]["row"]
        if len(rows) >= total:
            return rows, total
        page += 1


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = []
    for svc, status in SERVICES.items():
        rows, total = collect(svc)
        print(f"{status}: 받은 {len(rows)} / 전체 {total}")
        frames.append(pd.DataFrame(rows).assign(status=status))
    bills = pd.concat(frames, ignore_index=True)
    dup = bills.duplicated("BILL_ID").sum()
    bills = bills.drop_duplicates("BILL_ID")
    bills.to_csv(RAW / "bills.csv", index=False, encoding="utf-8-sig")
    print(f"저장 {len(bills)}건 (BILL_ID 중복 제거 {dup}건) → {RAW / 'bills.csv'}")


if __name__ == "__main__":
    main()
