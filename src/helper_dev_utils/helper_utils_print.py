import os
import sys
import platform
import tempfile
import string
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import importlib.resources as resources
import inspect
import warnings
from pathlib import Path
from typing import Any, Optional, Union

# 조건부 상대 임포트: 패키지 또는 직접 실행 모두 지원
try:
    from . import helper_logger
except ImportError:
    import helper_logger

logger = helper_logger.get_auto_logger()

try:
    from dotenv import load_dotenv, dotenv_values
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
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

#_print = print  # 기본 _print 함수를 user_print로 저장

_print = logger.info  # logger의 info 메서드로 대체

def print_dir_tree(
    root: str,
    indent: str = "",
    max_file_list: Optional[int] = 3,
    max_dir_list: Optional[int] = 3,
) -> None:
    """디렉토리 트리 구조를 계층형(tree) 형식으로 출력.

    주어진 경로(root)부터 시작하여 재귀적으로 디렉토리와 파일을 트리 구조로
    표현하여 출력합니다. max_file_list, max_dir_list를 사용하여 표시 개수를
    제한할 수 있으며, 초과분은 "... dirs", "... files" 표시로 생략됩니다.

    Args:
        root (str): 탐색 시작 디렉토리 경로.
        indent (str, optional): 들여쓰기 문자열(재귀 호출 시 누적).
            Defaults to "".
        max_file_list (Optional[int], optional): 디렉토리별 파일 표시 최대 개수.
            None이면 전체 표시. Defaults to None.
        max_dir_list (Optional[int], optional): 디렉토리별 하위 디렉토리 표시
            최대 개수. None이면 전체 표시. Defaults to None.

    Returns:
        None

    Raises:
        Exception: 디렉토리 접근 실패 시 에러 메시지 출력 후 반환.
    """
    # 지정된 경로의 항목 목록 조회(정렬됨)
    try:
        entries = sorted(os.listdir(root))
    except Exception as e:
        _print(indent + f"[Error] {e}")
        return

    # 디렉토리와 파일 분리
    dirs = [e for e in entries if os.path.isdir(os.path.join(root, e))]
    files = [e for e in entries if not os.path.isdir(os.path.join(root, e))]
    if max_dir_list is not None and max_dir_list == 0:
        max_dir_list = None
    if max_file_list is not None and max_file_list == 0:
        max_file_list = None

    # 전체 개수 저장
    total_dirs = len(dirs)
    total_files = len(files)

    # 제한에 따라 표시할 항목 결정
    display_dirs = dirs if max_dir_list is None else dirs[:max_dir_list]
    display_files = files if max_file_list is None else files[:max_file_list]

    # 표시할 항목의 set 생성(빠른 조회)
    allowed_dirs = set(display_dirs)
    allowed_files = set(display_files)

    # 생략된 항목 여부 판단
    has_more_dirs = (max_dir_list is not None) and (total_dirs > max_dir_list)
    has_more_files = (max_file_list is not None) and (total_files > max_file_list)

    # 각 항목 순회 및 출력
    for entry in entries:
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            # 표시 제한에 의해 제외된 디렉토리는 건너뜀
            if entry not in allowed_dirs:
                continue

            # 디렉토리 이름 출력
            _print(indent + "|-- " + entry)

            # 디렉토리 내 파일 개수 계산 및 출력
            try:
                file_count = len([f for f in os.listdir(path)])
            except Exception:
                file_count = 0
            _print(indent + "   " + f"[데이터파일: {file_count}개]")

            # 재귀 호출로 하위 디렉토리 탐색
            # 들여쓰기와 제한값 동일하게 전달
            print_dir_tree(
                root=path,
                indent=indent + "   ",
                max_file_list=max_file_list,
                max_dir_list=max_dir_list,
            )
        else:
            # 표시 제한에 의해 제외된 파일은 건너뜀
            if entry not in allowed_files:
                continue
            _print(indent + "|-- " + entry)

    # 생략된 항목 표시
    if has_more_dirs:
        _print(indent + "   " + "... dirs")
    if has_more_files:
        _print(indent + "   " + "... files")
            

def print_json_tree(
    data: Any,
    indent: str = "",
    max_depth: int = 4,
    _depth: int = 0,
    list_count: int = 1,
    print_value: bool = True,
    limit_value_text: int = 100,
) -> None:
    """JSON/딕셔너리/리스트를 파이프(|--) 스타일 트리 형태로 출력.

    주어진 데이터 구조를 재귀적으로 탐색하여 계층형 트리로 출력합니다.
    리스트는 앞/뒤 list_count개씩만 표시하고 중간은 "..." 생략 처리합니다.
    max_depth를 초과하면 더 이상 탐색하지 않습니다.

    Args:
        data (Any): 출력할 데이터(dict, list, 또는 기본 타입).
        indent (str, optional): 들여쓰기 문자열(재귀 호출 시 누적).
            Defaults to "".
        max_depth (int, optional): 탐색할 최대 깊이. Defaults to 4.
        _depth (int, optional): 현재 재귀 깊이(내부 사용). Defaults to 0.
        list_count (int, optional): 리스트에서 앞/뒤로 표시할 항목 수.
            Defaults to 1.
        print_value (bool, optional): True이면 값도 출력, False이면 타입만
            표시. Defaults to True.
        limit_value_text (int, optional): 값 문자열의 최대 표시 길이.
            초과 시 "..."로 생략. Defaults to 100.

    Returns:
        None
    """
    # 최대 깊이 초과 시 재귀 중단
    if _depth > max_depth:
        return

    if isinstance(data, dict):
        # 딕셔너리 순회
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # 중첩된 컨테이너: 타입만 표시하고 재귀 호출
                _print(f"{indent}|-- {key}")
                print_json_tree(
                    value,
                    indent + "    ",
                    max_depth,
                    _depth + 1,
                    list_count,
                    print_value,
                    limit_value_text,
                )
            else:
                # 기본 값: 타입과 함께 표시
                if print_value:
                    vstr = str(value)
                    # 길이 초과 시 앞 30자만 표시
                    short = (
                        vstr
                        if len(vstr) < limit_value_text
                        else f"{vstr[:30]}..."
                    )
                    _print(f"{indent}|-- {key}({type(value).__name__}): {short}")
                else:
                    _print(f"{indent}|-- {key}({type(value).__name__})")

    elif isinstance(data, list):
        # 리스트 길이와 앞/뒤 표시 개수 계산
        n = int(list_count) if list_count is not None else 0
        L = len(data)

        # 빈 리스트 처리
        if L == 0:
            _print(f"{indent}|-- [list] (0 items)")
            return

        # 리스트가 충분히 길면 앞/뒤 n개만 보여주고 중간 생략
        if n > 0 and L > 2 * n:
            _print(f"{indent}|-- [list] ({L} items)")

            # 앞쪽 n개 항목 출력
            for i in range(0, n):
                item = data[i]
                if isinstance(item, (dict, list)):
                    _print(f"{indent}    |-- [{i}]")
                    print_json_tree(
                        item,
                        indent + "        ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                else:
                    if print_value:
                        vstr = str(item)
                        short = (
                            vstr
                            if len(vstr) < limit_value_text
                            else f"{vstr[:30]}..."
                        )
                        _print(
                            f"{indent}    |-- [{i}]({type(item).__name__}): {short}"
                        )
                    else:
                        _print(
                            f"{indent}    |-- [{i}]({type(item).__name__})"
                        )

            # 중간 생략 표시
            omitted = L - 2 * n
            _print(f"{indent}    |-- ... ({omitted} items omitted)")

            # 뒤쪽 n개 항목 출력
            for j in range(L - n, L):
                item = data[j]
                if isinstance(item, (dict, list)):
                    _print(f"{indent}    |-- [{j}]")
                    print_json_tree(
                        item,
                        indent + "        ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                else:
                    if print_value:
                        vstr = str(item)
                        short = (
                            vstr
                            if len(vstr) < limit_value_text
                            else f"{vstr[:30]}..."
                        )
                        _print(
                            f"{indent}    |-- [{j}]({type(item).__name__}): {short}"
                        )
                    else:
                        _print(
                            f"{indent}    |-- [{j}]({type(item).__name__})"
                        )

        else:
            # 리스트가 짧거나 list_count=0인 경우 전체 출력
            _print(f"{indent}|-- [list] ({L} items)")
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    _print(f"{indent}    |-- [{i}]")
                    print_json_tree(
                        item,
                        indent + "        ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                else:
                    if print_value:
                        vstr = str(item)
                        short = (
                            vstr
                            if len(vstr) < limit_value_text
                            else f"{vstr[:30]}..."
                        )
                        _print(
                            f"{indent}    |-- [{i}]({type(item).__name__}): {short}"
                        )
                    else:
                        _print(
                            f"{indent}    |-- [{i}]({type(item).__name__})"
                        )
    else:
        # 기본 타입(str, int, float 등) 처리
        if print_value:
            vstr = str(data)
            short = (
                vstr
                if len(vstr) < limit_value_text
                else f"{vstr[:30]}..."
            )
            _print(f"{indent}{type(data).__name__}: {short}")
        else:
            _print(f"{indent}{type(data).__name__}")

def print_dic_tree(
    dic_data: Any,
    indent: str = "",
    max_depth: int = 3,
    _depth: int = 0,
    list_count: int = 1,
    print_value: bool = True,
    limit_value_text: int = 100,
) -> None:
    """PyTorch Tensor/NumPy 배열/딕셔너리/리스트를 박스드로잉 스타일 트리로 출력.

    주어진 데이터 구조를 재귀적으로 탐색하여 ├─, │, └─ 문자를 사용한 git 트리
    스타일로 출력합니다. PyTorch Tensor와 NumPy ndarray의 shape/dtype을
    자동으로 감지하여 표시합니다. 리스트는 앞/뒤 list_count개씩만 표시하고
    중간은 "..." 생략 처리합니다.

    Args:
        dic_data (Any): 출력할 데이터(dict, list, tuple, Tensor, ndarray,
            또는 기본 타입).
        indent (str, optional): 들여쓰기 문자열(재귀 호출 시 누적).
            Defaults to "".
        max_depth (int, optional): 탐색할 최대 깊이. Defaults to 3.
        _depth (int, optional): 현재 재귀 깊이(내부 사용). Defaults to 0.
        list_count (int, optional): 리스트/튜플에서 앞/뒤로 표시할 항목 수.
            Defaults to 1.
        print_value (bool, optional): True이면 값도 출력, False이면 타입과
            shape/dtype만 표시. Defaults to True.
        limit_value_text (int, optional): 값 문자열의 최대 표시 길이.
            초과 시 "..."로 생략. Defaults to 100.

    Returns:
        None

    Note:
        - Tensor/ndarray 감지를 위해 TORCH_AVAILABLE, NUMPY_AVAILABLE 플래그
          사용
        - 박스드로잉 문자: ├─(분기), │ (연결), └─(끝)
    """
    # 최대 깊이 초과 시 재귀 중단
    if _depth > max_depth:
        return

    if isinstance(dic_data, dict):
        # 딕셔너리 순회
        for key, value in dic_data.items():
            if isinstance(value, (dict, list, tuple)):
                # 중첩 컨테이너: 타입만 표시하고 재귀 호출
                _print(f"{indent}├─ {key} [{type(value).__name__}]")
                print_dic_tree(
                    value,
                    indent + "│  ",
                    max_depth,
                    _depth + 1,
                    list_count,
                    print_value,
                    limit_value_text,
                )
            elif TORCH_AVAILABLE and torch.is_tensor(value):
                # PyTorch Tensor: shape와 dtype 표시
                shape = tuple(value.shape)
                dtype = str(value.dtype)
                if print_value:
                    preview = str(value)
                    preview_str = (
                        preview[:limit_value_text]
                        + ("..." if len(preview) > limit_value_text else "")
                    )
                    _print(
                        f"{indent}├─ {key} [Tensor] shape={shape} dtype={dtype}"
                    )
                    _print(f"{indent}│  └─ {preview_str}")
                else:
                    _print(
                        f"{indent}├─ {key} [Tensor] shape={shape} dtype={dtype}"
                    )
            elif NUMPY_AVAILABLE and isinstance(value, np.ndarray):
                # NumPy 배열: shape와 dtype 표시
                shape = value.shape
                dtype = value.dtype
                if print_value:
                    preview = str(value)
                    preview_str = (
                        preview[:limit_value_text]
                        + ("..." if len(preview) > limit_value_text else "")
                    )
                    _print(
                        f"{indent}├─ {key} [ndarray] shape={shape} dtype={dtype}"
                    )
                    _print(f"{indent}│  └─ {preview_str}")
                else:
                    _print(
                        f"{indent}├─ {key} [ndarray] shape={shape} dtype={dtype}"
                    )
            else:
                # 기본 값: 타입과 함께 표시
                if print_value:
                    val_str = str(value)
                    short = (
                        val_str[:limit_value_text]
                        + ("..." if len(val_str) > limit_value_text else "")
                    )
                    _print(f"{indent}├─ {key} [{type(value).__name__}]: {short}")
                else:
                    _print(f"{indent}├─ {key} [{type(value).__name__}]")

    elif isinstance(dic_data, (list, tuple)):
        # 리스트/튜플 길이와 앞/뒤 표시 개수 계산
        n = int(list_count) if list_count is not None else 0
        L = len(dic_data)

        # 빈 리스트/튜플 처리
        if L == 0:
            _print(f"{indent}└─ [{type(dic_data).__name__}] (0 items)")
            return

        # 리스트가 충분히 길면 앞/뒤 n개만 보여주고 중간 생략
        if n > 0 and L > 2 * n:
            # 앞쪽 n개 항목 출력
            for i in range(0, n):
                item = dic_data[i]
                if isinstance(item, (dict, list, tuple)):
                    _print(f"{indent}├─ [{i}] [{type(item).__name__}]")
                    print_dic_tree(
                        item,
                        indent + "│  ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                elif TORCH_AVAILABLE and torch.is_tensor(item):
                    shape = tuple(item.shape)
                    dtype = str(item.dtype)
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [Tensor] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [Tensor] shape={shape} dtype={dtype}"
                        )
                elif NUMPY_AVAILABLE and isinstance(item, np.ndarray):
                    shape = item.shape
                    dtype = item.dtype
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [ndarray] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [ndarray] shape={shape} dtype={dtype}"
                        )
                else:
                    if print_value:
                        val_str = str(item)
                        short = (
                            val_str[:limit_value_text]
                            + ("..." if len(val_str) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [{type(item).__name__}]: {short}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [{type(item).__name__}]"
                        )

            # 중간 생략 표시
            omitted = L - 2 * n
            _print(f"{indent}├─ ... ({omitted} items omitted)")

            # 뒤쪽 n개 항목 출력
            for j in range(L - n, L):
                item = dic_data[j]
                if isinstance(item, (dict, list, tuple)):
                    _print(f"{indent}├─ [{j}] [{type(item).__name__}]")
                    print_dic_tree(
                        item,
                        indent + "│  ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                elif TORCH_AVAILABLE and torch.is_tensor(item):
                    shape = tuple(item.shape)
                    dtype = str(item.dtype)
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{j}] [Tensor] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{j}] [Tensor] shape={shape} dtype={dtype}"
                        )
                elif NUMPY_AVAILABLE and isinstance(item, np.ndarray):
                    shape = item.shape
                    dtype = item.dtype
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{j}] [ndarray] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{j}] [ndarray] shape={shape} dtype={dtype}"
                        )
                else:
                    if print_value:
                        val_str = str(item)
                        short = (
                            val_str[:limit_value_text]
                            + ("..." if len(val_str) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{j}] [{type(item).__name__}]: {short}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{j}] [{type(item).__name__}]"
                        )
        else:
            # 리스트가 짧거나 list_count=0인 경우 전체 출력
            for i, item in enumerate(dic_data):
                if isinstance(item, (dict, list, tuple)):
                    _print(f"{indent}├─ [{i}] [{type(item).__name__}]")
                    print_dic_tree(
                        item,
                        indent + "│  ",
                        max_depth,
                        _depth + 1,
                        list_count,
                        print_value,
                        limit_value_text,
                    )
                elif TORCH_AVAILABLE and torch.is_tensor(item):
                    shape = tuple(item.shape)
                    dtype = str(item.dtype)
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [Tensor] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [Tensor] shape={shape} dtype={dtype}"
                        )
                elif NUMPY_AVAILABLE and isinstance(item, np.ndarray):
                    shape = item.shape
                    dtype = item.dtype
                    if print_value:
                        preview = str(item)
                        preview_str = (
                            preview[:limit_value_text]
                            + ("..." if len(preview) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [ndarray] shape={shape} dtype={dtype}: {preview_str}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [ndarray] shape={shape} dtype={dtype}"
                        )
                else:
                    if print_value:
                        val_str = str(item)
                        short = (
                            val_str[:limit_value_text]
                            + ("..." if len(val_str) > limit_value_text else "")
                        )
                        _print(
                            f"{indent}├─ [{i}] [{type(item).__name__}]: {short}"
                        )
                    else:
                        _print(
                            f"{indent}├─ [{i}] [{type(item).__name__}]"
                        )

    elif TORCH_AVAILABLE and torch.is_tensor(dic_data):
        # 단일 Tensor 처리
        shape = tuple(dic_data.shape)
        dtype = str(dic_data.dtype)
        if print_value:
            preview = str(dic_data)
            preview_str = (
                preview[:limit_value_text]
                + ("..." if len(preview) > limit_value_text else "")
            )
            _print(f"{indent}└─ Tensor shape={shape} dtype={dtype}")
            _print(f"{indent}   {preview_str}")
        else:
            _print(f"{indent}└─ Tensor shape={shape} dtype={dtype}")

    elif NUMPY_AVAILABLE and isinstance(dic_data, np.ndarray):
        # 단일 NumPy 배열 처리
        shape = dic_data.shape
        dtype = dic_data.dtype
        if print_value:
            preview = str(dic_data)
            preview_str = (
                preview[:limit_value_text]
                + ("..." if len(preview) > limit_value_text else "")
            )
            _print(f"{indent}└─ ndarray shape={shape} dtype={dtype}")
            _print(f"{indent}   {preview_str}")
        else:
            _print(f"{indent}└─ ndarray shape={shape} dtype={dtype}")

    else:
        # 기본 타입(str, int, float 등) 처리
        if print_value:
            val_str = str(dic_data)
            short = (
                val_str[:limit_value_text]
                + ("..." if len(val_str) > limit_value_text else "")
            )
            _print(f"{indent}└─ {type(dic_data).__name__}: {short}")
        else:
            _print(f"{indent}└─ {type(dic_data).__name__}")


if __name__ == "__main__":
    """Main test: 디렉토리 트리 및 JSON 트리 구조 출력 데모"""
    
    # 현재 디렉토리 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    _print("=" * 60)
    _print("MAIN TEST: helper_utils_print 데모")
    _print("=" * 60)
    
    # 1. print_dir_tree 테스트 (상위 디렉토리 출력)
    _print("[테스트 1] print_dir_tree - 부모 디렉토리 구조")
    _print(f"경로: {parent_dir}\n")
    print_dir_tree(parent_dir, max_file_list=3, max_dir_list=3)
    
    # 2. print_json_tree 테스트
    _print("=" * 60)
    _print("[테스트 2] print_json_tree - 샘플 딕셔너리 구조")
    _print("=" * 60)
    sample_dict = {
        "name": "test_data",
        "version": 1.0,
        "items": [
            {"id": 1, "label": "item_a"},
            {"id": 2, "label": "item_b"},
            {"id": 3, "label": "item_c"}
        ],
        "metadata": {
            "created": "2025-12-05",
            "author": "test_user"
        }
    }
    print_json_tree(sample_dict, max_depth=3, list_count=1, print_value=True)
    
    _print("=" * 60)
    _print("MAIN TEST 완료")
    _print("=" * 60)
