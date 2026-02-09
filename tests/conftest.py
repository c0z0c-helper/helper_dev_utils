"""
conftest.py
===========
pytest 전역 설정 및 fixture

테스트 실행 전 .env.test 파일을 로드하여 환경변수를 설정합니다.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest


# 프로젝트 루트 및 src 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


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
