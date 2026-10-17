"""결과 대시보드(11단계). 전체 분류 결과·일치율·검토 대상을 한 화면에서 본다.

- 읽는 것: data/interim/coding.db(src/build_db.py), outputs/self_agreement.csv, outputs/raw/eval2_sonnet_v3.jsonl
- 원문이 보이는 것은 '검토' 탭뿐이다. 화면을 캡처해 공개할 때는 이 탭을 빼고, 나머지 탭은 건수·비율만 보인다
- 수치는 모두 의견 1건 = 1로 센다(같은 문안을 여러 사람이 냈으면 그 수만큼)

실행: streamlit run src/dashboard.py
"""
import sqlite3

import altair as alt
import pandas as pd
import streamlit as st

from common import ROOT

DB = ROOT / "data" / "interim" / "coding.db"
OUT = ROOT / "outputs"
TOPICS = {
    "rights": "권리·자유", "security": "안보·체제", "burden": "경제적 부담", "fairness": "공정·형평",
    "effect": "효과·필요성", "politics": "정치적 의도", "other": "기타 이유",
    "no_reason": "이유 없는 찬반", "unclear": "판단 불가",
}
STANCES = {"pro": "찬성", "con": "반대", "unknown": "불명"}
CONF = {"high": "높음", "medium": "중간", "low": "낮음", "rule": "규칙(15자 미만)"}
BILLS = ["국가보안법 폐지", "소득세법", "공인중개사법", "정보통신망법"]
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"  # 찬반은 찬성·반대 두 색 + 불명은 중립 회색
def theme_colors() -> tuple[str, str]:
    """(보조 글자색, 화면 배경색). 막대 끝 숫자와 칸 사이 틈을 밝은·어두운 화면에 맞춘다."""
    dark = getattr(getattr(st.context, "theme", None), "type", None) == "dark"
    return ("#c3c2b7", "#0e1117") if dark else ("#52514e", "#ffffff")


SOURCE = "출처: 열린국회정보(진행중/종료된 입법예고), 국회입법예고, 조회 2026-10-15"


@st.cache_data
def load():
    with sqlite3.connect(DB) as con:
        ops = pd.read_sql("select * from opinions", con)
        human = pd.read_sql("select * from human_labels", con)
        agree = pd.read_sql("select * from agreement", con)
        runs = pd.read_sql("select * from llm_runs", con)
    selfa = pd.read_csv(OUT / "self_agreement.csv", encoding="utf-8-sig")
    llm2 = pd.read_json(OUT / "raw" / "eval2_sonnet_v3.jsonl", lines=True, dtype={"id": str})
    ops["주제"] = ops.topic.map(TOPICS)
    ops["찬반"] = ops.stance.map(STANCES)
    return ops, human, agree, runs, selfa, llm2


def share_table(ops: pd.DataFrame, col: str) -> pd.DataFrame:
    t = ops.groupby(["bill", col]).size().rename("의견 수").reset_index()
    t["비율"] = t["의견 수"] / t.groupby("bill")["의견 수"].transform("sum")
    return t.rename(columns={"bill": "법안"})


def tab_overview(ops, agree, runs):
    main = agree[(agree.split == "eval2") & (agree.codebook == "v3") & (agree.measure == "topic")].iloc[-1]
    stance = agree[(agree.split == "eval2") & (agree.codebook == "v3") & (agree.measure == "stance")].iloc[-1]
    usd = runs[runs.target.str.startswith("all")].usd_list.sum()
    c = st.columns(5)
    c[0].metric("공개 의견", f"{len(ops):,}건", help="4개 법안, 법안당 의견 번호 무작위 500건 중 공개된 것")
    c[1].metric("주제", "9개", help="코드북 v3, 법안 공통 틀 + 찬반 칸")
    c[2].metric("주제 일치율", f"{main.accuracy:.2f}", help=f"새 평가 표본 50건, Cohen's κ {main.kappa:.2f}")
    c[3].metric("찬반 일치율", f"{stance.accuracy:.2f}", help="새 평가 표본 50건")
    c[4].metric("전체 분류 비용", f"${usd:.2f}", help="API 정가 환산액. 실제로는 구독 안에서 돌아 청구 없음")

    st.markdown("##### 어떻게 나뉘었나")
    nr = (ops.topic == "no_reason").mean()
    llm_nr = (ops[ops.route == "llm"].topic == "no_reason").mean()
    st.markdown(
        f"- 이유 없이 찬반만 밝힌 의견: **{nr:.0%}** (15자 미만은 모두, 15자 이상에서도 {llm_nr:.0%})\n"
        f"- 이유가 있는 의견에서는 법안마다 주된 주제가 다르다(법안별 결과 탭)\n"
        f"- LLM이 확신도 '낮음·중간'으로 낸 의견은 {(ops.confidence.isin(['low', 'medium'])).sum():,}건 — 사람이 다시 볼 후보(검토 탭)")
    st.caption(SOURCE)


def tab_bills(ops):
    INK, SURFACE = theme_colors()
    st.markdown("##### 주제 비율")
    reason_only = st.toggle("이유 없는 찬반 빼고 보기", value=False)
    data = ops[ops.topic != "no_reason"] if reason_only else ops
    t = share_table(data, "주제")
    order = [TOPICS[k] for k in TOPICS if not (reason_only and k == "no_reason")]
    bars = alt.Chart(t).mark_bar(cornerRadiusEnd=4, height={"band": 0.7}).encode(
        y=alt.Y("주제:N", sort=order, title=None),
        x=alt.X("비율:Q", axis=alt.Axis(format="%", grid=True, tickCount=3), title=None, scale=alt.Scale(domain=[0, 1])),
        color=alt.condition(alt.datum.주제 == "이유 없는 찬반", alt.value(GRAY), alt.value(BLUE)),
        tooltip=["법안", "주제", "의견 수", alt.Tooltip("비율:Q", format=".1%")],
    )
    text = bars.mark_text(align="left", dx=4, fontSize=11).encode(
        text=alt.Text("비율:Q", format=".0%"), color=alt.value(INK))
    st.altair_chart((bars + text).properties(width=200, height=260)
                    .facet(column=alt.Column("법안:N", sort=BILLS, title=None))
                    .configure_view(stroke=None), width="content")
    st.caption("막대 = 그 법안의 공개 의견 중 비율. 회색은 이유 없는 찬반" + (" (지금은 뺀 상태)" if reason_only else ""))

    st.markdown("##### 찬반")
    s = share_table(ops, "찬반")
    chart = alt.Chart(s).mark_bar(height={"band": 0.7}, stroke=SURFACE, strokeWidth=2).encode(
        y=alt.Y("법안:N", sort=BILLS, title=None, axis=alt.Axis(labelLimit=200)),
        x=alt.X("비율:Q", stack="normalize", axis=alt.Axis(format="%", tickCount=5), title=None),
        color=alt.Color("찬반:N", scale=alt.Scale(domain=list(STANCES.values()), range=[BLUE, ORANGE, GRAY]),
                        legend=alt.Legend(orient="top", title=None)),
        order=alt.Order("찬반:N", sort="descending"),
        tooltip=["법안", "찬반", "의견 수", alt.Tooltip("비율:Q", format=".1%")],
    )
    # 높이를 st.altair_chart에 직접 줘야 한다(차트 속성만 주면 화면 폭에 맞춰 눌려 법안 이름이 겹쳤다)
    st.altair_chart(chart, width="stretch", height=4 * 48 + 40)

    with st.expander("표로 보기"):
        st.dataframe(share_table(ops, "주제").pivot(index="주제", columns="법안", values="의견 수")
                     .reindex(list(TOPICS.values())).fillna(0).astype(int)[BILLS], width="stretch")
        st.dataframe(s.pivot(index="찬반", columns="법안", values="의견 수").fillna(0).astype(int)[BILLS],
                     width="stretch")
    st.caption("결과는 '의견이 어떤 주제로 나뉘는가'까지다. 의견을 남긴 사람은 국민 전체를 대표하지 않는다. " + SOURCE)


def tab_quality(human, agree, selfa, llm2):
    INK, SURFACE = theme_colors()
    st.markdown("##### 코드북 버전별 주제 일치율 (새 평가 표본 50건, 원래 라벨)")
    v = agree[(agree.split == "eval2") & (agree.measure == "topic")].drop_duplicates("codebook", keep="last")
    human_ref = selfa[(selfa.pair == "사람1-사람2") & (selfa.measure == "topic")].iloc[0]
    v = pd.concat([v.assign(항목="LLM 코드북 " + v.codebook, 종류="LLM"),
                   pd.DataFrame([{"항목": "사람 자기 일치도(처음 평가용)", "종류": "사람", "accuracy": human_ref.accuracy,
                                  "kappa": human_ref.kappa, "n": human_ref.n}])])
    order = ["LLM 코드북 v1", "LLM 코드북 v2", "LLM 코드북 v3", "사람 자기 일치도(처음 평가용)"]
    base = alt.Chart(v).encode(y=alt.Y("항목:N", title=None, sort=order, axis=alt.Axis(labelLimit=240)))
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.6}).encode(
        x=alt.X("accuracy:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%", tickCount=5), title=None),
        color=alt.Color("종류:N", scale=alt.Scale(domain=["LLM", "사람"], range=[BLUE, GRAY]), legend=None),
        tooltip=["항목", alt.Tooltip("accuracy", title="정확도", format=".2f"),
                 alt.Tooltip("kappa", title="κ", format=".2f"), alt.Tooltip("n", title="건수")])
    labels = base.mark_text(align="left", dx=4).encode(x="accuracy:Q", text=alt.Text("accuracy:Q", format=".2f"),
                                                       color=alt.value(INK))
    st.altair_chart((bars + labels).properties(height=190), width="stretch")
    st.caption("50건에서 정확도 0.70의 95% 구간은 0.57～0.83 — 버전 차이(2～4건)는 우연과 구분되지 않는다. "
               "사람 자기 일치도는 처음 평가용 50건을 하루 뒤 다시 단 결과(기억 효과로 높게 나왔을 수 있음)")

    st.markdown("##### 평가별 요약")
    rows = []
    for name, split, cb in [("처음 평가용 50건", "eval", "v2"), ("새 평가 표본 50건", "eval2", "v3")]:
        a = agree[(agree.split == split) & (agree.codebook == cb)].drop_duplicates("measure", keep="last")
        a = a.set_index("measure")
        rows.append({"평가": name, "코드북": cb, "찬반": a.loc["stance", "accuracy"], "주제": a.loc["topic", "accuracy"],
                     "주제 κ": a.loc["topic", "kappa"], "주제(이유 없는 찬반 뺀 것)": a.loc["topic_excl_no_reason", "accuracy"],
                     "이유 있음·없음": a.loc["reason_vs_no_reason", "accuracy"]})
    s = selfa[selfa.pair == "사람1-사람2"].set_index("measure")
    rows.append({"평가": "사람 자기 일치도(처음 평가용)", "코드북": "v1→v2", "찬반": s.loc["stance", "accuracy"],
                 "주제": s.loc["topic", "accuracy"], "주제 κ": s.loc["topic", "kappa"],
                 "주제(이유 없는 찬반 뺀 것)": s.loc["topic_excl_no_reason", "accuracy"], "이유 있음·없음": float("nan")})
    summary = pd.DataFrame(rows).set_index("평가")
    st.dataframe(summary.style.format("{:.2f}", subset=list(summary.columns[1:]), na_rep="—"), width="stretch")

    h = human[human.split == "eval2"].assign(id=lambda d: d.id)
    df = h.merge(llm2[["id", "topic", "confidence"]], on="id", suffixes=("_h", "_m"))
    left, right = st.columns(2)
    with left:
        st.markdown("##### 확신도별 주제 정확도 (새 평가 표본)")
        c = df.assign(맞음=df.topic_h == df.topic_m).groupby("confidence").맞음.agg(["mean", "size"]).reset_index()
        c["확신도"] = c.confidence.map(CONF)
        ch = alt.Chart(c).mark_bar(cornerRadiusEnd=4, color=BLUE, height={"band": 0.6}).encode(
            y=alt.Y("확신도:N", sort=["높음", "중간", "낮음"], title=None),
            x=alt.X("mean:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%", tickCount=5), title=None),
            tooltip=["확신도", alt.Tooltip("mean:Q", title="정확도", format=".2f"), alt.Tooltip("size:Q", title="건수")])
        t = ch.mark_text(align="left", dx=4, color=INK).encode(
            text=alt.Text("label:N")).transform_calculate(label="format(datum.mean, '.2f') + ' (' + datum.size + '건)'")
        st.altair_chart((ch + t).properties(height=140), width="stretch")
        st.caption("확신도 '높음'만 그대로 쓰고 나머지를 사람이 보는 운영이 가능하다는 근거")
    with right:
        st.markdown("##### 주제 혼동표 (행 = 사람, 열 = LLM)")
        m = pd.crosstab(df.topic_h.map(TOPICS), df.topic_m.map(TOPICS)).stack().rename("n").reset_index()
        m.columns = ["사람", "LLM", "n"]
        m = m[m.n > 0]
        heat = alt.Chart(m).mark_rect(stroke=SURFACE, strokeWidth=2).encode(
            x=alt.X("LLM:N", title=None, sort=list(TOPICS.values()), axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("사람:N", title=None, sort=list(TOPICS.values())),
            color=alt.Color("n:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["사람", "LLM", alt.Tooltip("n", title="건수")])
        txt = heat.mark_text().encode(text="n:Q", color=alt.condition(alt.datum.n > 6, alt.value("white"),
                                                                       alt.value("#0b0b0b")))
        st.altair_chart((heat + txt).properties(height=300), width="stretch")


def tab_review(ops):
    st.warning("원문이 보이는 탭이다. 화면을 캡처해 공개하지 않는다.")
    c1, c2, c3 = st.columns(3)
    bill = c1.selectbox("법안", ["전체"] + BILLS)
    conf = c2.multiselect("확신도", ["low", "medium", "high"], default=["low", "medium"], format_func=CONF.get)
    topic = c3.selectbox("LLM 주제", ["전체"] + list(TOPICS.values()))
    d = ops[(ops.route == "llm") & ops.confidence.isin(conf)].drop_duplicates(["BILL_NO", "text"])
    if bill != "전체":
        d = d[d.bill == bill]
    if topic != "전체":
        d = d[d.주제 == topic]
    st.caption(f"{len(d):,}건(같은 문안은 한 번만)")
    st.dataframe(d[["bill", "찬반", "주제", "confidence", "text", "evidence", "dup_n"]].rename(
        columns={"bill": "법안", "confidence": "확신도", "text": "의견", "evidence": "LLM 근거 구절",
                 "dup_n": "같은 문안 수"}), width="stretch", hide_index=True)


def main():
    st.set_page_config(page_title="입법예고 의견 분류", layout="wide")
    st.title("입법예고 의견 자동 분류")
    st.caption("국회입법예고 의견을 코드북에 따라 LLM(Claude Sonnet)으로 분류하고, 사람 검수 표본과의 일치율로 품질을 쟀다")
    ops, human, agree, runs, selfa, llm2 = load()
    t1, t2, t3, t4 = st.tabs(["개요", "법안별 결과", "품질", "검토(원문)"])
    with t1:
        tab_overview(ops, agree, runs)
    with t2:
        tab_bills(ops)
    with t3:
        tab_quality(human, agree, selfa, llm2)
    with t4:
        tab_review(ops)


if __name__ == "__main__":
    main()
