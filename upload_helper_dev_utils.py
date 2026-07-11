"""
helper-dev-utils PyPI 업로드 스크립트

사용법:
    python upload_helper_dev_utils.py [--test]
    
옵션:
    --test: TestPyPI에 업로드 (기본값: PyPI)
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# Windows 콘솔 코드페이지(cp949 등)와 무관하게 pip/build/twine이 항상 UTF-8로
# 입출력하도록 강제한다. 미설정 시 콘솔 로케일에 따라 서브프로세스(특히 pip의
# 격리 빌드 환경 설치 단계)에서 UnicodeDecodeError/UnicodeEncodeError가 발생할 수 있다.
_SUBPROCESS_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# twine은 기본적으로 사용자 홈 디렉터리의 .pypirc(%USERPROFILE%\.pypirc)만 찾고
# 프로젝트 루트의 .pypirc는 무시한다. 이 스크립트 옆의 .pypirc를 명시적으로 지정한다.
_PYPIRC_PATH = Path(__file__).parent / ".pypirc"


def clean_build():
    """빌드 디렉토리 정리"""
    print("빌드 디렉토리 정리 중...")
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"   삭제: {path}")
    print("정리 완료\n")


def build_package():
    """패키지 빌드"""
    print("패키지 빌드 중...")
    # --no-isolation: 격리된 임시 venv를 새로 만들지 않고 현재 환경의 setuptools/wheel을
    # 그대로 사용한다. 격리 venv 생성 직후 방금 만들어진 DLL을 백신 실시간 검사가
    # 잠그면서 발생하는 "DLL load failed" 오류(Windows)를 원천적으로 피할 수 있다.
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_SUBPROCESS_ENV,
    )
    
    if result.returncode != 0:
        print("빌드 실패:")
        print(result.stderr)
        sys.exit(1)
    
    print("빌드 완료\n")
    return result


def upload_package(test_mode=False):
    """패키지 업로드"""
    repository = "testpypi" if test_mode else "pypi"
    repo_name = "TestPyPI" if test_mode else "PyPI"
    
    print(f"{repo_name}에 업로드 중...")
    
    cmd = [sys.executable, "-m", "twine", "upload"]
    if _PYPIRC_PATH.exists():
        cmd.extend(["--config-file", str(_PYPIRC_PATH)])
    if test_mode:
        cmd.extend(["--repository", "testpypi"])
    cmd.append("dist/*")
    
    result = subprocess.run(cmd, env=_SUBPROCESS_ENV)
    
    if result.returncode != 0:
        print(f"{repo_name} 업로드 실패")
        sys.exit(1)
    
    print(f"{repo_name} 업로드 완료\n")


def main():
    """메인 실행 함수"""
    test_mode = "--test" in sys.argv
    
    print("=" * 60)
    print("helper-dev-utils PyPI 업로드")
    print("=" * 60)
    print()
    
    # 1. 빌드 디렉토리 정리
    clean_build()
    
    # 2. 패키지 빌드
    build_package()
    
    # 3. 패키지 업로드
    upload_package(test_mode)
    
    # 4. 완료 메시지
    if test_mode:
        print("TestPyPI에서 설치 테스트:")
        print("   pip install --index-url https://test.pypi.org/simple/ helper-dev-utils")
    else:
        print("PyPI에서 설치:")
        print("   pip install helper-dev-utils")
    
    print()
    print("모든 작업 완료!")


if __name__ == "__main__":
    main()
