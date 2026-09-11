import io
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def create_sample_files():
    """
    Generates standard test Excel files:
    1. sample_mahavir.xlsx
    2. sample_reference.xlsx
    covering all specification rules.
    """
    # -------------------------------------------------------------
    # 1. Sample Reference Data
    # -------------------------------------------------------------
    ref_rows = [
        # MS001: 2 different tickets for SAME part (Drain Pump: T1001, T1002) -> Approved
        {"Machine Serial Number": "MS001", "Ticket Number": "T1001", "Part Name": "Drain Pump", "Branch": "Mumbai"},
        {"Machine Serial Number": "MS001", "Ticket Number": "T1002", "Part Name": "Drain Pump", "Branch": "Mumbai"},
        
        # MS002: 1 ticket (T2001) -> Non-Genuine
        {"Machine Serial Number": "MS002", "Ticket Number": "T2001", "Part Name": "Pulsator", "Branch": "Delhi"},
        {"Machine Serial Number": "MS002", "Ticket Number": "T2001", "Part Name": "Pulsator Cap", "Branch": "Delhi"}, # duplicate ticket check
        
        # MS003: Front & Rear Suspension Rod with same ticket (T3001) -> Non-Genuine (0 additional)
        {"Machine Serial Number": "MS003", "Ticket Number": "T3001", "Part Name": "Front Suspension Rod", "Branch": "Bangalore"},
        {"Machine Serial Number": "MS003", "Ticket Number": "T3001", "Part Name": "Rear Suspension Rod", "Branch": "Bangalore"},
        
        # MS004: Front & Rear Suspension Rod with T4001, plus T4002 and T4003 (2 additional suspension tickets) -> Approved
        {"Machine Serial Number": "MS004", "Ticket Number": "T4001", "Part Name": "Front Suspension Rod", "Branch": "Pune"},
        {"Machine Serial Number": "MS004", "Ticket Number": "T4001", "Part Name": "Rear Suspension Rod", "Branch": "Pune"},
        {"Machine Serial Number": "MS004", "Ticket Number": "T4002", "Part Name": "Front Suspension Rod", "Branch": "Pune"},
        {"Machine Serial Number": "MS004", "Ticket Number": "T4003", "Part Name": "Rear Suspension Rod", "Branch": "Pune"},
        
        # MS005: Approved row (preserved)
        {"Machine Serial Number": "MS005", "Ticket Number": "T5001", "Part Name": "PCB Main", "Branch": "Kolkata"},
        
        # MS006: Damaged row (preserved)
        {"Machine Serial Number": "MS006", "Ticket Number": "T6001", "Part Name": "Outer Tub", "Branch": "Chennai"},
        
        # MS009: Suspension Rod with T9001 + 1 additional ticket T9002 -> Non-Genuine (< 2 additional)
        {"Machine Serial Number": "MS009", "Ticket Number": "T9001", "Part Name": "Front Suspension Rod", "Branch": "Goa"},
        {"Machine Serial Number": "MS009", "Ticket Number": "T9001", "Part Name": "Rear Suspension Rod", "Branch": "Goa"},
        {"Machine Serial Number": "MS009", "Ticket Number": "T9002", "Part Name": "Front Suspension Rod", "Branch": "Goa"},

        # MS010: 2 tickets on same machine but for DIFFERENT parts (T1010 Valve, T1011 Pump) -> Non-Genuine for Valve
        {"Machine Serial Number": "MS010", "Ticket Number": "T1010", "Part Name": "Inlet Valve", "Branch": "Delhi"},
        {"Machine Serial Number": "MS010", "Ticket Number": "T1011", "Part Name": "Drain Pump", "Branch": "Delhi"},
    ]
    ref_df = pd.DataFrame(ref_rows)
    
    # -------------------------------------------------------------
    # 2. Sample Mahavir Data
    # -------------------------------------------------------------
    mah_rows = [
        {"Machine Serial Number": "MS001", "Ticket Number": "T1001", "Part Name": "Drain Pump", "FQC Analysis": "NG to Verify", "TRF. PRICE": 450, "Technician": "Rajesh"},
        {"Machine Serial Number": "MS002", "Ticket Number": "T2001", "Part Name": "Pulsator", "FQC Analysis": "NG to Verify", "TRF. PRICE": 720, "Technician": "Amit"},
        {"Machine Serial Number": "MS003", "Ticket Number": "T3001", "Part Name": "Front Suspension Rod", "FQC Analysis": "NG to Verify", "TRF. PRICE": 380, "Technician": "Suresh"},
        {"Machine Serial Number": "MS003", "Ticket Number": "T3001", "Part Name": "Rear Suspension Rod", "FQC Analysis": "NG to Verify", "TRF. PRICE": 380, "Technician": "Suresh"},
        {"Machine Serial Number": "MS004", "Ticket Number": "T4001", "Part Name": "Front Suspension Rod", "FQC Analysis": "NG to Verify", "TRF. PRICE": 400, "Technician": "Vikram"},
        {"Machine Serial Number": "MS004", "Ticket Number": "T4001", "Part Name": "Rear Suspension Rod", "FQC Analysis": "NG to Verify", "TRF. PRICE": 400, "Technician": "Vikram"},
        {"Machine Serial Number": "MS005", "Ticket Number": "T5001", "Part Name": "PCB Main", "FQC Analysis": "Approved", "TRF. PRICE": 1850, "Technician": "Deepak"},
        {"Machine Serial Number": "MS006", "Ticket Number": "T6001", "Part Name": "Outer Tub", "FQC Analysis": "DAMAGED", "TRF. PRICE": 2400, "Technician": "Manoj"},
        {"Machine Serial Number": "MS007", "Ticket Number": "T7001", "Part Name": "Clutch Assembly", "FQC Analysis": "NG to Verify", "TRF. PRICE": 950, "Technician": "Anil"}, # Not in Ref
        {"Machine Serial Number": "",      "Ticket Number": "T8001", "Part Name": "Pressure Sensor", "FQC Analysis": "NG to Verify", "TRF. PRICE": 320, "Technician": "Pooja"}, # Missing Serial
        {"Machine Serial Number": "MS009", "Ticket Number": "T9001", "Part Name": "Front Suspension Rod", "FQC Analysis": "NG to Verify", "TRF. PRICE": 390, "Technician": "Kiran"},
        {"Machine Serial Number": "MS010", "Ticket Number": "T1010", "Part Name": "Inlet Valve", "FQC Analysis": "NG to Verify", "TRF. PRICE": 550, "Technician": "Rohit"},
    ]
    mah_df = pd.DataFrame(mah_rows)
    
    # Write styled Excel files
    ref_io = io.BytesIO()
    with pd.ExcelWriter(ref_io, engine="openpyxl") as writer:
        ref_df.to_excel(writer, sheet_name="Reference_Data", index=False)
    ref_io.seek(0)
    
    mah_io = io.BytesIO()
    with pd.ExcelWriter(mah_io, engine="openpyxl") as writer:
        mah_df.to_excel(writer, sheet_name="Mahavir_FQC", index=False)
    mah_io.seek(0)
    
    return mah_io.getvalue(), ref_io.getvalue()


def main():
    mah_bytes, ref_bytes = create_sample_files()
    with open("sample_mahavir.xlsx", "wb") as f:
        f.write(mah_bytes)
    with open("sample_reference.xlsx", "wb") as f:
        f.write(ref_bytes)
    print("Sample Excel files created successfully!")


if __name__ == "__main__":
    main()

