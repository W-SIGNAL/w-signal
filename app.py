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
st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

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

query_params = st.query_params
url_no_seri = query_params.get("no_seri", "").strip()
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

def hitung_frekuensi_kerusakan():
    perbaikan_list = data.get("Perbaikan", [])
    counter = {}
    for item in perbaikan_list:
        ns = str(item.get("Nomor Seri", "")).strip().lower()
        if ns: counter[ns] = counter.get(ns, 0) + 1
    return counter

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
            if menu_key == "Perencanaan RAB (Usulan)": temp_dict = recalculate_rab(temp_dict)
            st.session_state["w_signal_db"][menu_key] = temp_dict
            save_data(st.session_state["w_signal_db"])

def convert_df_to_excel(df_to_download):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_to_download.to_excel(writer, index=False, sheet_name='Data Rekap')
    return output.getvalue()

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
menu_sop = [
    "SOP Pemeliharaan Alkes", "SOP Perbaikan Alkes", "SOP Kalibrasi Alkes", 
    "SOP Penghapusan Alkes", "SOP Recall Alkes"
]

selected_menu = st.sidebar.radio("Navigasi Menu", menu_utama + menu_sop, label_visibility="collapsed")

if selected_menu == "Lihat Semua Data & Ringkasan":
    st.header("📋 Ringkasan Analisis Data W-SIGNAL")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Inventory", f"{len(data.get('Inventory Alkes', []))} Unit")
    col2.metric("Total Surat Masuk", f"{len(data.get('Surat Masuk (Nota Dinas)', []))} Surat")
    col3.metric("Total Perbaikan", f"{len(data.get('Perbaikan', []))} Laporan")
    col4.metric("Total Pemeliharaan", f"{len(data.get('Pemeliharaan', []))} Kegiatan")
    
    st.markdown("### 📂 Tinjauan Seluruh Data Log")
    tabs = st.tabs(list(KOLOM_DEFAULT.keys()))
    for i, key in enumerate(KOLOM_DEFAULT.keys()):
        with tabs[i]:
            df_tab = pd.DataFrame(data[key])
            st.dataframe(df_tab, use_container_width=True)

elif selected_menu in menu_sop:
    st.header(f"📚 Menu Dokumen: {selected_menu}")
    st.markdown("### 🔍 Pilih Alat dari Master Inventory & Upload SOP")
    daftar_alat = dapatkan_daftar_nama_alat_inventory()
    if not daftar_alat:
        st.warning("⚠️ Belum ada nama alat di dalam 'Inventory Alkes'. Sila isi data inventory terlebih dahulu.")
    else:
        pilih_nama_alat = st.selectbox("Silakan pilih Nama Alat untuk melihat/mengunggah SOP:", daftar_alat)
        sop_storage_key = f"{selected_menu}_{pilih_nama_alat}"
        st.markdown("---")
        col_up, col_down = st.columns(2)
        with col_up:
            st.markdown("#### 📤 Upload File SOP Baru")
            file_sop = st.file_uploader(f"Upload dokumen SOP (.pdf, .docx, .xlsx) untuk {pilih_nama_alat}", type=["pdf", "docx", "xlsx", "txt"], key=f"file_{sop_storage_key}")
            if file_sop is not None:
                if st.button("💾 Simpan Dokumen SOP", use_container_width=True):
                    import base64
                    encoded_file = base64.b64encode(file_sop.read()).decode('utf-8')
                    st.session_state["w_signal_db"]["SOP_Files"][sop_storage_key] = {
                        "filename": file_sop.name,
                        "base64_data": encoded_file
                    }
                    save_data(st.session_state["w_signal_db"])
                    st.success(f"Berhasil mengunggah dokumen SOP untuk {pilih_nama_alat}!")
                    st.rerun()
        with col_down:
            st.markdown("#### 📥 Download Dokumen SOP Aktif")
            saved_sop_dict = data.get("SOP_Files", {})
            if sop_storage_key in saved_sop_dict:
                file_info = saved_sop_dict[sop_storage_key]
                import base64
                decoded_bytes = base64.b64decode(file_info["base64_data"])
                st.info(f"📄 File aktif: **{file_info['filename']}**")
                st.download_button(label=f"📥 Download SOP {pilih_nama_alat}", data=decoded_bytes, file_name=file_info["filename"], use_container_width=True)
            else:
                st.warning("⚠️ Belum ada file SOP yang diupload untuk alat ini.")

else:
    st.header(f"📋 Menu: {selected_menu}")
    st.markdown("### 📥 Tambah Data Baru")
    with st.form(key=f"form_{selected_menu.lower().replace(' ', '_')}", clear_on_submit=True):
        inputs = {}
        if selected_menu == "Inventory Alkes":
            col1, col2, col3 = st.columns(3)
            inputs["Nama Alat"] = col1.text_input("Nama Alat")
            inputs["Merk"] = col2.text_input("Merk")
            inputs["Type"] = col3.text_input("Type")
            col4, col5 = st.columns(2)
            inputs["Nomor Seri"] = col4.text_input("Nomor Seri")
            inputs["Ruangan"] = col5.text_input("Ruangan")
            inputs["Tahun Pengadaan"] = st.text_input("Tahun Pengadaan")
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
            inputs["Note"] = ""

        if st.form_submit_button(label="➕ Tambah Data Manual"):
            st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
            if selected_menu in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                peta_inv = dapatkan_peta_inventory()
                ns_key = str(inputs.get("Nomor Seri", "")).strip().lower()
                if ns_key in peta_inv:
                    inputs["Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                    inputs["Merk"] = peta_inv[ns_key]["Merk"]
                    inputs["Type"] = peta_inv[ns_key]["Type"]
                    inputs["Ruangan"] = peta_inv[ns_key]["Ruangan"]
                    inputs["Note"] = ""
                elif ns_key != "":
                    inputs["Nama Alat"] = ""; inputs["Merk"] = ""; inputs["Type"] = ""; inputs["Ruangan"] = ""
                    inputs["Note"] = "⚠️ BELUM DIINVENTORY"
            st.session_state["w_signal_db"][selected_menu].append(inputs)
            if selected_menu == "Perencanaan RAB (Usulan)":
                st.session_state["w_signal_db"][selected_menu] = recalculate_rab(st.session_state["w_signal_db"][selected_menu])
            save_data(st.session_state["w_signal_db"])
            st.success(f"Data manual berhasil ditambahkan!")
            st.rerun()

    with st.expander(f"📂 Mass Upload File Excel / CSV ({selected_menu})"):
        st.markdown(f"**Format Judul Kolom Wajib:** `{', '.join(KOLOM_DEFAULT[selected_menu])}`")
        uploaded_file = st.file_uploader("Pilih file Excel (.xlsx) atau CSV (.csv)", type=["xlsx", "csv"], key=f"file_uploader_{selected_menu.lower().replace(' ', '_')}")
        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                st.dataframe(df_upload.head(3), caption="Pratonton Data (3 Baris Teratas)")
                if st.button("🚀 Konfirmasi & Masukkan Data Massal", key=f"btn_upload_{selected_menu.lower().replace(' ', '_')}", use_container_width=True):
                    st.session_state["undo_history"].append(copy.deepcopy(st.session_state["w_signal_db"]))
                    kolom_req = KOLOM_DEFAULT[selected_menu]
                    for col in kolom_req:
                        if col not in df_upload.columns:
                            df_upload[col] = 0 if col in ["Jumlah Stok", "In", "Out", "Pagu Sub Kegiatan", "Nilai SPH", "Nilai Kontrak", "Sisa Pagu Anggaran Kegiatan"] else ""
                    df_upload = df_upload[kolom_req]
                    if selected_menu in ["Perbaikan", "Kalibrasi", "Pemeliharaan"]:
                        peta_inv = dapatkan_peta_inventory()
                        for idx, row in df_upload.iterrows():
                            ns_key = str(row.get("Nomor Seri", "")).strip().lower()
                            if ns_key in peta_inv:
                                df_upload.at[idx, "Nama Alat"] = peta_inv[ns_key]["Nama Alat"]
                                df_upload.at[idx, "Merk"] = peta_inv[ns_key]["Merk"]
                                df_upload.at[idx, "Type"] = peta_inv[ns_key]["Type"]
                                if "Ruangan" in df_upload.columns: df_upload.at[idx, "Ruangan"] = peta_inv[ns_key]["Ruangan"]
                                df_upload.at[idx, "Note"] = ""
                            elif ns_key != "":
                                df_upload.at[idx, "Note"] = "⚠️ BELUM DIINVENTORY"
                    kolom_tanggal_sistem = ["Tanggal Perbaikan", "Tanggal Pemeliharaan", "Tanggal Kalibrasi", "Tanggal", "Tanggal Terima Surat", "Tanggal Surat"]
                    for col in kolom_tanggal_sistem:
                        if col in df_upload.columns: df_upload[col] = df_upload[col].apply(bersihkan_format_tanggal)
                    st.session_state["w_signal_db"][selected_menu].extend(df_upload.fillna("").to_dict(orient="records"))
                    if selected_menu == "Perencanaan RAB (Usulan)":
                        st.session_state["w_signal_db"][selected_menu] = recalculate_rab(st.session_state["w_signal_db"][selected_menu])
                    save_data(st.session_state["w_signal_db"])
                    st.success(f"Berhasil mengimpor {len(df_upload)} data!")
                    st.rerun()
            except Exception as e:
                st.error(f"Gagal memproses file. Error: {e}")

    st.markdown("---")
    st.markdown("### 📝 Live-Editor & Tabel Data")
    df_menu = pd.DataFrame(data.get(selected_menu, []))
    editor_key = f"editor_{selected_menu.lower().replace(' ', '_')}"
    edited_df = st.data_editor(df_menu, num_rows="dynamic", use_container_width=True, key=editor_key, on_change=handle_editor_change, args=(selected_menu, editor_key))
    
    if not df_menu.empty:
        try:
            excel_bytes = convert_df_to_excel(df_menu)
            st.download_button(label=f"📥 Download Seluruh Data {selected_menu} (.xlsx)", data=excel_bytes, file_name=f"Data_{selected_menu.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except:
            pass
        
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

if search_ns:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Hasil Pencarian Alat:")
    peta = dapatkan_peta_inventory()
    ns_clean = search_ns.strip().lower()
    if ns_clean in peta:
        info = peta[ns_clean]
        st.sidebar.success(f"**Alat Ditemukan!**\n\n* **Nama:** {info['Nama Alat']}\n* **Merk:** {info['Merk']}\n* **Type:** {info['Type']}\n* **Ruangan:** {info['Ruangan']}")
        freq = hitung_frekuensi_kerusakan().get(ns_clean, 0)
        if freq > 3: st.sidebar.error(f"⚠️ **Peringatan:** Alat ini sudah rusak sebanyak **{freq} kali**!")
        else: st.sidebar.info(f"Riwayat Perbaikan: {freq} kali.")
    else:
        st.sidebar.warning("Nomor Seri belum terdaftar di Inventory Alkes.")
