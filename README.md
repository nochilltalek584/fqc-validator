# FQC "NG to Verify" Validator & Quality Control Dashboard

An automated, data-preserving Excel validation engine and interactive Quality-Control Dashboard for determining whether **"NG to Verify"** records in **Mahavir Files** should be classified as **Approved** or **Non-Genuine** based on lookup records in **Reference Files**.

---

## 🎯 Validation Rules Matrix

### 1. Rule 1 — Multiple Different Ticket Numbers ($\ge 2$)
If the same **Machine Serial Number** appears with **two or more different Ticket Numbers** in the Reference File:
$$\implies \mathbf{Approved}$$

### 2. Rule 2 — Single Ticket Number ($= 1$)
If the same **Machine Serial Number** appears with only **one Ticket Number** in the Reference File (even if repeated across multiple rows):
$$\implies \mathbf{Non\text{-}Genuine}$$

### 3. Special Rule — Suspension Rod Pairing
- **Front Suspension Rod** and **Rear Suspension Rod** sharing the same Machine Serial Number and same Ticket Number are treated as **ONE ticket** (not two).
- **Approval Condition**: Must contain at least **two additional Ticket Numbers** that are different from the evaluating ticket ($|U_{\text{tickets}} \setminus \{T_{\text{eval}}\}| \ge 2$).
- Otherwise:
$$\implies \mathbf{Non\text{-}Genuine}$$

### 4. 100% Data Preservation Principle
- All non-"NG to Verify" remarks (e.g. `Approved`, `DAMAGED`, blank) remain **100% untouched**.
- No rows are deleted, reordered, merged, or duplicated.
- OpenPyXL preserves original styling, dates, fonts, and formula cells.

### 5. Quality Control & Flagging
- Missing Serial Number or Serial Number not found in Reference File $\implies$ Flagged for **Manual Review** in dedicated QC worksheet and dashboard.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+ (`pip install -r backend/requirements.txt`)
- Node.js 18+ (`cd frontend && npm install`)

### One-Command Startup
```bash
python run_app.py
```
This automatically starts:
- Flask REST API on `http://127.0.0.1:5000`
- Vite React Dashboard on `http://127.0.0.1:5173`

---

## 📁 Project Structure

```
costing_project/
├── backend/
│   ├── app.py                   # Flask REST API endpoints
│   ├── validator_engine.py      # Core rule engine & OpenPyXL preservation
│   ├── sample_data_generator.py # Test dataset generator covering all rules
│   ├── test_validator.py        # Automated test suite
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx               # Navigation bar & sample downloader
│   │   │   ├── FileDropzone.jsx         # Interactive Drag & Drop card
│   │   │   ├── QCStatsCards.jsx         # Metric KPI summary cards
│   │   │   ├── AuditTable.jsx           # Filterable/searchable records table
│   │   │   └── FlaggedReviewModal.jsx   # Manual review inspector modal
│   │   ├── views/
│   │   │   ├── ValidatorView.jsx        # Dual dropzone, process & downloads
│   │   │   ├── AuditDashboardView.jsx   # Visual Recharts analytics
│   │   │   └── RuleGuideView.jsx        # Rule guide & live sandbox simulator
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── run_app.py                   # Unified launcher
└── README.md
```
