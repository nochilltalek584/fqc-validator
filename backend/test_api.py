import io
import json
import logging
import duckdb
import pytest
import pandas as pd
from app import (
    app,
    check_file,
    extract_headers_fast,
    auto_seed_reference_db,
    HealthCheckFilter,
    VALIDATION_CACHE,
    cache_result,
    get_cache_key,
    DEFAULT_REF_DB_PATH
)
from sample_data_generator import create_sample_files
from validator_engine import ValidationError


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Core & Health Endpoints
# ---------------------------------------------------------------------------

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "reference_db" in data


def test_health_check_filter():
    filt = HealthCheckFilter()
    rec_health = logging.LogRecord("werkzeug", logging.INFO, "", 0, "GET /health HTTP/1.1", (), None)
    rec_other = logging.LogRecord("werkzeug", logging.INFO, "", 0, "POST /validate HTTP/1.1", (), None)
    assert filt.filter(rec_health) is False
    assert filt.filter(rec_other) is True


def test_auto_seed_reference_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "autoseed.duckdb")
    monkeypatch.setattr("app.DEFAULT_REF_DB_PATH", test_db)
    auto_seed_reference_db()
    assert duckdb.connect(database=test_db, read_only=True) is not None


# ---------------------------------------------------------------------------
# Sample Files Download
# ---------------------------------------------------------------------------

def test_sample_files_zip_and_individual(client):
    # 1. Default ZIP
    res_zip = client.get("/sample_files")
    assert res_zip.status_code == 200
    assert res_zip.content_type == "application/zip"

    # 2. Mahavir individual
    res_mah = client.get("/sample_files?file=mahavir")
    assert res_mah.status_code == 200
    assert "spreadsheetml" in res_mah.content_type

    # 3. Reference individual
    res_ref = client.get("/sample_files?file=reference")
    assert res_ref.status_code == 200
    assert "spreadsheetml" in res_ref.content_type


# ---------------------------------------------------------------------------
# Fast Header Extraction & Preview
# ---------------------------------------------------------------------------

def test_extract_headers_fast_all_formats(tmp_path):
    # 1. CSV
    csv_bytes = b"ColA,ColB,ColC\n1,2,3\n4,5,6\n"
    cols, count = extract_headers_fast(csv_bytes, "test.csv")
    assert cols == ["ColA", "ColB", "ColC"]
    assert count == 2

    # 2. TSV
    tsv_bytes = b"Col1\tCol2\nA\tB\n"
    cols_tsv, count_tsv = extract_headers_fast(tsv_bytes, "test.tsv")
    assert cols_tsv == ["Col1", "Col2"]
    assert count_tsv == 1

    # 3. Parquet
    pq_path = str(tmp_path / "fast.parquet")
    con = duckdb.connect()
    con.execute("CREATE TABLE fast_pq (Serial VARCHAR, Ticket VARCHAR)")
    con.execute("INSERT INTO fast_pq VALUES ('S1', 'T1'), ('S2', 'T2')")
    con.execute(f"COPY fast_pq TO '{pq_path.replace(chr(92), '/')}' (FORMAT PARQUET)")
    con.close()
    with open(pq_path, "rb") as f:
        pq_bytes = f.read()
    cols_pq, count_pq = extract_headers_fast(pq_bytes, "fast.parquet")
    assert "Serial" in cols_pq
    assert count_pq == 2

    # 4. Excel
    mah_bytes, _ = create_sample_files()
    cols_xlsx, count_xlsx = extract_headers_fast(mah_bytes, "sample.xlsx")
    assert "Machine Serial Number" in cols_xlsx
    assert count_xlsx >= 10

    # 5. Corrupted bytes
    cols_bad, count_bad = extract_headers_fast(b"not a valid file content", "corrupt.xlsx")
    assert isinstance(cols_bad, list)
    assert count_bad == 0


def test_preview_headers_api(client, tmp_path):
    mah_bytes, ref_bytes = create_sample_files()

    # 1. Preview with both Mahavir and Reference Excel files
    res = client.post("/preview_headers", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "reference": (io.BytesIO(ref_bytes), "sample_reference.xlsx")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    data = res.get_json()
    assert "mahavir" in data and "reference" in data
    assert data["reference"]["mode"] == "custom_file"
    assert "Machine Serial Number" in data["mahavir"]["columns"]

    # 2. Preview with only Mahavir (Reference falls back to Master DB mode)
    res_master = client.post("/preview_headers", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx")
    }, content_type="multipart/form-data")
    assert res_master.status_code == 200
    data_master = res_master.get_json()
    assert data_master["reference"]["mode"] == "master_db"

    # 3. Missing Mahavir file -> 400 error
    res_err = client.post("/preview_headers", data={}, content_type="multipart/form-data")
    assert res_err.status_code == 400
    assert "error" in res_err.get_json()


# ---------------------------------------------------------------------------
# Master Reference DB Management Endpoints
# ---------------------------------------------------------------------------

def test_reference_db_full_lifecycle(client, tmp_path):
    # 1. Seed sample
    seed_res = client.post("/reference_db/seed_sample")
    assert seed_res.status_code == 200
    assert seed_res.get_json()["status"] == "success"

    # 2. Get status
    status_res = client.get("/reference_db/status")
    assert status_res.status_code == 200
    assert status_res.get_json()["is_indexed"] is True

    # 3. Index new CSV file
    csv_bytes = b"Machine Serial Number,Ticket Number,Part Name\nMS100,T1001,Front Suspension Rod\nMS100,T1002,Rear Rod\n"
    index_res = client.post("/reference_db/index", data={
        "file": (io.BytesIO(csv_bytes), "custom_ref.csv")
    }, content_type="multipart/form-data")
    assert index_res.status_code == 200
    assert index_res.get_json()["metadata"]["total_records"] == 2

    # 4. Index invalid file extension -> 400
    bad_ext_res = client.post("/reference_db/index", data={
        "file": (io.BytesIO(b"data"), "custom_ref.exe")
    }, content_type="multipart/form-data")
    assert bad_ext_res.status_code == 400

    # 5. Index missing file -> 400
    no_file_res = client.post("/reference_db/index", data={}, content_type="multipart/form-data")
    assert no_file_res.status_code == 400

    # 6. Index corrupt content -> 400
    bad_content_res = client.post("/reference_db/index", data={
        "file": (io.BytesIO(b"ColA,ColB\n1,2\n"), "custom_bad.csv")
    }, content_type="multipart/form-data")
    assert bad_content_res.status_code == 400

    # 7. Clear DB
    clear_res = client.delete("/reference_db/clear")
    assert clear_res.status_code == 200
    assert clear_res.get_json()["metadata"]["is_indexed"] is False


# ---------------------------------------------------------------------------
# Validation API & Caching
# ---------------------------------------------------------------------------

def test_validate_with_custom_columns_and_caching(client):
    # Ensure sample DB seeded
    client.post("/reference_db/seed_sample")
    
    mah_bytes, ref_bytes = create_sample_files()
    
    # 1. Standard validation with custom column JSON
    res = client.post("/validate", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "reference": (io.BytesIO(ref_bytes), "sample_reference.xlsx"),
        "custom_mahavir_cols": json.dumps({"fqc": "FQC Analysis", "serial": "Machine Serial Number"}),
        "custom_ref_cols": json.dumps({"serial": "Machine Serial Number", "ticket": "Ticket Number"})
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

    # 2. Validation with invalid JSON in custom columns (safely ignored)
    res_bad_json = client.post("/validate", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "custom_mahavir_cols": "{not valid json}",
        "custom_ref_cols": "{not valid json}"
    }, content_type="multipart/form-data")
    assert res_bad_json.status_code == 200

    # 3. Cache hit check (trigger twice without custom columns)
    res_c1 = client.post("/validate", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx")
    }, content_type="multipart/form-data")
    assert res_c1.status_code == 200

    res_c2 = client.post("/validate", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx")
    }, content_type="multipart/form-data")
    assert res_c2.status_code == 200

    # 4. Direct ZIP download via query param
    res_zip = client.post("/validate?download=zip", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx")
    }, content_type="multipart/form-data")
    assert res_zip.status_code == 200
    assert res_zip.content_type == "application/zip"

    # 5. Direct ZIP download via form param
    res_zip_form = client.post("/validate", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "download": "zip"
    }, content_type="multipart/form-data")
    assert res_zip_form.status_code == 200
    assert res_zip_form.content_type == "application/zip"

    # 6. Missing Mahavir file -> 400
    res_no_mah = client.post("/validate", data={}, content_type="multipart/form-data")
    assert res_no_mah.status_code == 400


def test_cache_eviction_and_key():
    key1 = get_cache_key(b"test1", b"ref1", None)
    key2 = get_cache_key(b"test2", None, DEFAULT_REF_DB_PATH)
    assert key1 != key2

    # Test cache eviction over MAX_CACHE_SIZE
    VALIDATION_CACHE.clear()
    for i in range(6):
        cache_result(f"key_{i}", b"mah", b"qc", {"i": i})
    assert len(VALIDATION_CACHE) <= 4


# ---------------------------------------------------------------------------
# Download File API Endpoints
# ---------------------------------------------------------------------------

def test_download_file_all_types(client):
    client.post("/reference_db/seed_sample")
    mah_bytes, ref_bytes = create_sample_files()

    # 1. Download Mahavir processed file
    res_mah = client.post("/download_file", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "type": "mahavir"
    }, content_type="multipart/form-data")
    assert res_mah.status_code == 200
    assert "spreadsheetml" in res_mah.content_type

    # 2. Download QC Summary file
    res_qc = client.post("/download_file", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "type": "qc"
    }, content_type="multipart/form-data")
    assert res_qc.status_code == 200
    assert "spreadsheetml" in res_qc.content_type

    # 3. Download ZIP package
    res_zip = client.post("/download_file", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "type": "zip"
    }, content_type="multipart/form-data")
    assert res_zip.status_code == 200
    assert res_zip.content_type == "application/zip"

    # 4. Download with uploaded custom reference file
    res_custom = client.post("/download_file", data={
        "mahavir": (io.BytesIO(mah_bytes), "sample_mahavir.xlsx"),
        "reference": (io.BytesIO(ref_bytes), "sample_reference.xlsx"),
        "type": "zip"
    }, content_type="multipart/form-data")
    assert res_custom.status_code == 200

    # 5. Missing file error -> 400
    res_err = client.post("/download_file", data={}, content_type="multipart/form-data")
    assert res_err.status_code == 400


# ---------------------------------------------------------------------------
# Simulation & Check File Helper
# ---------------------------------------------------------------------------

def test_simulate_rule_all_paths(client):
    # 1. Approved normal
    res1 = client.post("/simulate_rule", json={
        "serial": "MS001", "ticket": "T1001", "part": "Pump", "ref_tickets": ["T1001", "T1002"]
    })
    assert res1.status_code == 200
    assert res1.get_json()["classification"] == "Approved"

    # 2. Non-Genuine normal
    res2 = client.post("/simulate_rule", json={
        "serial": "MS002", "ticket": "T2001", "part": "Pump", "ref_tickets": ["T2001"]
    })
    assert res2.status_code == 200
    assert res2.get_json()["classification"] == "Non-Genuine"

    # 3. Suspension rod approved
    res3 = client.post("/simulate_rule", json={
        "serial": "MS003", "ticket": "T3001", "part": "Front Suspension Rod", "ref_tickets": ["T3001", "T3002", "T3003"]
    })
    assert res3.status_code == 200
    assert res3.get_json()["classification"] == "Approved"
    assert res3.get_json()["is_suspension"] is True

    # 4. Empty payload default simulation
    res4 = client.post("/simulate_rule", json={})
    assert res4.status_code == 200


def test_check_file_helper():
    class MockFile:
        def __init__(self, filename, content=b"hello"):
            self.filename = filename
            self._content = content
        def read(self):
            return self._content

    # 1. Valid file
    assert check_file(MockFile("data.xlsx"), "Test") == b"hello"
    assert check_file(MockFile("data.csv"), "Test") == b"hello"
    assert check_file(MockFile("data.parquet"), "Test") == b"hello"

    # 2. Missing file
    with pytest.raises(ValidationError, match="missing"):
        check_file(None, "Missing")
    with pytest.raises(ValidationError, match="missing"):
        check_file(MockFile(""), "Empty")

    # 3. Invalid extension
    with pytest.raises(ValidationError, match="invalid file type"):
        check_file(MockFile("danger.exe"), "BadExt")


def test_sample_data_generator_main(tmp_path, monkeypatch):
    """Verify sample_data_generator produces valid Mahavir and Reference Excel files."""
    import sample_data_generator
    monkeypatch.chdir(tmp_path)
    sample_data_generator.main()
    assert (tmp_path / "sample_mahavir.xlsx").exists()
    assert (tmp_path / "sample_reference.xlsx").exists()



def test_api_server_error_handlers(client, monkeypatch):
    """Test 500 error handlers across all endpoints."""
    # 1. /reference_db/status error
    def mock_bad_metadata(path):
        raise RuntimeError("Metadata read failure")
    monkeypatch.setattr("app.get_db_metadata", mock_bad_metadata)
    res = client.get("/reference_db/status")
    assert res.status_code == 500
    
    # 2. /reference_db/seed_sample error
    def mock_bad_build(*args, **kwargs):
        raise RuntimeError("DB build failure")
    monkeypatch.setattr("app.build_persistent_reference_db", mock_bad_build)
    res_seed = client.post("/reference_db/seed_sample")
    assert res_seed.status_code == 500
    
    # 3. /reference_db/index generic error
    res_idx = client.post("/reference_db/index", data={
        "file": (io.BytesIO(b"Machine Serial Number,Ticket Number\n1,2\n"), "test.csv")
    }, content_type="multipart/form-data")
    assert res_idx.status_code == 500
    
    # 4. /reference_db/clear error
    def mock_bad_remove(path):
        raise RuntimeError("File delete error")
    monkeypatch.setattr("os.remove", mock_bad_remove)
    monkeypatch.setattr("os.path.exists", lambda p: True)
    res_clr = client.delete("/reference_db/clear")
    assert res_clr.status_code == 500
    
    # 5. /sample_files error
    def mock_bad_samples():
        raise RuntimeError("Sample creation failed")
    monkeypatch.setattr("app.create_sample_files", mock_bad_samples)
    res_samp = client.get("/sample_files")
    assert res_samp.status_code == 500
    
    # 6. /preview_headers error
    def mock_bad_headers(b, fn):
        raise RuntimeError("Header parse crashed")
    monkeypatch.setattr("app.extract_headers_fast", mock_bad_headers)
    res_prev = client.post("/preview_headers", data={
        "mahavir": (io.BytesIO(b"fake"), "test.xlsx")
    }, content_type="multipart/form-data")
    assert res_prev.status_code == 500
    
    # 7. /validate error
    def mock_bad_val(*args, **kwargs):
        raise RuntimeError("Validation engine crash")
    monkeypatch.setattr("app.process_validation", mock_bad_val)
    res_val = client.post("/validate", data={
        "mahavir": (io.BytesIO(b"fake"), "test.xlsx")
    }, content_type="multipart/form-data")
    assert res_val.status_code == 500
    
    # 8. /download_file error
    res_dl = client.post("/download_file", data={
        "mahavir": (io.BytesIO(b"fake"), "test.xlsx")
    }, content_type="multipart/form-data")
    assert res_dl.status_code == 500
    
    # 9. /simulate_rule error
    def mock_bad_eval(*args, **kwargs):
        raise RuntimeError("Simulate failed")
    monkeypatch.setattr("app.evaluate_record", mock_bad_eval)
    res_sim = client.post("/simulate_rule", json={"serial": "1"})
    assert res_sim.status_code == 500

