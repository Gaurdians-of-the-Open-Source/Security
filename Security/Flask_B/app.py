from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
from unzipper import extract_zip
from analyzer import (
    load_and_group_issues,
    save_grouped_issues,
    save_piece_markdowns,
    merge_markdowns_to_pdf,
)
from utils import make_dirs
import zipfile, json, uuid, shutil, traceback

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
# make_dirs는 상위 기본 디렉토리들을 만들어 준다고 가정 (received/extracted/files/markdowns/output)
DIRS = make_dirs(BASE_DIR)

def _job_dirs(job_id: str) -> dict:
    """요청별 job_id 하위 디렉토리 생성(있으면 초기화)"""
    def _p(root: Path) -> Path:
        return root / job_id

    paths = {
        "received":   _p(DIRS["received"]),
        "extracted":  _p(DIRS["extracted"]),
        "files":      _p(DIRS["files"]),
        "markdowns":  _p(DIRS["markdowns"]),
        "output":     _p(DIRS["output"]),
    }

    # received/extracted/files/markdowns는 싹 비우고 다시 생성
    for k in ["received", "extracted", "files", "markdowns"]:
        p = paths[k]
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True, exist_ok=True)

    # output은 결과물 위치: 폴더만 보장 (덮어쓰기 허용)
    paths["output"].mkdir(parents=True, exist_ok=True)
    return paths

@app.route('/deep-analyze', methods=['POST'])
def deep_analyze():
    if 'json_file' not in request.files or 'source_zip' not in request.files:
        return jsonify({'error': 'Missing files'}), 400

    json_file  = request.files['json_file']
    source_zip = request.files['source_zip']
    if not json_file.filename or not source_zip.filename:
        return jsonify({'error': 'Empty files'}), 400

    # A가 넘겨주는 job_id를 우선 사용, 없으면 생성
    job_id = (request.form.get("job_id") or "").strip() or uuid.uuid4().hex
    J = _job_dirs(job_id)

    json_path = J['received'] / 'issues.json'
    zip_path  = J['received'] / 'source.zip'

    json_file.save(str(json_path))
    source_zip.save(str(zip_path))

    try:
        # 1) 압축 해제
        extract_zip(zip_path, J['extracted'])

        # 2) 이슈 로드/그룹화 → 원본 파일 매핑
        grouped = load_and_group_issues(json_path)
        save_grouped_issues(J['files'], grouped, J['extracted'])

        # 3) LLM 생성 마크다운 조각 → 저장
        meta = save_piece_markdowns(J['files'], J['markdowns'])
        # meta 예시: {'job_id': ..., 'processed_total': ..., 'success_count': ..., 'skipped_count': ...}

        # 4) 마크다운 병합 → PDF 생성
        #   - merge_markdowns_to_pdf가 PDF 경로를 반환하도록 구현되어 있다면 그대로 사용
        #   - 반환값이 없다면 관례적으로 output/{job_id}.pdf 사용
        pdf_path = merge_markdowns_to_pdf(J['markdowns'], J['output'], meta)
        if pdf_path is None:
            # 함수가 경로를 반환하지 않는 구현인 경우를 대비
            cand = J['output'] / f"{meta.get('job_id', job_id)}.pdf"
            if not cand.exists():
                return jsonify({'error': 'PDF not generated'}), 500
            pdf_path = cand

        # 5) 응답: Accept에 따라 PDF 또는 JSON
        accept = (request.headers.get('Accept') or '').lower()
        if 'application/pdf' in accept:
            return send_file(
                str(pdf_path),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"{job_id}.pdf"
            )

        return jsonify({
            'message': 'ok',
            'job_id': job_id,
            'total': len(grouped),
            'processed_total': meta.get('processed_total'),
            'success_count': meta.get('success_count'),
            'skipped_count': meta.get('skipped_count'),
            'pdf_path': str(pdf_path),
        }), 200

    except (zipfile.BadZipFile, json.JSONDecodeError):
        return jsonify({'error': 'Bad request: invalid zip or json'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Internal error', 'detail': str(e)}), 500

if __name__ == '__main__':
    # 기본 포트 5001 (A에서 이 포트/엔드포인트로 쏘게 하면 됩니다)
    app.run(port=5001, debug=True)
