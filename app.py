import streamlit as st
import pandas as pd
import json
import os
import base64
import qrcode
from datetime import datetime, date

# --- IMPOR GSPREAD ---
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# URL Google Sheet Anda
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1LNy2HFfrDpRQu0tG-afxGG-HaSJh5ewIVGUopttb2qs/edit?usp=sharing"

# --- Koneksi Google Sheets Tanpa JSON Rahasia (Berbasis Publik Link Editor) ---
def get_gspread_client():
    if not GSPREAD_AVAILABLE:
        return None
    try:
        # Jika menggunakan gspread dengan metode authorized public/oauth atau json secrets
        if "gcp_service_account" in st.secrets:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["gcp_service_account"])
            from oauth2client.service_account import ServiceAccountCredentials
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client
        else:
            # Fallback jika ingin menggunakan gspread tanpa credentials (untuk sheet public edit)
            # Menggunakan gspread anonymous / gspread.no_credentials() jika didukung versi gspread, 
            # atau kita gunakan pandas untuk membaca CSV publik jika lebih stabil.
            pass
    except Exception:
        pass
    return None

# --- STRUKTUR KOLOM DEFAULT ---
KOLOM_DEFAULT = {
    "Inventory Alkes": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Tahun Pengadaan", "Harga Perolehan", "Kondisi Baik", "Kondisi KB", "Kondisi RB", "Ruangan"],
    "Perbaikan": ["Tanggal Perbaikan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Isian LK Service", "Foto", "Note"],
    "Pemeliharaan": ["Tanggal Pemeliharaan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Hasil Pemeliharaan", "Isian LK IPM", "Foto", "Note"],
    "Stok Suku Cadang": ["Nama Suku Cadang", "Spesifikasi", "Jumlah Stok", "Satuan", "In", "Out", "Keterangan"],
    "Perencanaan RAB (Usulan)": ["Sub Kegiatan", "Nama Kegiatan", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Keterangan"],
    "Surat Masuk (Nota Dinas)": ["Tanggal Terima Surat", "Tanggal Surat", "Nomor Surat", "Perihal", "Asal Surat", "Keterangan"],
    "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"],
    "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Kalibrasi Ulang"]
}

def load_data_from_gsheets():
    database = {}
    client = get_gspread_client()
    if client:
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            for sheet_name in KOLOM_DEFAULT.keys():
                try:
                    worksheet = sh.worksheet(sheet_name)
                    records = worksheet.get_all_records()
                    database[sheet_name] = records if records else []
                except Exception:
                    database[sheet_name] = []
        except Exception:
            database = fallback_load_local()
    else:
        # Membaca langsung via export CSV Google Sheets secara publik (Sangat stabil & tanpa login robot!)
        try:
            for sheet_name in KOLOM_DEFAULT.keys():
                csv_url = f"{SPREADSHEET_URL.split('/edit')[0]}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
                df = pd.read_csv(csv_url)
                database[sheet_name] = df.to_dict(orient="records")
        except Exception:
            database = fallback_load_local()

    if "SOP_Files" not in database:
        database["SOP_Files"] = {}
    return database

def save_row_to_gsheets(sheet_name, row_data):
    client = get_gspread_client()
    if client:
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet(sheet_name)
            headers = KOLOM_DEFAULT.get(sheet_name, list(row_data.keys()))
            row_values = [row_data.get(h, "") for h in headers]
            worksheet.append_row(row_values)
            return True
        except Exception as e:
            st.error(f"Gagal menyimpan ke Google Sheets: {e}")
            return False
    else:
        # Simpan lokal sebagai backup jika gspread belum terkonfigurasi penuh
        db = st.session_state.get("w_signal_db", {})
        if sheet_name not in db:
            db[sheet_name] = []
        db[sheet_name].append(row_data)
        fallback_save_local(db)
        return True

def fallback_load_local():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
    DB_FILE = os.path.join(BASE_DIR, "database_w_signal.json")
    loaded_db = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                loaded_db = json.load(f)
        except Exception:
            pass
    for k in KOLOM_DEFAULT.keys():
        if k not in loaded_db:
            loaded_db[k] = []
    return loaded_db

def fallback_save_local(data_to_save):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
    DB_FILE = os.path.join(BASE_DIR, "database_w_signal.json")
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data_to_save, f, indent=4)
    except Exception:
        pass


# --- SISTEM LOGIN MULTI-ROLE ---
def check_login():
    def login_entered():
        user_input = st.session_state.get("username_input", "").strip()
        pass_input = st.session_state.get("password_input", "").strip()

        CREDENTIALS = {
            "NAY": {"pass": "lalanana", "role": "Admin", "nama": "NAY (Super Administrator)"},
            "GUEST": {"pass": "12345", "role": "User", "nama": "Teknisi Lapangan"}
        }

        if user_input in CREDENTIALS:
            if pass_input == CREDENTIALS[user_input]["pass"]:
                st.session_state["login_success"] = True
                st.session_state["user_role"] = CREDENTIALS[user_input]["role"]
                st.session_state["user_nama"] = CREDENTIALS[user_input]["nama"]
                if "password_input" in st.session_state: del st.session_state["password_input"]
                if "username_input" in st.session_state: del st.session_state["username_input"]
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
                st.error("😕 Username atau Password salah.")
        return False
    else:
        return True

if check_login():
    role_aktif = st.session_state.get("user_role", "User")
    nama_aktif = st.session_state.get("user_nama", "User")

    st.set_page_config(page_title="W-SIGNAL", layout="wide")
    st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

    if "w_signal_db" not in st.session_state:
        st.session_state["w_signal_db"] = load_data_from_gsheets()
    
    data = st.session_state["w_signal_db"]
    query_params = st.query_params
    url_no_seri = query_params.get("no_seri", "").strip()

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

    # --- SIDEBAR & NAVIGASI ---
    st.sidebar.header("↩️ KONTROL DATA")
    st.sidebar.caption(f"Status: **{nama_aktif}** ({role_aktif})")
    
    if st.sidebar.button("🚪 Logout / Keluar", use_container_width=True):
        st.session_state["login_success"] = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 SCAN / CARI ALAT")
    search_ns = st.sidebar.text_input("Arahkan kursor & Scan Barcode:", value=url_no_seri)

    st.sidebar.markdown("---")
    st.sidebar.header("Pilih Menu:")

    if role_aktif == "Admin":
        menu_pilihan = [
            "Inventory Alkes", "Perbaikan", "Pemeliharaan", "Stok Suku Cadang",
            "Perencanaan RAB (Usulan)", "Surat Masuk (Nota Dinas)", "Rekap SR Vendor", 
            "Kalibrasi", "Lihat Semua Data & Ringkasan", "Manajemen SOP Alkes"
        ]
    else:
        menu_pilihan = ["Perbaikan", "Pemeliharaan"]

    selected_menu = st.sidebar.radio("Navigasi Menu", menu_pilihan, label_visibility="collapsed")

    if role_aktif == "Admin":
        total_perbaikan_notif = len(data.get('Perbaikan', []))
        total_pemeliharaan_notif = len(data.get('Pemeliharaan', []))
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔔 Pusat Notifikasi Admin")
        st.sidebar.info(f"📢 Total Laporan Masuk:\n* **Perbaikan:** {total_perbaikan_notif} Laporan\n* **Pemeliharaan:** {total_pemeliharaan_notif} Kegiatan")

    if selected_menu == "Lihat Semua Data & Ringkasan" and role_aktif == "Admin":
        st.header("📋 Ringkasan Analisis Data W-SIGNAL (Google Sheets)")
        if st.button("🔄 Segarkan / Tarik Data Terbaru"):
            st.session_state["w_signal_db"] = load_data_from_gsheets()
            st.rerun()

        tabs = st.tabs(list(KOLOM_DEFAULT.keys()))
        for i, key in enumerate(list(KOLOM_DEFAULT.keys())):
            with tabs[i]:
                df_tab = pd.DataFrame(data[key])
                st.dataframe(df_tab, use_container_width=True)

    else:
        st.header(f"📋 Menu: {selected_menu}")
        
        with st.form(key=f"form_{selected_menu.lower().replace(' ', '_')}", clear_on_submit=True):
            inputs = {}
            uploaded_photo = None

            if selected_menu == "Perbaikan":
                st.markdown("### 📥 Form Input Perbaikan Alkes & LK Service")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    inputs["Tanggal Perbaikan"] = str(st.date_input("Tanggal Perbaikan"))
                    inputs["Nama Teknisi"] = st.text_input("Nama Teknisi")
                    inputs["Nama Alat"] = st.text_input("Nama Alat")
                with col_s2:
                    inputs["Merk"] = st.text_input("Merk / Tipe")
                    inputs["Nomor Seri"] = st.text_input("Nomor Seri (SN)")
                    inputs["Ruangan"] = st.text_input("Ruangan")

                inputs["Kerusakan"] = st.text_area("Uraian Kerusakan")
                inputs["Tindakan"] = st.text_area("Tindakan Perbaikan")
                inputs["Keterangan"] = st.text_input("Keterangan")

                st.markdown("---")
                st.markdown("#### 🔧 Isian Lembar Kerja (LK Service Elektromedis)")
                lk_s1, lk_s2 = st.columns(2)
                with lk_s1:
                    suhu_s = st.text_input("Suhu Ruangan (°C)", value="25", key="suhu_serv")
                    kelembaban_s = st.text_input("Kelembaban (%)", value="60", key="kel_serv")
                    tegangan_s = st.text_input("Tegangan Jala-jala (V)", value="220", key="teg_serv")
                    env_s = f"Suhu: {suhu_s}°C, Kelembaban: {kelembaban_s}%, Tegangan: {tegangan_s}V"
                with lk_s2:
                    fisik_s = st.selectbox("Pemeriksaan Fisik / Main Unit / Aksesoris", ["Baik", "Kurang Baik", "Rusak"], key="fisik_serv")
                    fungsi_s = st.selectbox("Pengujian Fungsi (Switch, Keypad, Alarm)", ["Normal", "Gangguan"], key="fungsi_serv")
                    inputs["Isian LK Service"] = f"{env_s} | Fisik: {fisik_s}, Fungsi: {fungsi_s}"

                uploaded_photo = st.file_uploader("📷 Upload Foto Perbaikan (.jpg, .png):", type=["jpg", "jpeg", "png"])
                inputs["Foto"] = ""
                inputs["Note"] = ""

            elif selected_menu == "Pemeliharaan":
                st.markdown("### 📋 Form Input Pemeliharaan & Lembar Kerja (LK IPM)")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    inputs["Tanggal Pemeliharaan"] = str(st.date_input("Tanggal Pemeliharaan"))
                    inputs["Nama Teknisi"] = st.text_input("Nama Teknisi")
                    inputs["Nama Alat"] = st.text_input("Nama Alat")
                with col_p2:
                    inputs["Merk"] = st.text_input("Merk / Tipe")
                    inputs["Nomor Seri"] = st.text_input("Nomor Seri (SN)")
                    inputs["Ruangan"] = st.text_input("Ruangan")

                inputs["Hasil Pemeliharaan"] = st.selectbox("Hasil Pemeliharaan", ["Laik Pakai / Normal", "Perlu Perbaikan Lanjutan", "Tidak Laik Pakai"])

                st.markdown("---")
                st.markdown("#### 🔬 Isian Lembar Kerja (LK IPM Elektromedis)")
                lk_c1, lk_c2 = st.columns(2)
                with lk_c1:
                    suhu_p = st.text_input("Suhu Ruangan (°C)", value="25", key="suhu_ipm")
                    kelembaban_p = st.text_input("Kelembaban (%)", value="60", key="kel_ipm")
                    ground_p = st.text_input("Ground Resistance (Ω)", value="< 0.5", key="ground_ipm")
                with lk_c2:
                    stabilizer_p = st.selectbox("Stabilizer / Kelistrikan", ["Normal", "Tidak Normal"], key="stab_ipm")
                    fungsi_p = st.selectbox("Fungsi & Kelengkapan Alat", ["Lengkap & Berfungsi Baik", "Ada Catatan"], key="fungsi_ipm")
                    inputs["Isian LK IPM"] = f"Suhu: {suhu_p}°C, Kelembaban: {kelembaban_p}%, Ground: {ground_p}Ω, Stabilizer: {stabilizer_p}, Fungsi: {fungsi_p}"

                inputs["Keterangan"] = st.text_input("Keterangan / Catatan Pemeliharaan")
                uploaded_photo = st.file_uploader("📷 Upload Foto Alat / Lembar Kerja (.jpg, .png):", type=["jpg", "jpeg", "png"])
                inputs["Foto"] = ""
                inputs["Note"] = ""

            elif role_aktif == "Admin":
                if selected_menu == "Inventory Alkes":
                    inputs["Nama Alat"] = st.text_input("Nama Alat")
                    inputs["Merk"] = st.text_input("Merk")
                    inputs["Type"] = st.text_input("Type")
                    inputs["Nomor Seri"] = st.text_input("Nomor Seri")
                    inputs["Tahun Pengadaan"] = st.text_input("Tahun Pengadaan")
                    inputs["Harga Perolehan"] = st.number_input("Harga Perolehan (Rp)", min_value=0.0, step=1000.0)
                    inputs["Kondisi Baik"] = st.selectbox("Kondisi Baik", ["✓", "-"])
                    inputs["Kondisi KB"] = st.selectbox("Kondisi KB", ["-", "✓"])
                    inputs["Kondisi RB"] = st.selectbox("Kondisi RB", ["-", "✓"])
                    inputs["Ruangan"] = st.text_input("Ruangan")

            submit_button = st.form_submit_button(label="➕ Kirim & Simpan Laporan")
            if submit_button:
                if uploaded_photo is not None:
                    bytes_data = uploaded_photo.read()
                    inputs["Foto"] = base64.b64encode(bytes_data).decode('utf-8')

                if selected_menu in ["Perbaikan", "Pemeliharaan"]:
                    peta_inv = dapatkan_peta_inventory()
                    ns_key = str(inputs.get("Nomor Seri", "")).strip().lower()
                    if ns_key in peta_inv:
                        if not inputs.get("Nama Alat"): inputs["Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                        if not inputs.get("Merk"): inputs["Merk"] = peta_inv[ns_key]["Merk"]
                        if not inputs.get("Ruangan"): inputs["Ruangan"] = peta_inv[ns_key]["Ruangan"]

                success = save_row_to_gsheets(selected_menu, inputs)
                if success:
                    st.session_state["w_signal_db"] = load_data_from_gsheets()
                    st.success(f"Laporan {selected_menu} berhasil dikirim dan otomatis terekap di Super Admin!")
                    st.rerun()

        if role_aktif == "Admin":
            st.markdown("---")
            st.markdown("### 📝 Tabel & Galeri Riwayat Laporan (Pusat Data Admin)")
            if st.button("🔄 Refresh Data Google Sheets"):
                st.session_state["w_signal_db"] = load_data_from_gsheets()
                st.rerun()

            menu_data = data.get(selected_menu, [])
            df_menu = pd.DataFrame(menu_data)

            if not df_menu.empty:
                df_display = df_menu.copy()
                if "Foto" in df_display.columns:
                    df_display["Foto Status"] = df_display["Foto"].apply(lambda x: "🖼️ Ada Foto" if x else "Tidak Ada")
                    df_display = df_display.drop(columns=["Foto"])
                
                st.dataframe(df_display, use_container_width=True)

                if "Foto" in df_menu.columns:
                    st.markdown("#### 🖼️ Galeri Foto Bukti Laporan:")
                    cols = st.columns(3)
                    idx_col = 0
                    for idx, row in df_menu.iterrows():
                        if row.get("Foto"):
                            with cols[idx_col % 3]:
                                try:
                                    img_bytes = base64.b64decode(row["Foto"])
                                    teknisi_info = f"Teknisi: {row.get('Nama Teknisi', 'Umum')}"
                                    st.image(img_bytes, caption=f"{row.get('Nama Alat', 'Alat')} ({row.get('Nomor Seri', '')}) - {teknisi_info}", use_container_width=True)
                                except Exception:
                                    pass
                            idx_col += 1
