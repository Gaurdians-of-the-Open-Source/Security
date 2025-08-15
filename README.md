# 🔐 Security Logic – A↔B LLM Pipeline (README)

오픈소스 취약점 분석을 **정적분석 + LLM 리포팅**으로 자동화하는 두 개의 Flask 서비스(**Flask A**, **Flask B**) 통합 문서입니다. 사용자는 **Flask A에 ZIP 1개만 업로드**하면, A가 정적분석을 수행하고 결과를 **Flask B로 자동 전달**, B가 **LLM 기반 설명 + PDF 리포트**를 생성하여 **최종 PDF를 A가 그대로 응답**합니다.

---

## TL;DR (5분 설정)

1. Python 3.11+ (권장 3.13) 준비
2. 라이브러리 설치

   * \*\*Flask\_A/\*\*와 **Flask\_B/** 각각에서:

     ```powershell
     pip install -r requirements.txt
     ```
3. LLM 키 설정 (Anthropic Claude 3.5 Sonnet)

   ```powershell
   $env:ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. 서버 실행

   * 터미널1: `python Flask_B/app.py`  (기본: [http://127.0.0.1:5001](http://127.0.0.1:5001))
   * 터미널2: `python Flask_A/app.py`  (기본: [http://127.0.0.1:5000](http://127.0.0.1:5000))
5. 요청(사용자는 A만 호출)

   ```powershell
   curl.exe -X POST "http://127.0.0.1:5000/analyze" `
     -H "Accept: application/pdf" `
     -F "file=@C:/path/to/source.zip" `
     -o "C:/path/to/report.pdf"
   ```

---

## 아키텍처 개요

```
[Client]
   │  POST /analyze (ZIP)
   ▼
[Flask A]
   1) 업로드 ZIP 저장 → 압축해제
   2) 정적분석(Semgrep 등) → issues.json 생성
   3) forwarder.py로 Flask B /deep-analyze 에 멀티파트 전송
       ├─ form: { job_id, source_zip, json_file }
       └─ headers: { Accept: application/pdf or application/json }
   4) Flask B 응답을 그대로 클라이언트에 반환
   ▲
[Flask B]
   1) 요청 수신, job_id별 작업 폴더 초기화
   2) ZIP 저장/압축해제, issues.json 로드
   3) 파일별 이슈 그룹핑 → 원본 코드 매핑
   4) LLM으로 Markdown 조각 생성
   5) Markdown 병합 → HTML 변환 → PDF 생성(xhtml2pdf)
   6) PDF 바이너리로 즉시 응답(send_file)
```

---

## 주요 기능

* **원클릭 리포팅**: ZIP 업로드 한 번으로 PDF 리포트 다운로드
* **정적분석 + LLM**: 알려진 취약점 감지(정적분석) + 맥락 설명/개선안(LLM)
* **job\_id 격리**: 동시 요청도 안전한 디렉토리 구조
* **유연한 응답 형식**: `Accept` 헤더로 PDF/JSON 선택
* **Windows 친화적**: PowerShell, Malgun 폰트 예시 포함

---

## 디렉토리 구조

프로젝트 루트 예시:

```
Security/
├─ Flask_A/
│  ├─ app.py                 # /analyze: ZIP 업로드 → 정적분석 → B로 전달 → PDF 스트리밍 응답
│  ├─ forwarder.py           # B /deep-analyze 로 multipart 전송
│  ├─ analysis/
│  │  ├─ unzip.py            # save_and_unzip
│  │  └─ detector.py         # analyze_project → issues.json 생성
│  ├─ uploads/               # (job_id)/source.zip            # 런타임 산출물
│  └─ outputs/               # (job_id)/issues.json           # 런타임 산출물
│
├─ Flask_B/
│  ├─ app.py                 # /deep-analyze 수신 → LLM → PDF 생성 → 응답
│  ├─ unzipper.py            # extract_zip
│  ├─ analyzer.py            # load_and_group_issues, save_grouped_issues,
│  │                         # save_piece_markdowns, merge_markdowns_to_pdf
│  ├─ llm_utils.py           # Anthropic Claude 호출 (generate_llm_md)
│  ├─ utils.py               # make_dirs 등 공통 유틸
│  ├─ received/   (job_id)/  # A에서 받은 source.zip, issues.json
│  ├─ extracted/  (job_id)/  # zip 해제본
│  ├─ files/      (job_id)/  # 이슈 파일별 원본 수집
│  ├─ markdowns/  (job_id)/  # 파일별 LLM markdown 조각
│  └─ output/     (job_id)/  # 최종 report.pdf
│
├─ .gitignore
├─ README.md (본 문서)
└─ requirements.txt (A/B 각각 또는 공용)
```

> **주의**: `uploads/`, `outputs/`, `received/`, `extracted/`, `files/`, `markdowns/`, `output/`는 **런타임 산출물**로, `.gitignore`로 제외하세요. 빈 디렉토리 유지가 필요하면 `.gitkeep` 사용.

---

## 데이터 플로우 (상세)

### 1) Flask A – `/analyze`

* 입력: `multipart/form-data`

  * `file`: 프로젝트 ZIP
  * (선택) `job_id`: 미지정 시 UUID 생성
* 처리:

  1. `uploads/{job_id}/source.zip` 저장
  2. 압축해제 후 상위 1디렉토리 자동 진입(폴더 래핑 방지)
  3. `analyze_project(extracted_path)` → **issues.json** 생성
  4. `forwarder.send_to_flask_b(job_id, source.zip, issues.json, Accept)` 호출
* 출력:

  * `Accept: application/pdf` → **PDF 바이너리**
  * `Accept: application/json` → **JSON** (B가 제공하는 `pdf_path` 등 메타 정보)

### 2) Flask B – `/deep-analyze`

* 입력: `multipart/form-data`

  * `job_id` (필수)
  * `source_zip` (필수)
  * `json_file` (필수, A의 issues.json)
* 처리:

  1. `received/extracted/files/markdowns` **초기화** (job\_id별)
  2. ZIP/JSON 저장 → ZIP 압축해제
  3. `load_and_group_issues(json_path)` → 파일경로 기준 그룹핑
  4. `save_grouped_issues(files_dir, grouped, extracted_dir)` → 해당 원본 코드 조각 수집
  5. `save_piece_markdowns(files_dir, markdowns_dir)` → **LLM(Claude)** 로 마크다운 조각 생성
  6. `merge_markdowns_to_pdf(markdowns_dir, output_dir, meta)` → PDF 병합 생성
* 출력:

  * 기본: `send_file(..., mimetype="application/pdf")`로 **PDF 즉시 응답**
  * `Accept: application/json`일 때: `{ job_id, pdf_path, counts... }`

---

## 설치 & 실행

### 필수 요구사항

* Python 3.11 이상 (권장 3.13)
* OS: Windows / Linux / macOS

### 패키지 설치

A/B 각각에서:

```powershell
pip install -r requirements.txt
```

권장 `requirements.txt` 예시:

```
Flask>=3.0
flask-cors>=4.0
requests>=2.32
Markdown>=3.6
xhtml2pdf>=0.2.15
reportlab>=4.2
html5lib>=1.1
Pillow>=10.0
anthropic>=0.39.0
```

### 환경변수

* `ANTHROPIC_API_KEY` (필수): Claude 4 Sonnet 사용

  ```powershell
  $env:ANTHROPIC_API_KEY = "sk-ant-..."
  ```
* `FLASK_B_BASE_URL` (선택, 기본 `http://127.0.0.1:5001`): A→B 주소

  ```powershell
  $env:FLASK_B_BASE_URL = "http://127.0.0.1:5001"
  ```

### 서버 실행

```powershell
# 터미널 1
python Flask_B/app.py  # http://127.0.0.1:5001

# 터미널 2
python Flask_A/app.py  # http://127.0.0.1:5000
```

### 헬스체크

```powershell
curl.exe http://127.0.0.1:5001/health
curl.exe http://127.0.0.1:5000/health
```

---

## API 명세 (요약)

### A: `POST /analyze`

* 요청

  * Headers: `Accept: application/pdf | application/json`
  * Form: `file=@source.zip`, `[job_id=...]`
* 응답

  * `application/pdf` (기본)
  * 또는 JSON `{ status, job_id, ... }` (구현 선택)

### B: `POST /deep-analyze`

* 요청 (A가 내부적으로 호출)

  * Form: `job_id`, `source_zip=@source.zip`, `json_file=@issues.json`
  * Headers: `Accept: ...` (A에서 전달)
* 응답

  * `application/pdf` 바이너리
  * 또는 JSON `{ ok, job_id, pdf_path, counts... }`

---

## LLM 연동 (Anthropic Claude 4 Sonnet)

* `llm_utils.generate_llm_md(prompt)`: 파일별 이슈/코드를 입력으로 받아 **취약점 설명 + 개선 제안** 마크다운을 생성
* 모델명 예: `claude-3.5-sonnet-latest`
* 권장 프롬프트 포함 요소

  * 역할 지정(보안 리뷰어)
  * 입력 형식(이슈 JSON 요약 + 코드 스니펫)
  * 출력 형식(Markdown: Summary, Risk, Proof, Fix)
  * 코드 블록은 언어 태그 포함(\`\`\`\`python\` 등)

---

## PDF 생성

* 기본 파이프라인: **Markdown → HTML (python-Markdown) → PDF (xhtml2pdf)**
* Windows 한글 폰트 예시:

  ```css
  @font-face {
    font-family: "MalgunGothic";
    src: url("C:/Windows/Fonts/malgun.ttf");
  }
  body { font-family: "MalgunGothic"; }
  ```
* 리눅스/맥은 시스템 폰트 경로에 맞게 조정
* 대체 제너레이터: `fpdf2` / `reportlab`

---

## 에러 처리 & 트러블슈팅

* **`ModuleNotFoundError: markdown`** → `pip install Markdown`
* **`ModuleNotFoundError: anthropic`** → `pip install anthropic` + `ANTHROPIC_API_KEY` 설정
* **`KeyError: 'ANTHROPIC_API_KEY'`** → 환경변수/VSCode `launch.json` / `.env` 설정 확인
* **A에서 B 연결 실패(ForwardError/timeout)**

  * B 구동 여부, 포트/방화벽, `FLASK_B_BASE_URL` 확인
  * A→B `Accept` 헤더 전달 여부 확인
* **ZIP/JSON 파싱 오류** → `zipfile.BadZipFile`, `json.JSONDecodeError` 처리 분기 확인
* **Windows PowerShell에서 줄바꿈** → `^`(cmd) 대신 **백틱**(\`) 사용
* **PDF 한글 깨짐** → 폰트 임베딩 경로 점검

---

## 보안 고려사항

* 코드/이슈 데이터는 **민감정보가 없도록** 관리 (비밀키/토큰 업로드 금지)
* 업로드 ZIP은 **임시 저장 후 보관 기간 제한/자동 정리** 권장
* ZIP 해제 시 **zip-slip 방어**, 파일 수/총용량 상한
* LLM 프롬프트에 PII/비밀정보 유출 방지

---

## Git 운영 가이드 (산출물 제외)

* `.gitignore`로 ZIP/PDF 및 런타임 디렉토리 제외
* 이미 추적 중인 산출물 제거:

  ```powershell
  git rm -r --cached uploads outputs received extracted files markdown markdowns output
  git add .
  git commit -m "chore: untrack artifacts"
  git push
  ```

---

## 예시 코드 스니펫

**A → B 전송 (forwarder.py)**

```python
# RECEIVE_ENDPOINT = "/deep-analyze"
body, content_type, filename = send_to_flask_b(
    job_id=job_id,
    source_zip_path=zip_save_path,
    issues_json_path=issues_path,
    accept="application/pdf",
)
```

**B 응답 분기**

```python
accept = (request.headers.get('Accept') or '').lower()
if 'application/json' in accept:
    return jsonify({ 'ok': True, 'job_id': job_id, 'pdf_path': str(pdf_path) })
return send_file(str(pdf_path), mimetype='application/pdf', as_attachment=True,
                 download_name=f"{job_id}.pdf")
```

---

## 라이선스

프로젝트 루트의 `LICENSE` 참고 (미설정 시 추후 업데이트).

---

## 연락/기여

* Issue/PR 환영. 재현 스텝, 로그, 샘플 ZIP(민감정보 제거) 포함 시 빠른 대응 가능.
