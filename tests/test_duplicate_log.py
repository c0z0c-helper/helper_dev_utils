"""로그 중복 출력 테스트"""

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

# 환경변수 시뮬레이션: DEBUG 레벨 설정
import os

os.environ["LOG_LEVEL"] = "DEBUG"

logger = get_auto_logger()
logger.debug("Logger is set up.")

# 로거 목록 출력
print("\n전체 로거 목록:")
for name, logger_obj in logging.Logger.manager.loggerDict.items():
    if isinstance(logger_obj, logging.Logger) and name.startswith("helper"):
        print(f"  {name}: {logger_obj}")
        print(f"    handlers: {logger_obj.handlers}")
