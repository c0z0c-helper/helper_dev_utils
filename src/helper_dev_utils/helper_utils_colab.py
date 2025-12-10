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


def _find_cache_root(app_name: str = "sprint_mission") -> str:
    """
    캐시 디렉토리를 다음 우선순위로 찾습니다:
    1. .env 파일의 MY_CACHE_LOCAL (폴더 생성 시도 포함)
    2. OS별 자동 탐색 (Windows/Linux/macOS)
    3. 시스템 temp 폴더

    Parameters
    ----------
    app_name : str
        캐시 디렉토리 이름 (기본값: "sprint_mission")

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
                load_dotenv(env_path)
                my_cache_env = os.getenv("MY_CACHE_LOCAL")
                if my_cache_env:
                    # 경로 존재 확인
                    if os.path.exists(my_cache_env) and os.path.isdir(my_cache_env):
                        logger.debug("Found MY_CACHE_LOCAL from .env: %s", my_cache_env)
                        return os.path.abspath(my_cache_env)
                    # 폴더 생성 시도
                    try:
                        os.makedirs(my_cache_env, exist_ok=True)
                        logger.debug("Created MY_CACHE_LOCAL from .env: %s", my_cache_env)
                        return os.path.abspath(my_cache_env)
                    except (OSError, PermissionError) as e:
                        logger.warning("Failed to create MY_CACHE_LOCAL from .env (%s): %s", my_cache_env, e)
        except Exception as e:
            logger.warning("Failed to load .env file: %s", e)
    else:
        logger.warning("python-dotenv not available, skipping .env file loading")
    
    # 2순위: OS별 자동 탐색
    search_paths = []
    system = platform.system()
    
    if system == "Windows":
        # Windows: %LOCALAPPDATA%
        localappdata = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        search_paths.append(os.path.join(localappdata, app_name, "Cache"))
        # 대안: APPDATA
        appdata = os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        search_paths.append(os.path.join(appdata, app_name, "Cache"))
    
    elif system == "Linux":
        # Linux: XDG_CACHE_HOME 또는 ~/.cache
        xdg_cache = os.getenv("XDG_CACHE_HOME")
        if xdg_cache:
            search_paths.append(os.path.join(xdg_cache, app_name))
        else:
            search_paths.append(os.path.join(os.path.expanduser("~"), ".cache", app_name))
    
    elif system == "Darwin":
        # macOS: ~/Library/Caches
        search_paths.append(os.path.join(os.path.expanduser("~"), "Library", "Caches", app_name))
    
    # 탐색 및 첫 발견 즉시 반환
    for path in search_paths:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                real_path = os.path.realpath(path)
                logger.debug("_find_cache_root(): %s (real path: %s)", path, real_path)
                return real_path
        except (OSError, PermissionError):
            # 접근 불가능한 경로는 건너뜀
            continue
    
    # 3순위: temp 폴더
    temp_path = tempfile.gettempdir()
    logger.warning("Cache directory not found, falling back to temp folder: %s", temp_path)
    return temp_path


def _find_google_drive() -> str:
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
                load_dotenv(env_path)
                my_driver_env = os.getenv("MY_DRIVER_LOCAL")
                if my_driver_env:
                    # 경로 존재 확인
                    if os.path.exists(my_driver_env) and os.path.isdir(my_driver_env):
                        logger.debug("Found MY_DRIVER_LOCAL from .env: %s", my_driver_env)
                        return os.path.abspath(my_driver_env)
                    # 폴더 생성 시도
                    try:
                        os.makedirs(my_driver_env, exist_ok=True)
                        logger.debug("Created MY_DRIVER_LOCAL from .env: %s", my_driver_env)
                        return os.path.abspath(my_driver_env)
                    except (OSError, PermissionError) as e:
                        logger.warning("Failed to create MY_DRIVER_LOCAL from .env (%s): %s", my_driver_env, e)
        except Exception as e:
            logger.warning("Failed to load .env file: %s", e)
    else:
        logger.warning("python-dotenv not available, skipping .env file loading")
    
    # 2순위: OS별 자동 탐색
    search_paths = []
    system = platform.system()
    
    if system == "Windows":
        # Windows: 모든 드라이브 문자 확인
        for letter in string.ascii_uppercase:
            for folder_name in ["GoogleDrive", "Google Drive"]:
                search_paths.append(os.path.join(f"{letter}:\\", folder_name))
        # 사용자 홈 디렉토리
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.append(os.path.join(os.path.expanduser("~"), folder_name))
    
    elif system == "Linux":
        # Linux: 홈, /mnt, /media 등
        username = os.getenv("USER", "")
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.extend([
                os.path.join(os.path.expanduser("~"), folder_name),
                os.path.join("/mnt", folder_name),
                os.path.join("/media", username, folder_name) if username else None,
                os.path.join("/opt", folder_name),
            ])
        search_paths = [p for p in search_paths if p is not None]
    
    elif system == "Darwin":
        # macOS: 홈, /Volumes
        for folder_name in ["GoogleDrive", "Google Drive"]:
            search_paths.extend([
                os.path.join(os.path.expanduser("~"), folder_name),
                os.path.join("/Volumes", folder_name),
            ])
    
    # 탐색 및 첫 발견 즉시 반환
    for path in search_paths:
        try:
            if os.path.exists(path) and os.path.isdir(path):
                # 심볼릭 링크 해석
                real_path = os.path.realpath(path)
                logger.debug("my_driver(): %s (real path: %s)", path, real_path)
                return real_path
        except (OSError, PermissionError):
            # 접근 불가능한 경로는 건너뜀
            continue
    
    # 3순위: temp 폴더
    temp_path = tempfile.gettempdir()
    logger.warning("GoogleDrive not found, falling back to temp folder: %s", temp_path)
    return temp_path


_my_driver_local = _find_google_drive()
_my_driver_colab = r"/content/drive/MyDrive"
def my_driver(my_driver_local: str | None = None, my_driver_colab: str | None = None) -> str:
    """
    로컬 또는 Colab 환경에 맞는 Google Drive 루트 경로를 반환합니다.

    우선순위(높은 것부터)
    1. 함수 인자로 전달된 값 (my_driver_local, my_driver_colab) — 전달 시 전역 기본값을 덮어씀.
    2. .env 파일의 MY_DRIVER_LOCAL 값 (python-dotenv가 설치되어 있고 .env가 존재하는 경우).
       - .env의 MY_DRIVER_LOCAL 값이 설정되어 있으면 해당 경로를 우선 사용합니다.
       - 경로가 존재하지 않으면 폴더 생성을 시도하고, 생성 실패 시 경고 로그를 남깁니다.
    3. 모듈 초기화 시 자동 탐지된 값(_my_driver_local) — _find_google_drive()에서 결정됩니다.
    4. 위 모두 실패하면 시스템 임시 폴더(temp)를 반환합니다.

    설명
    - Colab 환경(IS_COLAB)이 감지되면 Colab용 경로(_my_driver_colab)를 반환합니다.
    - 로컬 실행 시에는 _my_driver_local을 반환합니다. _my_driver_local은 모듈 로드 시 _find_google_drive()로 설정됩니다.
    - 함수는 동작을 변경하지 않으며, 호출 시 전달된 인자로 전역 기본값을 덮어쓸 수 있게 되어 있습니다.

    Parameters
    ----------
    my_driver_local : str | None
        로컬 환경에서 사용할 드라이브 경로 (지정 시 전역 기본값을 덮어씀).
    my_driver_colab : str | None
        Colab 환경에서 사용할 드라이브 경로 (지정 시 전역 기본값을 덮어씀).

    Returns
    -------
    str
        현재 실행 환경에 맞는 드라이브 루트 경로 (Colab이면 colab 경로, 아니면 로컬 탐지 결과).
    """
    global _my_driver_local, _my_driver_colab

    # 전달된 인자로 전역 기본값 업데이트(명시적 우선권)
    if my_driver_local is not None:
        _my_driver_local = my_driver_local
        logger.info("Updated _my_driver_local: %s", _my_driver_local)
    if my_driver_colab is not None:
        _my_driver_colab = my_driver_colab
        logger.info("Updated _my_driver_colab: %s", _my_driver_colab)

    # Colab 환경이면 Colab 전용 경로 반환, 그렇지 않으면 로컬 탐지값 반환
    if IS_COLAB:
        return _my_driver_colab
    return _my_driver_local


def my_driver_path(
    *subpaths: Union[str, os.PathLike, None],
    create: bool = True,
    validate: bool = True,
    allow_escape: bool = False,
    my_driver_local: Optional[str] = None,
    my_driver_colab: Optional[str] = None,
) -> str:
    """
    my_driver() 루트와 선택적 하위 경로들을 결합하여 정규화된 절대 경로 문자열을 반환합니다.
    (Colab 및 로컬 환경 자동 감지)

    동작 우선순위:
    1. 첫 subpath가 절대경로이면 base를 무시하고 정규화된 절대 경로만 반환합니다.
    2. 상대 경로 subpath들은 my_driver()의 루트와 결합되어 정규화됩니다.
    3. create=True일 때 최종 경로의 디렉토리를 생성하려 시도합니다 (실패 시 OSError/PermissionError 발생).
    4. validate=True일 때 최종 경로가 존재하는지 확인하고 없으면 FileNotFoundError를 발생시킵니다 (create=True 후에 재확).
    5. allow_escape=False(기본)일 때 상대 경로가 my_driver 루트 밖으로 탈출하는 것을 방지합니다.

    Parameters
    ----------
    *subpaths : Union[str, os.PathLike]
        결합할 하위 경로 컴포넌트들 (0개 이상).
    create : bool, default=False
        True이면 최종 경로의 디렉토리를 생성합니다.
    validate : bool, default=False
        True이면 최종 경로가 존재하는지 검증하고, 없으면 FileNotFoundError를 발생시킵니다.
    allow_escape : bool, default=False
        False(기본)이면 상대 경로가 my_driver 루트를 벗어나는 것을 차단합니다.
    my_driver_local : Optional[str]
        로컬 환경에서 사용할 my_driver 루트 경로 (지정 시 전역 기본값을 재정의).
    my_driver_colab : Optional[str]
        Colab 환경에서 사용할 my_driver 루트 경로 (지정 시 전역 기본값을 재정의).

    Returns
    -------
    str
        정규화된 절대 경로 문자열.

    Raises
    ------
    TypeError
        subpath가 str 또는 os.PathLike 타입이 아닐 때.
    ValueError
        allow_escape=False인데 상대 경로가 my_driver 루트를 탈출하려 할 때.
    FileNotFoundError
        validate=True인데 최종 경로가 존재하지 않을 때 (create 후에도).
    OSError, PermissionError
        create=True인데 디렉토리 생성에 실패했을 때.

    Examples
    --------
    >>> my_driver_path('model', 'v1')  # my_driver()가 'D:/GoogleDrive'를 반환한다면
    'D:\\\\GoogleDrive\\\\model\\\\v1'  # Windows에서는 백슬래시 사용

    >>> my_driver_path('data', create=True)  # data 디렉토리 생성 후 경로 반환
    'D:\\\\GoogleDrive\\\\data'

    >>> my_driver_path('/tmp/other')  # 절대 경로는 base 무시
    '/tmp/other'

    >>> my_driver_path('..', allow_escape=False)  # ValueError 발생 (기본 동작)
    ValueError: ...
    """
    # 호출 시 전달된 인자로 my_driver 동작 재정의 (테스트/오버라이드 용)
    base_path = my_driver(my_driver_local=my_driver_local, my_driver_colab=my_driver_colab)
    base = Path(base_path).resolve(strict=False)
    logger.debug("my_driver_path base: %s", base)

    # 입력 subpath 처리: None 제거, 타입 확인
    processed_subpaths = []
    for sp in subpaths:
        if sp is None:
            continue
        if isinstance(sp, (str, os.PathLike)):
            processed_subpaths.append(str(sp))
        else:
            raise TypeError(
                f"Subpath must be str or os.PathLike, got {type(sp).__name__}"
            )

    # 시작점 결정: 첫 subpath가 절대경로면 해당 경로, 아니면 base
    if processed_subpaths and os.path.isabs(processed_subpaths[0]):
        start_path = Path(processed_subpaths[0]).resolve(strict=False)
        remaining_subpaths = processed_subpaths[1:]  # 나머지만 결합
        logger.debug("First subpath is absolute, using as start: %s", start_path)
    else:
        start_path = base
        remaining_subpaths = processed_subpaths

    # 나머지 subpath들 결합
    if remaining_subpaths:
        result_path = start_path.joinpath(*remaining_subpaths).resolve(strict=False)
    else:
        result_path = start_path

    # allow_escape=False일 때 경로 탈출 검사 (start_path 기준)
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

    logger.debug("my_driver_path result (before create/validate): %s", result_path)

    # create=True: 디렉토리 생성
    if create:
        try:
            result_path.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", result_path)
        except (OSError, PermissionError) as e:
            logger.error("Failed to create directory '%s': %s", result_path, e)
            raise

    # validate=True: 경로 존재 확인
    if validate:
        if not result_path.exists():
            logger.error("Path does not exist: %s", result_path)
            raise FileNotFoundError(f"Path does not exist: {result_path}")
        logger.debug("Path validation passed: %s", result_path)

    logger.debug("my_driver_path final: %s", result_path)
    return str(result_path)

# 캐시 경로 초기화
_my_cache_local = _find_cache_root()
_my_cache_colab = r"/content/cache/sprint_mission"

def my_cache(my_cache_local: str | None = None, my_cache_colab: str | None = None) -> str:
    """
    로컬 또는 Colab 환경에 맞는 캐시 루트 경로를 반환합니다.

    우선순위(높은 것부터)
    1. 함수 인자로 전달된 값 (my_cache_local, my_cache_colab) — 전달 시 전역 기본값을 덮어씀.
    2. .env 파일의 MY_CACHE_LOCAL 값 (python-dotenv가 설치되어 있고 .env가 존재하는 경우).
       - .env의 MY_CACHE_LOCAL 값이 설정되어 있으면 해당 경로를 우선 사용합니다.
       - 경로가 존재하지 않으면 폴더 생성을 시도합니다.
    3. 모듈 초기화 시 자동 탐지된 값(_my_cache_local) — _find_cache_root()에서 결정됩니다.
    4. 위 모두 실패하면 시스템 임시 폴더(temp)를 반환합니다.

    설명
    - Colab 환경(IS_COLAB)이 감지되면 Colab용 경로(_my_cache_colab)를 반환합니다.
    - 로컬 실행 시에는 _my_cache_local을 반환합니다. _my_cache_local은 모듈 로드 시 _find_cache_root()로 설정됩니다.
    - 함수는 동작을 변경하지 않으며, 호출 시 전달된 인자로 전역 기본값을 덮어쓸 수 있게 되어 있습니다.

    Parameters
    ----------
    my_cache_local : str | None
        로컬 환경에서 사용할 캐시 경로 (지정 시 전역 기본값을 덮어씀).
    my_cache_colab : str | None
        Colab 환경에서 사용할 캐시 경로 (지정 시 전역 기본값을 덮어씀).

    Returns
    -------
    str
        현재 실행 환경에 맞는 캐시 루트 경로 (Colab이면 colab 경로, 아니면 로컬 탐지 결과).
    """
    global _my_cache_local, _my_cache_colab

    # 전달된 인자로 전역 기본값 업데이트(명시적 우선권)
    if my_cache_local is not None:
        _my_cache_local = my_cache_local
        logger.info("Updated _my_cache_local: %s", _my_cache_local)
    if my_cache_colab is not None:
        _my_cache_colab = my_cache_colab
        logger.info("Updated _my_cache_colab: %s", _my_cache_colab)

    # Colab 환경이면 Colab 전용 경로 반환, 그렇지 않으면 로컬 탐지값 반환
    if IS_COLAB:
        return _my_cache_colab
    return _my_cache_local


def my_cache_path(
    *subpaths: Union[str, os.PathLike, None],
    create: bool = True,
    validate: bool = True,
    allow_escape: bool = False,
    my_cache_local: Optional[str] = None,
    my_cache_colab: Optional[str] = None,
) -> str:
    """
    my_cache() 루트와 선택적 하위 경로들을 결합하여 정규화된 절대 경로 문자열을 반환합니다.
    (Colab 및 로컬 환경 자동 감지)

    동작 우선순위:
    1. 첫 subpath가 절대경로이면 base를 무시하고 정규화된 절대 경로만 반환합니다.
    2. 상대 경로 subpath들은 my_cache()의 루트와 결합되어 정규화됩니다.
    3. create=True일 때 최종 경로의 디렉토리를 생성하려 시도합니다 (실패 시 OSError/PermissionError 발생).
    4. validate=True일 때 최종 경로가 존재하는지 확인하고 없으면 FileNotFoundError를 발생시킵니다 (create=True 후에 재확).
    5. allow_escape=False(기본)일 때 상대 경로가 my_cache 루트 밖으로 탈출하는 것을 방지합니다.

    Parameters
    ----------
    *subpaths : Union[str, os.PathLike]
        결합할 하위 경로 컴포넌트들 (0개 이상).
    create : bool, default=True
        True이면 최종 경로의 디렉토리를 생성합니다.
    validate : bool, default=True
        True이면 최종 경로가 존재하는지 검증하고, 없으면 FileNotFoundError를 발생시킵니다.
    allow_escape : bool, default=False
        False(기본)이면 상대 경로가 my_cache 루트를 벗어나는 것을 차단합니다.
    my_cache_local : Optional[str]
        로컬 환경에서 사용할 my_cache 루트 경로 (지정 시 전역 기본값을 재정의).
    my_cache_colab : Optional[str]
        Colab 환경에서 사용할 my_cache 루트 경로 (지정 시 전역 기본값을 재정의).

    Returns
    -------
    str
        정규화된 절대 경로 문자열.

    Raises
    ------
    TypeError
        subpath가 str 또는 os.PathLike 타입이 아닐 때.
    ValueError
        allow_escape=False인데 상대 경로가 my_cache 루트를 탈출하려 할 때.
    FileNotFoundError
        validate=True인데 최종 경로가 존재하지 않을 때 (create 후에도).
    OSError, PermissionError
        create=True인데 디렉토리 생성에 실패했을 때.

    Examples
    --------
    >>> my_cache_path('models', 'v1')  # my_cache()가 'D:/cache'를 반환한다면
    'D:\\\\cache\\\\models\\\\v1'  # Windows에서는 백슬래시 사용

    >>> my_cache_path('temp', create=True)  # temp 디렉토리 생성 후 경로 반환
    'D:\\\\cache\\\\temp'

    >>> my_cache_path('/tmp/other')  # 절대 경로는 base 무시
    '/tmp/other'

    >>> my_cache_path('..', allow_escape=False)  # ValueError 발생 (기본 동작)
    ValueError: ...
    """
    # 호출 시 전달된 인자로 my_cache 동작 재정의 (테스트/오버라이드 용)
    base_path = my_cache(my_cache_local=my_cache_local, my_cache_colab=my_cache_colab)
    base = Path(base_path).resolve(strict=False)
    logger.debug("my_cache_path base: %s", base)

    # 입력 subpath 처리: None 제거, 타입 확인
    processed_subpaths = []
    for sp in subpaths:
        if sp is None:
            continue
        if isinstance(sp, (str, os.PathLike)):
            processed_subpaths.append(str(sp))
        else:
            raise TypeError(
                f"Subpath must be str or os.PathLike, got {type(sp).__name__}"
            )

    # 첫 subpath가 절대경로인 경우: base 무시하고 절대 경로만 정규화해 반환 (탈출 검사 스킵)
    if processed_subpaths and os.path.isabs(processed_subpaths[0]):
        result_path = Path(processed_subpaths[0]).resolve(strict=False)
        logger.info("First subpath is absolute, returning (escape check skipped): %s", result_path)
        
        # create=True: 디렉토리 생성
        if create:
            try:
                result_path.mkdir(parents=True, exist_ok=True)
                logger.debug("Directory created: %s", result_path)
            except (OSError, PermissionError) as e:
                logger.error("Failed to create directory %s: %s", result_path, e)
                raise

        # validate=True: 경로 존재 여부 확인
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

    # allow_escape=False일 때 경로 탈출 검사
    if not allow_escape:
        # 경로 탈출 여부 확인: result_path가 base의 하위디렉토리인지 확인
        is_relative = False
        
        # Python 3.9+: is_relative_to() 사용 (False 반환, 예외 아님)
        if hasattr(result_path, "is_relative_to"):
            is_relative = result_path.is_relative_to(base)
        else:
            # 더 낮은 Python 버전: relative_to() 사용 (실패 시 ValueError 발생)
            try:
                result_path.relative_to(base)
                is_relative = True
            except ValueError:
                is_relative = False
        
        # 탈출 감지 시 오류 발생
        if not is_relative:
            logger.error("Path escape detected: %s is not relative to %s", result_path, base)
            raise ValueError(
                f"Resulting path '{result_path}' escapes my_cache base '{base}'. "
                f"Set allow_escape=True to override this check."
            )

    logger.debug("my_cache_path result (before create/validate): %s", result_path)

    # create=True: 디렉토리 생성
    if create:
        try:
            result_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Directory created: %s", result_path)
        except (OSError, PermissionError) as e:
            logger.error("Failed to create directory %s: %s", result_path, e)
            raise

    # validate=True: 경로 존재 여부 확인
    if validate:
        if not result_path.exists():
            logger.error("Validation failed: path does not exist: %s", result_path)
            raise FileNotFoundError(f"Path does not exist: {result_path}")
        logger.debug("Path validation passed: %s", result_path)

    return str(result_path)


if __name__ == "__main__":
    # 테스트: GoogleDrive 경로 탐지 및 출력
    logger.debug("=" * 60)
    logger.debug("GoogleDrive Path Detection Test")
    logger.debug("=" * 60)
    
    # 현재 OS 확인
    current_os = platform.system()
    logger.debug(f"Current OS: {current_os}")
    
    # 자동 탐지된 경로 출력
    logger.debug(f"Auto-detected _my_driver_local: {_my_driver_local}")
    logger.debug(f"Is Colab environment: {IS_COLAB}")
    
    # my_driver() 함수 테스트
    logger.debug(f"my_driver() returns: {my_driver()}")
    
    # 경로 존재 여부 확인
    if os.path.exists(_my_driver_local):
        logger.debug(f"✓ Path exists: {_my_driver_local}")
        logger.debug(f"  Is directory: {os.path.isdir(_my_driver_local)}")
    else:
        logger.debug(f"✗ Path does not exist: {_my_driver_local}")
    
    # .env 파일 확인
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        logger.debug(f"✓ .env file found at: {env_path}")
        if DOTENV_AVAILABLE:
            load_dotenv(env_path)
            my_driver_env = os.getenv("MY_DRIVER_LOCAL")
            logger.debug(f"MY_DRIVER_LOCAL from .env: {my_driver_env}")
        else:
            logger.debug("  (python-dotenv not available)")
    else:
        logger.debug(f"✗ .env file not found at: {env_path}")
    
    logger.debug("=" * 60)
    
    # 테스트: Cache 경로 탐지 및 출력
    logger.debug("=" * 60)
    logger.debug("Cache Path Detection Test")
    logger.debug("=" * 60)
    
    # 자동 탐지된 캐시 경로 출력
    logger.debug(f"Auto-detected _my_cache_local: {_my_cache_local}")
    logger.debug(f"Auto-detected _my_cache_colab: {_my_cache_colab}")
    
    # my_cache() 함수 테스트
    logger.debug(f"my_cache() returns: {my_cache()}")
    
    # 캐시 경로 존재 여부 확인
    if os.path.exists(_my_cache_local):
        logger.debug(f"✓ Cache path exists: {_my_cache_local}")
        logger.debug(f"  Is directory: {os.path.isdir(_my_cache_local)}")
    else:
        logger.debug(f"✗ Cache path does not exist: {_my_cache_local}")
    
    # my_cache_path() 함수 테스트
    try:
        test_cache_path = my_cache_path("test_subdir", validate=False)
        logger.debug(f"✓ my_cache_path('test_subdir'): {test_cache_path}")
    except Exception as e:
        logger.debug(f"✗ my_cache_path() error: {e}")
    
    # .env 파일의 MY_CACHE_LOCAL 확인
    if DOTENV_AVAILABLE:
        load_dotenv(env_path)
        my_cache_env = os.getenv("MY_CACHE_LOCAL")
        if my_cache_env:
            logger.debug(f"✓ MY_CACHE_LOCAL from .env: {my_cache_env}")
        else:
            logger.debug("  MY_CACHE_LOCAL not set in .env")
    
    logger.debug("=" * 60)


