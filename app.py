import io
import json
import os
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA DARK MODEREN
# ==========================================
st.set_page_config(
    page_title="W-SIGNAL - SIMRS Elektromedis",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .badge-condition {
        background-color: #238636;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-risk {
        background-color: #d29922;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-tech {
        background-color: #1f6feb;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .price-tag {
        font-size: 1.8rem;
        font-weight: 800;
        color: #3fb950;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
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
  if os.path.exists(LOCAL_DB_FILE):
    try:
      with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_all_local_data(data):
  with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_sheet_data(menu_name):
  db = load_all_local_data()
  records = db.get(menu_name, [])
  if not records:
    return pd.DataFrame()
  return pd.DataFrame(records)


def save_sheet_data(menu_name, new_data_dict):
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
    st.error(f"Gagal menyimpan data: {e}")
    return False


# ==========================================
# 3. FUNGSI EKSPOR & TEMPLATE EXCEL
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
# 4. AUTENTIKASI & LOGIN
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
# 5. SIDEBAR & NAVIGASI
# ==========================================
st.sidebar.markdown("### 🗂 KONTROL DATA")
st.sidebar.markdown(f"**Status Login:** `{st.session_state['username']}`")
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
      "Detail & Portfolio Alat (MDX Style)",
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
  menu_options = [
      "Detail & Portfolio Alat (MDX Style)",
      "Perbaikan",
      "Pemeliharaan",
  ]

selected_menu = st.sidebar.radio("", menu_options, label_visibility="collapsed")

# ==========================================
# 6. TAMPILAN PORTFOLIO ALAT (MDX STYLE)
# ==========================================
if selected_menu == "Detail & Portfolio Alat (MDX Style)":
  top_c1, top_c2 = st.columns([3, 1])
  with top_c1:
    st.caption("Home / Inventory / Detail / Alat Kesehatan RSUD Welas Asih")
  with top_c2:
    if st.button("🚩 Report Complaint / Laporkan Kerusakan", type="primary"):
      st.warning("Silakan menuju ke menu 'Perbaikan' di sidebar.")

  st.markdown("---")

  head_col1, head_col2 = st.columns([1, 2])
  with head_col1:
    st.image(
        "https://via.placeholder.com/400x300.png?text=Foto+Fisik+Alat",
        caption="Mindray BeneFusion eV3 / Infusion Pump",
        use_column_width=True,
    )

  with head_col2:
    st.title("Infusion Pump")
    st.markdown("""
        **SN:** `SH2A34000503T` | **ID Alat:** `EM-000895`  
        **Lokasi:** ICU Room 3 - RSUD Welas Asih
        """)

    m1, m2, m3 = st.columns(3)
    with m1:
      st.markdown("Kondisi")
      st.markdown(
          "<span class='badge-condition'>Baik</span>", unsafe_allow_html=True
      )
    with m2:
      st.markdown("Risk")
      st.markdown(
          "<span class='badge-risk'>Medium</span>", unsafe_allow_html=True
      )
    with m3:
      st.markdown("Teknologi")
      st.markdown(
          "<span class='badge-tech'>Menengah</span>", unsafe_allow_html=True
      )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Harga Pembelian:**")
    st.markdown(
        "<div class='price-tag'>Rp 26.500.000</div>", unsafe_allow_html=True
    )

  st.markdown("<br>", unsafe_allow_html=True)

  tab_data, tab_ipm, tab_admin, tab_doc, tab_part, tab_hist = st.tabs([
      "Data Alat",
      "IPM & Kalibrasi",
      "Administrasi",
      "Documents",
      "Sparepart",
      "History",
  ])

  with tab_data:
    st.subheader("Data Spesifikasi Alat & Fisik")
    d1, d2 = st.columns(2)
    with d1:
      st.markdown("**Status:** Aktif")
      st.markdown("**Kepemilikan:** Rumah Sakit RSUD Welas Asih")
      st.markdown("**Daya Listrik:** 46 VA")
    with d2:
      st.markdown("**Distributor:** PT. Internusa Dua Medika")
      st.markdown("**Tahun Pengadaan:** 2023")
      st.markdown("**Masa Garansi:** 2024-06-13")

  with tab_ipm:
    st.subheader("#Equipment Management (EM) Classification")
    em_df = pd.DataFrame({
        "Category": [
            "Equipment Function",
            "Clinical Application",
            "PM Requirement",
            "Incident History",
        ],
        "#EM": [8, 4, 4, 2],
        "Description": [
            "Physical therapy and treatment",
            "Potential patient or operator injury",
            "Above-average",
            "Significant: more than one every 6 months",
        ],
    })
    st.table(em_df)

    i1, i2 = st.columns(2)
    with i1:
      st.markdown("#### Maintenance (IPM)")
      st.markdown("- **Last Maintenance:** 21-07-2026")
      st.markdown("- **Next Maintenance:** 21-01-2027")
      st.markdown("- **Interval:** 6 Bulan (Semi-annual)")
    with i2:
      st.markdown("#### Kalibrasi")
      st.markdown("- **Last Calibration:** 22-09-2026")
      st.markdown("- **Next Calibration:** 22-09-2027")
      st.markdown("- **Interval:** 1 Tahun")

  with tab_admin:
    st.subheader("Data Administrasi & Penyusutan Value")
    a1, a2 = st.columns(2)
    with a1:
      st.markdown("**Nilai Perolehan:** Rp 26.500.000")
      st.markdown("**Penyusutan Tahunan:** Rp 2.650.000")
      st.markdown("**Usia Pakai:** 3 Tahun")
    with a2:
      st.markdown("**Akumulasi Penyusutan:** Rp 7.950.000")
      st.markdown("**Nilai Buku Saat Ini:** Rp 18.550.000")
      st.markdown("**Perkiraan Harga Pengganti:** Rp 31.783.334")

  with tab_doc:
    st.subheader("Technical Documents & Sertifikat")
    st.markdown("📄 **Service Manual:** `SM_Mindray_eV3.pdf` [Download]")
    st.markdown("📄 **SPO Operasional:** `IE/129/PA/IPSRS/23` [View]")
    st.markdown("📄 **SPO Preventive Maintenance:** `SPO_IPM_Infusion.pdf`")
    st.markdown("---")
    st.subheader("Sertifikat Kalibrasi")
    cal_data = pd.DataFrame({
        "Tanggal": ["22/09/2026", "04/12/2025", "17/09/2024"],
        "Institusi / BPFK": [
            "PT. NIRMALA KARYA",
            "PT. FAMED",
            "PT. Mitra Tera Akurasi",
        ],
        "Hasil": ["Laik Pakai", "Laik Pakai", "Laik Pakai"],
        "Berkas Sertifikat": [
            "Sertifikat_2026.pdf",
            "-",
            "1737678290_cert.pdf",
        ],
    })
    st.dataframe(cal_data, use_container_width=True)

  with tab_part:
    st.subheader("Tabel Sparepart Rutin & Penggantian Suku Cadang")
    part_df = load_sheet_data("Stok Suku Cadang")
    if not part_df.empty:
      st.dataframe(part_df, use_container_width=True)
    else:
      st.info("Belum ada riwayat penggantian suku cadang.")

  with tab_hist:
    st.subheader("Activity Graph & Historical Log")
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_facecolor("#161b22")
    fig.patch.set_facecolor("#161b22")
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "Mei",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    activity = [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0]
    ax.plot(months, activity, color="#238636", marker="o", linewidth=2)
    ax.tick_params(colors="white")
    st.pyplot(fig)

    st.markdown("---")
    st.markdown("🟢 **22 Sep 2026** — **Kalibrasi**: Laik Pakai (PT. Nirmala)")
    st.markdown("🔵 **21 Jul 2026** — **Maintenance**: Passed (Inspeksi Rutin)")
    st.markdown("🔴 **05 Jan 2026** — **Perbaikan**: Penggantian Sensor Drip")

# ==========================================
# 7. FORM INPUT LEMBAR KERJA & MENU W-SIGNAL
# ==========================================
elif selected_menu != "Lihat Semua Data & Ringkasan":
  st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")
  st.header(f"📝 Input Data / Lembar Kerja: {selected_menu}")

  # A. FORM PERBAIKAN
  if selected_menu == "Perbaikan":
    with st.form(key="form_perbaikan_lkem", clear_on_submit=True):
      st.subheader("📋 Lembar Kerja Service Elektromedis RSUD Welas Asih")

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
        alat_kerja = st.text_input("Alat Kerja / Calibrator")

      st.markdown("##### 🌡️ Inspection: Kondisi Lingkungan & Kelistrikan")
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

      st.markdown("##### 🛠️ Detail Perbaikan")
      keluhan = st.text_area("Keluhan / Masalah Awal")
      tahapan_pemeriksaan = st.text_area("Tahapan Pemeriksaan")
      analisa = st.text_area("Analisa Kerusakan")
      detail_action = st.text_area("Detail Action & Penggantian Part")

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
              "Keluhan": keluhan,
              "Tahapan Pemeriksaan": tahapan_pemeriksaan,
              "Analisa": analisa,
              "Detail Action": detail_action,
              "Hasil Pemeriksaan": hasil_pemeriksaan,
              "Rekomendasi": rekomendasi,
              "Teknisi Pelaksana": teknisi,
              "PJ Ruangan": pj_ruangan,
          }
          if uploaded_file is not None:
            new_row["Lampiran"] = uploaded_file.name

          if save_sheet_data(selected_menu, new_row):
            st.success("Data Perbaikan Berhasil Disimpan!")
            st.rerun()

  # B. FORM PEMELIHARAAN
  elif selected_menu == "Pemeliharaan":
    with st.form(key="form_pemeliharaan_ipm", clear_on_submit=True):
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

      h1, h2, h3 = st.columns(3)
      with h1:
        stok_konsumabel = st.selectbox(
            "Stok Konsumabel", ["Ada", "Tidak Ada", "Habis"]
        )
      with h2:
        hasil_maintenance = st.selectbox(
            "Hasil Maintenance",
            [
                "Alat Berfungsi Dengan Baik",
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
              "Display/Monitor": display_mon,
              "Switch On/Off": switch_on_off,
              "Control Setting": control_setting,
              "Keypad": keypad,
              "Alarm": alarm,
              "Power Cord": power_cord,
              "Stok Konsumabel": stok_konsumabel,
              "Penggantian Consumable": ganti_consumable,
              "Hasil Maintenance": hasil_maintenance,
              "Teknisi Pelaksana": teknisi,
              "PJ Ruangan": pj_ruangan,
          }
          if uploaded_file is not None:
            new_row["Lampiran"] = uploaded_file.name

          if save_sheet_data(selected_menu, new_row):
            st.success("Data Pemeliharaan Berhasil Disimpan!")
            st.rerun()

  # C. FORM STANDAR
  else:
    with st.form(key=f"form_standard_{selected_menu}", clear_on_submit=True):
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

  # MASS UPLOAD
  if st.session_state["user_role"] == "NAY":
    with st.expander(f"📁 Mass Upload & Download Template ({selected_menu})"):
      render_template_download_button(selected_menu)
      mass_file = st.file_uploader(
          "Upload File Excel untuk Mass Import",
          type=["xlsx", "xls"],
          key=f"mass_excel_{selected_menu}",
      )
      if mass_file is not None:
        if st.button(
            "🚀 Proses Mass Import Excel", key=f"btn_import_{selected_menu}"
        ):
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
  render_excel_download_button(
      df_current, filename_prefix=selected_menu.replace(" ", "_")
  )

# ==========================================
# 8. RINGKASAN & REKAPITULASI
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
