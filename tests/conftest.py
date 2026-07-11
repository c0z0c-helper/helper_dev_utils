"""
conftest.py
===========
pytest 전역 설정 및 fixture

테스트 실행 전 .env.test 파일을 로드하여 환경변수를 설정합니다.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


# 프로젝트 루트 및 src 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

_test_reports: list = []


def pytest_runtest_logreport(report: pytest.TestReport):
    """각 테스트의 최종 결과(setup 실패/스킵 또는 call)만 수집한다."""
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        _test_reports.append(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    """세션 종료 시 tests/report/년월일_시분초.md 로 결과 테이블을 기록한다."""
    if not _test_reports:
        return

    report_dir = Path(__file__).parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    report_file = report_dir / f"{now.strftime('%Y%m%d_%H%M%S')}.md"

    status_map = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}
    status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}

    passed = sum(1 for r in _test_reports if r.outcome == "passed")
    failed = sum(1 for r in _test_reports if r.outcome == "failed")
    skipped = sum(1 for r in _test_reports if r.outcome == "skipped")
    total = len(_test_reports)

    lines = [
        "# pytest 테스트 결과 리포트\n\n",
        f"**생성 시각**: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"**총 테스트 수**: {total}\n",
        f"**성공**: {passed}\n",
        f"**실패**: {failed}\n",
        f"**스킵**: {skipped}\n\n",
        "---\n\n",
        "## 테스트 결과 상세\n\n",
        "| 번호 | 테스트 | 결과 | 소요시간(s) |\n",
        "|------|--------|------|------------|\n",
    ]

    for i, report in enumerate(_test_reports, 1):
        status = status_map.get(report.outcome, report.outcome.upper())
        emoji = status_emoji.get(status, "❓")
        lines.append(f"| {i} | `{report.nodeid}` | {emoji} {status} | {report.duration:.3f} |\n")

    lines.append("\n---\n\n")
    lines.append("✅ **모든 테스트 통과!**\n" if failed == 0 else f"❌ **{failed}개 테스트 실패**\n")

    report_file.write_text("".join(lines), encoding="utf-8")
    print(f"\n[conftest] 테스트 리포트 생성: {report_file}")


@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """
    테스트 실행 전 .env.test 파일을 .env로 복사하여 환경변수 설정

    helper_utils_colab 모듈이 os.getcwd()/.env 파일을 읽으므로,
    .env.test를 프로젝트 루트의 .env로 복사합니다.

    Notes
    -----
    - autouse=True로 모든 테스트에 자동 적용
    - scope='session'으로 테스트 세션당 1회만 실행
    - 기존 .env 파일이 있으면 .env.backup으로 백업
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        pytest.skip("python-dotenv not available")
        return

    # .env.test 파일 경로 탐색
    test_dir = Path(__file__).parent
    project_root = test_dir.parent

    env_test_paths = [
        test_dir / ".env.test",  # tests/.env.test
        project_root / ".env.test",  # .env.test
    ]

    env_test_path = None
    for env_path in env_test_paths:
        if env_path.exists():
            env_test_path = env_path
            break

    if not env_test_path:
        # .env.test 파일이 없으면 임시 디렉토리 사용
        temp_cache = Path(tempfile.gettempdir()) / "helper_dev_utils_test_cache"
        temp_driver = Path(tempfile.gettempdir()) / "helper_dev_utils_test_driver"

        temp_cache.mkdir(exist_ok=True)
        temp_driver.mkdir(exist_ok=True)

        os.environ["MY_CACHE_LOCAL"] = str(temp_cache)
        os.environ["MY_DRIVER_PATH"] = str(temp_driver)

        print(f"\n[conftest] No .env.test found, using temp dirs:")
        print(f"  MY_CACHE_LOCAL={temp_cache}")
        print(f"  MY_DRIVER_PATH={temp_driver}")

        yield
        return

    # .env 파일 백업 및 .env.test 복사
    env_path = project_root / ".env"
    env_backup_path = project_root / ".env.backup"

    backup_created = False
    if env_path.exists():
        # 기존 .env 파일 백업
        import shutil

        shutil.copy2(env_path, env_backup_path)
        backup_created = True
        print(f"[conftest] Backed up existing .env to .env.backup")

    # .env.test를 .env로 복사
    import shutil

    shutil.copy2(env_test_path, env_path)
    print(f"[conftest] Copied {env_test_path} to {env_path}")

    # 환경변수 로드
    load_dotenv(env_path, override=True)
    print(f"[conftest] Loaded test environment from .env.test")
    print(f"  MY_CACHE_LOCAL={os.getenv('MY_CACHE_LOCAL')}")
    print(f"  MY_DRIVER_PATH={os.getenv('MY_DRIVER_PATH')}")

    yield

    # 테스트 종료 후 원상복구
    if backup_created and env_backup_path.exists():
        shutil.copy2(env_backup_path, env_path)
        env_backup_path.unlink()
        print("[conftest] Restored original .env from backup")
    elif not backup_created and env_path.exists():
        env_path.unlink()
        print("[conftest] Removed test .env file")
