"""
helper_logger 모듈

간단 설명:
- 일관된 로깅 설정을 위한 유틸리티를 제공한다.
- 주요 기능: 단축 레벨 포맷터(ShortLevelFormatter), 호출자 기반 자동 로거(get_auto_logger),
  콘솔/파일 핸들러 설정(get_logger), 타임스탬프 기반 로그 회전, 환경변수 샘플 생성(sample_logger_env).

특징:
- 환경변수(.env) 기반 로그 설정
- 우선순위: LOG_LEVEL(전체) → LOG_CONSOLE_LEVEL/LOG_FILE_LEVEL(개별) → 함수 매개변수 → 기본값
- python-dotenv 미설치 시 환경변수 무시하고 기본값 사용
- 로그 레벨 축약: DEBUG→D, INFO→I, WARNING→W, ERROR→E, CRITICAL→C
- 시간대: KST(Asia/Seoul) 적용(타임스탬프에 반영)
- get_logger: console/file 핸들러 구성, 중앙 집중 로깅 지원
- get_auto_logger: 호출자 모듈 이름을 자동 추출하여 로거 이름으로 사용
- 타임스탬프 기반 로그 로테이션: 파일 크기 초과 시 새 타임스탬프 파일 생성
- sample_logger_env: .env.example_logger 샘플 파일 자동 생성

사용 예:
>>> logger = get_logger("app", console=True, file=True)
>>> auto = get_auto_logger(console=True)
>>> env_file = sample_logger_env()

주의:
- 같은 이름으로 요청하면 동일한 로거 인스턴스를 재사용한다.
- 로거 레벨은 핸들러 레벨과 조합되어 실제 출력이 결정된다.
"""

import inspect
import logging
import logging.handlers
import os
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Union

# python-dotenv import (선택적 의존성)
try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

# 전역 변수
_loggers: Dict[str, logging.Logger] = {}
_file_handlers: Dict[Path, logging.Handler] = {}  # 파일 경로별 핸들러 캐시
_process_start_time: str = ""  # 프로세스 시작 시점 타임스탬프 (lazy initialization)

try:
    from zoneinfo import ZoneInfo  # Python 3.9+

    _kst = ZoneInfo("Asia/Seoul")
except ImportError:
    try:
        import pytz  # type: ignore

        _kst = pytz.timezone("Asia/Seoul")
    except ImportError:
        _kst = datetime.now().astimezone().tzinfo


def _get_process_start_time() -> str:
    """프로세스 시작 시점 타임스탬프 반환 (lazy initialization)"""
    global _process_start_time
    if not _process_start_time:
        _process_start_time = datetime.now(_kst).strftime("%Y%m%d_%H%M%S")
    return _process_start_time


class ShortLevelFormatter(logging.Formatter):
    """
    로그 레벨을 단축 표기하는 커스텀 포맷터

    로그 레벨을 한 글자로 축약:
    DEBUG→D, INFO→I, WARNING→W, ERROR→E, CRITICAL→C

    시간은 KST(Asia/Seoul) 적용
    """

    LEVEL_MAP: Dict[str, str] = {
        "DEBUG": "D",
        "INFO": "I",
        "WARNING": "W",
        "ERROR": "E",
        "CRITICAL": "C",
    }

    def format(self, record: logging.LogRecord) -> str:
        """로그 레벨을 축약하여 포맷"""
        record.levelname = self.LEVEL_MAP.get(record.levelname, record.levelname)
        return super().format(record)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """KST 시간으로 변환하여 포맷"""
        ct = datetime.fromtimestamp(record.created, tz=_kst)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.strftime("%Y-%m-%d %H:%M:%S")


class TimestampRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    타임스탬프 기반 로그 파일 로테이션 핸들러

    max_log_file_size 도달 시:
    - 일반 파일명 (app.log): app_20260208_143052.log 형식으로 새 파일 생성
    - 타임스탬프 파일명 (20260208_143052.log): 새 타임스탬프로 갱신
    """

    def __init__(
        self,
        filename: Path,
        log_file_basename: str,
        maxBytes: int = 0,
        encoding: Optional[str] = None,
    ):
        """
        Args:
            filename: 로그 파일 경로
            log_file_basename: 로그 파일 기본 이름 (auto_time 또는 커스텀)
            maxBytes: 최대 파일 크기 (0=무제한)
            encoding: 파일 인코딩
        """
        self.log_file_basename = log_file_basename
        self.log_dir = filename.parent

        # maxBytes=0이면 로테이션 비활성화
        super().__init__(
            str(filename),
            maxBytes=maxBytes,
            backupCount=0,  # 커스텀 로테이션 사용
            encoding=encoding,
        )

    def doRollover(self):
        """파일 크기 초과 시 타임스탬프 기반 새 파일 생성"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # 새 타임스탬프 생성
        new_timestamp = datetime.now(_kst).strftime("%Y%m%d_%H%M%S")

        if self.log_file_basename == "auto_time":
            # 타임스탬프 파일명 → 새 타임스탬프로 갱신
            new_filename = f"{new_timestamp}.log"
        else:
            # 일반 파일명 → 파일명_타임스탬프.log
            new_filename = f"{self.log_file_basename}_{new_timestamp}.log"

        # 새 파일 경로로 변경
        self.baseFilename = str(self.log_dir / new_filename)

        # 새 파일 열기
        if not self.delay:
            self.stream = self._open()


def _clear_handlers(logger: logging.Logger) -> None:
    """
    로거의 모든 핸들러를 제거하고 리소스 해제

    Args:
        logger: 핸들러를 제거할 로거 인스턴스
    """
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        # 파일 핸들러 캐시에 있는 경우 close하지 않음 (다른 로거가 사용 중일 수 있음)
        handler_file_path = None
        if isinstance(
            handler, (logging.handlers.RotatingFileHandler, TimestampRotatingFileHandler)
        ):
            handler_file_path = Path(handler.baseFilename)

        if handler_file_path and handler_file_path in _file_handlers:
            # 캐시된 핸들러는 close하지 않음
            pass
        else:
            # 캐시되지 않은 핸들러만 close
            handler.close()


def _load_env_config(
    env_path: Optional[Path] = None, use_env: bool = True
) -> Dict[str, Union[int, Path, bool, str, None]]:
    """
    .env 파일에서 로그 설정을 로드

    우선순위:
    1. LOG_LEVEL (전체 로그 레벨)
    2. LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL (개별 설정)
    3. LOG_DIR (로그 디렉토리)
    4. LOG_FILE_ENABLED (파일 로깅 활성화)
    5. LOG_USE_CENTRAL_FILE (중앙 집중 로깅)
    6. LOG_FILE_BASENAME (로그 파일 기본 이름)
    7. MAX_LOG_FILE_SIZE (로그 파일 최대 크기, MB)

    Args:
        env_path: .env 파일 경로 (기본: None = 현재 디렉토리)
        use_env: 환경변수 사용 여부 (기본: True)

    Returns:
        로그 설정 딕셔너리 {
            'console_level': Optional[int],
            'file_level': Optional[int],
            'log_dir': Optional[Path],
            'file': Optional[bool],
            'use_central_file': Optional[bool],
            'log_file_basename': Optional[str],
            'max_log_file_size': Optional[int]
        }
    """
    config: Dict[str, Union[int, Path, bool, str, None]] = {
        "console_level": None,
        "file_level": None,
        "log_dir": None,
        "file": None,
        "use_central_file": None,
        "log_file_basename": None,
        "max_log_file_size": None,
    }

    if not use_env or not _DOTENV_AVAILABLE:
        return config

    # .env 파일 로드
    if env_path:
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)

    # 로그 레벨 매핑
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # 1순위: LOG_LEVEL (전체)
    log_level_str = os.getenv("LOG_LEVEL", "").upper()
    if log_level_str in level_map:
        config["console_level"] = level_map[log_level_str]
        config["file_level"] = level_map[log_level_str]

    # 2순위: 개별 설정 (LOG_LEVEL이 없을 때만 적용)
    if config["console_level"] is None:
        console_level_str = os.getenv("LOG_CONSOLE_LEVEL", "").upper()
        if console_level_str in level_map:
            config["console_level"] = level_map[console_level_str]

    if config["file_level"] is None:
        file_level_str = os.getenv("LOG_FILE_LEVEL", "").upper()
        if file_level_str in level_map:
            config["file_level"] = level_map[file_level_str]

    # LOG_DIR
    log_dir_str = os.getenv("LOG_DIR", "").strip()
    if log_dir_str:
        config["log_dir"] = Path(log_dir_str)

    # LOG_FILE_ENABLED
    log_file_enabled_str = os.getenv("LOG_FILE_ENABLED", "").strip().lower()
    if log_file_enabled_str in ("true", "1", "yes"):
        config["file"] = True
    elif log_file_enabled_str in ("false", "0", "no"):
        config["file"] = False

    # LOG_USE_CENTRAL_FILE
    use_central_file_str = os.getenv("LOG_USE_CENTRAL_FILE", "").strip().lower()
    if use_central_file_str in ("true", "1", "yes"):
        config["use_central_file"] = True
    elif use_central_file_str in ("false", "0", "no"):
        config["use_central_file"] = False

    # LOG_FILE_BASENAME
    log_file_basename_str = os.getenv("LOG_FILE_BASENAME", "").strip()
    if log_file_basename_str:
        config["log_file_basename"] = log_file_basename_str

    # MAX_LOG_FILE_SIZE (MB 단위)
    max_log_file_size_str = os.getenv("MAX_LOG_FILE_SIZE", "").strip()
    if max_log_file_size_str.isdigit():
        config["max_log_file_size"] = int(max_log_file_size_str)

    return config


def get_logger(
    name: str,
    console: bool = True,
    console_level: Optional[int] = None,
    file: Optional[bool] = None,
    file_level: Optional[int] = None,
    log_level: Optional[int] = None,
    log_dir: Optional[Path] = None,
    use_env: bool = True,
    env_path: Optional[Path] = None,
    use_central_file: Optional[bool] = None,
    log_file_basename: Optional[str] = None,
    max_log_file_size: Optional[int] = None,
) -> logging.Logger:
    """
    로거 인스턴스 생성 및 반환

    환경변수 우선순위 (.env 파일):
    1. LOG_LEVEL: 전체 로그 레벨 설정
    2. LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL: 개별 설정
    3. LOG_DIR: 로그 디렉토리
    4. LOG_FILE_ENABLED: 파일 로깅 활성화 (true/false)
    5. LOG_USE_CENTRAL_FILE: 중앙 집중 로깅 (true/false, 기본: true)
    6. LOG_FILE_BASENAME: 로그 파일 기본 이름 (auto_time/커스텀, 기본: auto_time)
    7. MAX_LOG_FILE_SIZE: 로그 파일 최대 크기 (MB, 0=무제한, 기본: 10)

    최종 우선순위: 함수 매개변수 → 환경변수 → 기본값

    Args:
        name: 로거 이름
        console: 콘솔 출력 여부 (기본: True)
        console_level: 콘솔 로그 레벨 (기본: None → 환경변수 → INFO)
        file: 파일 저장 여부 (기본: None → 환경변수 → False)
        file_level: 파일 로그 레벨 (기본: None → 환경변수 → INFO)
        log_level: 전체 로그 레벨 (console_level, file_level 우선)
        log_dir: 로그 파일 저장 디렉토리 (기본: None → 환경변수 → ./logs)
        use_env: 환경변수 사용 여부 (기본: True)
        env_path: .env 파일 경로 (기본: None = 현재 디렉토리)
        use_central_file: 중앙 집중 로깅 (기본: None → 환경변수 → True)
        log_file_basename: 로그 파일 기본 이름 (기본: None → 환경변수 → auto_time)
            - "auto_time": YYYYMMDD_HHMMSS.log (프로세스 시작 시점)
            - 기타 문자열: <log_file_basename>.log
        max_log_file_size: 로그 파일 최대 크기 MB (기본: None → 환경변수 → 10, 0=무제한)

    Returns:
        설정된 로거 인스턴스

    Examples:
        >>> logger = get_logger("my_app")  # 환경변수 적용
        >>> logger = get_logger("my_app", use_central_file=True, log_file_basename="app")
        >>> logger = get_logger("my_app", use_central_file=False)  # 모듈별 분리
        >>> logger = get_logger("my_app", max_log_file_size=0)  # 무제한
    """
    # 중복 생성 방지
    if name in _loggers:
        return _loggers[name]

    # 환경변수 로드
    env_config = _load_env_config(env_path=env_path, use_env=use_env)

    # 우선순위: 함수 매개변수 → 환경변수 → 기본값
    final_console_level: int
    final_file_level: int
    final_file: bool
    final_log_dir: Path
    final_use_central_file: bool
    final_log_file_basename: str
    final_max_log_file_size: int

    if log_level is not None:
        final_console_level = log_level
        final_file_level = log_level
    else:
        if console_level is None:
            env_console = env_config["console_level"]
            final_console_level = env_console if isinstance(env_console, int) else logging.INFO
        else:
            final_console_level = console_level

        if file_level is None:
            env_file = env_config["file_level"]
            final_file_level = env_file if isinstance(env_file, int) else logging.INFO
        else:
            final_file_level = file_level

    if file is None:
        env_file_flag = env_config["file"]
        final_file = env_file_flag if isinstance(env_file_flag, bool) else False
    else:
        final_file = file

    if log_dir is None:
        env_log_dir = env_config["log_dir"]
        final_log_dir = env_log_dir if isinstance(env_log_dir, Path) else Path("./logs")
    else:
        final_log_dir = log_dir

    if use_central_file is None:
        env_use_central = env_config["use_central_file"]
        final_use_central_file = env_use_central if isinstance(env_use_central, bool) else True
    else:
        final_use_central_file = use_central_file

    if log_file_basename is None:
        env_basename = env_config["log_file_basename"]
        final_log_file_basename = env_basename if isinstance(env_basename, str) else "auto_time"
    else:
        final_log_file_basename = log_file_basename

    if max_log_file_size is None:
        env_max_size = env_config["max_log_file_size"]
        final_max_log_file_size = env_max_size if isinstance(env_max_size, int) else 10
    else:
        final_max_log_file_size = max_log_file_size

    logger = logging.getLogger(name)

    # 기존 핸들러 제거 (중복 방지)
    if logger.handlers:
        _clear_handlers(logger)

    # 로거 레벨은 가장 낮은 레벨로 설정 (핸들러에서 필터링)
    logger.setLevel(
        min(final_console_level, final_file_level) if final_file else final_console_level
    )
    logger.propagate = False

    # 포맷터 생성
    formatter = ShortLevelFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(final_console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 파일 핸들러
    if final_file:
        final_log_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 결정 로직
        if final_use_central_file:
            # 중앙 집중식: 모든 로거가 같은 파일 사용
            if final_log_file_basename == "auto_time":
                log_filename = f"{_get_process_start_time()}.log"
            else:
                log_filename = f"{final_log_file_basename}.log"
        else:
            # 모듈별 분리: 기존 방식 유지
            log_filename = f"{name}.log"

        log_file = final_log_dir / log_filename

        # 파일 핸들러 캐싱: 동일 경로의 핸들러가 이미 존재하면 재사용
        if log_file in _file_handlers:
            file_handler = _file_handlers[log_file]
            logger.addHandler(file_handler)
        else:
            # 파일 크기 제한 (MB → bytes)
            max_bytes = final_max_log_file_size * 1024 * 1024 if final_max_log_file_size > 0 else 0

            # 타임스탬프 로테이션 핸들러 사용
            file_handler = TimestampRotatingFileHandler(
                filename=log_file,
                log_file_basename=final_log_file_basename,
                maxBytes=max_bytes,
                encoding="utf-8",
            )
            file_handler.setLevel(final_file_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # 파일 핸들러 캐시에 저장
            _file_handlers[log_file] = file_handler

    # .set() 메서드 바인딩 (monkey-patch)
    logger.set = types.MethodType(_set_method, logger)

    _loggers[name] = logger
    return logger


def reconfigure_logger(name: str, **kwargs) -> logging.Logger:
    """
    기존 로거를 재구성 (독립 함수 방식)

    기존 핸들러를 모두 제거한 후 새로운 설정으로 로거를 재생성합니다.
    캐시에서 제거 후 get_logger를 재호출하므로 환경변수 및 매개변수 우선순위가 동일하게 적용됩니다.

    주의:
        - 파일 핸들러 캐시는 유지됩니다 (다른 로거가 사용 중일 수 있음)
        - 파일 핸들러 캐시를 완전히 초기화하려면 _clear_file_handler_cache()를 호출하세요

    Args:
        name: 로거 이름
        **kwargs: get_logger의 모든 매개변수 지원

    Returns:
        재구성된 로거 인스턴스 (기존과 동일한 인스턴스)

    Examples:
        >>> logger = get_logger("app", console=True)
        >>> logger = reconfigure_logger("app", console_level=logging.DEBUG, file=True)
        >>> logger.debug("재구성 후 DEBUG 출력")
    """
    logger = logging.getLogger(name)
    _clear_handlers(logger)
    if name in _loggers:
        del _loggers[name]
    return get_logger(name, **kwargs)


def _clear_file_handler_cache() -> None:
    """
    파일 핸들러 캐시를 완전히 초기화

    모든 캐시된 파일 핸들러를 close하고 캐시를 비웁니다.
    테스트 환경이나 완전한 로거 재초기화가 필요한 경우 사용합니다.

    Examples:
        >>> _clear_file_handler_cache()
        >>> # 새로운 파일 핸들러가 생성됩니다
    """
    global _file_handlers
    for handler in _file_handlers.values():
        try:
            handler.close()
        except Exception:
            pass
    _file_handlers.clear()


def _set_method(self, **kwargs):
    """
    로거 인스턴스 재구성 메서드 (monkey-patched)

    logger.set(**kwargs) 형태로 호출하여 기존 로거를 재구성합니다.

    Args:
        **kwargs: get_logger의 모든 매개변수 지원

    Returns:
        self: 재구성된 로거 인스턴스 (동일 인스턴스)

    Examples:
        >>> logger = get_logger("app")
        >>> logger.set(console_level=logging.DEBUG)
        >>> logger = logger.set(file=True)
    """
    reconfigure_logger(self.name, **kwargs)
    return self


def get_auto_logger(**kwargs) -> logging.Logger:
    """
    호출자 모듈 이름을 기반으로 자동 로거 생성 및 반환

    동작:
    - 현재 프레임의 한 단계 위(f_back)에서 호출자 정보를 얻어 호출자 모듈의
      __file__ 값을 사용하여 로거 이름(Path(...).stem)을 결정합니다.
    - 호출자 프레임 또는 __file__이 없는 경우 sys.argv[0] 또는 '__main__'을
      대체값으로 사용합니다.
    - 프레임 참조는 finally 블록에서 삭제하여 참조 순환(memory leak)을 방지합니다.
    - 전달된 모든 kwargs는 내부의 get_logger에 그대로 전달됩니다.
    - 기본적으로 환경변수(.env) 설정을 자동 적용합니다 (use_env=True).

    Args:
        **kwargs: get_logger로 전달할 옵션들

    Returns:
        logging.Logger: 생성되거나 재사용된 로거 인스턴스

    Examples:
        >>> logger = get_auto_logger()
        >>> logger = get_auto_logger(use_env=False)
        >>> logger = get_auto_logger(console_level=logging.DEBUG)
        >>> logger = get_auto_logger(file=True, log_file_basename="app")
    """
    frame = inspect.currentframe()
    try:
        caller = frame.f_back if frame is not None else None

        caller_file = None
        if caller is not None:
            caller_file = caller.f_globals.get("__file__")

        if not caller_file:
            caller_file = sys.argv[0] if len(sys.argv) > 0 and sys.argv[0] else "__main__"

        name = Path(caller_file).stem
    finally:
        try:
            del frame
        except Exception:
            pass

    return get_logger(name, **kwargs)


def sample_logger_env(output_dir: Optional[Path] = None) -> Path:
    """
    .env.example_logger 샘플 파일 생성

    현재 폴더(또는 지정된 폴더)에 helper_logger의 환경변수 설정 예제 파일을 생성합니다.
    파일명: .env.example_logger

    Args:
        output_dir: 파일을 생성할 디렉토리 (기본: None = 현재 디렉토리)

    Returns:
        생성된 파일의 경로 (Path 객체)

    Examples:
        >>> env_file = sample_logger_env()
        >>> print(env_file)
        Path('d:/path/to/.env.example_logger')
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    env_content = """# helper_logger 환경변수 설정 예제
# 이 파일을 .env로 복사하여 사용하세요

# =============================================================================
# 로그 레벨 설정 (우선순위)
# =============================================================================

# 1순위: 전체 로그 레벨 (콘솔과 파일 모두 적용)
# LOG_LEVEL을 설정하면 LOG_CONSOLE_LEVEL과 LOG_FILE_LEVEL보다 우선합니다
# 옵션: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# 2순위: 개별 로그 레벨 (LOG_LEVEL이 설정되지 않은 경우에만 적용)
# 콘솔 출력 로그 레벨
LOG_CONSOLE_LEVEL=WARNING

# 파일 저장 로그 레벨
LOG_FILE_LEVEL=DEBUG

# =============================================================================
# 로그 디렉토리 및 파일 설정
# =============================================================================

# 로그 파일이 저장될 디렉토리 경로
# 기본값: ./logs
LOG_DIR=./logs

# 파일 로깅 활성화 여부
# 옵션: true, false, 1, 0, yes, no
# 기본값: false (파일 로깅 비활성화)
LOG_FILE_ENABLED=false

# =============================================================================
# 중앙 집중식 로깅 설정 (권장)
# =============================================================================

# 중앙 집중 로깅 활성화 여부
# true: 모든 모듈이 하나의 파일에 로그 기록 (시퀀스 추적 용이)
# false: 모듈별로 개별 파일에 기록 (기존 방식)
# 기본값: true
LOG_USE_CENTRAL_FILE=true

# 로그 파일 기본 이름 설정
# auto_time: 프로세스 시작 시점 기준 타임스탬프 파일명 (YYYYMMDD_HHMMSS.log)
#            예: 20260208_143052.log (커널 재시작 시 새 파일 생성)
# 기타 문자열: 고정 파일명 사용
#            예: app → app.log, mylog → mylog.log
# 기본값: auto_time
LOG_FILE_BASENAME=auto_time

# 로그 파일 최대 크기 (MB 단위)
# 0: 무제한 (로테이션 비활성화)
# > 0: 지정된 크기 도달 시 새 파일 생성
#      - auto_time: 20260208_143052.log → 20260208_143125.log (새 타임스탬프)
#      - 일반 파일명 (app): app.log → app_20260208_143052.log (파일명_타임스탬프)
# 기본값: 10 (10MB)
MAX_LOG_FILE_SIZE=10

# =============================================================================
# 사용 예제
# =============================================================================
# 
# 예제 1: 타임스탬프 기반 중앙 집중식 로깅 (권장)
# LOG_FILE_ENABLED=true
# LOG_USE_CENTRAL_FILE=true
# LOG_FILE_BASENAME=auto_time
# MAX_LOG_FILE_SIZE=10
# → 결과: logs/20260208_143052.log (모든 모듈 통합)
# → 10MB 도달 시: logs/20260208_143125.log (새 타임스탬프)
#
# 예제 2: 고정 파일명으로 중앙 집중식 로깅
# LOG_FILE_ENABLED=true
# LOG_USE_CENTRAL_FILE=true
# LOG_FILE_BASENAME=app
# MAX_LOG_FILE_SIZE=10
# → 결과: logs/app.log (모든 모듈이 app.log에 기록)
# → 10MB 도달 시: logs/app_20260208_143052.log (파일명_타임스탬프)
#
# 예제 3: 무제한 크기 로그 파일
# LOG_FILE_ENABLED=true
# LOG_USE_CENTRAL_FILE=true
# LOG_FILE_BASENAME=app
# MAX_LOG_FILE_SIZE=0
# → 결과: logs/app.log (로테이션 없음, 무제한 증가)
#
# 예제 4: 모듈별 개별 파일 (기존 방식)
# LOG_FILE_ENABLED=true
# LOG_USE_CENTRAL_FILE=false
# → 결과: logs/module1.log, logs/module2.log (모듈별 분리)
#
# =============================================================================
# 우선순위 정리
# =============================================================================
#
# 최종 설정 우선순위:
# 1. 함수 매개변수
#    - console_level, file_level, file, log_dir
#    - use_central_file, log_file_basename, max_log_file_size
# 2. 환경변수 (.env 파일)
#    - LOG_LEVEL (전체)
#    - LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL (개별)
#    - LOG_DIR, LOG_FILE_ENABLED
#    - LOG_USE_CENTRAL_FILE, LOG_FILE_BASENAME, MAX_LOG_FILE_SIZE
# 3. 기본값
#    - console_level=INFO, file_level=INFO
#    - file=False, log_dir=./logs
#    - use_central_file=True, log_file_basename=auto_time
#    - max_log_file_size=10 (MB)
#
# =============================================================================
"""

    output_file = output_dir / ".env.example_logger"
    output_file.write_text(env_content, encoding="utf-8")

    return output_file


if __name__ == "__main__":
    """로거 기능 테스트"""
    print("=" * 60)
    print("로거 테스트 시작")
    print("=" * 60)

    # 테스트 1: 타임스탬프 기반 중앙 집중식 로깅
    print("\n[테스트 1] 타임스탬프 기반 중앙 집중식 로깅")
    test_logger1 = get_logger(
        "module1", file=True, use_central_file=True, log_file_basename="auto_time"
    )
    test_logger2 = get_logger(
        "module2", file=True, use_central_file=True, log_file_basename="auto_time"
    )

    test_logger1.info("module1 로그")
    test_logger2.info("module2 로그")
    print(f"→ 모든 로그가 logs/{_get_process_start_time()}.log에 기록됨")

    # 테스트 2: 고정 파일명 중앙 집중식 로깅
    print("\n[테스트 2] 고정 파일명 중앙 집중식 로깅")
    test_logger3 = get_logger("module3", file=True, use_central_file=True, log_file_basename="app")
    test_logger4 = get_logger("module4", file=True, use_central_file=True, log_file_basename="app")

    test_logger3.info("module3 로그")
    test_logger4.info("module4 로그")
    print("→ 모든 로그가 logs/app.log에 기록됨")

    # 테스트 3: 모듈별 개별 파일 (기존 방식)
    print("\n[테스트 3] 모듈별 개별 파일")
    test_logger5 = get_logger("module5", file=True, use_central_file=False)
    test_logger6 = get_logger("module6", file=True, use_central_file=False)

    test_logger5.info("module5 로그")
    test_logger6.info("module6 로그")
    print("→ logs/module5.log, logs/module6.log에 각각 기록됨")

    # 테스트 4: 로그 파일 크기 제한
    print("\n[테스트 4] 로그 파일 크기 제한 (시뮬레이션)")
    test_logger7 = get_logger(
        "test_rotation",
        file=True,
        use_central_file=True,
        log_file_basename="rotation_test",
        max_log_file_size=0,  # 실제 테스트 시 작은 값 (예: 0.001MB)
    )

    for i in range(10):
        test_logger7.info(f"로그 메시지 {i+1}")
    print("→ logs/rotation_test.log에 기록됨 (무제한 크기)")
    print("→ max_log_file_size=10 설정 시, 10MB 도달 시 rotation_test_20260208_143052.log 생성")

    # 테스트 5: sample_logger_env
    print("\n[테스트 5] sample_logger_env() - 샘플 파일 생성")
    env_file = sample_logger_env()
    print(f"✓ 생성 성공: {env_file}")

    # 테스트 6: 파일 핸들러 캐싱 검증
    print("\n[테스트 6] 파일 핸들러 캐싱 검증 (중복 출력 방지)")
    print(f"초기 파일 핸들러 캐시 크기: {len(_file_handlers)}")

    # 동일한 중앙 집중 파일을 사용하는 여러 로거 생성
    cache_logger1 = get_logger(
        "cache_test1", file=True, use_central_file=True, log_file_basename="cache_test"
    )
    print(f"cache_test1 생성 후 캐시 크기: {len(_file_handlers)}")
    print(f"cache_test1 핸들러 개수: {len(cache_logger1.handlers)}")

    cache_logger2 = get_logger(
        "cache_test2", file=True, use_central_file=True, log_file_basename="cache_test"
    )
    print(f"cache_test2 생성 후 캐시 크기: {len(_file_handlers)}")
    print(f"cache_test2 핸들러 개수: {len(cache_logger2.handlers)}")

    # 동일한 파일 핸들러 객체를 공유하는지 확인
    cache_logger1_file_handler = [
        h for h in cache_logger1.handlers if isinstance(h, TimestampRotatingFileHandler)
    ]
    cache_logger2_file_handler = [
        h for h in cache_logger2.handlers if isinstance(h, TimestampRotatingFileHandler)
    ]

    if cache_logger1_file_handler and cache_logger2_file_handler:
        same_handler = cache_logger1_file_handler[0] is cache_logger2_file_handler[0]
        print(f"동일한 핸들러 객체 공유: {same_handler}")

    cache_logger1.info("cache_test1 로그")
    cache_logger2.info("cache_test2 로그")
    print("→ logs/cache_test.log 파일을 확인하여 각 로그가 1회만 출력되는지 확인")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
