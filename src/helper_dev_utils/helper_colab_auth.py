"""
Google Colab 인증 및 마운트 유틸리티

주요 기능:
- Google Drive 자동 마운트
- Google 서비스 인증
- Colab Secrets 접근
"""

import os
from typing import Any, Optional, Tuple, List

try:
    from . import helper_logger
except ImportError:
    import helper_logger

try:
    import google.colab
    from google.colab import drive

    IS_COLAB = True
except ImportError:
    IS_COLAB = False


# 마운트 상태 추적 (모듈 레벨)
_drive_mounted = False


def _auto_mount_drive(mount_point: str = "/content/drive", force_remount: bool = False) -> bool:
    """
    Colab 환경에서 Google Drive를 자동으로 마운트합니다.

    Parameters
    ----------
    mount_point : str
        드라이브 마운트 지점 (기본값: "/content/drive")
    force_remount : bool
        강제 재마운트 여부 (기본값: False)

    Returns
    -------
    bool
        마운트 성공 여부
    """
    global _drive_mounted
    logger = helper_logger.get_auto_logger()

    if not IS_COLAB:
        logger.debug("Not in Colab environment, skipping drive mount")
        return False

    # 이미 마운트된 경우
    if _drive_mounted and not force_remount:
        logger.debug("Drive already mounted")
        return True

    # 물리적 마운트 확인
    my_drive_path = os.path.join(mount_point, "MyDrive")
    if os.path.exists(my_drive_path) and not force_remount:
        logger.debug("Drive already mounted at %s", mount_point)
        _drive_mounted = True
        return True

    # 마운트 시도
    try:
        logger.info("Mounting Google Drive at %s...", mount_point)
        drive.mount(mount_point, force_remount=force_remount)
        _drive_mounted = True
        logger.info("Drive mounted successfully")
        return True
    except Exception as e:
        logger.warning("Failed to mount drive: %s", e)
        return False


def google_authenticate(
    scopes: Optional[List[str]] = None, force: bool = False
) -> Tuple[Any, Optional[str]]:
    """
    Google 서비스 인증을 수행합니다. (Colab 전용)

    Parameters
    ----------
    scopes : Optional[List[str]]
        요청할 OAuth 스코프 목록 (미사용, 호환성 유지)
    force : bool
        강제 재인증 여부 (미사용, 호환성 유지)

    Returns
    -------
    credentials : Any
        인증된 자격증명 객체 (Colab: google.auth.credentials, 로컬: None)
    project_id : Optional[str]
        프로젝트 ID (있는 경우)

    Raises
    ------
    RuntimeError
        Colab 환경이 아닌 경우

    Examples
    --------
    >>> from helper_dev_utils import google_authenticate
    >>> creds, project = google_authenticate()
    >>> # PyDrive2, gspread 등과 함께 사용
    """
    logger = helper_logger.get_auto_logger()

    if not IS_COLAB:
        raise RuntimeError("google_authenticate() is only available in Google Colab environment")

    try:
        from google.colab import auth
        from google.auth import default

        logger.info("Authenticating Google user...")
        auth.authenticate_user()

        creds, project = default()
        logger.info("Authentication successful (project: %s)", project)

        return creds, project
    except Exception as e:
        logger.error("Authentication failed: %s", e)
        raise


def google_get_secret(
    key: str, default: Optional[str] = None, fallback_env: bool = True
) -> Optional[str]:
    """
    Colab Secrets 또는 환경변수에서 비밀값을 가져옵니다.

    Parameters
    ----------
    key : str
        비밀값의 키 이름
    default : Optional[str]
        값이 없을 때 반환할 기본값
    fallback_env : bool
        Colab이 아닐 때 환경변수에서 찾을지 여부 (기본값: True)

    Returns
    -------
    Optional[str]
        비밀값 또는 기본값

    Examples
    --------
    >>> from helper_dev_utils import google_get_secret
    >>> api_key = google_get_secret('OPENAI_API_KEY')
    >>> db_pass = google_get_secret('DB_PASSWORD', default='')
    """
    logger = helper_logger.get_auto_logger()

    # Colab 환경: userdata 우선
    if IS_COLAB:
        try:
            from google.colab import userdata

            value = userdata.get(key)
            logger.debug("Retrieved secret '%s' from Colab userdata", key)
            return value
        except KeyError:
            logger.debug("Secret '%s' not found in Colab userdata", key)
        except Exception as e:
            logger.warning("Failed to access Colab userdata for '%s': %s", key, e)

    # 환경변수 폴백
    if fallback_env:
        value = os.getenv(key, default)
        if value != default:
            logger.debug("Retrieved secret '%s' from environment variable", key)
        else:
            logger.debug("Secret '%s' not found, using default", key)
        return value

    logger.debug("Secret '%s' not found, using default", key)
    return default


def google_is_drive_mounted(mount_point: str = "/content/drive") -> bool:
    """
    Google Drive 마운트 상태를 확인합니다.

    Parameters
    ----------
    mount_point : str
        드라이브 마운트 지점 (기본값: "/content/drive")

    Returns
    -------
    bool
        마운트 여부
    """
    if not IS_COLAB:
        return False

    my_drive_path = os.path.join(mount_point, "MyDrive")
    return os.path.exists(my_drive_path)
