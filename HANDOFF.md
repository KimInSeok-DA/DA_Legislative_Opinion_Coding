# HANDOFF

## 현재 상태 (2026-10-15)

- 1～6단계 끝, PR #1～#5 머지. 로컬은 `main`만 있음(원격 `origin` = GitHub `KimInSeok-DA/DA_Legislative_Opinion_Coding`)
- 환경: Python 3.14.5 `.venv`, `requirements.txt`. `.env`의 두 키(열린국회정보·OpenAI) 동작 확인(10-15)
- 작업 기간 10-18～10-21(일정보다 앞서 있음)

| 단계 | 결과 | 근거 문서 |
|---|---|---|
| 1 법안 목록 | 20,274건 `data/raw/bills.csv` | 작업일지 10-15 |
| 3 법안 고르기 | 2214785 국가보안법 폐지(법사)·2218197 소득세법(재경)·2211676 공인중개사법(국토)·2208271 정보통신망법(과방), 법안당 의견 번호 무작위 500건 | `docs/의사결정/1015_01_법안_선택과_표본.md` |
| 4 의견 수집 | 2,000/2,000 `data/raw/opinions.jsonl`(허용 필드만), 공개 1,843 · 비공개 153 · 지워진 번호 4. 중복·개인정보 패턴 0 | 1015_01 결과란, `outputs/collection_summary.csv` |
| 5 정제 | `src/clean.py` → `data/interim/opinions_clean.csv`. 분류 텍스트 = 제목+본문(제목이 본문에 있으면 본문만), **15자 미만 573건은 규칙으로 "이유 없는 찬반"**, 15자 이상 **1,270건(고유 1,161)이 LLM 대상** | `docs/의사결정/1015_02_짧은_의견_기준.md` |
| 6 코드북 v1 | 찬반 칸(`pro`·`con`·`unknown`) + 법안 공통 주제 9개(`rights` `security` `burden` `fairness` `effect` `politics` `other` `no_reason` `unclear`), 단일 라벨. 코드북을 만들 때 읽은 100건(`src/codebook_read.py`)은 검수 표본에서 뺀다 | `docs/코드북.md`, `docs/의사결정/1015_03_코드북_v1.md` |
| 7 검수 표본 | 100건(개선 50 / 평가 50) + 규칙 쪽 20건, 라벨 시트 `data/labels/` | `docs/의사결정/1015_04_검수_표본과_같은_문안.md` |

`opinions_clean.csv` 열: `BILL_NO, opnNo, opnRgDt, inst_yn, text, text_len, route(llm/rule), dup_n(법안 안 같은 텍스트 수), pii_removed_clean`

## 다음 작업

7단계 표본 끝(브랜치 `review/sample`, 커밋 전): `docs/의사결정/1015_04_검수_표본과_같은_문안.md` — 같은 문안은 3글자 조각 자카드 0.6으로 묶어 묶음당 1건, 코드북을 만든 100건의 묶음은 통째로 제외(`src/dedup.py`, `src/review_sample.py`)

1. **사용자 라벨**(라벨 화면 `streamlit run src/label_app.py`, 브랜치 `label/app` 커밋 전): `data/labels/review_sheet.csv` 100건 + `rule_sheet.csv` 20건에 코드북 v1로 찬반(`pro`/`con`/`unknown`)·주제(9개 코드)·메모. 개선/평가 구분은 `review_key.csv`에만 있으니 라벨 전에 열지 않는다
   - 건별 라벨 시간 `data/labels/label_times.csv`(이전으로 돌아가 고치면 같은 id가 여러 줄 → id별로 더한다)
2. 8 LLM 분류: 출력 JSON = 찬반·주제·근거 문장·확신도. 모델은 공식 가격표 확인 후 gpt-5-mini/nano 비교, 표본 100건 먼저, 전체 전 비용 알림. 규칙 쪽 573건의 찬반은 낱말 규칙
3. 9 일치율: 찬반·주제 따로 정확도·κ·혼동표, 주제는 `no_reason` 뺀 결과도, **묶음 크기 가중 일치율**(`data/interim/groups.csv`)도 보조로. 규칙 쪽 20건 → 1015_02 바꾸는 조건 → 코드북 v2(개선용 50) → 평가용 50으로 v1·v2 비교
4. 10 전체 분류·SQLite → 11 대시보드·보고서·README

## 진행 방식 (사용자 선호)

- 작업 단위·사용자 판단이 필요한 지점에서 끊고, 커밋 전에 브랜치·파일·메시지·PR 본문을 먼저 보여 준다
- 커밋·푸시는 사용자가 "커밋, 푸시"라고 할 때만. **PR은 사용자가 웹에서 만든다** → PR 제목·본문을 복사용 텍스트로 준다
- 머지 후 사용자가 요청하면 `main` pull → 로컬 브랜치 삭제

## 알아둘 것

- 국회입법예고 요청: User-Agent 필수, CSRF 토큰(목록 페이지 meta) + 같은 세션, 요청 간격 1초(`src/common.py`). 오류 메시지의 인증키는 가려짐
- 본문 응답에 작성자·연락처 필드가 있음 → 수집기는 허용 필드만 저장. 추가 수집 시에도 같은 방식
- 법안 페이지(제안이유)는 `data/raw/bill_pages/`에 저장돼 있어 `src/bill_summary.py`는 다시 요청하지 않는다
- 터미널 한글: `python -I`만 쓰면 출력이 깨지고 `-I -X utf8`이면 괜찮다. 다만 `-I`는 스크립트 폴더를 import 경로에 넣지 않으므로, `src/` 모듈을 쓰는 프로젝트 코드는 `-I` 없이 `.venv/Scripts/python src/파일.py`로 실행

## 열린 결정

- 분류 모델(비용·JSON 출력 지원 확인 후) — 8단계
- 규칙 쪽 573건에 찬반을 붙이는 낱말 규칙 — 8단계
