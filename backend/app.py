import os
import io
import json
import zipfile
import traceback
import logging
from typing import List, Tuple, Optional
import openpyxl
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd

from validator_engine import (
    process_validation,
    ValidationError,
    evaluate_record,
    ReferenceIndex,
    is_suspension_rod,
    build_persistent_reference_db,
    get_db_metadata
)
from sample_data_generator import create_sample_files

# Filter out /health endpoint access logs from Werkzeug console output
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()

logging.getLogger("werkzeug").addFilter(HealthCheckFilter())

app = Flask(__name__)
# Allow up to 4 GB for multi-gigabyte reference database indexing
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DEFAULT_REF_DB_PATH = os.path.join(DATA_DIR, "reference_master.duckdb")


def auto_seed_reference_db():
    """Auto-seed sample master reference database if none exists yet."""
    if not os.path.exists(DEFAULT_REF_DB_PATH):
        try:
            _, ref_bytes = create_sample_files()
            build_persistent_reference_db(
                source_input=ref_bytes,
                db_path=DEFAULT_REF_DB_PATH,
                source_filename="sample_reference.xlsx"
            )
            print(f"✅ Master Reference Database auto-seeded at: {DEFAULT_REF_DB_PATH}")
        except Exception as e:
            print(f"⚠️ Could not auto-seed Master Reference DB: {e}")

# Run initial seed check
auto_seed_reference_db()


def check_file(file, label, allowed_extensions=(".xlsx", ".xls", ".csv", ".tsv", ".parquet")):
    if not file or not file.filename:
        raise ValidationError(f"'{label}' file is missing.")
    fn = file.filename.lower()
    if not any(fn.endswith(ext) for ext in allowed_extensions):
        raise ValidationError(f"'{label}': invalid file type. Allowed: {', '.join(allowed_extensions)}")
    return file.read()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "NG-to-Verify Validation & QC Dashboard",
        "version": "2.0.0",
        "reference_db": get_db_metadata(DEFAULT_REF_DB_PATH)
    })


@app.route("/reference_db/status", methods=["GET"])
def reference_db_status():
    """Returns status, record counts, and metadata of the persistent Master Reference DB."""
    try:
        meta = get_db_metadata(DEFAULT_REF_DB_PATH)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reference_db/index", methods=["POST"])
def reference_db_index():
    """Uploads and indexes a master reference file (.xlsx, .csv, .parquet, .tsv) into persistent DuckDB."""
    try:
        file = request.files.get("file")
        if not file or not file.filename:
            raise ValidationError("No master reference file provided.")
            
        data = check_file(file, "Master Reference File")
        
        meta = build_persistent_reference_db(
            source_input=data,
            db_path=DEFAULT_REF_DB_PATH,
            source_filename=file.filename
        )
        
        # Invalidate validation cache
        VALIDATION_CACHE.clear()
        
        return jsonify({
            "status": "success",
            "message": f"Successfully indexed {meta.get('total_records', 0):,} records into Master Reference Database.",
            "metadata": meta
        })
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Indexing failed: {str(e)}"}), 500


@app.route("/reference_db/seed_sample", methods=["POST"])
def reference_db_seed_sample():
    """Resets the Master Reference Database using the sample dataset."""
    try:
        _, ref_bytes = create_sample_files()
        meta = build_persistent_reference_db(
            source_input=ref_bytes,
            db_path=DEFAULT_REF_DB_PATH,
            source_filename="sample_reference.xlsx"
        )
        VALIDATION_CACHE.clear()
        return jsonify({
            "status": "success",
            "message": "Master Reference Database seeded with sample dataset.",
            "metadata": meta
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Seeding failed: {str(e)}"}), 500


@app.route("/reference_db/clear", methods=["DELETE"])
def reference_db_clear():
    """Clears the persistent Master Reference Database."""
    try:
        if os.path.exists(DEFAULT_REF_DB_PATH):
            os.remove(DEFAULT_REF_DB_PATH)
        VALIDATION_CACHE.clear()
        return jsonify({
            "status": "success",
            "message": "Master Reference Database cleared.",
            "metadata": get_db_metadata(DEFAULT_REF_DB_PATH)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to clear database: {str(e)}"}), 500


@app.route("/sample_files", methods=["GET"])
def sample_files():
    """Generates and downloads a ZIP containing sample Mahavir and Reference Excel files."""
    try:
        file_type = request.args.get("file")
        mah_bytes, ref_bytes = create_sample_files()
        
        if file_type == "mahavir":
            return send_file(
                io.BytesIO(mah_bytes),
                download_name="sample_mahavir.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif file_type == "reference":
            return send_file(
                io.BytesIO(ref_bytes),
                download_name="sample_reference.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sample_mahavir.xlsx", mah_bytes)
            zf.writestr("sample_reference.xlsx", ref_bytes)
        zip_buf.seek(0)
        
        return send_file(
            zip_buf,
            download_name="sample_test_files.zip",
            as_attachment=True,
            mimetype="application/zip"
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def extract_headers_fast(file_bytes: bytes, filename: str = "") -> Tuple[List[str], int]:
    """Lightweight read-only header and row sampling with minimal memory overhead."""
    fn = filename.lower()
    try:
        if fn.endswith((".csv", ".tsv", ".txt")):
            sep = "\t" if fn.endswith(".tsv") else ","
            df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, nrows=10)
            return [str(c).strip() for c in df.columns], len(df)
        elif fn.endswith(".parquet"):
            try:
                import tempfile
                import duckdb
                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
                    tf.write(file_bytes)
                    tf_path = tf.name
                try:
                    con = duckdb.connect()
                    rel = con.execute(f"SELECT * FROM read_parquet('{tf_path.replace(chr(92), '/')}') LIMIT 5")
                    cols = [desc[0] for desc in rel.description]
                    cnt = con.execute(f"SELECT count(*) FROM read_parquet('{tf_path.replace(chr(92), '/')}')").fetchone()[0]
                    con.close()
                    return cols, cnt
                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)
            except Exception:
                try:
                    df = pd.read_parquet(io.BytesIO(file_bytes))
                    return [str(c).strip() for c in df.columns], min(len(df), 1000)
                except Exception:
                    return [], 0
            
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        cols = []
        row_count = 0
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if not cols:
                cand = [str(c).strip() for c in row if c is not None]
                if cand:
                    cols = cand
            if any(c is not None for c in row):
                row_count += 1
            if idx > 1000:
                break
        wb.close()
        return cols, row_count
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=5, engine="openpyxl")
            return [str(c).strip() for c in df.columns], len(df)
        except Exception:
            return [], 0


@app.route("/preview_headers", methods=["POST"])
def preview_headers():
    """Returns detected columns from uploaded files without loading full workbooks into memory."""
    try:
        mah_file = request.files.get("mahavir")
        ref_file = request.files.get("reference")
        
        if not mah_file:
            raise ValidationError("Mahavir file is required for header preview.")
            
        mah_bytes = check_file(mah_file, "Mahavir File")
        mah_cols, mah_rows = extract_headers_fast(mah_bytes, mah_file.filename)
        
        ref_payload = {}
        if ref_file and ref_file.filename:
            ref_bytes = check_file(ref_file, "Reference File")
            ref_cols, ref_rows = extract_headers_fast(ref_bytes, ref_file.filename)
            ref_payload = {
                "filename": ref_file.filename,
                "columns": ref_cols,
                "rowCount": ref_rows,
                "mode": "custom_file"
            }
        else:
            db_meta = get_db_metadata(DEFAULT_REF_DB_PATH)
            ref_payload = {
                "filename": db_meta.get("source_filename") or "Master Reference DB",
                "columns": ["Machine Serial Number", "Ticket Number", "Part Name"],
                "rowCount": db_meta.get("total_records", 0),
                "mode": "master_db",
                "indexed_at": db_meta.get("indexed_at")
            }
        
        return jsonify({
            "mahavir": {
                "filename": mah_file.filename,
                "columns": mah_cols,
                "rowCount": mah_rows
            },
            "reference": ref_payload
        })
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to preview headers: {str(e)}"}), 500


import hashlib
import time

VALIDATION_CACHE = {}
MAX_CACHE_SIZE = 4


def get_cache_key(mah_bytes: bytes, ref_bytes: Optional[bytes], ref_db_path: Optional[str]) -> str:
    h = hashlib.sha256()
    h.update(mah_bytes)
    if ref_bytes:
        h.update(ref_bytes)
    elif ref_db_path and os.path.exists(ref_db_path):
        meta = get_db_metadata(ref_db_path)
        h.update(str(meta.get("indexed_at", "")).encode("utf-8"))
        h.update(str(meta.get("total_records", 0)).encode("utf-8"))
    return h.hexdigest()


def cache_result(cache_key: str, out_mah_bytes: bytes, qc_summary_bytes: bytes, stats_dict: dict):
    if len(VALIDATION_CACHE) >= MAX_CACHE_SIZE:
        oldest_key = min(VALIDATION_CACHE.keys(), key=lambda k: VALIDATION_CACHE[k]["timestamp"])
        VALIDATION_CACHE.pop(oldest_key, None)
    VALIDATION_CACHE[cache_key] = {
        "out_mah_bytes": out_mah_bytes,
        "qc_summary_bytes": qc_summary_bytes,
        "stats_dict": stats_dict,
        "timestamp": time.time()
    }


@app.route("/validate", methods=["POST"])
def validate():
    """
    Validates Mahavir file against Master Reference DB or an uploaded Reference file.
    Returns full QC statistics and audit log as JSON.
    """
    try:
        mah_file = request.files.get("mahavir")
        ref_file = request.files.get("reference")
        
        mah_bytes = check_file(mah_file, "Mahavir File")
        ref_bytes = check_file(ref_file, "Reference File") if (ref_file and ref_file.filename) else None
        
        custom_mah_cols = None
        custom_ref_cols = None
        
        if "custom_mahavir_cols" in request.form:
            try:
                custom_mah_cols = json.loads(request.form["custom_mahavir_cols"])
            except Exception:
                pass
                
        if "custom_ref_cols" in request.form:
            try:
                custom_ref_cols = json.loads(request.form["custom_ref_cols"])
            except Exception:
                pass
                
        cache_key = get_cache_key(mah_bytes, ref_bytes, DEFAULT_REF_DB_PATH)
        if cache_key in VALIDATION_CACHE and not custom_mah_cols and not custom_ref_cols:
            cached = VALIDATION_CACHE[cache_key]
            out_mah_bytes = cached["out_mah_bytes"]
            qc_summary_bytes = cached["qc_summary_bytes"]
            stats_dict = cached["stats_dict"]
        else:
            out_mah_io, qc_summary_io, stats_dict = process_validation(
                mahavir_bytes=mah_bytes,
                reference_bytes=ref_bytes,
                ref_db_path=DEFAULT_REF_DB_PATH if not ref_bytes else None,
                custom_mahavir_cols=custom_mah_cols,
                custom_ref_cols=custom_ref_cols
            )
            out_mah_bytes = out_mah_io.getvalue()
            qc_summary_bytes = qc_summary_io.getvalue()
            cache_result(cache_key, out_mah_bytes, qc_summary_bytes, stats_dict)
        
        # Check if user requested direct ZIP download
        if request.args.get("download") == "zip" or request.form.get("download") == "zip":
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("processed_mahavir.xlsx", out_mah_bytes)
                zf.writestr("qc_validation_summary.xlsx", qc_summary_bytes)
                zf.writestr("audit_metrics.json", json.dumps(stats_dict, indent=2))
            zip_buf.seek(0)
            return send_file(
                zip_buf,
                download_name="fqc_validated_package.zip",
                as_attachment=True,
                mimetype="application/zip"
            )
            
        return jsonify({
            "status": "success",
            "stats": stats_dict
        })
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route("/download_file", methods=["POST"])
def download_file():
    """Serves the requested file instantly from cache or processes on the fly."""
    try:
        file_type = request.form.get("type", "zip")
        mah_file = request.files.get("mahavir")
        ref_file = request.files.get("reference")
        
        mah_bytes = check_file(mah_file, "Mahavir File")
        ref_bytes = check_file(ref_file, "Reference File") if (ref_file and ref_file.filename) else None
        
        cache_key = get_cache_key(mah_bytes, ref_bytes, DEFAULT_REF_DB_PATH)
        if cache_key in VALIDATION_CACHE:
            cached = VALIDATION_CACHE[cache_key]
            out_mah_bytes = cached["out_mah_bytes"]
            qc_summary_bytes = cached["qc_summary_bytes"]
            stats_dict = cached["stats_dict"]
        else:
            out_mah_io, qc_summary_io, stats_dict = process_validation(
                mahavir_bytes=mah_bytes,
                reference_bytes=ref_bytes,
                ref_db_path=DEFAULT_REF_DB_PATH if not ref_bytes else None
            )
            out_mah_bytes = out_mah_io.getvalue()
            qc_summary_bytes = qc_summary_io.getvalue()
            cache_result(cache_key, out_mah_bytes, qc_summary_bytes, stats_dict)
        
        if file_type == "mahavir":
            return send_file(
                io.BytesIO(out_mah_bytes),
                download_name="processed_mahavir.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif file_type == "qc":
            return send_file(
                io.BytesIO(qc_summary_bytes),
                download_name="qc_validation_summary.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else: # zip
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("processed_mahavir.xlsx", out_mah_bytes)
                zf.writestr("qc_validation_summary.xlsx", qc_summary_bytes)
                zf.writestr("audit_metrics.json", json.dumps(stats_dict, indent=2))
            zip_buf.seek(0)
            return send_file(
                zip_buf,
                download_name="fqc_validated_package.zip",
                as_attachment=True,
                mimetype="application/zip"
            )
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/simulate_rule", methods=["POST"])
def simulate_rule():
    """Interactive Rule Sandbox API."""
    try:
        data = request.get_json() or {}
        serial = data.get("serial", "MS001")
        ticket = data.get("ticket", "T1001")
        part_name = data.get("part", "Drain Pump")
        
        # Build mock reference DF from ref_items (if provided) or ref_tickets
        ref_items = data.get("ref_items")
        if ref_items and isinstance(ref_items, list):
            ref_rows = []
            for item in ref_items:
                if isinstance(item, dict):
                    ref_rows.append({
                        "Machine Serial Number": item.get("serial", serial),
                        "Ticket Number": item.get("ticket", ""),
                        "Part Name": item.get("part", part_name)
                    })
                else:
                    ref_rows.append({
                        "Machine Serial Number": serial,
                        "Ticket Number": str(item),
                        "Part Name": part_name
                    })
            ref_df = pd.DataFrame(ref_rows)
        else:
            ref_tickets = data.get("ref_tickets", ["T1001", "T1002"])
            ref_df = pd.DataFrame([
                {"Machine Serial Number": serial, "Ticket Number": t, "Part Name": part_name}
                for t in ref_tickets
            ])
        
        ref_index = ReferenceIndex(source=ref_df, serial_col="Machine Serial Number", ticket_col="Ticket Number", part_col="Part Name")
        
        rec = evaluate_record(
            row_idx=1,
            serial=serial,
            ticket=ticket,
            part_name=part_name,
            original_fqc="NG to Verify",
            ref_index=ref_index
        )
        ref_index.close()
        
        return jsonify(rec)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

