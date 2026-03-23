"""
HF System — Privates Hedgefonds Dashboard v2.0
Helles Design, Champions als CSV-Upload, Namen sichtbar
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import io

# ═══════════════════════════════════════════════════════
# CORE PORTFOLIO — FEST DEFINIERT
# ═══════════════════════════════════════════════════════

CORE_POSITIONEN = [
    {'ticker': 'NVDA',  'name': 'NVIDIA',            'sektor': 'Tech/KI',    'score': 100},
    {'ticker': 'APH',   'name': 'Amphenol',           'sektor': 'Tech/KI',    'score': 98},
    {'ticker': 'AVGO',  'name': 'Broadcom',           'sektor': 'Halbleiter', 'score': 96},
    {'ticker': 'WMT',   'name': 'Walmart',            'sektor': 'Consumer',   'score': 94},
    {'ticker': 'TT',    'name': 'Trane Technologies', 'sektor': 'Industrie',  'score': 90},
    {'ticker': 'MSFT',  'name': 'Microsoft',          'sektor': 'Tech/KI',    'score': 88},
    {'ticker': 'LLY',   'name': 'Eli Lilly',          'sektor': 'Healthcare', 'score': 87},
    {'ticker': 'MA',    'name': 'Mastercard',         'sektor': 'Payments',   'score': 86},
    {'ticker': 'CTAS',  'name': 'Cintas',             'sektor': 'Services',   'score': 85},
    {'ticker': 'FICO',  'name': 'FICO',               'sektor': 'Fintech',    'score': 82},
]

# ═══════════════════════════════════════════════════════
# SEITEN-KONFIGURATION
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="HF System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* Helles, neutrales Design */
.stApp {
    background-color: #f8f9fb;
    font-family: 'Inter', sans-serif;
}
.main .block-container {
    padding: 1.5rem 2rem;
    max-width: 1400px;
}

/* Metriken */
[data-testid="stMetricValue"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: #1a202c !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    color: #718096 !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: #ffffff;
    border-bottom: 2px solid #e2e8f0;
    gap: 2px;
    border-radius: 8px 8px 0 0;
    padding: 0 8px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.02em;
    color: #718096;
    background: transparent;
    border: none;
    padding: 14px 18px;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
    background: transparent !important;
}

/* Buttons */
.stButton > button {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.82rem;
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    background: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
}

/* Trennlinien */
hr { border-color: #e2e8f0; margin: 16px 0; }

/* Dataframe */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

/* Upload */
.stFileUploader {
    background: #ffffff;
    border-radius: 8px;
    border: 2px dashed #cbd5e0;
    padding: 8px;
}

/* Expander */
.streamlit-expanderHeader {
    background: #ffffff !important;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    font-weight: 600 !important;
    color: #2d3748 !important;
}

/* Checkboxen */
.stCheckbox label {
    font-size: 0.85rem !important;
    color: #2d3748 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
}

/* Progress bar */
.stProgress > div > div {
    background: #2563eb !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# HILFSFUNKTIONEN — KARTEN & BADGES
# ═══════════════════════════════════════════════════════

def card(content: str, border_left: str = "#2563eb", bg: str = "#ffffff"):
    st.markdown(
        f'<div style="background:{bg};border:1px solid #e2e8f0;border-left:4px solid {border_left};'
        f'border-radius:8px;padding:16px 20px;margin-bottom:12px">{content}</div>',
        unsafe_allow_html=True
    )

def badge(text: str, color: str = "#2563eb", bg: str = "#eff6ff"):
    return (
        f'<span style="background:{bg};color:{color};font-size:0.68rem;font-weight:600;'
        f'padding:3px 8px;border-radius:4px;font-family:Inter,sans-serif">{text}</span>'
    )

def status_row(label: str, value: str, delta: str = "", color: str = "#2563eb"):
    return (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:10px 0;border-bottom:1px solid #f1f5f9">'
        f'<span style="font-size:0.85rem;color:#4a5568;font-weight:500">{label}</span>'
        f'<span style="font-family:DM Mono,monospace;font-size:0.85rem;font-weight:600;color:{color}">'
        f'{value} <span style="font-size:0.72rem;color:#718096">{delta}</span></span>'
        f'</div>'
    )

# ═══════════════════════════════════════════════════════
# DATEN — YAHOO FINANCE
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_vix():
    try:
        import yfinance as yf
        v = yf.Ticker("^VIX").history(period="2d")
        return round(float(v['Close'].iloc[-1]), 2) if not v.empty else None
    except:
        return None

@st.cache_data(ttl=3600)
def get_price(ticker):
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period="2d")
        return round(float(h['Close'].iloc[-1]), 2) if not h.empty else None
    except:
        return None

@st.cache_data(ttl=86400)
def get_daily(ticker, years=2):
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=years*365)
        h = yf.Ticker(ticker).history(start=start, end=end)
        if h.empty:
            return pd.DataFrame()
        h.index = pd.to_datetime(h.index).tz_localize(None)
        return h[['Close','Volume']].dropna()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_monthly(ticker, years=11):
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=years*365)
        h = yf.Ticker(ticker).history(start=start, end=end, interval="1mo")
        if h.empty:
            return pd.DataFrame()
        h.index = pd.to_datetime(h.index).tz_localize(None)
        return h[['Close']].dropna()
    except:
        return pd.DataFrame()

# ═══════════════════════════════════════════════════════
# CHAMPIONS CSV LADEN
# ═══════════════════════════════════════════════════════

def load_champions(uploaded_file=None):
    """Champions aus hochgeladener CSV oder Session State laden."""
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state['champions_df'] = df
        return df
    elif 'champions_df' in st.session_state:
        return st.session_state['champions_df']
    else:
        return pd.DataFrame()

# ═══════════════════════════════════════════════════════
# CHAMPIONS SCORE — POTENZFORMEL
# ═══════════════════════════════════════════════════════

def calc_geopak(close):
    if len(close) < 24:
        return None
    anfang = close.head(12).mean()
    ende = close.iloc[-1]
    if anfang <= 0:
        return None
    return round(((ende/anfang)**(1/(len(close)/12)) - 1)*100, 2)

def calc_konstanz(close):
    if len(close) < 24:
        return None
    ret = close.tail(120).pct_change().dropna()
    return round((ret > 0).sum()/len(ret)*100, 1) if len(ret) >= 12 else None

def calc_verlust(close):
    if len(close) < 24:
        return None
    ret = close.tail(120).pct_change().dropna()
    if len(ret) < 12:
        return None
    n = len(ret)
    fak = np.arange(1, n+1)
    v = ret[ret < 0]
    if len(v) == 0:
        return 0.5
    idx = [ret.index.get_loc(i) for i in v.index]
    vf = fak[idx]
    gew = np.sum(np.abs(v.values)*vf)/np.sum(vf)
    return round((len(v)/n)*gew*100, 2)

def calc_score(g, k, v):
    if any(x is None for x in [g, k, v]):
        return None
    if g <= 0 or k <= 0:
        return None
    vr = max(v, 0.5)
    return round((g**0.95)*((1/vr)**1.2)*((k/100)**1.5), 4)

@st.cache_data(ttl=86400)
def score_ticker(ticker):
    m = get_monthly(ticker)
    if m.empty or len(m) < 24:
        return None, None, None, None
    c = m['Close']
    g = calc_geopak(c)
    k = calc_konstanz(c)
    v = calc_verlust(c)
    return g, k, v, calc_score(g, k, v)

# ═══════════════════════════════════════════════════════
# OSZILLATOR
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def calc_oszillator(tickers):
    ueber, gesamt, details = 0, 0, []
    for t in tickers:
        try:
            h = get_daily(t)
            if h.empty or len(h) < 30:
                continue
            k = h['Close'].iloc[-1]
            gd = h['Close'].tail(200).mean() if len(h) >= 200 else h['Close'].mean()
            ab = k > gd
            if ab:
                ueber += 1
            gesamt += 1
            details.append({
                'Ticker': t,
                'Kurs': round(k, 2),
                'GD200': round(gd, 2),
                'Abstand %': round(((k-gd)/gd)*100, 1),
                'Status': '✅ Über GD200' if ab else '❌ Unter GD200'
            })
        except:
            continue
    wert = round(ueber/gesamt*100, 1) if gesamt > 0 else None
    return wert, ueber, gesamt, pd.DataFrame(details)

def vix_pos(vix):
    if vix is None: return 5
    if vix < 25:    return 5
    if vix < 30:    return 3
    if vix < 40:    return 1
    return 0

def ampel(vix, osc):
    vp = vix_pos(vix)
    adj = 0 if osc is None else (0 if osc >= 70 else (-1 if osc >= 40 else -2))
    p = max(0, vp + adj)
    if p >= 4: return p, '#16a34a', '#f0fdf4', '#dcfce7', 'GRÜNES LICHT — Vollgas'
    if p == 3: return p, '#ca8a04', '#fefce8', '#fef9c3', 'GELBES LICHT — Vorsicht'
    if p == 1: return p, '#ea580c', '#fff7ed', '#ffedd5', 'ORANGE — Defensiv'
    return p, '#dc2626', '#fef2f2', '#fee2e2', 'ROTES LICHT — Cash Modus'

# ═══════════════════════════════════════════════════════
# SATELLITEN SCANNER
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=86400)
def scan(ticker):
    try:
        spy = get_daily("SPY", 2)
        h = get_daily(ticker, 2)
        if h.empty or spy.empty or len(h) < 130:
            return None
        k = h['Close'].iloc[-1]
        gd = h['Close'].tail(200).mean() if len(h) >= 200 else h['Close'].mean()
        if k <= gd:
            return None
        if 'Volume' in h.columns and h['Volume'].tail(60).mean() < 4_000_000:
            return None
        ar = h['Close'].iloc[-1]/h['Close'].iloc[-130] - 1
        sr = spy['Close'].iloc[-1]/spy['Close'].iloc[-130] - 1
        if ar <= sr:
            return None
        hoch = h['Close'].tail(252).max() if len(h) >= 252 else h['Close'].max()
        if ((k-hoch)/hoch)*100 < -50:
            return None
        lag = 22
        ref = h['Close'].iloc[-lag]
        m260 = round(((ref/h['Close'].iloc[-282])-1)*100, 2) if len(h) >= 282 else None
        m130 = round(((ref/h['Close'].iloc[-152])-1)*100, 2) if len(h) >= 152 else None
        rs = round(ar*100, 2)
        rs_spy = round((ar-sr)*100, 2)
        ret_l = [(h['Close'].iloc[-i]/h['Close'].iloc[-(i+130)]-1)*100 for i in range(130, min(len(h),260))]
        rsz = round((rs-np.mean(ret_l))/np.std(ret_l), 2) if len(ret_l) > 10 else 0
        if m260 and m130:
            comp = round(m260*0.30+m130*0.25+rs*0.25+rsz*10*0.20, 2)
        else:
            return None
        return {
            'Ticker': ticker, 'Kurs': round(k, 2), 'GD200': round(gd, 2),
            'MOM260 %': m260, 'MOM130 %': m130, 'RS Score': rs,
            'RS vs SPY': rs_spy, 'RS z-Score': rsz, 'Score ⭐': comp
        }
    except:
        return None

# ═══════════════════════════════════════════════════════
# JOURNAL
# ═══════════════════════════════════════════════════════

DB = "journal.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT, ticker TEXT, name TEXT, typ TEXT,
        kurs REAL, betrag REAL, begruendung TEXT,
        ausstieg_trigger TEXT, ausstieg_kurs REAL,
        ausstieg_datum TEXT, pnl REAL, notizen TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS checkliste (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT, vix REAL, oszillator REAL,
        positionen INTEGER, notizen TEXT
    )''')
    conn.commit()
    conn.close()

def trade_add(ticker, name, typ, kurs, betrag, grund, trigger):
    init_db()
    conn = sqlite3.connect(DB)
    conn.execute(
        'INSERT INTO trades (datum,ticker,name,typ,kurs,betrag,begruendung,ausstieg_trigger) VALUES (?,?,?,?,?,?,?,?)',
        (datetime.now().strftime('%Y-%m-%d'), ticker.upper(), name, typ, kurs, betrag, grund, trigger)
    )
    conn.commit()
    conn.close()

def trades_load():
    init_db()
    conn = sqlite3.connect(DB)
    df = pd.read_sql('SELECT * FROM trades ORDER BY id DESC', conn)
    conn.close()
    return df

def checklist_save(vix, osc, pos, notizen):
    init_db()
    conn = sqlite3.connect(DB)
    conn.execute(
        'INSERT INTO checkliste (datum,vix,oszillator,positionen,notizen) VALUES (?,?,?,?,?)',
        (datetime.now().strftime('%Y-%m-%d'), vix, osc, pos, notizen)
    )
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════

for k, v in [('depot', 100000.0), ('sparrate', 1000.0)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════

st.markdown(
    '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;'
    'padding:16px 24px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between">'
    '<div>'
    '<span style="font-family:Inter,sans-serif;font-size:1.2rem;font-weight:700;color:#1a202c;letter-spacing:-0.02em">HF · System</span>'
    '<span style="font-size:0.72rem;color:#718096;margin-left:12px">Privates Hedgefonds Dashboard</span>'
    '</div>'
    f'<span style="font-family:DM Mono,monospace;font-size:0.72rem;color:#718096">'
    f'{datetime.now().strftime("%d.%m.%Y — %H:%M")}</span>'
    '</div>',
    unsafe_allow_html=True
)

# ═══════════════════════════════════════════════════════
# MARKTDATEN LADEN
# ═══════════════════════════════════════════════════════

vix = get_vix()
vt = f"{vix:.1f}" if vix else "—"
vc = "#16a34a" if vix and vix < 25 else "#ca8a04" if vix and vix < 30 else "#ea580c" if vix and vix < 40 else "#dc2626"

# ═══════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 Dashboard", "🏆 Champions", "📡 Satelliten",
    "💼 Core", "📊 Oszillator", "📋 Checkliste", "📓 Journal"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════

with tab1:
    st.markdown("### Markt-Cockpit")

    # Champions laden für Oszillator
    champions_df = load_champions()
    tickers_list = champions_df['Ticker'].tolist() if not champions_df.empty else []

    if tickers_list:
        with st.spinner("Lade Marktdaten..."):
            osc_wert, osc_u, osc_g, _ = calc_oszillator(tuple(tickers_list))
    else:
        osc_wert, osc_u, osc_g = None, 0, 0

    osc_txt = f"{osc_wert:.1f}%" if osc_wert else "—"
    pos, farbe, bg_hell, bg_leicht, text = ampel(vix, osc_wert)

    # Ampel
    st.markdown(
        f'<div style="background:{bg_hell};border:1px solid {farbe}40;border-left:5px solid {farbe};'
        f'border-radius:10px;padding:20px 24px;margin-bottom:20px">'
        f'<div style="display:flex;align-items:center;gap:16px">'
        f'<span style="font-size:2.2rem">{"🟢" if pos>=4 else "🟡" if pos==3 else "🟠" if pos==1 else "🔴"}</span>'
        f'<div>'
        f'<div style="font-family:Inter,sans-serif;font-size:1.1rem;font-weight:700;color:{farbe}">{text}</div>'
        f'<div style="font-size:0.82rem;color:#4a5568;margin-top:4px">'
        f'<b style="color:{farbe}">{pos} Satelliten-Positionen</b> erlaubt &nbsp;·&nbsp; '
        f'VIX: <b>{vt}</b> &nbsp;·&nbsp; Oszillator: <b>{osc_txt}</b>'
        f'</div></div></div></div>',
        unsafe_allow_html=True
    )

    # Metriken
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("VIX", vt, "Volatilität")
    m2.metric("Oszillator", osc_txt, f"{osc_u}/{osc_g} über GD200")
    m3.metric("Satelliten max.", str(pos), "VIX-gesteuert")
    m4.metric("Core", "60%", "10 Compounder")
    m5.metric("Crypto / Gold", "9% / 5%", "BTC+ETH / Hedge")

    st.markdown("---")

    col_links, col_rechts = st.columns(2)

    with col_links:
        st.markdown("**VIX Regelwerk**")
        for label, p, f, aktiv in [
            ("VIX < 25",  5, "#16a34a", vix and vix < 25),
            ("VIX 25–30", 3, "#ca8a04", vix and 25 <= vix < 30),
            ("VIX 30–40", 1, "#ea580c", vix and 30 <= vix < 40),
            ("VIX > 40",  0, "#dc2626", vix and vix >= 40),
        ]:
            bg = f"{f}12" if aktiv else "#ffffff"
            bd = f if aktiv else "#e2e8f0"
            tag = f' <span style="color:{f};font-size:0.65rem;font-weight:600">◀ AKTIV</span>' if aktiv else ''
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
                f'padding:10px 16px;margin-bottom:6px;display:flex;align-items:center;gap:16px">'
                f'<span style="font-family:DM Mono,monospace;font-size:0.82rem;color:{f};font-weight:500;width:90px">{label}</span>'
                f'<span style="font-size:1.1rem;font-weight:700;color:{f};width:25px">{p}</span>'
                f'<span style="font-size:0.78rem;color:#718096">Positionen{tag}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    with col_rechts:
        st.markdown("**Allokation**")
        for name, pct, f in [
            ("Core Portfolio", 60, "#2563eb"),
            ("Satelliten",     25, "#ca8a04"),
            ("Crypto",          9, "#7c3aed"),
            ("Gold",            5, "#b45309"),
            ("Altlasten",       1, "#9ca3af"),
        ]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
                f'<span style="font-size:0.78rem;color:#4a5568;width:120px">{name}</span>'
                f'<div style="flex:1;height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{f};border-radius:4px"></div></div>'
                f'<span style="font-size:0.82rem;font-weight:600;color:{f};width:32px;text-align:right">{pct}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    if not tickers_list:
        st.info("💡 Bitte laden Sie Ihre Champions-CSV im Tab **🏆 Champions** hoch um den Oszillator zu aktivieren.")

# ═══════════════════════════════════════════════════════
# TAB 2 — CHAMPIONS
# ═══════════════════════════════════════════════════════

with tab2:
    st.markdown("### Champions Pool")

    # CSV Upload
    st.markdown(
        '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:16px">'
        '<b style="color:#1d4ed8">Champions-CSV hochladen</b><br>'
        '<span style="font-size:0.8rem;color:#3730a3">Format: Spalten <code>Name</code>, <code>WKN</code>, <code>Ticker</code> — '
        'eine Zeile pro Champion. Wird automatisch für Oszillator und Score-Berechnung verwendet.</span>'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_champ = st.file_uploader(
        "Champions CSV hochladen",
        type=['csv'],
        key="champ_upload",
        label_visibility="collapsed"
    )

    champions_df = load_champions(uploaded_champ)

    if champions_df.empty:
        st.warning("⚠️ Noch keine Champions-CSV hochgeladen. Bitte laden Sie Ihre Datei hoch.")
        st.markdown(
            "**Erwartetes Format:**\n```\nName,WKN,Ticker\nNVIDIA,918422,NVDA\nMastercard,A0F602,MA\n...\n```"
        )
    else:
        # Champions-Tabelle mit Namen
        st.success(f"✅ {len(champions_df)} Champions geladen")

        # Spalten sicherstellen
        cols_show = [c for c in ['Name', 'WKN', 'Ticker'] if c in champions_df.columns]
        st.dataframe(
            champions_df[cols_show],
            use_container_width=True,
            height=380,
            hide_index=True
        )

        st.markdown("---")
        st.markdown("### Potenzformel")
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #2563eb;'
            'border-radius:8px;padding:12px 16px;font-family:DM Mono,monospace;font-size:0.88rem;'
            'color:#1e40af;margin-bottom:16px">'
            'GeoPAK10^0.95 × (1 / max(Verlust-Ratio, 0.5))^1.2 × (Gewinnkonstanz / 100)^1.5'
            '</div>',
            unsafe_allow_html=True
        )

        col_e, col_a = st.columns([1, 2])

        with col_e:
            st.markdown("**Einzelberechnung**")
            # Ticker + Name Auswahl aus Champions
            if 'Ticker' in champions_df.columns and 'Name' in champions_df.columns:
                optionen = [f"{row['Ticker']} — {row['Name']}" for _, row in champions_df.iterrows()]
                auswahl = st.selectbox("Champion auswählen", optionen, key="score_select")
                ticker_sel = auswahl.split(" — ")[0] if auswahl else ""
            else:
                ticker_sel = st.text_input("Ticker eingeben", placeholder="z.B. NVDA", key="score_input")

            if st.button("Score berechnen", key="btn_score"):
                if ticker_sel:
                    with st.spinner(f"Berechne {ticker_sel}..."):
                        g, k, v, s = score_ticker(ticker_sel)
                    if s:
                        st.markdown(
                            f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px">'
                            f'<div style="font-size:1.4rem;font-weight:700;color:#16a34a">Score: {s:.4f}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        sa, sb, sc = st.columns(3)
                        sa.metric("GeoPAK10", f"{g:.1f}%" if g else "—")
                        sb.metric("Konstanz", f"{k:.1f}%" if k else "—")
                        sc.metric("Verlust-Ratio", f"{v:.2f}" if v else "—")
                    else:
                        st.error("Nicht genug Daten verfügbar.")

        with col_a:
            st.markdown("**Alle Champions berechnen**")
            st.caption("Dauert 3–5 Minuten — Kurse werden von Yahoo Finance geladen.")
            if st.button("🚀 Alle berechnen", key="btn_all"):
                results = []
                prog = st.progress(0)
                status_ph = st.empty()
                tickers_all = champions_df['Ticker'].tolist() if 'Ticker' in champions_df.columns else []

                for i, row in champions_df.iterrows():
                    ticker = row.get('Ticker', '')
                    name = row.get('Name', ticker)
                    prog.progress((i+1)/len(champions_df))
                    status_ph.caption(f"Berechne {name} ({ticker})...")
                    g, k, v, s = score_ticker(ticker)
                    if s:
                        results.append({
                            'Rang': len(results)+1,
                            'Name': name,
                            'Ticker': ticker,
                            'GeoPAK10 (%)': g,
                            'Konstanz (%)': k,
                            'Verlust-Ratio': v,
                            'Score': s
                        })

                prog.empty()
                status_ph.empty()

                if results:
                    res_df = pd.DataFrame(results).sort_values('Score', ascending=False).reset_index(drop=True)
                    res_df['Rang'] = res_df.index + 1
                    st.success(f"✅ {len(res_df)} Champions berechnet — sortiert nach Score")
                    st.dataframe(res_df, use_container_width=True, height=500, hide_index=True)

# ═══════════════════════════════════════════════════════
# TAB 3 — SATELLITEN
# ═══════════════════════════════════════════════════════

with tab3:
    st.markdown("### Satelliten-Scanner")

    sa1, sa2, sa3, sa4 = st.columns(4)
    sa1.metric("Universum", "3.065", "Aktien gescreent")
    sa2.metric("Max. Positionen", str(pos), "VIX-gesteuert")
    sa3.metric("Einstieg", "€ 2.500", "Fix je Position")
    sa4.metric("Rhythmus", "Wöchentlich", "Fester Tag")

    st.markdown("---")

    # Universe Upload
    st.markdown(
        '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
        'padding:12px 16px;margin-bottom:12px">'
        '<b style="color:#15803d">Aktien-Universum hochladen</b><br>'
        '<span style="font-size:0.78rem;color:#166534">CSV mit Spalten <code>Ticker</code> und optional <code>Name</code>, <code>Sektor</code></span>'
        '</div>',
        unsafe_allow_html=True
    )

    uni_upload = st.file_uploader("Universe CSV", type=['csv'], key="uni_up", label_visibility="collapsed")

    if uni_upload:
        uni_df = pd.read_csv(uni_upload)
        if 'Ticker' in uni_df.columns:
            uni_tickers = uni_df['Ticker'].dropna().tolist()
            # Name-Mapping falls vorhanden
            name_map = {}
            if 'Name' in uni_df.columns:
                name_map = dict(zip(uni_df['Ticker'], uni_df['Name']))

            st.success(f"✅ {len(uni_tickers)} Aktien geladen")

            if st.button("🔍 Scanner starten", key="btn_scan"):
                results = []
                prog2 = st.progress(0)
                status2 = st.empty()
                limit = min(len(uni_tickers), 500)

                for i, t in enumerate(uni_tickers[:limit]):
                    prog2.progress((i+1)/limit)
                    name = name_map.get(t, t)
                    status2.caption(f"Scanne {name} ({t})... {i+1}/{limit}")
                    r = scan(t)
                    if r:
                        r['Name'] = name
                        results.append(r)

                prog2.empty()
                status2.empty()

                if results:
                    scan_df = pd.DataFrame(results)
                    # Name vorne
                    cols = ['Name', 'Ticker', 'Kurs', 'GD200', 'MOM260 %', 'MOM130 %', 'RS Score', 'RS vs SPY', 'RS z-Score', 'Score ⭐']
                    scan_df = scan_df[[c for c in cols if c in scan_df.columns]]
                    scan_df = scan_df.sort_values('Score ⭐', ascending=False).reset_index(drop=True)
                    scan_df.insert(0, '#', scan_df.index + 1)
                    st.success(f"✅ {len(results)} Kandidaten — Top 20 angezeigt")
                    st.dataframe(scan_df.head(20), use_container_width=True, height=500, hide_index=True)
                else:
                    st.warning("Keine Kandidaten nach Filterung gefunden.")
        else:
            st.error("CSV benötigt eine Spalte 'Ticker'")
    else:
        st.info("📁 Bitte laden Sie Ihre universe.csv hoch (Spalte: Ticker, optional: Name, Sektor)")

    st.markdown("---")
    st.markdown("**Ausstiegs-Trigger (2 von 3 = Verkaufen)**")
    for t, d in [
        ("🔴 Top-15-Exit", "Position fällt aus Top 15 des Universums → sofortiger Verkauf"),
        ("🔴 Strukturbruch", "Signal 1: Kurs unter Unterstützung | Signal 2: Kurs unter GD50 | Signal 3: RS -5 Plätze"),
        ("🔴 Notfall -15%", "Position verliert intraweek >15% vom Einstieg → Sofortverkauf ohne Checkliste"),
    ]:
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:7px;'
            f'padding:10px 14px;margin-bottom:6px">'
            f'<b style="font-size:0.82rem">{t}</b>'
            f'<span style="font-size:0.78rem;color:#718096;margin-left:8px">{d}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════
# TAB 4 — CORE
# ═══════════════════════════════════════════════════════

with tab4:
    st.markdown("### Core Portfolio — 10 Compounder")

    d1, d2 = st.columns(2)
    with d1:
        depot = st.number_input("Depot-Gesamtwert (€)", value=st.session_state.depot, step=1000.0, format="%.0f")
        st.session_state.depot = depot
    with d2:
        spar = st.number_input("Monatliche Sparrate (€)", value=st.session_state.sparrate, step=100.0, format="%.0f")
        st.session_state.sparrate = spar

    st.markdown("---")
    st.markdown("**Positionen**")

    ziel = depot / 10
    core_rows = []
    for p in CORE_POSITIONEN:
        kurs = get_price(p['ticker'])
        core_rows.append({
            'Ticker': p['ticker'],
            'Name': p['name'],
            'Sektor': p['sektor'],
            'Champions Score': p['score'],
            'Kurs': f"${kurs:.2f}" if kurs else "—",
            'Zielwert': f"€ {ziel:,.0f}",
            'Zielgewicht': "10%"
        })

    st.dataframe(pd.DataFrame(core_rows), use_container_width=True, height=400, hide_index=True)

    st.markdown("---")
    st.markdown("**Kapitalfluss nach Satelliten-Verkauf**")

    kf1, kf2 = st.columns(2)
    with kf1:
        erloese = st.number_input("Verkaufserlös (€)", value=3500.0, step=100.0, format="%.0f")
    with kf2:
        options = [f"{p['ticker']} — {p['name']}" for p in CORE_POSITIONEN]
        schwaechste = st.selectbox("Schwächste Position", options)

    if st.button("Kapitalfluss berechnen"):
        sat = min(2500.0, erloese)
        rest = erloese - sat
        core_ticker = schwaechste.split(" — ")[0]
        fehl = min(rest, ziel * 0.25)
        cash = max(0, rest - fehl)
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:18px;margin-top:8px">'
            f'<p style="font-size:0.68rem;color:#718096;margin-bottom:10px;font-weight:600">KAPITALFLUSS-HIERARCHIE</p>'
            + status_row("① Satellit-Rotation (2.500€)", f"€ {sat:,.0f}", "", "#2563eb")
            + status_row(f"② Core Nachkauf {core_ticker}", f"€ {fehl:,.0f}", "", "#16a34a")
            + status_row("③ Cash parken", f"€ {cash:,.0f}", "", "#718096")
            + '</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("**Allokations-Kalkulator**")
    ak = st.columns(4)
    for i, (name, pct, f) in enumerate([
        ('Core', 60, '#2563eb'),
        ('Satelliten', 25, '#ca8a04'),
        ('Crypto', 9, '#7c3aed'),
        ('Gold', 5, '#b45309'),
    ]):
        with ak[i]:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;'
                f'padding:16px;text-align:center">'
                f'<p style="font-size:0.72rem;color:#718096;margin:0 0 4px;font-weight:600">{name.upper()}</p>'
                f'<p style="font-size:1.5rem;font-weight:700;color:{f};margin:0">{pct}%</p>'
                f'<p style="font-family:DM Mono,monospace;font-size:0.78rem;color:#1a202c;margin:6px 0 2px">€ {depot*pct/100:,.0f}</p>'
                f'<p style="font-size:0.68rem;color:#718096;margin:0">+ € {spar*pct/100:,.0f}/Mo.</p>'
                f'</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════
# TAB 5 — OSZILLATOR
# ═══════════════════════════════════════════════════════

with tab5:
    st.markdown("### Champions-Oszillator")
    st.caption("Anteil der Champions über ihrem 200-Tage-GD — täglich automatisch berechnet.")

    champions_df2 = load_champions()
    if champions_df2.empty:
        st.warning("Bitte zuerst Champions-CSV im Tab **🏆 Champions** hochladen.")
    else:
        tickers2 = champions_df2['Ticker'].tolist()
        with st.spinner("Berechne Oszillator..."):
            ow, ou, og, od = calc_oszillator(tuple(tickers2))
        osc_txt2 = f"{ow:.1f}%" if ow else "—"

        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Oszillator", osc_txt2,
                  "Stark" if ow and ow >= 80 else "Positiv" if ow and ow >= 60 else "Gemischt" if ow and ow >= 40 else "Schwach")
        o2.metric("Über GD200", f"{ou}", f"von {og} Champions")
        o3.metric("Unter GD200", f"{og-ou}", f"von {og} Champions")
        o4.metric("VIX", vt, "Volatilität")

        st.markdown("---")

        if ow:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=ow,
                title={'text': "Champions-Oszillator", 'font': {'color': '#1a202c', 'size': 14}},
                number={'suffix': '%', 'font': {'color': '#2563eb', 'size': 36}},
                gauge={
                    'axis': {'range': [0,100], 'tickcolor': '#718096', 'tickfont': {'color': '#718096'}},
                    'bar': {'color': '#16a34a' if ow >= 60 else '#ca8a04' if ow >= 40 else '#dc2626'},
                    'bgcolor': '#f8fafc',
                    'bordercolor': '#e2e8f0',
                    'steps': [
                        {'range': [0, 20],   'color': '#fef2f2'},
                        {'range': [20, 40],  'color': '#fff7ed'},
                        {'range': [40, 60],  'color': '#fefce8'},
                        {'range': [60, 80],  'color': '#f0fdf4'},
                        {'range': [80, 100], 'color': '#dcfce7'},
                    ],
                }
            ))
            fig.update_layout(
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font={'color': '#1a202c'},
                height=280,
                margin=dict(t=40, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Interpretations-Skala**")
        for stand, markt, emp, f in [
            ("> 80%",  "Stabile Hausse",  "Maximal investiert",    "#16a34a"),
            ("60–80%", "Aufwärtstrend",   "Hoch investiert",       "#22c55e"),
            ("40–60%", "Gemischt",        "Neutral",               "#ca8a04"),
            ("20–40%", "Abwärtsdruck",    "Defensiv",              "#ea580c"),
            ("< 20%",  "Baisse",          "Max. Liquidität",       "#dc2626"),
        ]:
            aktiv = ow and (
                (stand == "> 80%"  and ow >= 80) or
                (stand == "60–80%" and 60 <= ow < 80) or
                (stand == "40–60%" and 40 <= ow < 60) or
                (stand == "20–40%" and 20 <= ow < 40) or
                (stand == "< 20%"  and ow < 20)
            )
            bd = f if aktiv else "#e2e8f0"
            bg = f"{f}12" if aktiv else "#ffffff"
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:7px;'
                f'padding:9px 14px;margin-bottom:5px;display:flex;gap:16px;align-items:center">'
                f'<span style="font-family:DM Mono,monospace;color:{f};width:65px;font-size:0.8rem;font-weight:500">{stand}</span>'
                f'<span style="color:#2d3748;width:150px;font-size:0.82rem;font-weight:500">{markt}</span>'
                f'<span style="color:#718096;font-size:0.78rem">{emp}</span>'
                f'{"<span style=color:"+f+";font-size:0.65rem;font-weight:700;margin-left:auto>◀ AKTUELL</span>" if aktiv else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

        # Detail mit Namen
        if not od.empty:
            with st.expander("📋 Alle Champions im Detail"):
                if 'Name' in champions_df2.columns:
                    od = od.merge(champions_df2[['Ticker','Name']], on='Ticker', how='left')
                    cols_od = ['Name', 'Ticker', 'Kurs', 'GD200', 'Abstand %', 'Status']
                else:
                    cols_od = ['Ticker', 'Kurs', 'GD200', 'Abstand %', 'Status']
                st.dataframe(
                    od[[c for c in cols_od if c in od.columns]].sort_values('Abstand %', ascending=False),
                    use_container_width=True, height=400, hide_index=True
                )

# ═══════════════════════════════════════════════════════
# TAB 6 — CHECKLISTE
# ═══════════════════════════════════════════════════════

with tab6:
    st.markdown("### Wöchentliche Checkliste")
    st.markdown(
        f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
        f'padding:10px 16px;margin-bottom:16px;font-size:0.82rem;color:#1d4ed8">'
        f'KW {datetime.now().isocalendar()[1]} · {datetime.now().strftime("%d.%m.%Y")} · '
        f'VIX: <b>{vt}</b> · Oszillator: <b>{osc_txt}</b> · Erlaubte Positionen: <b>{pos}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    cl1, cl2 = st.columns(2)
    with cl1:
        st.markdown("**🛰️ Satelliten-Check**")
        c1 = st.checkbox("Alle Positionen in Top 15?")
        c2 = st.checkbox("Signal 1 (Chart-Struktur) OK?")
        c3 = st.checkbox("Signal 2 (GD50) OK?")
        c4 = st.checkbox("Signal 3 (RS-Score) OK?")
        c5 = st.checkbox("VIX-Positionsanzahl eingehalten?")
        c6 = st.checkbox("Notfall -15% Trigger geprüft?")
        st.markdown("**💼 Core-Check**")
        c7 = st.checkbox("Gewichtungen berechnet?")
        c8 = st.checkbox("Schwächste Position identifiziert?")
        c9 = st.checkbox("Nachkauf-Budget festgelegt?")

    with cl2:
        st.markdown("**📊 Markt-Check**")
        c10 = st.checkbox("VIX abgelesen?")
        c11 = st.checkbox("Oszillator abgelesen?")
        c12 = st.checkbox("Ampelsignal notiert?")
        st.markdown("**🔍 Neue Kandidaten**")
        c13 = st.checkbox("Top 10 Screening geprüft?")
        c14 = st.checkbox("Branchen-Check (max. 2/Sektor)?")
        c15 = st.checkbox("Korrelations-Check mit Core?")
        c16 = st.checkbox("Freie Slots belegt?")

    checks = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16]
    done = sum(checks)
    pct_c = done/len(checks)
    fc = "#16a34a" if pct_c >= 0.8 else "#ca8a04" if pct_c >= 0.5 else "#dc2626"

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin:12px 0">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
        f'<span style="font-size:0.78rem;color:#718096;font-weight:600">FORTSCHRITT</span>'
        f'<span style="font-size:0.85rem;font-weight:700;color:{fc}">{done}/{len(checks)} erledigt</span>'
        f'</div>'
        f'<div style="height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden">'
        f'<div style="width:{pct_c*100:.0f}%;height:100%;background:{fc};border-radius:4px;transition:width 0.3s"></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    notizen_cl = st.text_area("Notizen", placeholder="Beobachtungen, Entscheidungen, Erkenntnisse dieser Woche...", key="cl_n")

    if st.button("✅ Checkliste speichern"):
        checklist_save(vix, osc_wert, pos, notizen_cl)
        st.success("✅ Gespeichert!")

# ═══════════════════════════════════════════════════════
# TAB 7 — JOURNAL
# ═══════════════════════════════════════════════════════

with tab7:
    st.markdown("### Trade Journal")

    trades = trades_load()
    if not trades.empty:
        j1, j2, j3 = st.columns(3)
        j1.metric("Gesamt Trades", len(trades))
        j2.metric("Offen", len(trades[trades['ausstieg_datum'].isna()]))
        j3.metric("Geschlossen", len(trades[trades['ausstieg_datum'].notna()]))
        st.markdown("---")

    jc1, jc2 = st.columns([1, 2])

    with jc1:
        st.markdown("**Neuer Eintrag**")
        j_ticker = st.text_input("Ticker", placeholder="z.B. NVDA")
        j_name = st.text_input("Unternehmensname", placeholder="z.B. NVIDIA Corporation")
        j_typ = st.selectbox("Typ", [
            "Satellit — Kauf", "Satellit — Verkauf",
            "Core — Nachkauf", "Core — Rotation", "Notiz"
        ])
        j_kurs = st.number_input("Kurs ($)", value=0.0, step=0.01, format="%.2f")
        j_betrag = st.number_input("Betrag (€)", value=2500.0, step=100.0, format="%.0f")
        j_grund = st.text_area("Einstiegsbegründung",
            placeholder="Warum diese Position? Ranking, Chart, Composite Score...", height=80)
        j_trigger = st.text_input("Ausstiegs-Trigger",
            placeholder="z.B. Top-15-Exit oder GD50-Bruch")

        if st.button("💾 Trade speichern"):
            if j_ticker and j_grund:
                trade_add(j_ticker, j_name, j_typ, j_kurs, j_betrag, j_grund, j_trigger)
                st.success("✅ Trade gespeichert!")
                st.rerun()
            else:
                st.error("Ticker und Begründung sind erforderlich.")

    with jc2:
        st.markdown("**Letzte Einträge**")
        if trades.empty:
            st.info("Noch keine Einträge. Erstellen Sie Ihren ersten Trade-Eintrag.")
        else:
            for _, row in trades.head(10).iterrows():
                pnl_html = ""
                if row.get('pnl') and not pd.isna(row['pnl']):
                    pc = "#16a34a" if row['pnl'] > 0 else "#dc2626"
                    pnl_html = f'<span style="color:{pc};font-weight:600"> € {row["pnl"]:+,.0f}</span>'
                offen = pd.isna(row.get('ausstieg_datum'))
                bd_c = "#2563eb" if offen else "#e2e8f0"
                name_display = f" — {row['name']}" if row.get('name') and not pd.isna(row.get('name','')) else ""
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:3px solid {bd_c};'
                    f'border-radius:8px;padding:12px 14px;margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
                    f'<span style="font-weight:700;color:#1a202c;font-size:0.9rem">'
                    f'{row["ticker"]}<span style="font-weight:400;color:#718096;font-size:0.8rem">{name_display}</span></span>'
                    f'<span style="font-size:0.65rem;color:#718096;font-family:DM Mono,monospace">'
                    f'{row["datum"]} · {row["typ"]}</span>'
                    f'</div>'
                    f'<p style="font-size:0.78rem;color:#718096;margin:2px 0">{str(row.get("begruendung",""))[:100]}</p>'
                    f'<p style="font-size:0.72rem;color:#718096;margin:2px 0">'
                    f'Exit: {row.get("ausstieg_trigger","—")}{pnl_html}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════

st.markdown(
    '<div style="text-align:center;padding:20px 0 8px;border-top:1px solid #e2e8f0;margin-top:24px">'
    '<p style="font-size:0.68rem;color:#cbd5e0">'
    'HF · System v2.0 — Privates Hedgefonds Dashboard — Streng vertraulich'
    '</p></div>',
    unsafe_allow_html=True
)
