"""
test_helper_utils_colab.py
============================
helper_utils_colab 모듈의 pytest 테스트 스위트

테스트 범위:
- my_driver(): Google Drive 경로 가져오기
- my_driver_path(): 하위 경로 포함 Google Drive 경로
- my_cache(): 캐시 디렉토리 경로 가져오기
- my_cache_path(): 하위 경로 포함 캐시 경로
- 환경변수 기반 경로 설정
- OS별 자동 탐색
"""

import os
import sys
import tempfile
import platform
from pathlib import Path

import pytest

# 프로젝트 루트에서 src 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from helper_dev_utils import my_driver, my_driver_path, my_cache, my_cache_path


# =============================================================================
# 픽스처
# =============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """환경변수 초기화"""
    monkeypatch.delenv("MY_DRIVER_PATH", raising=False)
    monkeypatch.delenv("MY_CACHE_PATH", raising=False)
    yield


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_driver_dir():
    """임시 드라이버 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# 테스트 클래스 1: my_cache
# =============================================================================


class TestMyCache:
    """my_cache() 함수 테스트"""

    def test_my_cache_basic(self, clean_env):
        """기본 캐시 경로 가져오기"""
        cache_path = my_cache()
        assert cache_path is not None
        assert isinstance(cache_path, str)
        assert len(cache_path) > 0

    def test_my_cache_with_env(self, monkeypatch, temp_cache_dir):
        """함수 인자로 캐시 경로 설정 테스트"""
        # my_cache_local 인자로 직접 전달
        cache_path = my_cache(my_cache_local=temp_cache_dir)
        assert temp_cache_dir in cache_path or cache_path == temp_cache_dir

    def test_my_cache_returns_valid_path(self, clean_env):
        """유효한 경로 반환 확인"""
        cache_path = my_cache()
        # 경로가 존재하거나 생성 가능해야 함
        path_obj = Path(cache_path)
        # 부모 디렉토리는 최소한 존재해야 함
        assert path_obj.parent.exists() or path_obj.exists()

    def test_my_cache_consistent(self, clean_env):
        """일관된 경로 반환 확인"""
        cache_path1 = my_cache()
        cache_path2 = my_cache()
        assert cache_path1 == cache_path2


# =============================================================================
# 테스트 클래스 2: my_cache_path
# =============================================================================


class TestMyCachePath:
    """my_cache_path() 함수 테스트"""

    def test_my_cache_path_basic(self, clean_env):
        """기본 캐시 경로 가져오기"""
        cache_path = my_cache_path()
        assert cache_path is not None
        assert isinstance(cache_path, str)

    def test_my_cache_path_with_subpath(self, clean_env):
        """하위 경로 포함"""
        subpath = "models/bert"
        cache_path = my_cache_path(subpath)
        assert subpath in cache_path or "models" in cache_path

    def test_my_cache_path_empty_string(self, clean_env):
        """빈 문자열 전달"""
        cache_path = my_cache_path("")
        base_cache = my_cache()
        assert cache_path == base_cache

    def test_my_cache_path_none(self, clean_env):
        """None 전달"""
        cache_path = my_cache_path(None)
        base_cache = my_cache()
        assert cache_path == base_cache

    def test_my_cache_path_multiple_levels(self, clean_env):
        """다중 레벨 하위 경로"""
        subpath = "data/images/train/labels"
        cache_path = my_cache_path(subpath)
        assert "data" in cache_path or cache_path.endswith(subpath)


# =============================================================================
# 테스트 클래스 3: my_driver
# =============================================================================


class TestMyDriver:
    """my_driver() 함수 테스트"""

    def test_my_driver_basic(self, clean_env):
        """기본 드라이버 경로 가져오기"""
        driver_path = my_driver()
        assert driver_path is not None
        assert isinstance(driver_path, str)
        assert len(driver_path) > 0

    def test_my_driver_with_env(self, monkeypatch, temp_driver_dir):
        """함수 인자로 드라이버 경로 설정 테스트"""
        # my_driver_local 인자로 직접 전달
        driver_path = my_driver(my_driver_local=temp_driver_dir)
        assert temp_driver_dir in driver_path or driver_path == temp_driver_dir

    def test_my_driver_returns_valid_path(self, clean_env):
        """유효한 경로 반환 확인"""
        driver_path = my_driver()
        # 경로가 존재하거나 생성 가능해야 함
        path_obj = Path(driver_path)
        assert path_obj.parent.exists() or path_obj.exists()

    def test_my_driver_consistent(self, clean_env):
        """일관된 경로 반환 확인"""
        driver_path1 = my_driver()
        driver_path2 = my_driver()
        assert driver_path1 == driver_path2


# =============================================================================
# 테스트 클래스 4: my_driver_path
# =============================================================================


class TestMyDriverPath:
    """my_driver_path() 함수 테스트"""

    def test_my_driver_path_basic(self, clean_env):
        """기본 드라이버 경로 가져오기"""
        driver_path = my_driver_path()
        assert driver_path is not None
        assert isinstance(driver_path, str)

    def test_my_driver_path_with_subpath(self, clean_env):
        """하위 경로 포함"""
        subpath = "datasets/images"
        driver_path = my_driver_path(subpath)
        assert subpath in driver_path or "datasets" in driver_path

    def test_my_driver_path_empty_string(self, clean_env):
        """빈 문자열 전달"""
        driver_path = my_driver_path("")
        base_driver = my_driver()
        assert driver_path == base_driver

    def test_my_driver_path_none(self, clean_env):
        """None 전달"""
        driver_path = my_driver_path(None)
        base_driver = my_driver()
        assert driver_path == base_driver

    def test_my_driver_path_multiple_levels(self, clean_env):
        """다중 레벨 하위 경로"""
        subpath = "projects/ml/data/raw"
        driver_path = my_driver_path(subpath)
        assert "projects" in driver_path or driver_path.endswith(subpath)


# =============================================================================
# 테스트 클래스 5: 환경변수 우선순위
# =============================================================================


class TestEnvironmentPriority:
    """환경변수 우선순위 테스트"""

    def test_cache_env_priority(self, monkeypatch, temp_cache_dir):
        """캐시 경로 함수 인자 우선순위 테스트"""
        # 함수 인자로 직접 전달하면 전역 변수 업데이트
        test_cache = temp_cache_dir
        cache_path = my_cache(my_cache_local=test_cache)
        assert test_cache in cache_path or cache_path == test_cache

    def test_driver_env_priority(self, monkeypatch, temp_driver_dir):
        """드라이버 경로 함수 인자 우선순위 테스트"""
        # 함수 인자로 직접 전달하면 전역 변수 업데이트
        test_driver = temp_driver_dir
        driver_path = my_driver(my_driver_local=test_driver)
        assert test_driver in driver_path or driver_path == test_driver

    def test_both_env_set(self, monkeypatch, temp_cache_dir, temp_driver_dir):
        """캐시와 드라이버 모두 함수 인자로 설정 테스트"""
        # 두 함수 모두 인자로 전달
        cache_path = my_cache(my_cache_local=temp_cache_dir)
        driver_path = my_driver(my_driver_local=temp_driver_dir)

        assert temp_cache_dir in cache_path or cache_path == temp_cache_dir
        assert temp_driver_dir in driver_path or driver_path == temp_driver_dir


# =============================================================================
# 테스트 클래스 6: OS별 경로 탐색
# =============================================================================


class TestOSSpecificPaths:
    """OS별 경로 탐색 테스트"""

    def test_cache_path_format(self, clean_env):
        """캐시 경로 형식 검증"""
        cache_path = my_cache()
        # 절대 경로여야 함
        assert os.path.isabs(cache_path)

    def test_driver_path_format(self, clean_env):
        """드라이버 경로 형식 검증"""
        driver_path = my_driver()
        # 절대 경로여야 함
        assert os.path.isabs(driver_path)

    def test_platform_detection(self, clean_env):
        """플랫폼 감지 테스트"""
        system = platform.system()
        cache_path = my_cache()

        # OS별로 적절한 경로 반환 확인
        if system == "Windows":
            # Windows: AppData 또는 temp
            assert "AppData" in cache_path or "Temp" in cache_path or "temp" in cache_path.lower()
        elif system in ["Linux", "Darwin"]:
            # Linux/Mac: home 디렉토리 또는 /tmp
            assert os.path.expanduser("~") in cache_path or "/tmp" in cache_path


# =============================================================================
# 테스트 클래스 7: 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_all_functions_work(self, clean_env):
        """모든 함수 정상 작동 확인"""
        # 기본 경로
        cache = my_cache()
        driver = my_driver()
        assert cache is not None
        assert driver is not None

        # 하위 경로
        cache_sub = my_cache_path("test")
        driver_sub = my_driver_path("test")
        assert "test" in cache_sub
        assert "test" in driver_sub

    def test_path_consistency(self, clean_env):
        """경로 일관성 검증"""
        cache1 = my_cache()
        cache2 = my_cache_path()
        assert cache1 == cache2

        driver1 = my_driver()
        driver2 = my_driver_path()
        assert driver1 == driver2

    def test_subpath_composition(self, clean_env):
        """하위 경로 조합 테스트"""
        base_cache = my_cache()
        sub_cache = my_cache_path("models/bert")

        # 하위 경로가 기본 경로를 포함해야 함
        assert base_cache in sub_cache or sub_cache.startswith(base_cache)


# =============================================================================
# 테스트 클래스 8: 엣지 케이스
# =============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_special_characters_in_subpath(self, clean_env):
        """특수 문자 포함 하위 경로"""
        subpath = "data_2024/test-files"
        cache_path = my_cache_path(subpath)
        # 정상적으로 경로 생성되어야 함
        assert cache_path is not None

    def test_unicode_in_subpath(self, clean_env):
        """유니코드 포함 하위 경로"""
        subpath = "데이터/한글폴더"
        cache_path = my_cache_path(subpath)
        # 정상적으로 경로 생성되어야 함
        assert cache_path is not None

    def test_absolute_path_as_subpath(self, clean_env, temp_cache_dir):
        """절대 경로를 하위 경로로 전달"""
        # 일부 구현에서는 절대 경로를 그대로 사용할 수 있음
        result = my_cache_path(temp_cache_dir)
        assert result is not None

    def test_relative_path_navigation(self, clean_env):
        """상대 경로 탐색 문자 포함 - 보안 검증으로 에러 발생 예상"""
        subpath = "../parent/child"
        # 구현이 경로 escape를 방지하므로 예외 발생 가능
        with pytest.raises(ValueError):
            my_cache_path(subpath)


# =============================================================================
# 테스트 클래스 9: 타입 검증
# =============================================================================


class TestTypeValidation:
    """타입 검증 테스트"""

    def test_return_types(self, clean_env):
        """반환 타입 검증"""
        assert isinstance(my_cache(), str)
        assert isinstance(my_driver(), str)
        assert isinstance(my_cache_path(), str)
        assert isinstance(my_driver_path(), str)

    def test_subpath_types(self, clean_env):
        """하위 경로 타입 검증"""
        # 문자열
        result1 = my_cache_path("test")
        assert isinstance(result1, str)

        # None
        result2 = my_cache_path(None)
        assert isinstance(result2, str)

        # 빈 문자열
        result3 = my_cache_path("")
        assert isinstance(result3, str)
