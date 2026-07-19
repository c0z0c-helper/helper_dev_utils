"""
helper_pandas 모듈

pandas 확장 기능을 제공하는 메인 모듈입니다.
- 기존 API 유지를 위한 재수출 모듈
- 텍스트 포맷팅 유틸리티 (core)
- 컬럼 설명 관리 (core)
- DataFrame/Series 출력 기능 (display)
- pandas extension 자동 등록
"""

# Standard library imports
import inspect
import os
import platform
import string
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Third-party imports
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Optional third-party imports (with import fallbacks)
try:
    import importlib.resources as resources
except ImportError:
    import importlib_resources as resources  # type: ignore

# 조건부 상대 임포트: 패키지 또는 직접 실행 모두 지원
try:
    from . import helper_logger
    from . import helper_pandas_core as core
    from . import helper_pandas_display as display
except ImportError:
    import helper_logger
    import helper_pandas_core as core
    import helper_pandas_display as display

try:
    import IPython
    from IPython.display import HTML

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

try:
    import google.colab
    from google.colab import drive

    IS_COLAB = True
except ImportError:
    IS_COLAB = False

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

# 하위 호환성을 위한 core 모듈 함수 재수출
_get_text_width = core.get_text_width
_format_value = core.format_value
_align_text = core.align_text
_calculate_column_widths = core.calculate_column_widths


# =============================================================================
# PANDAS EXTENSION: REGISTRATION FUNCTION
# =============================================================================


def set_pandas_extension(enable_head_override: bool = True) -> None:
    """pandas DataFrame/Series에 한글 컬럼 설명 기능을 추가합니다.

    Parameters
    ----------
    enable_head_override : bool, default True
        True면 head() 메서드를 head_att() 기능으로 대체합니다.

    Notes
    -----
    이 함수는 모듈 로드 시 자동으로 호출되므로 직접 호출할 필요가 없습니다.
    """
    # 원본 head 메서드 백업 (한 번만)
    if not hasattr(pd.DataFrame, "_head"):
        pd.DataFrame._head = pd.DataFrame.head
        pd.Series._head = pd.Series.head

    # 기본 기능 (core 모듈에서 가져옴)
    for cls in [pd.DataFrame, pd.Series]:
        setattr(cls, "set_head_att", core.set_head_att)
        setattr(cls, "get_head_att", core.get_head_att)
        setattr(cls, "remove_head_att", core.remove_head_att)
        setattr(cls, "clear_head_att", core.clear_head_att)

    # DataFrame/Series별 출력 함수 (display 모듈에서 가져옴)
    setattr(pd.DataFrame, "head_att", display.pd_head_att)
    setattr(pd.DataFrame, "print_head_att", display.print_head_att)
    setattr(pd.DataFrame, "_html_head_att", display._html_head_att)
    setattr(pd.DataFrame, "_string_head_att", display._string_head_att)
    setattr(pd.Series, "head_att", display.series_head_att)

    # head() 메서드 오버라이드
    if enable_head_override:
        setattr(pd.DataFrame, "head", display.pd_head_att)
        setattr(pd.Series, "head", display.series_head_att)
    else:
        # 원본 복원
        setattr(pd.DataFrame, "head", pd.DataFrame._head)
        setattr(pd.Series, "head", pd.Series._head)


# 모듈 로드 시 자동 등록
set_pandas_extension()


# =============================================================================
# MAIN FUNCTION FOR TESTING
# =============================================================================


def main() -> None:
    """head_att 기능 테스트를 위한 메인 함수.

    DataFrame과 Series의 head_att 관련 기능들을 테스트합니다:
    - set_head_att: 컬럼 설명 설정
    - get_head_att: 컬럼 설명 조회
    - head_att: 한글 컬럼명과 함께 데이터 출력
    - remove_head_att: 컬럼 설명 삭제
    - clear_head_att: 모든 컬럼 설명 초기화
    """
    logger = helper_logger.get_logger()
    _print = logger.info  # logger의 info 메서드로 대체

    _print("=" * 80)
    _print("pandas head_att 기능 테스트")
    _print("=" * 80)

    _print("✓ pandas extension 등록 완료")

    # =============================================================================
    # 테스트 1: DataFrame 기본 기능 테스트
    # =============================================================================
    _print("-" * 80)
    _print("테스트 1: DataFrame 기본 기능")
    _print("-" * 80)

    # 테스트 데이터 생성
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "score": [85.5, 92.3, 78.9, 88.1, 95.7],
            "city": ["Seoul", "Busan", "Daegu", "Incheon", "Gwangju"],
        }
    )

    _print("[원본 DataFrame]")
    _print(df)

    # =============================================================================
    # 테스트 2: set_head_att - 컬럼 설명 설정
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 2: set_head_att() - 컬럼 설명 설정")
    _print("-" * 80)

    # 딕셔너리로 여러 컬럼 설정
    df.set_head_att(
        {"id": "아이디", "name": "이름", "age": "나이", "score": "점수", "city": "도시"}
    )
    _print("✓ 컬럼 설명 설정 완료 (딕셔너리)")

    # 개별 컬럼 수정
    df.set_head_att("score", "시험점수")
    _print("✓ 'score' 컬럼 설명 수정: '점수' → '시험점수'")

    # =============================================================================
    # 테스트 3: get_head_att - 컬럼 설명 조회
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 3: get_head_att() - 컬럼 설명 조회")
    _print("-" * 80)

    # 전체 컬럼 설명 조회
    all_descriptions = df.get_head_att()
    _print(f"전체 컬럼 설명: {all_descriptions}")

    # 특정 컬럼 설명 조회
    score_desc = df.get_head_att("score")
    _print(f"'score' 컬럼 설명: {score_desc}")

    # 설명이 없는 컬럼 조회 (컬럼명 반환)
    unknown_desc = df.get_head_att("unknown")
    _print(f"'unknown' 컬럼 설명: {unknown_desc}")

    # =============================================================================
    # 테스트 4: head_att - 한글 컬럼명과 함께 데이터 출력
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 4: head() - 한글 컬럼명과 함께 데이터 출력")
    _print("-" * 80)

    _print("[기본 출력 - 5행]")
    df.head()

    _print("[문자열 형태로 반환]")
    result_str = df.head(rows=2, out="str")
    _print(f"반환된 문자열:\n{result_str}")

    # =============================================================================
    # 테스트 5: Series 기능 테스트
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 5: Series head 기능")
    _print("-" * 80)

    # Series 생성
    series = pd.Series([100, 200, 300, 400, 500], name="value")

    _print("[원본 Series]")
    _print(series)

    # Series에 컬럼 설명 설정
    series.set_head_att("value", "값")
    _print("✓ Series 컬럼 설명 설정: 'value' → '값'")

    _print("[Series head 출력]")
    series.head(rows=3)

    # =============================================================================
    # 테스트 6: remove_head_att - 컬럼 설명 삭제
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 6: remove_head_att() - 컬럼 설명 삭제")
    _print("-" * 80)

    # 단일 컬럼 삭제
    df.remove_head_att("city")

    _print("[삭제 후 컬럼 설명]")
    _print(df.get_head_att())

    # 여러 컬럼 삭제
    df.remove_head_att(["age", "score"])

    _print("[여러 컬럼 삭제 후]")
    _print(df.get_head_att())

    _print("[남은 컬럼 설명으로 출력]")
    df.head(rows=3)

    # =============================================================================
    # 테스트 7: clear_head_att - 모든 컬럼 설명 초기화
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 7: clear_head_att() - 모든 컬럼 설명 초기화")
    _print("-" * 80)

    df.clear_head_att()
    _print("✓ 모든 컬럼 설명 초기화 완료")

    _print("[초기화 후 컬럼 설명]")
    _print(df.get_head_att())

    _print("[컬럼 설명 없이 출력 (원본 컬럼명만 표시)]")
    df.head(rows=3)

    # =============================================================================
    # 테스트 8: 일부 컬럼만 설명이 있는 경우
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 8: 일부 컬럼만 설명이 있는 경우")
    _print("-" * 80)

    df.set_head_att({"id": "아이디", "name": "이름"})

    _print("✓ 일부 컬럼만 설명 설정 (id, name)")
    _print(f"현재 컬럼 설명: {df.get_head_att()}")

    _print("[일부 컬럼만 한글 설명이 있는 출력]")
    df.head(rows=3)

    # =============================================================================
    # 테스트 9: HTML 출력 테스트
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 9: HTML 출력 테스트")
    _print("-" * 80)

    df.set_head_att({"score": "시험점수", "city": "도시"})

    html_output = df.head(rows=3, out="html")
    _print("✓ HTML 출력 생성 완료")
    _print(f"HTML 타입: {type(html_output)}")
    if hasattr(html_output, "data"):
        _print(f"HTML 길이: {len(html_output.data)} 문자")
    else:
        _print(f"HTML 길이: {len(str(html_output))} 문자")

    # =============================================================================
    # 테스트 10: 실수 포맷팅 테스트
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 10: 실수 포맷팅 테스트")
    _print("-" * 80)

    df_float = pd.DataFrame(
        {
            "value1": [1.0, 2.5000, 3.1234567],
            "value2": [10.00, 20.1230, 30.9999],
            "value3": [100, 200, 300],
        }
    )

    df_float.set_head_att({"value1": "값1", "value2": "값2", "value3": "정수값"})

    _print("[실수 포맷팅 테스트 (소수점 4자리, 끝자리 0 제거)]")
    df_float.head()

    # =============================================================================
    # 테스트 11: enable_head_override 기능 테스트
    # =============================================================================
    _print("" + "-" * 80)
    _print("테스트 11: enable_head_override 기능 테스트")
    _print("-" * 80)

    # 새로운 테스트 데이터
    df_test = pd.DataFrame(
        {
            "product": ["A", "B", "C"],
            "price": [1000, 2000, 3000],
            "stock": [10, 20, 30],
        }
    )
    df_test.set_head_att({"product": "제품", "price": "가격", "stock": "재고"})

    _print("[오버라이드 모드: enable_head_override=True]")
    _print("df.head() 호출 (head_att 기능 사용):")
    df_test.head(rows=3)

    # =============================================================================
    # 테스트 완료
    # =============================================================================
    _print("" + "=" * 80)
    _print("✓ 모든 테스트 완료!")
    _print("=" * 80)


if __name__ == "__main__":
    main()
