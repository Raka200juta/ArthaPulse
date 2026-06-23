"""
ArthaPulse — Dashboard Finansial Indonesia
Versi: 2.1 (Fix Mobile Tooltip)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json
import re
import plotly.graph_objects as go

# ─── KONFIGURASI HALAMAN (harus paling awal) ──────────────────────────────────
st.set_page_config(
    page_title="ArthaPulse — Dashboard Finansial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── INISIALISASI FIREBASE (sekali saja) ──────────────────────────────────────
@st.cache_resource
def init_firebase():
    """Inisialisasi Firebase sekali saja dan kembalikan Firestore client."""
    if not firebase_admin._apps:
        firebase_info = json.loads(st.secrets["firebase_json"])
        cred = credentials.Certificate(firebase_info)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = init_firebase()
except Exception as e:
    st.error(f"⚠️ Gagal menginisialisasi Firebase: {e}")
    st.stop()

FIREBASE_WEB_API_KEY = st.secrets.get("firebase_web_api_key", "AIzaSyAbJ_CRg_VwXcO1Fd4oPSJlvLTRKLOyuRo")

# ─── SESSION STATE INITIALIZATION ─────────────────────────────────────────────
def init_session_state():
    defaults = {
        "user_info": None,
        "user_status": "Free",
        "auth_error": None,
        "auth_success": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.4rem; font-weight: 700;
        color: #0f172a; letter-spacing: -0.5px; margin-bottom: 0;
    }
    .main-subtitle {
        color: #64748b; font-size: 0.95rem;
        margin-top: 4px; margin-bottom: 1.5rem;
    }
    .signal-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px; padding: 20px 24px;
        color: white; margin-bottom: 12px;
    }
    .signal-card .signal-label {
        font-size: 0.75rem; text-transform: uppercase;
        letter-spacing: 1px; color: #94a3b8;
    }
    .signal-card .signal-value {
        font-size: 1.9rem; font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
    }
    .signal-card .signal-delta-positive { color: #4ade80; font-size: 0.9rem; font-weight: 600; }
    .signal-card .signal-delta-negative { color: #f87171; font-size: 0.9rem; font-weight: 600; }

    .badge-bullish  { background: #dcfce7; color: #166534; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
    .badge-bearish  { background: #fee2e2; color: #991b1b; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
    .badge-neutral  { background: #fef9c3; color: #854d0e; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }

    .summary-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.88rem; }
    .summary-label { color: #64748b; }
    .summary-value { font-weight: 600; color: #0f172a; }

    .section-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 2px;
        color: #94a3b8; margin: 1.5rem 0 0.5rem 0;
    }
    .premium-lock {
        background: linear-gradient(135deg, #1e1b4b, #311042);
        border: 1px solid #4c1d95; border-radius: 12px;
        padding: 24px; text-align: center; color: #c084fc;
    }

    [data-testid="stSidebar"] { background: #0f172a; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { font-family: 'Space Grotesk', sans-serif; }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }

    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }

    [data-testid="metric-container"] {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 14px 18px;
    }
</style>
""", unsafe_allow_html=True)


# ─── PLOTLY LAYOUT DEFAULTS ───────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=4, b=0),
    hovermode="x unified",
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)", zeroline=False),
)
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}


# ─── FUNGSI AUTENTIKASI ────────────────────────────────────────────────────────
def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email))


def login_user(email: str, password: str) -> dict | None:
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    try:
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
        data = resp.json()
        if "localId" in data:
            return {"uid": data["localId"], "email": data["email"]}
        error_msg = data.get("error", {}).get("message", "Kesalahan tidak diketahui")
        return {"error": _translate_firebase_error(error_msg)}
    except requests.exceptions.Timeout:
        return {"error": "Koneksi timeout. Coba lagi."}
    except Exception:
        return {"error": "Gagal terhubung ke server autentikasi."}


def register_user(email: str, password: str) -> dict:
    try:
        user = auth.create_user(email=email, password=password)
        db.collection("users").document(user.uid).set({
            "status": "Free",
            "email": email,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        return {"success": True}
    except Exception as e:
        err = str(e)
        if "EMAIL_EXISTS" in err or "email-already-exists" in err:
            return {"success": False, "error": "Email sudah terdaftar. Silakan login."}
        if "WEAK_PASSWORD" in err or "weak-password" in err:
            return {"success": False, "error": "Password terlalu lemah. Gunakan minimal 6 karakter."}
        return {"success": False, "error": f"Pendaftaran gagal: {err}"}


def _translate_firebase_error(msg: str) -> str:
    mapping = {
        "EMAIL_NOT_FOUND": "Email tidak terdaftar.",
        "INVALID_PASSWORD": "Password salah.",
        "INVALID_EMAIL": "Format email tidak valid.",
        "USER_DISABLED": "Akun ini telah dinonaktifkan.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Terlalu banyak percobaan. Coba lagi nanti.",
        "INVALID_LOGIN_CREDENTIALS": "Email atau password salah.",
    }
    for key, val in mapping.items():
        if key in msg:
            return val
    return f"Login gagal: {msg}"


@st.cache_data(ttl=60)
def get_user_status(uid: str) -> str:
    try:
        doc = db.collection("users").document(uid).get()
        return doc.to_dict().get("status", "Free") if doc.exists else "Free"
    except Exception:
        return "Free"


# ─── FUNGSI DATA & INDIKATOR ───────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_financial_data(ticker_symbol: str, time_period: str) -> pd.DataFrame:
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        ticker_data = yf.Ticker(ticker_symbol, session=session)
        df = ticker_data.history(period=time_period)
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def hitung_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def hitung_bollinger(series: pd.Series, period: int = 20) -> tuple:
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return sma + 2 * std, sma, sma - 2 * std


def hitung_macd(series: pd.Series) -> tuple:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def sinyal_teknikal(df: pd.DataFrame) -> dict:
    close = df["Close"]
    rsi = hitung_rsi(close).iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    macd_val, signal_val = hitung_macd(close)

    return {
        "RSI": round(rsi, 2),
        "RSI Status": "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Normal"),
        "MA20": round(ma20, 2),
        "MA50": round(ma50, 2),
        "Tren MA": "Bullish" if ma20 > ma50 else "Bearish",
        "MACD": round(macd_val.iloc[-1], 4),
        "MACD Status": "Bullish" if macd_val.iloc[-1] > signal_val.iloc[-1] else "Bearish",
    }


def warna_badge(status: str) -> str:
    if status in ("Bullish", "Oversold"):
        return "badge-bullish"
    if status in ("Bearish", "Overbought"):
        return "badge-bearish"
    return "badge-neutral"


DAFTAR_SAHAM = {
    "BBCA.JK": "BCA", "BBRI.JK": "BRI", "BMRI.JK": "Mandiri",
    "BBNI.JK": "BNI", "TLKM.JK": "Telkom", "ASII.JK": "Astra",
    "GOTO.JK": "GoTo", "UNVR.JK": "Unilever", "ADRO.JK": "Adaro",
    "PGAS.JK": "PGN", "ANTM.JK": "Antam", "MDKA.JK": "Merdeka Copper",
}

PERIODE_LABEL = {
    "1mo": "1 Bulan", "3mo": "3 Bulan",
    "6mo": "6 Bulan", "1y": "1 Tahun", "2y": "2 Tahun",
}


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="main-title" style="font-size:1.4rem;">📊 ArthaPulse</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle" style="color:#94a3b8;">Panel Kendali Analisis</p>', unsafe_allow_html=True)
    st.divider()

    if st.session_state.user_info is None:
        st.markdown("**🔐 Akses Akun**")
        menu_auth = st.radio("Pilih Aksi", ["Login", "Daftar"], horizontal=True, label_visibility="collapsed")

        auth_email    = st.text_input("Email", placeholder="nama@email.com")
        auth_password = st.text_input("Password", type="password", placeholder="Minimal 6 karakter")

        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
        if st.session_state.auth_success:
            st.success(st.session_state.auth_success)

        if menu_auth == "Login":
            if st.button("Masuk", use_container_width=True, type="primary"):
                st.session_state.auth_error = None
                st.session_state.auth_success = None

                if not auth_email or not auth_password:
                    st.session_state.auth_error = "Email dan password tidak boleh kosong."
                elif not is_valid_email(auth_email):
                    st.session_state.auth_error = "Format email tidak valid."
                else:
                    with st.spinner("Memverifikasi..."):
                        result = login_user(auth_email, auth_password)
                    if result and "uid" in result:
                        st.session_state.user_info   = result["uid"]
                        st.session_state.user_status = get_user_status(result["uid"])
                        st.session_state.auth_error  = None
                        st.rerun()
                    else:
                        st.session_state.auth_error = result.get("error", "Login gagal.") if result else "Login gagal."
                st.rerun()

        else:
            if st.button("Buat Akun", use_container_width=True, type="primary"):
                st.session_state.auth_error   = None
                st.session_state.auth_success = None

                if not auth_email or not auth_password:
                    st.session_state.auth_error = "Email dan password tidak boleh kosong."
                elif not is_valid_email(auth_email):
                    st.session_state.auth_error = "Format email tidak valid."
                elif len(auth_password) < 6:
                    st.session_state.auth_error = "Password minimal 6 karakter."
                else:
                    with st.spinner("Mendaftarkan akun..."):
                        result = register_user(auth_email, auth_password)
                    if result["success"]:
                        st.session_state.auth_success = "✅ Akun berhasil dibuat! Silakan login."
                    else:
                        st.session_state.auth_error = result.get("error", "Pendaftaran gagal.")
                st.rerun()

    else:
        st.session_state.user_status = get_user_status(st.session_state.user_info)
        is_premium = st.session_state.user_status == "Premium"

        if is_premium:
            st.success("✨ Akun Premium Aktif")
        else:
            st.info("Status Akun: Free Member")
            with st.expander("🚀 Upgrade ke Premium"):
                st.markdown("""
                <div style="background:linear-gradient(135deg,#1e1b4b 0%,#311042 100%);
                            padding:20px;border-radius:12px;border:1px solid #4c1d95;text-align:center;">
                    <h4 style="color:#c084fc;margin-top:0;font-family:'Space Grotesk',sans-serif;">PRO PLAN</h4>
                    <div style="font-size:1.8rem;font-weight:700;color:#f8fafc;margin:10px 0;">
                        Rp 49.000
                        <span style="font-size:0.8rem;color:#94a3b8;font-weight:400;">/ bulan</span>
                    </div>
                    <ul style="text-align:left;color:#cbd5e1;font-size:0.85rem;padding-left:20px;margin-bottom:20px;">
                        <li>Analisis Saham Tanpa Batas (&gt; 2 Saham)</li>
                        <li>Grafik Kinerja Relatif &amp; Return Harian</li>
                        <li>Matriks Korelasi Antar Saham</li>
                        <li>Indikator Makro Lebih Cepat</li>
                    </ul>
                    <a href="https://sociabuzz.com/raka200juta/shop" target="_blank"
                       style="display:block;background:#7c3aed;color:white;text-decoration:none;
                              padding:10px;border-radius:8px;font-weight:600;font-size:0.9rem;">
                        Beli Premium via Sociabuzz
                    </a>
                </div>
                """, unsafe_allow_html=True)

        if st.button("Log Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()

    st.divider()

    st.markdown("**⏱ Periode Data**")
    periode = st.selectbox(
        label="Periode",
        options=list(PERIODE_LABEL.keys()),
        index=1,
        format_func=lambda x: PERIODE_LABEL[x],
        label_visibility="collapsed",
    )

    st.markdown("**📋 Tampilan Indikator**")
    tampilkan_bb   = st.toggle("Bollinger Bands", value=True)
    tampilkan_ma   = st.toggle("Moving Average (MA20 & MA50)", value=True)
    tampilkan_rsi  = st.toggle("Panel RSI", value=True)
    tampilkan_macd = st.toggle("Panel MACD", value=False)

    st.divider()
    st.markdown("**🏦 Pilih Saham IDX**")

    is_premium_user = st.session_state.get("user_status") == "Premium"

    saham_default = ["BBCA.JK", "BBRI.JK", "TLKM.JK"]
    saham_pilihan = st.multiselect(
        label="Saham",
        options=list(DAFTAR_SAHAM.keys()),
        default=saham_default,
        format_func=lambda x: f"{DAFTAR_SAHAM[x]} ({x})",
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Data dari Yahoo Finance. Diperbarui setiap 5 menit.")


# ─── HEADER UTAMA ─────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-title">📊 ArthaPulse</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="main-subtitle">Analisis Real-Time USD/IDR · IHSG · Saham Pilihan — Pasar Indonesia</p>',
    unsafe_allow_html=True
)

# ─── MUAT DATA UTAMA ──────────────────────────────────────────────────────────
with st.spinner("Memuat data pasar..."):
    data_usd  = load_financial_data("IDR=X", periode)
    data_ihsg = load_financial_data("^JKSE", periode)

if data_usd.empty or data_ihsg.empty:
    st.error(
        "⚠️ Gagal memuat data pasar. "
        "Periksa koneksi internet atau coba tekan **Refresh Data** di sidebar."
    )
    st.stop()


# ─── SEKSI 1: RINGKASAN PASAR ─────────────────────────────────────────────────
st.markdown('<p class="section-label">📡 Ringkasan Pasar Hari Ini</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

usd_kini  = data_usd["Close"].iloc[-1]
usd_lalu  = data_usd["Close"].iloc[-2]
delta_usd = usd_kini - usd_lalu
pct_usd   = (delta_usd / usd_lalu) * 100

ihsg_kini  = data_ihsg["Close"].iloc[-1]
ihsg_lalu  = data_ihsg["Close"].iloc[-2]
delta_ihsg = ihsg_kini - ihsg_lalu
pct_ihsg   = (delta_ihsg / ihsg_lalu) * 100

ihsg_high = data_ihsg["High"].iloc[-1]
ihsg_low  = data_ihsg["Low"].iloc[-1]
usd_high  = data_usd["High"].max()
usd_low   = data_usd["Low"].min()

with col1:
    tanda = "▲" if delta_usd > 0 else "▼"
    kelas = "signal-delta-negative" if delta_usd > 0 else "signal-delta-positive"
    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-label">Kurs USD / IDR</div>
        <div class="signal-value">Rp {usd_kini:,.0f}</div>
        <div class="{kelas}">{tanda} {abs(delta_usd):,.0f} ({pct_usd:+.2f}%)</div>
    </div>""", unsafe_allow_html=True)

with col2:
    tanda = "▲" if delta_ihsg > 0 else "▼"
    kelas = "signal-delta-positive" if delta_ihsg > 0 else "signal-delta-negative"
    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-label">IHSG — Jakarta Composite</div>
        <div class="signal-value">{ihsg_kini:,.2f}</div>
        <div class="{kelas}">{tanda} {abs(delta_ihsg):,.2f} ({pct_ihsg:+.2f}%)</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-label">IHSG — Rentang Hari Ini</div>
        <div class="signal-value" style="font-size:1.4rem;">{ihsg_low:,.0f} – {ihsg_high:,.0f}</div>
        <div class="signal-delta-positive">Low → High</div>
    </div>""", unsafe_allow_html=True)

with col4:
    periode_label_short = {"1mo": "1 Bln", "3mo": "3 Bln", "6mo": "6 Bln", "1y": "1 Thn", "2y": "2 Thn"}.get(periode, periode)
    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-label">USD/IDR — Range {periode_label_short}</div>
        <div class="signal-value" style="font-size:1.3rem;">Rp {usd_low:,.0f}</div>
        <div class="signal-delta-positive">Terkuat ↑ Rp {usd_high:,.0f}</div>
    </div>""", unsafe_allow_html=True)


# ─── FUNGSI HELPER: PANEL GRAFIK ──────────────────────────────────────────────
def render_chart_panel(df: pd.DataFrame, label: str, is_idr: bool = False):
    """Render grafik harga + indikator opsional menggunakan Plotly."""
    col_grafik, col_analisis = st.columns([2, 1])

    with col_grafik:
        # ── Grafik Harga Utama ──
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            name=label, line=dict(color="#29b5e8", width=2)
        ))
        if tampilkan_ma:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"].rolling(20).mean(),
                name="MA20", line=dict(color="#f59e0b", width=1.5, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"].rolling(50).mean(),
                name="MA50", line=dict(color="#10b981", width=1.5, dash="dot")
            ))
        if tampilkan_bb:
            bb_up, bb_mid, bb_low = hitung_bollinger(df["Close"])
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_up, name="BB Atas",
                line=dict(color="#ef4444", width=1, dash="dash")
            ))
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_low, name="BB Bawah",
                line=dict(color="#6366f1", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(99,102,241,0.05)"
            ))

        fig.update_layout(
            height=320,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            **PLOTLY_BASE
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Panel RSI ──
        if tampilkan_rsi:
            rsi_s = hitung_rsi(df["Close"])
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=df.index, y=rsi_s,
                name="RSI", line=dict(color="#a855f7", width=2)
            ))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef4444", opacity=0.5)
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="#4ade80", opacity=0.5)
            fig_rsi.update_layout(
                height=120,
                showlegend=False,
                yaxis=dict(showgrid=False, zeroline=False, range=[0, 100]),
                **{k: v for k, v in PLOTLY_BASE.items() if k != "yaxis"}
            )
            st.caption("RSI (14 periode) — Overbought >70 | Oversold <30")
            st.plotly_chart(fig_rsi, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Panel MACD ──
        if tampilkan_macd:
            macd_s, signal_s = hitung_macd(df["Close"])
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(
                x=df.index, y=macd_s,
                name="MACD", line=dict(color="#3b82f6", width=2)
            ))
            fig_macd.add_trace(go.Scatter(
                x=df.index, y=signal_s,
                name="Signal", line=dict(color="#f97316", width=1.5)
            ))
            fig_macd.update_layout(
                height=120,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                **PLOTLY_BASE
            )
            st.caption("MACD (12,26,9)")
            st.plotly_chart(fig_macd, use_container_width=True, config=PLOTLY_CONFIG)

    with col_analisis:
        sinyal = sinyal_teknikal(df)
        harga_fmt = f"Rp {sinyal['MA20']:,.0f}" if is_idr else f"{sinyal['MA20']:,.2f}"
        ma50_fmt  = f"Rp {sinyal['MA50']:,.0f}" if is_idr else f"{sinyal['MA50']:,.2f}"

        st.markdown(f"**🔍 Analisis Teknikal {label}**")
        st.markdown(f"""
        <div style="background:#f8fafc;border-radius:12px;padding:16px;border:1px solid #e2e8f0;">
            <div class="summary-row">
                <span class="summary-label">RSI (14)</span>
                <span class="summary-value">
                    {sinyal['RSI']} —
                    <span class="{warna_badge(sinyal['RSI Status'])}">{sinyal['RSI Status']}</span>
                </span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Tren MA</span>
                <span class="summary-value">
                    <span class="{warna_badge(sinyal['Tren MA'])}">{sinyal['Tren MA']}</span>
                </span>
            </div>
            <div class="summary-row">
                <span class="summary-label">MA 20</span>
                <span class="summary-value">{harga_fmt}</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">MA 50</span>
                <span class="summary-value">{ma50_fmt}</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">MACD</span>
                <span class="summary-value">
                    <span class="{warna_badge(sinyal['MACD Status'])}">{sinyal['MACD Status']}</span>
                </span>
            </div>
            <div class="summary-row" style="border-bottom:none;">
                <span class="summary-label">Volatilitas</span>
                <span class="summary-value">{df['Close'].pct_change().std()*100:.2f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📊 Statistik Periode**")
        fmt = "Rp {:,.0f}" if is_idr else "{:,.2f}"
        st.dataframe(
            pd.DataFrame({
                "": ["Tertinggi", "Terendah", "Rata-rata", "Median", "Std Dev"],
                "Nilai": [
                    fmt.format(df["Close"].max()),
                    fmt.format(df["Close"].min()),
                    fmt.format(df["Close"].mean()),
                    fmt.format(df["Close"].median()),
                    fmt.format(df["Close"].std()),
                ],
            }).set_index(""),
            use_container_width=True,
            height=212,
        )


# ─── SEKSI 2: GRAFIK USD/IDR & IHSG ──────────────────────────────────────────
st.markdown('<p class="section-label">📈 Grafik Pergerakan Harga</p>', unsafe_allow_html=True)

tab_usd_chart, tab_ihsg_chart = st.tabs(["💵 USD / IDR", "📊 IHSG"])

with tab_usd_chart:
    render_chart_panel(data_usd, "Harga (IDR)", is_idr=True)

with tab_ihsg_chart:
    render_chart_panel(data_ihsg, "IHSG", is_idr=False)


# ─── SEKSI 3: ANALISIS SAHAM ──────────────────────────────────────────────────
st.markdown('<p class="section-label">🏦 Portofolio Saham Pilihan</p>', unsafe_allow_html=True)

MAX_FREE_SAHAM = 2
if not is_premium_user and len(saham_pilihan) > MAX_FREE_SAHAM:
    st.warning(
        f"🔒 **Batas Akun Free:** Hanya {MAX_FREE_SAHAM} saham yang dapat dianalisis secara bersamaan. "
        "Upgrade ke **Premium** untuk membuka semua saham.",
        icon="🔒"
    )
    saham_pilihan = saham_pilihan[:MAX_FREE_SAHAM]

if not saham_pilihan:
    st.info("Pilih minimal satu saham di sidebar untuk memulai analisis.", icon="ℹ️")
else:
    data_saham_dict: dict[str, pd.DataFrame] = {}
    tickers_gagal: list[str] = []

    with st.spinner("Memuat data saham..."):
        for ticker in saham_pilihan:
            df = load_financial_data(ticker, periode)
            if not df.empty:
                data_saham_dict[ticker] = df
            else:
                tickers_gagal.append(ticker)

    if tickers_gagal:
        st.warning(f"⚠️ Gagal memuat data untuk: {', '.join(tickers_gagal)}. Data lainnya tetap ditampilkan.")

    if not data_saham_dict:
        st.error("Tidak dapat memuat data saham yang dipilih. Coba refresh.")
    else:
        # ── Tabel Ringkasan ──
        ringkasan = []
        for ticker, df in data_saham_dict.items():
            harga_kini = df["Close"].iloc[-1]
            harga_lalu = df["Close"].iloc[-2]
            chg = harga_kini - harga_lalu
            pct = (chg / harga_lalu) * 100
            sinyal_s = sinyal_teknikal(df)
            ringkasan.append({
                "Saham": f"{DAFTAR_SAHAM.get(ticker, ticker)} ({ticker.replace('.JK', '')})",
                "Harga (Rp)": f"{harga_kini:,.0f}",
                "Perubahan": f"{chg:+,.0f}",
                "% Ubah": f"{pct:+.2f}%",
                "52W High": f"{df['High'].max():,.0f}",
                "52W Low": f"{df['Low'].min():,.0f}",
                "RSI": sinyal_s["RSI"],
                "Tren": sinyal_s["Tren MA"],
                "MACD": sinyal_s["MACD Status"],
            })

        df_ringkasan = pd.DataFrame(ringkasan).set_index("Saham")
        st.dataframe(df_ringkasan, use_container_width=True, height=min(200 + 38 * len(ringkasan), 500))

        # ── Grafik Perbandingan ──
        st.markdown("<br>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns([3, 1])

        with col_g1:
            if is_premium_user:
                tab_nominal, tab_normalized, tab_return = st.tabs([
                    "Harga Absolut", "Performa Relatif (Base=100)", "Return Harian (%)"
                ])

                with tab_nominal:
                    fig_nom = go.Figure()
                    for t, d in data_saham_dict.items():
                        fig_nom.add_trace(go.Scatter(
                            x=d.index, y=d["Close"],
                            name=DAFTAR_SAHAM.get(t, t)
                        ))
                    fig_nom.update_layout(
                        height=300,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        **PLOTLY_BASE
                    )
                    st.plotly_chart(fig_nom, use_container_width=True, config=PLOTLY_CONFIG)

                with tab_normalized:
                    fig_norm = go.Figure()
                    for t, d in data_saham_dict.items():
                        normed = (d["Close"] / d["Close"].iloc[0]) * 100
                        fig_norm.add_trace(go.Scatter(
                            x=d.index, y=normed,
                            name=DAFTAR_SAHAM.get(t, t)
                        ))
                    fig_norm.update_layout(
                        height=300,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        **PLOTLY_BASE
                    )
                    st.caption("Nilai 100 = harga awal periode. Di atas 100 = saham naik.")
                    st.plotly_chart(fig_norm, use_container_width=True, config=PLOTLY_CONFIG)

                with tab_return:
                    fig_ret = go.Figure()
                    for t, d in data_saham_dict.items():
                        ret = d["Close"].pct_change() * 100
                        fig_ret.add_trace(go.Scatter(
                            x=d.index, y=ret,
                            name=DAFTAR_SAHAM.get(t, t)
                        ))
                    fig_ret.update_layout(
                        height=300,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        **PLOTLY_BASE
                    )
                    st.caption("Return harian (%). Volatilitas tinggi = fluktuasi lebih besar.")
                    st.plotly_chart(fig_ret, use_container_width=True, config=PLOTLY_CONFIG)

            else:
                # Tampilkan harga absolut saja untuk Free
                fig_free = go.Figure()
                for t, d in data_saham_dict.items():
                    fig_free.add_trace(go.Scatter(
                        x=d.index, y=d["Close"],
                        name=DAFTAR_SAHAM.get(t, t)
                    ))
                fig_free.update_layout(
                    height=300,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    **PLOTLY_BASE
                )
                st.plotly_chart(fig_free, use_container_width=True, config=PLOTLY_CONFIG)

                st.markdown("""
                <div class="premium-lock" style="margin-top:8px;padding:14px;font-size:0.85rem;">
                    🔒 <b>Grafik Performa Relatif &amp; Return Harian</b> tersedia di akun Premium.
                </div>""", unsafe_allow_html=True)

        with col_g2:
            st.markdown("**📈 Return Kumulatif**")
            for ticker, df in data_saham_dict.items():
                ret_total = ((df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1) * 100
                nama  = DAFTAR_SAHAM.get(ticker, ticker)
                warna = "#4ade80" if ret_total >= 0 else "#f87171"
                tanda = "▲" if ret_total >= 0 else "▼"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:10px 14px;background:#0f172a;border-radius:10px;
                            margin-bottom:8px;border:1px solid #1e293b;">
                    <span style="font-weight:600;font-size:0.85rem;color:#f8fafc;">{nama}</span>
                    <span style="color:{warna};font-weight:700;font-size:0.9rem;">{tanda} {abs(ret_total):.2f}%</span>
                </div>""", unsafe_allow_html=True)

        # ── Matriks Korelasi (Premium only) ──
        if len(data_saham_dict) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            if is_premium_user:
                with st.expander("🔗 Lihat Matriks Korelasi Antar Saham"):
                    df_close = pd.DataFrame({t: d["Close"] for t, d in data_saham_dict.items()})
                    df_corr  = df_close.pct_change().corr().round(2)
                    df_corr.columns = [DAFTAR_SAHAM.get(c, c) for c in df_corr.columns]
                    df_corr.index   = [DAFTAR_SAHAM.get(i, i) for i in df_corr.index]
                    st.caption("Mendekati 1.0 = bergerak searah · Mendekati -1.0 = berlawanan arah")
                    st.dataframe(
                        df_corr.style.background_gradient(cmap="RdYlGn", vmin=-1, vmax=1),
                        use_container_width=True,
                    )
            else:
                st.markdown("""
                <div class="premium-lock">
                    🔒 <b>Matriks Korelasi Antar Saham</b> tersedia untuk akun <b>Premium</b>.<br>
                    <small style="color:#94a3b8;">Upgrade untuk melihat hubungan pergerakan antar saham.</small>
                </div>""", unsafe_allow_html=True)


# ─── SEKSI 4: DATA HISTORIS ───────────────────────────────────────────────────
st.markdown('<p class="section-label">📋 Data Historis</p>', unsafe_allow_html=True)

with st.expander("Lihat Tabel Data OHLCV Lengkap"):
    n_baris = st.number_input(
        "Jumlah baris terakhir:", min_value=5, max_value=250, value=20, step=5
    )
    tab_h_usd, tab_h_ihsg, tab_h_saham = st.tabs(["USD/IDR", "IHSG", "Saham Pilihan"])

    def render_ohlcv(df: pd.DataFrame):
        disp = df[["Open", "High", "Low", "Close", "Volume"]].tail(int(n_baris)).copy()
        disp.index = disp.index.strftime("%d %b %Y")
        st.dataframe(disp.style.format("{:,.2f}"), use_container_width=True)

    with tab_h_usd:
        render_ohlcv(data_usd)

    with tab_h_ihsg:
        render_ohlcv(data_ihsg)

    with tab_h_saham:
        if saham_pilihan and data_saham_dict:
            saham_terpilih = st.selectbox(
                "Pilih saham:",
                list(data_saham_dict.keys()),
                format_func=lambda x: f"{DAFTAR_SAHAM.get(x, x)} ({x})",
            )
            render_ohlcv(data_saham_dict[saham_terpilih])
        else:
            st.info("Pilih saham di sidebar terlebih dahulu.")


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "📊 **ArthaPulse** — Data bersumber dari Yahoo Finance melalui yfinance. "
    "Informasi ini **bukan** rekomendasi investasi. "
    "Lakukan riset mandiri sebelum mengambil keputusan finansial."
)