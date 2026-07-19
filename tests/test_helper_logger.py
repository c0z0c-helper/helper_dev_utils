"""
helper_logger 모듈 pytest 테스트

모든 공개 인터페이스에 대한 테스트를 포함합니다.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# 테스트 대상 모듈
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import helper_dev_utils.helper_logger as helper_logger
from helper_dev_utils.helper_logger import (
    get_logger,
    LogFormatter,
)


@pytest.fixture
def temp_dir(tmp_path):
    """임시 디렉토리 픽스처"""
    return tmp_path


@pytest.fixture(autouse=True)
def clear_logger_cache():
    """각 테스트 전후 로거 상태 및 로그 파일 캐시 초기화"""
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        if hasattr(logger, "handlers"):
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
    logging.Logger.manager.loggerDict.clear()
    helper_logger._log_file_path = None

    yield

    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        if hasattr(logger, "handlers"):
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
    logging.Logger.manager.loggerDict.clear()
    helper_logger._log_file_path = None


def _find_log_file(log_dir: Path) -> Path:
    files = list(log_dir.rglob("*.log"))
    assert len(files) == 1, f"기대한 로그 파일 개수는 1개, 실제: {files}"
    return files[0]


class TestLogFormatter:
    """LogFormatter 클래스 테스트"""

    def test_default_timezone_is_seoul(self):
        formatter = LogFormatter()
        assert formatter.tz == ZoneInfo("Asia/Seoul")

    def test_custom_timezone_string(self):
        formatter = LogFormatter(tz="UTC")
        assert formatter.tz == ZoneInfo("UTC")

    def test_level_abbreviation_via_fmt(self):
        formatter = LogFormatter(fmt="%(levelname).1s - %(message)s")

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

    def test_format_time_uses_configured_timezone(self):
        formatter = LogFormatter(tz="UTC", datefmt="%Y-%m-%d %H:%M:%S")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.created = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()

        formatted_time = formatter.formatTime(record, "%Y-%m-%d %H:%M:%S")
        assert formatted_time == "2026-01-01 12:00:00"


class TestGetLogger:
    """get_logger 함수 테스트"""

    def test_basic_logger_creation(self):
        logger = get_logger("test_basic")

        assert logger is not None
        assert logger.name == "test_basic"
        assert len(logger.handlers) == 1  # 콘솔 핸들러만
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_name_and_message_separated_without_location(self, capsys):
        logger = get_logger("test_name_sep", enable_file=False, enable_line=False)
        logger.info("hello")
        captured = capsys.readouterr()
        assert "test_name_sep - hello" in captured.err

    def test_file_disabled_by_default(self):
        logger = get_logger("test_file_default")
        assert len(logger.handlers) == 1
        assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_default_level_is_info(self):
        logger = get_logger("test_default_level")
        assert logger.level == logging.INFO

    def test_custom_level(self):
        logger = get_logger("test_custom_level", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_no_duplicate_handlers_on_repeated_calls(self):
        get_logger("test_dup")
        logger = get_logger("test_dup")
        logger = get_logger("test_dup")

        assert len(logger.handlers) == 1

    def test_propagate_is_false(self):
        logger = get_logger("test_propagate")
        assert logger.propagate is False

    def test_file_logging(self, temp_dir):
        logger = get_logger("test_file", enable_file_write=True, log_dir=temp_dir)

        assert len(logger.handlers) == 2  # 콘솔 + 파일
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

        logger.info("Test message")
        for handler in logger.handlers:
            handler.flush()

        log_file = _find_log_file(temp_dir)
        assert "Test message" in log_file.read_text(encoding="utf-8")

    def test_file_logging_path_layout(self, temp_dir):
        logger = get_logger("test_file_layout", enable_file_write=True, log_dir=temp_dir)
        log_file = _find_log_file(temp_dir)

        # {log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log
        relative_parts = log_file.relative_to(temp_dir).parts
        assert len(relative_parts) == 4
        year, month, day, filename = relative_parts
        assert len(year) == 4 and year.isdigit()
        assert len(month) == 2 and month.isdigit()
        assert len(day) == 2 and day.isdigit()
        assert filename.startswith(f"{year}{month}{day}_")
        assert filename.endswith(".log")

    def test_file_logging_shared_across_loggers(self, temp_dir):
        logger1 = get_logger("test_shared1", enable_file_write=True, log_dir=temp_dir)
        logger2 = get_logger("test_shared2", enable_file_write=True, log_dir=temp_dir)

        logger1.info("From logger1")
        logger2.info("From logger2")
        for handler in list(logger1.handlers) + list(logger2.handlers):
            handler.flush()

        log_file = _find_log_file(temp_dir)  # 파일이 하나만 생성되어야 함
        content = log_file.read_text(encoding="utf-8")
        assert "From logger1" in content
        assert "From logger2" in content

    def test_custom_timezone(self):
        logger = get_logger("test_tz", tz="UTC")
        formatter = logger.handlers[0].formatter
        assert isinstance(formatter, LogFormatter)
        assert formatter.tz == ZoneInfo("UTC")

    def test_enable_file_shows_caller_filename(self, capsys):
        logger = get_logger("test_enable_file", enable_file=True)
        logger.info("hello")
        captured = capsys.readouterr()
        assert "test_helper_logger.py" in captured.err
        assert "hello" in captured.err

    def test_enable_line_shows_caller_lineno(self, capsys):
        logger = get_logger("test_enable_line", enable_line=True)
        logger.info("hello")
        captured = capsys.readouterr()
        assert "(:" in captured.err
        assert "hello" in captured.err

    def test_enable_file_and_line_together(self, capsys):
        logger = get_logger("test_enable_both", enable_file=True, enable_line=True)
        logger.info("hello")
        captured = capsys.readouterr()
        assert "test_helper_logger.py:" in captured.err

    def test_enable_file_line_enabled_by_default(self, capsys):
        logger = get_logger("test_enable_default")
        logger.info("hello")
        captured = capsys.readouterr()
        assert "test_helper_logger.py:" in captured.err

    def test_empty_name_omits_name_from_output(self, capsys):
        logger = get_logger(name="")
        logger.info("hello")
        captured = capsys.readouterr()
        assert "root" not in captured.err
        assert "hello" in captured.err


class TestGetLoggerOmittedName:
    """name 생략 시 빈 이름(anonymous) 로거를 사용하는 동작 테스트"""

    def test_omitted_name_is_empty(self, capsys):
        logger = get_logger()
        logger.info("hello")
        captured = capsys.readouterr()

        assert logger is not None
        assert logger.name == "root"  # logging.getLogger("")는 root 로거를 반환한다
        assert "root" not in captured.err
        assert "hello" in captured.err

    def test_omitted_name_with_kwargs(self, temp_dir):
        logger = get_logger(enable_file_write=True, log_dir=temp_dir)

        assert len(logger.handlers) == 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)


class TestGetLoggerEnv:
    """환경 변수 기반 설정 테스트"""

    def test_logger_name_from_env(self, monkeypatch):
        monkeypatch.setenv("LOGGER_NAME", "env_named")
        logger = get_logger()
        assert logger.name == "env_named"

    def test_logger_level_from_env(self, monkeypatch):
        monkeypatch.setenv("LOGGER_LEVEL", "DEBUG")
        logger = get_logger("test_env_level")
        assert logger.level == logging.DEBUG

    def test_logger_tz_from_env(self, monkeypatch):
        monkeypatch.setenv("LOGGER_TZ", "UTC")
        logger = get_logger("test_env_tz")
        formatter = logger.handlers[0].formatter
        assert formatter.tz == ZoneInfo("UTC")

    def test_logger_enable_line_from_env(self, monkeypatch, capsys):
        monkeypatch.setenv("LOGGER_ENABLE_LINE", "true")
        logger = get_logger("test_env_enable_line")
        logger.info("hello")
        captured = capsys.readouterr()
        assert "(:" in captured.err

    def test_logger_enable_file_from_env_false(self, monkeypatch, capsys):
        monkeypatch.setenv("LOGGER_ENABLE_FILE", "false")
        logger = get_logger("test_env_disable_file")
        logger.info("hello")
        captured = capsys.readouterr()
        assert "test_helper_logger.py" not in captured.err

    def test_logger_enable_line_from_env_false(self, monkeypatch, capsys):
        monkeypatch.setenv("LOGGER_ENABLE_LINE", "false")
        logger = get_logger("test_env_disable_line")
        logger.info("hello")
        captured = capsys.readouterr()
        assert "(:" not in captured.err

    def test_explicit_kwarg_overrides_env(self, monkeypatch):
        monkeypatch.setenv("LOGGER_NAME", "env_named")
        logger = get_logger("explicit_named")
        assert logger.name == "explicit_named"

    def test_explicit_level_overrides_env(self, monkeypatch):
        monkeypatch.setenv("LOGGER_LEVEL", "DEBUG")
        logger = get_logger("test_env_level_override", level=logging.WARNING)
        assert logger.level == logging.WARNING


class TestIntegration:
    """통합 테스트"""

    def test_logger_level_filtering(self, temp_dir):
        logger = get_logger("test_filter", level=logging.WARNING, enable_file_write=True, log_dir=temp_dir)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        for handler in logger.handlers:
            handler.flush()

        log_file = _find_log_file(temp_dir)
        content = log_file.read_text(encoding="utf-8")
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_reconfiguring_logger_does_not_duplicate_output(self, temp_dir, capsys):
        get_logger("test_reconf", enable_file_write=True, log_dir=temp_dir)
        logger = get_logger("test_reconf", enable_file_write=True, log_dir=temp_dir)

        logger.warning("Single line")
        for handler in logger.handlers:
            handler.flush()

        captured = capsys.readouterr()
        assert captured.err.count("Single line") == 1

        log_file = _find_log_file(temp_dir)
        content = log_file.read_text(encoding="utf-8")
        assert content.count("Single line") == 1
