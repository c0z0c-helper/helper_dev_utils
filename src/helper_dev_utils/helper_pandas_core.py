"""
helper_pandas_core 모듈

pandas 확장 기능의 핵심 유틸리티를 제공합니다.
- 텍스트 폭 계산 (한글/영문)
- 값 포맷팅
- 텍스트 정렬
- 컬럼 폭 계산
- 컬럼 설명 관리 (set/get/remove/clear)
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


# =============================================================================
# TEXT FORMATTING UTILITIES
# =============================================================================


def get_text_width(text: Any) -> int:
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


def format_value(value: Any) -> str:
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


def align_text(text: Any, width: int, align: str = "left") -> str:
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
    current_width = get_text_width(text_str)
    padding = max(0, width - current_width)

    if align == "right":
        return " " * padding + text_str
    elif align == "center":
        left_padding = padding // 2
        right_padding = padding - left_padding
        return " " * left_padding + text_str + " " * right_padding
    else:  # left (default)
        return text_str + " " * padding


def calculate_column_widths(df_display: pd.DataFrame, labels: Dict[str, str]) -> List[int]:
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
        max_index_width = max(get_text_width(str(idx)) for idx in df_display.index)

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
            max_data_width = max(get_text_width(format_value(val)) for val in df_display[col])

        # 각 요소의 최대 폭 계산
        max_width = max(
            get_text_width(korean_name),
            get_text_width(english_name),
            max_data_width,
        )

        # pandas 스타일: 최소 여유 공간 (1칸)
        column_width = max_width + 1
        widths.append(column_width)

    return widths


# =============================================================================
# COLUMN DESCRIPTION MANAGEMENT
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
