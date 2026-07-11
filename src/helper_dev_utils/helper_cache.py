"""
캐시 경로 관리 유틸리티

로컬/Colab 환경에서 캐시 디렉토리 경로를 자동으로 관리합니다.
"""

import os
from pathlib import Path
from typing import Optional, Union

try:
    from . import helper_logger
    from . import helper_path_finder
except ImportError:
    import helper_logger
    import helper_path_finder

try:
    import google.colab

    IS_COLAB = True
except ImportError:
    IS_COLAB = False


# 전역 변수 초기화
_cache_local = helper_path_finder.find_cache_root()
_cache_colab = r"/content/cache/.cache"


def cache(cache_local: Optional[str] = None, cache_colab: Optional[str] = None) -> str:
    """
    로컬 또는 Colab 환경에 맞는 캐시 루트 경로를 반환합니다.

    Parameters
    ----------
    cache_local : Optional[str]
        로컬 환경에서 사용할 캐시 경로
    cache_colab : Optional[str]
        Colab 환경에서 사용할 캐시 경로

    Returns
    -------
    str
        현재 실행 환경에 맞는 캐시 루트 경로
    """
    logger = helper_logger.get_auto_logger()
    global _cache_local, _cache_colab

    if cache_local is not None:
        _cache_local = cache_local
        logger.info("Updated _cache_local: %s", _cache_local)
    if cache_colab is not None:
        _cache_colab = cache_colab
        logger.info("Updated _cache_colab: %s", _cache_colab)

    if IS_COLAB:
        return _cache_colab
    return _cache_local


def cache_path(
    *subpaths: Union[str, os.PathLike, None],
    create: bool = True,
    validate: bool = True,
    allow_escape: bool = False,
    cache_local: Optional[str] = None,
    cache_colab: Optional[str] = None,
) -> str:
    """
    cache() 루트와 하위 경로들을 결합하여 절대 경로를 반환합니다.

    Parameters
    ----------
    *subpaths : Union[str, os.PathLike, None]
        결합할 하위 경로 컴포넌트들
    create : bool
        디렉토리 생성 여부 (기본값: True)
    validate : bool
        경로 존재 검증 여부 (기본값: True)
    allow_escape : bool
        루트 탈출 허용 여부 (기본값: False)
    cache_local : Optional[str]
        로컬 환경용 루트 경로
    cache_colab : Optional[str]
        Colab 환경용 루트 경로

    Returns
    -------
    str
        정규화된 절대 경로 문자열

    Raises
    ------
    TypeError
        subpath 타입 오류
    ValueError
        경로 탈출 감지
    FileNotFoundError
        경로 존재하지 않음
    OSError, PermissionError
        디렉토리 생성 실패
    """
    logger = helper_logger.get_auto_logger()
    base_path = cache(cache_local=cache_local, cache_colab=cache_colab)
    base = Path(base_path).resolve(strict=False)
    logger.debug("cache_path base: %s", base)

    processed_subpaths = []
    for sp in subpaths:
        if sp is None:
            continue
        if isinstance(sp, (str, os.PathLike)):
            processed_subpaths.append(str(sp))
        else:
            raise TypeError(f"Subpath must be str or os.PathLike, got {type(sp).__name__}")

    # 절대경로인 경우 base 무시
    if processed_subpaths and os.path.isabs(processed_subpaths[0]):
        result_path = Path(processed_subpaths[0]).resolve(strict=False)
        logger.info("First subpath is absolute, returning (escape check skipped): %s", result_path)

        if create:
            try:
                result_path.mkdir(parents=True, exist_ok=True)
                logger.debug("Directory created: %s", result_path)
            except (OSError, PermissionError) as e:
                logger.error("Failed to create directory %s: %s", result_path, e)
                raise

        if validate:
            if not result_path.exists():
                logger.error("Validation failed: path does not exist: %s", result_path)
                raise FileNotFoundError(f"Path does not exist: {result_path}")
            logger.debug("Path validation passed: %s", result_path)

        return str(result_path)

    # 상대 경로: base와 결합
    if processed_subpaths:
        result_path = base.joinpath(*processed_subpaths).resolve(strict=False)
    else:
        result_path = base

    if not allow_escape:
        is_relative = False
        if hasattr(result_path, "is_relative_to"):
            is_relative = result_path.is_relative_to(base)
        else:
            try:
                result_path.relative_to(base)
                is_relative = True
            except ValueError:
                is_relative = False

        if not is_relative:
            logger.error("Path escape detected: %s is not relative to %s", result_path, base)
            raise ValueError(
                f"Resulting path '{result_path}' escapes cache base '{base}'. "
                f"Set allow_escape=True to override this check."
            )

    logger.debug("cache_path result (before create/validate): %s", result_path)

    if create:
        try:
            result_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Directory created: %s", result_path)
        except (OSError, PermissionError) as e:
            logger.error("Failed to create directory %s: %s", result_path, e)
            raise

    if validate:
        if not result_path.exists():
            logger.error("Validation failed: path does not exist: %s", result_path)
            raise FileNotFoundError(f"Path does not exist: {result_path}")
        logger.debug("Path validation passed: %s", result_path)

    return str(result_path)
