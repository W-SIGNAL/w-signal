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


@st.cache_data(ttl=60)
def load_sheet_data(worksheet_name):
  try:
    gc = get_gspread_client()
    sh = gc.open("W-SIGNAL_Database")
    worksheet = sh.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)
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
# 3. FUNGSI EKSPOR KE EXCEL (.XLSX)
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


# ==========================================
# 4. MANAJEMEN AUTENTIKASI / LOGIN
# ==========================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
  st.session_state["user_role"] = ""
  st.session_state["username"] = ""

st.sidebar.title("📟 KONTROL DATA")

if not st.session_state["logged_in"]:
  st.sidebar.subheader("🔒 Login System")
  username_input = st.sidebar.text_input("Username")
  password_input = st.sidebar.text_input("Password", type="password")

  if st.sidebar.button("Login", use_container_width=True):
    if username_input == "NAY" and password_input == "lalanana":
      st.session_state["logged_in"] = True
      st.session_state["user_role"] = "NAY"
      st.session_state["username"] = "NAY (Super Administrator)"
      st.sidebar.success("Login Berhasil!")
      st.rerun()
    elif username_input == "GUEST" and password_input == "12345":
      st.session_state["logged_in"] = True
      st.session_state["user_role"] = "GUEST"
      st.session_state["username"] = "GUEST (Teknisi Lapangan)"
      st.sidebar.success("Login Berhasil!")
      st.rerun()
    else:
      st.sidebar.error("Username atau Password salah!")

  # Tampilan Halaman Utama Sebelum Login
  st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")
  st.warning("🔒 Silakan Login melalui menu di sebelah kiri untuk mengakses aplikasi.")
  st.stop()  # Menghentikan eksekusi kode di bawah jika belum login

# Jika Sudah Login
st.sidebar.markdown(f"**Status:** {st.session_state['username']}")
if st.sidebar.button("Logout / Keluar", use_container_width=True):
  st.session_state["logged_in"] = False
  st.session_state["user_role"] = ""
  st.session_state["username"] = ""
  st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 5. PILIHAN MENU APLIKASI
# ==========================================
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

selected_menu = st.sidebar.radio("Pilih Menu:", menu_options)

st.title("📟 W-SIGNAL (Welas Asih System for Inventory & General Alkes Log)")

# ==========================================
# 6. FORM INPUT & TABEL DATA
# ==========================================
if selected_menu != "Lihat Semua Data & Ringkasan":
  st.header(f"📝 Input Data: {selected_menu}")

  with st.form(key=f"form_{selected_menu}", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      tanggal = st.date_input("Tanggal").strftime("%Y-%m-%d")
      teknisi = st.text_input(
          "Nama Teknisi", value=st.session_state["username"]
      )
      nama_alat = st.text_input("Nama Alat")
      merk = st.text_input("Merk")

    with col2:
      nomor_seri = st.text_input("Nomor Seri / SN")
      ruangan = st.text_input("Ruangan / Lokasi")
      keterangan = st.text_area("Keterangan / Catatan")

    submitted = st.form_submit_button(
        f"Simpan Data {selected_menu}", use_container_width=True
    )

    if submitted:
      if not nama_alat:
        st.warning("Mohon isi minimal Nama Alat!")
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
# 7. RINGKASAN & REKAPITULASI
# ==========================================
else:
  st.header("📊 Ringkasan Analisis Data W-SIGNAL")

  if st.button("🔄 Segarkan Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

  tabs = st.tabs(menu_options[:-1])

  for idx, sheet_name in enumerate(menu_options[:-1]):
    with tabs[idx]:
      st.subheader(f"Rekapitulasi {sheet_name}")
      df_tab = load_sheet_data(sheet_name)

      render_excel_download_button(
          df_tab, filename_prefix=f"Rekap_{sheet_name.replace(' ', '_')}"
      )
      st.dataframe(df_tab, use_container_width=True)
