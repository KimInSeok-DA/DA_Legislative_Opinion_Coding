# HANDOFF

## 현재 상태 (2026-10-17)

- 1～11단계 끝. PR #1～#11 머지. 브랜치 `docs/readme-guide`(README 다시 쓰기) 커밋 전. 본인용 설명서는 `_private/03_프로젝트_설명서.md`
- 환경: Python 3.14.5 `.venv`, `requirements.txt`. 분류는 **Claude Code 명령줄 `claude -p`(구독 안, 추가 결제 없음) + Sonnet**(의사결정 1016_01). OpenAI 키는 크레딧이 없어 쓰지 않음

| 단계 | 결과 | 근거 문서 |
|---|---|---|
| 1 법안 목록 | 20,274건 `data/raw/bills.csv` | 작업일지 10-15 |
| 3 법안 고르기 | 2214785 국가보안법 폐지·2218197 소득세법·2211676 공인중개사법·2208271 정보통신망법, 법안당 의견 번호 무작위 500건 | 1015_01 |
| 4 의견 수집 | 2,000/2,000, 공개 1,843 · 비공개 153 · 지워진 번호 4 | 1015_01, `outputs/collection_summary.csv` |
| 5 정제 | 15자 미만 573건 규칙 "이유 없는 찬반", 15자 이상 1,270건(고유 1,161) LLM. 규칙 쪽 20건 확인으로 **15자 유지** | 1015_02 |
| 6～7 코드북·표본 | 코드북 v1, 검수 표본 100(개선 50/평가 50) + 규칙 쪽 20, 사용자 라벨 완료 | 1015_03, 1015_04 |
| 8 LLM 분류 | `src/classify.py`(`claude -p`, JSON 스키마), 결과 `outputs/raw/sample_<모델>_<코드북>.jsonl`, 토큰 `outputs/llm_runs.csv` | 1016_01 |
| 9 일치율 | `src/agreement.py`, `src/self_agreement.py` → `outputs/agreement.csv`, `outputs/self_agreement.csv`. **최종 코드북 v3, 새 평가 표본 50건: 찬반 1.00, 주제 0.70(κ 0.61)**. 처음 평가용 v2 0.80, 사람 자기 일치도 0.90 | 1017_01, 1017_02 |
| 10 전체 분류 | Sonnet + v3로 LLM 쪽 고유 1,161건(`outputs/raw/all_sonnet_v3.jsonl`), 15자 미만 573건 찬반 낱말 규칙(사람 20건과 20/20) → `src/build_db.py` → `data/interim/coding.db`, `outputs/topic_by_bill.csv`, `outputs/stance_by_bill.csv` | 작업일지 10-17 |

- 개선용 라벨은 사용자가 다시 읽고 13칸 고침(`data/labels/relabel_log.csv`, 원본 `review_sheet_original.csv`). 고친 개선용으로 낸 일치율은 성능 지표로 쓰지 않는다. **평가용·새 평가 라벨은 고치지 않는다**
- 지난 코드북은 `docs/코드북_버전/`(v1·v2·v3). `src/classify.py --codebook v2 --sheet eval2`처럼 같은 표본에 지난 버전을 돌린다
- 분류는 `claude -p`를 의견마다 부른다(구독 안, 사용량 한도 있음). 결과가 빈 건은 넘기고 다시 실행하면 그 건만 다시 시도

## 다음 작업

- 11단계 결과물: `src/dashboard.py`(`streamlit run src/dashboard.py`, 검토 탭은 원문이 보여 공개 캡처 금지), `outputs/report.md`, `README.md`
- 남은 것(사용자): 대시보드 확인, 저장소 공개 설정, 포트폴리오 1장
- 더 한다면: 코더 간 신뢰도(다른 사람 1명이 평가 표본을 달기), 같은 코드북 반복 실행의 흔들림, 확신도 기준 사람 검토 운영 시험

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

- 없음
