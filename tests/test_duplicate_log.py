"""로그 중복 출력 테스트"""

import sys
from pathlib import Path

# tests 폴더에서 실행 시 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging

from src.helper_dev_utils import get_logger
from src.helper_dev_utils import set_pandas_extension

logger = get_logger(level=logging.DEBUG)
logger.debug("Logger is set up.")

# 같은 이름으로 재호출해도 핸들러가 중복 등록되지 않는지 확인
logger = get_logger(level=logging.DEBUG)
logger.debug("Second call - should not duplicate output.")

# 로거 목록 출력
print("\n전체 로거 목록:")
for name, logger_obj in logging.Logger.manager.loggerDict.items():
    if isinstance(logger_obj, logging.Logger) and name.startswith("test"):
        print(f"  {name}: {logger_obj}")
        print(f"    handlers: {logger_obj.handlers}")
