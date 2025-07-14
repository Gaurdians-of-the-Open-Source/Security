# analysis/formatter.py

def format_semgrep_results(semgrep_results):
    formatted = []

    for item in semgrep_results:
        formatted.append({
            "file": item.get("path"),
            "line": item.get("start", {}).get("line"),
            "code": item.get("extra", {}).get("lines"),
            "message": item.get("extra", {}).get("message"),
            "severity": item.get("extra", {}).get("metadata", {}).get("severity", "UNKNOWN"),
            "rule": item.get("check_id")
        })

    return formatted
