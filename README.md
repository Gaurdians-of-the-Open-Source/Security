# 🔐 Security Logic — A↔B LLM Pipeline (README)

This repository automates open‑source security reviews by combining **static analysis** with **LLM‑assisted reporting** across two Flask services: **Flask A** (ingest + static analysis) and **Flask B** (LLM markdown generation + PDF rendering). A client only uploads a single ZIP to **Flask A**; A analyzes and forwards artifacts to **Flask B**, which returns a **final PDF**. A simply streams B’s response back to the client.

---

## TL;DR (5‑minute setup)

1. **Python**: 3.11+ (3.13 recommended)
2. **Install deps** (in both `Flask_A/` and `Flask_B/`):

   ```powershell
   pip install -r requirements.txt
   ```
3. **LLM key & model** (Anthropic Claude **Sonnet 4**):

   ```powershell
   $env:ANTHROPIC_API_KEY = "sk-ant-..."
   $env:ANTHROPIC_MODEL = "sonnet-4"   # or provider alias, e.g. "claude-sonnet-4-latest"
   ```
4. **Run servers**

   * Terminal 1: `python Flask_B/app.py`  → [http://127.0.0.1:5001](http://127.0.0.1:5001)
   * Terminal 2: `python Flask_A/app.py`  → [http://127.0.0.1:5000](http://127.0.0.1:5000)
5. **Call A (client only hits A):**

   ```powershell
   curl.exe -X POST "http://127.0.0.1:5000/analyze" `
     -H "Accept: application/pdf" `
     -F "file=@C:/path/to/source.zip" `
     -o "C:/path/to/report.pdf"
   ```

---

## Architecture

```
[Client]
   │  POST /analyze (ZIP)
   ▼
[Flask A]
   1) Save ZIP  → unzip
   2) Static analysis (e.g., Semgrep) → issues.json
   3) POST multipart to Flask B /deep-analyze
       form: { job_id, source_zip, json_file }
       headers: { Accept: application/pdf | application/json }
   4) Stream B’s response back to client
   ▲
[Flask B]
   1) Init job directories (by job_id)
   2) Save + unzip ZIP, load issues.json
   3) Group issues by file → map to source
   4) Generate per‑file Markdown with LLM (Sonnet 4)
   5) Merge Markdown → HTML → PDF (xhtml2pdf)
   6) Return PDF (or JSON metadata)
```

---

## Key Features

* **One‑shot reporting**: upload ZIP → receive PDF
* **Static analysis + LLM**: known pattern detection + human‑readable remediation
* **Job isolation**: per‑`job_id` working directories (safe for concurrency)
* **Flexible response**: choose PDF or JSON via `Accept` header
* **Windows‑friendly**: PowerShell examples, font hints

---

## Project Layout

```
Security/
├─ Flask_A/
│  ├─ app.py                 # /analyze: ingest ZIP → static analysis → forward to B → stream PDF
│  ├─ forwarder.py           # posts multipart to B /deep-analyze
│  ├─ analysis/
│  │  ├─ unzip.py            # save_and_unzip
│  │  └─ detector.py         # analyze_project → issues.json
│  ├─ uploads/               # (job_id)/source.zip         (runtime)
│  └─ outputs/               # (job_id)/issues.json        (runtime)
│
├─ Flask_B/
│  ├─ app.py                 # /deep-analyze → LLM → PDF → response
│  ├─ unzipper.py            # extract_zip
│  ├─ analyzer.py            # load_and_group_issues, save_grouped_issues,
│  │                         # save_piece_markdowns, merge_markdowns_to_pdf
│  ├─ llm_utils.py           # Anthropic Sonnet 4 client (generate_llm_md)
│  ├─ utils.py               # make_dirs, etc.
│  ├─ received/   (job_id)/  # A’s source.zip, issues.json
│  ├─ extracted/  (job_id)/  # unzipped tree
│  ├─ files/      (job_id)/  # collected source slices by issue
│  ├─ markdowns/  (job_id)/  # per‑file LLM markdown pieces
│  └─ output/     (job_id)/  # final report.pdf
│
├─ .gitignore
├─ README.md (this file)
└─ requirements.txt (per service or shared)
```

> **Note:** `uploads/`, `outputs/`, `received/`, `extracted/`, `files/`, `markdowns/`, `output/` are **runtime artifacts** and must be ignored by Git. Use `.gitkeep` if you want empty directories tracked.

---

## Data Flow (Detailed)

### A — `POST /analyze`

**Input** (multipart/form-data)

* `file`: project ZIP
* `job_id` *(optional)*: if omitted, A generates a UUID

**Process**

1. Save to `uploads/{job_id}/source.zip`
2. Unwrap single top‑level directory if present (avoid nested folder wrappers)
3. Run `analyze_project(extracted_path)` → write **issues.json**
4. Call `forwarder.send_to_flask_b(job_id, source.zip, issues.json, Accept)`

**Output**

* With `Accept: application/pdf` → **PDF** (binary)
* With `Accept: application/json` → **JSON** (B’s `pdf_path`, counts, etc.)

### B — `POST /deep-analyze`

**Input** (multipart/form-data)

* `job_id`, `source_zip`, `json_file`

**Process**

1. Reset job directories (`received/`, `extracted/`, `files/`, `markdowns/`)
2. Save + unzip ZIP; load `issues.json`
3. `load_and_group_issues(json_path)` → group by file/location
4. `save_grouped_issues(files_dir, grouped, extracted_dir)` → map to code
5. `save_piece_markdowns(files_dir, markdowns_dir)` → **LLM (Sonnet 4)** generates Markdown blocks
6. `merge_markdowns_to_pdf(markdowns_dir, output_dir, meta)` → final PDF

**Output**

* Default: `send_file(..., mimetype="application/pdf")`
* If `Accept: application/json`: `{ job_id, pdf_path, counts... }`

---

## Installation & Running

### Requirements

* Python 3.11+ (3.13 recommended)
* OS: Windows / Linux / macOS

### Dependencies

Run in each service directory:

```powershell
dir Flask_A; pip install -r Flask_A/requirements.txt

dir Flask_B; pip install -r Flask_B/requirements.txt
```

**Suggested `requirements.txt`:**

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

### Environment Variables

* `ANTHROPIC_API_KEY` *(required)*
* `ANTHROPIC_MODEL` *(optional, default: `sonnet-4`)*
* `FLASK_B_BASE_URL` *(optional, default: `http://127.0.0.1:5001`)*

PowerShell example:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:ANTHROPIC_MODEL = "sonnet-4"
$env:FLASK_B_BASE_URL = "http://127.0.0.1:5001"
```

### Run

```powershell
# Terminal 1
python Flask_B/app.py  # http://127.0.0.1:5001

# Terminal 2
python Flask_A/app.py  # http://127.0.0.1:5000
```

### Health Checks

```powershell
curl.exe http://127.0.0.1:5001/health
curl.exe http://127.0.0.1:5000/health
```

---

## API Reference (Quick)

### A — `POST /analyze`

* **Headers**: `Accept: application/pdf | application/json`
* **Form**: `file=@source.zip`, `[job_id=...]`
* **Returns**: PDF or JSON

### B — `POST /deep-analyze`

* **Form**: `job_id`, `source_zip=@...`, `json_file=@...`
* **Returns**: PDF or JSON metadata

---

## LLM Integration — **Sonnet 4**

Example `llm_utils.py` (simplified):

```python
from anthropic import Anthropic
import os

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

MODEL = os.getenv("ANTHROPIC_MODEL", "sonnet-4")  # e.g., "sonnet-4" or provider alias
client = Anthropic(api_key=API_KEY)

def generate_llm_md(prompt: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text
```

**Prompting tips**

* Role: security reviewer
* Inputs: issue summary + relevant code snippet(s)
* Output: Markdown sections (Summary, Impact, Evidence, Fix), fenced code blocks with language tags

---

## PDF Rendering

Default pipeline: **Markdown → HTML (python‑Markdown) → PDF (xhtml2pdf)**.

Windows font example (to prevent CJK garbling):

```css
@font-face { font-family: "MalgunGothic"; src: url("C:/Windows/Fonts/malgun.ttf"); }
body { font-family: "MalgunGothic"; }
```

Alternative generators: `fpdf2` or `reportlab`.

---

## Troubleshooting

* `ModuleNotFoundError: markdown` → `pip install Markdown`
* `ModuleNotFoundError: anthropic` → `pip install anthropic` + set `ANTHROPIC_API_KEY`
* `KeyError: 'ANTHROPIC_API_KEY'` → set env var or use `.env` / VS Code `launch.json`
* A→B forwarding errors (timeout/refused) → ensure B is running; verify `FLASK_B_BASE_URL`
* Bad ZIP/JSON → catch `zipfile.BadZipFile`, `json.JSONDecodeError`
* PowerShell line continuation → use backticks (`` ` ``), not `^`
* PDF font issues → verify font path in CSS/@font-face

---

## Security Considerations

* Avoid secrets/PII in uploaded archives
* Limit ZIP size / file count; defend against zip‑slip
* Auto‑prune runtime artifacts (`received/`, `extracted/`, etc.)
* Prompt templates should minimize leakage of sensitive context

---

## Git Hygiene (exclude artifacts)

Sample `.gitignore` highlights:

```
__pycache__/
*.pyc
*.log
*.zip
*.pdf
uploads/**
outputs/**
received/**
extracted/**
files/**
markdown/**
markdowns/**
output/**
!**/.gitkeep
```

To untrack already committed artifacts:

```powershell
git rm -r --cached uploads outputs received extracted files markdown markdowns output
git add .
git commit -m "chore: untrack artifacts"
```

---





## 연락/기여

* Issue/PR 환영. 재현 스텝, 로그, 샘플 ZIP(민감정보 제거) 포함 시 빠른 대응 가능.
