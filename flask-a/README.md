# 🔐 Flask-A: Static Code Vulnerability Analyzer

This is a Flask-based backend system that performs static code analysis on uploaded source code (in `.zip` format) and outputs a JSON report of potential vulnerabilities.

## 📌 Features

- 📦 Accepts zipped source code uploads via `/analyze` endpoint
- 🔍 Automatically detects and extracts source files in multiple languages (Java, JavaScript, Python, etc.)
- 🧠 Uses Semgrep for static analysis with built-in rules
- 📄 Outputs vulnerability reports in clean, structured JSON
- 🗃 Saves results with unique job IDs for later reference

## 🚀 Quickstart

```bash
# Upload a zip file for analysis
curl -X POST -F "file=@your_project.zip" http://localhost:5000/analyze
Response:


{
  "status": "success",
  "job_id": "xxxx-xxxx",
  "result_file": "outputs/xxxx-xxxx.json"
}

📁 Folder Structure
flask-a/
├── app.py                  # Main Flask app
├── uploads/                # Uploaded zip files
├── outputs/                # Analysis results (.json)
├── analysis/
│   ├── unzip.py            # Handles saving & unzipping files
│   ├── detector.py         # Runs Semgrep on matched files
│   └── formatter.py        # Formats Semgrep output to clean JSON
└── requirements.txt        # Dependencies
🛠 Tech Stack
Python 3.10+

Flask

Semgrep for static analysis

UUID for per-upload job tracking

🧠 Future Plans
Markdown or PDF report generation

LLM integration (e.g., Deepseek-Coder) for explanation

Web dashboard frontend (React/Electron)

Support for more languages and rule customization
