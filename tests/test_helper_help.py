"""
test_helper_help.py
===================
helper_help 모듈의 pytest 테스트 스위트

테스트 범위:
- helper_help(): 함수/메서드 시그니처 및 docstring 출력
- helper_search(): 모듈 내 함수/클래스 이름 기반 검색
"""

import sys
import types
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from helper_dev_utils import helper_help, helper_search


# =============================================================================
# 픽스처
# =============================================================================


@pytest.fixture
def simple_func():
    """docstring이 있는 단순 함수"""

    def add(a: int, b: int) -> int:
        """두 정수를 더한다."""
        return a + b

    return add


@pytest.fixture
def no_doc_func():
    """docstring이 없는 함수"""

    def no_doc(x):
        return x

    return no_doc


@pytest.fixture
def sample_module():
    """테스트용 가상 모듈 생성"""
    mod = types.ModuleType("sample_mod")

    def alpha_func():
        """알파 함수"""

    def beta_search():
        """베타 검색 함수"""

    def gamma_func():
        """감마 함수"""

    class AlphaClass:
        """알파 클래스"""

    setattr(mod, "alpha_func", alpha_func)
    setattr(mod, "beta_search", beta_search)
    setattr(mod, "gamma_func", gamma_func)
    setattr(mod, "AlphaClass", AlphaClass)
    return mod


# =============================================================================
# helper_help 테스트
# =============================================================================


class TestHelperHelp:
    def test_output_contains_signature(self, capsys, simple_func):
        """시그니처가 출력에 포함되는지 확인"""
        helper_help(simple_func)
        captured = capsys.readouterr()
        assert "Signature" in captured.out
        assert "add" in captured.out

    def test_output_contains_docstring(self, capsys, simple_func):
        """docstring이 출력에 포함되는지 확인"""
        helper_help(simple_func)
        captured = capsys.readouterr()
        assert "Docstring" in captured.out
        assert "두 정수를 더한다." in captured.out

    def test_output_contains_param_types(self, capsys, simple_func):
        """파라미터 타입힌트가 시그니처에 포함되는지 확인"""
        helper_help(simple_func)
        captured = capsys.readouterr()
        assert "int" in captured.out

    def test_no_docstring_fallback(self, capsys, no_doc_func):
        """docstring이 없으면 fallback 메시지 출력 확인"""
        helper_help(no_doc_func)
        captured = capsys.readouterr()
        assert "(docstring 없음)" in captured.out

    def test_builtin_function(self, capsys):
        """내장 함수(len)에 대해 예외 없이 실행되는지 확인"""
        helper_help(len)
        captured = capsys.readouterr()
        assert "Signature" in captured.out or "len" in captured.out

    def test_pandas_dataframe_method(self, capsys):
        """pandas DataFrame.groupby 메서드에 대해 정상 출력 확인"""
        pd = pytest.importorskip("pandas")
        helper_help(pd.DataFrame.groupby)
        captured = capsys.readouterr()
        assert "groupby" in captured.out

    def test_matplotlib_function(self, capsys):
        """matplotlib pyplot.plot 함수에 대해 정상 출력 확인"""
        plt = pytest.importorskip("matplotlib.pyplot")
        helper_help(plt.plot)
        captured = capsys.readouterr()
        assert "plot" in captured.out

    def test_returns_none(self, simple_func):
        """반환값이 None인지 확인"""
        result = helper_help(simple_func)
        assert result is None

    def test_lambda(self, capsys):
        """lambda 함수에 대해 예외 없이 실행되는지 확인"""
        f = lambda x: x * 2  # noqa: E731
        helper_help(f)
        captured = capsys.readouterr()
        assert "Signature" in captured.out


# =============================================================================
# helper_search 테스트
# =============================================================================


class TestHelperSearch:
    def test_query_filters_results(self, capsys, sample_module):
        """query가 포함된 이름만 출력되는지 확인"""
        helper_search(sample_module, "alpha")
        captured = capsys.readouterr()
        assert "alpha_func" in captured.out or "AlphaClass" in captured.out
        assert "beta_search" not in captured.out
        assert "gamma_func" not in captured.out

    def test_query_case_insensitive(self, capsys, sample_module):
        """query 검색이 대소문자를 구분하지 않는지 확인"""
        helper_search(sample_module, "ALPHA")
        captured = capsys.readouterr()
        assert "alpha_func" in captured.out or "AlphaClass" in captured.out

    def test_query_none_returns_all(self, capsys, sample_module):
        """query=None 이면 전체 목록이 출력되는지 확인"""
        helper_search(sample_module)
        captured = capsys.readouterr()
        assert "alpha_func" in captured.out
        assert "beta_search" in captured.out
        assert "gamma_func" in captured.out

    def test_no_match_message(self, capsys, sample_module):
        """일치하는 항목이 없으면 안내 메시지 출력 확인"""
        helper_search(sample_module, "zzz_not_exist")
        captured = capsys.readouterr()
        assert "없습니다" in captured.out

    def test_result_count_in_output(self, capsys, sample_module):
        """출력에 검색 건수가 표시되는지 확인"""
        helper_search(sample_module, "func")
        captured = capsys.readouterr()
        assert "건" in captured.out

    def test_module_name_in_output(self, capsys, sample_module):
        """출력에 모듈 이름이 포함되는지 확인"""
        helper_search(sample_module, "alpha")
        captured = capsys.readouterr()
        assert "sample_mod" in captured.out

    def test_pandas_module_search(self, capsys):
        """pandas 모듈에서 'merge' 검색 결과 확인"""
        pd = pytest.importorskip("pandas")
        helper_search(pd, "merge")
        captured = capsys.readouterr()
        assert "merge" in captured.out

    def test_helper_dev_utils_search(self, capsys):
        """helper_dev_utils 자체 모듈 검색 확인"""
        import helper_dev_utils

        helper_search(helper_dev_utils, "logger")
        captured = capsys.readouterr()
        assert "get_logger" in captured.out or "get_auto_logger" in captured.out

    def test_returns_none(self, sample_module):
        """반환값이 None인지 확인"""
        result = helper_search(sample_module, "alpha")
        assert result is None
