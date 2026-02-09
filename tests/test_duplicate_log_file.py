"""로그 중복 출력 테스트 - 파일 로깅"""

import sys
from pathlib import Path

# tests 폴더에서 실행 시 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.helper_dev_utils import get_auto_logger
from src.helper_dev_utils import set_pandas_extension
import warnings
import logging

warnings.filterwarnings("ignore")

# 환경변수 시뮬레이션: DEBUG 레벨 및 파일 로깅 활성화
import os

os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["LOG_FILE_ENABLED"] = "true"
os.environ["LOG_USE_CENTRAL_FILE"] = "true"

logger = get_auto_logger()
logger.debug("First log - Logger is set up.")
logger.debug("Second log - Testing duplicate prevention.")

# 로거 목록 출력
print("\n전체 로거 목록:")
for name, logger_obj in logging.Logger.manager.loggerDict.items():
    if isinstance(logger_obj, logging.Logger) and name.startswith("helper"):
        print(f"  {name}: {logger_obj}")
        print(f"    handlers: {logger_obj.handlers}")

# test_duplicate_log_file 로거 핸들러 확인
test_logger = logging.getLogger("test_duplicate_log_file")
print(f"\ntest_duplicate_log_file 로거:")
print(f"  handlers: {test_logger.handlers}")
print(f"  핸들러 개수: {len(test_logger.handlers)}")

# 파일 핸들러 캐시 확인
from src.helper_dev_utils import helper_logger

print(f"\n파일 핸들러 캐시 크기: {len(helper_logger._file_handlers)}")
print("캐시된 파일 경로:")
for path in helper_logger._file_handlers.keys():
    print(f"  {path}")
