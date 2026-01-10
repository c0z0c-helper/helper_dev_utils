"""
helper_logger 모듈

간단 설명:
- 일관된 로깅 설정을 위한 유틸리티를 제공한다.
- 주요 기능: 단축 레벨 포맷터(ShortLevelFormatter), 호출자 기반 자동 로거(get_auto_logger),
  콘솔/파일 핸들러 설정(get_logger), 회전 로그(RotatingFileHandler) 지원, 환경변수 샘플 생성(sample_logger_env).

특징:
- 환경변수(.env) 기반 로그 설정: LOG_LEVEL, LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL, LOG_DIR, LOG_FILE_ENABLED
- 우선순위: LOG_LEVEL(전체) → LOG_CONSOLE_LEVEL/LOG_FILE_LEVEL(개별) → 함수 매개변수 → 기본값
- python-dotenv 미설치 시 환경변수 무시하고 기본값 사용
- 로그 레벨 축약: DEBUG→D, INFO→I, WARNING→W, ERROR→E, CRITICAL→C
- 시간대: KST(Asia/Seoul) 적용(타임스탬프에 반영)
- get_logger: console/file 핸들러 구성, max_bytes와 backup_count로 로그 회전 제어
- get_auto_logger: 호출자 모듈 이름을 자동 추출하여 로거 이름으로 사용(프레임 참조 해제 포함)
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
from typing import Optional, Dict, Any, Union

# python-dotenv import (선택적 의존성)
try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

# 전역 변수
_loggers: Dict[str, logging.Logger] = {}
try:
    from zoneinfo import ZoneInfo  # Python 3.9+

    _kst = ZoneInfo("Asia/Seoul")
except ImportError:
    try:
        import pytz  # type: ignore

        _kst = pytz.timezone("Asia/Seoul")
    except ImportError:
        # 어떤 타임존 정보도 없으면 시스템 로컬 timezone으로 대체
        _kst = datetime.now().astimezone().tzinfo


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


def _clear_handlers(logger: logging.Logger) -> None:
    """
    로거의 모든 핸들러를 제거하고 리소스 해제

    Args:
        logger: 핸들러를 제거할 로거 인스턴스
    """
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def _load_env_config(
    env_path: Optional[Path] = None, use_env: bool = True
) -> Dict[str, Union[int, Path, bool, None]]:
    """
    .env 파일에서 로그 설정을 로드

    우선순위:
    1. LOG_LEVEL (전체 로그 레벨)
    2. LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL (개별 설정)
    3. LOG_DIR (로그 디렉토리)
    4. LOG_FILE_ENABLED (파일 로깅 활성화)

    Args:
        env_path: .env 파일 경로 (기본: None = 현재 디렉토리)
        use_env: 환경변수 사용 여부 (기본: True)

    Returns:
        로그 설정 딕셔너리 {
            'console_level': Optional[int],
            'file_level': Optional[int],
            'log_dir': Optional[Path],
            'file': Optional[bool]
        }
    """
    config: Dict[str, Union[int, Path, bool, None]] = {
        "console_level": None,
        "file_level": None,
        "log_dir": None,
        "file": None,
    }

    if not use_env or not _DOTENV_AVAILABLE:
        return config

    # .env 파일 로드
    if env_path:
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)

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

    return config


def get_logger(
    name: str,
    console: bool = True,
    console_level: Optional[int] = None,
    file: Optional[bool] = None,
    file_level: Optional[int] = None,
    log_level: Optional[int] = None,
    log_dir: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    use_env: bool = True,
    env_path: Optional[Path] = None,
) -> logging.Logger:
    """
    로거 인스턴스 생성 및 반환

    환경변수 우선순위 (.env 파일):
    1. LOG_LEVEL: 전체 로그 레벨 설정
    2. LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL: 개별 설정
    3. LOG_DIR: 로그 디렉토리
    4. LOG_FILE_ENABLED: 파일 로깅 활성화 (true/false)

    최종 우선순위: 함수 매개변수 → 환경변수 → 기본값

    Args:
        name: 로거 이름
        console: 콘솔 출력 여부 (기본: True)
        console_level: 콘솔 로그 레벨 (기본: None → 환경변수 → INFO)
        file: 파일 저장 여부 (기본: None → 환경변수 → False)
        file_level: 파일 로그 레벨 (기본: None → 환경변수 → DEBUG)
        log_level: 전체 로그 레벨 (console_level, file_level 우선)
        log_dir: 로그 파일 저장 디렉토리 (기본: None → 환경변수 → ./logs)
        max_bytes: 로그 파일 최대 크기 (기본: 10MB)
        backup_count: 백업 파일 개수 (기본: 5)
        use_env: 환경변수 사용 여부 (기본: True)
        env_path: .env 파일 경로 (기본: None = 현재 디렉토리)

    Returns:
        설정된 로거 인스턴스

    Examples:
        >>> logger = get_logger("my_app")  # 환경변수 적용
        >>> logger = get_logger("my_app", use_env=False)  # 환경변수 무시
        >>> logger = get_logger("my_app", console_level=logging.WARNING)  # 명시적 설정
        >>> logger = get_logger("my_app", env_path=Path(".env.local"))  # 커스텀 .env
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
    final_log_dir: Optional[Path]

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
        final_log_dir = env_log_dir if isinstance(env_log_dir, Path) else None
    else:
        final_log_dir = log_dir

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
        # fmt='%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
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
        if final_log_dir is None:
            final_log_dir = Path("./logs")
        final_log_dir.mkdir(parents=True, exist_ok=True)

        log_file = final_log_dir / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(final_file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # .set() 메서드 바인딩 (monkey-patch)
    logger.set = types.MethodType(_set_method, logger)

    _loggers[name] = logger
    return logger


def reconfigure_logger(name: str, **kwargs) -> logging.Logger:
    """
    기존 로거를 재구성 (독립 함수 방식)

    기존 핸들러를 모두 제거한 후 새로운 설정으로 로거를 재생성합니다.
    캐시에서 제거 후 get_logger를 재호출하므로 환경변수 및 매개변수 우선순위가 동일하게 적용됩니다.

    Args:
        name: 로거 이름
        **kwargs: get_logger의 모든 매개변수 지원
            - console, console_level, file, file_level, log_level, log_dir
            - max_bytes, backup_count, use_env, env_path

    Returns:
        재구성된 로거 인스턴스 (기존과 동일한 인스턴스)

    Examples:
        >>> logger = get_logger("app", console=True)
        >>> logger = reconfigure_logger("app", console_level=logging.DEBUG, file=True)
        >>> logger.debug("재구성 후 DEBUG 출력")

    주의:
        - 기존 핸들러가 모두 제거되고 새로 생성됩니다
        - 다른 곳에서 참조 중인 동일 이름 로거도 영향받습니다
        - 로거 이름은 변경 불가능합니다 (Python logging 내부 구조)
    """
    logger = logging.getLogger(name)
    _clear_handlers(logger)
    if name in _loggers:
        del _loggers[name]
    return get_logger(name, **kwargs)


def _set_method(self, **kwargs):
    """
    로거 인스턴스 재구성 메서드 (monkey-patched)

    logger.set(**kwargs) 형태로 호출하여 기존 로거를 재구성합니다.
    내부적으로 reconfigure_logger를 호출하며, self를 반환하여
    재할당 없이도 사용 가능합니다.

    Args:
        **kwargs: get_logger의 모든 매개변수 지원

    Returns:
        self: 재구성된 로거 인스턴스 (동일 인스턴스)

    Examples:
        >>> logger = get_logger("app")
        >>> logger.set(console_level=logging.DEBUG)  # 반환값 무시
        >>> logger = logger.set(file=True)  # 명시적 재할당 (권장)
    """
    reconfigure_logger(self.name, **kwargs)
    return self


def get_auto_logger(**kwargs) -> logging.Logger:
    """
    호출자 모듈 이름을 기반으로 자동 로거 생성 및 반환.

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
            - console, file, console_level, file_level, log_level, log_dir
            - use_env: 환경변수 사용 여부 (기본: True)
            - env_path: .env 파일 경로 (기본: None)

    Returns:
        logging.Logger: 생성되거나 재사용된 로거 인스턴스

    Examples:
        >>> logger = get_auto_logger()  # 환경변수 자동 적용
        >>> logger = get_auto_logger(use_env=False)  # 환경변수 무시
        >>> logger = get_auto_logger(console_level=logging.DEBUG)
        >>> logger = get_auto_logger(file=True, env_path=Path(".env.local"))
    """
    frame = inspect.currentframe()
    try:
        caller = frame.f_back if frame is not None else None

        # 호출자 전역에서 '__file__'을 시도하여 호출자 모듈 경로를 획득
        caller_file = None
        if caller is not None:
            caller_file = caller.f_globals.get("__file__")

        # __file__이 없거나 호출자 정보가 없을 때의 안전한 대체값
        if not caller_file:
            caller_file = sys.argv[0] if len(sys.argv) > 0 and sys.argv[0] else "__main__"

        name = Path(caller_file).stem
    finally:
        # 프레임 참조 해제(참조 순환 방지)
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

        >>> env_file = sample_logger_env(output_dir=Path("./config"))
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # .env.example_logger 파일 내용
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
# 사용 예제
# =============================================================================
# 
# 예제 1: 모든 로그를 DEBUG 레벨로 설정하고 파일에 저장
# LOG_LEVEL=DEBUG
# LOG_FILE_ENABLED=true
# LOG_DIR=./my_logs
#
# 예제 2: 콘솔은 WARNING, 파일은 DEBUG (파일 로깅 활성화)
# # LOG_LEVEL=  (주석 처리)
# LOG_CONSOLE_LEVEL=WARNING
# LOG_FILE_LEVEL=DEBUG
# LOG_FILE_ENABLED=true
#
# 예제 3: 환경변수 무시하고 코드에서 직접 설정
# logger = get_logger("my_app", use_env=False, console_level=logging.INFO)
#
# =============================================================================
# 우선순위 정리
# =============================================================================
#
# 최종 설정 우선순위:
# 1. 함수 매개변수 (console_level, file_level, file, log_dir 등)
# 2. 환경변수 (.env 파일)
#    - LOG_LEVEL (전체)
#    - LOG_CONSOLE_LEVEL, LOG_FILE_LEVEL (개별)
#    - LOG_DIR, LOG_FILE_ENABLED
# 3. 기본값 (console_level=INFO, file_level=DEBUG, file=False, log_dir=./logs)
#
# =============================================================================
"""

    # 파일 생성
    output_file = output_dir / ".env.example_logger"
    output_file.write_text(env_content, encoding="utf-8")

    return output_file


# 모듈 레벨 기본 로거
logger = get_auto_logger()

if __name__ == "__main__":
    """로거 기능 테스트"""

    print("=" * 60)
    print("로거 테스트 시작")
    print("=" * 60)

    # 테스트 1: 콘솔만 (기본)
    print("\n[테스트 1] 콘솔 전용 로거 (INFO 레벨)")
    test_logger1 = get_logger("test_console")
    test_logger1.debug("디버그 메시지 - 출력 안 됨")
    test_logger1.info("인포 메시지")
    test_logger1.warning("경고 메시지")
    test_logger1.error("에러 메시지")
    test_logger1.critical("크리티컬 메시지")

    # 테스트 2: 콘솔 + 파일
    print("\n[테스트 2] 콘솔(INFO) + 파일(DEBUG)")
    test_logger2 = get_logger("test_both", console=True, file=True)
    test_logger2.debug("디버그 - 파일에만 기록")
    test_logger2.info("인포 - 콘솔 + 파일")
    test_logger2.warning("경고 - 콘솔 + 파일")
    print(f"로그 파일: ./logs/test_both.log")

    # 테스트 3: 로그 레벨 다르게 설정
    print("\n[테스트 3] 콘솔(WARNING) vs 파일(DEBUG)")
    test_logger3 = get_logger(
        "test_levels",
        console=True,
        console_level=logging.WARNING,
        file=True,
        file_level=logging.DEBUG,
    )
    test_logger3.debug("디버그 - 파일에만")
    test_logger3.info("인포 - 파일에만")
    test_logger3.warning("경고 - 콘솔 + 파일")
    test_logger3.error("에러 - 콘솔 + 파일")
    print(f"로그 파일: ./logs/test_levels.log")

    # 테스트 4: 커스텀 경로
    print("\n[테스트 4] 커스텀 로그 디렉토리")
    custom_dir = Path("./test_logs")
    test_logger4 = get_logger("test_custom", console=False, file=True, log_dir=custom_dir)
    test_logger4.info("커스텀 경로에 저장")
    print(f"로그 파일: {custom_dir}/test_custom.log")

    # 테스트 5: 중복 생성 방지 확인
    print("\n[테스트 5] 중복 생성 방지")
    logger_a = get_logger("duplicate_test")
    logger_b = get_logger("duplicate_test")
    print(f"같은 인스턴스: {logger_a is logger_b}")

    # 테스트 6: 환경변수 사용 (use_env=True)
    print("\n[테스트 6] 환경변수 설정 테스트")
    print(
        "환경변수 로드 가능 여부:", "가능" if _DOTENV_AVAILABLE else "불가능 (python-dotenv 미설치)"
    )
    test_logger6 = get_logger("test_env", use_env=True)
    test_logger6.debug("환경변수 기반 DEBUG")
    test_logger6.info("환경변수 기반 INFO")
    test_logger6.warning("환경변수 기반 WARNING")
    print("환경변수(.env) 설정이 적용됩니다 (LOG_LEVEL, CONSOLE_LOG_LEVEL 등)")

    # 테스트 7: 환경변수 무시 (use_env=False)
    print("\n[테스트 7] 환경변수 무시")
    test_logger7 = get_logger("test_no_env", use_env=False, console_level=logging.WARNING)
    test_logger7.info("INFO - 출력 안 됨")
    test_logger7.warning("WARNING - 출력됨")
    print("환경변수를 무시하고 함수 매개변수만 사용")

    # 테스트 8: get_auto_logger 환경변수
    print("\n[테스트 8] get_auto_logger 환경변수 자동 적용")
    auto_logger = get_auto_logger()
    auto_logger.info("자동 로거 - 환경변수 적용")
    print(f"자동 로거 이름: {auto_logger.name}")

    # 테스트 9: sample_logger_env 함수
    print("\n[테스트 9] sample_logger_env() - 샘플 파일 생성")
    try:
        env_file = sample_logger_env()
        print(f"✓ 생성 성공: {env_file}")
        print(f"  파일 크기: {env_file.stat().st_size} bytes")
    except Exception as e:
        print(f"✗ 생성 실패: {e}")

    # 테스트 10: logger.set() 메서드
    print("\n[테스트 10] logger.set() - 로거 재구성")
    test_logger10 = get_logger("test_set", console=True, console_level=logging.INFO)
    test_logger10.info("초기 설정: INFO 레벨")
    test_logger10.debug("DEBUG - 출력 안 됨")

    print("  → logger.set(console_level=logging.DEBUG) 호출")
    test_logger10.set(console_level=logging.DEBUG)
    test_logger10.debug("DEBUG - 재구성 후 출력됨")
    test_logger10.info("INFO - 여전히 출력됨")

    # 테스트 11: reconfigure_logger 함수
    print("\n[테스트 11] reconfigure_logger() - 독립 함수 방식")
    test_logger11 = get_logger("test_reconfig", console=True, file=False)
    test_logger11.info("초기 설정: 콘솔만")

    print("  → reconfigure_logger('test_reconfig', file=True) 호출")
    test_logger11 = reconfigure_logger(
        "test_reconfig", console=True, file=True, file_level=logging.DEBUG
    )
    test_logger11.info("재구성 후: 콘솔 + 파일")
    print(f"  로그 파일: ./logs/test_reconfig.log")

    # 테스트 12: 동일 인스턴스 확인
    print("\n[테스트 12] 재구성 후 동일 인스턴스 확인")
    logger_before = get_logger("test_instance")
    logger_after = logger_before.set(console_level=logging.WARNING)
    print(f"  동일 인스턴스: {logger_before is logger_after}")
    print(f"  logger_before.name: {logger_before.name}")
    print(f"  logger_after.name: {logger_after.name}")

    # 테스트 13: get_logger 중복 호출 - 핸들러 중복 확인
    print("\n[테스트 13] get_logger 중복 호출 - 핸들러 중복 확인")
    test_logger13_1 = get_logger("test_duplicate_handler")
    print(f"  첫 호출 후 핸들러 개수: {len(test_logger13_1.handlers)}")
    test_logger13_1.info("첫 번째 호출 - 로그 1회 출력 예상")

    test_logger13_2 = get_logger("test_duplicate_handler")
    print(f"  두 번째 호출 후 핸들러 개수: {len(test_logger13_2.handlers)}")
    print(f"  동일 인스턴스: {test_logger13_1 is test_logger13_2}")
    test_logger13_2.info("두 번째 호출 - 로그 1회 출력 예상 (중복 안 됨)")

    test_logger13_3 = get_logger("test_duplicate_handler")
    print(f"  세 번째 호출 후 핸들러 개수: {len(test_logger13_3.handlers)}")
    test_logger13_3.info("세 번째 호출 - 로그 1회 출력 예상 (중복 안 됨)")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
