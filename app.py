import streamlit as st
import pandas as pd
import json
import os
import copy
import io
import base64
import qrcode  # Menghasilkan QR code alat
from datetime import datetime, date

# --- 0. SISTEM LOGIN MULTI-ROLE (ADMIN & USER PUBLIK) ---
def check_login():
    """Mengembalikan True jika login berhasil, serta menyimpan role pengguna."""
    def login_entered():
        user_input = st.session_state.get("username_input", "").strip()
        pass_input = st.session_state.get("password_input", "").strip()

        # Data Kredensial Account
        CREDENTIALS = {
            "NAY": {"pass": "lalanana", "role": "Admin", "nama": "NAY (Super Administrator)"},
            "GUEST": {"pass": "12345", "role": "User", "nama": "Teknisi Lapangan"}
        }

        if user_input in CREDENTIALS:
            pass_benar = CREDENTIALS[user_input]["pass"]
            if pass_input == pass_benar:
                st.session_state["login_success"] = True
                st.session_state["user_role"] = CREDENTIALS[user_input]["role"]
                st.session_state["user_nama"] = CREDENTIALS[user_input]["nama"]
                if "password_input" in st.session_state:
                    del st.session_state["password_input"]
                if "username_input" in st.session_state:
                    del st.session_state["username_input"]
            else:
                st.session_state["login_success"] = False
        else:
            st.session_state["login_success"] = False

    if not st.session_state.get("login_success", False):
        st.markdown("<h2 style='text-align: center;'>🔒 Login Sistem W-SIGNAL</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username:", key="username_input")
            st.text_input("Password:", type="password", key="password_input")
            st.button("Masuk / Login", on_click=login_entered, use_container_width=True)
            
            st.info("💡 **Akses Teknisi / Publik:**\n* **Username:** `GUEST` | **Password:** `12345` (Input Perbaikan & Pemeliharaan)")
            
            if st.session_state.get("login_success") == False:
                st.error("😕 Username atau Password salah. Silakan coba lagi.")
                
        return False
    else:
        return True

# JALANKAN APLIKASI HANYA JIKA SUDAH LOGIN
if check_login():

    role_aktif = st.session_state.get("user_role", "User")
    nama_aktif = st.session_state.get("user_nama", "User")

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
        byte_im = buf.getvalue()
        return byte_im

    # --- 1. KONFIGURASI HALAMAN ---
    st.set_page_config(page_title="W-SIGNAL", layout="wide")
    st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
    DB_FILE = os.path.join(BASE_DIR, "database_w_signal.json")

    # --- STRUKTUR KOLOM DEFAULT ---
    KOLOM_DEFAULT = {
        "Inventory Alkes": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Tahun Pengadaan", "Harga Perolehan", "Kondisi Baik", "Kondisi KB", "Kondisi RB", "Ruangan"],
        "Perbaikan": ["Tanggal Perbaikan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Foto", "Note"],
        "Pemeliharaan": ["Tanggal Pemeliharaan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Keterangan", "Foto", "Note"],
        "Stok Suku Cadang": ["Nama Suku Cadang", "Spesifikasi", "Jumlah Stok", "Satuan", "In", "Out", "Keterangan"],
        "Perencanaan RAB (Usulan)": ["Sub Kegiatan", "Nama Kegiatan", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Keterangan"],
        "Surat Masuk (Nota Dinas)": ["Tanggal Terima Surat", "Tanggal Surat", "Nomor Surat", "Perihal", "Asal Surat", "Keterangan"],
        "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"],
        "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Kalibrasi Ulang"]
    }

    # --- 2. FUNGSI DATABASE ---
    def load_data():
        loaded_db = {}
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r") as f: 
                    loaded_db = json.load(f)
            except Exception as e:
                st.error(f"Gagal membaca database lama. Error: {e}")
         
        for k in KOLOM_DEFAULT.keys():
            if k not in loaded_db:
                loaded_db[k] = []
                
        if "SOP_Files" not in loaded_db:
            loaded_db["SOP_Files"] = {}
            
        return loaded_db

    def save_data(data_to_save):
        try:
            with open(DB_FILE, "w") as f: 
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            st.error(f"Gagal mengamankan data ke file: {e}")

    # --- 3. INISIALISASI SESSION STATE ---
    if "w_signal_db" not in st.session_state:
        st.session_state["w_signal_db"] = load_data()

    if "undo_history" not in st.session_state:
        st.session_state["undo_history"] = []

    query_params = st.query_params
    url_no_seri = query_params.get("no_seri", "").strip()
    data = st.session_state["w_signal_db"]

    # --- 4. FUNGSI HELPER ---
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
                    "Ruangan": item.get("Ruangan", ""),
                    "Tahun Pengadaan": item.get("Tahun Pengadaan", "")
                }
        return peta

    def dapatkan_daftar_nama_alat_inventory():
        inv_list = data.get("Inventory Alkes", [])
        nama_set = set()
        for item in inv_list:
            nama = str(item.get("Nama Alat", "")).strip()
            if nama:
                nama_set.add(nama)
        return sorted(list(nama_set))

    def hitung_frekuensi_kerusakan():
        perbaikan_list = data.get("Perbaikan", [])
        counter = {}
        for item in perbaikan_list:
            ns = str(item.get("Nomor Seri", "")).strip().lower()
            if ns:
                counter[ns] = counter.get(ns, 0) + 1
        return counter

    def dapatkan_set_terkalibrasi():
        kalibrasi_list = data.get("Kalibrasi", [])
        ns_set = set()
        for item in kalibrasi_list:
            ns = str(item.get("Nomor Seri", "")).strip().lower()
            if ns:
                ns_set.add(ns)
        return ns_set

    def dapatkan_set_terpelihara():
        pemeliharaan_list = data.get("Pemeliharaan", [])
        ns_set = set()
        for item in pemeliharaan_list:
            ns = str(item.get("Nomor Seri", "")).strip().lower()
            if ns:
                ns_set.add(ns)
        return ns_set

    def recalculate_rab(rab_list):
        df = pd.DataFrame(rab_list)
        if df.empty: return rab_list
        kolom_wajib = ["Sub Kegiatan", "Nama Kegiatan", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Keterangan"]
        for col in kolom_wajib:
            if col not in df.columns: df[col] = 0 if "Pagu" in col or "Nilai" in col else ""
                
        df["Pagu Sub Kegiatan"] = df["Pagu Sub Kegiatan"].apply(lambda x: float(str(x).replace(',','').replace('.','')) if x else 0.0)
        df["Nilai SPH"] = df["Nilai SPH"].apply(lambda x: float(str(x).replace(',','').replace('.','')) if x else 0.0)
        df["Nilai Kontrak"] = df["Nilai Kontrak"].apply(lambda x: float(str(x).replace(',','').replace('.','')) if x else 0.0)
        
        master_pagu = {}
        for idx, row in df.iterrows():
            sub_keg = row["Sub Kegiatan"]
            pagu_val = row["Pagu Sub Kegiatan"]
            if sub_keg not in master_pagu and pagu_val > 0: master_pagu[sub_keg] = pagu_val
                
        sisa_list = []
        current_pagu_tracker = master_pagu.copy() 
        for idx, row in df.iterrows():
            sub_keg = row["Sub Kegiatan"]
            kontrak = row["Nilai Kontrak"]
            pagu_induk = current_pagu_tracker.get(sub_keg, 0.0)
            pagu_terbaru = pagu_induk - kontrak
            sisa_list.append(int(pagu_terbaru))
            current_pagu_tracker[sub_keg] = pagu_terbaru
            if sub_keg in master_pagu: df.at[idx, "Pagu Sub Kegiatan"] = int(master_pagu[sub_keg])

        df["Sisa Pagu Anggaran Kegiatan"] = sisa_list
        return df.to_dict(orient="records")

    def bersihkan_format_tanggal(val):
        if pd.isna(val) or val == "" or str(val).strip() == "nan":
            return ""
        if isinstance(val, (datetime, date)):
            return val.strftime('%Y-%m-%d')
        val_str = str(val).strip()
        if " " in val_str:
            val_str = val_str.split(" ")[0]
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
                            df_current[col] = 0 if col in ["Jumlah Stok", "In", "Out", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Harga Perolehan"] else ""
                
                for row_idx, changes in raw_editor_data.get("edited_rows", {}).items():
                    for col, val in changes.items():
                        if col in df_current.columns: 
                            df_current.iat[row_idx, df_current.columns.get_loc(col)] = val
                            
                for new_row in raw_editor_data.get("added_rows", []):
                    df_current = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)
                    
                deleted_indices = raw_editor_data.get("deleted_rows", [])
                if deleted_indices: 
                    df_current = df_current.drop(deleted_indices).reset_index(drop=True)
                    
                kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat", "Kalibrasi Ulang"]
                for col in kolom_tanggal_sistem:
                    if col in df_current.columns:
                        df_current[col] = df_current[col].apply(bersihkan_format_tanggal)

                temp_dict = df_current.fillna("").to_dict(orient="records")
                if menu_key == "Perencanaan RAB (Usulan)": 
                    temp_dict = recalculate_rab(temp_dict)
                
                st.session_state["w_signal_db"][menu_key] = temp_dict
                save_data(st.session_state["w_signal_db"])

    def convert_df_to_excel(df_to_download):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_to_download.to_excel(writer, index=False, sheet_name='Data Rekap')
        return output.getvalue()

    # --- 7. SIDEBAR & PEMBATASAN HAK AKSES ---
    st.sidebar.header("↩️ KONTROL DATA")
    st.sidebar.caption(f"Status: **{nama_aktif}** ({role_aktif})")
    
    if st.sidebar.button("🚪 Logout / Keluar", use_container_width=True):
        st.session_state["login_success"] = False
        st.rerun()

    if role_aktif == "Admin" and st.session_state["undo_history"]:
        if st.sidebar.button("↩️ Undo Perubahan Terakhir", use_container_width=True):
            st.session_state["w_signal_db"] = st.session_state["undo_history"].pop()
            save_data(st.session_state["w_signal_db"])
            st.success("Perubahan terakhir berhasil dibatalkan!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 SCAN / CARI ALAT")
    search_ns = st.sidebar.text_input("Arahkan kursor & Scan Barcode:", value=url_no_seri)

    st.sidebar.markdown("---")
    st.sidebar.header("Pilih Menu:")

    if role_aktif == "Admin":
        menu_
