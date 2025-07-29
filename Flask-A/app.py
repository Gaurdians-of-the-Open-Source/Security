from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import json

from analysis.unzip import save_and_unzip
from analysis.detector import analyze_project

app = Flask(__name__)
CORS(app)

@app.route("/analyze", methods=["POST"])
def analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        # 1. 압축 해제
        extracted_path = save_and_unzip(file)
        print("[압축 해제 위치]", extracted_path)
        print("[압축 해제 후 내용]", os.listdir(extracted_path))

        # 2. 상위 디렉토리 1개만 있으면 내부로 진입
        subitems = os.listdir(extracted_path)
        if len(subitems) == 1:
            subdir = os.path.join(extracted_path, subitems[0])
            if os.path.isdir(subdir):
                print("[자동 진입] →", subdir)
                extracted_path = subdir

        # 3. 정적 분석 수행
        formatted = analyze_project(extracted_path)

        # 4. UUID 기반 저장
        job_id = str(uuid.uuid4())
        os.makedirs("outputs", exist_ok=True)

        # 5. issues.json 저장
        issues_path = os.path.join("outputs", f"{job_id}_issues.json")
        with open(issues_path, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)

        # 6. 응답 반환
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "issues_file": issues_path,
            "found_issues": len(formatted)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
