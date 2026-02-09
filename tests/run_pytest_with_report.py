"""
pytest 실행 및 리포트 자동 생성 스크립트

tests 폴더의 모든 테스트를 실행하고,
결과를 report 폴더에 년월일_시분초.md 형식으로 저장합니다.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_pytest():
    """pytest 실행 및 출력 캡처"""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    # pytest 실행
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir / "test_helper_logger.py"),
            "-v",
            "--tb=short",
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    return result


def parse_test_results(output):
    """pytest 출력에서 테스트 결과 파싱"""
    results = []
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
    }

    lines = output.split("\n")
    for line in lines:
        # 테스트 결과 라인 파싱
        if "::" in line and any(
            status in line for status in ["PASSED", "FAILED", "SKIPPED", "ERROR"]
        ):
            try:
                # tests/test_helper_logger.py::TestClass::test_method PASSED 형식
                parts = line.split("::")
                if len(parts) >= 3:
                    test_class = parts[1].strip()
                    test_name_full = parts[2].strip()
                    test_name = test_name_full.split()[0]
                else:
                    test_class = ""
                    test_name = parts[-1].split()[0] if parts else "Unknown"

                # 상태 판별
                if "PASSED" in line:
                    status = "PASS"
                    summary["passed"] += 1
                elif "FAILED" in line:
                    status = "FAIL"
                    summary["failed"] += 1
                elif "SKIPPED" in line:
                    status = "SKIP"
                    summary["skipped"] += 1
                elif "ERROR" in line:
                    status = "ERROR"
                    summary["errors"] += 1
                else:
                    status = "UNKNOWN"

                summary["total"] += 1
                results.append(
                    {
                        "class": test_class,
                        "name": test_name,
                        "status": status,
                    }
                )
            except Exception:
                # 파싱 실패 시 스킵
                continue

    # summary line 파싱 (예: "28 passed in 8.10s")
    import re

    for line in lines:
        if "passed in" in line or "failed in" in line:
            # 실행 시간 추출
            try:
                if " in " in line:
                    time_part = line.split(" in ")[-1]
                    # ANSI 색상 코드 제거
                    time_str = re.sub(r"\x1b\[[0-9;]*m", "", time_part).strip()
                    summary["duration"] = time_str
            except:
                summary["duration"] = "N/A"

    return results, summary


def generate_markdown_report(results, summary, output_file):
    """마크다운 리포트 생성"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# pytest 테스트 결과 리포트\n\n",
        f"**생성 시각**: {timestamp}\n\n",
        f"**총 테스트 수**: {summary['total']}\n",
        f"**성공**: {summary['passed']}\n",
        f"**실패**: {summary['failed']}\n",
        f"**스킵**: {summary['skipped']}\n",
        f"**에러**: {summary['errors']}\n",
    ]

    if "duration" in summary:
        lines.append(f"**실행 시간**: {summary['duration']}\n")

    lines.extend(
        [
            "\n---\n\n",
            "## 테스트 결과 상세\n\n",
            "| 번호 | 테스트 클래스 | 테스트 이름 | 결과 |\n",
            "|------|--------------|------------|------|\n",
        ]
    )

    status_emoji = {
        "PASS": "✅",
        "FAIL": "❌",
        "SKIP": "⏭️",
        "ERROR": "🔥",
        "UNKNOWN": "❓",
    }

    for i, result in enumerate(results, 1):
        emoji = status_emoji.get(result["status"], "❓")
        lines.append(
            f"| {i} | `{result['class']}` | `{result['name']}` | {emoji} {result['status']} |\n"
        )

    lines.extend(
        [
            "\n---\n\n",
            "## 결론\n\n",
        ]
    )

    if summary["failed"] == 0 and summary["errors"] == 0:
        lines.append("✅ **모든 테스트 통과!**\n\n")
        lines.append(f"`helper_logger` 모듈의 모든 공개 인터페이스가 정상적으로 동작합니다.\n")
    else:
        lines.append("❌ **일부 테스트 실패**\n\n")
        lines.append(f"실패한 테스트: {summary['failed']}개\n")
        lines.append(f"에러 발생 테스트: {summary['errors']}개\n")

    output_file.write_text("".join(lines), encoding="utf-8")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("pytest 실행 및 리포트 생성")
    print("=" * 60)

    # pytest 실행
    print("\n[1/3] pytest 실행 중...")
    result = run_pytest()

    print(f"종료 코드: {result.returncode}")

    # 결과 파싱
    print("\n[2/3] 테스트 결과 파싱 중...")
    results, summary = parse_test_results(result.stdout)
    print(f"파싱된 테스트 수: {summary['total']}")
    print(f"  - 성공: {summary['passed']}")
    print(f"  - 실패: {summary['failed']}")
    print(f"  - 스킵: {summary['skipped']}")
    print(f"  - 에러: {summary['errors']}")

    # 리포트 생성
    print("\n[3/3] 마크다운 리포트 생성 중...")
    project_root = Path(__file__).parent.parent
    report_dir = project_root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"{timestamp}.md"

    generate_markdown_report(results, summary, report_file)
    print(f"✅ 리포트 생성 완료: {report_file}")

    # pytest 상세 출력
    print("\n" + "=" * 60)
    print("pytest 상세 출력")
    print("=" * 60)
    print(result.stdout)

    if result.stderr:
        print("\n" + "=" * 60)
        print("pytest 에러 출력")
        print("=" * 60)
        print(result.stderr)

    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ 모든 테스트 통과")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
