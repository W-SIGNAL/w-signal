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
# 2. KONEKSI GOOGLE SHEETS VIA SECRETS
# ==========================================
@st.cache_resource
def get_gspread_client():
  scopes = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
  ]
  if "gcp_service_account" in st.secrets:
    secret_dict = dict(st.secrets["gcp_service_account"])
  else:
    st.error(
        "Secrets '[gcp_service_account]' tidak ditemukan di Streamlit Cloud!"
    )
    st.stop()

  creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
  return gspread.authorize(creds)


@st.cache_data(ttl=10)
def load_sheet_data(worksheet_name):
  """Membaca data dari Google Sheets dengan penanganan struktur header ganda."""
  try:
    gc = get_gspread_client()
    sh = gc.open("W-SIGNAL_Database")
    worksheet = sh.worksheet(worksheet_name)
    data = worksheet.get_all_values()
    if not data or len(data) <= 1:
      return pd.DataFrame()

    headers = data[0]
    rows = data[1:]

    # Jika baris pertama data sama persis dengan header (duplikat header), abaikan
    if rows and rows[0] == headers:
      rows = rows[1:]

    return pd.DataFrame(rows, columns=headers)
  except Exception as e:
    return pd.DataFrame()


def save_sheet_data(worksheet_name, new_data_dict):
  try:
    gc = get_gspread_client()
    sh = gc.open("W-SIGNAL_Database")
    try:
      worksheet = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
      worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")

    headers = list(new_data_dict.keys())
    existing_records = worksheet.get_all_records()

    if not existing_records:
      worksheet.append_row(headers)

    row_to_append = [str(new_data_dict.get(h, "")) for h in headers]
    worksheet.append_row(row_to_append)
    st.cache_data.clear()
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
        label=f"📥 Unduh {filename_prefix} (.xlsx)",
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
      "Tanggal",
      "Nama Teknisi",
      "Nama Alat",
      "Merk",
      "Nomor Seri",
      "Ruangan",
      "Keterangan",
  ]
  df_template = pd.DataFrame(columns=columns)
  template_bytes = convert_df_to_excel(
      df_template, sheet_name=sheet_name[:30]
  )
  st.download_button(
      label=f"📄 Unduh Template Excel ({sheet_name})",
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
# 5. DASHBOARD UTAMA & HAK AKSES MENU
# ==========================================
st.sidebar.title("📟 KONTROL DATA")
st.sidebar.markdown(f"**Status Login:** {st.session_state['username']}")
if st.sidebar.button("Logout / Keluar", use_container_width=True):
  st.session_state["logged_in"] = False
  st.session_state["user_role"] = ""
  st.session_state["username"] = ""
  st.rerun()

st.sidebar.markdown("---")

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
  ]
else:  # Untuk GUEST / Teknisi
  menu_options = ["Perbaikan", "Pemeliharaan"]

selected_menu = st.sidebar.radio("Pilih Menu:", menu_options)

st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

# ==========================================
# 6. FORM INPUT & TABEL DATA
# ==========================================
if selected_menu != "Lihat Semua Data & Ringkasan":
  st.header(f"📝 Input Data: {selected_menu}")

  # Fitur Download Template untuk Super Admin (NAY)
  if st.session_state["user_role"] == "NAY":
    with st.expander("📥 Unduh Template Spreadsheet"):
      render_template_download_button(selected_menu)

  default_teknisi_val = "" if st.session_state["user_role"] == "GUEST" else ""

  with st.form(key=f"form_{selected_menu}", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      tanggal = st.date_input("Tanggal").strftime("%Y-%m-%d")
      teknisi = st.text_input(
          "Nama Teknisi",
          value=default_teknisi_val,
          placeholder="Ketik Nama Anda...",
      )
      nama_alat = st.text_input("Nama Alat")
      merk = st.text_input("Merk")

    with col2:
      nomor_seri = st.text_input("Nomor Seri / SN")
      ruangan = st.text_input("Ruangan / Lokasi")
      keterangan = st.text_area("Keterangan / Catatan")

    uploaded_file_name = ""
    if st.session_state["user_role"] == "NAY":
      uploaded_file = st.file_uploader(
          "Upload File / Lampiran (PDF, Image, XLSX)",
          type=["pdf", "png", "jpg", "jpeg", "xlsx"],
      )
      if uploaded_file is not None:
        uploaded_file_name = uploaded_file.name

    submitted = st.form_submit_button(
        f"Simpan Data {selected_menu}", use_container_width=True
    )

    if submitted:
      if not nama_alat:
        st.warning("Mohon isi minimal Nama Alat!")
      elif not teknisi:
        st.warning("Mohon isi Nama Teknisi!")
      else:
        new_row = {
            "Tanggal": tanggal,
            "Nama Teknisi": teknisi,
            "Nama Alat": nama_alat,
            "Merk": merk,
            "Nomor Seri": nomor_seri,
            "Ruangan": ruangan,
            "Keterangan": keterangan,
        }
        if st.session_state["user_role"] == "NAY" and uploaded_file_name:
          new_row["Lampiran"] = uploaded_file_name

        with st.spinner("Menyimpan data ke Cloud Google Sheets..."):
          if save_sheet_data(selected_menu, new_row):
            st.success(
                f"Data {selected_menu} berhasil disimpan ke Google Sheets!"
            )

  st.markdown("---")
  st.subheader(f"📋 Tabel Data Terkini: {selected_menu}")
  df_current = load_sheet_data(selected_menu)

  render_excel_download_button(
      df_current, filename_prefix=f"Rekap_{selected_menu.replace(' ', '_')}"
  )
  st.dataframe(df_current, use_container_width=True)

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

      col_d1, col_d2 = st.columns(2)
      with col_d1:
        render_excel_download_button(
            df_tab, filename_prefix=f"Rekap_{sheet_name.replace(' ', '_')}"
        )
      with col_d2:
        render_template_download_button(sheet_name)

      st.dataframe(df_tab, use_container_width=True)
