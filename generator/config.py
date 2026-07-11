"""경로와 빌드 설정."""

import os
from pathlib import Path

# 이 repo 루트 (generator/ 의 부모).
REPO_ROOT = Path(__file__).resolve().parent.parent

# 형제 앱이 매일 쓰는 브리핑 JSON 디렉터리. 환경변수로 override 가능.
DATA_DIR = Path(
    os.environ.get(
        "ARCHIVE_DATA_DIR",
        REPO_ROOT.parent / "korean_worldnews_dailybriefing" / "data",
    )
)

# 정적 사이트 출력(= GitHub Pages 배포 대상).
OUTPUT_DIR = Path(os.environ.get("ARCHIVE_OUTPUT_DIR", REPO_ROOT / "docs"))

TEMPLATE_DIR = REPO_ROOT / "templates"
ASSETS_DIR = REPO_ROOT / "assets"

# 권역별 표시 건수(이메일과 동일한 기본값).
TOP_N = int(os.environ.get("ARCHIVE_TOP_N", "5"))

SITE_TITLE = "GRIP"
SITE_FULL = "Global Regional Intelligence Platform"
SITE_TAGLINE = "세계의 변화를 읽고, 비즈니스 기회를 연결합니다."
SITE_DESC = "국가별 정책·산업·시장 변화를 선별하여 기업과 기관에 필요한 인사이트를 제공합니다."

# GitHub Pages 프로젝트 서브패스. 링크가 이 경로 아래에서 해석된다.
BASE_PATH = os.environ.get("ARCHIVE_BASE_PATH", "/worldnews-archive/")

# 공유 미리보기(OG) 절대 URL의 기준. og:image 등은 절대경로여야 한다.
SITE_URL = os.environ.get(
    "ARCHIVE_SITE_URL", "https://valueinfomaker-lab.github.io/worldnews-archive/"
)

# 뉴스레터 구독 폼이 POST 할 Google Apps Script 웹앱 URL(공개, 비밀 아님).
# 미설정이면 폼은 보이되 제출 시 "준비 중" 안내만 표시한다. 환경변수로 override 가능.
SUBSCRIBE_ENDPOINT = os.environ.get(
    "GRIP_SUBSCRIBE_ENDPOINT",
    "https://script.google.com/macros/s/AKfycbytccNcz_JQYHRbOlmfoKiD4t9fOd5nY5zK4zgaxWFGExDinqO550vo21S5joz73b65/exec",
)
