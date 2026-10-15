# HANDOFF

## 현재 상태 (2026-10-15)

- 설정만 끝남: `AGENTS.md`·`CLAUDE.md`·`.gitignore`(원문·라벨 폴더 제외 포함)·`.gitattributes`·`.env.example`·`.claude/settings.json`(attribution 끔)·`.githooks/`(`core.hooksPath` 설정됨)·`.python-version`(3.14), 원격 `origin`(GitHub `KimInSeok-DA/DA_Legislative_Opinion_Coding`), PR #1(설정·법안 목록 수집) 머지
- `.env`: 두 키 모두 동작 확인(10-15, 재발급 후). 열린국회정보 「진행중 입법예고」 251건(User-Agent 없으면 400), OpenAI `/v1/models` 200
- 작업 기간 10-18～10-21

## 다음 작업

0～2단계 끝(10-15): `.venv`(3.14)·`requirements.txt`, 법안 목록 20,274건(`data/raw/bills.csv`), 의견 페이지 요청 방식 확인 — 자세한 것은 `docs/작업일지/2026-10-15.md`

3. 법안 고르기(브랜치 `decision/bill-selection`): **결정됨** `docs/의사결정/1015_01_법안_선택과_표본.md` — 2214785·2218197·2211676·2208271, 법안당 의견 번호 무작위 500건, 20자 미만은 규칙 분류. PR #2 머지
4. 의견 수집(브랜치 `collect/opinions`, 커밋 전): 2,000/2,000건 `data/raw/opinions.jsonl`(허용 필드만), 공개 1,843 · 20자 이상 1,005, 중복·개인정보 패턴 0. 집계 `outputs/collection_summary.csv`, 표는 1015_01 결과란
5. 정제: `html.unescape`(본문 31건 엔티티) 후 길이 재계산, 20자 기준 확정(제목+본문으로 볼지 — 본문<20·제목≥20 18건), 응답 없음 4건은 지워진 번호로 제외 → 코드북 v1 → 검수 표본 100건

## 열린 결정

- 분류 모델(비용·JSON 출력 지원 확인 후)
- 20자 기준 확정(5단계, 실제 분포 확인 후)
