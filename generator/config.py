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

SITE_TITLE = "세계뉴스 일일 브리핑 아카이브"

# GitHub Pages 프로젝트 서브패스. 링크가 이 경로 아래에서 해석된다.
BASE_PATH = os.environ.get("ARCHIVE_BASE_PATH", "/worldnews-archive/")
