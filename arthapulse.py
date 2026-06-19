import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ─── KONFIGURASI HALAMAN ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="ArthaPulse — Dashboard Finansial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Font & Warna Dasar */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header Utama */
    .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.5px;
        margin-bottom: 0;
    }
    .main-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 4px;
        margin-bottom: 1.5rem;
    }

    /* Kartu Sinyal */
    .signal-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 20px 24px;
        color: white;
        margin-bottom: 12px;
    }
    .signal-card .signal-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; }
    .signal-card .signal-value { font-size: 1.9rem; font-weight: 700; font-family: 'Space Grotesk', sans-serif; }
    .signal-card .signal-delta-positive { color: #4ade80; font-size: 0.9rem; font-weight: 600; }
    .signal-card .signal-delta-negative { color: #f87171; font-size: 0.9rem; font-weight: 600; }

    /* Badge Indikator Teknikal */
    .badge-bullish { background: #dcfce7; color: #166534; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
    .badge-bearish { background: #fee2e2; color: #991b1b; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
    .badge-neutral { background: #fef9c3; color: #854d0e; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }

    /* Tabel Ringkasan */
    .summary-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.88rem; }
    .summary-label { color: #64748b; }
    .summary-value { font-weight: 600; color: #0f172a; }

    /* Section Divider */
    .section-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #94a3b8;
        margin: 1.5rem 0 0.5rem 0;
    }

    /* Penyesuaian Sidebar */
    [data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Sembunyikan elemen default Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Metric override */
    [data-testid="metric-container"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
    }
</style>
""", unsafe_allow_html=True)


# ─── FUNGSI UTILITAS ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache 5 menit, otomatis refresh
def load_financial_data(ticker_symbol: str, time_period: str) -> pd.DataFrame:
    """Ambil data historis dari Yahoo Finance."""
    try:
        df = yf.Ticker(ticker_symbol).history(period=time_period)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def hitung_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Hitung Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def hitung_bollinger(series: pd.Series, period: int = 20) -> tuple:
    """Hitung Bollinger Bands."""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return sma + 2 * std, sma, sma - 2 * std


def hitung_macd(series: pd.Series) -> tuple:
    """Hitung MACD dan sinyal."""
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal


def format_idr(angka: float) -> str:
    """Format angka ke format Rupiah."""
    if angka >= 1_000_000_000_000:
        return f"Rp {angka/1_000_000_000_000:.2f}T"
    elif angka >= 1_000_000_000:
        return f"Rp {angka/1_000_000_000:.2f}M"
    else:
        return f"Rp {angka:,.0f}"


def sinyal_teknikal(df: pd.DataFrame) -> dict:
    """Hasilkan ringkasan sinyal teknikal."""
    close = df['Close']
    rsi = hitung_rsi(close).iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    macd, signal = hitung_macd(close)
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]

    tren = "Bullish" if ma20 > ma50 else "Bearish"
    rsi_status = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Normal")
    macd_status = "Bullish" if macd_val > signal_val else "Bearish"

    return {
        "RSI": round(rsi, 2),
        "RSI Status": rsi_status,
        "MA20": round(ma20, 2),
        "MA50": round(ma50, 2),
        "Tren MA": tren,
        "MACD": round(macd_val, 4),
        "MACD Status": macd_status,
    }


def warna_badge(status: str) -> str:
    if status in ("Bullish", "Oversold"):
        return "badge-bullish"
    elif status in ("Bearish", "Overbought"):
        return "badge-bearish"
    return "badge-neutral"


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="main-title" style="font-size:1.4rem;">📊 ArthaPulse</p>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Panel Kendali Analisis</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("**⏱ Periode Data**")
    periode = st.selectbox(
        label="Periode",
        options=["1mo", "3mo", "6mo", "1y", "2y"],
        index=1,
        format_func=lambda x: {"1mo": "1 Bulan", "3mo": "3 Bulan", "6mo": "6 Bulan", "1y": "1 Tahun", "2y": "2 Tahun"}[x],
        label_visibility="collapsed"
    )

    st.markdown("**📋 Tampilan**")
    tampilkan_bb = st.toggle("Bollinger Bands", value=True)
    tampilkan_ma = st.toggle("Moving Average (MA20 & MA50)", value=True)
    tampilkan_rsi = st.toggle("Panel RSI", value=True)
    tampilkan_macd = st.toggle("Panel MACD", value=False)

    st.divider()
    st.markdown("**🏦 Pilih Saham IDX**")
    daftar_saham = {
        "BBCA.JK": "BCA", "BBRI.JK": "BRI", "BMRI.JK": "Mandiri",
        "BBNI.JK": "BNI", "TLKM.JK": "Telkom", "ASII.JK": "Astra",
        "GOTO.JK": "GoTo", "UNVR.JK": "Unilever", "ADRO.JK": "Adaro",
        "PGAS.JK": "PGN", "ANTM.JK": "Antam", "MDKA.JK": "Merdeka Copper",
    }
    saham_pilihan = st.multiselect(
        label="Saham",
        options=list(daftar_saham.keys()),
        default=["BBCA.JK", "BBRI.JK", "TLKM.JK"],
        format_func=lambda x: f"{daftar_saham[x]} ({x})",
        label_visibility="collapsed"
    )

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Data bersumber dari Yahoo Finance. Diperbarui setiap 5 menit.")


# ─── HEADER UTAMA ─────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-title">📊 ArthaPulse</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Analisis Real-Time USD/IDR · IHSG · Saham Pilihan — Pasar Indonesia</p>', unsafe_allow_html=True)

# ─── AMBIL DATA UTAMA ─────────────────────────────────────────────────────────
with st.spinner("Memuat data pasar..."):
    data_usd = load_financial_data("IDR=X", periode)
    data_ihsg = load_financial_data("^JKSE", periode)

if data_usd.empty or data_ihsg.empty:
    st.error("⚠️ Gagal memuat data. Periksa koneksi internet atau coba lagi dalam beberapa saat.")
    st.stop()

# ─── SEKSI 1: RINGKASAN PASAR (KARTU ATAS) ────────────────────────────────────
st.markdown('<p class="section-label">📡 Ringkasan Pasar Hari Ini</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

usd_kini = data_usd['Close'].iloc[-1]
usd_lalu = data_usd['Close'].iloc[-2]
delta_usd = usd_kini - usd_lalu
pct_usd = (delta_usd / usd_lalu) * 100

ihsg_kini = data_ihsg['Close'].iloc[-1]
ihsg_lalu = data_ihsg['Close'].iloc[-2]
delta_ihsg = ihsg_kini - ihsg_lalu
pct_ihsg = (delta_ihsg / ihsg_lalu) * 100

ihsg_high = data_ihsg['High'].iloc[-1]
ihsg_low = data_ihsg['Low'].iloc[-1]
ihsg_vol = data_ihsg['Volume'].iloc[-1] if 'Volume' in data_ihsg.columns else 0

with col1:
    tanda = "▲" if delta_usd > 0 else "▼"
    kelas = "signal-delta-negative" if delta_usd > 0 else "signal-delta-positive"  # IDR melemah = negatif
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
    usd_high = data_usd['High'].max()
    usd_low = data_usd['Low'].min()
    
    # Solusi: Pindahkan kamus teks ke variabel luar untuk menghindari bentrokan f-string
    periode_label = {"1mo": "1 Bln", "3mo": "3 Bln", "6mo": "6 Bln", "1y": "1 Thn", "2y": "2 Thn"}.get(periode, periode)
    
    st.markdown(f"""
    <div class="signal-card">
        <div class="signal-label">USD/IDR — Range {periode_label}</div>
        <div class="signal-value" style="font-size:1.3rem;">Rp {usd_low:,.0f}</div>
        <div class="signal-delta-positive">Terkuat ↑ Rp {usd_high:,.0f}</div>
    </div>""", unsafe_allow_html=True)

# ─── SEKSI 2: GRAFIK USD/IDR DAN IHSG BERDAMPINGAN ───────────────────────────
st.markdown('<p class="section-label">📈 Grafik Pergerakan Harga</p>', unsafe_allow_html=True)

tab_usd_chart, tab_ihsg_chart = st.tabs(["💵 USD / IDR", "📊 IHSG"])

with tab_usd_chart:
    col_grafik, col_analisis = st.columns([2, 1])

    with col_grafik:
        df_usd_plot = pd.DataFrame({"Harga (IDR)": data_usd['Close']})
        if tampilkan_ma:
            df_usd_plot['MA20'] = data_usd['Close'].rolling(20).mean()
            df_usd_plot['MA50'] = data_usd['Close'].rolling(50).mean()
        if tampilkan_bb:
            bb_up, bb_mid, bb_low = hitung_bollinger(data_usd['Close'])
            df_usd_plot['BB Atas'] = bb_up
            df_usd_plot['BB Bawah'] = bb_low
        st.line_chart(df_usd_plot.dropna(), height=320, color=["#29b5e8", "#f59e0b", "#10b981", "#ef4444", "#6366f1"])

        if tampilkan_rsi:
            rsi_usd = hitung_rsi(data_usd['Close'])
            df_rsi = pd.DataFrame({"RSI": rsi_usd})
            st.caption("Indikator RSI (14 periode) — Overbought >70 | Oversold <30")
            st.line_chart(df_rsi.dropna(), height=120, color=["#a855f7"])

        if tampilkan_macd:
            macd, signal = hitung_macd(data_usd['Close'])
            df_macd = pd.DataFrame({"MACD": macd, "Signal": signal})
            st.caption("Indikator MACD")
            st.line_chart(df_macd.dropna(), height=120, color=["#3b82f6", "#f97316"])

    with col_analisis:
        sinyal = sinyal_teknikal(data_usd)
        st.markdown("**🔍 Analisis Teknikal USD/IDR**")
        st.markdown(f"""
        <div style="background:#f8fafc;border-radius:12px;padding:16px;border:1px solid #e2e8f0;">
            <div class="summary-row"><span class="summary-label">RSI (14)</span><span class="summary-value">{sinyal['RSI']} — <span class="{warna_badge(sinyal['RSI Status'])}">{sinyal['RSI Status']}</span></span></div>
            <div class="summary-row"><span class="summary-label">Tren MA</span><span class="summary-value"><span class="{warna_badge(sinyal['Tren MA'])}">{sinyal['Tren MA']}</span></span></div>
            <div class="summary-row"><span class="summary-label">MA 20</span><span class="summary-value">Rp {sinyal['MA20']:,.0f}</span></div>
            <div class="summary-row"><span class="summary-label">MA 50</span><span class="summary-value">Rp {sinyal['MA50']:,.0f}</span></div>
            <div class="summary-row"><span class="summary-label">MACD</span><span class="summary-value"><span class="{warna_badge(sinyal['MACD Status'])}">{sinyal['MACD Status']}</span></span></div>
            <div class="summary-row" style="border-bottom:none;"><span class="summary-label">Volatilitas</span><span class="summary-value">{data_usd['Close'].pct_change().std()*100:.2f}%</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📊 Statistik Periode**")
        st.dataframe(
            pd.DataFrame({
                "": ["Tertinggi", "Terendah", "Rata-rata", "Median", "Std Dev"],
                "Nilai (Rp)": [
                    f"{data_usd['Close'].max():,.0f}",
                    f"{data_usd['Close'].min():,.0f}",
                    f"{data_usd['Close'].mean():,.0f}",
                    f"{data_usd['Close'].median():,.0f}",
                    f"{data_usd['Close'].std():,.0f}",
                ]
            }).set_index(""),
            use_container_width=True,
            height=212
        )

with tab_ihsg_chart:
    col_grafik2, col_analisis2 = st.columns([2, 1])

    with col_grafik2:
        df_ihsg_plot = pd.DataFrame({"IHSG": data_ihsg['Close']})
        if tampilkan_ma:
            df_ihsg_plot['MA20'] = data_ihsg['Close'].rolling(20).mean()
            df_ihsg_plot['MA50'] = data_ihsg['Close'].rolling(50).mean()
        if tampilkan_bb:
            bb_up, bb_mid, bb_low = hitung_bollinger(data_ihsg['Close'])
            df_ihsg_plot['BB Atas'] = bb_up
            df_ihsg_plot['BB Bawah'] = bb_low
        st.line_chart(df_ihsg_plot.dropna(), height=320, color=["#29e889", "#f59e0b", "#10b981", "#ef4444", "#6366f1"])

        if tampilkan_rsi:
            rsi_ihsg = hitung_rsi(data_ihsg['Close'])
            df_rsi_ihsg = pd.DataFrame({"RSI": rsi_ihsg})
            st.caption("Indikator RSI (14 periode)")
            st.line_chart(df_rsi_ihsg.dropna(), height=120, color=["#a855f7"])

        if tampilkan_macd:
            macd_i, signal_i = hitung_macd(data_ihsg['Close'])
            df_macd_i = pd.DataFrame({"MACD": macd_i, "Signal": signal_i})
            st.caption("Indikator MACD")
            st.line_chart(df_macd_i.dropna(), height=120, color=["#3b82f6", "#f97316"])

    with col_analisis2:
        sinyal_i = sinyal_teknikal(data_ihsg)
        st.markdown("**🔍 Analisis Teknikal IHSG**")
        st.markdown(f"""
        <div style="background:#f8fafc;border-radius:12px;padding:16px;border:1px solid #e2e8f0;">
            <div class="summary-row"><span class="summary-label">RSI (14)</span><span class="summary-value">{sinyal_i['RSI']} — <span class="{warna_badge(sinyal_i['RSI Status'])}">{sinyal_i['RSI Status']}</span></span></div>
            <div class="summary-row"><span class="summary-label">Tren MA</span><span class="summary-value"><span class="{warna_badge(sinyal_i['Tren MA'])}">{sinyal_i['Tren MA']}</span></span></div>
            <div class="summary-row"><span class="summary-label">MA 20</span><span class="summary-value">{sinyal_i['MA20']:,.2f}</span></div>
            <div class="summary-row"><span class="summary-label">MA 50</span><span class="summary-value">{sinyal_i['MA50']:,.2f}</span></div>
            <div class="summary-row"><span class="summary-label">MACD</span><span class="summary-value"><span class="{warna_badge(sinyal_i['MACD Status'])}">{sinyal_i['MACD Status']}</span></span></div>
            <div class="summary-row" style="border-bottom:none;"><span class="summary-label">Volatilitas</span><span class="summary-value">{data_ihsg['Close'].pct_change().std()*100:.2f}%</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📊 Statistik Periode**")
        st.dataframe(
            pd.DataFrame({
                "": ["Tertinggi", "Terendah", "Rata-rata", "Median", "Std Dev"],
                "Nilai": [
                    f"{data_ihsg['Close'].max():,.2f}",
                    f"{data_ihsg['Close'].min():,.2f}",
                    f"{data_ihsg['Close'].mean():,.2f}",
                    f"{data_ihsg['Close'].median():,.2f}",
                    f"{data_ihsg['Close'].std():,.2f}",
                ]
            }).set_index(""),
            use_container_width=True,
            height=212
        )

# ─── SEKSI 3: ANALISIS SAHAM PILIHAN ──────────────────────────────────────────
st.markdown('<p class="section-label">🏦 Portofolio Saham Pilihan</p>', unsafe_allow_html=True)

if not saham_pilihan:
    st.info("Pilih minimal satu saham di sidebar untuk memulai analisis saham.", icon="ℹ️")
else:
    # Muat semua data saham
    data_saham_dict = {}
    with st.spinner("Memuat data saham..."):
        for ticker in saham_pilihan:
            df = load_financial_data(ticker, periode)
            if not df.empty:
                data_saham_dict[ticker] = df

    if not data_saham_dict:
        st.error("Tidak dapat memuat data saham yang dipilih.")
    else:
        # ── Tabel Ringkasan Saham ──
        ringkasan = []
        for ticker, df in data_saham_dict.items():
            harga_kini = df['Close'].iloc[-1]
            harga_lalu = df['Close'].iloc[-2]
            chg = harga_kini - harga_lalu
            pct = (chg / harga_lalu) * 100
            high52 = df['High'].max()
            low52 = df['Low'].min()
            sinyal_s = sinyal_teknikal(df)
            ringkasan.append({
                "Saham": f"{daftar_saham.get(ticker, ticker)} ({ticker.replace('.JK','')})",
                "Harga (Rp)": f"{harga_kini:,.0f}",
                "Perubahan": f"{chg:+,.0f}",
                "% Ubah": f"{pct:+.2f}%",
                "Tertinggi": f"{high52:,.0f}",
                "Terendah": f"{low52:,.0f}",
                "RSI": sinyal_s['RSI'],
                "Tren": sinyal_s['Tren MA'],
                "MACD": sinyal_s['MACD Status'],
            })

        df_ringkasan = pd.DataFrame(ringkasan).set_index("Saham")
        st.dataframe(df_ringkasan, use_container_width=True, height=min(200 + 38 * len(ringkasan), 500))

        # ── Grafik Perbandingan (Normalisasi 100) ──
        st.markdown("<br>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns([3, 1])

        with col_g1:
            tab_nominal, tab_normalized, tab_return = st.tabs(["Harga Absolut", "Performa Relatif (Base=100)", "Return Harian (%)"])

            with tab_nominal:
                df_harga = pd.DataFrame({t: d['Close'] for t, d in data_saham_dict.items()})
                st.line_chart(df_harga, height=300)

            with tab_normalized:
                df_norm = pd.DataFrame({t: (d['Close'] / d['Close'].iloc[0]) * 100 for t, d in data_saham_dict.items()})
                st.caption("Nilai 100 = harga awal periode. Di atas 100 berarti saham naik sejak awal periode.")
                st.line_chart(df_norm, height=300)

            with tab_return:
                df_ret = pd.DataFrame({t: d['Close'].pct_change() * 100 for t, d in data_saham_dict.items()})
                st.caption("Return harian dalam persen (%). Volatilitas tinggi = batang yang lebih tinggi.")
                st.line_chart(df_ret.dropna(), height=300)

        with col_g2:
            st.markdown("**📈 Return Kumulatif**")
            for ticker, df in data_saham_dict.items():
                ret_total = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
                nama = daftar_saham.get(ticker, ticker)
                warna = "#4ade80" if ret_total >= 0 else "#f87171"
                tanda = "▲" if ret_total >= 0 else "▼"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:10px 14px;background:#f8fafc;border-radius:10px;
                            margin-bottom:8px;border:1px solid #e2e8f0;">
                    <span style="font-weight:600;font-size:0.85rem;">{nama}</span>
                    <span style="color:{warna};font-weight:700;font-size:0.9rem;">{tanda} {abs(ret_total):.2f}%</span>
                </div>""", unsafe_allow_html=True)

        # ── Korelasi Antar Saham (jika >1 saham) ──
        if len(data_saham_dict) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🔗 Lihat Matriks Korelasi Antar Saham"):
                df_close = pd.DataFrame({t: d['Close'] for t, d in data_saham_dict.items()})
                df_corr = df_close.pct_change().corr().round(2)
                df_corr.columns = [daftar_saham.get(c, c) for c in df_corr.columns]
                df_corr.index = [daftar_saham.get(i, i) for i in df_corr.index]
                st.caption("Nilai mendekati 1.0 = bergerak searah. Nilai mendekati -1.0 = bergerak berlawanan.")
                st.dataframe(df_corr.style.background_gradient(cmap="RdYlGn", vmin=-1, vmax=1), use_container_width=True)

# ─── SEKSI 4: DATA HISTORIS LENGKAP ───────────────────────────────────────────
st.markdown('<p class="section-label">📋 Data Historis</p>', unsafe_allow_html=True)

with st.expander("Lihat Tabel Data OHLCV Lengkap"):
    tab_h_usd, tab_h_ihsg, tab_h_saham = st.tabs(["USD/IDR", "IHSG", "Saham Pilihan"])

    n_baris = st.number_input("Jumlah baris terakhir:", min_value=5, max_value=250, value=20, step=5)

    with tab_h_usd:
        df_tampil = data_usd[['Open', 'High', 'Low', 'Close', 'Volume']].tail(int(n_baris)).copy()
        df_tampil.index = df_tampil.index.strftime('%d %b %Y')
        st.dataframe(df_tampil.style.format("{:,.2f}"), use_container_width=True)

    with tab_h_ihsg:
        df_tampil2 = data_ihsg[['Open', 'High', 'Low', 'Close', 'Volume']].tail(int(n_baris)).copy()
        df_tampil2.index = df_tampil2.index.strftime('%d %b %Y')
        st.dataframe(df_tampil2.style.format("{:,.2f}"), use_container_width=True)

    with tab_h_saham:
        if saham_pilihan and data_saham_dict:
            saham_terpilih = st.selectbox("Pilih saham:", list(data_saham_dict.keys()),
                                          format_func=lambda x: f"{daftar_saham.get(x, x)} ({x})")
            df_saham_tampil = data_saham_dict[saham_terpilih][['Open', 'High', 'Low', 'Close', 'Volume']].tail(int(n_baris)).copy()
            df_saham_tampil.index = df_saham_tampil.index.strftime('%d %b %Y')
            st.dataframe(df_saham_tampil.style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("Pilih saham di sidebar terlebih dahulu.")

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "📊 **ArthaPulse** — Data bersumber dari Yahoo Finance melalui yfinance. "
    "Informasi ini bukan merupakan rekomendasi investasi. "
    "Selalu lakukan riset mandiri sebelum mengambil keputusan finansial."
)
