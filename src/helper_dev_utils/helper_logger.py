"""
helper_logger 모듈

간단 설명:
- 콘솔(및 선택적 파일) 출력을 위한 최소 로깅 유틸리티를 제공한다.
- 로그 레벨은 한 글자로 축약되어 출력된다 (DEBUG→D, INFO→I, WARNING→W, ERROR→E, CRITICAL→C).
- 타임스탬프의 타임존을 설정할 수 있다 (기본: Asia/Seoul).
- 같은 이름으로 재호출해도 핸들러가 중복 등록되지 않는다.
- 파일 저장은 기본적으로 비활성화되어 있으며, 활성화 시 프로세스 시작 시점을 기준으로
  {log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log 경로에 기록된다 (같은 프로세스 내 로거들이 파일을 공유).
- enable_file/enable_line 옵션을 켜면 로그를 호출한 소스 파일명/라인 번호를 함께 출력한다
  (기본값은 둘 다 True이며, 한쪽만 명시하면 나머지는 False로 취급되어 서로 독립적으로 동작한다).

사용 예:
>>> logger = get_logger("app")
>>> logger.info("Hello World")
>>> anon = get_logger()  # name 생략 시 빈 이름(익명/anonymous) 로거 사용
>>> file_logger = get_logger("app", enable_file_write=True)  # logs/2026/07/11/20260711_134800.log
"""

import logging
import os
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


def _build_fmt(name: str, enable_file: bool, enable_line: bool) -> str:
    """name 유무 및 enable_file/enable_line 옵션에 따라 포맷 문자열을 구성한다.

    name="" 인 경우 logging.getLogger("")가 root 로거(logger.name == "root")를
    반환하므로 %(name)s를 그대로 쓰면 "root"가 찍힌다. 이를 피하기 위해 name이
    비어 있으면 name 표시 자체를 포맷에서 제외한다.
    """
    if enable_file and enable_line:
        location = "(%(filename)s:%(lineno)d) - "
    elif enable_file:
        location = "(%(filename)s) - "
    elif enable_line:
        location = "(:%(lineno)d) - "
    else:
        location = ""
    name_part = "%(name)s" if name else ""

    if name_part and location:
        name_part += " "
    elif name_part:
        name_part += " - "

    return f"%(asctime)s [%(levelname).1s] {name_part}{location}%(message)s"

def _env_bool(env_key: str) -> bool:
    """환경 변수 값을 bool로 변환한다 ("1"/"true"/"yes"/"on"을 참으로 간주, 대소문자 무시)."""
    return env_key in os.environ and os.environ[env_key].strip().lower() in ("1", "true", "yes", "on")

def _env_bool_optional(env_key: str) -> Optional[bool]:
    """환경 변수 bool 값을 반환한다. 값이 없거나 공백이면 None을 반환한다."""
    value = _env_str(env_key)
    if value is None:
        return None
    return value.lower() in ("1", "true", "yes", "on")

def _env_str(env_key: str) -> Optional[str]:
    """환경 변수 문자열 값을 반환한다. 빈 문자열/공백이면 미지정(None)으로 간주한다."""
    value = os.environ.get(env_key)
    if value is None:
        return None
    value = value.strip()
    return value if value else None

def _resolve_enable_flags(
    enable_file: Optional[bool], enable_line: Optional[bool]
) -> tuple[bool, bool]:
    
    file_value = enable_file if enable_file is not None else _env_bool_optional("LOGGER_ENABLE_FILE")
    line_value = enable_line if enable_line is not None else _env_bool_optional("LOGGER_ENABLE_LINE")

    if file_value is None and line_value is None:
        return True, True

    return bool(file_value), bool(line_value)

def get_logger(
    name: Optional[str] = None,
    level: Optional[Union[int, str]] = None,
    tz: Optional[Union[str, ZoneInfo]] = None,
    enable_file: Optional[bool] = None,
    enable_line: Optional[bool] = None,
    enable_file_write: Optional[bool] = None,
    log_dir: Optional[Union[str, Path]] = None,
) -> logging.Logger:
    """
    콘솔(및 선택적 파일) 핸들러가 구성된 로거를 반환한다.

    각 인자를 생략하면(None) 다음 우선순위로 값이 결정된다.
        1. 환경 변수 (.env 포함, python-dotenv 설치 시): LOGGER_NAME, LOGGER_LEVEL, LOGGER_TZ,
           LOGGER_ENABLE_FILE_WRITE, LOGGER_LOG_DIR, LOGGER_ENABLE_FILE, LOGGER_ENABLE_LINE
        2. 그래도 없으면 하드코딩된 기본값
           (name="", level=INFO, tz=Asia/Seoul, enable_file=True, enable_line=True,
            enable_file_write=False, log_dir="logs")

    name을 생략하면 빈 이름(anonymous/root) 로거가 반환된다.

    enable_file/enable_line은 파라미터나 환경 변수로 둘 다 미지정인 경우에만
    함께 True가 기본값이 된다. 한쪽만 명시하면 나머지는 False로 취급되어
    서로 독립적으로 동작한다 (예: enable_line=True만 주면 파일명 없이 라인 번호만 표시).

    Args:
        name: 로거 이름. None이면 환경 변수 → 빈 이름("") 순으로 결정된다.
        level: 로그 레벨 (int 또는 str)
        tz: 타임스탬프에 적용할 타임존
        enable_file_write: 파일 저장 활성화 여부
            활성화 시 {log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log 경로에 기록되며,
            파일명은 프로세스 시작 시점 기준 1회 결정되어 같은 프로세스의 모든 로거가 공유한다.
        log_dir: 파일 저장 활성화 시 사용할 기준 디렉토리
        enable_file: 로그를 호출한 소스 파일명 표시 여부
            enable_file_write(로그 파일 저장)과는 별개 옵션이다.
        enable_line: 로그를 호출한 소스 라인 번호 표시 여부

    Returns:
        설정된 로거 인스턴스

    Examples:
        >>> logger = get_logger()  # name 생략 시 빈 이름(anonymous) 로거
        >>> logger = get_logger("app", level=logging.DEBUG)
        >>> logger = get_logger("app", enable_file_write=True)
        >>> logger = get_logger("app", enable_file_write=True, log_dir="var/logs")
        >>> logger = get_logger("app", enable_file=True, enable_line=True)
        >>> logger = get_logger(name="")  # 이름 없는(anonymous) 로거
        >>> logger.info("hi")  # ... app (main.py:10) - hi
    """

    if name is None:
        name = _env_str("LOGGER_NAME") or ""

    if level is None:
        level = _env_str("LOGGER_LEVEL") or logging.INFO

    if tz is None:
        tz = _env_str("LOGGER_TZ") or DEFAULT_TZ
    
    enable_file, enable_line = _resolve_enable_flags(enable_file, enable_line)

    if enable_file_write is None:
        enable_file_write = _env_bool("LOGGER_ENABLE_FILE_WRITE") or False
    if log_dir is None:
        log_dir = _env_str("LOGGER_LOG_DIR") or DEFAULT_LOG_DIR

    # level이 문자열인 경우 logging 모듈의 상수로 변환
    if isinstance(level, str):
        logging_level = getattr(logging, level.upper(), logging.INFO)
    else:
        logging_level = level

    formatter = LogFormatter(fmt=_build_fmt(name, enable_file, enable_line), tz=tz)

    logger = logging.getLogger(name)
    logger.setLevel(logging_level)
    for handler in logger.handlers:
        handler.close()
    logger.handlers = []  # 중복 출력 방지
    logger.propagate = False  # 부모 로거로의 전파 방지

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if enable_file_write:
        log_file_path = _get_log_file_path(log_dir, tz)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(override=True)  # .env 파일이 있으면 환경 변수 로드
    except ImportError:
        pass
    
    logger = get_logger("demo")
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    logger = get_logger()
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    logger = get_logger(enable_file=True)
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    logger = get_logger(enable_line=True)
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    logger = get_logger(enable_file=True, enable_line=True)
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    logger = get_logger("daemo", enable_file=True, enable_line=True)
    logger.debug("debug message (숨김, 기본 레벨은 INFO)")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
