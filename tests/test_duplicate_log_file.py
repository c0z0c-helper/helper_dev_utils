"""로그 중복 출력 테스트 - 파일 로깅"""

import sys
from pathlib import Path

# tests 폴더에서 실행 시 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging

from src.helper_dev_utils import get_logger
from src.helper_dev_utils import set_pandas_extension

log_dir = project_root / "logs"

logger = get_logger(level=logging.DEBUG, enable_file_write=True, log_dir=log_dir)
logger.debug("First log - Logger is set up.")

# 같은 이름으로 재호출해도 핸들러가 중복 등록되지 않는지, 같은 로그 파일을 공유하는지 확인
logger = get_logger(level=logging.DEBUG, enable_file_write=True, log_dir=log_dir)
logger.debug("Second log - Testing duplicate prevention.")

print(f"\n핸들러 개수: {len(logger.handlers)}")
print(f"핸들러: {logger.handlers}")

log_file = next(f for f in logger.handlers if isinstance(f, logging.FileHandler)).baseFilename
content = Path(log_file).read_text(encoding="utf-8")
print(f"\n로그 파일: {log_file}")
print(f"'Second log' 등장 횟수: {content.count('Second log')}")
