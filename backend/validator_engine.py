import io
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Set


class ValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Column Matchers & Helpers
# ---------------------------------------------------------------------------

SERIAL_ALIASES = [
    "machine serial number", "machine serial no", "machine serial no.",
    "machine_serial_no", "machine_serial_number", "machine_sl_no", "machine sl no",
    "m/c  sl.no.", "m/c sl.no.", "m/c sl no", "m/c sl.no", "m/c.sl.no", "m/c. sl.no.",
    "m/c serial no", "m/c serial no.", "m/c_sl_no", "mc_sl_no", "mc sl no", "mc sl.no.",
    "serial no", "serial no.", "serial number", "serial_no", "serial_number", "serial",
    "sl no", "sl no.", "sl.no.", "sl.no", "sl_no", "sl.#", "sl #",
    "equipment serial no", "unit serial no", "device serial no", "m/c no", "mc no",
    "sr_no", "sr.no", "sr.no.", "sr no", "sr no."
]

TICKET_ALIASES = [
    "ticket number", "ticket no", "ticket no.", "ticket_no", "ticket_number",
    "ticket", "tickets", "tkt no", "tkt no.", "tkt_no", "tkt_number", "ticket #", "tkt #",
    "call no", "call no.", "call_no", "call number", "call_number", "call id", "call_id", "call#",
    "complaint no", "complaint no.", "complaint_no", "complaint number", "complaint_number",
    "job no", "job no.", "job_no", "job number", "job card no", "job_card_no", "jobcard no",
    "service order", "service order no", "service_order_no", "service_order",
    "notification", "notification no", "notification_no", "notification #",
    "order no", "order number", "order_no", "order #",
    "token no", "token_no", "token number", "case no", "case number", "case_no",
    "request no", "request_no", "request number", "c/n no", "cn no", "incident no", "incident_no"
]

FQC_ALIASES = [
    "fqc analysis", "fqc verification", "fqc_analysis", "fqc_verification",
    "fqc", "fqc remarks", "fqc remark", "fqc status", "fqc action",
    "remarks", "remark", "status", "verification", "action", "decision"
]

PART_ALIASES = [
    "part", "part name", "part description", "part_name", "part_description",
    "part cat", "part category", "part_cat", "item description", "material description",
    "item name", "material name", "component", "spares description", "spare part", "item"
]


def find_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    """Find the best matching column name from aliases."""
    normalized_cols = {str(c).strip().lower(): c for c in columns if c is not None}
    
    # 1. Exact alias match
    for alias in aliases:
        if alias in normalized_cols:
            return normalized_cols[alias]
            
    # 2. Substring match (prioritizing longer alias matches to prevent false positives)
    for alias in sorted(aliases, key=len, reverse=True):
        for norm, orig in normalized_cols.items():
            if alias in norm or (len(norm) >= 4 and norm in alias):
                return orig
                
    return None


def clean_val_str(val: Any) -> str:
    """Normalize any string, float, integer or cell value."""
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).replace("\xa0", " ").strip()
    # Strip trailing float formatting e.g. 1001.0 -> 1001
    if s.endswith(".0") and (s[:-2].isdigit() or s[:-2].replace("-", "").isdigit()):
        s = s[:-2]
    return " ".join(s.split())



def normalize_serial(val: Any) -> str:
    """Normalize serial number."""
    return clean_val_str(val)


def normalize_ticket(val: Any) -> str:
    """Normalize ticket number."""
    return clean_val_str(val)


def normalize_str(val: Any) -> str:
    if val is None or pd.isna(val):
        return ""
    return str(val).replace("\xa0", " ").strip()


def normalize_part_key(val: Any) -> str:
    """
    Normalizes a part name into a canonical token-ordered key for robust part comparison.
    - If suspension rod or companion component: returns '__suspension_rod__'
    - Standard parts: stripped, lowercase, alphanumeric tokens sorted alphabetically
      (e.g., 'Drain Pump' -> 'drain pump', 'Pump Drain' -> 'drain pump', 'PCB Main' -> 'main pcb').
    - Empty/missing values return ''.
    """
    if val is None or pd.isna(val):
        return ""
    s = normalize_str(val).lower()
    if not s:
        return ""
    if is_suspension_rod(s):
        return "__suspension_rod__"
    clean = re.sub(r'[^a-z0-9]+', ' ', s)
    tokens = sorted([t for t in clean.split() if t])
    return " ".join(tokens)


import os
import datetime
import shutil

EXPLICIT_NON_SUSPENSION_KEYWORDS = {
    "motor", "pump", "valve", "pcb", "pulsator", "sensor", "switch",
    "clutch", "belt", "harness", "board", "display", "capacitor",
    "filter", "hose", "pipe", "knob", "timer", "panel", "door",
    "gasket", "seal", "heater", "fan", "blower", "transformer",
    "magnetron", "drain", "inlet", "gearbox", "pulley", "agitator",
    "dispenser", "drum", "bearing", "compressor", "relay", "magneto"
}


def is_suspension_rod(part_name: Any) -> bool:
    """
    Robustly detect if part is a Suspension Rod (Front, Rear, Pair, Set, or abbreviation).
    Supports both spaced ("SUS ASLY REAR") and concatenated codes ("SUSASLY6.5SSREARCBWG").
    Guarantees that non-suspension components (Motors, Pumps, PCBs, Valves, etc.) are NEVER misclassified.
    """
    p = normalize_str(part_name).lower()
    if not p:
        return False
    
    clean = re.sub(r'[^a-z0-9]', ' ', p)
    words = clean.split()
    word_set = set(words)
    
    # 1. Guard against non-suspension parts (word-level or substring)
    if any(k in word_set or (len(k) >= 3 and k in p) for k in EXPLICIT_NON_SUSPENSION_KEYWORDS):
        return False

    # 2. Direct full keywords
    if "suspension" in p or "damper rod" in p or "balance rod" in p or "spring rod" in p or "fricdamper" in p or "friction damper" in p:
        return True
        
    # 3. Check concatenated abbreviations (e.g., susasly, suspassy, susrod, susfront, susrear)
    if re.search(r'sus(p)?(asly|assy|rod|spring|bar|damper|strut|leg|arm)', p):
        return True
    if re.search(r'sus(p)?.*?(rear|front|damper|rod|spring|asly|assy|pair|set)', p):
        return True
    if re.search(r'(rear|front|fr|rr|fl|rl).*?sus(p)?', p):
        return True
        
    # 4. Check suspension abbreviations (sus / susp) with word context
    has_susp = any(w == "sus" or w == "susp" or w.startswith("susp") or w.startswith("sus") for w in words)
    has_rod_context = any(w in word_set for w in [
        "rod", "rods", "spring", "springs", "bar", "damper", "strut", "asly", "assy", "kit", "pair", "set", "leg", "arm", "front", "rear", "fr", "rr", "fl", "rl", "f", "r", "lh", "rh"
    ])
    
    if has_susp and has_rod_context:
        return True

    # 5. Check "rod" with directional/function indicator (e.g., "Front Rod", "Rear Rod", "Damper Rod")
    if "rod" in word_set and any(w in word_set for w in ["front", "rear", "fr", "rr", "fl", "rl", "f", "r", "lh", "rh", "spring", "damper", "balance"]):
        return True
            
    # 6. Regex fallback for hyphenated/slashed codes e.g. "F-SUSP", "SUSP-ROD", "ROD/SUSP", "SUS.ROD", "SUS-ASLY"
    pattern = r'\b(susp?|sus)\b.*?\b(rod|spring|bar|damper|strut|asly|assy|pair|set|fr|rr|front|rear|f|r)\b|\b(rod|spring|bar|damper|strut|asly|assy|front|rear|fr|rr|f|r)\b.*?\b(susp?|sus)\b'
    if re.search(pattern, clean):
        return True
        
    return False


def is_rod_or_suspension_like(part_name: Any) -> bool:
    """Check if part name could be a companion suspension rod or component."""
    p = normalize_str(part_name).lower()
    if not p:
        return False
        
    clean = re.sub(r'[^a-z0-9]', ' ', p)
    words = set(clean.split())
    
    # Exclude non-suspension parts
    if any(k in words for k in EXPLICIT_NON_SUSPENSION_KEYWORDS):
        return False
        
    if is_suspension_rod(p):
        return True
        
    explicit_rod_terms = {"damper", "strut", "balance rod", "front rod", "rear rod", "fr rod", "rr rod", "susp rod", "sus asly", "spring", "springs", "rod", "rods"}
    return any(term in p for term in explicit_rod_terms)


def extract_tickets(val: Any) -> List[str]:
    """Extract one or multiple ticket numbers from a cell (handles commas, slashes, semicolons, newlines)."""
    s = normalize_str(val)
    if not s:
        return []
    # Split on comma, slash, semicolon, newline, pipe, ampersand
    tokens = re.split(r'[,/;\n|&]+', s)
    results = []
    for t in tokens:
        clean = clean_val_str(t)
        if clean:
            results.append(clean)
    return results if results else [clean_val_str(s)]


def is_ng_to_verify(val: Any) -> bool:
    """Robustly detect 'NG to Verify' in any casing, spacing, punctuation, or variation."""
    s = normalize_str(val).lower()
    if not s:
        return False
    if s in ["ng to verify", "ng-to-verify", "ng_to_verify", "ng to verification", "ng verify"]:
        return True
    clean = re.sub(r'[^a-z0-9]', ' ', s)
    clean = " ".join(clean.split())
    if "ng" in clean and ("verify" in clean or "verifi" in clean or "check" in clean):
        return True
    return False


import duckdb
import gc


# ---------------------------------------------------------------------------
# Reference File Indexer (DuckDB-Powered Columnar Engine)
# ---------------------------------------------------------------------------

class ReferenceIndex:
    """
    High-performance, low-memory Reference Index powered by DuckDB.
    Supports both persistent on-disk pre-indexed databases (instant zero-latency lookups)
    and on-the-fly in-memory token indexing.
    """
    def __init__(
        self,
        source: Any = None,
        serial_col: Optional[str] = None,
        ticket_col: Optional[str] = None,
        part_col: Optional[str] = None,
        db_path: Optional[str] = None
    ):
        self.serial_col = serial_col
        self.ticket_col = ticket_col
        self.part_col = part_col
        self.db_path = db_path
        
        if db_path and os.path.exists(db_path):
            # Connect to existing persistent DuckDB index in read-only mode (instant)
            self.con = duckdb.connect(database=db_path, read_only=True)
            self.con.execute("PRAGMA threads=4;")
        else:
            # In-memory embedded DuckDB instance
            self.con = duckdb.connect(database=":memory:")
            self.con.execute("PRAGMA threads=4;")
            self.con.execute("PRAGMA max_memory='1GB';")
            
            # Base token table
            self.con.execute("""
                CREATE TABLE ref_tokens (
                    serial VARCHAR,
                    serial_key VARCHAR,
                    ticket VARCHAR,
                    ticket_key VARCHAR,
                    part VARCHAR,
                    part_key VARCHAR,
                    is_suspension BOOLEAN
                );
            """)
            
            if source is not None:
                self._build_index(source)

    def _build_index(self, source: Any):
        batch = []
        BATCH_SIZE = 10000
        
        def flush_batch():
            nonlocal batch
            if batch:
                self.con.executemany(
                    "INSERT INTO ref_tokens VALUES (?, ?, ?, ?, ?, ?, ?)",
                    batch
                )
                batch = []

        if isinstance(source, pd.DataFrame):
            serial_series = source[self.serial_col] if (self.serial_col and self.serial_col in source.columns) else [None] * len(source)
            ticket_series = source[self.ticket_col] if (self.ticket_col and self.ticket_col in source.columns) else [None] * len(source)
            part_series = source[self.part_col] if (self.part_col and self.part_col in source.columns) else [None] * len(source)
            
            for raw_serial, raw_ticket, raw_part in zip(serial_series, ticket_series, part_series):
                serial = normalize_serial(raw_serial)
                part = normalize_str(raw_part)
                is_susp = is_suspension_rod(part)
                p_key = normalize_part_key(part)
                tickets = extract_tickets(raw_ticket)
                
                if not serial and not tickets:
                    continue
                    
                s_key = serial.lower() if serial else ""
                
                if not tickets:
                    batch.append((serial, s_key, "", "", part, p_key, is_susp))
                    if len(batch) >= BATCH_SIZE:
                        flush_batch()
                else:
                    for t in tickets:
                        t_clean = t.strip()
                        if serial or t_clean:
                            batch.append((
                                serial,
                                s_key,
                                t_clean,
                                t_clean.lower(),
                                part,
                                p_key,
                                is_susp
                            ))
                            if len(batch) >= BATCH_SIZE:
                                flush_batch()
                                
        flush_batch()
        
        # Materialize Serial Summary (aggregated unique tickets per machine serial)
        self.con.execute("""
            CREATE TABLE serial_summary AS
            SELECT 
                serial_key,
                FIRST(serial) as original_serial,
                ARRAY_AGG(DISTINCT ticket) FILTER (WHERE ticket != '') as unique_tickets,
                COUNT(DISTINCT ticket) FILTER (WHERE ticket != '') as ticket_count,
                BOOL_OR(is_suspension) as has_suspension
            FROM ref_tokens
            WHERE serial_key != ''
            GROUP BY serial_key;

            CREATE INDEX idx_serial_summary ON serial_summary(serial_key);
        """)

        # Materialize Part-Specific Serial Summary (tickets per serial + part)
        self.con.execute("""
            CREATE TABLE serial_part_summary AS
            SELECT 
                serial_key,
                part_key,
                FIRST(part) as original_part,
                ARRAY_AGG(DISTINCT ticket) FILTER (WHERE ticket != '') as unique_tickets,
                COUNT(DISTINCT ticket) FILTER (WHERE ticket != '') as ticket_count,
                BOOL_OR(is_suspension) as has_suspension
            FROM ref_tokens
            WHERE serial_key != ''
            GROUP BY serial_key, part_key;

            CREATE INDEX idx_serial_part_summary ON serial_part_summary(serial_key, part_key);
        """)

        # Materialize Ticket Summary (reverse lookup: ticket -> associated serials)
        self.con.execute("""
            CREATE TABLE ticket_summary AS
            SELECT 
                ticket_key,
                FIRST(ticket) as original_ticket,
                ARRAY_AGG(DISTINCT serial) FILTER (WHERE serial != '') as unique_serials,
                COUNT(DISTINCT serial) FILTER (WHERE serial != '') as serial_count,
                BOOL_OR(is_suspension) as has_suspension
            FROM ref_tokens
            WHERE ticket_key != ''
            GROUP BY ticket_key;

            CREATE INDEX idx_ticket_summary ON ticket_summary(ticket_key);
        """)

        # Cross-reference for reverse lookups: ticket -> all associated tickets for those serials
        self.con.execute("""
            CREATE TABLE ticket_lookup AS
            SELECT 
                t.ticket_key,
                t.original_ticket,
                t.unique_serials,
                ARRAY_AGG(DISTINCT all_t.ticket) FILTER (WHERE all_t.ticket != '') as all_associated_tickets,
                BOOL_OR(t.has_suspension) as has_suspension
            FROM ticket_summary t
            LEFT JOIN ref_tokens all_t 
                ON (all_t.serial != '' AND list_contains(t.unique_serials, all_t.serial)) 
                OR (t.ticket_key = all_t.ticket_key)
            WHERE t.ticket_key != ''
            GROUP BY t.ticket_key, t.original_ticket, t.unique_serials;

            CREATE INDEX idx_ticket_lookup ON ticket_lookup(ticket_key);
        """)

    def lookup(self, serial: str, ticket: str, part_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Unified lookup using DuckDB indexed SQL queries.
        Returns unique_tickets (machine-level), part_tickets (specific part), part_breakdown, serial, has_suspension, and matched_by.
        """
        s_key = normalize_serial(serial).lower() if serial else ""
        t_key = normalize_ticket(ticket).lower() if ticket else ""
        p_key = normalize_part_key(part_name) if part_name else ""
        
        # 1. Primary Lookup by Serial Number
        if s_key:
            res = self.con.execute(
                "SELECT original_serial, unique_tickets, has_suspension FROM serial_summary WHERE serial_key = ?",
                [s_key]
            ).fetchone()
            if res and res[0] is not None:
                orig_serial, all_tickets_raw, has_susp = res
                all_tickets = set([t for t in (all_tickets_raw or []) if t])
                
                # Fetch part-level breakdown for this serial
                part_rows = self.con.execute(
                    "SELECT part_key, original_part, unique_tickets, has_suspension FROM serial_part_summary WHERE serial_key = ?",
                    [s_key]
                ).fetchall()
                
                part_breakdown = {}
                part_tickets = set()
                for pk, orig_p, tkts, susp in part_rows:
                    t_list = [t for t in (tkts or []) if t]
                    part_breakdown[pk] = {
                        "part": orig_p or pk,
                        "tickets": t_list,
                        "is_suspension": bool(susp)
                    }
                    if p_key and (pk == p_key or (p_key == "__suspension_rod__" and bool(susp))):
                        part_tickets.update(t_list)
                        
                return {
                    "matched_by": "serial",
                    "serial": orig_serial or serial,
                    "unique_tickets": all_tickets,
                    "part_tickets": part_tickets,
                    "part_breakdown": part_breakdown,
                    "has_suspension": bool(has_susp),
                    "requested_part_key": p_key
                }
                    
        # 2. Secondary Lookup by Ticket Number (Reverse Lookup)
        if t_key:
            res = self.con.execute(
                "SELECT original_ticket, unique_serials, all_associated_tickets, has_suspension FROM ticket_lookup WHERE ticket_key = ?",
                [t_key]
            ).fetchone()
            if res and res[0] is not None:
                orig_ticket, unique_serials, all_tickets_raw, has_susp = res
                resolved_serial = unique_serials[0] if (unique_serials and len(unique_serials) > 0) else (serial or "")
                all_tickets = set([t for t in (all_tickets_raw or [orig_ticket]) if t])
                if not all_tickets and orig_ticket:
                    all_tickets = {orig_ticket}
                    
                part_breakdown = {}
                part_tickets = set()
                
                if resolved_serial:
                    part_rows = self.con.execute(
                        "SELECT part_key, original_part, unique_tickets, has_suspension FROM serial_part_summary WHERE serial_key = ?",
                        [resolved_serial.lower()]
                    ).fetchall()
                    for pk, orig_p, tkts, susp in part_rows:
                        t_list = [t for t in (tkts or []) if t]
                        part_breakdown[pk] = {
                            "part": orig_p or pk,
                            "tickets": t_list,
                            "is_suspension": bool(susp)
                        }
                        if p_key and (pk == p_key or (p_key == "__suspension_rod__" and bool(susp))):
                            part_tickets.update(t_list)
                else:
                    if orig_ticket:
                        part_tickets.add(orig_ticket)
                        
                return {
                    "matched_by": "ticket",
                    "serial": resolved_serial,
                    "unique_tickets": all_tickets,
                    "part_tickets": part_tickets,
                    "part_breakdown": part_breakdown,
                    "has_suspension": bool(has_susp),
                    "requested_part_key": p_key
                }
                
        return None

    def close(self):
        """Releases the DuckDB connection and triggers garbage collection."""
        try:
            self.con.close()
        except Exception:
            pass
        gc.collect()


def get_db_metadata(db_path: str) -> Dict[str, Any]:
    """Retrieve metadata about the pre-indexed DuckDB Reference Database."""
    if not os.path.exists(db_path):
        return {
            "is_indexed": False,
            "total_records": 0,
            "unique_serials": 0,
            "unique_tickets": 0,
            "indexed_at": None,
            "source_filename": None,
            "file_size_mb": 0,
            "db_path": db_path
        }
    try:
        con = duckdb.connect(database=db_path, read_only=True)
        meta = con.execute("SELECT indexed_at, source_filename, total_records, unique_serials, unique_tickets FROM db_metadata LIMIT 1").fetchone()
        con.close()
        
        file_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        if meta:
            indexed_at, source_filename, total_records, unique_serials, unique_tickets = meta
            return {
                "is_indexed": True,
                "total_records": int(total_records or 0),
                "unique_serials": int(unique_serials or 0),
                "unique_tickets": int(unique_tickets or 0),
                "indexed_at": indexed_at,
                "source_filename": source_filename,
                "file_size_mb": file_size_mb,
                "db_path": db_path
            }
        else:
            return {
                "is_indexed": True,
                "total_records": 0,
                "unique_serials": 0,
                "unique_tickets": 0,
                "indexed_at": None,
                "source_filename": None,
                "file_size_mb": file_size_mb,
                "db_path": db_path
            }
    except Exception as e:
        return {
            "is_indexed": False,
            "error": str(e),
            "db_path": db_path,
            "total_records": 0,
            "unique_serials": 0,
            "unique_tickets": 0,
            "file_size_mb": 0
        }


def build_persistent_reference_db(
    source_input: Any,
    db_path: str,
    source_filename: str = "",
    serial_col: Optional[str] = None,
    ticket_col: Optional[str] = None,
    part_col: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds a persistent DuckDB reference database file from .xlsx, .csv, .parquet, or DataFrame.
    Atomically writes to temp file before replacing the target db_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    temp_db_path = db_path + f".tmp_{int(datetime.datetime.now().timestamp())}"
    
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

    con = duckdb.connect(database=temp_db_path)
    con.execute("PRAGMA threads=8;")
    con.execute("PRAGMA max_memory='4GB';")

    con.execute("""
        CREATE TABLE ref_tokens (
            serial VARCHAR,
            serial_key VARCHAR,
            ticket VARCHAR,
            ticket_key VARCHAR,
            part VARCHAR,
            part_key VARCHAR,
            is_suspension BOOLEAN
        );
    """)

    # 1. Determine Input Type and Extract DataFrame / Records
    if isinstance(source_input, pd.DataFrame):
        ref_df = source_input
        s_col = serial_col or find_column(list(ref_df.columns), SERIAL_ALIASES)
        t_col = ticket_col or find_column(list(ref_df.columns), TICKET_ALIASES)
        p_col = part_col or find_column(list(ref_df.columns), PART_ALIASES)
    elif isinstance(source_input, bytes):
        # Determine format
        if source_filename.lower().endswith((".csv", ".tsv", ".txt")):
            text_io = io.BytesIO(source_input)
            sep = "\t" if source_filename.lower().endswith(".tsv") else ","
            ref_df = pd.read_csv(text_io, sep=sep, low_memory=False)
            s_col = serial_col or find_column(list(ref_df.columns), SERIAL_ALIASES)
            t_col = ticket_col or find_column(list(ref_df.columns), TICKET_ALIASES)
            p_col = part_col or find_column(list(ref_df.columns), PART_ALIASES)
        elif source_filename.lower().endswith(".parquet"):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
                tf.write(source_input)
                tf_path = tf.name
            try:
                ref_df = duckdb.connect().execute(f"SELECT * FROM read_parquet('{tf_path.replace(chr(92), '/')}')").df()
            finally:
                if os.path.exists(tf_path):
                    os.remove(tf_path)
            s_col = serial_col or find_column(list(ref_df.columns), SERIAL_ALIASES)
            t_col = ticket_col or find_column(list(ref_df.columns), TICKET_ALIASES)
            p_col = part_col or find_column(list(ref_df.columns), PART_ALIASES)
        else: # Excel default
            ref_df, s_col, t_col, p_col = load_reference_df(source_input)
    elif isinstance(source_input, str) and os.path.exists(source_input):
        # File on disk
        fn = source_input.lower()
        if fn.endswith((".csv", ".tsv")):
            sep = "\t" if fn.endswith(".tsv") else ","
            ref_df = pd.read_csv(source_input, sep=sep, low_memory=False)
            s_col = serial_col or find_column(list(ref_df.columns), SERIAL_ALIASES)
            t_col = ticket_col or find_column(list(ref_df.columns), TICKET_ALIASES)
            p_col = part_col or find_column(list(ref_df.columns), PART_ALIASES)
        elif fn.endswith(".parquet"):
            ref_df = duckdb.connect().execute(f"SELECT * FROM read_parquet('{source_input.replace(chr(92), '/')}')").df()
            s_col = serial_col or find_column(list(ref_df.columns), SERIAL_ALIASES)
            t_col = ticket_col or find_column(list(ref_df.columns), TICKET_ALIASES)
            p_col = part_col or find_column(list(ref_df.columns), PART_ALIASES)
        else:
            with open(source_input, "rb") as f:
                ref_df, s_col, t_col, p_col = load_reference_df(f.read())
    else:
        con.close()
        raise ValidationError("Unsupported source input format for persistent database indexing.")

    if not s_col and not t_col:
        con.close()
        raise ValidationError(f"Could not find Machine Serial Number or Ticket Number column in '{source_filename}'. Available columns: {list(ref_df.columns)}")

    # 2. Batch Insert into ref_tokens
    batch = []
    BATCH_SIZE = 25000
    
    serial_series = ref_df[s_col] if (s_col and s_col in ref_df.columns) else [None] * len(ref_df)
    ticket_series = ref_df[t_col] if (t_col and t_col in ref_df.columns) else [None] * len(ref_df)
    part_series = ref_df[p_col] if (p_col and p_col in ref_df.columns) else [None] * len(ref_df)
    
    for raw_serial, raw_ticket, raw_part in zip(serial_series, ticket_series, part_series):
        serial = normalize_serial(raw_serial)
        part = normalize_str(raw_part)
        is_susp = is_suspension_rod(part)
        p_key = normalize_part_key(part)
        tickets = extract_tickets(raw_ticket)
        
        if not serial and not tickets:
            continue
            
        s_key = serial.lower() if serial else ""
        
        if not tickets:
            batch.append((serial, s_key, "", "", part, p_key, is_susp))
            if len(batch) >= BATCH_SIZE:
                con.executemany("INSERT INTO ref_tokens VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                batch = []
        else:
            for t in tickets:
                t_clean = t.strip()
                if serial or t_clean:
                    batch.append((
                        serial,
                        s_key,
                        t_clean,
                        t_clean.lower(),
                        part,
                        p_key,
                        is_susp
                    ))
                    if len(batch) >= BATCH_SIZE:
                        con.executemany("INSERT INTO ref_tokens VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                        batch = []

    if batch:
        con.executemany("INSERT INTO ref_tokens VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        batch = []

    # 3. Materialize Summary Tables and Indexes
    con.execute("""
        CREATE TABLE serial_summary AS
        SELECT 
            serial_key,
            FIRST(serial) as original_serial,
            ARRAY_AGG(DISTINCT ticket) FILTER (WHERE ticket != '') as unique_tickets,
            COUNT(DISTINCT ticket) FILTER (WHERE ticket != '') as ticket_count,
            BOOL_OR(is_suspension) as has_suspension
        FROM ref_tokens
        WHERE serial_key != ''
        GROUP BY serial_key;

        CREATE INDEX idx_serial_summary ON serial_summary(serial_key);
    """)

    con.execute("""
        CREATE TABLE serial_part_summary AS
        SELECT 
            serial_key,
            part_key,
            FIRST(part) as original_part,
            ARRAY_AGG(DISTINCT ticket) FILTER (WHERE ticket != '') as unique_tickets,
            COUNT(DISTINCT ticket) FILTER (WHERE ticket != '') as ticket_count,
            BOOL_OR(is_suspension) as has_suspension
        FROM ref_tokens
        WHERE serial_key != ''
        GROUP BY serial_key, part_key;

        CREATE INDEX idx_serial_part_summary ON serial_part_summary(serial_key, part_key);
    """)

    con.execute("""
        CREATE TABLE ticket_summary AS
        SELECT 
            ticket_key,
            FIRST(ticket) as original_ticket,
            ARRAY_AGG(DISTINCT serial) FILTER (WHERE serial != '') as unique_serials,
            COUNT(DISTINCT serial) FILTER (WHERE serial != '') as serial_count,
            BOOL_OR(is_suspension) as has_suspension
        FROM ref_tokens
        WHERE ticket_key != ''
        GROUP BY ticket_key;

        CREATE INDEX idx_ticket_summary ON ticket_summary(ticket_key);
    """)

    con.execute("""
        CREATE TABLE ticket_lookup AS
        SELECT 
            t.ticket_key,
            t.original_ticket,
            t.unique_serials,
            ARRAY_AGG(DISTINCT all_t.ticket) FILTER (WHERE all_t.ticket != '') as all_associated_tickets,
            BOOL_OR(t.has_suspension) as has_suspension
        FROM ticket_summary t
        LEFT JOIN ref_tokens all_t 
            ON (all_t.serial != '' AND list_contains(t.unique_serials, all_t.serial)) 
            OR (t.ticket_key = all_t.ticket_key)
        WHERE t.ticket_key != ''
        GROUP BY t.ticket_key, t.original_ticket, t.unique_serials;

        CREATE INDEX idx_ticket_lookup ON ticket_lookup(ticket_key);
    """)

    # 4. Compute Counts and Write Metadata
    total_records = con.execute("SELECT COUNT(*) FROM ref_tokens").fetchone()[0]
    unique_serials = con.execute("SELECT COUNT(*) FROM serial_summary").fetchone()[0]
    unique_tickets = con.execute("SELECT COUNT(*) FROM ticket_summary").fetchone()[0]
    indexed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    con.execute("""
        CREATE TABLE db_metadata (
            indexed_at VARCHAR,
            source_filename VARCHAR,
            total_records BIGINT,
            unique_serials BIGINT,
            unique_tickets BIGINT,
            file_size_bytes BIGINT
        );
    """)
    con.execute(
        "INSERT INTO db_metadata VALUES (?, ?, ?, ?, ?, ?)",
        [indexed_at, source_filename or "Reference Dataset", total_records, unique_serials, unique_tickets, 0]
    )

    con.close()

    # 5. Atomic File Replacement
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            # Fallback backup rename
            backup_path = db_path + f".old_{int(datetime.datetime.now().timestamp())}"
            shutil.move(db_path, backup_path)
            
    shutil.move(temp_db_path, db_path)

    return get_db_metadata(db_path)



# ---------------------------------------------------------------------------
# Core Rule Evaluation
# ---------------------------------------------------------------------------

def evaluate_record(
    row_idx: int,
    serial: str,
    ticket: str,
    part_name: str,
    original_fqc: str,
    ref_index: ReferenceIndex,
    is_suspension: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Evaluate a single record where original_fqc is 'NG to Verify'.
    Evaluates against Reference Data using Serial and/or Ticket Number,
    enforcing that multi-ticket approvals must be for the same part/category.
    """
    clean_serial = normalize_serial(serial)
    clean_ticket = normalize_ticket(ticket)
    clean_part = normalize_str(part_name)
    
    if is_suspension is not None:
        is_susp = is_suspension
    else:
        is_susp = is_suspension_rod(clean_part)
    
    # 1. Check if both Serial and Ticket are completely missing in Mahavir
    if not clean_serial and not clean_ticket:
        return {
            "row_idx": row_idx,
            "serial": clean_serial,
            "ticket": clean_ticket,
            "part": clean_part,
            "original_fqc": original_fqc,
            "new_fqc": original_fqc,
            "classification": "Manual Review",
            "is_suspension": is_susp,
            "status": "FLAGGED",
            "reason": "Both Machine Serial Number and Ticket Number are missing in Mahavir file.",
            "ref_tickets": []
        }
        
    # 2. Lookup in Reference Data (by Serial Number or Ticket Number and Part Name)
    ref_info = ref_index.lookup(clean_serial, clean_ticket, clean_part)
    
    if not ref_info:
        # Neither Serial nor Ticket was found in Reference Database
        identifier = f"Serial '{clean_serial}'" if clean_serial else f"Ticket '{clean_ticket}'"
        if clean_serial and clean_ticket:
            identifier = f"Serial '{clean_serial}' / Ticket '{clean_ticket}'"
        return {
            "row_idx": row_idx,
            "serial": clean_serial,
            "ticket": clean_ticket,
            "part": clean_part,
            "original_fqc": original_fqc,
            "new_fqc": original_fqc,
            "classification": "Manual Review",
            "is_suspension": is_susp,
            "status": "NOT_FOUND_IN_REF",
            "reason": f"{identifier} not found in Reference File.",
            "ref_tickets": []
        }

    # Check if Reference data indicates this ticket/serial is a suspension rod replacement
    if is_suspension is None and not is_susp:
        if ref_info.get("has_suspension") and (is_rod_or_suspension_like(clean_part) or not clean_part):
            is_susp = True
        
    resolved_serial = ref_info.get("serial") or clean_serial
    matched_by = ref_info.get("matched_by", "serial")
    part_breakdown = ref_info.get("part_breakdown", {})
    all_ref_tickets = set(ref_info.get("unique_tickets", set()))
    part_ref_tickets = set(ref_info.get("part_tickets", set()))
    
    # 3. Special Rule: Suspension Rod
    if is_susp:
        susp_tickets_set = set(part_ref_tickets) if ref_info.get("requested_part_key") == "__suspension_rod__" else set()
        if not susp_tickets_set:
            for pk, p_info in part_breakdown.items():
                if pk == "__suspension_rod__" or p_info.get("is_suspension"):
                    susp_tickets_set.update(p_info.get("tickets", []))
        if not susp_tickets_set and not part_breakdown:
            susp_tickets_set = set(all_ref_tickets)
            
        if clean_ticket:
            susp_tickets_set.add(clean_ticket)
            
        all_distinct_tickets = sorted(list(susp_tickets_set))
        eval_ticket = clean_ticket or (all_distinct_tickets[0] if all_distinct_tickets else "")
        additional_tickets = [t for t in all_distinct_tickets if t != eval_ticket]
        additional_count = len(additional_tickets)
        
        if additional_count >= 2:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Approved",
                "classification": "Approved",
                "is_suspension": True,
                "status": "SUCCESS",
                "reason": (
                    f"Suspension Rod (Pair) Approved ({'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Found {additional_count} additional distinct suspension ticket(s) "
                    f"({', '.join(additional_tickets)}) besides evaluating ticket '{eval_ticket}'."
                ),
                "ref_tickets": all_distinct_tickets,
                "additional_tickets": additional_tickets
            }
        else:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Non-Genuine",
                "classification": "Non-Genuine",
                "is_suspension": True,
                "status": "SUCCESS",
                "reason": (
                    f"Suspension Rod (Pair) Non-Genuine ({'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Only {additional_count} additional distinct suspension ticket(s) found "
                    f"({', '.join(additional_tickets) if additional_tickets else 'none'}) besides evaluating ticket '{eval_ticket}'. "
                    f"Requires >= 2 additional tickets."
                ),
                "ref_tickets": all_distinct_tickets,
                "additional_tickets": additional_tickets
            }
            
    # 4. Standard Part Rules (Rule 1 & Rule 2 with Same-Part Matching)
    if clean_part:
        part_tickets_set = set(part_ref_tickets)
        if clean_ticket:
            part_tickets_set.add(clean_ticket)
            
        all_part_tickets = sorted(list(part_tickets_set))
        distinct_part_count = len(all_part_tickets)
        
        if distinct_part_count >= 2:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Approved",
                "classification": "Approved",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": (
                    f"Rule 1 Approved ({'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Found {distinct_part_count} distinct ticket(s) for part '{clean_part}' on this machine ({', '.join(all_part_tickets)})."
                ),
                "ref_tickets": all_part_tickets
            }
        elif distinct_part_count == 1:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Non-Genuine",
                "classification": "Non-Genuine",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": (
                    f"Rule 2 Non-Genuine ({'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Only 1 unique ticket found for part '{clean_part}' on this machine ({all_part_tickets[0]}). Requires >= 2 distinct tickets for the same part."
                ),
                "ref_tickets": all_part_tickets
            }
        else:
            # 0 tickets for clean_part on this serial in Reference
            other_parts_summary = [f"{p_data.get('part', k)} ({len(p_data.get('tickets', []))} tkt)" for k, p_data in part_breakdown.items() if p_data.get("tickets")]
            other_parts_text = f"Found tickets for other parts: {', '.join(other_parts_summary)}" if other_parts_summary else "No tickets recorded for this part in Reference."
            all_machine_tickets = sorted(list(all_ref_tickets))
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Non-Genuine",
                "classification": "Non-Genuine",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": (
                    f"Rule 2 Non-Genuine ({'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Serial '{resolved_serial or clean_serial}' has tickets in Reference, but 0 tickets for part '{clean_part}'. {other_parts_text}"
                ),
                "ref_tickets": all_machine_tickets
            }
    else:
        # Fallback when Part Name is missing in Mahavir row
        all_distinct_tickets_set = set(all_ref_tickets)
        if clean_ticket:
            all_distinct_tickets_set.add(clean_ticket)
        all_distinct_tickets = sorted(list(all_distinct_tickets_set))
        total_distinct_count = len(all_distinct_tickets)
        
        if total_distinct_count >= 2:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Approved",
                "classification": "Approved",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": (
                    f"Rule 1 Approved (Notice: Part Name missing in Mahavir - matched at Machine level; {'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Found {total_distinct_count} distinct ticket(s) for this machine ({', '.join(all_distinct_tickets)})."
                ),
                "ref_tickets": all_distinct_tickets
            }
        elif total_distinct_count == 1:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Non-Genuine",
                "classification": "Non-Genuine",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": (
                    f"Rule 2 Non-Genuine (Notice: Part Name missing in Mahavir - matched at Machine level; {'matched via Ticket' if matched_by == 'ticket' else 'matched via Serial'}): "
                    f"Only 1 unique ticket found for this machine ({all_distinct_tickets[0]}). Requires >= 2 distinct tickets."
                ),
                "ref_tickets": all_distinct_tickets
            }
        else:
            return {
                "row_idx": row_idx,
                "serial": resolved_serial or clean_serial,
                "ticket": clean_ticket,
                "part": clean_part,
                "original_fqc": original_fqc,
                "new_fqc": "Non-Genuine",
                "classification": "Non-Genuine",
                "is_suspension": False,
                "status": "SUCCESS",
                "reason": f"No valid reference tickets found for Serial '{resolved_serial or clean_serial}'.",
                "ref_tickets": []
            }


# ---------------------------------------------------------------------------
# Reference File Fast Loader & Indexer (Multi-Sheet Safe Loader)
# ---------------------------------------------------------------------------

def load_reference_df(ref_bytes: bytes) -> Tuple[pd.DataFrame, Optional[str], Optional[str], Optional[str]]:
    """
    Rapidly loads ALL data from ALL sheets in the Reference file.
    Uses openpyxl read_only streaming for maximum speed and zero memory bloat.
    """
    ref_io = io.BytesIO(ref_bytes)
    try:
        wb = openpyxl.load_workbook(ref_io, read_only=True, data_only=True)
    except Exception as e:
        raise ValidationError(f"Cannot open Reference File: {str(e)}")

    all_rows = []
    global_ref_serial_col = None
    global_ref_ticket_col = None
    global_ref_part_col = None

    # Iterate through ALL sheets in the workbook
    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        rows_iter = ws.iter_rows(values_only=True)
        sheet_headers = None
        s_col = None
        t_col = None
        p_col = None
        
        # Scan first 15 rows for header
        s_idx = None
        t_idx = None
        p_idx = None
        for r_idx, row in enumerate(rows_iter):
            if r_idx > 15:
                break
            if not row:
                continue
            cand_headers = [str(c).strip() if c is not None else "" for c in row]
            cand_serial = find_column(cand_headers, SERIAL_ALIASES)
            cand_ticket = find_column(cand_headers, TICKET_ALIASES)
            if cand_serial or cand_ticket:
                s_col = cand_serial
                t_col = cand_ticket
                p_col = find_column(cand_headers, PART_ALIASES)
                s_idx = cand_headers.index(s_col) if s_col else None
                t_idx = cand_headers.index(t_col) if t_col else None
                p_idx = cand_headers.index(p_col) if p_col else None
                break

        if s_idx is not None or t_idx is not None:
            consecutive_empty = 0
            for row in rows_iter:
                s_val = row[s_idx] if (s_idx is not None and len(row) > s_idx) else None
                t_val = row[t_idx] if (t_idx is not None and len(row) > t_idx) else None
                p_val = row[p_idx] if (p_idx is not None and len(row) > p_idx) else None
                
                if s_val is None and t_val is None and p_val is None:
                    consecutive_empty += 1
                    if consecutive_empty > 100:
                        break
                    continue
                consecutive_empty = 0
                
                if s_val is not None or t_val is not None:
                    all_rows.append({
                        "Machine Serial Number": s_val,
                        "Ticket Number": t_val,
                        "Part Name": p_val
                    })

    wb.close()

    # Fallback to pandas if openpyxl read_only did not find rows
    if not all_rows:
        try:
            ref_io.seek(0)
            ref_sheets = pd.read_excel(ref_io, sheet_name=None, engine="openpyxl")
            frames = [df for df in ref_sheets.values() if not df.empty]
            if frames:
                ref_df = pd.concat(frames, ignore_index=True)
                ref_df.columns = [str(c).strip() for c in ref_df.columns]
                s_col = find_column(list(ref_df.columns), SERIAL_ALIASES)
                t_col = find_column(list(ref_df.columns), TICKET_ALIASES)
                p_col = find_column(list(ref_df.columns), PART_ALIASES)
                return ref_df, s_col, t_col, p_col
        except Exception as e:
            raise ValidationError(f"Error reading Reference File: {str(e)}")

    ref_df = pd.DataFrame(all_rows)
    return ref_df, "Machine Serial Number", "Ticket Number", "Part Name"


# ---------------------------------------------------------------------------
# Main Engine: Process Files
# ---------------------------------------------------------------------------

def process_validation(
    mahavir_bytes: bytes,
    reference_bytes: Optional[bytes] = None,
    ref_db_path: Optional[str] = None,
    custom_mahavir_cols: Optional[Dict[str, str]] = None,
    custom_ref_cols: Optional[Dict[str, str]] = None
) -> Tuple[io.BytesIO, io.BytesIO, Dict[str, Any]]:
    """
    Processes Mahavir file against Reference data with high-speed DuckDB lookups and 100% data preservation.
    Accepts either an ad-hoc reference_bytes file OR a pre-indexed persistent DuckDB reference database path.
    Returns:
      (processed_mahavir_io, qc_summary_io, qc_stats_dict)
    """
    # 1. Initialize Reference Index (Ad-hoc uploaded file OR Pre-Indexed Master Database)
    if reference_bytes:
        ref_df, auto_ref_serial, auto_ref_ticket, auto_ref_part = load_reference_df(reference_bytes)
        ref_serial_col = (custom_ref_cols or {}).get("serial") or auto_ref_serial or find_column(list(ref_df.columns), SERIAL_ALIASES)
        ref_ticket_col = (custom_ref_cols or {}).get("ticket") or auto_ref_ticket or find_column(list(ref_df.columns), TICKET_ALIASES)
        ref_part_col = (custom_ref_cols or {}).get("part") or auto_ref_part or find_column(list(ref_df.columns), PART_ALIASES)
        
        if not ref_serial_col:
            raise ValidationError(f"Reference File missing Machine Serial Number column. Available columns: {list(ref_df.columns)}")
        if not ref_ticket_col:
            raise ValidationError(f"Reference File missing Ticket Number column. Available columns: {list(ref_df.columns)}")
            
        ref_index = ReferenceIndex(source=ref_df, serial_col=ref_serial_col, ticket_col=ref_ticket_col, part_col=ref_part_col)
    elif ref_db_path and os.path.exists(ref_db_path):
        meta = get_db_metadata(ref_db_path)
        if not meta.get("is_indexed") or meta.get("total_records", 0) == 0:
            raise ValidationError(f"Persistent Master Reference Database at '{ref_db_path}' contains no records. Please re-index reference data.")
        ref_index = ReferenceIndex(db_path=ref_db_path)
        ref_serial_col = f"Master DB ({meta.get('source_filename', 'Indexed')})"
        ref_ticket_col = f"Master DB ({meta.get('source_filename', 'Indexed')})"
        ref_part_col = f"Master DB ({meta.get('source_filename', 'Indexed')})"
    else:
        raise ValidationError("No Reference File uploaded and Master Reference Database is not yet initialized. Please upload a Reference File or index a Master Database.")
    
    # 2. Load Mahavir Workbook for 100% preservation across ALL sheets (TL, FL/UF, MW/MV, DW/DV, etc.)
    mah_io = io.BytesIO(mahavir_bytes)
    try:
        wb = openpyxl.load_workbook(mah_io, data_only=False)
    except Exception as e:
        raise ValidationError(f"Cannot open Mahavir File as Excel workbook: {str(e)}")
        
    evaluated_records: List[Dict[str, Any]] = []
    
    approved_count = 0
    non_genuine_count = 0
    not_found_count = 0
    suspension_count = 0
    manual_review_count = 0
    total_ng_found = 0
    total_rows = 0
    processed_sheets: List[str] = []
    detected_cols: Dict[str, Any] = {}
    missing_reasons: List[str] = []

    # Iterate through ALL sheets in the Mahavir workbook
    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        if ws is None:
            continue
            
        # Find Header Row & Columns in first 15 rows of this sheet
        header_row_idx = None
        header_col_map: Dict[str, int] = {}
        
        for r in range(1, min(15, (ws.max_row or 15) + 1)):
            row_vals = [ws.cell(row=r, column=c).value for c in range(1, min(100, (ws.max_column or 100) + 1))]
            cand_headers = [str(val).strip() for val in row_vals if val is not None]
            cand_fqc = find_column(cand_headers, FQC_ALIASES)
            cand_serial = find_column(cand_headers, SERIAL_ALIASES)
            if cand_fqc and cand_serial:
                header_row_idx = r
                header_col_map = {
                    str(ws.cell(row=r, column=c).value).strip(): c
                    for c in range(1, len(row_vals) + 1)
                    if ws.cell(row=r, column=c).value is not None
                }
                break
                
        # If this sheet doesn't contain FQC and Serial columns, record details
        if not header_col_map or header_row_idx is None:
            # Check what's in first row
            r1_vals = [str(ws.cell(row=1, column=c).value).strip() for c in range(1, min(50, (ws.max_column or 50) + 1)) if ws.cell(row=1, column=c).value is not None]
            c_fqc = find_column(r1_vals, FQC_ALIASES)
            c_serial = find_column(r1_vals, SERIAL_ALIASES)
            if not c_fqc and not c_serial:
                missing_reasons.append(f"Sheet '{sheetname}': missing both 'FQC Analysis' and 'Machine Serial Number'")
            elif not c_fqc:
                missing_reasons.append(f"Sheet '{sheetname}': missing 'FQC Analysis' column. Found columns: {r1_vals}")
            elif not c_serial:
                missing_reasons.append(f"Sheet '{sheetname}': missing 'Machine Serial Number' column. Found columns: {r1_vals}")
            continue
            
        col_names = list(header_col_map.keys())
        mah_fqc_col = (custom_mahavir_cols or {}).get("fqc") or find_column(col_names, FQC_ALIASES)
        mah_serial_col = (custom_mahavir_cols or {}).get("serial") or find_column(col_names, SERIAL_ALIASES)
        mah_ticket_col = (custom_mahavir_cols or {}).get("ticket") or find_column(col_names, TICKET_ALIASES)
        mah_part_col = (custom_mahavir_cols or {}).get("part") or find_column(col_names, PART_ALIASES)
        
        if not mah_fqc_col and not mah_serial_col:
            missing_reasons.append(f"Sheet '{sheetname}': missing both 'FQC Analysis' and 'Machine Serial Number' columns")
            continue
        if not mah_fqc_col:
            missing_reasons.append(f"Sheet '{sheetname}': missing 'FQC Analysis' column (Found columns: {col_names})")
            continue
        if not mah_serial_col:
            missing_reasons.append(f"Sheet '{sheetname}': missing 'Machine Serial Number' column (Found columns: {col_names})")
            continue
            
        fqc_col_idx = header_col_map[mah_fqc_col]
        serial_col_idx = header_col_map[mah_serial_col]
        ticket_col_idx = header_col_map.get(mah_ticket_col) if mah_ticket_col else None
        part_col_idx = header_col_map.get(mah_part_col) if mah_part_col else None
        
        processed_sheets.append(sheetname)
        if not detected_cols:
            detected_cols = {
                "fqc": mah_fqc_col,
                "serial": mah_serial_col,
                "ticket": mah_ticket_col,
                "part": mah_part_col
            }
            
        # Pass 1 (Sheet-Level): Identify Ticket-Level Suspension Rod replacements
        collected_rows = []
        ticket_has_suspension = {} # ticket_key -> bool
        serial_has_suspension = {} # serial_key -> bool
        
        consecutive_empty = 0
        for row_num, row_cells in enumerate(ws.iter_rows(min_row=header_row_idx + 1), start=header_row_idx + 1):
            num_cells = len(row_cells)
            fqc_cell = row_cells[fqc_col_idx - 1] if num_cells >= fqc_col_idx else None
            if fqc_cell is None:
                continue
            raw_fqc_val = fqc_cell.value
            
            serial_val = row_cells[serial_col_idx - 1].value if num_cells >= serial_col_idx else None
            ticket_val = row_cells[ticket_col_idx - 1].value if (ticket_col_idx and num_cells >= ticket_col_idx) else None
            part_val = row_cells[part_col_idx - 1].value if (part_col_idx and num_cells >= part_col_idx) else None
            
            # Check if row is completely empty
            if raw_fqc_val is None and serial_val is None and ticket_val is None and part_val is None:
                consecutive_empty += 1
                if consecutive_empty >= 100:
                    break
                continue
                
            consecutive_empty = 0
            total_rows += 1
            
            s_norm = normalize_str(serial_val)
            t_norm = normalize_str(ticket_val)
            p_norm = normalize_str(part_val)
            
            is_susp_direct = is_suspension_rod(p_norm)
            if is_susp_direct:
                if t_norm:
                    ticket_has_suspension[t_norm.lower()] = True
                    for extracted_t in extract_tickets(t_norm):
                        ticket_has_suspension[extracted_t.lower()] = True
                if s_norm:
                    serial_has_suspension[s_norm.lower()] = True
                    
            collected_rows.append({
                "row_num": row_num,
                "fqc_cell": fqc_cell,
                "raw_fqc_val": raw_fqc_val,
                "serial_norm": s_norm,
                "ticket_norm": t_norm,
                "part_norm": p_norm,
                "is_susp_direct": is_susp_direct
            })
            
        # Pass 2 (Sheet-Level): Evaluate 'NG to Verify' rows and update cell values
        for item in collected_rows:
            row_num = item["row_num"]
            fqc_cell = item["fqc_cell"]
            raw_fqc_val = item["raw_fqc_val"]
            s_norm = item["serial_norm"]
            t_norm = item["ticket_norm"]
            p_norm = item["part_norm"]
            raw_fqc = normalize_str(raw_fqc_val)
            
            if is_ng_to_verify(raw_fqc_val):
                total_ng_found += 1
                
                is_susp = item["is_susp_direct"]
                if not is_susp and t_norm:
                    t_key = t_norm.lower()
                    if ticket_has_suspension.get(t_key):
                        if is_rod_or_suspension_like(p_norm) or not p_norm:
                            is_susp = True
                            
                rec = evaluate_record(
                    row_idx=row_num,
                    serial=s_norm,
                    ticket=t_norm,
                    part_name=p_norm,
                    original_fqc=raw_fqc,
                    ref_index=ref_index,
                    is_suspension=is_susp if is_susp else None
                )
                rec["sheet_name"] = sheetname
                
                # Update FQC Analysis cell in this sheet for conclusive classifications
                if rec["classification"] in ["Approved", "Non-Genuine"]:
                    fqc_cell.value = rec["classification"]
                    if rec["classification"] == "Approved":
                        approved_count += 1
                    else:
                        non_genuine_count += 1
                else:
                    if rec["status"] == "NOT_FOUND_IN_REF":
                        not_found_count += 1
                    manual_review_count += 1
                    
                if rec["is_suspension"]:
                    suspension_count += 1
                    
                evaluated_records.append(rec)

    if not processed_sheets:
        err_detail = "; ".join(missing_reasons) if missing_reasons else f"Checked sheets: {wb.sheetnames}"
        raise ValidationError(f"Could not process Mahavir File: {err_detail}")

    # Save Processed Mahavir Workbook (with all sheets preserved and updated)
    out_mah_io = io.BytesIO()
    wb.save(out_mah_io)
    out_mah_io.seek(0)
    
    # 3. Generate Dedicated QC Summary Excel
    qc_summary_io = generate_qc_workbook(
        evaluated_records=evaluated_records,
        stats={
            "total_rows": total_rows,
            "total_ng_found": total_ng_found,
            "approved_count": approved_count,
            "non_genuine_count": non_genuine_count,
            "not_found_count": not_found_count,
            "suspension_count": suspension_count,
            "manual_review_count": manual_review_count,
            "processed_sheets": processed_sheets,
        }
    )
    
    stats_dict = {
        "total_rows": total_rows,
        "total_ng_found": total_ng_found,
        "approved_count": approved_count,
        "non_genuine_count": non_genuine_count,
        "not_found_count": not_found_count,
        "suspension_count": suspension_count,
        "manual_review_count": manual_review_count,
        "processed_sheets": processed_sheets,
        "records": evaluated_records,
        "detected_columns": {
            "mahavir": detected_cols,
            "reference": {
                "serial": ref_serial_col,
                "ticket": ref_ticket_col,
                "part": ref_part_col
            }
        }
    }
    
    # Close DuckDB resources and reclaim RAM
    ref_index.close()
    gc.collect()
    
    return out_mah_io, qc_summary_io, stats_dict


# ---------------------------------------------------------------------------
# QC Excel Generator
# ---------------------------------------------------------------------------

def generate_qc_workbook(evaluated_records: List[Dict[str, Any]], stats: Dict[str, Any]) -> io.BytesIO:
    """Creates a beautifully formatted QC Validation Excel Report."""
    wb = openpyxl.Workbook()
    
    # Sheet 1: Executive Summary
    ws_sum = wb.active
    ws_sum.title = "Executive Summary"
    ws_sum.views.sheetView[0].showGridLines = True
    
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=14, bold=True, color="0F172A")
    regular_font = Font(name="Segoe UI", size=10)
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    ws_sum.merge_cells("A1:D1")
    ws_sum["A1"] = "FQC Analysis 'NG to Verify' Validation Summary"
    ws_sum["A1"].font = title_font
    
    summary_data = [
        ("Sheets Processed", ", ".join(stats.get("processed_sheets", [])) if stats.get("processed_sheets") else "All Active"),
        ("Total Rows Audited", stats["total_rows"]),
        ("Total 'NG to Verify' Records Identified", stats["total_ng_found"]),
        ("Classified as 'Approved'", stats["approved_count"]),
        ("Classified as 'Non-Genuine'", stats["non_genuine_count"]),
        ("Suspension Rod Records Evaluated", stats["suspension_count"]),
        ("Serial Numbers NOT Found in Reference", stats["not_found_count"]),
        ("Records Flagged for Manual Review", stats["manual_review_count"]),
    ]
    
    ws_sum.cell(row=3, column=1, value="Validation Metric").font = header_font
    ws_sum.cell(row=3, column=1).fill = header_fill
    ws_sum.cell(row=3, column=2, value="Count / Details").font = header_font
    ws_sum.cell(row=3, column=2).fill = header_fill
    
    for i, (label, val) in enumerate(summary_data, start=4):
        c1 = ws_sum.cell(row=i, column=1, value=label)
        c2 = ws_sum.cell(row=i, column=2, value=val)
        c1.font = regular_font
        c2.font = bold_font
        c1.border = border_thin
        c2.border = border_thin
        c2.alignment = Alignment(horizontal="center")
        
    ws_sum.column_dimensions["A"].width = 45
    ws_sum.column_dimensions["B"].width = 24
    
    # Sheet 2: All Evaluated Records Log
    ws_log = wb.create_sheet(title="FQC Validation Log")
    ws_log.views.sheetView[0].showGridLines = True
    
    log_headers = [
        "Sheet", "Excel Row #", "Machine Serial No.", "Ticket No.", "Part Name",
        "Original FQC", "Updated FQC", "Suspension Rod?", "Status", "Reference Tickets Found", "Audit Reason"
    ]
    
    ws_log.append(log_headers)
    for cell in ws_log[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    approved_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # light green
    nongen_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")   # light red
    flag_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")     # light yellow
    
    for rec in evaluated_records:
        row_vals = [
            rec.get("sheet_name", ""),
            rec["row_idx"],
            rec["serial"],
            rec["ticket"],
            rec["part"],
            rec["original_fqc"],
            rec["classification"],
            "Yes" if rec["is_suspension"] else "No",
            rec["status"],
            ", ".join(rec.get("ref_tickets", [])),
            rec["reason"]
        ]
        ws_log.append(row_vals)
        curr_row = ws_log.max_row
        row_cells = ws_log[curr_row]
        
        fill_to_apply = None
        if rec["classification"] == "Approved":
            fill_to_apply = approved_fill
        elif rec["classification"] == "Non-Genuine":
            fill_to_apply = nongen_fill
        elif rec["classification"] == "Manual Review":
            fill_to_apply = flag_fill
            
        for col_idx, cell in enumerate(row_cells, start=1):
            cell.font = regular_font
            cell.border = border_thin
            if col_idx in (1, 2, 8, 9):
                cell.alignment = Alignment(horizontal="center")
            if col_idx == 7 and fill_to_apply:
                cell.fill = fill_to_apply
                cell.font = bold_font
                
    # Column auto-widths for log
    col_widths = [12, 14, 22, 16, 24, 16, 16, 16, 18, 28, 60]
    for idx, width in enumerate(col_widths, start=1):
        col_letter = openpyxl.utils.get_column_letter(idx)
        ws_log.column_dimensions[col_letter].width = width
        
    # Sheet 3: Flagged for Manual Review
    flagged_records = [r for r in evaluated_records if r["classification"] == "Manual Review"]
    if flagged_records:
        ws_flag = wb.create_sheet(title="Manual Review Required")
        ws_flag.views.sheetView[0].showGridLines = True
        
        flag_headers = ["Sheet", "Excel Row #", "Machine Serial No.", "Ticket No.", "Part Name", "Flag Type", "Action Required"]
        ws_flag.append(flag_headers)
        for cell in ws_flag[1]:
            cell.font = header_font
            cell.fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
            
        for rec in flagged_records:
            flag_vals = [
                rec.get("sheet_name", ""),
                rec["row_idx"],
                rec["serial"],
                rec["ticket"],
                rec["part"],
                rec["status"],
                rec["reason"]
            ]
            ws_flag.append(flag_vals)
            curr_row = ws_flag.max_row
            for col_idx, cell in enumerate(ws_flag[curr_row], start=1):
                cell.font = regular_font
                cell.border = border_thin
                if col_idx in (1, 2):
                    cell.alignment = Alignment(horizontal="center")
                    
        for idx, width in enumerate([12, 14, 22, 16, 24, 20, 65], start=1):
            ws_flag.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width
            
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out
