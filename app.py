import streamlit as st
import pandas as pd
import json
import os
import copy
import io
import qrcode  # Pastikan sudah pip install qrcode pillow
from datetime import datetime, date

def generate_qr_code(no_seri, nama_alat):
    # 1. Tentukan URL dasar aplikasi Anda (Ganti setelah Anda deploy ke Streamlit Cloud)
    # Saat masih di komputer local, bisa gunakan localhost
    base_url = "http://localhost:8501" 
    # Jika nanti sudah deploy, ganti menjadi misalnya: "https://w-signal.streamlit.app"
    
    # 2. Gabungkan URL dengan parameter Nomor Seri alat
    qr_data = f"{base_url}/?no_seri={no_seri}"
    
    # 3. Proses pembuatan gambar QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 4. Konversi gambar ke format Bytes agar bisa didownload di Streamlit
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    return byte_im

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="W-SIGNAL", layout="wide")
st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "database_w_signal.json")

# --- 2. FUNGSI DATABASE (LOAD & SAVE) ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                return json.load(f)
        except Exception as e:
            st.error(f"Gagal membaca database lama. Error: {e}")
    return {
        "Inventory Alkes": [], "Perbaikan": [], "Pemeliharaan": [], 
        "Stok Suku Cadang": [], "Perencanaan RAB (Usulan)": [], 
        "Surat Masuk (Nota Dinas)": [], "Rekap SR Vendor": [], "Kalibrasi": []
    }

def save_data(data_to_save):
    try:
        with open(DB_FILE, "w") as f: 
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        st.error(f"Gagal mengamankan data ke file: {e}")

# --- 3. INISIALISASI SESSION STATE ---
if "w_signal_db" not in st.session_state:
    raw_data = load_data()
    keys_default = ["Inventory Alkes", "Perbaikan", "Pemeliharaan", "Stok Suku Cadang", 
                    "Perencanaan RAB (Usulan)", "Surat Masuk (Nota Dinas)", "Rekap SR Vendor", "Kalibrasi"]
    for k in keys_default:
        if k not in raw_data:
            raw_data[k] = []
    st.session_state["w_signal_db"] = raw_data

if "undo_history" not in st.session_state:
    st.session_state["undo_history"] = []

# FITUR BARU: Menangkap lemparan Nomor Seri dari hasil Scan QR HP melalui URL Parameter
query_params = st.query_params
url_no_seri = query_params.get("no_seri", "").strip()

data = st.session_state["w_signal_db"]

# --- 4. FUNGSI MAPPER MASTER DATA INVENTORY ---
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

def hitung_frekuensi_kerusakan():
    perbaikan_list = data.get("Perbaikan", [])
    counter = {}
    for item in perbaikan_list:
        ns = str(item.get("Nomor Seri", "")).strip().lower()
        if ns:
            counter[ns] = counter.get(ns, 0) + 1
    return counter

# --- 5. LOGIKA ANGGARAN RUNNING TOTAL RAB ---
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

# --- FUNGSI HELPER: MEMBERSIHKAN FORMAT TANGGAL DARI JAM ---
def bersihkan_format_tanggal(val):
    if pd.isna(val) or val == "":
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')
    val_str = str(val).strip()
    if " " in val_str:
        val_str = val_str.split(" ")[0]
    return val_str

# --- 6. AUTOMATION EDITOR (AUTO-SAVE & RELASI DATA) ---
def handle_editor_change(menu_key, editor_key):
    if editor_key in st.session_state:
        raw_editor_data = st.session_state[editor_key]
        
        if raw_editor_data.get("edited_rows") or raw_editor_data.get("added_rows") or raw_editor_data.get("deleted_rows"):
            st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
            df_current = pd.DataFrame(data[menu_key])
            
            kolom_default = {
                "Perbaikan": ["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Note"],
                "Pemeliharaan": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"],
                "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Note"],
                "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"],
                "Inventory Alkes": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tahun Pengadaan"],
                "Stok Suku Cadang": ["Nama Suku Cadang", "Spesifikasi", "Jumlah Stok", "Satuan", "In", "Out", "Keterangan"]
            }
            
            if menu_key in kolom_default:
                for col in kolom_default[menu_key]:
                    if col not in df_current.columns:
                        df_current[col] = 0 if col in ["Jumlah Stok", "In", "Out"] else ""
            
            for row_idx, changes in raw_editor_data.get("edited_rows", {}).items():
                for col, val in changes.items():
                    if col in df_current.columns: 
                        df_current.iat[row_idx, df_current.columns.get_loc(col)] = val
                        
            for new_row in raw_editor_data.get("added_rows", []):
                df_current = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)
                
            deleted_indices = raw_editor_data.get("deleted_rows", [])
            if deleted_indices: 
                df_current = df_current.drop(deleted_indices).reset_index(drop=True)
                
            if menu_key in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                peta_inv = dapatkan_peta_inventory()
                for idx, row in df_current.iterrows():
                    ns_key = str(row.get("Nomor Seri", "")).strip().lower()
                    current_note = str(row.get("Note", "")).strip()
                    
                    if ns_key in peta_inv:
                        df_current.at[idx, "Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                        df_current.at[idx, "Merk"] = peta_inv[ns_key]["Merk"]
                        df_current.at[idx, "Type"] = peta_inv[ns_key]["Type"]
                        if "Ruangan" in df_current.columns:
                            df_current.at[idx, "Ruangan"] = peta_inv[ns_key]["Ruangan"]
                        
                        if current_note == "⚠️ BELUM DIINVENTORY":
                            df_current.at[idx, "Note"] = ""
                            
                    elif ns_key != "":
                        if not current_note or current_note == "None":
                            df_current.at[idx, "Note"] = "⚠️ BELUM DIINVENTORY"

            kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
            for col in kolom_tanggal_sistem:
                if col in df_current.columns:
                    df_current[col] = df_current[col].apply(bersihkan_format_tanggal)

            temp_dict = df_current.fillna("").to_dict(orient="records")
            if menu_key == "Perencanaan RAB (Usulan)": 
                temp_dict = recalculate_rab(temp_dict)
            
            st.session_state["w_signal_db"][menu_key] = temp_dict
            save_data(st.session_state["w_signal_db"])

# --- 7. EXCEL EXPORTER ---
def convert_df_to_excel(df_to_download):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_to_download.to_excel(writer, index=False, sheet_name='Data Rekap')
    return output.getvalue()

# --- 8. SIDEBAR CONTROLS & NAVIGASI ---
st.sidebar.header("↩️ KONTROL DATA")
if st.session_state["undo_history"]:
    if st.sidebar.button("↩️ Undo Perubahan Terakhir", use_container_width=True):
        st.session_state["w_signal_db"] = st.session_state["undo_history"].pop()
        save_data(st.session_state["w_signal_db"])
        st.rerun()
else:
    st.sidebar.button("↩️ Undo (Tidak ada riwayat)", disabled=True, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("🔐 VALIDASI QR INPUT")
qr_gate_input = st.sidebar.text_input("Scan QR Code Petugas / Admin:", type="password", key="app_qr_gate").strip()

KODE_QR_VALID = "ADMIN-W-SIGNAL"
akses_terbuka = False

if qr_gate_input == KODE_QR_VALID:
    st.sidebar.success("🔓 AKSES TERBUKA! Form dapat diisi.")
    akses_terbuka = True
elif qr_gate_input != "":
    st.sidebar.error("❌ QR CODE TIDAK DIKENAL")

st.sidebar.markdown("---")
st.sidebar.header("🔍 SCAN / CARI ALAT")

# Menentukan nilai default kolom pencarian sidebar (jika mendeteksi QR Scan dari luar/URL)
default_search_value = url_no_seri if url_no_seri else ""
barcode_input = st.sidebar.text_input("Arahkan kursor & Scan Barcode / Input No Seri:", value=default_search_value, key="sidebar_barcode").strip().lower()

if barcode_input:
    peta_inv = dapatkan_peta_inventory()
    map_rusak = hitung_frekuensi_kerusakan()
    
    if barcode_input in peta_inv:
        alat_info = peta_inv[barcode_input]
        st.sidebar.success("✅ Data Alat Ditemukan!")
        
        with st.sidebar.expander("📊 Detail Informasi Alat", expanded=True):
            st.markdown(f"**Nama Alat:** {alat_info['Nama Alat']}")
            st.markdown(f"**Merk:** {alat_info['Merk']}")
            st.markdown(f"**Type:** {alat_info['Type']}")
            st.markdown(f"**Ruangan:** {alat_info['Ruangan']}")
            st.markdown(f"**Tahun Pengadaan:** {alat_info['Tahun Pengadaan']}")
            
            total_rusak = map_rusak.get(barcode_input, 0)
            st.markdown(f"**Total Riwayat Perbaikan:** `{total_rusak}x`")
    else:
        st.sidebar.error("❌ Nomor Seri tidak terdaftar di Inventory.")

st.sidebar.markdown("---")
menu = st.sidebar.radio("Pilih Menu:", [
    "📋 Inventory Alkes", "🔧 Perbaikan", "📆 Pemeliharaan", "⚙️ Stok Suku Cadang", 
    "💰 Perencanaan RAB (Usulan)", "📝 Surat Masuk (Nota Dinas)", "🏢 Rekap SR Vendor", "🎯 Kalibrasi", "📊 Lihat Semua Data & Ringkasan"
])

# --- 9. RENDERING ENGINE ---
def render_page(menu_key, form_fields=None):
    st.header(f"{menu}")
    peta_inv = dapatkan_peta_inventory()
    map_rusak = hitung_frekuensi_kerusakan()
    
    if form_fields:
        with st.form(f"form_{menu_key}", clear_on_submit=False): # Diubah ke False agar form tidak langsung hilang saat tombol download QR ditekan
            inputs = {}
            cols = st.columns(len(form_fields))
            for idx, (field_name, field_type) in enumerate(form_fields.items()):
                with cols[idx % len(cols)]:
                    if field_type == "int": inputs[field_name] = st.number_input(field_name, min_value=0, step=1, disabled=not akses_terbuka)
                    elif field_type == "text_area": inputs[field_name] = st.text_area(field_name, disabled=not akses_terbuka)
                    elif field_type == "date": inputs[field_name] = str(st.date_input(field_name, disabled=not akses_terbuka))
                    elif field_type == "readonly": st.text_input(field_name, value="Otomatis Sistem", disabled=True)
                    else: inputs[field_name] = st.text_input(field_name, disabled=not akses_terbuka)
                    
            submit_button = st.form_submit_button("Tambah Data", disabled=not akses_terbuka)
            
            if not akses_terbuka:
                st.warning("⚠️ FORM INPUT TERKUNCI! Silakan scan QR Code Petugas/Admin di sidebar kiri terlebih dahulu untuk menambahkan data baru.")
            
            if submit_button and akses_terbuka:
                st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
                
                ns_input = str(inputs.get("Nomor Seri", "")).strip().lower()
                if menu_key in ["Perbaikan", "Pemeliharaan", "Kalibrasi"] and ns_input in peta_inv:
                    inputs["Nama Alat"] = peta_inv[ns_input]["Nama Alat"]
                    inputs["Merk"] = peta_inv[ns_input]["Merk"]
                    inputs["Type"] = peta_inv[ns_input]["Type"]
                    inputs["Note"] = ""
                    if "Ruangan" in form_fields: inputs["Ruangan"] = peta_inv[ns_input]["Ruangan"]
                elif menu_key in ["Perbaikan", "Pemeliharaan", "Kalibrasi"] and ns_input != "":
                    inputs["Nama Alat"] = ""
                    inputs["Merk"] = ""
                    inputs["Type"] = ""
                    inputs["Note"] = "⚠️ BELUM DIINVENTORY"
                    if "Ruangan" in form_fields: inputs["Ruangan"] = ""
                        
                data[menu_key].append(inputs)
                save_data(data)
                st.success(f"Berhasil menambahkan data baru ke {menu_key}!")
                
                # INTEGRASI GEN-QR OTOMATIS: Jika yang ditambah adalah Alat Baru di Inventory, buatkan QR Code-nya
                if menu_key == "Inventory Alkes" and ns_input:
                    nama_alkes = inputs.get("Nama Alat", "Alat")
                    qr_img_bytes = generate_qr_code(inputs.get("Nomor Seri", ""), nama_alkes)
                    
                    st.write("---")
                    st.subheader("🖨️ STIKER QR CODE GENERATOR")
                    st.image(qr_img_bytes, caption=f"QR Code - {nama_alkes} ({inputs.get('Nomor Seri', '')})", width=180)
                    st.download_button(
                        label="📥 Unduh QR Code (Stiker Alkes)",
                        data=qr_img_bytes,
                        file_name=f"QR_{inputs.get('Nomor Seri', '')}.png",
                        mime="image/png"
                    )

    # --- FITUR UPLOAD FILE EXCEL/CSV MASSAL ---
    st.markdown("---")
    with st.expander(f"📥 Mass Upload File Excel / CSV ({menu_key})"):
        st.info("Pastikan nama kolom pada file Excel/CSV sama dengan nama kolom di tabel sistem.")
        uploaded_file = st.file_uploader("Pilih file (.xlsx atau .csv)", type=["xlsx", "csv"], key=f"uploader_{menu_key}")
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    df_uploaded = pd.read_excel(uploaded_file)
                
                df_uploaded = df_uploaded.fillna("")
                
                kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
                for col in kolom_tanggal_sistem:
                    if col in df_uploaded.columns:
                        df_uploaded[col] = df_uploaded[col].apply(bersihkan_format_tanggal)
                
                st.write("🔍 **Preview Data yang diunggah:**")
                st.dataframe(df_uploaded.head(5), use_container_width=True)
                
                if st.button("🚀 Konfirmasi & Masukkan Data", key=f"btn_confirm_{menu_key}"):
                    st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
                    uploaded_records = df_uploaded.to_dict(orient="records")
                    
                    if menu_key in ["Perbaikan", "Pemeliharaan", "Kalibrasi"]:
                        for row in uploaded_records:
                            ns_key = str(row.get("Nomor Seri", "")).strip().lower()
                            if ns_key in peta_inv:
                                row["Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                                row["Merk"] = peta_inv[ns_key]["Merk"]
                                row["Type"] = peta_inv[ns_key]["Type"]
                                row["Ruangan"] = peta_inv[ns_key]["Ruangan"]
                                row["Note"] = ""
                            elif ns_key != "":
                                row["Note"] = "⚠️ BELUM DIINVENTORY"
                    
                    data[menu_key].extend(uploaded_records)
                    if menu_key == "Perencanaan RAB (Usulan)":
                        data[menu_key] = recalculate_rab(data[menu_key])
                        
                    save_data(data)
                    st.success(f"Berhasil mengimpor {len(uploaded_records)} data baru ke {menu_key}!")
                    st.rerun()
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")
    st.markdown("---")

    st.subheader(f"📝 Live-Editor & Tabel Data {menu_key}")
    df_current = pd.DataFrame(data[menu_key])
    
    kolom_wajib_render = {
        "Perbaikan": ["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Note"],
        "Pemeliharaan": ["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"],
        "Kalibrasi": ["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Note"],
        "Rekap SR Vendor": ["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"]
    }
    
    if menu_key in kolom_wajib_render:
        for col in kolom_wajib_render[menu_key]:
            if col not in df_current.columns: df_current[col] = ""

    kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
    for col in kolom_tanggal_sistem:
        if col in df_current.columns:
            df_current[col] = df_current[col].apply(bersihkan_format_tanggal)

    if not df_current.empty:
        if menu_key == "Kalibrasi":
            df_current = df_current.reindex(columns=["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Note"])
        elif menu_key == "Perbaikan":
            df_current["Total Rusak"] = df_current["Nomor Seri"].apply(lambda x: f"{map_rusak.get(str(x).strip().lower(), 0)}x" if str(x).strip() else "0x")
            df_current = df_current.reindex(columns=["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Total Rusak", "Note"])
        elif menu_key == "Pemeliharaan":
            df_current = df_current.reindex(columns=["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"])
        elif menu_key == "Rekap SR Vendor":
            df_current = df_current.reindex(columns=["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"])

        st.download_button(
            label=f"📥 Download Data {menu_key} (.xlsx)",
            data=convert_df_to_excel(df_current),
            file_name=f"rekap_{menu_key.lower().replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if "Nomor Seri" in df_current.columns:
        df_current["Nomor Seri"] = df_current["Nomor Seri"].astype(str)

    df_current.index = df_current.index + 1
    editor_key = f"editor_{menu_key.replace(' ', '_')}"
    
    disabled_cols = []
    if menu_key in ["Perbaikan", "Pemeliharaan", "Kalibrasi"]:
        disabled_cols = ["Nama Alat", "Merk", "Type", "Ruangan", "Note", "Total Rusak"]
        
    st.data_editor(
        df_current, 
        num_rows="dynamic", 
        use_container_width=True, 
        key=editor_key, 
        on_change=handle_editor_change, 
        args=(menu_key, editor_key),
        disabled=disabled_cols,
        column_config={
            "Nomor Seri": st.column_config.TextColumn(
                "Nomor Seri",
                help="Ubah Nomor Seri di sini",
                disabled=False
            )
        }
    )

# --- 10. CONTROLLER ROUTER ---
if menu == "📋 Inventory Alkes": 
    render_page("Inventory Alkes", {"Nama Alat": "text", "Merk": "text", "Type": "text", "Nomor Seri": "text", "Ruangan": "text", "Tahun Pengadaan": "text"})
elif menu == "🔧 Perbaikan": 
    render_page("Perbaikan", {"Tanggal Perbaikan": "date", "Nomor Seri": "text", "Nama Alat": "readonly", "Merk": "readonly", "Type": "readonly", "Ruangan": "readonly", "Kerusakan": "text_area", "Tindakan": "text_area", "Keterangan": "text"})
elif menu == "📆 Pemeliharaan": 
    render_page("Pemeliharaan", {"Nama Alat": "readonly", "Merk": "readonly", "Type": "readonly", "Nomor Seri": "text", "Ruangan": "readonly", "Tanggal Pemeliharaan": "date", "Keterangan": "text"})
elif menu == "⚙️ Stok Suku Cadang": 
    render_page("Stok Suku Cadang", {"Nama Suku Cadang": "text", "Spesifikasi": "text", "Jumlah Stok": "int", "Satuan": "text", "In": "int", "Out": "int", "Keterangan": "text"})
elif menu == "💰 Perencanaan RAB (Usulan)": 
    render_page("Perencanaan RAB (Usulan)", {"Sub Kegiatan": "text", "Nama Kegiatan": "text", "Pagu Sub Kegiatan": "int", "Nilai SPH": "int", "Nilai Kontrak": "int", "Keterangan": "text"})
elif menu == "📝 Surat Masuk (Nota Dinas)": 
    render_page("Surat Masuk (Nota Dinas)", {"Tanggal Terima Surat": "date", "Dari": "text", "Tanggal Surat": "date", "Hal": "text", "Keterangan": "text_area"})
elif menu == "🏢 Rekap SR Vendor": 
    render_page("Rekap SR Vendor", {"Tanggal": "date", "Penyedia": "text", "Data Alat": "text", "Kegiatan": "text", "Analisa": "text_area", "Keterangan": "text"})
elif menu == "🎯 Kalibrasi": 
    render_page("Kalibrasi", {"Tanggal Kalibrasi": "date", "Nomor Seri": "text", "Nama Alat": "readonly", "Merk": "readonly", "Type": "readonly", "Ruangan": "readonly", "Keterangan": "text"})
elif menu == "📊 Lihat Semua Data & Ringkasan":
    st.header("📊 W-SIGNAL Dashboard Analisis")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Inventory", f"{len(data.get('Inventory Alkes', []))} Unit")
    c2.metric("Total Surat Masuk", f"{len(data.get('Surat Masuk (Nota Dinas)', []))} Surat")
    c3.metric("Total Perbaikan", f"{len(data.get('Perbaikan', []))} Laporan")
    c4.metric("Total Pemeliharaan", f"{len(data.get('Pemeliharaan', []))} Kegiatan")
    
    st.write("---")
    st.subheader("🗂️ Tinjauan Seluruh Data Log")
    tabs = st.tabs(["Inventory", "Perbaikan", "Pemeliharaan", "Stok Suku Cadang", "Perencanaan RAB", "Surat Masuk", "SR Vendor", "Kalibrasi"])
    keys = ["Inventory Alkes", "Perbaikan", "Pemeliharaan", "Stok Suku Cadang", "Perencanaan RAB (Usulan)", "Surat Masuk (Nota Dinas)", "Rekap SR Vendor", "Kalibrasi"]
    filenames = ["inventory", "perbaikan", "pemeliharaan", "stok_sukucadang", "rab_usulan", "surat_masuk", "sr_vendor", "kalibrasi"]
    
    peta_inv = dapatkan_peta_inventory()
    map_rusak = hitung_frekuensi_kerusakan()
    for t, k, f in zip(tabs, keys, filenames):
        with t:
            df = pd.DataFrame(data.get(k, []))
            
            kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
            for col in kolom_tanggal_sistem:
                if col in df.columns:
                    df[col] = df[col].apply(bersihkan_format_tanggal)
                    
            if not df.empty:
                if k == "Kalibrasi":
                    df = df.reindex(columns=["Tanggal Kalibrasi", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Keterangan", "Note"])
                elif k == "Perbaikan":
                    df["Total Rusak"] = df["Nomor Seri"].apply(lambda x: f"{map_rusak.get(str(x).strip().lower(), 0)}x" if str(x).strip() else "0x")
                    df = df.reindex(columns=["Tanggal Perbaikan", "Nomor Seri", "Nama Alat", "Merk", "Type", "Ruangan", "Kerusakan", "Tindakan", "Keterangan", "Total Rusak", "Note"])
                elif k == "Pemeliharaan":
                    df = df.reindex(columns=["Nama Alat", "Merk", "Type", "Nomor Seri", "Ruangan", "Tanggal Pemeliharaan", "Keterangan", "Note"])
                elif k == "Rekap SR Vendor":
                    df = df.reindex(columns=["Tanggal", "Penyedia", "Data Alat", "Kegiatan", "Analisa", "Keterangan"])
                st.download_button(f"📥 Download Excel ({k})", convert_df_to_excel(df), f"rekap_{f}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            df.index = df.index + 1
            st.dataframe(df, use_container_width=True)