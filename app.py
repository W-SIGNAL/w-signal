import io
import json
import os
import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLES
# ==========================================
st.set_page_config(
    page_title="W-SIGNAL",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    .section-header {
        color: #4CAF50;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

LOCAL_DB_FILE = "database_w_signal.json"


# ==========================================
# 2. PENYIMPANAN DATA LOKAL (FILE JSON)
# ==========================================
def load_all_local_data():
  """Membaca seluruh database dari file JSON lokal."""
  if os.path.exists(LOCAL_DB_FILE):
    try:
      with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_all_local_data(data):
  """Menyimpan seluruh database ke file JSON lokal."""
  with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_sheet_data(menu_name):
  """Mengambil data tabel sebagai DataFrame Pandas."""
  db = load_all_local_data()
  records = db.get(menu_name, [])
  if not records:
    return pd.DataFrame()
  return pd.DataFrame(records)


def save_sheet_data(menu_name, new_data_dict):
  """Menambahkan satu baris data ke penyimpanan lokal."""
  try:
    db = load_all_local_data()
    if menu_name not in db:
      db[menu_name] = []

    clean_dict = {
        str(k).strip(): str(v).strip()
        for k, v in new_data_dict.items()
        if v is not None
    }
    db[menu_name].append(clean_dict)

    save_all_local_data(db)
    return True
  except Exception as e:
    st.error(f"Gagal menyimpan data lokal: {e}")
    return False


# ==========================================
# 3. FUNGSI EKSPOR & TEMPLATE EXCEL (.XLSX)
# ==========================================
def convert_df_to_excel(df, sheet_name="Data_Rekap"):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name=sheet_name)
  return output.getvalue()


def render_excel_download_button(df, filename_prefix="Rekap_Data"):
  if not df.empty:
    excel_data = convert_df_to_excel(df, sheet_name=filename_prefix[:30])
    st.download_button(
        label=f"📥 Download Seluruh Data {filename_prefix} (.xlsx)",
        data=excel_data,
        file_name=f"{filename_prefix}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
  else:
    st.info("Belum ada data untuk diunduh.")


def render_template_download_button(sheet_name):
  if sheet_name == "Perbaikan":
    columns = [
        "No LKEM",
        "Tanggal Pekerjaan",
        "Nama Alat",
        "Merk/Tipe",
        "Nomor Seri",
        "Ruang/Instalasi",
        "Keluhan",
        "Analisa",
        "Tindakan / Action",
        "Hasil Akhir",
        "Rekomendasi",
        "Teknisi Pelaksana",
        "PJ Ruangan",
    ]
  elif sheet_name == "Pemeliharaan":
    columns = [
        "No LKEM",
        "Tanggal IPM",
        "Nama Alat",
        "Merk/Tipe",
        "Nomor Seri",
        "Ruang/Instalasi",
        "Suhu Ruangan",
        "Kelembaban",
        "Tegangan",
        "Pembersihan Unit",
        "Pemeriksaan Fungsi",
        "Stok Konsumabel",
        "Hasil Maintenance",
        "Teknisi Pelaksana",
        "PJ Ruangan",
    ]
  else:
    columns = [
        "Nama Alat",
        "Merk",
        "Type",
        "Nomor Seri",
        "Tahun Pengadaan",
        "Harga Perolehan",
        "Kondisi",
        "Ruangan",
        "Keterangan",
    ]

  df_template = pd.DataFrame(columns=columns)
  template_bytes = convert_df_to_excel(
      df_template, sheet_name=sheet_name[:30]
  )
  st.download_button(
      label=f"📄 Download Template Excel ({sheet_name})",
      data=template_bytes,
      file_name=f"Template_{sheet_name.replace(' ', '_')}.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
      use_container_width=True,
  )


# ==========================================
# 4. MANAJEMEN AUTENTIKASI & HALAMAN LOGIN
# ==========================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["user_role"] = ""
  st.session_state["username"] = ""

if not st.session_state["logged_in"]:
  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### 🔒 Login Sistem W-SIGNAL")

    with st.form("login_form"):
      username_input = st.text_input("Username")
      password_input = st.text_input("Password", type="password")
      submit_login = st.form_submit_button(
          "Masuk / Login", use_container_width=True
      )

      if submit_login:
        if username_input == "NAY" and password_input == "lalanana":
          st.session_state["logged_in"] = True
          st.session_state["user_role"] = "NAY"
          st.session_state["username"] = "NAY"
          st.success("Login Berhasil sebagai Super Admin!")
          st.rerun()
        elif username_input == "GUEST" and password_input == "12345":
          st.session_state["logged_in"] = True
          st.session_state["user_role"] = "GUEST"
          st.session_state["username"] = "GUEST"
          st.success("Login Berhasil sebagai Teknisi!")
          st.rerun()
        else:
          st.error("Username atau Password salah!")

    st.info(
        "💡 **Akses Teknisi:**\n- Username: `GUEST` | Password: `12345`"
        " (Khusus Input Perbaikan & Pemeliharaan)."
    )
  st.stop()

# ==========================================
# 5. SIDEBAR & MENU UTAMA
# ==========================================
st.sidebar.markdown("### 🗂 KONTROL DATA")
st.sidebar.markdown(f"**Status Login:** {st.session_state['username']}")
if st.sidebar.button("Logout / Keluar", use_container_width=True):
  st.session_state["logged_in"] = False
  st.session_state["user_role"] = ""
  st.session_state["username"] = ""
  st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 SCAN / CARI ALAT")
search_barcode = st.sidebar.text_input(
    "Arahkan kursor & Scan Barcode:", placeholder="Ketik/Scan No. Seri..."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Pilih Menu:")

if st.session_state["user_role"] == "NAY":
  menu_options = [
      "Inventory Alkes",
      "Perbaikan",
      "Pemeliharaan",
      "Stok Suku Cadang",
      "Perencanaan RAB (Usulan)",
      "Surat Masuk (Nota Dinas)",
      "Rekap SR Vendor",
      "Kalibrasi",
      "Lihat Semua Data & Ringkasan",
      "Manajemen SOP Alkes",
  ]
else:
  menu_options = ["Perbaikan", "Pemeliharaan"]

selected_menu = st.sidebar.radio("", menu_options, label_visibility="collapsed")

# ==========================================
# 6. TAMPILAN UTAMA & FORM INPUT
# ==========================================
st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

if selected_menu != "Lihat Semua Data & Ringkasan":

  st.header(f"📝 Input / Lembar Kerja: {selected_menu}")

  with st.form(key=f"form_{selected_menu}", clear_on_submit=True):

    # -------------------------------------------------------------
    # A. FORM KHUSUS PERBAIKAN (LK SERVICE ELEKTROMEDIS)
    # -------------------------------------------------------------
    if selected_menu == "Perbaikan":
      st.subheader("📋 Lembar Kerja Service Elektromedis")

      c1, c2, c3 = st.columns(3)
      with c1:
        no_lkem = st.text_input("No. LKEM", placeholder=".../IPSRS/.../20...")
        tgl_pekerjaan = st.date_input("Tanggal Pekerjaan")
      with c2:
        instalasi = st.text_input("Instalasi / Unit")
        ruangan = st.text_input("Ruangan")
      with c3:
        nama_alat = st.text_input("Nama Alat *")
        merk_tipe = st.text_input("Merk / Tipe")

      c4, c5, c6 = st.columns(3)
      with c4:
        nomor_seri = st.text_input("Nomor Seri (SN)")
      with c5:
        tgl_kalibrasi = st.text_input("Tanggal Kalibrasi Terakhir")
      with c6:
        alat_kerja = st.text_input("Alat Kerja / Calibrator yang Digunakan")

      st.markdown(
          "##### 🌡️ Inspection: Kondisi Lingkungan & Kelistrikan"
      )
      e1, e2, e3, e4, e5 = st.columns(5)
      with e1:
        suhu = st.text_input("Suhu (°C)")
      with e2:
        kelembaban = st.text_input("Kelembaban (%)")
      with e3:
        tegangan_jala = st.text_input("Tegangan Jala-jala (V)")
      with e4:
        ups_volt = st.text_input("UPS (V)")
      with e5:
        stabilizer_volt = st.text_input("Stabilizer (V)")

      st.markdown("##### 🔍 Inspection: Fisik & Keamanan Listrik")
      f1, f2, f3, f4 = st.columns(4)
      with f1:
        penempatan = st.selectbox(
            "Penempatan Alat", ["Baik", "Tidak Baik", "N/A"]
        )
      with f2:
        trolley = st.selectbox(
            "Roda / Trolley / Bracket", ["Baik", "Tidak Baik", "N/A"]
        )
      with f3:
        fisik_unit = st.selectbox(
            "Kondisi Fisik Main Unit",
            ["Baik (B)", "Cukup (C/RR)", "Rusak Berat (RB)"],
        )
      with f4:
        ground_res = st.text_input("Ground Resistance (≤ 0,5 Ω)")

      st.markdown("##### 🛠️ Detail Perbaikan / Service Log")
      keluhan = st.text_area("Keluhan / Masalah Awal")
      tahapan_pemeriksaan = st.text_area("Tahapan Pemeriksaan")
      analisa = st.text_area("Analisa Kerusakan")

      st.markdown("##### 🔧 Tindakan / Action")
      action_type = st.multiselect(
          "Tindakan Perbaikan:",
          [
              "Perbaikan Langsung",
              "Ganti Spare Part (Stock)",
              "Tunda Perbaikan",
              "Ganti Spare Part (PBJP)",
              "Perlu Perbaikan Pihak Ketiga",
          ],
      )
      detail_action = st.text_area("Detail Tindakan & Penggantian Part")

      st.markdown("##### 📌 Hasil Pekerjaan & Rekomendasi")
      r1, r2 = st.columns(2)
      with r1:
        hasil_pemeriksaan = st.selectbox(
            "Hasil Pemeriksaan",
            [
                "Alat Berfungsi Dengan Baik",
                "Alat Tidak Dapat Berfungsi Dengan Baik",
            ],
        )
        rekomendasi = st.selectbox(
            "Rekomendasi Akhir",
            [
                "Alat Dapat Digunakan",
                "Alat Tidak Dapat Digunakan",
                "Alat Sudah Tidak Laik Operasi (Usul Penghapusan)",
            ],
        )
      with r2:
        teknisi = st.text_input(
            "Teknisi Pelaksana", value=st.session_state["username"]
        )
        pj_ruangan = st.text_input("PJ Alat / Ruangan")

      uploaded_file = st.file_uploader(
          "Upload Foto / Lampiran Service", type=["pdf", "png", "jpg", "xlsx"]
      )

      submitted = st.form_submit_button(
          "Simpan Lembar Kerja Perbaikan", use_container_width=True
      )

      if submitted:
        if not nama_alat:
          st.warning("Mohon isi minimal Nama Alat!")
        else:
          new_row = {
              "No LKEM": no_lkem,
              "Tanggal Pekerjaan": str(tgl_pekerjaan),
              "Instalasi": instalasi,
              "Ruangan": ruangan,
              "Nama Alat": nama_alat,
              "Merk/Tipe": merk_tipe,
              "Nomor Seri": nomor_seri,
              "Tgl Kalibrasi": tgl_kalibrasi,
              "Alat Kerja": alat_kerja,
              "Suhu (°C)": suhu,
              "Kelembaban (%)": kelembaban,
              "Tegangan Jala": tegangan_jala,
              "UPS (V)": ups_volt,
              "Stabilizer (V)": stabilizer_volt,
              "Penempatan": penempatan,
              "Roda/Trolley": trolley,
              "Fisik Main Unit": fisik_unit,
              "Ground Resistance": ground_res,
              "Keluhan": keluhan,
              "Tahapan Pemeriksaan": tahapan_pemeriksaan,
              "Analisa": analisa,
              "Tindakan": ", ".join(action_type),
              "Detail Action": detail_action,
              "Hasil Pemeriksaan": hasil_pemeriksaan,
              "Rekomendasi": rekomendasi,
              "Teknisi Pelaksana": teknisi,
              "PJ Ruangan": pj_ruangan,
          }
          if uploaded_file is not None:
            new_row["Lampiran"] = uploaded_file.name

          if save_sheet_data(selected_menu, new_row):
            st.success("Lembar Kerja Perbaikan berhasil disimpan!")
            st.rerun()

    # -------------------------------------------------------------
    # B. FORM KHUSUS PEMELIHARAAN (LK IPM ELEKTROMEDIS)
    # -------------------------------------------------------------
    elif selected_menu == "Pemeliharaan":
      st.subheader("📋 Lembar Kerja Inspection Preventive Maintenance (IPM)")

      c1, c2, c3 = st.columns(3)
      with c1:
        no_lkem = st.text_input("No. LKEM", placeholder=".../IPSRS/.../20...")
        tgl_ipm = st.date_input("Tanggal Pemeliharaan (IPM)")
      with c2:
        instalasi = st.text_input("Instalasi / Unit")
        ruangan = st.text_input("Ruangan")
      with c3:
        nama_alat = st.text_input("Nama Alat *")
        merk_tipe = st.text_input("Merk / Tipe")

      c4, c5, c6 = st.columns(3)
      with c4:
        nomor_seri = st.text_input("Nomor Seri (SN)")
      with c5:
        tgl_kalibrasi = st.text_input("Tanggal Kalibrasi Terakhir")
      with c6:
        alat_kerja = st.text_input("Alat Kerja yang Digunakan")

      st.markdown(
          "##### 🌡️ Kondisi Lingkungan & Kelistrikan"
      )
      e1, e2, e3, e4, e5 = st.columns(5)
      with e1:
        suhu = st.text_input("Suhu (°C)")
      with e2:
        kelembaban = st.text_input("Kelembaban (%)")
      with e3:
        tegangan_jala = st.text_input("Tegangan Jala-jala (V)")
      with e4:
        ups_volt = st.text_input("UPS (V)")
      with e5:
        stabilizer_volt = st.text_input("Stabilizer (V)")

      st.markdown("##### 🔍 Inspection & Pemeriksaan Fungsi Alat")
      f1, f2, f3 = st.columns(3)
      with f1:
        display_mon = st.selectbox("Display / Monitor", ["Baik", "Tidak Baik"])
        switch_on_off = st.selectbox("Switch On/Off", ["Baik", "Tidak Baik"])
      with f2:
        control_setting = st.selectbox(
            "Control Setting", ["Baik", "Tidak Baik"]
        )
        keypad = st.selectbox("Keypad", ["Baik", "Tidak Baik"])
      with f3:
        alarm = st.selectbox("Alarm", ["Baik", "Tidak Baik"])
        power_cord = st.selectbox(
            "Power Cord / Adaptor", ["Baik", "Tidak Baik"]
        )

      st.markdown("##### 🧹 Preventive Maintenance Tasks")
      p1, p2, p3 = st.columns(3)
      with p1:
        pembersihan_unit = st.selectbox(
            "Pembersihan Main Unit", ["Dilakukan", "Tidak Dilakukan"]
        )
      with p2:
        pembersihan_aksesoris = st.selectbox(
            "Pembersihan Aksesoris", ["Dilakukan", "Tidak Dilakukan"]
        )
      with p3:
        pantau_fungsi = st.selectbox(
            "Pemantauan Fungsi & Kinerja", ["Dilakukan", "Tidak Dilakukan"]
        )

      st.markdown("##### 📦 Stok Konsumabel & Hasil Maintenance")
      h1, h2, h3 = st.columns(3)
      with h1:
        stok_konsumabel = st.selectbox(
            "Stok Konsumabel", ["Ada", "Tidak Ada", "Habis"]
        )
      with h2:
        hasil_maintenance = st.selectbox(
            "Hasil Maintenance",
            [
                "Allet Berfungsi Dengan Baik",
                "Alat Tidak Dapat Berfungsi Dengan Baik",
            ],
        )
      with h3:
        ganti_consumable = st.text_input(
            "Penggantian Consumable Part / Baterai"
        )

      m1, m2 = st.columns(2)
      with m1:
        teknisi = st.text_input(
            "Teknisi Pelaksana", value=st.session_state["username"]
        )
      with m2:
        pj_ruangan = st.text_input("PJ Alat / Ruangan")

      uploaded_file = st.file_uploader(
          "Upload Foto / Lampiran Pemeliharaan",
          type=["pdf", "png", "jpg", "xlsx"],
      )

      submitted = st.form_submit_button(
          "Simpan Lembar Kerja IPM", use_container_width=True
      )

      if submitted:
        if not nama_alat:
          st.warning("Mohon isi minimal Nama Alat!")
        else:
          new_row = {
              "No LKEM": no_lkem,
              "Tanggal IPM": str(tgl_ipm),
              "Instalasi": instalasi,
              "Ruangan": ruangan,
              "Nama Alat": nama_alat,
              "Merk/Tipe": merk_tipe,
              "Nomor Seri": nomor_seri,
              "Tgl Kalibrasi": tgl_kalibrasi,
              "Alat Kerja": alat_kerja,
              "Suhu (°C)": suhu,
              "Kelembaban (%)": kelembaban,
              "Tegangan Jala": tegangan_jala,
              "Display/Monitor": display_mon,
              "Switch On/Off": switch_on_off,
              "Control Setting": control_setting,
              "Keypad": keypad,
              "Alarm": alarm,
              "Power Cord": power_cord,
              "Pembersihan Unit": pembersihan_unit,
              "Pembersihan Aksesoris": pembersihan_aksesoris,
              "Pemantauan Fungsi": pantau_fungsi,
              "Stok Konsumabel": stok_konsumabel,
              "Penggantian Consumable": ganti_consumable,
              "Hasil Maintenance": hasil_maintenance,
              "Teknisi Pelaksana": teknisi,
              "PJ Ruangan": pj_ruangan,
          }
          if uploaded_file is not None:
            new_row["Lampiran"] = uploaded_file.name

          if save_sheet_data(selected_menu, new_row):
            st.success("Lembar Kerja Pemeliharaan berhasil disimpan!")
            st.rerun()

    # -------------------------------------------------------------
    # C. FORM STANDAR UNTUK MENU LAINNYA
    # -------------------------------------------------------------
    else:
      with st.form(key=f"form_std_{selected_menu}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
          nama_alat = st.text_input("Nama Alat")
          merk = st.text_input("Merk")
          type_alat = st.text_input("Type")
          nomor_seri = st.text_input("Nomor Seri / SN")
          tahun_pengadaan = st.text_input("Tahun Pengadaan")
        with col2:
          harga_perolehan = st.text_input("Harga Perolehan")
          kondisi = st.selectbox(
              "Kondisi", ["Kondisi Baik", "Kondisi KB", "Kondisi RB"]
          )
          ruangan = st.text_input("Ruangan / Lokasi")
          keterangan = st.text_area("Keterangan / Catatan")

        uploaded_file = st.file_uploader(
            "Upload Foto / Lampiran (PDF, PNG, JPG, XLSX)",
            type=["pdf", "png", "jpg", "jpeg", "xlsx"],
        )

        submitted_std = st.form_submit_button(
            f"Simpan Data {selected_menu}", use_container_width=True
        )

        if submitted_std:
          if not nama_alat:
            st.warning("Mohon isi minimal Nama Alat!")
          else:
            new_row = {
                "Nama Alat": nama_alat,
                "Merk": merk,
                "Type": type_alat,
                "Nomor Seri": nomor_seri,
                "Tahun Pengadaan": tahun_pengadaan,
                "Harga Perolehan": harga_perolehan,
                kondisi: "✓",
                "Ruangan": ruangan,
                "Keterangan": keterangan,
            }
            if uploaded_file is not None:
              new_row["Lampiran"] = uploaded_file.name

            if save_sheet_data(selected_menu, new_row):
              st.success(f"Data {selected_menu} berhasil disimpan!")
              st.rerun()

  # Fitur Mass Upload Excel Khusus Admin (NAY)
  if st.session_state["user_role"] == "NAY":
    with st.expander(f"📁 Mass Upload & Download Template ({selected_menu})"):
      render_template_download_button(selected_menu)

      mass_file = st.file_uploader(
          "Upload File Excel untuk Mass Import",
          type=["xlsx", "xls"],
          key="mass_excel",
      )
      if mass_file is not None:
        if st.button("🚀 Proses Mass Import Excel"):
          try:
            df_mass = pd.read_excel(mass_file)
            count = 0
            for _, row in df_mass.iterrows():
              row_dict = row.dropna().to_dict()
              clean_dict = {
                  str(k).strip(): str(v).strip() for k, v in row_dict.items()
              }
              if save_sheet_data(selected_menu, clean_dict):
                count += 1
            st.success(f"Berhasil mengimpor {count} baris data!")
            st.rerun()
          except Exception as e:
            st.error(f"Gagal memproses file Excel: {e}")

  # Bagian Tabel Data & Download Harian
  st.markdown("---")
  st.subheader(f"📋 Live-Editor & Tabel Data: {selected_menu}")

  df_current = load_sheet_data(selected_menu)

  if search_barcode and not df_current.empty:
    match_col = [
        col
        for col in df_current.columns
        if "seri" in col.lower() or "alat" in col.lower()
    ]
    if match_col:
      df_current = df_current[
          df_current[match_col[0]]
          .astype(str)
          .str.contains(search_barcode, case=False, na=False)
      ]

  st.dataframe(df_current, use_container_width=True)

  # Tombol Download Excel Harian
  render_excel_download_button(
      df_current, filename_prefix=selected_menu.replace(" ", "_")
  )

# ==========================================
# 7. RINGKASAN & REKAPITULASI (Hanya Admin)
# ==========================================
else:
  st.header("📊 Ringkasan Analisis Data W-SIGNAL")

  all_menus = [
      "Inventory Alkes",
      "Perbaikan",
      "Pemeliharaan",
      "Stok Suku Cadang",
      "Perencanaan RAB (Usulan)",
      "Surat Masuk (Nota Dinas)",
      "Rekap SR Vendor",
      "Kalibrasi",
  ]
  tabs = st.tabs(all_menus)

  for idx, sheet_name in enumerate(all_menus):
    with tabs[idx]:
      st.subheader(f"Rekapitulasi {sheet_name}")
      df_tab = load_sheet_data(sheet_name)
      st.dataframe(df_tab, use_container_width=True)
      render_excel_download_button(
          df_tab, filename_prefix=f"Rekap_{sheet_name.replace(' ', '_')}"
      )
