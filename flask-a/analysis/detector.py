# analysis/detector.py
import os
import subprocess
import json

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".swift": "swift"
}

SEMGREP_RULESET = "auto"  # Semgrep이 자동으로 언어 감지

def find_source_files(root_dir):
    files_by_ext = {}
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            path = os.path.join(root, file)
            ext = os.path.splitext(file)[-1]
            if ext in SUPPORTED_EXTENSIONS:
                print(f"[파일 발견] {ext} - {path}")
                files_by_ext.setdefault(ext, []).append(path)
    return files_by_ext

def run_semgrep(files):
    if not files:
        return []

    try:
        result = subprocess.run(
            ["semgrep", "--json", "-f", SEMGREP_RULESET] + files,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[Semgrep 실패]", e.stderr)
        return []

def analyze_project(project_path):
    print("[정적 분석 시작] →", project_path)
    files_by_ext = find_source_files(project_path)

    all_results = []
    for ext, files in files_by_ext.items():
        print(f"[{ext}] 확장자에 대해 Semgrep 실행 ({len(files)}개)")
        result = run_semgrep(files)
        all_results.extend(result.get("results", []))

    print(f"[분석 완료] 총 발견된 취약점: {len(all_results)}개")
    return all_results
