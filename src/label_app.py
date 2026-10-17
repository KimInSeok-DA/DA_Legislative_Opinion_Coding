"""사람 검수용 라벨 화면(7단계). 의견을 하나씩 보여 주고 찬반·주제를 버튼으로 고른다.

- 시트: data/labels/review_sheet.csv(검수 표본 100건), rule_sheet.csv(규칙 쪽 20건)
- 저장할 때마다 같은 CSV에 바로 쓴다 → 끄고 다시 켜도 이어서 단다
- LLM 결과와 개선/평가 구분(review_key.csv)은 읽지 않는다. 답을 미리 보고 따라가지 않게
- 건마다 라벨에 걸린 시간을 label_times.csv에 남긴다(사람 검수 시간과 LLM 분류 시간을 비교하려고)

실행: streamlit run src/label_app.py
"""
import html
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
LABELS = Path(os.getenv("LABEL_DIR", ROOT / "data" / "labels"))  # 시험할 때만 다른 폴더로
CODEBOOK = ROOT / "docs" / "코드북.md"
# 다시 달기: 평가용 50건을 순서를 섞고 번호를 새로 붙인 시트(사람 자기 일치도, 의사결정 1017_01). 이전 라벨은 보이지 않는다
SHEETS = {"검수 표본 (100건)": "review_sheet.csv", "규칙 쪽 (20건)": "rule_sheet.csv",
          "다시 달기 (50건)": "recheck_sheet.csv", "새 평가 (50건)": "eval2_sheet.csv"}
TIMES = LABELS / "label_times.csv"
BILL_NOS = {"국가보안법 폐지": "2214785", "소득세법": "2218197", "공인중개사법": "2211676", "정보통신망법": "2208271"}

STANCES = {"pro": "찬성", "con": "반대", "unknown": "불명"}
TOPICS = {
    "rights": "권리·자유", "security": "안보·체제", "burden": "경제적 부담", "fairness": "공정·형평",
    "effect": "효과·필요성", "politics": "정치적 의도", "other": "기타 이유",
    "no_reason": "이유 없는 찬반", "unclear": "판단 불가",
}


@st.cache_data
def codebook_sections() -> dict[str, str]:
    """코드북에서 화면에 띄울 부분: 3절(주제 한눈에), 4절(판단 순서), 6절 법안별 맥락."""
    md = CODEBOOK.read_text(encoding="utf-8")

    def between(start: str, end_pattern: str) -> str:
        i = md.index(start)
        m = re.compile(end_pattern, re.M).search(md, i + len(start))
        return md[i:m.start() if m else len(md)].strip()

    out = {"topics": between("## 3. 주제 한눈에", r"^## "), "order": between("## 4. 판단 순서", r"^## 5\.")}
    for no in BILL_NOS.values():
        out[no] = between(f"### {no}", r"^##")
    return out


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def save(df: pd.DataFrame, path: Path) -> bool:
    tmp = path.with_suffix(".tmp")
    try:
        df.to_csv(tmp, index=False, encoding="utf-8-sig")
        os.replace(tmp, path)  # 다 쓴 뒤에 바꿔치기 → 저장 중에 꺼져도 시트가 깨지지 않는다
        return True
    except PermissionError:
        st.error("저장 실패: 시트가 엑셀 등 다른 프로그램에 열려 있습니다. 닫고 다시 저장하세요.")
        return False


def log_time(sheet: str, item_id: str, seconds: float):
    row = pd.DataFrame([{"sheet": sheet, "id": item_id, "seconds": round(seconds, 1),
                         "saved_at": datetime.now().isoformat(timespec="seconds")}])
    row.to_csv(TIMES, mode="a", header=not TIMES.exists(), index=False, encoding="utf-8-sig")


def first_unlabeled(df: pd.DataFrame) -> int:
    todo = df.index[(df.stance == "") | (df.topic == "")]
    return int(todo[0]) if len(todo) else len(df) - 1


def go(i: int):
    st.session_state.idx = i
    st.session_state.started = time.monotonic()


def main():
    st.set_page_config(page_title="의견 라벨", layout="wide")
    cb = codebook_sections()

    with st.sidebar:
        sheet_name = st.radio("시트", list(SHEETS), key="sheet")
        path = LABELS / SHEETS[sheet_name]
        df = load(path)
        done = int(((df.stance != "") & (df.topic != "")).sum())
        st.progress(done / len(df), text=f"{done} / {len(df)}건 완료")
        if st.session_state.get("loaded_sheet") != sheet_name:  # 시트를 바꾸면 안 단 곳부터
            st.session_state.loaded_sheet = sheet_name
            go(first_unlabeled(df))
        st.button("안 단 곳으로", on_click=go, args=(first_unlabeled(df),), width="stretch")
        with st.expander("주제 한눈에 (코드북 3절)", expanded=True):
            st.markdown(cb["topics"])
        with st.expander("판단 순서 (코드북 4절)"):
            st.markdown(cb["order"])

    i = min(st.session_state.idx, len(df) - 1)
    row = df.loc[i]
    st.caption(f"{row.id}  ·  {i + 1} / {len(df)}")
    st.subheader(row.bill)
    st.markdown(f"<div style='font-size:1.15rem; line-height:1.7; padding:1rem; border:1px solid #8884; "
                f"border-radius:8px'>{html.escape(row.text)}</div>",
                unsafe_allow_html=True)
    with st.expander("법안 맥락과 적용 (코드북 6절)"):
        st.markdown(cb[BILL_NOS[row.bill]])

    left, right = st.columns([1, 2])
    with left:
        stance = st.radio("찬반", list(STANCES), format_func=lambda k: f"{STANCES[k]} ({k})",
                          index=list(STANCES).index(row.stance) if row.stance in STANCES else None,
                          key=f"stance_{sheet_name}_{row.id}")
    with right:
        topic = st.radio("주제", list(TOPICS), format_func=lambda k: f"{TOPICS[k]} ({k})", horizontal=True,
                         index=list(TOPICS).index(row.topic) if row.topic in TOPICS else None,
                         key=f"topic_{sheet_name}_{row.id}")
    memo = st.text_input("메모 (망설였을 때만)", value=row.memo, key=f"memo_{sheet_name}_{row.id}")

    prev_col, save_col, next_col = st.columns([1, 2, 1])
    prev_col.button("← 이전", on_click=go, args=(max(i - 1, 0),), disabled=i == 0, width="stretch")
    next_col.button("다음 →", on_click=go, args=(min(i + 1, len(df) - 1),), disabled=i == len(df) - 1,
                    width="stretch")
    if save_col.button("저장하고 다음", type="primary", width="stretch"):
        if stance is None or topic is None:
            st.warning("찬반과 주제를 모두 고르세요.")
        else:
            df.loc[i, ["stance", "topic", "memo"]] = [stance, topic, memo.strip()]
            if save(df, path):
                log_time(SHEETS[sheet_name], row.id, time.monotonic() - st.session_state.started)
                go(min(i + 1, len(df) - 1) if i < len(df) - 1 else i)
                st.rerun()
    if done == len(df):
        st.success("이 시트는 모두 달았습니다.")


if __name__ == "__main__":
    main()
