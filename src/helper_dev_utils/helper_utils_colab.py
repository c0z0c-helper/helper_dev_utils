"""
helper_utils_colab.py - Backward Compatibility Layer

이 모듈은 이전 버전 호환성을 위해 유지됩니다.
새로운 코드에서는 다음 모듈을 직접 import하세요:
- helper_path_finder: 경로 탐색 기능
- helper_google_driver: Google Drive 경로 관리
- helper_cache: 캐시 경로 관리
- helper_colab_auth: Google Colab 인증
"""

import os
import sys
import platform
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import importlib.resources as resources
import inspect
import warnings
from pathlib import Path
from typing import Any, Optional, Union

try:
    from . import helper_logger
    from . import helper_path_finder
    from . import helper_google_driver
    from . import helper_cache
    from . import helper_colab_auth
except ImportError:
    import helper_logger
    import helper_path_finder
    import helper_google_driver
    import helper_cache
    import helper_colab_auth

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


# ===========================
# Backward Compatibility 재수출
# ===========================

# 경로 탐색 함수 재수출
find_cache_root = helper_path_finder.find_cache_root
find_google_drive = helper_path_finder.find_google_drive

# Google Drive 함수 재수출
google_driver = helper_google_driver.google_driver
google_driver_path = helper_google_driver.google_driver_path

# 캐시 함수 재수출
cache = helper_cache.cache
cache_path = helper_cache.cache_path

# Google Colab 인증 함수 재수출
google_authenticate = helper_colab_auth.google_authenticate
google_get_secret = helper_colab_auth.google_get_secret
google_is_drive_mounted = helper_colab_auth.google_is_drive_mounted


# ===========================
# 폰트 설정 함수 (matplotlib)
# ===========================


def setup_matplotlib_korean_font() -> None:
    """
    matplotlib에서 한글을 지원하는 폰트를 설정합니다.

    Windows, macOS, Linux/Colab 환경에서 사용 가능한 한글 폰트를 자동으로 감지합니다.
    """
    logger = helper_logger.get_auto_logger()
    font_name = _get_korean_font()
    if font_name:
        plt.rcParams["font.family"] = font_name
        plt.rcParams["axes.unicode_minus"] = False
        logger.info("Matplotlib Korean font set to: %s", font_name)
    else:
        logger.warning("No Korean font found, matplotlib may display Korean text as boxes")


def _get_korean_font() -> Optional[str]:
    """
    시스템에서 사용 가능한 한글 폰트를 감지합니다.

    Returns
    -------
    Optional[str]
        한글 폰트 이름 (없으면 None)
    """
    logger = helper_logger.get_auto_logger()
    system = platform.system()

    # 우선순위 폰트 목록
    candidate_fonts = []

    if system == "Windows":
        candidate_fonts = ["Malgun Gothic", "맑은 고딕", "Gulim", "굴림", "Batang", "바탕"]
    elif system == "Darwin":  # macOS
        candidate_fonts = ["AppleGothic", "Apple SD Gothic Neo"]
    elif system == "Linux" or IS_COLAB:
        candidate_fonts = [
            "NanumGothic",
            "NanumBarunGothic",
            "NanumMyeongjo",
            "DejaVu Sans",
        ]

    # 시스템에서 사용 가능한 폰트 확인
    available_fonts = {f.name for f in fm.fontManager.ttflist}

    for font in candidate_fonts:
        if font in available_fonts:
            logger.debug("Found Korean font: %s", font)
            return font

    logger.warning("No Korean font found in system fonts")
    return None


def display_markdown(text: str) -> Optional[Any]:
    """
    Jupyter 환경에서 Markdown을 렌더링합니다.

    Parameters
    ----------
    text : str
        렌더링할 Markdown 텍스트

    Returns
    -------
    Optional[Any]
        IPython.display 객체 (Jupyter 환경이 아니면 None)
    """
    logger = helper_logger.get_auto_logger()

    if IPYTHON_AVAILABLE:
        try:
            from IPython.display import display, Markdown

            display_obj = Markdown(text)
            display(display_obj)
            logger.debug("Markdown displayed successfully")
            return display_obj
        except Exception as e:
            logger.warning("Failed to display Markdown: %s", e)
    else:
        logger.warning("IPython not available, cannot display Markdown")

    return None


def display_html(html: str) -> Optional[Any]:
    """
    Jupyter 환경에서 HTML을 렌더링합니다.

    Parameters
    ----------
    html : str
        렌더링할 HTML 텍스트

    Returns
    -------
    Optional[Any]
        IPython.display 객체 (Jupyter 환경이 아니면 None)
    """
    logger = helper_logger.get_auto_logger()

    if IPYTHON_AVAILABLE:
        try:
            from IPython.display import display

            display_obj = HTML(html)
            display(display_obj)
            logger.debug("HTML displayed successfully")
            return display_obj
        except Exception as e:
            logger.warning("Failed to display HTML: %s", e)
    else:
        logger.warning("IPython not available, cannot display HTML")

    return None


if __name__ == "__main__":
    logger = helper_logger.get_auto_logger()

    # 테스트: GoogleDrive 경로 탐지 및 출력
    logger.debug("=" * 60)
    logger.debug("GoogleDrive Path Detection Test")
    logger.debug("=" * 60)

    current_os = platform.system()
    logger.debug(f"Current OS: {current_os}")
    logger.debug(f"Is Colab environment: {IS_COLAB}")
    logger.debug(f"google_driver() returns: {google_driver()}")

    logger.debug("=" * 60)

    # 테스트: Cache 경로 탐지 및 출력
    logger.debug("=" * 60)
    logger.debug("Cache Path Detection Test")
    logger.debug("=" * 60)

    logger.debug(f"cache() returns: {cache()}")

    try:
        test_cache_path = cache_path("test_subdir", validate=False)
        logger.debug(f"✓ cache_path('test_subdir'): {test_cache_path}")
    except Exception as e:
        logger.debug(f"✗ cache_path() error: {e}")

    logger.debug("=" * 60)
