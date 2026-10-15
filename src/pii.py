"""본문 속 개인정보 패턴(주민번호·전화번호·이메일)을 지운다. 이용약관 제12조."""
import re

PATTERNS = [  # 순서 중요: 주민번호를 전화번호보다 먼저
    ("[주민번호]", re.compile(r"\d{6}\s*-\s*[1-8]\d{6}")),
    ("[이메일]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("[전화번호]", re.compile(r"(?<!\d)(?:01[016789]|0[2-6]\d?)[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)")),
]


def scrub(text: str) -> tuple[str, int]:
    """(지운 텍스트, 바꾼 개수)"""
    n = 0
    for token, pat in PATTERNS:
        text, k = pat.subn(token, text)
        n += k
    return text, n


def count(text: str) -> int:
    return sum(len(pat.findall(text)) for _, pat in PATTERNS)
