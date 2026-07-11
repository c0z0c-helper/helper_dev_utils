"""
test_helper_utils_colab.py
============================
helper_utils_colab 모듈의 pytest 테스트 스위트

테스트 범위:
- google_driver(): Google Drive 경로 가져오기
- google_driver_path(): 하위 경로 포함 Google Drive 경로
- cache(): 캐시 디렉토리 경로 가져오기
- cache_path(): 하위 경로 포함 캐시 경로
- 함수 인자 기반 경로 설정
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

from helper_dev_utils import google_driver, google_driver_path, cache, cache_path


# =============================================================================
# 픽스처
# =============================================================================


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
# 테스트 클래스 1: cache
# =============================================================================


class TestCache:
    """cache() 함수 테스트"""

    def test_cache_basic(self):
        """기본 캐시 경로 가져오기"""
        result = cache()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_cache_with_local(self, temp_cache_dir):
        """cache_local 인자로 캐시 경로 설정 테스트"""
        result = cache(cache_local=temp_cache_dir)
        assert temp_cache_dir in result or result == temp_cache_dir

    def test_cache_returns_valid_path(self):
        """유효한 경로 반환 확인"""
        result = cache()
        path_obj = Path(result)
        assert path_obj.parent.exists() or path_obj.exists()

    def test_cache_consistent(self):
        """일관된 경로 반환 확인"""
        result1 = cache()
        result2 = cache()
        assert result1 == result2


# =============================================================================
# 테스트 클래스 2: cache_path
# =============================================================================


class TestCachePath:
    """cache_path() 함수 테스트"""

    def test_cache_path_basic(self):
        """기본 캐시 경로 가져오기"""
        result = cache_path()
        assert result is not None
        assert isinstance(result, str)

    def test_cache_path_with_subpath(self):
        """하위 경로 포함"""
        result = cache_path("models", "bert")
        assert "models" in result
        assert "bert" in result

    def test_cache_path_none(self):
        """None 전달 - 기본 경로와 동일"""
        result = cache_path(None)
        base = cache()
        assert result == base

    def test_cache_path_multiple_levels(self):
        """다중 레벨 하위 경로"""
        result = cache_path("data", "images", "train")
        assert "data" in result

    def test_cache_path_escape_raises(self):
        """경로 탈출 시 ValueError 발생"""
        with pytest.raises(ValueError):
            cache_path("../parent/child")


# =============================================================================
# 테스트 클래스 3: google_driver
# =============================================================================


class TestGoogleDriver:
    """google_driver() 함수 테스트"""

    def test_google_driver_basic(self):
        """기본 드라이버 경로 가져오기"""
        result = google_driver()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_google_driver_with_local(self, temp_driver_dir):
        """google_driver_local 인자로 드라이버 경로 설정 테스트"""
        result = google_driver(google_driver_local=temp_driver_dir)
        assert temp_driver_dir in result or result == temp_driver_dir

    def test_google_driver_returns_valid_path(self):
        """유효한 경로 반환 확인"""
        result = google_driver()
        path_obj = Path(result)
        assert path_obj.parent.exists() or path_obj.exists()

    def test_google_driver_consistent(self):
        """일관된 경로 반환 확인"""
        result1 = google_driver()
        result2 = google_driver()
        assert result1 == result2


# =============================================================================
# 테스트 클래스 4: google_driver_path
# =============================================================================


class TestGoogleDriverPath:
    """google_driver_path() 함수 테스트"""

    def test_google_driver_path_basic(self):
        """기본 드라이버 경로 가져오기"""
        result = google_driver_path()
        assert result is not None
        assert isinstance(result, str)

    def test_google_driver_path_with_subpath(self):
        """하위 경로 포함"""
        result = google_driver_path("datasets", "images")
        assert "datasets" in result
        assert "images" in result

    def test_google_driver_path_none(self):
        """None 전달 - 기본 경로와 동일"""
        result = google_driver_path(None)
        base = google_driver()
        assert result == base

    def test_google_driver_path_multiple_levels(self):
        """다중 레벨 하위 경로"""
        result = google_driver_path("projects", "ml", "data")
        assert "projects" in result

    def test_google_driver_path_escape_raises(self):
        """경로 탈출 시 ValueError 발생"""
        with pytest.raises(ValueError):
            google_driver_path("../parent/child")


# =============================================================================
# 테스트 클래스 5: OS별 경로 탐색
# =============================================================================


class TestOSSpecificPaths:
    """OS별 경로 탐색 테스트"""

    def test_cache_path_is_absolute(self):
        """캐시 경로 절대 경로 검증"""
        result = cache()
        assert os.path.isabs(result)

    def test_driver_path_is_absolute(self):
        """드라이버 경로 절대 경로 검증"""
        result = google_driver()
        assert os.path.isabs(result)

    def test_platform_detection(self):
        """플랫폼 감지 테스트"""
        system = platform.system()
        result = cache()

        if system == "Windows":
            assert (
                "AppData" in result
                or "Temp" in result
                or "temp" in result.lower()
                or "cache" in result.lower()
            )
        elif system in ["Linux", "Darwin"]:
            assert os.path.expanduser("~") in result or "/tmp" in result


# =============================================================================
# 테스트 클래스 6: 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_all_functions_work(self):
        """모든 함수 정상 작동 확인"""
        base_cache = cache()
        base_driver = google_driver()
        assert base_cache is not None
        assert base_driver is not None

        cache_sub = cache_path("test")
        driver_sub = google_driver_path("test")
        assert "test" in cache_sub
        assert "test" in driver_sub

    def test_path_consistency(self):
        """경로 일관성 검증 - cache()와 cache_path() 기본값 동일"""
        c1 = cache()
        c2 = cache_path()
        assert c1 == c2

        d1 = google_driver()
        d2 = google_driver_path()
        assert d1 == d2

    def test_subpath_composition(self):
        """하위 경로 조합 테스트"""
        base = cache()
        sub = cache_path("models", "bert")
        assert sub.startswith(base)


# =============================================================================
# 테스트 클래스 7: 엣지 케이스
# =============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_special_characters_in_subpath(self):
        """특수 문자 포함 하위 경로"""
        result = cache_path("data_2024", "test-files")
        assert result is not None

    def test_unicode_in_subpath(self):
        """유니코드 포함 하위 경로"""
        result = cache_path("데이터", "한글폴더")
        assert result is not None


# =============================================================================
# 테스트 클래스 8: 타입 검증
# =============================================================================


class TestTypeValidation:
    """타입 검증 테스트"""

    def test_return_types(self):
        """반환 타입 검증"""
        assert isinstance(cache(), str)
        assert isinstance(google_driver(), str)
        assert isinstance(cache_path(), str)
        assert isinstance(google_driver_path(), str)

    def test_subpath_none_type(self):
        """None 하위 경로 타입 검증"""
        assert isinstance(cache_path(None), str)
        assert isinstance(google_driver_path(None), str)
