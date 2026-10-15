import streamlit as st
import pandas as pd
import json
import os
import copy
import io
import qrcode  # Menghasilkan QR code alat
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
    "Perbaikan": ["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Note"],
    "Pemeliharaan": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"],
    "Stok Suku Cadang": ["Nama Suku Cadang", "Spesifikasi", "Jumlah Stok", "Satuan", "In", "Out", "Keterangan"],
    "Perencanaan RAB (Usulan)": ["Sub Kegiatan", "Nama Kegiatan", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Keterangan"],
    "Surat Masuk (Nota Dinas)": ["Tanggal Terima Surat", "Tanggal Surat", "Nomor Surat", "Perihal", "Asal Surat", "Keterangan"],
    "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"],
    "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Kalibrasi Ulang"]
}

# --- 2. FUNGSI DATABASE (LOAD, FIX & SAVE) ---
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
        
    if "Kalibrasi" in loaded_db:
        for item in loaded_db["Kalibrasi"]:
            if "Note" in item and "Kalibrasi Ulang" not in item:
                item["Kalibrasi Ulang"] = item.pop("Note")

    if loaded_db["Inventory Alkes"]:
        target_cols = KOLOM_DEFAULT["Inventory Alkes"]
        fixed_inventory = []
        for item in loaded_db["Inventory Alkes"]:
            new_item = {}
            for col in target_cols:
                new_item[col] = item.get(col, "")
            fixed_inventory.append(new_item)
        loaded_db["Inventory Alkes"] = fixed_inventory
        
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

# --- 4. FUNGSI MAPPER DATA INVENTORY ---
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

# --- 5. LOGIKA ANGGARAN RAB ---
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

# --- 7. SIDEBAR & URUTAN MENU ---
st.sidebar.header("↩️ KONTROL DATA")
if st.session_state["undo_history"]:
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

menu_utama = [
    "Inventory Alkes", "Perbaikan", "Pemeliharaan", "Stok Suku Cadang",
    "Perencanaan RAB (Usulan)", "Surat Masuk (Nota Dinas)", "Rekap SR Vendor", 
    "Kalibrasi", "Lihat Semua Data & Ringkasan"
]
menu_sop_tunggal = ["Manajemen SOP Alkes"]

selected_menu = st.sidebar.radio("Navigasi Menu", menu_utama + menu_sop_tunggal, label_visibility="collapsed")

# --- 8. LOGIKA HALAMAN UTAMA ---
if selected_menu == "Lihat Semua Data & Ringkasan":
    st.header("📋 Ringkasan Analisis Data W-SIGNAL")
    
    # Hitung rincian kondisi inventory
    inv_list_data = data.get('Inventory Alkes', [])
    total_inv_count = len(inv_list_data)
    baik_count = sum(1 for item in inv_list_data if str(item.get("Kondisi Baik", "")).strip() in ["✓", "1", "True", "true"])
    kb_count = sum(1 for item in inv_list_data if str(item.get("Kondisi KB", "")).strip() in ["✓", "1", "True", "true"])
    rb_count = sum(1 for item in inv_list_data if str(item.get("Kondisi RB", "")).strip() in ["✓", "1", "True", "true"])
    
    inv_subtitle = f"Baik: {baik_count} | KB: {kb_count} | RB: {rb_count}"

    # Metrik Baris Pertama (3 Kotak)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Inventory", f"{total_inv_count} Unit", help=inv_subtitle)
    col2.metric("Total Pemeliharaan", f"{len(data.get('Pemeliharaan', []))} Kegiatan")
    col3.metric("Total Kalibrasi", f"{len(data.get('Kalibrasi', []))} Data")
    
    # Metrik Baris Kedua (3 Kotak)
    col4, col5, col6 = st.columns(3)
    col4.metric("Total Perbaikan", f"{len(data.get('Perbaikan', []))} Laporan")
    col5.metric("Total Surat Masuk", f"{len(data.get('Surat Masuk (Nota Dinas)', []))} Surat")
    col6.metric("Total Usulan", f"{len(data.get('Perencanaan RAB (Usulan)', []))} Usulan")
    
    st.markdown(f"<p style='text-align: center; color: gray; font-size: 14px;'>Rincian Kondisi Alat -> {inv_subtitle}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📂 Tinjauan Seluruh Data Log")
    tabs = st.tabs(list(KOLOM_DEFAULT.keys()))
    
    # Tab 1: Inventory Alkes dengan Data Bridging
    with tabs[0]:
        inv_data = data.get("Inventory Alkes", [])
        df_inv = pd.DataFrame(inv_data)
        if not df_inv.empty:
            freq_perbaikan = hitung_frekuensi_kerusakan()
            set_kalibrasi = dapatkan_set_terkalibrasi()
            set_pemeliharaan = dapatkan_set_terpelihara()
            
            jumlah_perbaikan_col = []
            status_kalibrasi_col = []
            status_pemeliharaan_col = []
            
            for idx, row in df_inv.iterrows():
                ns = str(row.get("Nomor Seri", "")).strip().lower()
                jumlah_perbaikan_col.append(freq_perbaikan.get(ns, 0))
                status_kalibrasi_col.append("Sudah Dikalibrasi" if ns in set_kalibrasi else "Belum Dikalibrasi")
                status_pemeliharaan_col.append("Sudah Dipelihara" if ns in set_pemeliharaan else "Belum Dipelihara")
                
            df_inv["Jumlah Perbaikan"] = jumlah_perbaikan_col
            df_inv["Status Kalibrasi"] = status_kalibrasi_col
            df_inv["Status Pemeliharaan"] = status_pemeliharaan_col
            
        st.dataframe(df_inv, use_container_width=True)

    # Tab Lainnya
    for i, key in enumerate(list(KOLOM_DEFAULT.keys())[1:], start=1):
        with tabs[i]:
            df_tab = pd.DataFrame(data[key])
            st.dataframe(df_tab, use_container_width=True)

elif selected_menu == "Manajemen SOP Alkes":
    st.header("📚 Pusat Dokumen SOP Alkes")
    kategori_sop = ["SOP Instalasi", "SOP Perbaikan", "SOP Pemeliharaan", "SOP Kalibrasi", "SOP Penghapusan", "SOP Recall"]
    selected_sop_tab = st.selectbox("Pilih Kategori Jenis SOP:", kategori_sop)
    
    st.markdown(f"### 🔍 Kategori Aktif: {selected_sop_tab}")
    daftar_alat = dapatkan_daftar_nama_alat_inventory()
    
    if not daftar_alat:
        st.warning("⚠️ Belum ada nama alat di dalam 'Inventory Alkes'. Sila isi data inventory terlebih dahulu.")
    else:
        pilih_nama_alat = st.selectbox("Pilih Nama Alat:", daftar_alat, key=f"select_alat_{selected_sop_tab}")
        sop_storage_key = f"{selected_sop_tab}_{pilih_nama_alat}"
        
        st.markdown("---")
        col_up, col_down = st.columns(2)
        with col_up:
            st.markdown(f"#### 📤 Upload File {selected_sop_tab}")
            file_sop = st.file_uploader(f"Upload dokumen (.pdf, .docx, .xlsx) untuk {pilih_nama_alat}", type=["pdf", "docx", "xlsx", "txt"], key=f"file_{sop_storage_key}")
            if file_sop is not None:
                if st.button("💾 Simpan Dokumen", use_container_width=True, key=f"save_{sop_storage_key}"):
                    file_bytes = file_sop.read()
                    import base64
                    encoded_file = base64.b64encode(file_bytes).decode('utf-8')
                    st.session_state["w_signal_db"]["SOP_Files"][sop_storage_key] = {
                        "filename": file_sop.name,
                        "base64_data": encoded_file,
                        "kategori": selected_sop_tab,
                        "nama_alat": pilih_nama_alat
                    }
                    save_data(st.session_state["w_signal_db"])
                    st.success(f"Berhasil mengunggah {selected_sop_tab} untuk {pilih_nama_alat}!")
                    st.rerun()
                    
        with col_down:
            st.markdown(f"#### 📥 Download Dokumen Aktif")
            saved_sop_dict = data.get("SOP_Files", {})
            if sop_storage_key in saved_sop_dict:
                file_info = saved_sop_dict[sop_storage_key]
                import base64
                decoded_bytes = base64.b64decode(file_info["base64_data"])
                st.info(f"📄 File tersimpan: **{file_info['filename']}**")
                st.download_button(
                    label=f"📥 Download {selected_sop_tab} - {pilih_nama_alat}",
                    data=decoded_bytes,
                    file_name=file_info["filename"],
                    use_container_width=True,
                    key=f"dl_{sop_storage_key}"
                )
            else:
                st.warning(f"⚠️ Belum ada file {selected_sop_tab} yang diupload untuk alat ini.")

else:
    # --- MENAMPILKAN MENU LOG DATA BIASA ---
    st.header(f"📋 Menu: {selected_menu}")
    
    # 1. FORM INPUT MANUAL
    st.markdown("### 📥 Tambah Data Baru")
    with st.form(key=f"form_{selected_menu.lower().replace(' ', '_')}", clear_on_submit=True):
        inputs = {}
        if selected_menu == "Inventory Alkes":
            col1, col2, col3 = st.columns(3)
            inputs["Nama Alat"] = col1.text_input("Nama Alat")
            inputs["Merk"] = col2.text_input("Merk")
            inputs["Type"] = col3.text_input("Type")
            
            col4, col5, col6 = st.columns(3)
            inputs["Nomor Seri"] = col4.text_input("Nomor Seri")
            inputs["Tahun Pengadaan"] = col5.text_input("Tahun Pengadaan")
            inputs["Harga Perolehan"] = col6.number_input("Harga Perolehan (Rp)", min_value=0.0, step=1000.0)
            
            col7, col8 = st.columns(2)
            inputs["Ruangan"] = col7.text_input("Ruangan")
            
            st.markdown("**Status Kondisi Alat:**")
            cond_col1, cond_col2, cond_col3 = st.columns(3)
            pilih_kondisi = cond_col1.radio("Pilih Kondisi:", ["Baik", "KB (Kurang Baik)", "RB (Rusak Berat)"], index=0)
            
            inputs["Kondisi Baik"] = "✓" if pilih_kondisi == "Baik" else ""
            inputs["Kondisi KB"] = "✓" if pilih_kondisi == "KB (Kurang Baik)" else ""
            inputs["Kondisi RB"] = "✓" if pilih_kondisi == "RB (Rusak Berat)" else ""
            
        elif selected_menu == "Perbaikan":
            inputs["Tanggal Perbaikan"] = st.date_input("Tanggal Perbaikan").strftime('%Y-%m-%d')
            inputs["Nomor Seri"] = st.text_input("Nomor Seri")
            inputs["Kerusakan"] = st.text_area("Kerusakan")
            inputs["Tindakan"] = st.text_area("Tindakan")
            inputs["Keterangan"] = st.text_input("Keterangan")
            inputs["Note"] = ""
            
        elif selected_menu == "Pemeliharaan":
            inputs["Nomor Seri"] = st.text_input("Nomor Seri")
            inputs["Tanggal Pemeliharaan"] = st.date_input("Tanggal Pemeliharaan").strftime('%Y-%m-%d')
            inputs["Keterangan"] = st.text_area("Keterangan")
            inputs["Note"] = ""
            
        elif selected_menu == "Stok Suku Cadang":
            inputs["Nama Suku Cadang"] = st.text_input("Nama Suku Cadang")
            inputs["Spesifikasi"] = st.text_input("Spesifikasi")
            col1, col2 = st.columns(2)
            inputs["Jumlah Stok"] = col1.number_input("Jumlah Stok", min_value=0, step=1)
            inputs["Satuan"] = col2.text_input("Satuan")
            inputs["In"] = st.number_input("In", min_value=0, step=1)
            inputs["Out"] = st.number_input("Out", min_value=0, step=1)
            inputs["Keterangan"] = st.text_input("Keterangan")
            
        elif selected_menu == "Perencanaan RAB (Usulan)":
            inputs["Sub Kegiatan"] = st.text_input("Sub Kegiatan")
            inputs["Nama Kegiatan"] = st.text_input("Nama Kegiatan")
            inputs["Pagu Sub Kegiatan"] = st.number_input("Pagu Sub Kegiatan", min_value=0.0)
            inputs["Nilai SPH"] = st.number_input("Nilai SPH", min_value=0.0)
            inputs["Nilai Kontrak"] = st.number_input("Nilai Kontrak", min_value=0.0)
            inputs["Keterangan"] = st.text_input("Keterangan")
            
        elif selected_menu == "Surat Masuk (Nota Dinas)":
            inputs["Tanggal Terima Surat"] = st.date_input("Tanggal Terima Surat").strftime('%Y-%m-%d')
            inputs["Tanggal Surat"] = st.date_input("Tanggal Surat").strftime('%Y-%m-%d')
            inputs["Nomor Surat"] = st.text_input("Nomor Surat")
            inputs["Perihal"] = st.text_input("Perihal")
            inputs["Asal Surat"] = st.text_input("Asal Surat")
            inputs["Keterangan"] = st.text_input("Keterangan")
            
        elif selected_menu == "Rekap SR Vendor":
            inputs["Tanggal"] = st.date_input("Tanggal").strftime('%Y-%m-%d')
            inputs["Penyedia"] = st.text_input("Penyedia / Vendor")
            inputs["Data Alat"] = st.text_input("Data Alat")
            inputs["Kegiatan"] = st.text_input("Kegiatan")
            inputs["Analisa"] = st.text_area("Analisa")
            inputs["Keterangan"] = st.text_input("Keterangan")
            
        elif selected_menu == "Kalibrasi":
            inputs["Tanggal Kalibrasi"] = st.date_input("Tanggal Kalibrasi").strftime('%Y-%m-%d')
            inputs["Nomor Seri"] = st.text_input("Nomor Seri")
            inputs["Keterangan"] = st.text_input("Keterangan")
            inputs["Kalibrasi Ulang"] = st.date_input("Kalibrasi Ulang").strftime('%Y-%m-%d')

        submit_button = st.form_submit_button(label="➕ Tambah Data Manual")
        if submit_button:
            st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
            if selected_menu in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                peta_inv = dapatkan_peta_inventory()
                ns_key = str(inputs.get("Nomor Seri", "")).strip().lower()
                if ns_key in peta_inv:
                    inputs["Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                    inputs["Merk"] = peta_inv[ns_key]["Merk"]
                    inputs["Type"] = peta_inv[ns_key]["Type"]
                    inputs["Ruangan"] = peta_inv[ns_key]["Ruangan"]

            st.session_state["w_signal_db"][selected_menu].append(inputs)
            if selected_menu == "Perencanaan RAB (Usulan)":
                st.session_state["w_signal_db"][selected_menu] = recalculate_rab(st.session_state["w_signal_db"][selected_menu])
            save_data(st.session_state["w_signal_db"])
            st.success(f"Data manual berhasil ditambahkan!")
            st.rerun()

    # 2. FITUR MASS UPLOAD & TOMBOL DOWNLOAD TEMPLATE
    with st.expander(f"📂 Mass Upload & Download Template ({selected_menu})"):
        st.markdown(f"**Format Judul Kolom Wajib pada File Excel Anda:**")
        st.code(", ".join(KOLOM_DEFAULT[selected_menu]))
        
        df_template_kosong = pd.DataFrame(columns=KOLOM_DEFAULT[selected_menu])
        template_excel_bytes = convert_df_to_excel(df_template_kosong)
        st.download_button(
            label=f"📥 Download Template Kosong Excel ({selected_menu})",
            data=template_excel_bytes,
            file_name=f"Template_{selected_menu.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.markdown("---")
        uploaded_file = st.file_uploader(f"Pilih file Excel (.xlsx) atau CSV (.csv) untuk {selected_menu}", type=["xlsx", "csv"], key=f"file_uploader_{selected_menu.lower().replace(' ', '_')}")
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                df_upload.columns = df_upload.columns.str.strip()
                
                kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat", "Kalibrasi Ulang"]
                for col in kolom_tanggal_sistem:
                    if col in df_upload.columns:
                        df_upload[col] = df_upload[col].apply(bersihkan_format_tanggal)
                
                st.dataframe(df_upload.head(3), use_container_width=True)
                
                if st.button("🚀 Konfirmasi & Masukkan Data Massal", key=f"btn_upload_{selected_menu.lower().replace(' ', '_')}", use_container_width=True):
                    st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
                    
                    kolom_req = KOLOM_DEFAULT[selected_menu]
                    df_processed = pd.DataFrame(columns=kolom_req)
                    for col in kolom_req:
                        if col in df_upload.columns:
                            df_processed[col] = df_upload[col]
                        else:
                            df_processed[col] = 0 if col in ["Jumlah Stok", "In", "Out", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan", "Harga Perolehan"] else ""
                    
                    df_processed = df_processed.fillna("")
                    
                    if selected_menu in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                        peta_inv = dapatkan_peta_inventory()
                        for idx, row in df_processed.iterrows():
                            ns_key = str(row.get("Nomor Seri", "")).strip().lower()
                            if ns_key in peta_inv:
                                df_processed.at[idx, "Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                                df_processed.at[idx, "Merk"] = peta_inv[ns_key]["Merk"]
                                df_processed.at[idx, "Type"] = peta_inv[ns_key]["Type"]
                                if "Ruangan" in df_processed.columns:
                                    df_processed.at[idx, "Ruangan"] = peta_inv[ns_key]["Ruangan"]
                    
                    for col in kolom_tanggal_sistem:
                        if col in df_processed.columns:
                            df_processed[col] = df_processed[col].apply(bersihkan_format_tanggal)
                    
                    uploaded_dict = df_processed.to_dict(orient="records")
                    st.session_state["w_signal_db"][selected_menu].extend(uploaded_dict)
                    
                    if selected_menu == "Perencanaan RAB (Usulan)":
                        st.session_state["w_signal_db"][selected_menu] = recalculate_rab(st.session_state["w_signal_db"][selected_menu])
                        
                    save_data(st.session_state["w_signal_db"])
                    st.success(f"Berhasil mengimpor {len(df_processed)} data baru ke dalam {selected_menu}!")
                    st.rerun()
            except Exception as e:
                st.error(f"Gagal memproses file. Silakan periksa format kolom Anda. Error: {e}")

    # 3. FITUR FORMAT / KOSONGKAN DATA DENGAN PASSWORD
    with st.expander(f"⚠️ Zona Bahaya: Format / Kosongkan Data {selected_menu}"):
        st.warning(f"Tindakan ini akan menghapus SELURUH isi data pada menu **{selected_menu}** saja, tanpa menghapus data pada menu lain.")
        confirm_check = st.checkbox(f"Saya yakin ingin mengosongkan seluruh data {selected_menu}", key=f"chk_reset_{selected_menu.lower().replace(' ', '_')}")
        
        input_password = st.text_input("Masukkan Password Keamanan:", type="password", key=f"pwd_reset_{selected_menu.lower().replace(' ', '_')}")
        
        if confirm_check:
            if st.button(f"🗑️ Kosongkan Data {selected_menu} Sekarang", type="primary", key=f"btn_reset_{selected_menu.lower().replace(' ', '_')}"):
                if input_password == "NAY123":
                    st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
                    st.session_state["w_signal_db"][selected_menu] = []
                    save_data(st.session_state["w_signal_db"])
                    st.success(f"Data pada menu **{selected_menu}** berhasil dikosongkan!")
                    st.rerun()
                else:
                    st.error("❌ Password salah! Penghapusan dibatalkan.")

    st.markdown("---")
    
    # 4. LIVE EDITOR UTAMA & DOWNLOAD FILE EXCEL REKAP
    st.markdown("### 📝 Live-Editor & Tabel Data")
    menu_data = data.get(selected_menu, [])
    df_menu = pd.DataFrame(menu_data)
    
    if selected_menu in KOLOM_DEFAULT:
        for col in KOLOM_DEFAULT[selected_menu]:
            if col not in df_menu.columns:
                df_menu[col] = ""
        df_menu = df_menu[KOLOM_DEFAULT[selected_menu]]

    editor_key = f"editor_{selected_menu.lower().replace(' ', '_')}"
    
    edited_df = st.data_editor(
        df_menu,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        on_change=handle_editor_change,
        args=(selected_menu, editor_key)
    )
    
    if not df_menu.empty:
        excel_bytes = convert_df_to_excel(df_menu)
        st.download_button(
            label=f"📥 Download Seluruh Data {selected_menu} (.xlsx)",
            data=excel_bytes,
            file_name=f"Data_{selected_menu.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    if selected_menu == "Inventory Alkes" and not df_menu.empty:
        st.markdown("---")
        st.markdown("### 🖨️ Generator QR Code Alat")
        pilih_alat = st.selectbox("Pilih No Seri Alat untuk dibuatkan QR:", df_menu["Nomor Seri"].unique() if "Nomor Seri" in df_menu.columns else [])
        if pilih_alat:
            row_alat = df_menu[df_menu["Nomor Seri"] == pilih_alat].iloc[0]
            nama_alkes = row_alat.get("Nama Alat", "Alat")
            qr_img = generate_qr_code(pilih_alat, nama_alkes)
            st.image(qr_img, caption=f"QR Code - {nama_alkes} ({pilih_alat})", width=200)
            st.download_button(label="📥 Download Gambar QR Code", data=qr_img, file_name=f"QR_{pilih_alat}.png", mime="image/png")

# --- FITUR PENCARIAN BARCODE SIDEBAR ---
if search_ns:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Hasil Pencarian Alat:")
    peta = dapatkan_peta_inventory()
    ns_clean = search_ns.strip().lower()
    if ns_clean in peta:
        info = peta[ns_clean]
        st.sidebar.success(f"**Alat Ditemukan!**\n\n* **Nama:** {info['Nama Alat']}\n* **Merk:** {info['Merk']}\n* **Type:** {info['Type']}\n* **Ruangan:** {info['Ruangan']}")
        freq = hitung_frekuensi_kerusakan().get(ns_clean, 0)
        if freq > 3:
            st.sidebar.error(f"⚠️ **Peringatan Kerusakan:** Alat ini sudah rusak sebanyak **{freq} kali**!")
        else:
            st.sidebar.info(f"Riwayat Perbaikan: {freq} kali.")
    else:
        st.sidebar.warning("Nomor Seri belum terdaftar di Inventory Alkes.")
