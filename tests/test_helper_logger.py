"""
helper_logger 모듈 pytest 테스트

모든 공개 인터페이스에 대한 테스트를 포함합니다.
"""

import logging
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 테스트 대상 모듈
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from helper_dev_utils.helper_logger import (
    get_logger,
    get_auto_logger,
    reconfigure_logger,
    sample_logger_env,
    ShortLevelFormatter,
    TimestampRotatingFileHandler,
    _get_process_start_time,
    _clear_handlers,
    _load_env_config,
    _loggers,
)


@pytest.fixture
def temp_dir():
    """임시 디렉토리 픽스처"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def clear_logger_cache():
    """각 테스트 후 로거 캐시 초기화"""
    yield
    _loggers.clear()
    # logging 모듈의 로거 매니저도 초기화
    logging.Logger.manager.loggerDict.clear()


class TestShortLevelFormatter:
    """ShortLevelFormatter 클래스 테스트"""

    def test_format_level_mapping(self):
        """로그 레벨 축약 매핑 테스트"""
        formatter = ShortLevelFormatter()

        assert formatter.LEVEL_MAP["DEBUG"] == "D"
        assert formatter.LEVEL_MAP["INFO"] == "I"
        assert formatter.LEVEL_MAP["WARNING"] == "W"
        assert formatter.LEVEL_MAP["ERROR"] == "E"
        assert formatter.LEVEL_MAP["CRITICAL"] == "C"

    def test_format_record(self):
        """로그 레코드 포맷 테스트"""
        formatter = ShortLevelFormatter(fmt="%(levelname)s - %(message)s")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert formatted.startswith("I -")
        assert "test message" in formatted


class TestTimestampRotatingFileHandler:
    """TimestampRotatingFileHandler 클래스 테스트"""

    def test_handler_initialization(self, temp_dir):
        """핸들러 초기화 테스트"""
        log_file = temp_dir / "test.log"
        handler = TimestampRotatingFileHandler(
            filename=log_file,
            log_file_basename="test",
            maxBytes=1024,
            encoding="utf-8",
        )

        assert handler.log_file_basename == "test"
        assert handler.log_dir == temp_dir
        assert handler.maxBytes == 1024

        handler.close()

    def test_rollover_auto_time(self, temp_dir):
        """auto_time 모드 롤오버 테스트"""
        log_file = temp_dir / "20260208_143052.log"
        handler = TimestampRotatingFileHandler(
            filename=log_file,
            log_file_basename="auto_time",
            maxBytes=100,
            encoding="utf-8",
        )

        # 롤오버 시뮬레이션
        handler.doRollover()

        # 새 파일명이 타임스탬프 형식인지 확인
        new_filename = Path(handler.baseFilename).name
        assert new_filename.endswith(".log")
        assert len(new_filename.split("_")) == 2  # YYYYMMDD_HHMMSS.log

        handler.close()

    def test_rollover_custom_basename(self, temp_dir):
        """커스텀 basename 롤오버 테스트"""
        log_file = temp_dir / "app.log"
        handler = TimestampRotatingFileHandler(
            filename=log_file,
            log_file_basename="app",
            maxBytes=100,
            encoding="utf-8",
        )

        # 롤오버 시뮬레이션
        handler.doRollover()

        # 새 파일명이 app_YYYYMMDD_HHMMSS.log 형식인지 확인
        new_filename = Path(handler.baseFilename).name
        assert new_filename.startswith("app_")
        assert new_filename.endswith(".log")

        handler.close()


class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_get_process_start_time(self):
        """프로세스 시작 시간 반환 테스트"""
        timestamp = _get_process_start_time()

        assert isinstance(timestamp, str)
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
        assert "_" in timestamp

    def test_clear_handlers(self):
        """핸들러 제거 테스트"""
        logger = logging.getLogger("test_clear")
        handler = logging.StreamHandler()
        logger.addHandler(handler)

        assert len(logger.handlers) == 1

        _clear_handlers(logger)

        assert len(logger.handlers) == 0

    def test_load_env_config_no_env(self):
        """환경변수 없을 때 기본값 반환 테스트"""
        config = _load_env_config(use_env=False)

        assert config["console_level"] is None
        assert config["file_level"] is None
        assert config["log_dir"] is None
        assert config["file"] is None
        assert config["use_central_file"] is None
        assert config["log_file_basename"] is None
        assert config["max_log_file_size"] is None


class TestGetLogger:
    """get_logger 함수 테스트"""

    def test_basic_logger_creation(self):
        """기본 로거 생성 테스트"""
        logger = get_logger("test_basic")

        assert logger is not None
        assert logger.name == "test_basic"
        assert len(logger.handlers) == 1  # 콘솔 핸들러만

    def test_logger_caching(self):
        """로거 캐싱 테스트"""
        logger1 = get_logger("test_cache")
        logger2 = get_logger("test_cache")

        assert logger1 is logger2

    def test_console_only_logger(self):
        """콘솔 전용 로거 테스트"""
        logger = get_logger("test_console", console=True, file=False)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_file_logger(self, temp_dir):
        """파일 로거 테스트"""
        logger = get_logger(
            "test_file",
            console=False,
            file=True,
            log_dir=temp_dir,
            use_central_file=False,
        )

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], TimestampRotatingFileHandler)

        # 로그 파일 생성 확인
        logger.info("Test message")
        log_file = temp_dir / "test_file.log"
        assert log_file.exists()

    def test_central_file_auto_time(self, temp_dir):
        """중앙 집중 로깅 (auto_time) 테스트"""
        logger1 = get_logger(
            "module1",
            file=True,
            log_dir=temp_dir,
            use_central_file=True,
            log_file_basename="auto_time",
            console=False,
        )
        logger2 = get_logger(
            "module2",
            file=True,
            log_dir=temp_dir,
            use_central_file=True,
            log_file_basename="auto_time",
            console=False,
        )

        logger1.info("Module1 message")
        logger2.info("Module2 message")

        # 같은 파일에 기록되는지 확인
        timestamp = _get_process_start_time()
        log_file = temp_dir / f"{timestamp}.log"
        assert log_file.exists()

        content = log_file.read_text(encoding="utf-8")
        assert "Module1 message" in content
        assert "Module2 message" in content

    def test_central_file_custom_basename(self, temp_dir):
        """중앙 집중 로깅 (커스텀 basename) 테스트"""
        logger1 = get_logger(
            "module3",
            file=True,
            log_dir=temp_dir,
            use_central_file=True,
            log_file_basename="app",
            console=False,
        )
        logger2 = get_logger(
            "module4",
            file=True,
            log_dir=temp_dir,
            use_central_file=True,
            log_file_basename="app",
            console=False,
        )

        logger1.info("Module3 message")
        logger2.info("Module4 message")

        log_file = temp_dir / "app.log"
        assert log_file.exists()

        content = log_file.read_text(encoding="utf-8")
        assert "Module3 message" in content
        assert "Module4 message" in content

    def test_module_separate_logging(self, temp_dir):
        """모듈별 분리 로깅 테스트"""
        logger1 = get_logger(
            "module5",
            file=True,
            log_dir=temp_dir,
            use_central_file=False,
            console=False,
        )
        logger2 = get_logger(
            "module6",
            file=True,
            log_dir=temp_dir,
            use_central_file=False,
            console=False,
        )

        logger1.info("Module5 message")
        logger2.info("Module6 message")

        log_file1 = temp_dir / "module5.log"
        log_file2 = temp_dir / "module6.log"

        assert log_file1.exists()
        assert log_file2.exists()

        assert "Module5 message" in log_file1.read_text(encoding="utf-8")
        assert "Module6 message" in log_file2.read_text(encoding="utf-8")

    def test_log_levels(self):
        """로그 레벨 설정 테스트"""
        logger = get_logger(
            "test_levels",
            console=True,
            console_level=logging.WARNING,
        )

        assert logger.handlers[0].level == logging.WARNING

    def test_max_log_file_size_unlimited(self, temp_dir):
        """무제한 로그 파일 크기 테스트"""
        logger = get_logger(
            "test_unlimited",
            file=True,
            log_dir=temp_dir,
            max_log_file_size=0,
            use_central_file=False,
            console=False,
        )

        handler = logger.handlers[0]
        assert handler.maxBytes == 0


class TestReconfigureLogger:
    """reconfigure_logger 함수 테스트"""

    def test_reconfigure_logger(self):
        """로거 재구성 테스트"""
        logger = get_logger("test_reconfig", console=True, file=False)
        initial_handler_count = len(logger.handlers)

        logger = reconfigure_logger("test_reconfig", console=True, file=False)

        assert len(logger.handlers) == initial_handler_count

    def test_reconfigure_logger_change_settings(self, temp_dir):
        """설정 변경 재구성 테스트"""
        logger = get_logger("test_reconfig2", console=True, file=False)
        assert len(logger.handlers) == 1

        logger = reconfigure_logger(
            "test_reconfig2",
            console=False,
            file=True,
            log_dir=temp_dir,
            use_central_file=False,
        )

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], TimestampRotatingFileHandler)


class TestGetAutoLogger:
    """get_auto_logger 함수 테스트"""

    def test_auto_logger_creation(self):
        """자동 로거 생성 테스트"""
        logger = get_auto_logger()

        assert logger is not None
        # 테스트 파일명 기반 로거 이름
        assert (
            "test_helper_logger" in logger.name
            or "pytest" in logger.name
            or "__main__" in logger.name
        )

    def test_auto_logger_with_kwargs(self, temp_dir):
        """kwargs 전달 테스트"""
        logger = get_auto_logger(
            file=True,
            log_dir=temp_dir,
            use_central_file=False,
            console=False,
        )

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], TimestampRotatingFileHandler)


class TestSampleLoggerEnv:
    """sample_logger_env 함수 테스트"""

    def test_sample_env_file_creation(self, temp_dir):
        """샘플 파일 생성 테스트"""
        env_file = sample_logger_env(output_dir=temp_dir)

        assert env_file.exists()
        assert env_file.name == ".env.example_logger"

        content = env_file.read_text(encoding="utf-8")
        assert "LOG_LEVEL" in content
        assert "LOG_USE_CENTRAL_FILE" in content
        assert "LOG_FILE_BASENAME" in content
        assert "MAX_LOG_FILE_SIZE" in content

    def test_sample_env_file_default_dir(self):
        """기본 디렉토리 생성 테스트"""
        env_file = sample_logger_env()

        assert env_file.exists()
        assert env_file.parent == Path.cwd()

        # 테스트 후 정리
        env_file.unlink(missing_ok=True)


class TestLoggerSetMethod:
    """logger.set() 메서드 테스트"""

    def test_set_method_exists(self):
        """set 메서드 존재 확인"""
        logger = get_logger("test_set_method")

        assert hasattr(logger, "set")
        assert callable(logger.set)

    def test_set_method_reconfiguration(self, temp_dir):
        """set 메서드로 재구성 테스트"""
        logger = get_logger("test_set_method2", console=True, file=False)
        initial_handlers = len(logger.handlers)

        logger.set(console=False, file=True, log_dir=temp_dir, use_central_file=False)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], TimestampRotatingFileHandler)

    def test_set_method_returns_self(self):
        """set 메서드가 self 반환하는지 테스트"""
        logger = get_logger("test_set_method3")
        result = logger.set(console=True)

        assert result is logger


class TestIntegration:
    """통합 테스트"""

    def test_multiple_loggers_same_file(self, temp_dir):
        """여러 로거가 같은 파일에 로깅"""
        loggers = [
            get_logger(
                f"module{i}",
                file=True,
                log_dir=temp_dir,
                use_central_file=True,
                log_file_basename="integration",
                console=False,
            )
            for i in range(5)
        ]

        for i, logger in enumerate(loggers):
            logger.info(f"Message from module {i}")

        log_file = temp_dir / "integration.log"
        assert log_file.exists()

        content = log_file.read_text(encoding="utf-8")
        for i in range(5):
            assert f"Message from module {i}" in content

    def test_logger_level_filtering(self, temp_dir):
        """로그 레벨 필터링 테스트"""
        logger = get_logger(
            "test_filter",
            file=True,
            log_dir=temp_dir,
            console=False,
            file_level=logging.WARNING,
            use_central_file=False,
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        log_file = temp_dir / "test_filter.log"
        content = log_file.read_text(encoding="utf-8")

        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content
        assert "Error message" in content
