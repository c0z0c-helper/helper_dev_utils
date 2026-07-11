"""
helper_logger 모듈

간단 설명:
- 콘솔(및 선택적 파일) 출력을 위한 최소 로깅 유틸리티를 제공한다.
- 로그 레벨은 한 글자로 축약되어 출력된다 (DEBUG→D, INFO→I, WARNING→W, ERROR→E, CRITICAL→C).
- 타임스탬프의 타임존을 설정할 수 있다 (기본: Asia/Seoul).
- 같은 이름으로 재호출해도 핸들러가 중복 등록되지 않는다.
- 파일 저장은 기본적으로 비활성화되어 있으며, 활성화 시 프로세스 시작 시점을 기준으로
  {log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log 경로에 기록된다 (같은 프로세스 내 로거들이 파일을 공유).

사용 예:
>>> logger = get_logger("app")
>>> logger.info("Hello World")
>>> auto = get_auto_logger()  # 호출자 모듈 이름을 로거 이름으로 사용
>>> file_logger = get_logger("app", file=True)  # logs/2026/07/11/20260711_134800.log
"""

import inspect
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

DEFAULT_TZ = "Asia/Seoul"
DEFAULT_FMT = "%(asctime)s [%(levelname).1s] %(name)s - %(message)s"
DEFAULT_DATEFMT = "%y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = "logs"

# 루트 로거의 기본 핸들러를 제거하여 중복 출력을 방지한다.
logging.root.handlers = []

# 프로세스 내에서 공유하는 로그 파일 경로 (최초 활성화 시점에 1회 결정)
_log_file_path: Optional[Path] = None


class LogFormatter(logging.Formatter):
    """지정된 타임존으로 시간을 표시하는 포맷터"""

    def __init__(
        self,
        fmt: str = DEFAULT_FMT,
        datefmt: Optional[str] = DEFAULT_DATEFMT,
        tz: Union[str, ZoneInfo] = DEFAULT_TZ,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = ZoneInfo(tz) if isinstance(tz, str) else tz

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()


def _get_log_file_path(log_dir: Union[str, Path], tz: Union[str, ZoneInfo]) -> Path:
    """프로세스 시작 시점 기준 로그 파일 경로를 1회 계산하여 캐시한다."""
    global _log_file_path
    if _log_file_path is None:
        tzinfo = ZoneInfo(tz) if isinstance(tz, str) else tz
        now = datetime.now(tzinfo)
        _log_file_path = Path(log_dir) / now.strftime("%Y") / now.strftime("%m") / now.strftime(
            "%d"
        ) / f"{now.strftime('%Y%m%d_%H%M%S')}.log"
        _log_file_path.parent.mkdir(parents=True, exist_ok=True)
    return _log_file_path


def get_logger(
    name: str,
    level: int = logging.INFO,
    tz: Union[str, ZoneInfo] = DEFAULT_TZ,
    file: bool = False,
    log_dir: Union[str, Path] = DEFAULT_LOG_DIR,
) -> logging.Logger:
    """
    콘솔(및 선택적 파일) 핸들러가 구성된 로거를 반환한다.

    Args:
        name: 로거 이름
        level: 로그 레벨 (기본: INFO)
        tz: 타임스탬프에 적용할 타임존 (기본: Asia/Seoul)
        file: 파일 저장 활성화 여부 (기본: False)
            활성화 시 {log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log 경로에 기록되며,
            파일명은 프로세스 시작 시점 기준 1회 결정되어 같은 프로세스의 모든 로거가 공유한다.
        log_dir: 파일 저장 활성화 시 사용할 기준 디렉토리 (기본: "logs")

    Returns:
        설정된 로거 인스턴스

    Examples:
        >>> logger = get_logger("app", level=logging.DEBUG)
        >>> logger = get_logger("app", file=True)
        >>> logger = get_logger("app", file=True, log_dir="var/logs")
    """
    formatter = LogFormatter(tz=tz)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.close()
    logger.handlers = []  # 중복 출력 방지
    logger.propagate = False  # 부모 로거로의 전파 방지

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if file:
        log_file_path = _get_log_file_path(log_dir, tz)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_auto_logger(**kwargs) -> logging.Logger:
    """
    호출자 모듈 이름을 기반으로 자동 로거 생성 및 반환

    호출자 프레임의 __file__ 값을 사용하여 로거 이름(Path(...).stem)을 결정한다.
    호출자 프레임 또는 __file__이 없는 경우 sys.argv[0] 또는 '__main__'을 대체값으로 사용한다.

    Args:
        **kwargs: get_logger로 전달할 옵션들 (level, tz, file, log_dir)

    Returns:
        logging.Logger: 설정된 로거 인스턴스

    Examples:
        >>> logger = get_auto_logger()
        >>> logger = get_auto_logger(level=logging.DEBUG)
    """
    frame = inspect.currentframe()
    try:
        caller = frame.f_back if frame is not None else None
        caller_file = caller.f_globals.get("__file__") if caller is not None else None

        if not caller_file:
            caller_file = sys.argv[0] if len(sys.argv) > 0 and sys.argv[0] else "__main__"

        name = Path(caller_file).stem
    finally:
        del frame

    return get_logger(name, **kwargs)


if __name__ == "__main__":
    logger = get_logger("demo")
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
