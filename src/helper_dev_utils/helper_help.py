"""
함수 및 메소드 도움말 검색 유틸리티
"""

import inspect
from typing import Any, Optional


def helper_help(fdn: Any) -> None:
    """입력된 함수 또는 메서드의 도움말(시그니처 + docstring)을 출력한다.

    Parameters
    ----------
    fdn : object
        도움말을 확인할 함수 또는 메서드 객체.

    Examples
    --------
    >>> from helper_dev_utils import get_logger
    >>> helper_help(get_logger)
    """
    name = getattr(fdn, "__qualname__", getattr(fdn, "__name__", repr(fdn)))

    try:
        sig = inspect.signature(fdn)
        sig_str = f"{name}{sig}"
    except (ValueError, TypeError):
        sig_str = name

    doc = inspect.getdoc(fdn) or "(docstring 없음)"

    print(f"Signature : {sig_str}")
    print(f"Docstring :\n{doc}")


def helper_search(lbn: object, query: Optional[str] = None) -> None:
    """입력된 모듈에서 사용 가능한 함수/클래스 중 이름에 query가 포함된 것을 출력한다.

    Parameters
    ----------
    lbn : object
        검색 대상 모듈 또는 패키지 객체.
    query : str, optional
        함수/클래스 이름에서 검색할 문자열. None이면 전체 목록을 출력한다.

    Examples
    --------
    >>> import helper_dev_utils
    >>> helper_search(helper_dev_utils, "logger")
    """
    members = inspect.getmembers(
        lbn, predicate=lambda obj: inspect.isfunction(obj) or inspect.isclass(obj)
    )

    q = query.lower() if query else None
    results = [name for name, _ in members if q is None or q in name.lower()]

    if not results:
        print(f"'{query}' 에 해당하는 항목이 없습니다.")
        return

    label = f"'{query}'" if query else "전체"
    print(f"[{getattr(lbn, '__name__', repr(lbn))}] {label} 검색 결과 ({len(results)}건)")
    for name in results:
        print(f"  - {name}")


if __name__ == "__main__":
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- helper_help 예시 ---
    print("=" * 60)
    print("[helper_help] pandas DataFrame.groupby")
    print("=" * 60)
    helper_help(pd.DataFrame.groupby)

    print()
    print("=" * 60)
    print("[helper_help] matplotlib pyplot.plot")
    print("=" * 60)
    helper_help(plt.plot)

    # --- helper_search 예시 ---
    print()
    print("=" * 60)
    print("[helper_search] pandas 모듈에서 'merge' 검색")
    print("=" * 60)
    helper_search(pd, "merge")

    print()
    print("=" * 60)
    print("[helper_search] matplotlib.pyplot 모듈에서 'plot' 검색")
    print("=" * 60)
    helper_search(plt, "plot")
