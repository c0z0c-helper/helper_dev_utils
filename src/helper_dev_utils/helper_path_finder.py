"""
경로 탐색 유틸리티

Google Drive 및 캐시 디렉토리를 자동으로 탐색하는 기능을 제공합니다.
"""

import os
import platform
import tempfile
import string
from typing import Optional

try:
    from . import helper_logger
except ImportError:
    import helper_logger

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def find_cache_root(app_name: str = ".cache") -> str:
    """
    캐시 디렉토리를 다음 우선순위로 찾습니다:
    1. .env 파일의 MY_CACHE_LOCAL (폴더 생성 시도 포함)
    2. OS별 자동 탐색 (Windows/Linux/macOS)
    3. 시스템 temp 폴더

    Parameters
    ----------
    app_name : str
        캐시 디렉토리 이름 (기본값: ".cache")

    Returns
    -------
    str
        발견되거나 생성된 캐시 경로, 또는 temp 폴더 경로.
    """
    logger = helper_logger.get_auto_logger()

    # 1순위: .env 파일의 MY_CACHE_LOCAL
    if DOTENV_AVAILABLE:
        try:
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                my_cache_env = os.getenv("MY_CACHE_LOCAL")
                if my_cache_env:
                    if os.path.exists(my_cache_env) and os.path.isdir(my_cache_env):
                        logger.debug("Found MY_CACHE_LOCAL from .env: %s", my_cache_env)
                        return os.path.abspath(my_cache_env)
                    try:
                        os.makedirs(my_cache_env, exist_ok=True)
                        logger.debug("Created MY_CACHE_LOCAL from .env: %s", my_cache_env)
                        return os.path.abspath(my_cache_env)
                    except (OSError, PermissionError) as e:
                        logger.warning(
                            "Failed to create MY_CACHE_LOCAL from .env (%s): %s", my_cache_env, e
                        )
        except Exception as e:
            logger.warning("Failed to load .env file: %s", e)

    # 2순위: OS별 자동 탐색
    search_paths = []
    system = platform.system()

    if system == "Windows":
        localappdata = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        search_paths.append(os.path.join(localappdata, app_name, "Cache"))
        appdata = os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        search_paths.append(os.path.join(appdata, app_name, "Cache"))
    elif system == "Linux":
        xdg_cache = os.getenv("XDG_CACHE_HOME")
        if xdg_cache:
            search_paths.append(os.path.join(xdg_cache, app_name))
        else:
            search_paths.append(os.path.join(os.path.expanduser("~"), ".cache", app_name))
    elif system == "Darwin":
        search_paths.append(os.path.join(os.path.expanduser("~"), "Library", "Caches", app_name))

    for path in search_paths:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                real_path = os.path.realpath(path)
                logger.debug("find_cache_root(): %s (real path: %s)", path, real_path)
                return real_path
        except (OSError, PermissionError):
            continue

    # 3순위: temp 폴더
    temp_path = tempfile.gettempdir()
    return temp_path


def find_google_drive() -> str:
    """
    GoogleDrive 폴더를 다음 우선순위로 찾습니다:
    1. .env 파일의 MY_DRIVER_LOCAL (폴더 생성 시도 포함)
    2. OS별 자동 탐색 (Windows/Linux/macOS)
    3. 시스템 temp 폴더

    Returns
    -------
    str
        발견되거나 생성된 GoogleDrive 경로, 또는 temp 폴더 경로.
    """
    logger = helper_logger.get_auto_logger()

    # 1순위: .env 파일의 MY_DRIVER_LOCAL
    if DOTENV_AVAILABLE:
        try:
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                my_driver_env = os.getenv("MY_DRIVER_LOCAL")
                if my_driver_env:
                    if os.path.exists(my_driver_env) and os.path.isdir(my_driver_env):
                        logger.debug("Found MY_DRIVER_LOCAL from .env: %s", my_driver_env)
                        return os.path.abspath(my_driver_env)
                    try:
                        os.makedirs(my_driver_env, exist_ok=True)
                        logger.debug("Created MY_DRIVER_LOCAL from .env: %s", my_driver_env)
                        return os.path.abspath(my_driver_env)
                    except (OSError, PermissionError) as e:
                        logger.warning(
                            "Failed to create MY_DRIVER_LOCAL from .env (%s): %s", my_driver_env, e
                        )
        except Exception as e:
            logger.warning("Failed to load .env file: %s", e)

    # 2순위: OS별 자동 탐색
    search_paths = []
    system = platform.system()

    if system == "Windows":
        for letter in string.ascii_uppercase:
            for folder_name in ["GoogleDrive", "Google Drive"]:
                search_paths.append(os.path.join(f"{letter}:\\", folder_name))
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.append(os.path.join(os.path.expanduser("~"), folder_name))
    elif system == "Linux":
        username = os.getenv("USER", "")
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.extend(
                [
                    os.path.join(os.path.expanduser("~"), folder_name),
                    os.path.join("/mnt", folder_name),
                    os.path.join("/media", username, folder_name) if username else None,
                    os.path.join("/opt", folder_name),
                ]
            )
        search_paths = [p for p in search_paths if p is not None]
    elif system == "Darwin":
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.extend(
                [
                    os.path.join(os.path.expanduser("~"), folder_name),
                    os.path.join("/Volumes", folder_name),
                ]
            )

    for path in search_paths:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                real_path = os.path.realpath(path)
                logger.debug("find_google_drive(): %s (real path: %s)", path, real_path)
                return real_path
        except (OSError, PermissionError):
            continue

    # 3순위: temp 폴더
    temp_path = tempfile.gettempdir()
    return temp_path
