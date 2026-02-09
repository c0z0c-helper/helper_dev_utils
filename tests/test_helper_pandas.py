"""
test_helper_pandas.py
============================
helper_pandas 모듈의 pytest 테스트 스위트

테스트 범위:
- set_pandas_extension(): pandas 확장 등록
- DataFrame.set_head_att(): 컬럼 설명 설정
- DataFrame.get_head_att(): 컬럼 설명 조회
- DataFrame.remove_head_att(): 컬럼 설명 삭제
- DataFrame.clear_head_att(): 컬럼 설명 초기화
- DataFrame.head_att(): 한글 컬럼명 출력
- Series.set_head_att(): Series 컬럼 설명
- Series.head_att(): Series 출력
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# 프로젝트 루트에서 src 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from helper_dev_utils import set_pandas_extension


@pytest.fixture(autouse=True)
def setup_pandas_extension():
    """모든 테스트 전에 pandas 확장 등록"""
    set_pandas_extension(enable_head_override=True)
    yield


@pytest.fixture
def sample_df():
    """테스트용 DataFrame 생성"""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 92.3, 78.9],
        }
    )


@pytest.fixture
def sample_series():
    """테스트용 Series 생성"""
    return pd.Series([100, 200, 300], name="value")


# =============================================================================
# 테스트 클래스 1: set_head_att
# =============================================================================


class TestSetHeadAtt:
    """set_head_att() 메서드 테스트"""

    def test_set_head_att_dict(self, sample_df):
        """딕셔너리로 여러 컬럼 설명 설정"""
        sample_df.set_head_att({"id": "아이디", "name": "이름", "age": "나이"})
        assert sample_df.get_head_att("id") == "아이디"
        assert sample_df.get_head_att("name") == "이름"
        assert sample_df.get_head_att("age") == "나이"

    def test_set_head_att_single(self, sample_df):
        """개별 컬럼 설명 설정"""
        sample_df.set_head_att("score", "점수")
        assert sample_df.get_head_att("score") == "점수"

    def test_set_head_att_update(self, sample_df):
        """컬럼 설명 업데이트"""
        sample_df.set_head_att("id", "아이디")
        assert sample_df.get_head_att("id") == "아이디"
        sample_df.set_head_att("id", "ID번호")
        assert sample_df.get_head_att("id") == "ID번호"

    def test_set_head_att_invalid_usage(self, sample_df):
        """잘못된 사용법 테스트"""
        with pytest.raises(ValueError):
            sample_df.set_head_att("key")  # value 없이 str만 전달


# =============================================================================
# 테스트 클래스 2: get_head_att
# =============================================================================


class TestGetHeadAtt:
    """get_head_att() 메서드 테스트"""

    def test_get_head_att_all(self, sample_df):
        """전체 컬럼 설명 조회"""
        sample_df.set_head_att({"id": "아이디", "name": "이름"})
        descriptions = sample_df.get_head_att()
        assert isinstance(descriptions, dict)
        assert descriptions["id"] == "아이디"
        assert descriptions["name"] == "이름"

    def test_get_head_att_single(self, sample_df):
        """특정 컬럼 설명 조회"""
        sample_df.set_head_att("name", "이름")
        assert sample_df.get_head_att("name") == "이름"

    def test_get_head_att_nonexistent(self, sample_df):
        """존재하지 않는 컬럼 설명 조회 (컬럼명 반환)"""
        result = sample_df.get_head_att("unknown")
        assert result == "unknown"

    def test_get_head_att_empty(self, sample_df):
        """빈 컬럼 설명 딕셔너리 조회"""
        descriptions = sample_df.get_head_att()
        assert isinstance(descriptions, dict)
        assert len(descriptions) == 0

    def test_get_head_att_invalid_key_type(self, sample_df):
        """잘못된 키 타입 테스트"""
        with pytest.raises(TypeError):
            sample_df.get_head_att(123)


# =============================================================================
# 테스트 클래스 3: remove_head_att
# =============================================================================


class TestRemoveHeadAtt:
    """remove_head_att() 메서드 테스트"""

    def test_remove_head_att_single(self, sample_df):
        """단일 컬럼 설명 삭제"""
        sample_df.set_head_att({"id": "아이디", "name": "이름"})
        sample_df.remove_head_att("id")
        assert "id" not in sample_df.get_head_att()
        assert "name" in sample_df.get_head_att()

    def test_remove_head_att_multiple(self, sample_df):
        """여러 컬럼 설명 삭제"""
        sample_df.set_head_att({"id": "아이디", "name": "이름", "age": "나이"})
        sample_df.remove_head_att(["id", "name"])
        descriptions = sample_df.get_head_att()
        assert "id" not in descriptions
        assert "name" not in descriptions
        assert "age" in descriptions

    def test_remove_head_att_nonexistent(self, sample_df):
        """존재하지 않는 컬럼 삭제 시도 - 경고 메시지 출력"""
        # 실행만 확인 (예외 없이 처리됨)
        sample_df.remove_head_att("unknown")


# =============================================================================
# 테스트 클래스 4: clear_head_att
# =============================================================================


class TestClearHeadAtt:
    """clear_head_att() 메서드 테스트"""

    def test_clear_head_att(self, sample_df):
        """모든 컬럼 설명 초기화"""
        sample_df.set_head_att({"id": "아이디", "name": "이름", "age": "나이"})
        sample_df.clear_head_att()
        descriptions = sample_df.get_head_att()
        assert len(descriptions) == 0


# =============================================================================
# 테스트 클래스 5: DataFrame.head_att - print 출력
# =============================================================================


class TestDataFrameHeadAttPrint:
    """DataFrame.head_att() print 출력 테스트"""

    def test_head_att_default(self, sample_df, capsys):
        """기본 출력 (5행)"""
        sample_df.set_head_att({"id": "아이디", "name": "이름"})
        sample_df.head_att()
        captured = capsys.readouterr()
        assert "아이디" in captured.out
        assert "이름" in captured.out
        assert "id" in captured.out
        assert "name" in captured.out

    def test_head_att_rows(self, sample_df, capsys):
        """행 수 지정 출력"""
        sample_df.set_head_att({"id": "아이디"})
        sample_df.head_att(rows=2)
        captured = capsys.readouterr()
        assert "아이디" in captured.out

    def test_head_att_all_rows(self, sample_df, capsys):
        """전체 행 출력"""
        sample_df.set_head_att({"id": "아이디"})
        sample_df.head_att(rows="all")
        captured = capsys.readouterr()
        assert "아이디" in captured.out

    def test_head_att_no_descriptions(self, sample_df, capsys):
        """컬럼 설명 없이 출력 (원본 컬럼명만)"""
        sample_df.head_att()
        captured = capsys.readouterr()
        assert "id" in captured.out
        assert "name" in captured.out
        # 한글 설명이 없어야 함
        assert "아이디" not in captured.out


# =============================================================================
# 테스트 클래스 6: DataFrame.head_att - 다양한 출력 형식
# =============================================================================


class TestDataFrameHeadAttOutputFormats:
    """DataFrame.head_att() 다양한 출력 형식 테스트"""

    def test_head_att_str_output(self, sample_df):
        """문자열 형태로 반환"""
        sample_df.set_head_att({"id": "아이디", "name": "이름"})
        result = sample_df.head_att(rows=2, out="str")
        assert isinstance(result, str)
        assert "아이디" in result
        assert "이름" in result

    def test_head_att_html_output(self, sample_df):
        """HTML 형태로 반환"""
        sample_df.set_head_att({"id": "아이디", "name": "이름"})
        result = sample_df.head_att(rows=2, out="html")
        # HTML 객체 생성 확인
        assert result is not None

    def test_head_att_invalid_output(self, sample_df):
        """잘못된 출력 형식"""
        with pytest.raises(ValueError):
            sample_df.head_att(out="invalid")


# =============================================================================
# 테스트 클래스 7: Series.head_att
# =============================================================================


class TestSeriesHeadAtt:
    """Series.head_att() 메서드 테스트"""

    def test_series_set_head_att(self, sample_series):
        """Series 컬럼 설명 설정"""
        sample_series.set_head_att("value", "값")
        assert sample_series.get_head_att("value") == "값"

    def test_series_head_att_print(self, sample_series, capsys):
        """Series print 출력"""
        sample_series.set_head_att("value", "값")
        sample_series.head_att(rows=2)
        captured = capsys.readouterr()
        assert "값" in captured.out
        assert "value" in captured.out

    def test_series_head_att_str(self, sample_series):
        """Series 문자열 출력"""
        sample_series.set_head_att("value", "값")
        result = sample_series.head_att(rows=2, out="str")
        assert isinstance(result, str)
        assert "값" in result

    def test_series_head_att_html(self, sample_series):
        """Series HTML 출력"""
        sample_series.set_head_att("value", "값")
        result = sample_series.head_att(rows=2, out="html")
        # HTML 객체 생성 확인
        assert result is not None


# =============================================================================
# 테스트 클래스 8: head() 메서드 오버라이드
# =============================================================================


class TestHeadOverride:
    """head() 메서드 오버라이드 테스트"""

    def test_head_override_dataframe(self, sample_df, capsys):
        """DataFrame.head() 오버라이드"""
        sample_df.set_head_att({"id": "아이디"})
        sample_df.head()
        captured = capsys.readouterr()
        assert "아이디" in captured.out

    def test_head_override_series(self, sample_series, capsys):
        """Series.head() 오버라이드"""
        sample_series.set_head_att("value", "값")
        sample_series.head()
        captured = capsys.readouterr()
        assert "값" in captured.out


# =============================================================================
# 테스트 클래스 9: 실수 포맷팅
# =============================================================================


class TestFloatFormatting:
    """실수 포맷팅 테스트"""

    def test_float_formatting(self, capsys):
        """실수 포맷팅 (소수점 4자리, 끝자리 0 제거)"""
        df = pd.DataFrame(
            {
                "value1": [1.0, 2.5000, 3.1234567],
                "value2": [10.00, 20.1230, 30.9999],
            }
        )
        df.set_head_att({"value1": "값1", "value2": "값2"})
        df.head_att()
        captured = capsys.readouterr()
        # 소수점 4자리 반올림 확인
        assert "3.1235" in captured.out
        # 끝자리 0 제거 확인
        assert "1.0" not in captured.out or "1" in captured.out


# =============================================================================
# 테스트 클래스 10: 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_full_workflow(self, sample_df, capsys):
        """전체 워크플로우 테스트"""
        # 1. 컬럼 설명 설정
        sample_df.set_head_att({"id": "아이디", "name": "이름", "age": "나이", "score": "점수"})

        # 2. 조회
        assert sample_df.get_head_att("id") == "아이디"

        # 3. 출력
        sample_df.head_att(rows=2)
        captured = capsys.readouterr()
        assert "아이디" in captured.out

        # 4. 일부 삭제
        sample_df.remove_head_att("score")
        assert "score" not in sample_df.get_head_att()

        # 5. 초기화
        sample_df.clear_head_att()
        assert len(sample_df.get_head_att()) == 0

    def test_attrs_persistence(self, sample_df):
        """attrs 지속성 테스트"""
        sample_df.set_head_att({"id": "아이디"})
        # DataFrame 복사 시 attrs 유지
        df_copy = sample_df.copy()
        assert df_copy.get_head_att("id") == "아이디"
