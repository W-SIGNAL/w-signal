import streamlit as st
import pandas as pd
import json
import os
import copy
import io
import base64
import qrcode
from datetime import datetime, date

# --- 0. SISTEM LOGIN MULTI-ROLE (ADMIN & USER PUBLIK) ---
def check_login():
    """Mengembalikan True jika login berhasil, serta menyimpan role pengguna."""
    def login_entered():
        user_input = st.session_state.get("username_input", "").strip()
        pass_input = st.session_state.get("password_input", "").strip()

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
        "Perbaikan": ["Tanggal Perbaikan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Isian LK Service", "Foto", "Note"],
        "Pemeliharaan": ["Tanggal Pemeliharaan", "Nama Teknisi", "Nama Alat", "Merk", "Nomor Seri", "Ruangan", "Hasil Pemeliharaan", "Isian LK IPM", "Foto", "Note"],
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

    # --- 7. SIDEBAR & MENU ---
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

    # Notifikasi Super Admin
    if role_aktif == "Admin":
        total_perbaikan_notif = len(data.get('Perbaikan', []))
        total_pemeliharaan_notif = len(data.get('Pemeliharaan', []))
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔔 Pusat Notifikasi Admin")
        st.sidebar.info(f"📢 Total Laporan Masuk:\n* **Perbaikan:** {total_perbaikan_notif} Laporan\n* **Pemeliharaan:** {total_pemeliharaan_notif} Kegiatan")

    if selected_menu == "Lihat Semua Data & Ringkasan" and role_aktif == "Admin":
        st.header("📋 Ringkasan Analisis Data W-SIGNAL")
        inv_list_data = data.get('Inventory Alkes', [])
        total_inv_count = len(inv_list_data)
        baik_count = sum(1 for item in inv_list_data if str(item.get("Kondisi Baik", "")).strip() in ["✓", "1", "True", "true"])
        kb_count = sum(1 for item in inv_list_data if str(item.get("Kondisi KB", "")).strip() in ["✓", "1", "True", "true"])
        rb_count = sum(1 for item in inv_list_data if str(item.get("Kondisi RB", "")).strip() in ["✓", "1", "True", "true"])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Inventory", f"{total_inv_count} Unit")
        col2.metric("Total Pemeliharaan", f"{len(data.get('Pemeliharaan', []))} Kegiatan")
        col3.metric("Total Kalibrasi", f"{len(data.get('Kalibrasi', []))} Data")
        
        st.markdown("---")
        tabs = st.tabs(list(KOLOM_DEFAULT.keys()))
        for i, key in enumerate(list(KOLOM_DEFAULT.keys())):
            with tabs[i]:
                df_tab = pd.DataFrame(data[key])
                st.dataframe(df_tab, use_container_width=True)

    else:
        st.header(f"📋 Menu: {selected_menu}")
        
        # --- FORM INPUT PERBAIKAN & PEMELIHARAAN (LK SERVICE & LK IPM) ---
        with st.form(key=f"form_{selected_menu.lower().replace(' ', '_')}", clear_on_submit=True):
            inputs = {}
            uploaded_photo = None

            if selected_menu == "Perbaikan":
                st.markdown("### 📥 Form Input Perbaikan Alkes & LK Service")
                
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    inputs["Tanggal Perbaikan"] = st.date_input("Tanggal Perbaikan").strftime('%Y-%m-%d')
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
                inputs["Note"] = ""

            elif selected_menu == "Pemeliharaan":
                st.markdown("### 📋 Form Input Pemeliharaan & Lembar Kerja (LK IPM)")
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    inputs["Tanggal Pemeliharaan"] = st.date_input("Tanggal Pemeliharaan").strftime('%Y-%m-%d')
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
                inputs["Note"] = ""

            elif role_aktif == "Admin":
                if selected_menu == "Inventory Alkes":
                    inputs["Nama Alat"] = st.text_input("Nama Alat")
                    inputs["Merk"] = st.text_input("Merk")
                    inputs["Type"] = st.text_input("Type")
                    inputs["Nomor Seri"] = st.text_input("Nomor Seri")
                    inputs["Tahun Pengadaan"] = st.text_input("Tahun Pengadaan")
                    inputs["Harga Perolehan"] = st.number_input("Harga Perolehan (Rp)", min_value=0.0, step=1000.0)
                    inputs["Ruangan"] = st.text_input("Ruangan")

            submit_button = st.form_submit_button(label="➕ Kirim & Simpan Laporan")
            if submit_button:
                if uploaded_photo is not None:
                    bytes_data = uploaded_photo.read()
                    encoded_img = base64.b64encode(bytes_data).decode('utf-8')
                    inputs["Foto"] = encoded_img
                else:
                    inputs["Foto"] = ""

                # Auto-fill dari database inventory jika nomor seri cocok
                if selected_menu in ["Perbaikan", "Pemeliharaan"]:
                    peta_inv = dapatkan_peta_inventory()
                    ns_key = str(inputs.get("Nomor Seri", "")).strip().lower()
                    if ns_key in peta_inv:
                        if not inputs.get("Nama Alat"): inputs["Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                        if not inputs.get("Merk"): inputs["Merk"] = peta_inv[ns_key]["Merk"]
                        if not inputs.get("Ruangan"): inputs["Ruangan"] =
