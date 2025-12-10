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
except ImportError:
    import helper_logger

logger = helper_logger.get_auto_logger()

try:
    from dotenv import dotenv_values, load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

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

# _print = _print  # 기본 _print 함수를 user_print로 저장

_print = logger.info  # logger의 info 메서드로 대체


# =============================================================================
# HELPER FUNCTIONS FOR TEXT FORMATTING
# =============================================================================


def _get_text_width(text: Any) -> int:
    """텍스트 폭 계산 (한글 2칸, 영문 1칸).

    Parameters
    ----------
    text : Any
        폭을 계산할 텍스트. None이면 0 반환.

    Returns
    -------
    int
        텍스트의 표시 폭. 한글은 2칸, 영문/숫자는 1칸으로 계산.
    """
    if text is None:
        return 0
    return sum(2 if ord(char) >= 0x1100 else 1 for char in str(text))


def _format_value(value: Any) -> str:
    """값을 포맷팅합니다.

    실수형은 소수점 이하 4자리로 반올림하고, 정수형은 그대로 표시.
    배열이나 시리즈는 문자열로 변환.

    Parameters
    ----------
    value : Any
        포맷팅할 값.

    Returns
    -------
    str
        포맷팅된 값의 문자열 표현.
    """
    try:
        # 배열이나 시리즈인 경우 문자열로 변환
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            return str(value)

        # pandas NA 체크 (스칼라 값에만 적용)
        if pd.isna(value):
            return str(value)
        elif isinstance(value, (int, np.integer)):
            return str(value)
        elif isinstance(value, (float, np.floating)):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        else:
            return str(value)
    except (ValueError, TypeError):
        # 예외 발생 시 안전하게 문자열로 변환
        return str(value)


def _align_text(text: Any, width: int, align: str = "left") -> str:
    """텍스트를 지정된 폭에 맞춰 정렬.

    Parameters
    ----------
    text : Any
        정렬할 텍스트.
    width : int
        정렬 폭.
    align : str, default 'left'
        정렬 방향 ('left', 'right', 'center').

    Returns
    -------
    str
        정렬된 텍스트.
    """
    text_str = str(text)
    current_width = _get_text_width(text_str)
    padding = max(0, width - current_width)

    if align == "right":
        return " " * padding + text_str
    elif align == "center":
        left_padding = padding // 2
        right_padding = padding - left_padding
        return " " * left_padding + text_str + " " * right_padding
    else:  # left (default)
        return text_str + " " * padding


def _calculate_column_widths(
    df_display: pd.DataFrame, labels: Dict[str, str]
) -> List[int]:
    """컬럼 폭 계산 (pandas 기본 스타일).

    Parameters
    ----------
    df_display : pd.DataFrame
        표시할 DataFrame.
    labels : dict of {str: str}
        컬럼명과 한글 설명의 매핑.

    Returns
    -------
    list of int
        각 컬럼의 표시 폭 리스트.
    """
    widths = []

    # 첫 번째 컬럼: 인덱스 폭 계산
    if len(df_display) == 0:
        max_index_width = 1  # 최소 폭
    else:
        max_index_width = max(_get_text_width(str(idx)) for idx in df_display.index)

    # 인덱스 컬럼 폭 (pandas 스타일: 최소 여유 공간)
    index_width = max_index_width + 1
    widths.append(index_width)

    # 나머지 컬럼들
    for col in df_display.columns:
        korean_name = labels.get(col, col)
        english_name = col

        # 데이터가 비어있을 때 처리
        if len(df_display) == 0:
            max_data_width = 0
        else:
            max_data_width = max(
                _get_text_width(_format_value(val)) for val in df_display[col]
            )

        # 각 요소의 최대 폭 계산
        max_width = max(
            _get_text_width(korean_name),
            _get_text_width(english_name),
            max_data_width,
        )

        # pandas 스타일: 최소 여유 공간 (1칸)
        column_width = max_width + 1
        widths.append(column_width)

    return widths


# =============================================================================
# PANDAS EXTENSION: BASIC COLUMN DESCRIPTION FUNCTIONS
# =============================================================================


def set_head_att(
    self, key_or_dict: Union[Dict[str, str], str], value: Optional[str] = None
) -> None:
    """컬럼 설명을 설정합니다.

    Parameters
    ----------
    key_or_dict : dict or str
        - dict: 여러 컬럼 설명을 한 번에 설정 {"컬럼명": "설명"}
        - str: 단일 컬럼명 (value와 함께 사용)
    value : str, optional
        key_or_dict가 str일 때 해당 컬럼의 설명.

    Examples
    --------
    >>> df.set_head_att({"id": "ID", "state": "지역"})
    >>> df.set_head_att("id", "아이디")
    """
    # attrs 초기화
    if not hasattr(self, "attrs"):
        self.attrs = {}
    if "column_descriptions" not in self.attrs:
        self.attrs["column_descriptions"] = {}

    if isinstance(key_or_dict, dict):
        # 딕셔너리로 여러 개 설정
        self.attrs["column_descriptions"].update(key_or_dict)
    elif isinstance(key_or_dict, str) and value is not None:
        # 개별 설정/수정
        self.attrs["column_descriptions"][key_or_dict] = value
    else:
        raise ValueError("사용법: set_head_att(dict) 또는 set_head_att(key, value)")


def get_head_att(self, key: Optional[str] = None) -> Union[Dict[str, str], str]:
    """컬럼 설명을 반환합니다.

    Parameters
    ----------
    key : str, optional
        특정 컬럼의 설명을 가져올 컬럼명. None이면 전체 딕셔너리 반환.

    Returns
    -------
    dict or str
        - key가 None이면 전체 컬럼 설명 딕셔너리 반환
        - key가 주어지면 해당 컬럼의 설명 문자열 반환

    Raises
    ------
    KeyError
        존재하지 않는 컬럼명을 요청했을 때.
    TypeError
        key가 문자열이 아닐 때.

    Examples
    --------
    >>> descriptions = df.get_head_att()           # 전체 딕셔너리
    >>> score_desc = df.get_head_att('score')     # 특정 컬럼 설명
    >>> descriptions['new_col'] = '새로운 설명'    # 딕셔너리 직접 수정 가능
    """
    # attrs 초기화
    if not hasattr(self, "attrs"):
        self.attrs = {}
    if "column_descriptions" not in self.attrs:
        self.attrs["column_descriptions"] = {}

    # key가 None이면 전체 딕셔너리 반환
    if key is None:
        return self.attrs["column_descriptions"]

    # key 타입 검증
    if not isinstance(key, str):
        raise TypeError(f"key는 문자열이어야 합니다. 현재 타입: {type(key)}")

    # key 존재 여부 확인
    if key not in self.attrs["column_descriptions"]:
        return key  # 컬럼 설명이 없으면 key 자체 반환 (None 대신)

    return self.attrs["column_descriptions"][key]


def remove_head_att(self, key: Union[str, List[str]]) -> None:
    """특정 컬럼 설명 또는 컬럼 설명 리스트 삭제.

    Parameters
    ----------
    key : str or List[str]
        삭제할 컬럼명 또는 컬럼명 리스트.
    """
    if not hasattr(self, "attrs") or "column_descriptions" not in self.attrs:
        return

    if isinstance(key, str):
        key = [key]

    for k in key:
        if k in self.attrs["column_descriptions"]:
            self.attrs["column_descriptions"].pop(k)
            print(f"컬럼 설명 '{k}' 삭제 완료")
        else:
            print(f"'{k}' 컬럼 설명을 찾을 수 없습니다.")


def clear_head_att(self) -> None:
    """모든 컬럼 설명을 초기화합니다."""
    if not hasattr(self, "attrs"):
        self.attrs = {}
    self.attrs["column_descriptions"] = {}


# =============================================================================
# PANDAS EXTENSION: DISPLAY FUNCTIONS FOR DATAFRAME
# =============================================================================


def pd_head_att(self, rows: Union[int, str] = 5, out: Optional[str] = None) -> Any:
    """한글 컬럼 설명이 포함된 DataFrame을 다양한 형태로 출력합니다.

    Parameters
    ----------
    rows : int or str, optional
        출력할 행 수 (기본값: 5). 'all' 또는 -1이면 전체 출력.
    out : str, optional
        출력 형식 (기본값: 'print'). 'print', 'html', 'str' 중 선택.

    Returns
    -------
    str or None
        - 'print'일 경우 None 반환 (콘솔 출력).
        - 'html'일 경우 HTML 객체 반환.
        - 'str'일 경우 문자열 형태로 반환.

    Raises
    ------
    ValueError
        잘못된 out 옵션.

    Examples
    --------
    >>> df.head_att()  # 기본 출력 (5행)
    >>> df.head_att(rows=10)  # 10행 출력
    >>> df.head_att(out='html')  # HTML 형태로 출력
    >>> df.head_att(rows='all', out='print')  # 전체 데이터 출력 (콘솔)
    """
    labels = self.attrs.get("column_descriptions", {})

    # 출력할 데이터 결정
    if isinstance(rows, str) and rows.lower() == "all":
        df_display = self
    elif isinstance(rows, int):
        if rows == -1:
            df_display = self
        elif rows == 0:
            df_display = self.iloc[0:0]
        else:
            # 원본 head() 사용 (재귀 방지)
            if hasattr(pd.DataFrame, '_original_head'):
                df_display = pd.DataFrame._original_head(self, rows)
            else:
                df_display = self.iloc[:rows]
    else:
        # 원본 head() 사용 (재귀 방지)
        if hasattr(pd.DataFrame, '_original_head'):
            df_display = pd.DataFrame._original_head(self, 5)
        else:
            df_display = self.iloc[:5]

    # 보조 컬럼명 출력 조건
    # 1. column_descriptions가 완전히 비어 있으면 보조 컬럼명 출력하지 않음
    # 2. column_descriptions가 비어 있지 않고 특정 컬럼만 비어 있으면 기존과 동일하게 처리
    if not labels:
        # 보조 컬럼명 없이 오리지널 컬럼명만 한 번 출력
        def print_original_only(df_display):
            # 영문 헤더 출력 (오른쪽 정렬)
            column_widths = _calculate_column_widths(df_display, {})
            index_width = column_widths[0]
            data_widths = column_widths[1:]
            english_parts = []
            english_parts.append(_align_text("", index_width, "right"))
            for col, width in zip(df_display.columns, data_widths):
                english_parts.append(_align_text(col, width, "right"))
            print("".join(english_parts))
            # 데이터 출력
            for idx, row in df_display.iterrows():
                row_parts = []
                row_parts.append(_align_text(str(idx), index_width, "right"))
                for val, width in zip(row, data_widths):
                    row_parts.append(_align_text(_format_value(val), width, "right"))
                print("".join(row_parts))

        if out is None or out.lower() == "print":
            print_original_only(df_display)
            return None
        elif out.lower() == "html":
            # HTML 헤더는 오리지널 컬럼명만 출력
            df_copy = df_display.copy()
            # 실수형 값들을 포맷팅
            for col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(_format_value)
            df_copy.columns = list(df_display.columns)
            if IPYTHON_AVAILABLE:
                return HTML(df_copy.to_html(escape=False))
            else:
                return df_copy.to_html(escape=False)
        elif out.lower() in ["str", "string"]:
            # 문자열 형태로 오리지널 컬럼명만 출력
            column_widths = _calculate_column_widths(df_display, {})
            result = ""
            english_row = ""
            for i, col in enumerate(df_display.columns):
                english_row += _align_text(col, column_widths[i])
            result += english_row + "\n"
            for idx, row in df_display.iterrows():
                data_row = ""
                for i, val in enumerate(row):
                    if i == 0:
                        text = str(idx)
                        formatted_val = _format_value(val)
                        data_row += _align_text(
                            text, column_widths[i] - _get_text_width(formatted_val)
                        )
                        data_row += formatted_val
                    else:
                        data_row += _align_text(_format_value(val), column_widths[i])
                result += data_row + "\n"
            return result.rstrip()
        else:
            raise ValueError(
                "out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다."
            )
    else:
        # 기존 로직 (보조 컬럼명 일부만 비어 있으면 기존과 동일하게 처리)
        if out is None or out.lower() == "print":
            return self.print_head_att(df_display, labels)
        elif out.lower() == "html":
            return self._html_head_att(df_display, labels)
        elif out.lower() in ["str", "string"]:
            return self._string_head_att(df_display, labels)
        else:
            raise ValueError(
                "out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다."
            )


def print_head_att(self, df_display: pd.DataFrame, labels: Dict[str, str]) -> None:
    """print 형태로 출력 (pandas 기본 스타일).

    Parameters
    ----------
    df_display : pd.DataFrame
        표시할 DataFrame.
    labels : dict of {str: str}
        컬럼명과 한글 설명의 매핑.
    """
    column_widths = _calculate_column_widths(df_display, labels)

    # 첫 번째 부분은 인덱스용
    index_width = column_widths[0]
    data_widths = column_widths[1:]

    # 한글 헤더 출력 (오른쪽 정렬)
    korean_parts = []
    korean_parts.append(_align_text("", index_width, "right"))  # 인덱스 헤더는 빈공간
    for col, width in zip(df_display.columns, data_widths):
        korean_name = labels.get(col, col)
        korean_parts.append(_align_text(korean_name, width, "right"))
    print("".join(korean_parts))

    # 영문 헤더 출력 (오른쪽 정렬)
    english_parts = []
    english_parts.append(_align_text("", index_width, "right"))  # 인덱스 헤더는 빈공간
    for col, width in zip(df_display.columns, data_widths):
        english_parts.append(_align_text(col, width, "right"))
    print("".join(english_parts))

    # 데이터 출력 (모두 오른쪽 정렬 - pandas 기본 스타일)
    for idx, row in df_display.iterrows():
        row_parts = []
        # 인덱스 출력 (오른쪽 정렬)
        row_parts.append(_align_text(str(idx), index_width, "right"))
        # 데이터 출력 (오른쪽 정렬)
        for val, width in zip(row, data_widths):
            row_parts.append(_align_text(_format_value(val), width, "right"))
        print("".join(row_parts))


def _html_head_att(self, df_display: pd.DataFrame, labels: Dict[str, str]) -> Any:
    """HTML 형태로 출력.

    Parameters
    ----------
    df_display : pd.DataFrame
        표시할 DataFrame.
    labels : dict of {str: str}
        컬럼명과 한글 설명의 매핑.

    Returns
    -------
    HTML or str
        HTML 객체 또는 HTML 문자열.
    """
    header = []
    for col in df_display.columns:
        if col in labels and labels[col]:
            header.append(f"{labels[col]}<br>{col}")
        else:
            header.append(col)

    df_copy = df_display.copy()
    # 실수형 값들을 포맷팅
    for col in df_copy.columns:
        df_copy[col] = df_copy[col].apply(_format_value)
    df_copy.columns = header

    if IPYTHON_AVAILABLE:
        return HTML(df_copy.to_html(escape=False))
    else:
        return df_copy.to_html(escape=False)


def _string_head_att(self, df_display: pd.DataFrame, labels: Dict[str, str]) -> str:
    """문자열 형태로 출력.

    Parameters
    ----------
    df_display : pd.DataFrame
        표시할 DataFrame.
    labels : dict of {str: str}
        컬럼명과 한글 설명의 매핑.

    Returns
    -------
    str
        포맷된 문자열.
    """
    column_widths = _calculate_column_widths(df_display, labels)

    result = ""

    # 한글 헤더 생성
    korean_row = ""
    for i, col in enumerate(df_display.columns):
        korean_name = labels.get(col, col)
        korean_row += _align_text(korean_name, column_widths[i])
    result += korean_row + "\n"

    # 영문 헤더 생성
    english_row = ""
    for i, col in enumerate(df_display.columns):
        english_row += _align_text(col, column_widths[i])
    result += english_row + "\n"

    # 데이터 생성
    for idx, row in df_display.iterrows():
        data_row = ""
        for i, val in enumerate(row):
            if i == 0:
                text = str(idx)
                formatted_val = _format_value(val)
                data_row += _align_text(
                    text, column_widths[i] - _get_text_width(formatted_val)
                )
                data_row += formatted_val
            else:
                data_row += _align_text(_format_value(val), column_widths[i])
        result += data_row + "\n"

    return result.rstrip()


# =============================================================================
# PANDAS EXTENSION: DISPLAY FUNCTIONS FOR SERIES
# =============================================================================


def series_head_att(self, rows: Union[int, str] = 5, out: Optional[str] = None) -> Any:
    """한글 컬럼 설명이 포함된 Series를 다양한 형태로 출력합니다.

    Parameters
    ----------
    rows : int or str, optional
        출력할 행 수 (기본값: 5). 'all' 또는 -1이면 전체 출력.
    out : str, optional
        출력 형식 (기본값: 'print'). 'print', 'html', 'str' 중 선택.

    Returns
    -------
    str or None
        - 'print'일 경우 None 반환 (콘솔 출력).
        - 'html'일 경우 HTML 객체 반환.
        - 'str'일 경우 문자열 형태로 반환.
    """
    labels = self.attrs.get("column_descriptions", {})

    # 출력할 데이터 결정
    if isinstance(rows, str) and rows.lower() == "all":
        series_display = self
    elif isinstance(rows, int):
        if rows == -1:
            series_display = self
        elif rows == 0:
            series_display = self.iloc[0:0]
        else:
            # 원본 head() 사용 (재귀 방지)
            if hasattr(pd.Series, '_original_head'):
                series_display = pd.Series._original_head(self, rows)
            else:
                series_display = self.iloc[:rows]
    else:
        # 원본 head() 사용 (재귀 방지)
        if hasattr(pd.Series, '_original_head'):
            series_display = pd.Series._original_head(self, 5)
        else:
            series_display = self.iloc[:5]

    series_name = self.name if self.name is not None else "Series"
    korean_name = labels.get(series_name, series_name)

    if out is None or out.lower() == "print":
        # 인덱스 최대 폭 계산
        index_widths = [_get_text_width(str(idx)) for idx in series_display.index]
        max_index_width = max(index_widths) if index_widths else 0

        # 데이터 최대 폭 계산
        data_widths = [_get_text_width(_format_value(val)) for val in series_display]
        max_data_width = max(data_widths) if data_widths else 0

        # 헤더 폭 계산
        korean_header_width = _get_text_width(korean_name)
        english_header_width = _get_text_width(series_name)

        # 각 컬럼의 최대 폭 결정
        index_column_width = max(max_index_width, 5) + 2
        data_column_width = (
            max(max_data_width, korean_header_width, english_header_width) + 2
        )

        # 헤더 출력
        korean_header = _align_text("인덱스", index_column_width) + _align_text(
            korean_name, data_column_width
        )
        print(korean_header)

        english_header = _align_text("index", index_column_width) + _align_text(
            series_name, data_column_width
        )
        print(english_header)

        # 데이터 출력
        for idx, val in series_display.items():
            data_row = _align_text(str(idx), index_column_width) + _align_text(
                _format_value(val), data_column_width
            )
            print(data_row)

        return None

    elif out.lower() == "html":
        df = series_display.to_frame()
        # 실수형 값들을 포맷팅
        df.iloc[:, 0] = df.iloc[:, 0].apply(_format_value)

        if series_name in labels and labels[series_name]:
            df.columns = [f"{labels[series_name]}<br>{series_name}"]
        else:
            df.columns = [series_name]

        if IPYTHON_AVAILABLE:
            return HTML(df.to_html(escape=False))
        else:
            return df.to_html(escape=False)

    elif out.lower() in ["str", "string"]:
        # 인덱스 최대 폭 계산
        index_widths = [_get_text_width(str(idx)) for idx in series_display.index]
        max_index_width = max(index_widths) if index_widths else 0

        # 데이터 최대 폭 계산
        data_widths = [_get_text_width(_format_value(val)) for val in series_display]
        max_data_width = max(data_widths) if data_widths else 0

        # 헤더 폭 계산
        korean_header_width = _get_text_width(korean_name)
        english_header_width = _get_text_width(series_name)

        # 각 컬럼의 최대 폭 결정
        index_column_width = (
            max(max_index_width, _get_text_width("인덱스"), _get_text_width("index"))
            + 2
        )
        data_column_width = (
            max(max_data_width, korean_header_width, english_header_width) + 2
        )

        result = ""

        # 한글 헤더 생성
        korean_header = _align_text("인덱스", index_column_width) + _align_text(
            korean_name, data_column_width
        )
        result += korean_header + "\n"

        # 영문 헤더 생성
        english_header = _align_text("index", index_column_width) + _align_text(
            series_name, data_column_width
        )
        result += english_header + "\n"

        # 데이터 생성
        for idx, val in series_display.items():
            data_row = _align_text(str(idx), index_column_width) + _align_text(
                _format_value(val), data_column_width
            )
            result += data_row + "\n"

        return result.rstrip()

    else:
        raise ValueError(
            "out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다."
        )


# =============================================================================
# PANDAS EXTENSION: REGISTRATION FUNCTION
# =============================================================================

def set_pandas_extension(enable_head_override: bool = True) -> None:
    """pandas DataFrame/Series에 한글 컬럼 설명 기능을 추가합니다.
    
    Parameters
    ----------
    enable_head_override : bool, default False
        True면 head() 메서드를 head_att() 기능으로 대체합니다.
    
    Notes
    -----
    이 함수는 모듈 로드 시 자동으로 호출되므로 직접 호출할 필요가 없습니다.
    """
    # 원본 head 메서드 백업 (한 번만)
    if not hasattr(pd.DataFrame, '_original_head'):
        pd.DataFrame._original_head = pd.DataFrame.head
        pd.Series._original_head = pd.Series.head
    
    # 기본 기능
    for cls in [pd.DataFrame, pd.Series]:
        setattr(cls, "set_head_att", set_head_att)
        setattr(cls, "get_head_att", get_head_att)
        setattr(cls, "remove_head_att", remove_head_att)
        setattr(cls, "clear_head_att", clear_head_att)
    
    # DataFrame/Series별 출력 함수
    setattr(pd.DataFrame, "head_att", pd_head_att)
    setattr(pd.DataFrame, "print_head_att", print_head_att)
    setattr(pd.DataFrame, "_html_head_att", _html_head_att)
    setattr(pd.DataFrame, "_string_head_att", _string_head_att)
    setattr(pd.Series, "head_att", series_head_att)
    
    # head() 메서드 오버라이드
    if enable_head_override:
        setattr(pd.DataFrame, "head", pd_head_att)
        setattr(pd.Series, "head", series_head_att)
    else:
        # 원본 복원
        setattr(pd.DataFrame, "head", pd.DataFrame._original_head)
        setattr(pd.Series, "head", pd.Series._original_head)

# =============================================================================
# MAIN FUNCTION FOR TESTING
# =============================================================================
set_pandas_extension()

def main() -> None:
    """head_att 기능 테스트를 위한 메인 함수.

    DataFrame과 Series의 head_att 관련 기능들을 테스트합니다:
    - set_head_att: 컬럼 설명 설정
    - get_head_att: 컬럼 설명 조회
    - head_att: 한글 컬럼명과 함께 데이터 출력
    - remove_head_att: 컬럼 설명 삭제
    - clear_head_att: 모든 컬럼 설명 초기화
    """
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
