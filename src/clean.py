"""수집한 의견을 정제해 분류 대상을 나눈다(의사결정 1015_01, 1015_02).

1. 공개 의견만(status=ok). 비공개·응답 없음(지워진 번호)은 뺀다
2. HTML 엔티티를 풀고(&quot; 등, 두 번 이스케이프된 것도) <br>을 공백으로, 공백을 하나로
3. 분류 텍스트 = 제목 + 본문. 제목이 본문에 이미 들어 있으면 본문만
4. 엔티티를 푼 뒤 개인정보 패턴을 다시 지운다
5. 텍스트 MIN_LEN자 미만 → route=rule("이유 없는 찬반"), 이상 → route=llm
같은 텍스트 반복은 지우지 않고 dup_n(법안 안 같은 텍스트 수)으로 표시한다.
결과: data/interim/opinions_clean.csv (원문 포함, 비공개 폴더)
"""
import html
import json
import re

import pandas as pd

from collect_opinions import OUT
from common import ROOT
from pii import scrub

MIN_LEN = 15  # 의사결정 1015_02
CLEAN = ROOT / "data" / "interim" / "opinions_clean.csv"


def norm(s: str | None) -> str:
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"(?i)<br\s*/?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def merge(title: str, body: str) -> str:
    if not title or title.rstrip(".!") in body:
        return body
    return f"{title} {body}"


def main():
    raw = pd.DataFrame(json.loads(line) for line in OUT.open(encoding="utf-8"))
    df = raw[raw.status == "ok"].copy()
    df["title"], df["body"] = df.sj.map(norm), df.cn.map(norm)
    df["text"] = [merge(t, b) for t, b in zip(df.title, df.body)]
    scrubbed = df.text.map(scrub)
    df["text"], df["pii_removed_clean"] = scrubbed.str[0], scrubbed.str[1]
    df["text_len"] = df.text.str.len()
    df["route"] = df.text_len.map(lambda n: "llm" if n >= MIN_LEN else "rule")
    df["dup_n"] = df.groupby(["BILL_NO", "text"]).text.transform("size")
    cols = ["BILL_NO", "opnNo", "opnRgDt", "inst_yn", "text", "text_len", "route", "dup_n", "pii_removed_clean"]
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(CLEAN, index=False, encoding="utf-8-sig")

    print(f"수집 {len(raw)} → 공개 {len(df)} (비공개 {(raw.status == 'hidden').sum()}, 응답 없음 {(raw.status == 'missing').sum()})")
    print(f"엔티티 남음 {df.text.str.contains(r'&(?:[a-z]+|#\d+);').sum()}, 태그 남음 {df.text.str.contains(r'<[a-zA-Z/][^>]*>').sum()}, "
          f"정제 후 지운 개인정보 패턴 {df.pii_removed_clean.sum()}")
    s = df.groupby("BILL_NO").agg(public=("text", "size"), llm=("route", lambda x: (x == "llm").sum()),
                                  rule=("route", lambda x: (x == "rule").sum()),
                                  llm_unique=("text", lambda x: x[df.loc[x.index, "route"] == "llm"].nunique()))
    s.loc["합계"] = s.sum()
    print(s.to_string())
    print(f"→ {CLEAN}")


if __name__ == "__main__":
    main()
