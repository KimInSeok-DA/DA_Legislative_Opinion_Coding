"""LLM 분류(8단계). 코드북을 그대로 지시문에 넣고 의견 하나마다 찬반·주제·근거 구절·확신도를 JSON으로 받는다.

- 호출: Claude Code 명령줄(`claude -p`)을 의견 하나마다 실행한다. 사용자의 Claude 구독 안에서 돌아가 API 결제가 없다
  (OpenAI API는 크레딧이 없어 쓰지 않기로 함, 10-16 사용자 결정)
  - 도구·MCP·슬래시 명령을 모두 끄고, 빈 임시 폴더에서 실행해 프로젝트 지시문(CLAUDE.md)이 섞이지 않게 한다
  - 출력은 `--json-schema`로 강제한다 → 코드북에 없는 값이 나오지 않는다
- 지시문 = 코드북 1～6절(버전 기록 7절은 뺀다). 사람 검수와 같은 기준
- 결과에는 근거 구절(원문 일부)이 들어가므로 outputs/raw/(gitignore)에 둔다. 토큰 집계만 outputs/llm_runs.csv
  - usd는 실제 청구가 아니라 명령줄이 알려 주는 API 정가 환산액(구독 안에서는 청구되지 않음)
- 이미 분류한 id는 다시 부르지 않는다(중간에 끊겨도 이어서)
- 사람 라벨·개선/평가 구분(review_key.csv)은 읽지 않는다

실행: python src/classify.py --model sonnet [--sheet eval2] [--limit 3]
"""
import argparse
import json
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

from common import ROOT

CODEBOOK = ROOT / "docs" / "코드북.md"
SNAPSHOTS = ROOT / "docs" / "코드북_버전"  # 지난 버전과 같은 표본에서 비교할 때(--codebook v2)
# 결과 파일 앞머리 → 시트. 시트에서는 id·bill·text만 쓴다
SHEETS = {"sample": "review_sheet.csv",  # 검수 표본 100건(개선 50·평가 50)
          "eval2": "eval2_sheet.csv",  # 새 평가 표본 50건(의사결정 1017_02)
          "all": None}  # 10단계 전체: route=llm 고유 텍스트(법안·텍스트가 같으면 한 번만)
OUT = ROOT / "outputs" / "raw"
RUNS = ROOT / "outputs" / "llm_runs.csv"

STANCES = ["pro", "con", "unknown"]
TOPICS = ["rights", "security", "burden", "fairness", "effect", "politics", "other", "no_reason", "unclear"]
SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {"type": "string", "description": "주제 판단의 근거가 된 의견 속 구절을 그대로 옮긴 것. 근거가 없으면 빈 문자열"},
        "stance": {"type": "string", "enum": STANCES},
        "topic": {"type": "string", "enum": TOPICS},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["evidence", "stance", "topic", "confidence"],
    "additionalProperties": False,
}


def instructions(codebook: Path) -> str:
    md = codebook.read_text(encoding="utf-8")
    md = md[:md.index("## 7. 버전 기록")].strip()
    return ("당신은 국회입법예고 법안 의견을 아래 코드북에 따라 분류하는 코더다. "
            "의견 하나를 읽고 찬반(stance) 하나와 주제(topic) 하나를 고른다. "
            "코드북 4절의 판단 순서와 '이유로 치지 않는 것', '자주 헷갈리는 것', 6절의 법안별 적용을 그대로 따른다. "
            "evidence에는 주제를 고른 근거 구절을 의견에서 그대로 옮기고, confidence는 코드북 기준으로 다른 주제와 "
            "헷갈릴 여지가 얼마나 되는지로 고른다. 도구는 쓰지 않고 결과만 낸다.\n\n" + md)


def codebook_version(codebook: Path) -> str:
    return re.search(r"버전: \*\*(v\d+)\*\*", codebook.read_text(encoding="utf-8")).group(1)


def all_texts() -> pd.DataFrame:
    """LLM 쪽 고유 텍스트. id = 법안번호_그 텍스트가 처음 나온 의견 번호."""
    from clean import CLEAN
    from review_sample import BILL_NAMES
    df = pd.read_csv(CLEAN, dtype={"BILL_NO": str, "opnNo": str}, encoding="utf-8-sig")
    u = df[df.route == "llm"].drop_duplicates(["BILL_NO", "text"])
    return pd.DataFrame({"id": u.BILL_NO + "_" + u.opnNo, "bill": u.BILL_NO.map(BILL_NAMES), "text": u.text})


def classify_one(model: str, workdir: Path, row) -> dict | None:
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--system-prompt-file", "system.txt",
           "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence", "--setting-sources", "",
           "--output-format", "json", "--json-schema", json.dumps(SCHEMA, ensure_ascii=False)]
    t0 = time.monotonic()
    for attempt in range(3):
        p = subprocess.run(cmd, input=f"법안: {row.bill}\n의견:\n{row.text}", capture_output=True, text=True,
                           encoding="utf-8", cwd=workdir, timeout=300)
        try:
            r = json.loads(p.stdout)
            if not r.get("is_error") and r.get("structured_output"):
                break
        except json.JSONDecodeError:
            r = {}
        if attempt == 2:
            # 성공이라고 하면서 결과 JSON이 빈 경우가 있다(10-17, 1건) → 멈추지 않고 넘기고, 다시 실행하면 이 건만 다시 시도
            print(f"{row.id}: 실패({r.get('subtype') or p.stderr[:200]}), 넘김")
            return None
        time.sleep(10 * (attempt + 1))
    u = r["usage"]
    return {"id": row.id, **r["structured_output"], "model": next(iter(r["modelUsage"])),
            "input_tokens": u["input_tokens"] + u["cache_creation_input_tokens"] + u["cache_read_input_tokens"],
            "cached_tokens": u["cache_read_input_tokens"], "output_tokens": u["output_tokens"],
            "usd_list": r["total_cost_usd"], "seconds": round(time.monotonic() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="claude 명령줄의 모델 이름(haiku, sonnet 등)")
    ap.add_argument("--sheet", default="sample", choices=list(SHEETS))
    ap.add_argument("--codebook", help="지난 버전 이름(v1, v2 …). 없으면 docs/코드북.md")
    ap.add_argument("--limit", type=int, help="앞에서 n건만(시험용)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    codebook = SNAPSHOTS / f"코드북_{args.codebook}.md" if args.codebook else CODEBOOK
    version = codebook_version(codebook)
    if args.sheet == "all":
        sheet = all_texts()
    else:
        sheet = pd.read_csv(ROOT / "data" / "labels" / SHEETS[args.sheet], dtype=str, encoding="utf-8-sig",
                            keep_default_na=False)[["id", "bill", "text"]]
    if args.limit:
        sheet = sheet.head(args.limit)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.sheet}_{args.model}_{version}.jsonl"
    done = {json.loads(line)["id"] for line in path.open(encoding="utf-8")} if path.exists() else set()
    todo = sheet[~sheet.id.isin(done)]
    print(f"{args.model} 코드북 {version} {args.sheet}: {len(sheet)}건 중 남은 {len(todo)}건")

    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp, path.open("a", encoding="utf-8") as f:
        workdir = Path(tmp)
        (workdir / "system.txt").write_text(instructions(codebook), encoding="utf-8")
        with ThreadPoolExecutor(args.workers) as ex:
            for res in ex.map(lambda row: classify_one(args.model, workdir, row), todo.itertuples()):
                if res is None:
                    continue
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
    wall = time.monotonic() - t0

    res = pd.read_json(path, lines=True, dtype={"id": str})  # "법안_번호" 꼴 id가 숫자로 바뀌지 않게
    res = res[res.id.isin(sheet.id)]
    new = res[res.id.isin(todo.id)]
    if len(new):
        run = {"run_at": datetime.now().isoformat(timespec="seconds"), "target": args.sheet, "model": new.model.iloc[0],
               "codebook": version, "n": len(new), "input_tokens": int(new.input_tokens.sum()),
               "cached_tokens": int(new.cached_tokens.sum()), "output_tokens": int(new.output_tokens.sum()),
               "usd_list": round(new.usd_list.sum(), 4), "wall_seconds": round(wall, 1)}
        pd.DataFrame([run]).to_csv(RUNS, mode="a", header=not RUNS.exists(), index=False, encoding="utf-8-sig")
        print(run)
    print(f"전체 {len(res)}건, 확신도 {res.confidence.value_counts().to_dict()}")
    print(res.topic.value_counts().to_string())


if __name__ == "__main__":
    main()
