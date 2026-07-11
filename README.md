# helper-dev-utils

[![PyPI version](https://badge.fury.io/py/helper-dev-utils.svg)](https://badge.fury.io/py/helper-dev-utils)
[![Python](https://img.shields.io/pypi/pyversions/helper-dev-utils.svg)](https://pypi.org/project/helper-dev-utils/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python 개발 시 자주 사용하는 유틸리티 모음 라이브러리

## 주요 기능

- **helper_logger**: 로깅 유틸리티 (콘솔/파일 핸들러, 타임존 설정, 기본 KST)
- **helper_pandas**: Pandas 확장 기능 (한글 컬럼 설명, 데이터 출력, HTML/콘솔 지원)
- **helper_utils_print**: 출력 유틸리티 (디렉토리/JSON/딕셔너리 트리 구조 출력)
- **helper_utils_colab**: 경로 관리 유틸리티 (로컬/Colab 환경 경로 자동 탐색)
- **helper_help**: 도움말 유틸리티 (함수/메서드 시그니처·docstring 출력, 모듈 함수 검색)

## 설치

### 기본 설치
```bash
pip install helper-dev-utils

# 테스트 서버
pip install --index-url https://test.pypi.org/simple/ helper-dev-utils
```

### 선택적 의존성 설치
```bash
# .env 파일 지원
pip install helper-dev-utils[dotenv]

# Jupyter/Colab 지원
pip install helper-dev-utils[jupyter]

# PyTorch Tensor 지원
pip install helper-dev-utils[torch]

# Google Drive 관리 기능 지원 (empty_drive_trash 등, Colab 전용)
pip install helper-dev-utils[google]

# 모든 선택적 의존성 설치
pip install helper-dev-utils[all]
```

## 사용법

### 1. Logger (helper_logger)

콘솔(및 선택적 파일) 로깅을 위한 최소 유틸리티입니다. 레벨은 한 글자로 축약 출력되고,
같은 이름으로 재호출해도 핸들러가 중복 등록되지 않습니다.

```python
from helper_dev_utils import get_auto_logger
import logging

# 자동으로 호출자 모듈명을 로거 이름으로 사용
logger = get_auto_logger()
logger.info("Hello World")
logger.warning("경고 메시지")
logger.error("에러 메시지")

# 레벨/타임존 설정
logger = get_auto_logger(level=logging.DEBUG, tz="UTC")
logger.debug("디버그 메시지")

# 파일 저장 활성화 (기본은 비활성화)
# logs/YYYY/MM/DD/YYYYMMDD_HHMMSS.log 에 기록되며, 같은 프로세스의 로거들이 파일을 공유
logger = get_auto_logger(file=True, log_dir="logs")
```

- `tz`: 타임스탬프에 적용할 타임존 (기본: `Asia/Seoul`)
- `file`: 파일 저장 활성화 여부 (기본: `False`)
- `log_dir`: 파일 저장 활성화 시 사용할 기준 디렉토리 (기본: `"logs"`)

### 2. Pandas Extension (helper_pandas)

DataFrame과 Series에 한글 컬럼 설명 기능을 추가합니다.

```python
from helper_dev_utils import set_pandas_extension
import pandas as pd

# Pandas 확장 등록
set_pandas_extension()

# DataFrame 생성
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['Seoul', 'Busan', 'Incheon']
})

# 컬럼 설명 추가 (개별)
df.set_head_att('name', '사용자 이름')
df.set_head_att('age', '나이')
df.set_head_att('city', '거주 도시')

# 컬럼 설명 추가 (딕셔너리)
df.set_head_att({
    'name': '사용자 이름',
    'age': '나이',
    'city': '거주 도시'
})

# 한글 컬럼명과 함께 출력
df.head_att()
# 출력:
# 사용자 이름    나이  거주 도시
# name          age   city
# Alice          25   Seoul
# Bob            30   Busan
# Charlie        35   Incheon

# 또는 head() 메서드 오버라이드 사용 (enable_head_override=True일 때)
df.head()

# 다양한 출력 형식
df.head_att(rows=10)              # 10행 출력
df.head_att(rows='all')           # 전체 출력
df.head_att(out='html')           # HTML 형태로 출력
df.head_att(out='str')            # 문자열로 반환

# 컬럼 설명 조회
print(df.get_head_att('name'))    # 출력: 사용자 이름
print(df.get_head_att())          # 전체 딕셔너리 출력

# 컬럼 설명 삭제
df.remove_head_att('age')         # 단일 삭제
df.remove_head_att(['name', 'city'])  # 여러 개 삭제
df.clear_head_att()               # 전체 초기화
```

### 3. Print Utilities (helper_utils_print)

디렉토리, JSON, 딕셔너리를 트리 구조로 출력합니다.

```python
from helper_dev_utils import print_dir_tree, print_json_tree, print_dic_tree

# 디렉토리 트리 출력
print_dir_tree('/path/to/directory', max_depth=3)

# JSON/딕셔너리 트리 출력 (파이프 스타일)
data = {
    'users': [
        {'name': 'Alice', 'age': 25},
        {'name': 'Bob', 'age': 30}
    ],
    'config': {'debug': True}
}
print_json_tree(data, max_depth=5, max_list_items=10)

# 딕셔너리 트리 출력 (박스 드로잉 스타일)
print_dic_tree(data, max_depth=5, show_values=True)
```

### 4. Colab/Path Utilities (helper_utils_colab)

로컬 및 Google Colab 환경에서 경로를 자동으로 관리합니다.

```python
from helper_dev_utils import my_driver, my_cache

# Google Drive 경로 가져오기 (Colab에서 자동 마운트)
drive_path = my_driver()
print(drive_path)  # /content/drive/MyDrive (Colab) 또는 로컬 경로

# 캐시 디렉토리 가져오기 (OS별 자동 탐색)
cache_path = my_cache()
print(cache_path)  # ~/.cache (Linux/Mac) 또는 로컬 경로

# 하위 경로 지정
model_cache = my_cache('models/bert')
data_drive = my_driver('datasets/images')
```

**환경변수 우선 지원**:
```env
MY_DRIVER_PATH=/custom/drive/path
MY_CACHE_PATH=/custom/cache/path
```

### 5. Help Utilities (helper_help)

함수·메서드의 시그니처와 docstring을 출력하고, 모듈에서 이름으로 함수를 검색합니다.

```python
from helper_dev_utils import helper_help, helper_search
import pandas as pd
import matplotlib.pyplot as plt

# 함수 도움말 출력 (시그니처 + docstring)
helper_help(pd.DataFrame.groupby)
helper_help(plt.plot)

# 출력 예시:
# Signature : DataFrame.groupby(self, by=None, ...)
# Docstring :
# Group DataFrame using a mapper or by a Series of columns.
# ...
```

```python
# 모듈에서 이름에 query가 포함된 함수 검색
helper_search(pd, "merge")
# 출력:
# [pandas] 'merge' 검색 결과 (3건)
#   - merge
#   - merge_asof
#   - merge_ordered

# query=None 이면 전체 목록 출력
helper_search(pd)
```

| 함수 | 설명 |
|------|------|
| `helper_help(fdn)` | 함수/메서드의 시그니처와 docstring 출력 |
| `helper_search(lbn, query=None)` | 모듈 내 함수/클래스 중 이름에 query가 포함된 항목 출력. query 생략 시 전체 목록 |

## 의존성

### 필수 의존성

- `matplotlib >= 3.2.0`
- `numpy >= 1.16.0`
- `pandas >= 1.0.0`
- `backports.zoneinfo >= 0.2.1` (Python < 3.9 에서만; 3.9+ 는 표준 라이브러리 `zoneinfo` 사용)

### 선택적 의존성

- `python-dotenv >= 0.19.0` - `.env` 파일 지원
- `IPython >= 7.0.0` - Jupyter/Colab 지원
- `torch >= 1.0.0` - PyTorch Tensor 지원
- `google-api-python-client >= 2.0.0` - `empty_drive_trash()` (Colab 전용)

## 개발 및 테스트

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/c0z0c-helper/helper_dev_utils.git
cd helper_dev_utils

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 편집 가능 모드로 설치
pip install -e .
```

### 테스트 실행

```bash
# 전체 테스트 실행
pytest tests -v

# 특정 테스트 파일 실행
pytest tests/test_helper_logger.py -v
pytest tests/test_helper_utils_colab.py -v

# 커버리지 포함 실행
pytest tests --cov=helper_dev_utils --cov-report=html
```

테스트를 실행하면 `tests/conftest.py`가 결과를 자동으로 수집하여
`tests/report/YYYYMMDD_HHMMSS.md`에 통과/실패/스킵 여부가 포함된 표 형태의 리포트를 생성합니다.

### 테스트 환경 설정

테스트에서 `helper_utils_colab` 함수를 검증하려면 `.env.test` 파일을 사용합니다:

1. `.env.test` 파일을 프로젝트 루트에 생성 (이미 샘플이 제공됨)
2. 테스트용 캐시 및 드라이버 경로 설정:

```env
# Windows
MY_CACHE_LOCAL=C:/Users/YOUR_USERNAME/AppData/Local/Temp/helper_dev_utils_test_cache
MY_DRIVER_PATH=C:/Users/YOUR_USERNAME/AppData/Local/Temp/helper_dev_utils_test_driver

# Linux/macOS
# MY_CACHE_LOCAL=/tmp/helper_dev_utils_test_cache
# MY_DRIVER_PATH=/tmp/helper_dev_utils_test_driver
```

`conftest.py`가 자동으로 `.env.test`를 로드하여 테스트 실행 전 환경을 설정합니다.

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여

이슈 리포트 및 풀 리퀘스트는 [GitHub Repository](https://github.com/c0z0c-helper/helper_dev_utils)에서 환영합니다!

## 작성자

**c0z0c** - [c0z0c.dev@gmail.com](mailto:c0z0c.dev@gmail.com)

## 관련 라이브러리

- [helper-plot-hangul](https://pypi.org/project/helper-plot-hangul) - Matplotlib 한글 폰트 자동 설정
- [helper-md-doc](https://pypi.org/project/helper-md-doc) - md doc 파일 라이브러리
- [helper-hwp](https://pypi.org/project/helper-hwp) - HWP 파일 파싱 라이브러리

---

## 버전 히스토리

### 0.5.7 이하

- `helper_logger`: 로깅 유틸리티 초기 구현 및 환경변수 기반 설정 지원
- `helper_pandas`: Pandas 확장 기능 (한글 컬럼 설명, `head_att`, `show` 등)
- `helper_utils_print`: `print_dir_tree`, `print_json_tree`, `print_dic_tree` 구현
- `helper_utils_colab`: 로컬/Colab 환경 경로 자동 탐색 구현

### 0.5.8

- `helper_cache`: 캐시 유틸리티 모듈 추가
- `helper_colab_auth`: Google 인증 관련 함수 추가 (`google_authenticate`, `google_get_secret`, `google_is_drive_mounted`)

### 0.5.9

- `helper_help`: 함수/메서드 시그니처 및 docstring 출력 기능 추가
- `helper_search`: 모듈 내 함수·클래스 이름 기반 검색 기능 추가

### 0.5.10

- `helper_utils_print`: `set_print_tree()` / `set_log_tree()` 함수 추가 - 트리 출력 시 `print` 또는 `logger.info` 전환 가능
- `helper_utils_print`: `print_json_tree`, `print_dic_tree`의 `max_depth`, `list_count` 기본값을 `None`(무한대)으로 변경
- `__init__.py`: `set_print_tree`, `set_log_tree` 패키지 레벨 노출 추가
- `tests`: `test_helper_utils_colab.py` 실제 API(`google_driver`, `google_driver_path`, `cache`, `cache_path`)에 맞게 수정
- `tests`: `test_helper_utils_print.py`에 `set_print_tree`/`set_log_tree` 전환 및 `None` 기본값 테스트 추가 (총 31개)

### 0.6.0

- `helper_logger`: 콘솔(+선택적 파일) 출력을 위한 최소 구현으로 리팩토링. 회전 로깅/중앙집중 파일/`.env` 우선순위 시스템/`reconfigure_logger`/`sample_logger_env`를 제거하고 `get_logger`, `get_auto_logger`만 유지
- `helper_logger`: 레벨 축약을 `%(levelname).1s` 포맷으로 단순화, `tz` 인자로 타임존 설정 가능(기본 `Asia/Seoul`)
- `helper_logger`: `file`(기본 `False`)/`log_dir`(기본 `"logs"`) 옵션 추가 — 활성화 시 `{log_dir}/YYYY/MM/DD/YYYYMMDD_HHMMSS.log`에 기록되며 같은 프로세스의 로거들이 파일을 공유
- `__init__.py`: `sample_logger_env`, `reconfigure_logger` 패키지 레벨 노출 제거
- `tests`: `conftest.py`에 pytest 훅 추가 — 테스트 실행 시 `tests/report/YYYYMMDD_HHMMSS.md`에 결과 표 자동 생성
