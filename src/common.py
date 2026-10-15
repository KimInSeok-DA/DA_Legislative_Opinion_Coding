"""수집 공통: 경로, .env, 요청 간격을 지키는 HTTP 세션."""
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
load_dotenv(ROOT / ".env")

# User-Agent가 없으면 열린국회정보가 HTTP 400을 돌려준다(10-15 확인)
HEADERS = {"User-Agent": "Mozilla/5.0 (research; legislative-opinion-coding)"}
MIN_INTERVAL = 1.0  # 이용약관 제12조: 요청 간격 1초 이상

_session = requests.Session()
_session.headers.update(HEADERS)
_last = 0.0


def fetch(method: str, url: str, **kwargs) -> requests.Response:
    """요청 사이 MIN_INTERVAL초를 보장하고, 실패는 2번까지 다시 시도한다."""
    global _last
    for attempt in range(3):
        wait = MIN_INTERVAL - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        try:
            r = _session.request(method, url, timeout=30, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == 2:
                # requests 오류 메시지에는 URL(KEY=인증키 포함)이 들어간다 → 가리고 다시 던진다
                raise RuntimeError(re.sub(r"KEY=[^&\s]+", "KEY=***", str(e))) from None
            time.sleep(3 * (attempt + 1))


def assembly_key() -> str:
    key = os.getenv("ASSEMBLY_API_KEY")
    if not key:
        raise SystemExit("ASSEMBLY_API_KEY가 .env에 없습니다")
    return key


PAL = "https://pal.assembly.go.kr"


def csrf_token(html: str) -> str:
    """국회입법예고 페이지의 meta _csrf 값. POST 요청에 같이 보낸다."""
    m = re.search(r'<meta name="_csrf" content="([^"]+)"', html)
    if not m:
        raise RuntimeError("CSRF 토큰을 찾지 못했습니다")
    return m.group(1)
