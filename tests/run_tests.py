"""
pytest 실행 및 리포트 생성 스크립트

tests 폴더의 모든 테스트를 실행하고,
결과를 report 폴더에 마크다운 테이블로 저장합니다.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json


def run_pytest_with_json():
    """pytest를 JSON 리포트 형식으로 실행"""
    tests_dir = Path(__file__).parent.parent / "tests"

    # pytest 실행 (JSON 출력)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=pytest_report.json",
        ],
        capture_output=True,
        text=True,
    )

    return result


def parse_pytest_output(stdout, stderr):
    """pytest 출력 파싱하여 테스트 결과 추출"""
    results = []

    lines = stdout.split("\n")
    for line in lines:
        if "::" in line and (
            "PASSED" in line or "FAILED" in line or "SKIPPED" in line or "ERROR" in line
        ):
            # 테스트 라인 파싱
            parts = line.split("::")
            if len(parts) >= 2:
                test_file = parts[0].strip()
                rest = "::".join(parts[1:])

                # 상태 추출
                status = "UNKNOWN"
                if "PASSED" in rest:
                    status = "PASS"
                elif "FAILED" in rest:
                    status = "FAIL"
                elif "SKIPPED" in rest:
                    status = "SKIP"
                elif "ERROR" in rest:
                    status = "ERROR"

                # 테스트 이름 추출
                test_name = rest.split()[0].strip()

                results.append(
                    {
                        "file": test_file,
                        "name": test_name,
                        "status": status,
                    }
                )

    return results


def generate_markdown_report(results, output_file):
    """마크다운 테이블 형식 리포트 생성"""
    report_lines = [
        "# pytest 테스트 결과 리포트\n",
        f"**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**총 테스트 수**: {len(results)}\n",
        f"**성공**: {sum(1 for r in results if r['status'] == 'PASS')}\n",
        f"**실패**: {sum(1 for r in results if r['status'] == 'FAIL')}\n",
        f"**스킵**: {sum(1 for r in results if r['status'] == 'SKIP')}\n",
        f"**에러**: {sum(1 for r in results if r['status'] == 'ERROR')}\n",
        "\n---\n\n",
        "## 테스트 결과 상세\n\n",
        "| 번호 | 테스트 파일 | 테스트 이름 | 결과 |\n",
        "|------|------------|------------|------|\n",
    ]

    for i, result in enumerate(results, 1):
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌",
            "SKIP": "⏭️",
            "ERROR": "🔥",
            "UNKNOWN": "❓",
        }

        emoji = status_emoji.get(result["status"], "❓")
        report_lines.append(
            f"| {i} | `{result['file']}` | `{result['name']}` | {emoji} {result['status']} |\n"
        )

    output_file.write_text("".join(report_lines), encoding="utf-8")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("pytest 실행 및 리포트 생성")
    print("=" * 60)

    # pytest 실행
    print("\n[1단계] pytest 실행 중...")
    result = run_pytest_with_json()

    print(f"\n종료 코드: {result.returncode}")
    if result.returncode == 0:
        print("✅ 모든 테스트 통과")
    else:
        print("❌ 일부 테스트 실패")

    # 결과 파싱
    print("\n[2단계] 테스트 결과 파싱 중...")
    results = parse_pytest_output(result.stdout, result.stderr)
    print(f"파싱된 테스트 수: {len(results)}")

    # 리포트 생성
    print("\n[3단계] 마크다운 리포트 생성 중...")
    report_dir = Path(__file__).parent.parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"{timestamp}.md"

    generate_markdown_report(results, report_file)
    print(f"✅ 리포트 생성 완료: {report_file}")

    # pytest stdout 출력
    print("\n" + "=" * 60)
    print("pytest 출력")
    print("=" * 60)
    print(result.stdout)

    if result.stderr:
        print("\n" + "=" * 60)
        print("pytest 에러")
        print("=" * 60)
        print(result.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
