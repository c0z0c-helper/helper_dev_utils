"""
helper_pandas_display 모듈

pandas DataFrame/Series의 출력 기능을 제공합니다.
- DataFrame 출력 (print/html/string)
- Series 출력 (print/html/string)
- 한글 컬럼 설명 지원
"""

from typing import Any, Dict, Optional, Union

import pandas as pd

try:
    from . import helper_pandas_core as core
except ImportError:
    import helper_pandas_core as core

try:
    import IPython
    from IPython.display import HTML

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False


# =============================================================================
# DATAFRAME DISPLAY FUNCTIONS
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
            if hasattr(pd.DataFrame, "_head"):
                df_display = pd.DataFrame._head(self, rows)
            else:
                df_display = self.iloc[:rows]
    else:
        # 원본 head() 사용 (재귀 방지)
        if hasattr(pd.DataFrame, "_head"):
            df_display = pd.DataFrame._head(self, 5)
        else:
            df_display = self.iloc[:5]

    # 보조 컬럼명 출력 조건
    # 1. column_descriptions가 완전히 비어 있으면 보조 컬럼명 출력하지 않음
    # 2. column_descriptions가 비어 있지 않고 특정 컬럼만 비어 있으면 기존과 동일하게 처리
    if not labels:
        # 보조 컬럼명 없이 오리지널 컬럼명만 한 번 출력
        def print_original_only(df_display):
            # 영문 헤더 출력 (오른쪽 정렬)
            column_widths = core.calculate_column_widths(df_display, {})
            index_width = column_widths[0]
            data_widths = column_widths[1:]
            english_parts = []
            english_parts.append(core.align_text("", index_width, "right"))
            for col, width in zip(df_display.columns, data_widths):
                english_parts.append(core.align_text(col, width, "right"))
            print("".join(english_parts))
            # 데이터 출력
            for idx, row in df_display.iterrows():
                row_parts = []
                row_parts.append(core.align_text(str(idx), index_width, "right"))
                for val, width in zip(row, data_widths):
                    row_parts.append(core.align_text(core.format_value(val), width, "right"))
                print("".join(row_parts))

        if out is None or out.lower() == "print":
            print_original_only(df_display)
            return None
        elif out.lower() == "html":
            # HTML 헤더는 오리지널 컬럼명만 출력
            df_copy = df_display.copy()
            # 실수형 값들을 포맷팅
            for col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(core.format_value)
            df_copy.columns = list(df_display.columns)
            if IPYTHON_AVAILABLE:
                return HTML(df_copy.to_html(escape=False))
            else:
                return df_copy.to_html(escape=False)
        elif out.lower() in ["str", "string"]:
            # 문자열 형태로 오리지널 컬럼명만 출력
            column_widths = core.calculate_column_widths(df_display, {})
            result = ""
            english_row = ""
            for i, col in enumerate(df_display.columns):
                english_row += core.align_text(col, column_widths[i])
            result += english_row + "\n"
            for idx, row in df_display.iterrows():
                data_row = ""
                for i, val in enumerate(row):
                    if i == 0:
                        text = str(idx)
                        formatted_val = core.format_value(val)
                        data_row += core.align_text(
                            text, column_widths[i] - core.get_text_width(formatted_val)
                        )
                        data_row += formatted_val
                    else:
                        data_row += core.align_text(core.format_value(val), column_widths[i])
                result += data_row + "\n"
            return result.rstrip()
        else:
            raise ValueError("out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다.")
    else:
        # 기존 로직 (보조 컬럼명 일부만 비어 있으면 기존과 동일하게 처리)
        if out is None or out.lower() == "print":
            return self.print_head_att(df_display, labels)
        elif out.lower() == "html":
            return self._html_head_att(df_display, labels)
        elif out.lower() in ["str", "string"]:
            return self._string_head_att(df_display, labels)
        else:
            raise ValueError("out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다.")


def print_head_att(self, df_display: pd.DataFrame, labels: Dict[str, str]) -> None:
    """print 형태로 출력 (pandas 기본 스타일).

    Parameters
    ----------
    df_display : pd.DataFrame
        표시할 DataFrame.
    labels : dict of {str: str}
        컬럼명과 한글 설명의 매핑.
    """
    column_widths = core.calculate_column_widths(df_display, labels)

    # 첫 번째 부분은 인덱스용
    index_width = column_widths[0]
    data_widths = column_widths[1:]

    # 한글 헤더 출력 (오른쪽 정렬)
    korean_parts = []
    korean_parts.append(core.align_text("", index_width, "right"))  # 인덱스 헤더는 빈공간
    for col, width in zip(df_display.columns, data_widths):
        korean_name = labels.get(col, col)
        korean_parts.append(core.align_text(korean_name, width, "right"))
    print("".join(korean_parts))

    # 영문 헤더 출력 (오른쪽 정렬)
    english_parts = []
    english_parts.append(core.align_text("", index_width, "right"))  # 인덱스 헤더는 빈공간
    for col, width in zip(df_display.columns, data_widths):
        english_parts.append(core.align_text(col, width, "right"))
    print("".join(english_parts))

    # 데이터 출력 (모두 오른쪽 정렬 - pandas 기본 스타일)
    for idx, row in df_display.iterrows():
        row_parts = []
        # 인덱스 출력 (오른쪽 정렬)
        row_parts.append(core.align_text(str(idx), index_width, "right"))
        # 데이터 출력 (오른쪽 정렬)
        for val, width in zip(row, data_widths):
            row_parts.append(core.align_text(core.format_value(val), width, "right"))
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
        df_copy[col] = df_copy[col].apply(core.format_value)
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
    column_widths = core.calculate_column_widths(df_display, labels)

    result = ""

    # 한글 헤더 생성
    korean_row = ""
    for i, col in enumerate(df_display.columns):
        korean_name = labels.get(col, col)
        korean_row += core.align_text(korean_name, column_widths[i])
    result += korean_row + "\n"

    # 영문 헤더 생성
    english_row = ""
    for i, col in enumerate(df_display.columns):
        english_row += core.align_text(col, column_widths[i])
    result += english_row + "\n"

    # 데이터 생성
    for idx, row in df_display.iterrows():
        data_row = ""
        for i, val in enumerate(row):
            if i == 0:
                text = str(idx)
                formatted_val = core.format_value(val)
                data_row += core.align_text(
                    text, column_widths[i] - core.get_text_width(formatted_val)
                )
                data_row += formatted_val
            else:
                data_row += core.align_text(core.format_value(val), column_widths[i])
        result += data_row + "\n"

    return result.rstrip()


# =============================================================================
# SERIES DISPLAY FUNCTIONS
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
            if hasattr(pd.Series, "_head"):
                series_display = pd.Series._head(self, rows)
            else:
                series_display = self.iloc[:rows]
    else:
        # 원본 head() 사용 (재귀 방지)
        if hasattr(pd.Series, "_head"):
            series_display = pd.Series._head(self, 5)
        else:
            series_display = self.iloc[:5]

    series_name = self.name if self.name is not None else "Series"
    korean_name = labels.get(series_name, series_name)

    if out is None or out.lower() == "print":
        # 인덱스 최대 폭 계산
        index_widths = [core.get_text_width(str(idx)) for idx in series_display.index]
        max_index_width = max(index_widths) if index_widths else 0

        # 데이터 최대 폭 계산
        data_widths = [core.get_text_width(core.format_value(val)) for val in series_display]
        max_data_width = max(data_widths) if data_widths else 0

        # 헤더 폭 계산
        korean_header_width = core.get_text_width(korean_name)
        english_header_width = core.get_text_width(series_name)

        # 각 컬럼의 최대 폭 결정
        index_column_width = max(max_index_width, 5) + 2
        data_column_width = max(max_data_width, korean_header_width, english_header_width) + 2

        # 헤더 출력
        korean_header = core.align_text("인덱스", index_column_width) + core.align_text(
            korean_name, data_column_width
        )
        print(korean_header)

        english_header = core.align_text("index", index_column_width) + core.align_text(
            series_name, data_column_width
        )
        print(english_header)

        # 데이터 출력
        for idx, val in series_display.items():
            data_row = core.align_text(str(idx), index_column_width) + core.align_text(
                core.format_value(val), data_column_width
            )
            print(data_row)

        return None

    elif out.lower() == "html":
        df = series_display.to_frame()
        # 실수형 값들을 포맷팅 - dtype 불일치 방지를 위해 먼저 object로 변환
        df = df.astype({df.columns[0]: "object"})
        df.iloc[:, 0] = df.iloc[:, 0].apply(core.format_value)

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
        index_widths = [core.get_text_width(str(idx)) for idx in series_display.index]
        max_index_width = max(index_widths) if index_widths else 0

        # 데이터 최대 폭 계산
        data_widths = [core.get_text_width(core.format_value(val)) for val in series_display]
        max_data_width = max(data_widths) if data_widths else 0

        # 헤더 폭 계산
        korean_header_width = core.get_text_width(korean_name)
        english_header_width = core.get_text_width(series_name)

        # 각 컬럼의 최대 폭 결정
        index_column_width = (
            max(max_index_width, core.get_text_width("인덱스"), core.get_text_width("index")) + 2
        )
        data_column_width = max(max_data_width, korean_header_width, english_header_width) + 2

        result = ""

        # 한글 헤더 생성
        korean_header = core.align_text("인덱스", index_column_width) + core.align_text(
            korean_name, data_column_width
        )
        result += korean_header + "\n"

        # 영문 헤더 생성
        english_header = core.align_text("index", index_column_width) + core.align_text(
            series_name, data_column_width
        )
        result += english_header + "\n"

        # 데이터 생성
        for idx, val in series_display.items():
            data_row = core.align_text(str(idx), index_column_width) + core.align_text(
                core.format_value(val), data_column_width
            )
            result += data_row + "\n"

        return result.rstrip()

    else:
        raise ValueError("out 옵션은 'html', 'print', 'str', 'string' 중 하나여야 합니다.")
