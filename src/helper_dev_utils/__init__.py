"""
helper-dev-utils
============

Python 유틸리티 모음 라이브러리

주요 모듈:
- helper_logger: 로깅 유틸리티 (콘솔/파일 핸들러, 타임존 설정)
- helper_pandas: Pandas 확장 기능 (한글 컬럼 설명, 데이터 출력)
- helper_utils_print: 출력 유틸리티 (디렉토리/JSON/딕셔너리 트리 구조 출력)
- helper_utils_colab: 경로 관리 유틸리티 (로컬/Colab 환경 경로 자동 탐색)

기본 사용법:
    # Logger
    from helper_dev_utils import get_logger
    logger = get_logger()  # 호출자 모듈명을 로거 이름으로 자동 사용
    logger.info("Hello World")

    # Pandas Extension
    from helper_dev_utils import set_pandas_extension
    import pandas as pd
    set_pandas_extension()
    df = pd.DataFrame({'name': ['Alice', 'Bob']})
    df.set_col_description('name', '사용자 이름')
    df.show()

    # Print Tree
    from helper_dev_utils import print_dir_tree, print_json_tree
    print_dir_tree('/path/to/directory')
    print_json_tree({'key': 'value'})

    # Colab Path
    from helper_dev_utils import my_driver, my_cache
    driver_path = my_driver()  # Google Drive 경로
    cache_path = my_cache()    # 캐시 경로
"""

__version__ = "0.6.5"

# Import main functions from each module
from .helper_logger import (
    get_logger,
)

from .helper_pandas import (
    set_pandas_extension,
)

from .helper_utils_print import (
    print_dir_tree,
    print_json_tree,
    print_dic_tree,
)

from .helper_utils_colab import (
    google_driver,
    google_driver_path,
    cache,
    cache_path,
    IS_COLAB,
    IPYTHON_AVAILABLE,
)

from .helper_colab_auth import (
    google_authenticate,
    google_get_secret,
    google_is_drive_mounted,
)

from .helper_help import (
    helper_help,
    helper_search,
)

__all__ = [
    # Logger utilities
    "get_logger",
    # Pandas extension
    "set_pandas_extension",
    # Print utilities
    "print_dir_tree",
    "print_json_tree",
    "print_dic_tree",
    # Colab/Path utilities
    "google_driver",
    "google_driver_path",
    "cache",
    "cache_path",
    # Environment detection
    "IS_COLAB",
    "IPYTHON_AVAILABLE",
    # Colab authentication
    "google_authenticate",
    "google_get_secret",
    "google_is_drive_mounted",
    # Help utilities
    "helper_help",
    "helper_search",
    # Version
    "__version__",
]
