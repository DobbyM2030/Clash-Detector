import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from clash_detector import detect_clashes, summarize_clashes
from pdf_export import build_clash_report

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
EXPORT_DIR = BASE_DIR / "storage" / "exports"
ALLOWED_EXTENSIONS = {"ifc"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024

CLASH_RUNS = {}


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/clashes/upload", methods=["POST"])
def upload_ifc_file():
    uploaded_file = request.files.get("ifcFile")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Please choose an IFC file to upload."}), 400

    if not is_allowed_file(uploaded_file.filename):
        return jsonify({"error": "Only .ifc files are supported."}), 400

    run_id = str(uuid.uuid4())
    safe_name = secure_filename(uploaded_file.filename)
    stored_name = f"{run_id}_{safe_name}"
    file_path = UPLOAD_DIR / stored_name
    uploaded_file.save(file_path)

    try:
        clashes = detect_clashes(file_path)
    except Exception as error:
        return jsonify({"error": f"IFC geometry analysis failed: {error}"}), 422

    summary = summarize_clashes(clashes)

    CLASH_RUNS[run_id] = {
        "runId": run_id,
        "filename": safe_name,
        "filePath": str(file_path),
        "summary": summary,
        "clashes": clashes,
    }

    return jsonify(CLASH_RUNS[run_id])


@app.route("/api/clashes/<run_id>")
def get_clash_run(run_id):
    clash_run = CLASH_RUNS.get(run_id)

    if clash_run is None:
        return jsonify({"error": "Clash run not found."}), 404

    return jsonify(clash_run)


@app.route("/api/clashes/<run_id>/export-pdf", methods=["POST"])
def export_pdf(run_id):
    clash_run = CLASH_RUNS.get(run_id)

    if clash_run is None:
        return jsonify({"error": "Clash run not found."}), 404

    pdf_path = EXPORT_DIR / f"clash-report-{run_id}.pdf"
    build_clash_report(pdf_path, clash_run)

    return send_file(pdf_path, as_attachment=True, download_name=f"{clash_run['filename']}-clash-report.pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
