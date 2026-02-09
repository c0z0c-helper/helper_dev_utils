"""
test_helper_utils_print.py
============================
helper_utils_print 모듈의 pytest 테스트 스위트

테스트 범위:
- print_dir_tree(): 디렉토리 트리 구조 출력
- print_json_tree(): JSON 트리 구조 출력 (파이프 스타일)
- print_dic_tree(): 딕셔너리 트리 구조 출력 (박스 드로잉 스타일)

주의: print 함수들은 logger.info()로 출력하므로 capsys로 캡처되지 않음
      예외 없이 실행되는지만 검증
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# 프로젝트 루트에서 src 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from helper_dev_utils import print_dir_tree, print_json_tree, print_dic_tree


# =============================================================================
# 픽스처
# =============================================================================


@pytest.fixture
def temp_dir_structure():
    """임시 디렉토리 구조 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 파일 생성
        (Path(tmpdir) / "file1.txt").write_text("test1")
        (Path(tmpdir) / "file2.py").write_text("test2")

        # 하위 디렉토리 생성
        subdir1 = Path(tmpdir) / "subdir1"
        subdir1.mkdir()
        (subdir1 / "subfile1.txt").write_text("sub1")

        subdir2 = Path(tmpdir) / "subdir2"
        subdir2.mkdir()
        (subdir2 / "subfile2.txt").write_text("sub2")

        # 중첩 디렉토리
        nested = subdir1 / "nested"
        nested.mkdir()
        (nested / "nested_file.txt").write_text("nested")

        yield tmpdir


@pytest.fixture
def sample_dict():
    """테스트용 딕셔너리"""
    return {
        "name": "Alice",
        "age": 25,
        "address": {"city": "Seoul", "zipcode": "12345"},
        "hobbies": ["reading", "coding", "gaming"],
        "scores": {"math": 95, "english": 88, "science": 92},
    }


@pytest.fixture
def sample_json():
    """테스트용 JSON 형태 데이터"""
    return {
        "users": [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 30},
            {"name": "Charlie", "age": 35},
        ],
        "config": {"debug": True, "timeout": 30},
        "metadata": {"version": "1.0.0", "author": "test"},
    }


# =============================================================================
# 테스트 클래스 1: print_dir_tree
# =============================================================================


class TestPrintDirTree:
    """print_dir_tree() 함수 테스트"""

    def test_print_dir_tree_basic(self, temp_dir_structure):
        """기본 디렉토리 트리 출력 - 예외 없이 실행"""
        print_dir_tree(temp_dir_structure)

    def test_print_dir_tree_max_file_list(self, temp_dir_structure):
        """파일 개수 제한 테스트"""
        print_dir_tree(temp_dir_structure, max_file_list=1)

    def test_print_dir_tree_max_dir_list(self, temp_dir_structure):
        """디렉토리 개수 제한 테스트"""
        print_dir_tree(temp_dir_structure, max_dir_list=1)

    def test_print_dir_tree_nonexistent(self):
        """존재하지 않는 경로 테스트 - 예외 없이 처리"""
        print_dir_tree("/nonexistent/path/xyz")

    def test_print_dir_tree_empty_dir(self):
        """빈 디렉토리 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            print_dir_tree(tmpdir)


# =============================================================================
# 테스트 클래스 2: print_json_tree
# =============================================================================


class TestPrintJsonTree:
    """print_json_tree() 함수 테스트"""

    def test_print_json_tree_basic(self, sample_json):
        """기본 JSON 트리 출력"""
        print_json_tree(sample_json)

    def test_print_json_tree_max_depth(self, sample_json):
        """최대 깊이 제한 테스트"""
        print_json_tree(sample_json, max_depth=1)

    def test_print_json_tree_list_count(self, sample_json):
        """리스트 항목 개수 제한 테스트"""
        print_json_tree(sample_json, list_count=2)

    def test_print_json_tree_simple_dict(self):
        """단순 딕셔너리 출력"""
        data = {"key1": "value1", "key2": "value2"}
        print_json_tree(data)

    def test_print_json_tree_nested(self):
        """중첩 구조 테스트"""
        data = {
            "level1": {
                "level2": {"level3": {"level4": "deep"}},
            }
        }
        print_json_tree(data, max_depth=10)

    def test_print_json_tree_print_value_false(self, sample_json):
        """값 숨김 옵션 테스트"""
        print_json_tree(sample_json, print_value=False)


# =============================================================================
# 테스트 클래스 3: print_dic_tree
# =============================================================================


class TestPrintDicTree:
    """print_dic_tree() 함수 테스트"""

    def test_print_dic_tree_basic(self, sample_dict):
        """기본 딕셔너리 트리 출력"""
        print_dic_tree(sample_dict)

    def test_print_dic_tree_print_value_true(self, sample_dict):
        """값 표시 옵션 테스트"""
        print_dic_tree(sample_dict, print_value=True)

    def test_print_dic_tree_print_value_false(self, sample_dict):
        """값 숨김 옵션 테스트"""
        print_dic_tree(sample_dict, print_value=False)

    def test_print_dic_tree_max_depth(self, sample_dict):
        """최대 깊이 제한 테스트"""
        print_dic_tree(sample_dict, max_depth=1)

    def test_print_dic_tree_simple(self):
        """단순 딕셔너리 출력"""
        data = {"a": 1, "b": 2, "c": 3}
        print_dic_tree(data, print_value=True)

    def test_print_dic_tree_list_count(self, sample_dict):
        """리스트 항목 개수 제한 테스트"""
        print_dic_tree(sample_dict, list_count=2)


# =============================================================================
# 테스트 클래스 4: 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_all_print_functions(self, temp_dir_structure, sample_dict):
        """모든 print 함수 실행 테스트 - 예외 없이 실행"""
        # 1. 디렉토리 트리
        print_dir_tree(temp_dir_structure, max_file_list=5, max_dir_list=5)

        # 2. JSON 트리
        print_json_tree(sample_dict, max_depth=5)

        # 3. 딕셔너리 트리
        print_dic_tree(sample_dict, print_value=True)

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        # 빈 딕셔너리
        print_json_tree({})

        # None 값 포함
        data = {"key": None, "nested": {"value": None}}
        print_dic_tree(data, print_value=True)

        # 리스트만 있는 경우
        list_data = {"items": [1, 2, 3, 4, 5]}
        print_json_tree(list_data)


# =============================================================================
# 테스트 클래스 5: 타입 검증
# =============================================================================


class TestTypeValidation:
    """타입 검증 테스트"""

    def test_print_dir_tree_types(self, temp_dir_structure):
        """print_dir_tree 타입 검증"""
        # 정상 실행 (예외 발생 안 함)
        print_dir_tree(temp_dir_structure)
        print_dir_tree(temp_dir_structure, indent="  ")
        print_dir_tree(temp_dir_structure, max_file_list=0)
        print_dir_tree(temp_dir_structure, max_dir_list=None)

    def test_print_json_tree_types(self, sample_json):
        """print_json_tree 타입 검증"""
        # 정상 실행
        print_json_tree(sample_json)
        print_json_tree(sample_json, max_depth=0)
        print_json_tree(sample_json, list_count=100)
        print_json_tree(sample_json, print_value=False)

    def test_print_dic_tree_types(self, sample_dict):
        """print_dic_tree 타입 검증"""
        # 정상 실행
        print_dic_tree(sample_dict)
        print_dic_tree(sample_dict, max_depth=10)
        print_dic_tree(sample_dict, print_value=False)
        print_dic_tree(sample_dict, list_count=0)
