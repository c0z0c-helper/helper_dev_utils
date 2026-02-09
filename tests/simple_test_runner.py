"""
간단한 pytest 실행 및 리포트 생성 스크립트
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("pytest 실행 및 리포트 생성")
    print("=" * 60)

    # pytest 실행
    print("\n[1단계] pytest 실행 중...")

    tests_dir = Path(__file__).parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir / "test_helper_logger.py"),
            "-v",
            "--tb=line",
        ],
        capture_output=True,
        text=True,
        cwd=tests_dir.parent,
    )

    print(f"\n종료 코드: {result.returncode}")

    # 출력 파싱
    results = []
    for line in result.stdout.split("\n"):
        if "::" in line and any(
            status in line for status in ["PASSED", "FAILED", "SKIPPED", "ERROR"]
        ):
            # 간단한 파싱
            if "PASSED" in line:
                status = "PASS"
            elif "FAILED" in line:
                status = "FAIL"
            elif "SKIPPED" in line:
                status = "SKIP"
            else:
                status = "ERROR"

            test_name = line.split("::")[1].split()[0] if "::" in line else "Unknown"
            results.append({"name": test_name, "status": status})

    # 리포트 생성
    print("\n[2단계] 마크다운 리포트 생성 중...")
    report_dir = tests_dir.parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"{timestamp}.md"

    # 리포트 작성
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# pytest 테스트 결과 리포트\n\n")
        f.write(f"**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**총 테스트 수**: {len(results)}\n")
        f.write(f"**성공**: {sum(1 for r in results if r['status'] == 'PASS')}\n")
        f.write(f"**실패**: {sum(1 for r in results if r['status'] == 'FAIL')}\n")
        f.write(f"**스킵**: {sum(1 for r in results if r['status'] == 'SKIP')}\n")
        f.write(f"**에러**: {sum(1 for r in results if r['status'] == 'ERROR')}\n\n")
        f.write("---\n\n")
        f.write("## 테스트 결과 상세\n\n")
        f.write("| 번호 | 테스트 이름 | 결과 |\n")
        f.write("|------|------------|------|\n")

        for i, result in enumerate(results, 1):
            emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "ERROR": "🔥"}.get(
                result["status"], "❓"
            )
            f.write(f"| {i} | `{result['name']}` | {emoji} {result['status']} |\n")

    print(f"✅ 리포트 생성 완료: {report_file}")

    # 출력
    print("\n" + "=" * 60)
    print("pytest 출력")
    print("=" * 60)
    print(result.stdout)

    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
