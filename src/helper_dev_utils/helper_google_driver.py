"""
Google Drive 경로 관리 유틸리티

로컬/Colab 환경에서 Google Drive 경로를 자동으로 관리합니다.
"""

import os
from pathlib import Path
from typing import Optional, Union

try:
    from . import helper_logger
    from . import helper_path_finder
    from . import helper_colab_auth
except ImportError:
    import helper_logger
    import helper_path_finder
    import helper_colab_auth

try:
    import google.colab
    from google.colab import drive

    IS_COLAB = True
except ImportError:
    IS_COLAB = False


# 전역 변수 초기화
_google_driver_local = helper_path_finder.find_google_drive()
_google_driver_colab = r"/content/drive/MyDrive"


def google_driver(
    google_driver_local: str | None = None,
    google_driver_colab: str | None = None,
    auto_mount: bool = True,
) -> str:
    """
    로컬 또는 Colab 환경에 맞는 Google Drive 루트 경로를 반환합니다.

    Parameters
    ----------
    google_driver_local : str | None
        로컬 환경에서 사용할 드라이브 경로
    google_driver_colab : str | None
        Colab 환경에서 사용할 드라이브 경로
    auto_mount : bool
        Colab 환경에서 자동 마운트 여부 (기본값: True)

    Returns
    -------
    str
        현재 실행 환경에 맞는 드라이브 루트 경로
    """
    logger = helper_logger.get_auto_logger()
    global _google_driver_local, _google_driver_colab

    if google_driver_local is not None:
        _google_driver_local = google_driver_local
        logger.info("Updated _google_driver_local: %s", _google_driver_local)
    if google_driver_colab is not None:
        _google_driver_colab = google_driver_colab
        logger.info("Updated _google_driver_colab: %s", _google_driver_colab)

    if IS_COLAB:
        if auto_mount:
            try:
                helper_colab_auth._auto_mount_drive()
            except Exception:
                my_drive_path = os.path.join("/content/drive", "MyDrive")
                if not os.path.exists(my_drive_path):
                    try:
                        logger.info("Mounting Google Drive...")
                        drive.mount("/content/drive", force_remount=False)
                        logger.info("Drive mounted successfully")
                    except Exception as e:
                        logger.warning("Failed to mount drive: %s", e)
        return _google_driver_colab
    return _google_driver_local


def google_driver_path(
    *subpaths: Union[str, os.PathLike, None],
    create: bool = True,
    validate: bool = True,
    allow_escape: bool = False,
    google_driver_local: Optional[str] = None,
    google_driver_colab: Optional[str] = None,
) -> str:
    """
    google_driver() 루트와 하위 경로들을 결합하여 절대 경로를 반환합니다.

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
    google_driver_local : Optional[str]
        로컬 환경용 루트 경로
    google_driver_colab : Optional[str]
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
    base_path = google_driver(
        google_driver_local=google_driver_local, google_driver_colab=google_driver_colab
    )
    base = Path(base_path).resolve(strict=False)
    logger.debug("google_driver_path base: %s", base)

    processed_subpaths = []
    for sp in subpaths:
        if sp is None:
            continue
        if isinstance(sp, (str, os.PathLike)):
            processed_subpaths.append(str(sp))
        else:
            raise TypeError(f"Subpath must be str or os.PathLike, got {type(sp).__name__}")

    if processed_subpaths and os.path.isabs(processed_subpaths[0]):
        start_path = Path(processed_subpaths[0]).resolve(strict=False)
        remaining_subpaths = processed_subpaths[1:]
        logger.debug("First subpath is absolute, using as start: %s", start_path)
    else:
        start_path = base
        remaining_subpaths = processed_subpaths

    if remaining_subpaths:
        result_path = start_path.joinpath(*remaining_subpaths).resolve(strict=False)
    else:
        result_path = start_path

    if not allow_escape:
        is_relative = False
        if hasattr(result_path, "is_relative_to"):
            is_relative = result_path.is_relative_to(start_path)
        else:
            try:
                result_path.relative_to(start_path)
                is_relative = True
            except ValueError:
                is_relative = False

        if not is_relative:
            logger.error("Path escape detected: %s is not relative to %s", result_path, start_path)
            raise ValueError(
                f"Resulting path '{result_path}' escapes start path '{start_path}'. "
                f"Set allow_escape=True to override this check."
            )

    logger.debug("google_driver_path result (before create/validate): %s", result_path)

    if create:
        try:
            result_path.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", result_path)
        except (OSError, PermissionError) as e:
            logger.error("Failed to create directory '%s': %s", result_path, e)
            raise

    if validate:
        if not result_path.exists():
            logger.error("Path does not exist: %s", result_path)
            raise FileNotFoundError(f"Path does not exist: {result_path}")
        logger.debug("Path validation passed: %s", result_path)

    logger.debug("google_driver_path final: %s", result_path)
    return str(result_path)


def empty_drive_trash(force: bool = False) -> dict:
    """
    Google Drive 휴지통을 비웁니다.

    Parameters
    ----------
    force : bool
        확인 없이 휴지통을 비울지 여부 (기본값: False)

    Returns
    -------
    dict
        결과 정보 {'success': bool, 'message': str}

    Raises
    ------
    RuntimeError
        Colab 환경이 아닌 경우
    ImportError
        필수 라이브러리가 없는 경우

    Examples
    --------
    >>> from helper_dev_utils import empty_drive_trash
    >>> result = empty_drive_trash(force=True)
    >>> print(result['message'])
    """
    logger = helper_logger.get_auto_logger()

    if not IS_COLAB:
        raise RuntimeError("empty_drive_trash() is only available in Google Colab environment")

    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        logger.error("googleapiclient not found: %s", e)
        raise ImportError(
            "google-api-python-client is required. "
            "Install with: pip install google-api-python-client"
        ) from e

    try:
        creds, _ = helper_colab_auth.google_authenticate()
        service = build("drive", "v3", credentials=creds)

        if not force:
            logger.warning("휴지통을 비우려면 force=True를 설정하세요")
            return {"success": False, "message": "Confirmation required. Set force=True"}

        logger.info("Google Drive 휴지통 비우는 중...")
        service.files().emptyTrash().execute()
        logger.info("휴지통이 성공적으로 비워졌습니다")

        return {"success": True, "message": "Trash emptied successfully"}

    except Exception as e:
        logger.error("휴지통 비우기 실패: %s", e)
        return {"success": False, "message": f"Failed to empty trash: {e}"}
