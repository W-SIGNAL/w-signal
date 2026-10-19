import io
import json
import gspread
from google.oauth2.service_account import Credentials
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
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 2. KONEKSI GOOGLE SHEETS VIA SECRETS (FIXED)
# ==========================================
@st.cache_resource
def get_gspread_client():
  scopes = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
  ]
  if "gcp_service_account" not in st.secrets:
    st.error(
        "Secrets '[gcp_service_account]' tidak ditemukan di Streamlit Cloud!"
    )
    st.stop()

  raw_secret = st.secrets["gcp_service_account"]

  # Penanganan fleksibel untuk format Dict maupun JSON String
  if isinstance(raw_secret, str):
    secret_dict = json.loads(raw_secret)
  else:
    secret_dict = dict(raw_secret)

  # Memastikan private_key terformat dengan newlines yang benar
  if "private_key" in secret_dict:
    secret_dict["private_key"] = secret_dict["private_key"].replace(
        "\\n", "\n"
    )

  creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
  return gspread.authorize(creds)


@st.cache_data(ttl=5)
def load_sheet_data(worksheet_name):
  try:
    gc = get_gspread_client()
    sh = gc.open("W-SIGNAL_Database")

    target_ws = None
    for ws in sh.worksheets():
      if ws.title.strip().lower() == worksheet_name.strip().lower():
        target_ws = ws
        break

    if target_ws is None:
      return pd.DataFrame()

    data = target_ws.get_all_values()
    if not data or len(data) == 0:
      return pd.DataFrame()

    header_idx = 0
    for idx, row in enumerate(data[:5]):
      cleaned_row = [str(cell).strip() for cell in row]
      if any(
          k in cleaned_row
          for k in ["Nama Alat", "Merk", "Tanggal", "Nomor Seri"]
      ):
        header_idx = idx
        break

    headers = [str(h).strip() for h in data[header_idx]]
    rows = data[header_idx + 1 :]

    df = pd.DataFrame(rows, columns=headers)
    df = df.replace("", None).dropna(how="all").fillna("")
    return df
  except Exception as e:
    return pd.DataFrame()


def save_sheet_data(worksheet_name, new_data_dict):
  try:
    gc = get_gspread_client()
    sh = gc.open("W-SIGNAL_Database")

    target_ws = None
    for ws in sh.worksheets():
      if ws.title.strip().lower() == worksheet_name.strip().lower():
        target_ws = ws
        break

    if target_ws is None:
      target_ws = sh.add_worksheet(
          title=worksheet_name, rows="500", cols="20"
      )

    existing_data = target_ws.get_all_values()

    if not existing_data:
      headers = list(new_data_dict.keys())
      target_ws.append_row(headers)
      existing_headers = headers
    else:
      existing_headers = [str(h).strip() for h in existing_data[0]]

    row_to_append = []
    for h in existing_headers:
      row_to_append.append(str(new_data_dict.get(h, "")))

    for k, v in new_data_dict.items():
      if k not in existing_headers:
        existing_headers.append(k)
        row_to_append.append(str(v))

    target_ws.append_row(row_to_append)
    return True
  except Exception as e:
    st.error(f"Gagal menyimpan data ke Google Sheets: {e}")
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
  columns = [
      "Nama Alat",
      "Merk",
      "Type",
      "Nomor Seri",
      "Tahun Pengadaan",
      "Harga Perolehan",
      "Kondisi Baik",
      "Kondisi KB",
      "Kondisi RB",
      "Ruangan",
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

  st.header(f"📝 Input / Tambah Data: {selected_menu}")

  with st.form(key=f"form_{selected_menu}", clear_on_submit=True):
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

    submitted = st.form_submit_button(
        f"Simpan Data {selected_menu}", use_container_width=True
    )

    if submitted:
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

        with st.spinner("Menyimpan data ke Google Sheets..."):
          if save_sheet_data(selected_menu, new_row):
            st.cache_data.clear()
            st.success("Data berhasil disimpan!")

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
        if st.button("🚀 Proses Mass Import Excel ke Google Sheets"):
          try:
            df_mass = pd.read_excel(mass_file)
            count = 0
            with st.spinner("Sedang memproses dan memasukkan data massal..."):
              for _, row in df_mass.iterrows():
                row_dict = row.dropna().to_dict()
                clean_dict = {
                    str(k).strip(): str(v).strip() for k, v in row_dict.items()
                }
                if save_sheet_data(selected_menu, clean_dict):
                  count += 1
            st.cache_data.clear()
            st.success(
                f"Berhasil mengimpor {count} baris data ke Google Sheets!"
            )
            st.rerun()
          except Exception as e:
            st.error(f"Gagal memproses file Excel: {e}")

  # Bagian Tabel Data
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
# 7. RINGKASAN & REKAPITULASI (Hanya Admin)
# ==========================================
else:
  st.header("📊 Ringkasan Analisis Data W-SIGNAL")

  if st.button("🔄 Segarkan Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

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
