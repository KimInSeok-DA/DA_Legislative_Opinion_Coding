# HANDOFF

## 현재 상태 (2026-10-15)

- 설정만 끝남: `AGENTS.md`·`CLAUDE.md`·`.gitignore`(원문·라벨 폴더 제외 포함)·`.gitattributes`·`.env.example`·`.claude/settings.json`(attribution 끔)·`.githooks/`(`core.hooksPath` 설정됨)·`.python-version`(3.14), 원격 `origin`(GitHub `KimInSeok-DA/DA_Legislative_Opinion_Coding`) 연결, `main`에 README 첫 커밋만 푸시(10-15). 나머지 설정 파일은 아직 커밋 전
- `.env`: 두 키 모두 동작 확인(10-15, 재발급 후). 열린국회정보 「진행중 입법예고」 251건(User-Agent 없으면 400), OpenAI `/v1/models` 200
- 작업 기간 10-18～10-21

## 다음 작업

0～2단계 끝(10-15): `.venv`(3.14)·`requirements.txt`, 법안 목록 20,274건(`data/raw/bills.csv`), 의견 페이지 요청 방식 확인 — 자세한 것은 `docs/작업일지/2026-10-15.md`

3. 법안 고르기: 사이트 목록 `sortCol=OPN_CNT`로 의견 수 상위 후보표 → 위원회가 다른 3～5개, **법안 안 표본 추출 방식**(`opnNo` 무작위, 연속 번호인지 확인 필요) → 의사결정 문서, 사용자 결정
4. 의견 수집기: 허용 필드(`lgsltPaId, opnNo, sj, cn, opnRgDt, opbYn, delYn`)만 저장, 개인정보 패턴 제거, 건수 대조
5. 정제 → 코드북 v1 → 검수 표본 100건

## 열린 결정

- 분류 모델(비용·JSON 출력 지원 확인 후)
- 고를 법안·위원회, 법안당 표본 수(상위 법안 의견 3만～12만 건, 캠페인성 반복 의견 비중 확인 필요)
- 나머지 설정 파일 첫 PR 시점(사용자)
