"""
HF System — Privates Hedgefonds Dashboard
All-in-One Version — keine Unterordner nötig
Einfach app.py + requirements.txt in GitHub
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import os
import io

# ═══════════════════════════════════════════════════════
# CHAMPIONS DATEN — EINGEBETTET
# ═══════════════════════════════════════════════════════

CHAMPIONS_CSV = """Name,WKN,Ticker
Nvidia,918422,NVDA
Microsoft,870747,MSFT
Broadcom,A2JG9Z,AVGO
Casella Waste Systems,910249,CWST
Cadence,873567,CDNS
Constellation Software,A0JM27,CSU.TO
Progressive,865496,PGR
Amphenol,882749,APH
Trane Technologies,A2P09K,TT
Cintas,880205,CTAS
Mastercard,A0F602,MA
Arthur J. Gallagher,869761,AJG
O'Reilly Automotive,A1H5JY,ORLY
Boston Scientific,884113,BSX
Visa,A0NC7B,V
FICO,873369,FICO
T-Mobile US,A1T7LU,TMUS
Motorola Solutions,A0YHMA,MSI
Walmart,860853,WMT
Costco Wholesale,888351,COST
ServiceNow,A1JX4P,NOW
MSCI Inc.,A0M63R,MSCI
Synopsys,883703,SNPS
Berkshire Hathaway B,A0YJQ2,BRK-B
Itochu,855471,ITOCY
AutoZone,881531,AZO
S&P Global,A2AHZ7,SPGI
Intuit,886053,INTU
Apple,865985,AAPL
Hermes,886670,RMS.PA
Waste Management,893579,WM
Nasdaq Inc.,813516,NDAQ
Eli Lilly,858560,LLY
Deutsche Boerse,581005,DB1.DE
Stryker,864952,SYK
Moodys,915246,MCO
IDEXX Laboratories,888210,IDXX
Wolters Kluwer,A0J2R1,WKL.AS
Alphabet,A14Y6F,GOOGL
McDonalds,856958,MCD
TJX Companies,854854,TJX
Old Dominion,923655,ODFL
Abbott Laboratories,850103,ABT
Graco,859357,GGG
Hannover Rueck,840221,HNR1.DE
Muenchener Rueck,843002,MUV2.DE
Ametek,908668,AME
Amazon,906866,AMZN
Nemetschek,645290,NEM.DE
Netflix,552484,NFLX
Texas Instruments,852654,TXN
ITW,861219,ITW
Yum Brands,909190,YUM
Atoss Software,510440,AOF.DE
LOreal,853888,OR.PA
Lonza Group,928619,LONN.SW
LSE Group,A0JEJF,LSEG.L
ASML Holding,A1J4U4,ASML
Thermo Fisher,857209,TMO
Booking Holdings,A2JEXP,BKNG
Danaher,866197,DHR
Home Depot,866953,HD
Sherwin-Williams,856050,SHW
Lindt Spruengli,870503,LISP.SW
MTU Aero Engines,A0D9PT,MTX.DE
Sika,A2JNV8,SIKA.SW
BlackRock,A40PW4,BLK
Mettler-Toledo,910553,MTD
LVMH,853292,MC.PA
Givaudan,938427,GIVN.SW
Union Pacific,858144,UNP
NextEra Energy,A1CZ4H,NEE
EssilorLuxottica,863195,EL.PA
Ecolab,854545,ECL
Dominos,A0B6VQ,DPZ
American Water Works,A0NJ38,AWK
Fiserv,881793,FI
Church Dwight,864371,CHD
Balchem,905650,BCPC
Adobe,871981,ADBE
Keurig Dr Pepper,A2JQPZ,KDP
Geberit,A0MQWG,GEBN.SW
UnitedHealth Group,869561,UNH
CTS Eventim,547030,EVD.DE
Bechtle,515870,BC8.DE
Compass Group,A2DR6K,CPG.L
Edwards Lifesciences,936853,EW
CN,897879,CNI
Samsung,881823,005930.KS
Novo Nordisk,A3EU6F,NVO
PepsiCo,851995,PEP
Sartorius,716563,SRT.DE
Mondelez,A1J4U0,MDLZ
Cooper Companies,A402VX,COO
Rational,701080,RAA.DE
Starbucks,884437,SBUX
Symrise,SYM999,SY1.DE
Sixt,723133,SIX2.DE
Adidas,A1EWWW,ADS.DE
Colgate-Palmolive,850667,CL"""

# Core Portfolio
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
# KONFIGURATION
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="HF System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

.stApp { background-color: #1f2937; }
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}
.stTabs [data-baseweb="tab-list"] {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b7280;
    background: transparent;
    border: none;
}
.stTabs [aria-selected="true"] {
    color: #00d4aa !important;
    border-bottom: 2px solid #00d4aa !important;
    background: transparent !important;
}
.stButton > button {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: #00d4aa;
    color: #1f2937;
    border: none;
    border-radius: 8px;
}
.stButton > button:hover { opacity: 0.85; }
hr { border-color: #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# DATEN FUNKTIONEN
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_vix():
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        if not hist.empty:
            return round(float(hist['Close'].iloc[-1]), 2)
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def get_price(ticker):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if not hist.empty:
            return round(float(hist['Close'].iloc[-1]), 2)
    except:
        pass
    return None

@st.cache_data(ttl=86400)
def get_daily(ticker, years=2):
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=years*365)
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist[['Close','Volume']].dropna()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_monthly(ticker, years=11):
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=years*365)
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end, interval="1mo")
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist[['Close']].dropna()
    except:
        return pd.DataFrame()

def load_champions():
    df = pd.read_csv(io.StringIO(CHAMPIONS_CSV))
    return df

# ═══════════════════════════════════════════════════════
# CHAMPIONS SCORE — POTENZFORMEL
# ═══════════════════════════════════════════════════════

def calc_geopak10(close):
    if len(close) < 24:
        return None
    anfang = close.head(12).mean()
    ende = close.iloc[-1]
    if anfang <= 0:
        return None
    jahre = len(close) / 12
    return round(((ende / anfang) ** (1/jahre) - 1) * 100, 2)

def calc_gewinnkonstanz(close):
    if len(close) < 24:
        return None
    data = close.tail(120)
    ret = data.pct_change().dropna()
    if len(ret) < 12:
        return None
    return round((ret > 0).sum() / len(ret) * 100, 1)

def calc_verlust_ratio(close):
    if len(close) < 24:
        return None
    data = close.tail(120)
    ret = data.pct_change().dropna()
    if len(ret) < 12:
        return None
    n = len(ret)
    faktoren = np.arange(1, n+1)
    verluste = ret[ret < 0]
    if len(verluste) == 0:
        return 0.5
    prob = len(verluste) / n
    idx = [ret.index.get_loc(i) for i in verluste.index]
    vf = faktoren[idx]
    gew_verlust = np.sum(np.abs(verluste.values) * vf) / np.sum(vf)
    return round(prob * gew_verlust * 100, 2)

def calc_champions_score(geopak, konstanz, verlust):
    if any(v is None for v in [geopak, konstanz, verlust]):
        return None
    if geopak <= 0 or konstanz <= 0:
        return None
    vr = max(verlust, 0.5)
    score = (geopak**0.95) * ((1/vr)**1.2) * ((konstanz/100)**1.5)
    return round(score, 4)

@st.cache_data(ttl=86400)
def score_ticker(ticker):
    monthly = get_monthly(ticker)
    if monthly.empty or len(monthly) < 24:
        return None, None, None, None
    c = monthly['Close']
    g = calc_geopak10(c)
    k = calc_gewinnkonstanz(c)
    v = calc_verlust_ratio(c)
    s = calc_champions_score(g, k, v)
    return g, k, v, s

# ═══════════════════════════════════════════════════════
# OSZILLATOR
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def calc_oszillator(tickers):
    ueber = 0
    gesamt = 0
    details = []
    for ticker in tickers:
        try:
            hist = get_daily(ticker)
            if hist.empty or len(hist) < 30:
                continue
            kurs = hist['Close'].iloc[-1]
            gd200 = hist['Close'].tail(200).mean() if len(hist) >= 200 else hist['Close'].mean()
            above = kurs > gd200
            if above:
                ueber += 1
            gesamt += 1
            details.append({
                'Ticker': ticker,
                'Kurs': round(kurs, 2),
                'GD200': round(gd200, 2),
                'Abstand %': round(((kurs-gd200)/gd200)*100, 1),
                'Status': '✅ Über' if above else '❌ Unter'
            })
        except:
            continue
    wert = round(ueber/gesamt*100, 1) if gesamt > 0 else None
    return wert, ueber, gesamt, pd.DataFrame(details)

def vix_positionen(vix):
    if vix is None: return 5
    if vix < 25:    return 5
    if vix < 30:    return 3
    if vix < 40:    return 1
    return 0

def ampel_signal(vix, osc):
    vix_pos = vix_positionen(vix)
    if osc is None:
        osc_adj = 0
    elif osc >= 70:
        osc_adj = 0
    elif osc >= 40:
        osc_adj = -1
    else:
        osc_adj = -2
    final = max(0, vix_pos + osc_adj)
    if final >= 4:
        return final, '🟢', '#00d4aa', 'GRÜNES LICHT'
    elif final == 3:
        return final, '🟡', '#f5a623', 'GELBES LICHT'
    elif final == 1:
        return final, '🟠', '#ff8c42', 'DEFENSIV'
    else:
        return final, '🔴', '#e84855', 'CASH MODUS'

# ═══════════════════════════════════════════════════════
# SATELLITEN SCANNER
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=86400)
def scan_ticker(ticker):
    try:
        import yfinance as yf
        spy = get_daily("SPY", 2)
        hist = get_daily(ticker, 2)
        if hist.empty or spy.empty or len(hist) < 130:
            return None

        kurs = hist['Close'].iloc[-1]

        # GD200 Filter
        gd200 = hist['Close'].tail(200).mean() if len(hist) >= 200 else hist['Close'].mean()
        if kurs <= gd200:
            return None

        # Volumen Filter
        if 'Volume' in hist.columns:
            avg_vol = hist['Volume'].tail(60).mean()
            if avg_vol < 4_000_000:
                return None

        # RS > SPY
        aktie_ret = (hist['Close'].iloc[-1] / hist['Close'].iloc[-130] - 1)
        spy_ret = (spy['Close'].iloc[-1] / spy['Close'].iloc[-130] - 1)
        if aktie_ret <= spy_ret:
            return None

        # Drawdown
        hoch = hist['Close'].tail(252).max() if len(hist) >= 252 else hist['Close'].max()
        dd = ((kurs - hoch) / hoch) * 100
        if dd < -50:
            return None

        # MOM260 + MOM130 (AQR Lag)
        lag = 22
        ref = hist['Close'].iloc[-lag] if len(hist) > lag else hist['Close'].iloc[-1]

        mom260 = round(((ref / hist['Close'].iloc[-282] - 1) * 100), 2) if len(hist) >= 282 else None
        mom130 = round(((ref / hist['Close'].iloc[-152] - 1) * 100), 2) if len(hist) >= 152 else None

        # RS Score
        rs_score = round(aktie_ret * 100, 2)
        rs_vs_spy = round((aktie_ret - spy_ret) * 100, 2)

        # RS z-Score
        ret_130 = [(hist['Close'].iloc[-i] / hist['Close'].iloc[-(i+130)] - 1)*100
                   for i in range(130, min(len(hist), 260))]
        rs_zscore = round((rs_score - np.mean(ret_130)) / np.std(ret_130), 2) if len(ret_130) > 10 else 0

        # Composite
        if mom260 and mom130:
            composite = round(
                mom260*0.30 + mom130*0.25 + rs_score*0.25 + rs_zscore*10*0.20, 2
            )
        else:
            return None

        return {
            'Ticker': ticker,
            'Kurs': round(kurs, 2),
            'GD200': round(gd200, 2),
            'MOM260': mom260,
            'MOM130': mom130,
            'RS Score': rs_score,
            'RS vs SPY': rs_vs_spy,
            'RS z-Score': rs_zscore,
            'Composite ⭐': composite
        }
    except:
        return None

# ═══════════════════════════════════════════════════════
# JOURNAL (SQLite)
# ═══════════════════════════════════════════════════════

DB = "journal.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT, ticker TEXT, typ TEXT,
        kurs REAL, betrag REAL,
        begruendung TEXT, ausstieg_trigger TEXT,
        ausstieg_kurs REAL, ausstieg_datum TEXT,
        pnl REAL, notizen TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS checkliste (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT, vix REAL, oszillator REAL,
        positionen INTEGER, notizen TEXT
    )''')
    conn.commit()
    conn.close()

def trade_add(ticker, typ, kurs, betrag, grund, trigger):
    init_db()
    conn = sqlite3.connect(DB)
    conn.execute(
        'INSERT INTO trades (datum,ticker,typ,kurs,betrag,begruendung,ausstieg_trigger) VALUES (?,?,?,?,?,?,?)',
        (datetime.now().strftime('%Y-%m-%d'), ticker.upper(), typ, kurs, betrag, grund, trigger)
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

if 'depot' not in st.session_state:
    st.session_state.depot = 100000.0
if 'sparrate' not in st.session_state:
    st.session_state.sparrate = 1000.0

# ═══════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════

c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.markdown(
        '<h2 style="font-family:Syne,sans-serif;font-weight:800;color:#00d4aa;margin:0;font-size:1.3rem;letter-spacing:0.1em">HF · SYSTEM</h2>'
        '<p style="font-family:DM Mono,monospace;font-size:0.6rem;color:#6b7280;margin:0;letter-spacing:0.12em">PRIVATES HEDGEFONDS DASHBOARD</p>',
        unsafe_allow_html=True
    )
with c2:
    st.markdown(
        f'<p style="font-family:DM Mono,monospace;font-size:0.72rem;color:#6b7280;margin-top:14px">'
        f'{datetime.now().strftime("%d.%m.%Y — %H:%M")}</p>',
        unsafe_allow_html=True
    )
with c3:
    vix = get_vix()
    vc = "#00d4aa" if vix and vix < 25 else "#f5a623" if vix and vix < 30 else "#ff8c42" if vix and vix < 40 else "#e84855"
    vt = f"{vix:.1f}" if vix else "—"
    st.markdown(
        f'<div style="text-align:right;margin-top:6px">'
        f'<span style="font-family:DM Mono,monospace;font-size:0.58rem;color:#6b7280">VIX</span><br>'
        f'<span style="font-family:Syne,sans-serif;font-size:1.7rem;font-weight:800;color:{vc}">{vt}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown("<hr style='border-color:#e5e7eb;margin:8px 0 16px 0'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════

champions_df = load_champions()
tickers_list = champions_df['Ticker'].tolist()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 Dashboard", "🏆 Champions", "📡 Satelliten",
    "💼 Core", "📊 Oszillator", "📋 Checkliste", "📓 Journal"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════

with tab1:
    st.markdown("### Echtzeit-Cockpit")

    with st.spinner("Lade Marktdaten..."):
        osc_wert, osc_ueber, osc_gesamt, _ = calc_oszillator(tuple(tickers_list))

    pos, emoji, farbe, text = ampel_signal(vix, osc_wert)
    osc_txt = f"{osc_wert:.1f}%" if osc_wert else "—"

    # Ampel
    st.markdown(
        f'<div style="background:{farbe}15;border:2px solid {farbe};border-radius:16px;'
        f'padding:24px;text-align:center;margin-bottom:24px">'
        f'<div style="font-size:2.8rem">{emoji}</div>'
        f'<div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;color:{farbe};margin:8px 0">{text}</div>'
        f'<div style="font-family:DM Mono,monospace;font-size:1rem;color:{farbe};font-weight:700">'
        f'{pos} SATELLITEN-POSITIONEN ERLAUBT</div>'
        f'<div style="font-family:DM Mono,monospace;font-size:0.68rem;color:#6b7280;margin-top:8px">'
        f'VIX {vt} &nbsp;|&nbsp; Oszillator {osc_txt}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Metriken
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Core Portfolio", "60%", "10 Compounder")
    m2.metric("Satelliten max.", str(pos), "VIX-gesteuert")
    m3.metric("Crypto", "9%", "BTC 70% / ETH 30%")
    m4.metric("Gold", "5%", "Hedge")
    m5.metric("Oszillator", osc_txt, f"{osc_ueber}/{osc_gesamt} über GD200")

    st.markdown("---")
    col_vix, col_alloc = st.columns(2)

    with col_vix:
        st.markdown("**VIX Regelwerk**")
        for label, p, f, aktiv in [
            ("VIX < 25", 5, "#00d4aa", vix and vix < 25),
            ("VIX 25–30", 3, "#f5a623", vix and 25 <= vix < 30),
            ("VIX 30–40", 1, "#ff8c42", vix and 30 <= vix < 40),
            ("VIX > 40",  0, "#e84855", vix and vix >= 40),
        ]:
            bg = f"{f}15" if aktiv else "#ffffff"
            bd = f if aktiv else "#e5e7eb"
            tag = ' <span style="color:#00d4aa;font-size:0.62rem">◀ AKTIV</span>' if aktiv else ''
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
                f'padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:14px">'
                f'<span style="font-family:DM Mono,monospace;color:{f};width:85px;font-size:0.82rem">{label}</span>'
                f'<span style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:{f};width:25px">{p}</span>'
                f'<span style="font-size:0.73rem;color:#6b7280">Positionen{tag}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    with col_alloc:
        st.markdown("**Gesamt-Allokation**")
        for name, pct, f in [
            ("Core Portfolio", 60, "#00d4aa"),
            ("Satelliten", 25, "#f5a623"),
            ("Crypto", 9, "#8b5cf6"),
            ("Gold", 5, "#c9a84c"),
            ("Altlasten", 1, "#6b7280"),
        ]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:9px">'
                f'<span style="font-family:DM Mono,monospace;font-size:0.68rem;color:#6b7280;width:115px">{name}</span>'
                f'<div style="flex:1;height:7px;background:#e5e7eb;border-radius:4px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{f};border-radius:4px"></div></div>'
                f'<span style="font-family:Syne,sans-serif;font-size:0.82rem;font-weight:700;color:{f};width:32px;text-align:right">{pct}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════
# TAB 2 — CHAMPIONS SCORE
# ═══════════════════════════════════════════════════════

with tab2:
    st.markdown("### Champions Score — Potenzformel")
    st.markdown(
        '<div style="font-family:DM Mono,monospace;font-size:0.85rem;color:#00d4aa;'
        'background:#00d4aa12;border:1px solid #00d4aa30;border-radius:8px;padding:12px 16px;margin-bottom:20px">'
        'GeoPAK10^0.95 × (1/max(Verlust-Ratio, 0.5))^1.2 × (Gewinnkonstanz/100)^1.5'
        '</div>',
        unsafe_allow_html=True
    )

    col_s1, col_s2 = st.columns([1, 2])

    with col_s1:
        st.markdown("**Einzelberechnung**")
        ticker_in = st.text_input("Ticker", placeholder="z.B. NVDA", key="score_ticker")
        if st.button("Score berechnen", key="btn_score"):
            if ticker_in:
                with st.spinner(f"Berechne {ticker_in.upper()}..."):
                    g, k, v, s = score_ticker(ticker_in.upper())
                if s:
                    st.success(f"Champions Score: **{s:.4f}**")
                    sa, sb, sc = st.columns(3)
                    sa.metric("GeoPAK10", f"{g:.1f}%" if g else "—")
                    sb.metric("Konstanz", f"{k:.1f}%" if k else "—")
                    sc.metric("Verlust-Ratio", f"{v:.2f}" if v else "—")
                else:
                    st.error("Nicht genug Daten verfügbar.")

    with col_s2:
        st.markdown("**Champions-Liste**")
        st.dataframe(champions_df, use_container_width=True, height=380)

    st.markdown("---")
    st.markdown("**Alle Champions berechnen** — dauert 3-5 Minuten")

    if st.button("🚀 Alle Champions berechnen", key="btn_all"):
        results = []
        prog = st.progress(0)
        for i, row in champions_df.iterrows():
            prog.progress((i+1)/len(champions_df))
            g, k, v, s = score_ticker(row['Ticker'])
            if s:
                results.append({
                    'Rang': len(results)+1,
                    'Name': row['Name'],
                    'Ticker': row['Ticker'],
                    'GeoPAK10 (%)': g,
                    'Konstanz (%)': k,
                    'Verlust-Ratio': v,
                    'Score': s
                })
        prog.empty()
        if results:
            res_df = pd.DataFrame(results).sort_values('Score', ascending=False).reset_index(drop=True)
            res_df['Rang'] = res_df.index + 1
            st.success(f"✅ {len(res_df)} Champions berechnet")
            st.dataframe(res_df, use_container_width=True, height=500)

# ═══════════════════════════════════════════════════════
# TAB 3 — SATELLITEN
# ═══════════════════════════════════════════════════════

with tab3:
    st.markdown("### Satelliten-Scanner")

    sa1, sa2, sa3, sa4 = st.columns(4)
    sa1.metric("Universum", "3.065", "Aktien")
    sa2.metric("Erlaubte Positionen", str(pos), "VIX-gesteuert")
    sa3.metric("Einstieg", "€ 2.500", "Fix je Position")
    sa4.metric("Rhythmus", "Wöchentlich", "Fester Tag")

    st.markdown("---")

    # Universum Upload
    st.markdown("**Ihr Aktien-Universum**")
    uploaded = st.file_uploader(
        "universe.csv hochladen (Spalte: Ticker)",
        type=['csv'],
        key="universe_upload"
    )

    if uploaded:
        universe_df = pd.read_csv(uploaded)
        if 'Ticker' in universe_df.columns:
            uni_tickers = universe_df['Ticker'].dropna().tolist()
            st.success(f"✅ {len(uni_tickers)} Aktien geladen")

            if st.button("🔍 Scanner starten", key="btn_scan"):
                results = []
                prog2 = st.progress(0)
                status2 = st.empty()

                for i, t in enumerate(uni_tickers[:500]):  # Limit für Demo
                    prog2.progress((i+1)/min(len(uni_tickers), 500))
                    status2.text(f"Scanne {t}... ({i+1}/{min(len(uni_tickers),500)})")
                    r = scan_ticker(t)
                    if r:
                        results.append(r)

                prog2.empty()
                status2.empty()

                if results:
                    scan_df = pd.DataFrame(results).sort_values('Composite ⭐', ascending=False).reset_index(drop=True)
                    scan_df.insert(0, '#', scan_df.index + 1)
                    st.success(f"✅ {len(results)} Kandidaten gefunden")
                    st.dataframe(scan_df.head(20), use_container_width=True, height=500)
                else:
                    st.warning("Keine Kandidaten nach Filterung.")
        else:
            st.error("CSV braucht eine Spalte namens 'Ticker'")
    else:
        st.info(
            "📁 Bitte laden Sie Ihre universe.csv hoch.\n\n"
            "Format: Eine Spalte mit dem Namen **Ticker** — eine Zeile pro Aktie."
        )

    st.markdown("---")
    st.markdown("**Ausstiegs-Trigger**")
    st.markdown(
        '<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px">'
        '<p style="font-size:0.83rem;margin:4px 0">🔴 <b>Top-15-Exit:</b> Position fällt aus Top 15 → sofort verkaufen</p>'
        '<p style="font-size:0.83rem;margin:4px 0">🔴 <b>Strukturbruch:</b> 2 von 3 Signalen aktiv → sofort verkaufen</p>'
        '<p style="font-size:0.83rem;margin:4px 0">&nbsp;&nbsp;&nbsp;&nbsp;Signal 1: Wochenschlusskurs unter letzter Unterstützung</p>'
        '<p style="font-size:0.83rem;margin:4px 0">&nbsp;&nbsp;&nbsp;&nbsp;Signal 2: Kurs unter 50-Tage-GD</p>'
        '<p style="font-size:0.83rem;margin:4px 0">&nbsp;&nbsp;&nbsp;&nbsp;Signal 3: Ranking -5 Plätze oder RS unter 4-Wochen-Schnitt</p>'
        '<p style="font-size:0.83rem;margin:4px 0">🔴 <b>Notfall:</b> -15% intraweek → sofort verkaufen</p>'
        '</div>',
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════
# TAB 4 — CORE
# ═══════════════════════════════════════════════════════

with tab4:
    st.markdown("### Core Portfolio — 10 Compounder")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        depot = st.number_input("Depot-Gesamtwert (€)", value=st.session_state.depot, step=1000.0, format="%.0f")
        st.session_state.depot = depot
    with col_d2:
        spar = st.number_input("Monatliche Sparrate (€)", value=st.session_state.sparrate, step=100.0, format="%.0f")
        st.session_state.sparrate = spar

    st.markdown("---")

    # Core Tabelle
    ziel = depot / 10
    core_data = []
    for p in CORE_POSITIONEN:
        kurs = get_price(p['ticker'])
        core_data.append({
            'Ticker': p['ticker'],
            'Unternehmen': p['name'],
            'Sektor': p['sektor'],
            'Score': p['score'],
            'Kurs': f"${kurs:.2f}" if kurs else "—",
            'Zielwert': f"€ {ziel:,.0f}",
            'Gewicht': "10%"
        })

    st.dataframe(pd.DataFrame(core_data), use_container_width=True, height=400)

    st.markdown("---")

    # Kapitalfluss Rechner
    st.markdown("**Kapitalfluss nach Satelliten-Verkauf**")
    kf1, kf2 = st.columns(2)
    with kf1:
        erloese = st.number_input("Verkaufserlös (€)", value=3500.0, step=100.0, format="%.0f")
    with kf2:
        schwaechste = st.selectbox("Schwächste Core-Position",
            [f"{p['ticker']} — {p['name']}" for p in CORE_POSITIONEN])

    if st.button("Kapitalfluss berechnen", key="btn_kf"):
        satellit = min(2500, erloese)
        rest = erloese - satellit
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin-top:12px">'
            f'<p style="font-family:DM Mono,monospace;font-size:0.62rem;color:#6b7280;margin-bottom:12px">KAPITALFLUSS-HIERARCHIE</p>'
            f'<p style="margin:8px 0"><span style="color:#00d4aa;font-weight:700">Schritt 1</span> — Satellit Rotation: <b>€ {satellit:,.0f}</b></p>'
            f'<p style="margin:8px 0"><span style="color:#4ade80;font-weight:700">Schritt 2</span> — Core Nachkauf ({schwaechste.split(" — ")[0]}): <b>€ {min(rest, ziel*0.22):,.0f}</b></p>'
            f'<p style="margin:8px 0"><span style="color:#6b7280;font-weight:700">Cash</span> — Parken: <b>€ {max(0, rest - ziel*0.22):,.0f}</b></p>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("**Allokations-Kalkulator**")
    ak = st.columns(4)
    for i, (name, pct, f) in enumerate([
        ('Core Portfolio', 60, '#00d4aa'),
        ('Satelliten', 25, '#f5a623'),
        ('Crypto', 9, '#8b5cf6'),
        ('Gold', 5, '#c9a84c'),
    ]):
        with ak[i]:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px;text-align:center">'
                f'<p style="font-family:DM Mono,monospace;font-size:0.58rem;color:#6b7280;margin:0 0 4px">{name.upper()}</p>'
                f'<p style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:800;color:{f};margin:0">{pct}%</p>'
                f'<p style="font-family:DM Mono,monospace;font-size:0.75rem;color:#1f2937;margin:4px 0 1px">€ {depot*pct/100:,.0f}</p>'
                f'<p style="font-size:0.65rem;color:#6b7280;margin:0">+ € {spar*pct/100:,.0f}/Mo.</p>'
                f'</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════
# TAB 5 — OSZILLATOR
# ═══════════════════════════════════════════════════════

with tab5:
    st.markdown("### Champions-Oszillator")
    st.markdown("Anteil der Champions über ihrem 200-Tage-GD — täglich automatisch berechnet.")

    o1, o2, o3 = st.columns(3)
    o1.metric("Champions-Oszillator", osc_txt,
              "Starke Hausse" if osc_wert and osc_wert >= 80 else
              "Aufwärtstrend" if osc_wert and osc_wert >= 60 else
              "Gemischt" if osc_wert and osc_wert >= 40 else
              "Schwäche" if osc_wert else "—")
    o2.metric("Über GD200", f"{osc_ueber} / {osc_gesamt}", "Champions")
    o3.metric("VIX", vt, "Volatilitätsindex")

    st.markdown("---")

    if osc_wert:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=osc_wert,
            title={'text': "Champions-Oszillator", 'font': {'color': '#1f2937', 'size': 15}},
            number={'suffix': '%', 'font': {'color': '#00d4aa', 'size': 38}},
            gauge={
                'axis': {'range': [0, 100], 'tickcolor': '#6b7280'},
                'bar': {'color': '#00d4aa' if osc_wert >= 60 else '#f5a623' if osc_wert >= 40 else '#e84855'},
                'bgcolor': '#ffffff',
                'bordercolor': '#e5e7eb',
                'steps': [
                    {'range': [0, 20],   'color': '#2a1215'},
                    {'range': [20, 40],  'color': '#2a1a0e'},
                    {'range': [40, 60],  'color': '#e5e7eb'},
                    {'range': [60, 80],  'color': '#0d2b1e'},
                    {'range': [80, 100], 'color': '#0a2318'},
                ],
            }
        ))
        fig.update_layout(paper_bgcolor='#f7f9fc', font={'color': '#1f2937'}, height=280, margin=dict(t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Interpretations-Skala**")
    for stand, markt, empfehlung, f in [
        ("> 80%", "Stabile Hausse", "Maximal investiert", "#00d4aa"),
        ("60–80%", "Aufwärtstrend", "Hoch investiert", "#4ade80"),
        ("40–60%", "Gemischt", "Neutral", "#f5a623"),
        ("20–40%", "Abwärtsdruck", "Defensiv", "#ff8c42"),
        ("< 20%", "Baisse", "Maximale Liquidität", "#e84855"),
    ]:
        aktiv = osc_wert and (
            (stand == "> 80%" and osc_wert >= 80) or
            (stand == "60–80%" and 60 <= osc_wert < 80) or
            (stand == "40–60%" and 40 <= osc_wert < 60) or
            (stand == "20–40%" and 20 <= osc_wert < 40) or
            (stand == "< 20%" and osc_wert < 20)
        )
        bd = f if aktiv else "#e5e7eb"
        bg = f"{f}12" if aktiv else "#ffffff"
        st.markdown(
            f'<div style="background:{bg};border:1px solid {bd};border-radius:7px;'
            f'padding:9px 14px;margin-bottom:5px;display:flex;gap:16px;align-items:center">'
            f'<span style="font-family:DM Mono,monospace;color:{f};width:70px;font-size:0.8rem">{stand}</span>'
            f'<span style="color:#1f2937;width:160px;font-size:0.82rem">{markt}</span>'
            f'<span style="color:#6b7280;font-size:0.78rem">{empfehlung}</span>'
            f'{"<span style=color:#00d4aa;font-size:0.62rem;margin-left:auto>◀ AKTUELL</span>" if aktiv else ""}'
            f'</div>',
            unsafe_allow_html=True
        )

    # Details
    _, _, _, osc_details = calc_oszillator(tuple(tickers_list))
    if not osc_details.empty:
        with st.expander("📋 Detail — Alle Champions vs. GD200"):
            st.dataframe(
                osc_details.sort_values('Abstand %', ascending=False),
                use_container_width=True, height=400
            )

# ═══════════════════════════════════════════════════════
# TAB 6 — CHECKLISTE
# ═══════════════════════════════════════════════════════

with tab6:
    st.markdown("### Wöchentliche Checkliste")
    st.markdown(
        f'<p style="font-family:DM Mono,monospace;font-size:0.72rem;color:#6b7280">'
        f'KW {datetime.now().isocalendar()[1]} — {datetime.now().strftime("%d.%m.%Y")}'
        f' | VIX: {vt} | Oszillator: {osc_txt} | Positionen: {pos}</p>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    cl1, cl2 = st.columns(2)

    with cl1:
        st.markdown("**🛰️ Satelliten-Check**")
        c1 = st.checkbox("Alle Positionen noch in Top 15?")
        c2 = st.checkbox("Signal 1 (Chart-Struktur) geprüft?")
        c3 = st.checkbox("Signal 2 (GD50) geprüft?")
        c4 = st.checkbox("Signal 3 (RS-Score) geprüft?")
        c5 = st.checkbox("VIX-Anzahl eingehalten?")
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
        c13 = st.checkbox("Top 10 aus Screening geprüft?")
        c14 = st.checkbox("Branchen-Check (max. 2/Sektor)?")
        c15 = st.checkbox("Korrelations-Check mit Core?")
        c16 = st.checkbox("Freie Slots belegt?")

    checks = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16]
    done = sum(checks)
    pct_done = done / len(checks)
    fc = "#00d4aa" if pct_done >= 0.8 else "#f5a623" if pct_done >= 0.5 else "#e84855"

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin:12px 0">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:7px">'
        f'<span style="font-family:DM Mono,monospace;font-size:0.72rem;color:#6b7280">FORTSCHRITT</span>'
        f'<span style="font-family:Syne,sans-serif;font-weight:700;color:{fc}">{done}/{len(checks)}</span>'
        f'</div>'
        f'<div style="height:7px;background:#e5e7eb;border-radius:4px;overflow:hidden">'
        f'<div style="width:{pct_done*100:.0f}%;height:100%;background:{fc};border-radius:4px"></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    notizen_cl = st.text_area("Notizen", placeholder="Beobachtungen, Entscheidungen...", key="cl_notes")

    if st.button("✅ Checkliste speichern", key="btn_cl"):
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
        offene = len(trades[trades['ausstieg_datum'].isna()])
        j2.metric("Offen", offene)
        j3.metric("Geschlossen", len(trades) - offene)
        st.markdown("---")

    jc1, jc2 = st.columns([1, 2])

    with jc1:
        st.markdown("**Neuer Eintrag**")
        j_ticker = st.text_input("Ticker", placeholder="z.B. AAPL", key="j_t")
        j_typ = st.selectbox("Typ", [
            "Satellit — Kauf", "Satellit — Verkauf",
            "Core — Nachkauf", "Notiz"
        ], key="j_typ")
        j_kurs = st.number_input("Kurs ($)", value=0.0, step=0.01, format="%.2f", key="j_k")
        j_betrag = st.number_input("Betrag (€)", value=2500.0, step=100.0, format="%.0f", key="j_b")
        j_grund = st.text_area("Einstiegsbegründung",
            placeholder="Ranking, Chart, Signal...", height=80, key="j_g")
        j_trigger = st.text_input("Ausstiegs-Trigger",
            placeholder="z.B. Top-15-Exit", key="j_tr")

        if st.button("💾 Speichern", key="btn_j"):
            if j_ticker and j_grund:
                trade_add(j_ticker, j_typ, j_kurs, j_betrag, j_grund, j_trigger)
                st.success("✅ Trade gespeichert!")
                st.rerun()
            else:
                st.error("Ticker und Begründung erforderlich.")

    with jc2:
        st.markdown("**Letzte Einträge**")
        if trades.empty:
            st.info("Noch keine Einträge.")
        else:
            for _, row in trades.head(10).iterrows():
                pnl = ""
                if row.get('pnl') and not pd.isna(row['pnl']):
                    pc = "#00d4aa" if row['pnl'] > 0 else "#e84855"
                    pnl = f'<span style="color:{pc};font-weight:700"> € {row["pnl"]:+,.0f}</span>'
                status_c = "#00d4aa" if pd.isna(row.get('ausstieg_datum')) else "#6b7280"
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;'
                    f'padding:12px 14px;margin-bottom:7px">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                    f'<span style="font-family:Syne,sans-serif;font-weight:700;color:{status_c}">{row["ticker"]}</span>'
                    f'<span style="font-family:DM Mono,monospace;font-size:0.62rem;color:#6b7280">{row["datum"]} · {row["typ"]}</span>'
                    f'</div>'
                    f'<p style="font-size:0.78rem;color:#6b7280;margin:2px 0">{str(row.get("begruendung",""))[:90]}</p>'
                    f'<p style="font-size:0.72rem;color:#6b7280;margin:2px 0">Exit: {row.get("ausstieg_trigger","—")}{pnl}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# Footer
st.markdown(
    '<div style="text-align:center;padding:24px 0 8px;border-top:1px solid #e5e7eb;margin-top:24px">'
    '<p style="font-family:DM Mono,monospace;font-size:0.6rem;color:#6b7280">'
    'HF · SYSTEM — Privates Hedgefonds Dashboard — Streng vertraulich</p>'
    '</div>',
    unsafe_allow_html=True
)
