import streamlit as st
import pandas as pd
import json
import os
import copy
import io
import qrcode
from datetime import datetime, date

def generate_qr_code(no_seri, nama_alat):
    base_url = "https://w-signal.streamlit.app" 
    qr_data = f"{base_url}/?no_seri={no_seri}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

st.set_page_config(page_title="W-SIGNAL", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "database_w_signal.json")

KOLOM_DEFAULT = {
    "Inventory Alkes": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tahun Pengadaan"],
    "Perbaikan": ["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Note"],
    "Pemeliharaan": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"],
    "Stok Suku Cadang": ["Nama Suku Cadang", "Spesifikasi", "Jumlah Stok", "Satuan", "In", "Out", "Keterangan"],
    "Perencanaan RAB (Usulan)": ["Sub Kegiatan", "Nama Kegiatan", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Keterangan"],
    "Surat Masuk (Nota Dinas)": ["Tanggal Terima Surat", "Tanggal Surat", "Nomor Surat", "Perihal", "Asal Surat", "Keterangan"],
    "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"],
    "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Note"]
}

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                return json.load(f)
        except Exception as e:
            pass
    initial_db = {k: [] for k in KOLOM_DEFAULT.keys()}
    initial_db["SOP_Files"] = {} 
    return initial_db

def save_data(data_to_save):
    try:
        with open(DB_FILE, "w") as f: 
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        st.error(f"Gagal mengamankan data: {e}")

if "w_signal_db" not in st.session_state:
    raw_data = load_data()
    for k in KOLOM_DEFAULT.keys():
        if k not in raw_data: raw_data[k] = []
    if "SOP_Files" not in raw_data: raw_data["SOP_Files"] = {}
    st.session_state["w_signal_db"] = raw_data

if "undo_history" not in st.session_state:
    st.session_state["undo_history"] = []

# --- AMBIL PARAMETER NO SERI QR CODE ---
query_params = st.query_params
url_no_seri = query_params.get("no_seri", "")
if isinstance(url_no_seri, list):
    url_no_seri = url_no_seri[0] if url_no_seri else ""
url_no_seri = str(url_no_seri).strip()

data = st.session_state["w_signal_db"]

def dapatkan_peta_inventory():
    inv_list = data.get("Inventory Alkes", [])
    peta = {}
    for item in inv_list:
        ns = str(item.get("Nomor Seri", "")).strip().lower()
        if ns:
            peta[ns] = {
                "Nama Alat": item.get("Nama Alat", ""),
                "Merk": item.get("Merk", ""),
                "Type": item.get("Type", ""),
                "Nomor Seri": item.get("Nomor Seri", ""),
                "Ruangan": item.get("Ruangan", ""),
                "Tahun Pengadaan": item.get("Tahun Pengadaan", "")
            }
    return peta

def dapatkan_daftar_nama_alat_inventory():
    inv_list = data.get("Inventory Alkes", [])
    nama_set = set()
    for item in inv_list:
        nama = str(item.get("Nama Alat", "")).strip()
        if nama: nama_set.add(nama)
    return sorted(list(nama_set))

def bersihkan_format_tanggal(val):
    if pd.isna(val) or val == "": return ""
    if isinstance(val, (datetime, date)): return val.strftime('%Y-%m-%d')
    val_str = str(val).strip()
    if " " in val_str: val_str = val_str.split(" ")[0]
    return val_str

def handle_editor_change(menu_key, editor_key):
    if editor_key in st.session_state:
        raw_editor_data = st.session_state[editor_key]
        if raw_editor_data.get("edited_rows") or raw_editor_data.get("added_rows") or raw_editor_data.get("deleted_rows"):
            st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
            df_current = pd.DataFrame(data[menu_key])
            if menu_key in KOLOM_DEFAULT:
                for col in KOLOM_DEFAULT[menu_key]:
                    if col not in df_current.columns:
                        df_current[col] = 0 if col in ["Jumlah Stok", "In", "Out", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan"] else ""
            for row_idx, changes in raw_editor_data.get("edited_rows", {}).items():
                for col, val in changes.items():
                    if col in df_current.columns: df_current.iat[row_idx, df_current.columns.get_loc(col)] = val
            for new_row in raw_editor_data.get("added_rows", []):
                df_current = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)
            deleted_indices = raw_editor_data.get("deleted_rows", [])
            if deleted_indices: df_current = df_current.drop(deleted_indices).reset_index(drop=True)
            if menu_key in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                peta_inv = dapatkan_peta_inventory()
                for idx, row in df_current.iterrows():
                    ns_key = str(row.get("Nomor Seri", "")).strip().lower()
                    current_note = str(row.get("Note", "")).strip()
                    if ns_key in peta_inv:
                        df_current.at[idx, "Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                        df_current.at[idx, "Merk"] = peta_inv[ns_key]["Merk"]
                        df_current.at[idx, "Type"] = peta_inv[ns_key]["Type"]
                        if "Ruangan" in df_current.columns: df_current.at[idx, "Ruangan"] = peta_inv[ns_key]["Ruangan"]
                        if current_note == "⚠️ BELUM DIINVENTORY": df_current.at[idx, "Note"] = ""
                    elif ns_key != "":
                        if not current_note or current_note == "None": df_current.at[idx, "Note"] = "⚠️ BELUM DIINVENTORY"
            kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
            for col in kolom_tanggal_sistem:
                if col in df_current.columns: df_current[col] = df_current[col].apply(bersihkan_format_tanggal)
            temp_dict = df_current.fillna("").to_dict(orient="records")
            st.session_state["w_signal_db"][menu_key] = temp_dict
            save_data(st.session_state["w_signal_db"])

def convert_df_to_excel(df_to_download):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_to_download.to_excel(writer, index=False, sheet_name='Data Rekap')
    return output.getvalue()


# =====================================================================
# CONDITION A: JIKA DI-SCAN VIA KAMERA (DITEMUKAN PARAMETER URL NO_SERI)
# =====================================================================
if url_no_seri != "":
    st.title("📟 W-SIGNAL (E-Label Info Alat Terintegrasi)")
    peta_inv = dapatkan_peta_inventory()
    ns_clean = url_no_seri.strip().lower()
