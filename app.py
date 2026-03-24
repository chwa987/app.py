"""
HF System — Privates Hedgefonds Dashboard v3.0
Finale Momentum-Logik:
- Filter: Kurs > 10, Vol ≥ 5Mio, Kurs > GD200
- Ranking: MOM260 (40%) + MOMJT (30%) + GD130-Abstand (30%)
- Breadth-Oszillator mit 4 Stufen
- VIX: ignorieren < 25, reduzieren ≥ 25, keine Käufe > 40
- Positionsgröße = Top-N × Breadth-Faktor, dann VIX-Korrektur
- Stabilität: 2-Wochen-Bestätigung
- Sektor: max. 2 pro Sektor (via yfinance)
- Exit: Teilverkauf −20% vom Hoch, Vollverkauf 2W unter Level
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import io

# ═══════════════════════════════════════════════════════
# CORE PORTFOLIO
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

.stApp { background-color: #f8f9fb; font-family: 'Inter', sans-serif; }
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

[data-testid="stMetricValue"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: #1a202c !important;
}
[data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #718096 !important; }

.stTabs [data-baseweb="tab-list"] {
    background-color: #ffffff;
    border-bottom: 2px solid #e2e8f0;
    border-radius: 8px 8px 0 0;
    padding: 0 8px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.78rem;
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

.stButton > button {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
}
.stButton > button:hover { background: #1d4ed8; }

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.85rem;
    font-weight: 700;
    color: #1a202c;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}

hr { border-color: #e2e8f0; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# DATEN — YAHOO FINANCE (unverändert)
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

@st.cache_data(ttl=86400)
def get_sektor(ticker):
    """Sektor via yfinance laden — für Sektorregel max. 2 pro Sektor."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get('sector', info.get('industry', 'Unbekannt'))
    except:
        return 'Unbekannt'

# ═══════════════════════════════════════════════════════
# CHAMPIONS SCORE — POTENZFORMEL (unverändert)
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
    """7140 Ein-und-Ausstiegs-Szenarien (120×119÷2)."""
    if len(close) < 24:
        return None
    data = close.tail(120).values
    n = len(data)
    positive = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            if data[j] > data[i]:
                positive += 1
    if total == 0:
        return None
    return round(positive / total * 100, 1)

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
    gew = np.sum(np.abs(v.values)*vf) / np.sum(vf)
    return round((len(v)/n)*gew*100, 2)

def calc_score(g, k, v):
    if any(x is None for x in [g, k, v]):
        return None
    if g <= 0 or k <= 0:
        return None
    vr = max(v, 0.5)
    return round((g**0.95) * ((1/vr)**1.2) * ((k/100)**1.5), 4)

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
# CHAMPIONS LADEN (unverändert)
# ═══════════════════════════════════════════════════════

def load_champions(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state['champions_df'] = df
        return df
    elif 'champions_df' in st.session_state:
        return st.session_state['champions_df']
    return pd.DataFrame()

# ═══════════════════════════════════════════════════════
# BREADTH-OSZILLATOR — NEU
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def calc_oszillator(tickers):
    """Anteil der Aktien über GD200 — Breadth-Indikator."""
    ueber, gesamt, details = 0, 0, []
    for t in tickers:
        try:
            h = get_daily(t)
            if h.empty or len(h) < 30:
                continue
            k = h['Close'].iloc[-1]
            gd = h['Close'].tail(200).mean() if len(h) >= 200 else h['Close'].mean()
            ab = k > gd
            if ab: ueber += 1
            gesamt += 1
            details.append({
                'Ticker': t, 'Kurs': round(k,2), 'GD200': round(gd,2),
                'Abstand %': round(((k-gd)/gd)*100,1),
                'Status': '✅ Über' if ab else '❌ Unter'
            })
        except:
            continue
    wert = round(ueber/gesamt*100,1) if gesamt > 0 else None
    return wert, ueber, gesamt, pd.DataFrame(details)

def breadth_faktor(osc):
    """
    Breadth-Stufen:
    ≥ 60% → Faktor 1.0 (volle Positionsanzahl)
    40–60% → Faktor 0.6 (reduziert)
    30–40% → Faktor 0.3 (stark reduziert, keine neuen Käufe)
    < 30%  → Faktor 0.0 (Positionen abbauen)
    """
    if osc is None:
        return 1.0, "Keine Daten", "#718096", True
    if osc >= 60:
        return 1.0, "Volle Positionsanzahl", "#16a34a", True
    if osc >= 40:
        return 0.6, "Reduziert — Vorsicht", "#ca8a04", True
    if osc >= 30:
        return 0.3, "Stark reduziert — keine neuen Käufe", "#ea580c", False
    return 0.0, "Positionen abbauen — Cash-Modus", "#dc2626", False

def vix_korrektur(vix, basis_pos):
    """
    VIX-Regeln:
    VIX < 25  → ignorieren (kein Einfluss)
    VIX 25–40 → Positionsanzahl reduzieren (-2)
    VIX > 40  → keine neuen Käufe (Positionen auf 0 setzen)
    """
    if vix is None or vix < 25:
        return basis_pos, True   # (erlaubte Positionen, neue Käufe erlaubt)
    if vix <= 40:
        return max(0, basis_pos - 2), True
    return 0, False  # Keine neuen Käufe

def berechne_positionen(top_n, osc, vix):
    """
    Gesamtlogik Positionsgröße:
    1. Basis = Top-N (aus Sidebar)
    2. × Breadth-Faktor
    3. VIX-Korrektur anwenden
    """
    bf, bf_text, bf_farbe, neue_kauf_erlaubt_breadth = breadth_faktor(osc)
    basis = max(1, round(top_n * bf))
    finale_pos, neue_kauf_erlaubt_vix = vix_korrektur(vix, basis)
    neue_kauf_erlaubt = neue_kauf_erlaubt_breadth and neue_kauf_erlaubt_vix
    return finale_pos, neue_kauf_erlaubt, bf_text, bf_farbe

def vix_pos(vix):
    """Vereinfacht für Header-Anzeige."""
    if vix is None or vix < 25: return 5
    if vix <= 40: return 3
    return 0

def ampel(vix, osc, top_n=5):
    pos, neue_kauf, bf_text, bf_farbe = berechne_positionen(top_n, osc, vix)
    if pos >= 4 and neue_kauf:
        return pos, '#16a34a', '#f0fdf4', 'GRÜNES LICHT — Vollgas'
    if pos >= 3 and neue_kauf:
        return pos, '#ca8a04', '#fefce8', 'GELBES LICHT — Vorsicht'
    if pos >= 1:
        return pos, '#ea580c', '#fff7ed', 'ORANGE — Keine neuen Käufe'
    return pos, '#dc2626', '#fef2f2', 'ROTES LICHT — Positionen abbauen'

# ═══════════════════════════════════════════════════════
# NEUES MOMENTUM-RANKING — KERN DER ÜBERARBEITUNG
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=86400)
def scan(ticker, min_vol=5_000_000, min_kurs=10.0):
    """
    Neues Momentum-System:

    FILTER (alle müssen erfüllt sein):
    - Kurs > 10 €/$ (Penny-Stock-Schutz)
    - Ø Volumen (60T) ≥ 5 Mio
    - Kurs > GD200 (Pflichtfilter — kein Ranking-Faktor)

    RANKING (Composite Score):
    - MOM260  = 12-Monats-Momentum (AQR-Lag)          → 40%
    - MOMJT   = 6-Monats-Momentum / Jahrestrend        → 30%
    - GD130   = Abstand zur 130-Tage-Linie (Nähe)     → 30%

    OPTIONAL:
    - Malus bei extremer GD200-Überdehnung (> 50% über GD200)
    """
    try:
        import yfinance as yf
        h = get_daily(ticker, years=2)
        if h.empty or len(h) < 150:
            return None

        k = h['Close'].iloc[-1]

        # ── FILTER 1: Kurs > 10 ──────────────────────────
        if k < min_kurs:
            return None

        # ── FILTER 2: GD200 Pflichtfilter ───────────────
        if len(h) < 200:
            return None
        gd200 = h['Close'].tail(200).mean()
        if k <= gd200:
            return None
        gd200_abstand = round(((k - gd200) / gd200) * 100, 1)

        # ── FILTER 3: Volumen ≥ 5 Mio ───────────────────
        if 'Volume' in h.columns:
            avg_vol = h['Volume'].tail(60).mean()
            if avg_vol < min_vol:
                return None
        else:
            avg_vol = 0

        # ── GD130 berechnen ──────────────────────────────
        if len(h) < 130:
            return None
        gd130 = h['Close'].tail(130).mean()
        gd130_abstand = round(((k - gd130) / gd130) * 100, 1)

        # ── MOM260: 12-Monats-Momentum (AQR-Lag 22T) ────
        # Letzter Monat ausgeschlossen — verhindert kurzfristige Reversal-Verzerrung
        lag = 22
        if len(h) < 282:  # 260 + 22
            return None
        ref_lag = h['Close'].iloc[-lag]
        basis_260 = h['Close'].iloc[-282]
        if basis_260 <= 0:
            return None
        mom260 = round(((ref_lag / basis_260) - 1) * 100, 2)

        # ── MOMJT: 6-Monats-Jahrestrend (130T mit Lag) ──
        if len(h) < 152:  # 130 + 22
            return None
        basis_130 = h['Close'].iloc[-152]
        if basis_130 <= 0:
            return None
        momjt = round(((ref_lag / basis_130) - 1) * 100, 2)

        # ── NORMIERUNG für fairen Vergleich ─────────────
        # Alle 3 Komponenten werden auf gleiche Skala gebracht
        # GD130-Abstand direkt nutzbar (bereits in %)
        # MOM260 und MOMJT ebenfalls in %

        # ── COMPOSITE SCORE ──────────────────────────────
        # MOM260 (40%) + MOMJT (30%) + GD130-Abstand (30%)
        score_raw = (
            mom260 * 0.40 +
            momjt  * 0.30 +
            gd130_abstand * 0.30
        )

        # ── OPTIONALER MALUS: extreme GD200-Überdehnung ─
        # Wenn Kurs > 50% über GD200 → kleiner Malus (Rückschlagsrisiko)
        malus = 0.0
        if gd200_abstand > 50:
            # Proportionaler Malus: jeder Prozentpunkt über 50% kostet 0.1 Score-Punkte
            malus = (gd200_abstand - 50) * 0.1
        score = round(score_raw - malus, 2)

        # ── 52W-HOCH für Exit-Signal ──────────────────────
        hoch_52w = h['Close'].tail(252).max() if len(h) >= 252 else h['Close'].max()
        abstand_hoch = round(((k - hoch_52w) / hoch_52w) * 100, 1)

        # ── EXIT-SIGNAL prüfen ───────────────────────────
        # Teilverkauf-Signal: -20% vom 52W-Hoch
        exit_signal = ""
        if abstand_hoch <= -20:
            exit_signal = "⚠️ TEILVERKAUF −20% vom Hoch"

        return {
            'Ticker':        ticker,
            'Kurs':          round(k, 2),
            'GD200':         round(gd200, 2),
            'GD200 Abst.%':  gd200_abstand,
            'GD130':         round(gd130, 2),
            'GD130 Abst.%':  gd130_abstand,
            'MOM260 %':      mom260,
            'MOMJT %':       momjt,
            'Score ⭐':       score,
            '52W Abst.%':    abstand_hoch,
            'Exit Signal':   exit_signal,
            'Ø Vol (60T)':   int(avg_vol),
        }
    except:
        return None

# ═══════════════════════════════════════════════════════
# SEKTOR-LADEN via yfinance
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=86400)
def lade_sektoren(tickers_tuple):
    """Sektoren für alle Kandidaten laden — gecacht."""
    result = {}
    for t in tickers_tuple:
        result[t] = get_sektor(t)
    return result

def sektor_filter(scan_df, max_pro_sektor=2):
    """
    Sektorregel: max. 2 Aktien pro Sektor.
    Nimmt die besten nach Score, filtert Duplikate heraus.
    """
    if scan_df.empty or 'Sektor' not in scan_df.columns:
        return scan_df
    sektor_count = {}
    behalten = []
    for _, row in scan_df.iterrows():
        s = row.get('Sektor', 'Unbekannt')
        count = sektor_count.get(s, 0)
        if count < max_pro_sektor:
            sektor_count[s] = count + 1
            behalten.append(True)
        else:
            behalten.append(False)
    return scan_df[behalten].reset_index(drop=True)

# ═══════════════════════════════════════════════════════
# STABILITÄT — 2-WOCHEN-BESTÄTIGUNG
# ═══════════════════════════════════════════════════════

def init_stabilitaet_db():
    """Speichert wöchentliche Ranking-Snapshots für Stabilitätsprüfung."""
    conn = sqlite3.connect("journal.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS ranking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT,
        ticker TEXT,
        rank INTEGER,
        score REAL
    )''')
    conn.commit()
    conn.close()

def speichere_ranking(scan_df):
    """Aktuelles Ranking in DB speichern."""
    init_stabilitaet_db()
    conn = sqlite3.connect("journal.db")
    heute = datetime.now().strftime('%Y-%m-%d')
    conn.execute("DELETE FROM ranking_history WHERE datum = ?", (heute,))
    for i, row in scan_df.iterrows():
        conn.execute(
            "INSERT INTO ranking_history (datum, ticker, rank, score) VALUES (?,?,?,?)",
            (heute, row['Ticker'], i+1, row.get('Score ⭐', 0))
        )
    conn.commit()
    conn.close()

def pruefe_stabilitaet(ticker, top_n):
    """
    2-Wochen-Bestätigung:
    Kauf nur wenn Ticker in den letzten 2 Wochen kontinuierlich in Top-N war.
    Verkauf erst nach 2 Wochen außerhalb Top-N.
    """
    init_stabilitaet_db()
    conn = sqlite3.connect("journal.db")
    zwei_wochen_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    df = pd.read_sql(
        "SELECT datum, rank FROM ranking_history WHERE ticker=? AND datum>=? ORDER BY datum",
        conn, params=(ticker, zwei_wochen_ago)
    )
    conn.close()
    if df.empty:
        return 'neu', 1  # Neu im System — noch nicht bestätigt
    in_top_n = (df['rank'] <= top_n).all()
    wochen_drin = len(df['datum'].unique())
    if in_top_n and wochen_drin >= 2:
        return 'bestätigt', wochen_drin
    elif in_top_n:
        return 'beobachten', wochen_drin
    else:
        return 'exit_kandidat', wochen_drin

# ═══════════════════════════════════════════════════════
# JOURNAL (unverändert)
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
# VIX AUTOMATISCH LADEN
# ═══════════════════════════════════════════════════════

vix = get_vix()
vt = f"{vix:.1f}" if vix else "—"
vc = "#16a34a" if vix and vix < 25 else "#ca8a04" if vix and vix < 30 else "#ea580c" if vix and vix < 40 else "#dc2626"

# ═══════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════

st.markdown(
    '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;'
    'padding:16px 24px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between">'
    '<div>'
    '<span style="font-family:Inter,sans-serif;font-size:1.2rem;font-weight:700;color:#1a202c">HF · System</span>'
    '<span style="font-size:0.72rem;color:#718096;margin-left:12px">Privates Hedgefonds Dashboard v3.0</span>'
    '</div>'
    f'<div style="display:flex;align-items:center;gap:20px">'
    f'<span style="font-family:DM Mono,monospace;font-size:0.72rem;color:#718096">{datetime.now().strftime("%d.%m.%Y — %H:%M")}</span>'
    f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:6px 14px;text-align:center">'
    f'<span style="font-family:DM Mono,monospace;font-size:0.6rem;color:#718096;display:block">VIX</span>'
    f'<span style="font-family:Inter,sans-serif;font-size:1.1rem;font-weight:700;color:{vc}">{vt}</span>'
    f'</div></div></div>',
    unsafe_allow_html=True
)

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

    champions_df = load_champions()
    tickers_list = champions_df['Ticker'].tolist() if not champions_df.empty else []

    if tickers_list:
        with st.spinner("Lade Breadth-Oszillator..."):
            osc_wert, osc_u, osc_g, _ = calc_oszillator(tuple(tickers_list))
    else:
        osc_wert, osc_u, osc_g = None, 0, 0

    osc_txt = f"{osc_wert:.1f}%" if osc_wert else "—"

    # Positionsberechnung mit neuer Logik
    top_n_default = 5
    pos, neue_kauf, bf_text, bf_farbe = berechne_positionen(top_n_default, osc_wert, vix)
    _, farbe, bg_hell, text = ampel(vix, osc_wert, top_n_default)

    st.markdown(
        f'<div style="background:{bg_hell};border:1px solid {farbe}40;border-left:5px solid {farbe};'
        f'border-radius:10px;padding:20px 24px;margin-bottom:20px">'
        f'<div style="display:flex;align-items:center;gap:16px">'
        f'<span style="font-size:2.2rem">{"🟢" if pos>=4 and neue_kauf else "🟡" if pos>=3 and neue_kauf else "🟠" if pos>=1 else "🔴"}</span>'
        f'<div><div style="font-size:1.1rem;font-weight:700;color:{farbe}">{text}</div>'
        f'<div style="font-size:0.82rem;color:#4a5568;margin-top:4px">'
        f'<b style="color:{farbe}">{pos} Positionen</b> · '
        f'Neue Käufe: <b>{"✅ Ja" if neue_kauf else "❌ Nein"}</b> · '
        f'VIX: <b>{vt}</b> · Breadth: <b>{osc_txt}</b></div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("VIX", vt, "< 25 = ignorieren")
    m2.metric("Breadth", osc_txt, bf_text[:20])
    m3.metric("Positionen", str(pos), f"Neue Käufe: {'Ja' if neue_kauf else 'Nein'}")
    m4.metric("Core", "60%", "10 Compounder")
    m5.metric("Crypto / Gold", "9% / 5%", "BTC+ETH / Hedge")

    st.markdown("---")
    col_links, col_rechts = st.columns(2)

    with col_links:
        st.markdown("**VIX Regelwerk (neu)**")
        vix_val = vix if vix else 0
        for label, beschr, f, aktiv in [
            ("VIX < 25",  "Ignorieren — kein Einfluss",       "#16a34a", vix_val < 25),
            ("VIX 25–40", "Positionsanzahl −2",                "#ca8a04", 25 <= vix_val <= 40),
            ("VIX > 40",  "Keine neuen Käufe",                 "#dc2626", vix_val > 40),
        ]:
            bg = f"{f}12" if aktiv else "#ffffff"
            bd = f if aktiv else "#e2e8f0"
            tag = f' <span style="color:{f};font-size:0.62rem;font-weight:700">◀ AKTIV</span>' if aktiv else ''
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
                f'padding:10px 16px;margin-bottom:6px;display:flex;align-items:center;gap:14px">'
                f'<span style="font-family:DM Mono,monospace;font-size:0.78rem;color:{f};width:90px">{label}</span>'
                f'<span style="font-size:0.78rem;color:#4a5568">{beschr}{tag}</span></div>',
                unsafe_allow_html=True
            )

        st.markdown("**Breadth-Regelwerk (neu)**")
        for label, beschr, f, aktiv in [
            ("≥ 60%",    "Volle Positionsanzahl",              "#16a34a", osc_wert and osc_wert >= 60),
            ("40–60%",   "Reduziert (× 0.6)",                  "#ca8a04", osc_wert and 40 <= osc_wert < 60),
            ("30–40%",   "Stark reduziert — keine neuen Käufe","#ea580c", osc_wert and 30 <= osc_wert < 40),
            ("< 30%",    "Positionen abbauen",                  "#dc2626", osc_wert and osc_wert < 30),
        ]:
            bg = f"{f}12" if aktiv else "#ffffff"
            bd = f if aktiv else "#e2e8f0"
            tag = f' <span style="color:{f};font-size:0.62rem;font-weight:700">◀ AKTIV</span>' if aktiv else ''
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
                f'padding:8px 14px;margin-bottom:5px;display:flex;align-items:center;gap:14px">'
                f'<span style="font-family:DM Mono,monospace;font-size:0.75rem;color:{f};width:70px">{label}</span>'
                f'<span style="font-size:0.75rem;color:#4a5568">{beschr}{tag}</span></div>',
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

        st.markdown("**Ranking-Formel**")
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #2563eb;'
            'border-radius:8px;padding:12px 14px;font-family:DM Mono,monospace;font-size:0.78rem;color:#1e40af">'
            'MOM260 × 40% + MOMJT × 30% + GD130-Abstand × 30%<br>'
            '<span style="color:#718096;font-size:0.7rem">Optional: Malus bei GD200-Überdehnung > 50%</span>'
            '</div>',
            unsafe_allow_html=True
        )

    if not tickers_list:
        st.info("💡 Bitte laden Sie Ihre Champions-CSV im Tab **🏆 Champions** hoch.")

# ═══════════════════════════════════════════════════════
# TAB 2 — CHAMPIONS (unverändert)
# ═══════════════════════════════════════════════════════

with tab2:
    st.markdown("### Champions Pool")

    st.markdown(
        '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 18px;margin-bottom:16px">'
        '<b style="color:#1d4ed8">Champions-CSV hochladen</b><br>'
        '<span style="font-size:0.8rem;color:#3730a3">Format: Spalten <code>Name</code>, <code>WKN</code>, <code>Ticker</code></span>'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_champ = st.file_uploader("Champions CSV", type=['csv'], key="champ_upload", label_visibility="collapsed")
    champions_df = load_champions(uploaded_champ)

    if champions_df.empty:
        st.warning("⚠️ Noch keine Champions-CSV hochgeladen.")
        st.markdown("**Format:** `Name,WKN,Ticker` — eine Zeile pro Champion")
    else:
        st.success(f"✅ {len(champions_df)} Champions geladen")
        cols_show = [c for c in ['Name','WKN','Ticker','Branche','geoPAK10','GewinnKonstanz','VerlustRatio','Trend','Kommentar'] if c in champions_df.columns]
        st.dataframe(champions_df[cols_show], use_container_width=True, height=380, hide_index=True)

        st.markdown("---")
        st.markdown("### Potenzformel")
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #2563eb;'
            'border-radius:8px;padding:12px 16px;font-family:DM Mono,monospace;font-size:0.82rem;color:#1e40af;margin-bottom:8px">'
            'GeoPAK10^0.95 × (1/max(VR, 0.5))^1.2 × (GK/100)^1.5'
            '</div>',
            unsafe_allow_html=True
        )

        col_e, col_a = st.columns([1, 2])

        with col_e:
            st.markdown("**Einzelberechnung**")
            if 'Ticker' in champions_df.columns and 'Name' in champions_df.columns:
                optionen = [f"{row['Ticker']} — {row['Name']}" for _, row in champions_df.iterrows()]
                auswahl = st.selectbox("Champion auswählen", optionen, key="score_select")
                ticker_sel = auswahl.split(" — ")[0] if auswahl else ""
            else:
                ticker_sel = st.text_input("Ticker", placeholder="z.B. NVDA")

            if st.button("Score berechnen"):
                if ticker_sel:
                    with st.spinner(f"Berechne {ticker_sel}..."):
                        g, k, v, s = score_ticker(ticker_sel)
                    if s:
                        st.markdown(
                            f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px">'
                            f'<div style="font-size:1.4rem;font-weight:700;color:#16a34a">Score: {s:.4f}</div></div>',
                            unsafe_allow_html=True
                        )
                        sa, sb, sc = st.columns(3)
                        sa.metric("GeoPAK10", f"{g:.1f}%" if g else "—")
                        sb.metric("Konstanz", f"{k:.1f}%" if k else "—")
                        sc.metric("Verlust-Ratio", f"{v:.2f}" if v else "—")
                    else:
                        st.error("Nicht genug Daten.")

        with col_a:
            st.markdown("**Alle Champions berechnen** (3–5 Min.)")
            if st.button("🚀 Alle berechnen", key="btn_all"):
                results = []
                prog = st.progress(0)
                stat = st.empty()
                for i, row in champions_df.iterrows():
                    ticker = row.get('Ticker','')
                    name = row.get('Name', ticker)
                    prog.progress((i+1)/len(champions_df))
                    stat.caption(f"Berechne {name} ({ticker})...")
                    g, k, v, s = score_ticker(ticker)
                    if s:
                        results.append({'Rang': len(results)+1, 'Name': name, 'Ticker': ticker,
                                        'GeoPAK10 (%)': g, 'Konstanz (%)': k, 'VR': v, 'Score': s})
                prog.empty()
                stat.empty()
                if results:
                    res_df = pd.DataFrame(results).sort_values('Score', ascending=False).reset_index(drop=True)
                    res_df['Rang'] = res_df.index + 1
                    st.success(f"✅ {len(res_df)} Champions berechnet")
                    st.dataframe(res_df, use_container_width=True, height=500, hide_index=True)

# ═══════════════════════════════════════════════════════
# TAB 3 — SATELLITEN (neue Logik, gleiches Layout)
# ═══════════════════════════════════════════════════════

with tab3:
    # SIDEBAR — gleiche Struktur, neue Parameter
    with st.sidebar:
        st.markdown("### ⚙️ Satelliten-Filter")
        st.markdown("---")

        st.markdown("**Universum**")
        uni_upload_side = st.file_uploader("Universe CSV", type=['csv'], key="uni_side", label_visibility="collapsed")
        if uni_upload_side:
            uni_df_side = pd.read_csv(uni_upload_side)
            st.session_state['universe_df'] = uni_df_side
            st.success(f"✅ {len(uni_df_side)} Aktien")

        st.markdown("---")
        st.markdown("**Filter**")
        min_kurs = st.number_input("Min. Kurs (€/$)", value=10.0, step=1.0, format="%.1f")
        min_vol = st.number_input("Min. Ø Volumen (60T)", value=5_000_000, step=500_000, format="%d")

        st.markdown("---")
        st.markdown("**Ranking**")
        top_n = st.slider("Top-N Positionen (Basis)", min_value=3, max_value=20, value=5)
        top_anzeige = st.slider("Anzeige (Top N)", min_value=10, max_value=50, value=50)

        st.markdown("---")
        st.markdown("**Sektorregel**")
        max_sektor = st.number_input("Max. Aktien pro Sektor", value=2, min_value=1, max_value=5)
        lade_sektoren_check = st.checkbox("Sektoren via yfinance laden", value=False,
                                           help="Dauert länger — lädt Sektor für jeden Kandidaten")

        st.markdown("---")
        st.markdown("**Stabilität**")
        st.markdown(
            '<div style="font-size:0.72rem;color:#718096;line-height:1.7">'
            'Kauf: 2 Wochen in Top-N ✅<br>'
            'Verkauf: 2 Wochen außerhalb ❌<br>'
            'Kein Sofort-Exit ohne Bestätigung'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        # Live-Positionsberechnung in Sidebar
        pos_live, neue_kauf_live, bf_txt, bf_farbe = berechne_positionen(top_n, osc_wert, vix)
        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px">'
            f'<p style="font-size:0.65rem;color:#718096;margin:0 0 6px;font-weight:600">AKTUELLE LAGE</p>'
            f'<p style="font-size:0.78rem;margin:2px 0">VIX: <b style="color:{vc}">{vt}</b></p>'
            f'<p style="font-size:0.78rem;margin:2px 0">Breadth: <b>{osc_txt}</b></p>'
            f'<p style="font-size:0.78rem;margin:2px 0">Erlaubte Pos.: <b style="color:{bf_farbe}">{pos_live}</b></p>'
            f'<p style="font-size:0.78rem;margin:2px 0">Neue Käufe: <b>{"✅" if neue_kauf_live else "❌"}</b></p>'
            f'<p style="font-size:0.72rem;color:#718096;margin:4px 0 0">{bf_txt}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    # HAUPTBEREICH
    st.markdown("### Satelliten-Scanner")

    sa1, sa2, sa3, sa4 = st.columns(4)
    sa1.metric("Universum", str(len(st.session_state.get('universe_df', pd.DataFrame()))), "Aktien geladen")
    sa2.metric("Erlaubte Positionen", str(pos_live if 'pos_live' in dir() else vix_pos(vix)), "Breadth + VIX")
    sa3.metric("Einstieg", "€ 2.500", "Fix je Position")
    sa4.metric("Neue Käufe", "✅ Ja" if (neue_kauf_live if 'neue_kauf_live' in dir() else True) else "❌ Nein", "2W Bestätigung nötig")

    st.markdown("---")

    # Ranking-Formel-Info
    st.markdown(
        '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
        'padding:10px 16px;margin-bottom:12px;font-size:0.8rem;color:#15803d">'
        '📊 <b>Ranking-Formel:</b> MOM260 (40%) + MOMJT/6M (30%) + GD130-Abstand (30%) · '
        'GD200 = nur Filter, kein Ranking-Faktor · '
        'Malus bei Überdehnung > 50% über GD200'
        '</div>',
        unsafe_allow_html=True
    )

    if 'universe_df' not in st.session_state:
        st.markdown(
            '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
            'padding:12px 16px;margin-bottom:12px">'
            '<b style="color:#15803d">Universum hochladen</b><br>'
            '<span style="font-size:0.78rem;color:#166534">CSV mit Spalte <code>Ticker</code> und optional <code>Name</code></span>'
            '</div>',
            unsafe_allow_html=True
        )
        uni_upload = st.file_uploader("Universe CSV", type=['csv'], key="uni_main", label_visibility="collapsed")
        if uni_upload:
            uni_df = pd.read_csv(uni_upload)
            st.session_state['universe_df'] = uni_df
            st.rerun()
    else:
        uni_df = st.session_state['universe_df']
        if 'Ticker' in uni_df.columns:
            uni_tickers = uni_df['Ticker'].dropna().tolist()
            name_map = dict(zip(uni_df['Ticker'], uni_df['Name'])) if 'Name' in uni_df.columns else {}

            col_scan, col_save, col_clear = st.columns([1, 1, 3])
            with col_scan:
                scan_btn = st.button("🔍 Scanner starten")
            with col_save:
                if st.button("💾 Ranking speichern", help="Wöchentliches Ranking für Stabilitätsprüfung speichern"):
                    if 'scan_results' in st.session_state and st.session_state.scan_results is not None:
                        speichere_ranking(st.session_state.scan_results)
                        st.success("✅ Ranking gespeichert!")
            with col_clear:
                if st.button("🗑️ Universum zurücksetzen"):
                    del st.session_state['universe_df']
                    st.rerun()

            if scan_btn:
                results = []
                prog2 = st.progress(0)
                status2 = st.empty()
                limit = len(uni_tickers)

                for i, t in enumerate(uni_tickers):
                    prog2.progress((i+1)/limit)
                    if i % 50 == 0:
                        status2.caption(f"Scanne {i+1}/{limit} · Kandidaten: {len(results)}")
                    r = scan(t, min_vol=min_vol, min_kurs=min_kurs)
                    if r:
                        r['Name'] = name_map.get(t, t)
                        results.append(r)

                prog2.empty()
                status2.empty()

                if results:
                    scan_df = pd.DataFrame(results)
                    scan_df = scan_df.sort_values('Score ⭐', ascending=False).reset_index(drop=True)

                    # Sektoren laden (optional)
                    if lade_sektoren_check:
                        with st.spinner("Lade Sektoren via yfinance..."):
                            tickers_tuple = tuple(scan_df['Ticker'].tolist())
                            sektoren = lade_sektoren(tickers_tuple)
                            scan_df['Sektor'] = scan_df['Ticker'].map(sektoren)
                        # Sektorregel anwenden
                        scan_df_gefiltert = sektor_filter(scan_df.head(top_anzeige), max_sektor)
                    else:
                        scan_df_gefiltert = scan_df.copy()

                    # Stabilität prüfen
                    stabilitaet = []
                    for _, row in scan_df_gefiltert.iterrows():
                        status_stab, wochen = pruefe_stabilitaet(row['Ticker'], top_n)
                        if status_stab == 'bestätigt':
                            stabilitaet.append(f"✅ {wochen}W bestätigt")
                        elif status_stab == 'beobachten':
                            stabilitaet.append(f"👁️ {wochen}W beobachten")
                        elif status_stab == 'exit_kandidat':
                            stabilitaet.append(f"⚠️ Exit-Kandidat")
                        else:
                            stabilitaet.append("🆕 Neu")
                    scan_df_gefiltert['Stabilität'] = stabilitaet

                    # Ranking-Nummern
                    scan_df_gefiltert.insert(0, '#', scan_df_gefiltert.index + 1)

                    # In Session State speichern für "Ranking speichern"
                    st.session_state.scan_results = scan_df_gefiltert

                    st.success(f"✅ {len(results)} Kandidaten · Top {min(top_anzeige, len(scan_df_gefiltert))} angezeigt")

                    # Kaufsignal-Hinweis
                    if not (neue_kauf_live if 'neue_kauf_live' in dir() else True):
                        st.warning("⚠️ Aktuell keine neuen Käufe erlaubt (Breadth < 40% oder VIX > 40). Nur bestehende Positionen halten.")

                    # Spaltenreihenfolge
                    cols_show = ['#', 'Name', 'Ticker', 'Kurs', 'GD200', 'GD200 Abst.%',
                                 'GD130', 'GD130 Abst.%', 'MOM260 %', 'MOMJT %',
                                 'Score ⭐', '52W Abst.%', 'Exit Signal', 'Stabilität']
                    if 'Sektor' in scan_df_gefiltert.columns:
                        cols_show.insert(4, 'Sektor')

                    final_cols = [c for c in cols_show if c in scan_df_gefiltert.columns]
                    st.dataframe(
                        scan_df_gefiltert[final_cols].head(top_anzeige),
                        use_container_width=True,
                        height=600,
                        hide_index=True
                    )

                    # Kauf-Regeln Zusammenfassung
                    with st.expander("📋 Kauf- & Verkaufs-Regeln"):
                        st.markdown(
                            "**Einstieg — alle Bedingungen müssen erfüllt sein:**\n"
                            "- ✅ Kurs über GD200\n"
                            "- ✅ Im Top-Ranking (Score ⭐)\n"
                            "- ✅ 2 Wochen bestätigt (Spalte: Stabilität)\n"
                            "- ✅ Positionslimit nicht erreicht\n"
                            "- ✅ Sektorregel: max. 2 pro Sektor\n"
                            "- ✅ Neue Käufe erlaubt (Breadth ≥ 40% und VIX ≤ 40)\n\n"
                            "**Exit-Regeln (kein Sofort-Exit):**\n"
                            "- ⚠️ **Teilverkauf:** −20% vom 52W-Hoch → 50% der Position verkaufen\n"
                            "- 🔴 **Vollverkauf:** 2 Wochen unter Strukturlevel\n"
                            "- 🔴 **Vollverkauf:** 20–30% unter Ausbruchsniveau\n\n"
                            "**Rebalancing:** Wöchentlich — keine täglichen Umschichtungen.\n"
                            "Speichern Sie das Ranking nach jedem Scan mit '💾 Ranking speichern'."
                        )
                else:
                    st.warning("Keine Kandidaten nach Filterung.")

# ═══════════════════════════════════════════════════════
# TAB 4 — CORE (unverändert)
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

    ziel = depot / 10
    core_rows = []
    for p in CORE_POSITIONEN:
        kurs = get_price(p['ticker'])
        core_rows.append({
            'Ticker': p['ticker'], 'Name': p['name'], 'Sektor': p['sektor'],
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
        schwaechste = st.selectbox("Schwächste Position", [f"{p['ticker']} — {p['name']}" for p in CORE_POSITIONEN])

    if st.button("Kapitalfluss berechnen"):
        sat = min(2500.0, erloese)
        rest = erloese - sat
        core_ticker = schwaechste.split(" — ")[0]
        fehl = min(rest, ziel * 0.25)
        cash = max(0, rest - fehl)

        def sr(l, v, c="#2563eb"):
            return (f'<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9">'
                    f'<span style="font-size:0.85rem;color:#4a5568">{l}</span>'
                    f'<span style="font-family:DM Mono,monospace;font-size:0.85rem;font-weight:600;color:{c}">{v}</span></div>')

        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:18px;margin-top:8px">'
            f'<p style="font-size:0.68rem;color:#718096;margin-bottom:10px;font-weight:600">KAPITALFLUSS-HIERARCHIE</p>'
            + sr("① Satellit-Rotation (2.500€)", f"€ {sat:,.0f}", "#2563eb")
            + sr(f"② Core Nachkauf {core_ticker}", f"€ {fehl:,.0f}", "#16a34a")
            + sr("③ Cash parken", f"€ {cash:,.0f}", "#718096")
            + '</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("**Allokations-Kalkulator**")
    ak = st.columns(4)
    for i, (name, pct, f) in enumerate([('Core', 60, '#2563eb'), ('Satelliten', 25, '#ca8a04'), ('Crypto', 9, '#7c3aed'), ('Gold', 5, '#b45309')]):
        with ak[i]:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center">'
                f'<p style="font-size:0.72rem;color:#718096;margin:0 0 4px;font-weight:600">{name.upper()}</p>'
                f'<p style="font-size:1.5rem;font-weight:700;color:{f};margin:0">{pct}%</p>'
                f'<p style="font-family:DM Mono,monospace;font-size:0.78rem;color:#1a202c;margin:6px 0 2px">€ {depot*pct/100:,.0f}</p>'
                f'<p style="font-size:0.68rem;color:#718096;margin:0">+ € {spar*pct/100:,.0f}/Mo.</p>'
                f'</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════
# TAB 5 — OSZILLATOR (neue Breadth-Logik)
# ═══════════════════════════════════════════════════════

with tab5:
    st.markdown("### Breadth-Oszillator")
    st.caption("Anteil der Aktien über GD200 — Grundlage für Positionsberechnung.")

    champions_df2 = load_champions()
    if champions_df2.empty:
        st.warning("Bitte zuerst Champions-CSV im Tab **🏆 Champions** hochladen.")
    else:
        tickers2 = champions_df2['Ticker'].tolist()
        with st.spinner("Berechne Breadth-Oszillator..."):
            ow, ou, og, od = calc_oszillator(tuple(tickers2))
        osc_txt2 = f"{ow:.1f}%" if ow else "—"

        bf2, bf2_text, bf2_farbe, neue_ok = breadth_faktor(ow)

        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Breadth-Oszillator", osc_txt2, bf2_text[:25])
        o2.metric("Über GD200", f"{ou}", f"von {og} Aktien")
        o3.metric("Breadth-Faktor", f"× {bf2:.1f}", "Positionsmultiplikator")
        o4.metric("VIX", vt, "< 25 = kein Einfluss")

        st.markdown("---")

        # Positionsberechnung anzeigen
        top_n_osc = st.number_input("Top-N Basis (für Berechnung)", value=5, min_value=1, max_value=20, key="osc_topn")
        pos_calc, neue_kauf_calc, _, _ = berechne_positionen(top_n_osc, ow, vix)

        st.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:16px">'
            f'<p style="font-size:0.68rem;color:#718096;font-weight:600;margin-bottom:8px">POSITIONSBERECHNUNG</p>'
            f'<div style="display:flex;gap:24px;flex-wrap:wrap">'
            f'<div><span style="font-size:0.75rem;color:#718096">Basis (Top-N)</span><br>'
            f'<span style="font-size:1.2rem;font-weight:700">{top_n_osc}</span></div>'
            f'<div><span style="font-size:0.75rem;color:#718096">× Breadth-Faktor</span><br>'
            f'<span style="font-size:1.2rem;font-weight:700;color:{bf2_farbe}">{bf2:.1f}</span></div>'
            f'<div><span style="font-size:0.75rem;color:#718096">= Nach Breadth</span><br>'
            f'<span style="font-size:1.2rem;font-weight:700">{max(1,round(top_n_osc*bf2))}</span></div>'
            f'<div><span style="font-size:0.75rem;color:#718096">− VIX-Korrektur</span><br>'
            f'<span style="font-size:1.2rem;font-weight:700;color:{vc}">{"−2" if vix and 25<=vix<=40 else "0" if not vix or vix<25 else "alle"}</span></div>'
            f'<div><span style="font-size:0.75rem;color:#718096">= Finale Positionen</span><br>'
            f'<span style="font-size:1.4rem;font-weight:800;color:{"#16a34a" if neue_kauf_calc else "#dc2626"}">{pos_calc}</span></div>'
            f'<div><span style="font-size:0.75rem;color:#718096">Neue Käufe</span><br>'
            f'<span style="font-size:1.2rem">{"✅ Ja" if neue_kauf_calc else "❌ Nein"}</span></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        if ow:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=ow,
                title={'text': "Breadth-Oszillator (% über GD200)", 'font': {'color': '#1a202c', 'size': 14}},
                number={'suffix': '%', 'font': {'color': '#2563eb', 'size': 36}},
                gauge={
                    'axis': {'range': [0,100], 'tickcolor': '#718096'},
                    'bar': {'color': '#16a34a' if ow>=60 else '#ca8a04' if ow>=40 else '#dc2626'},
                    'bgcolor': '#f8fafc', 'bordercolor': '#e2e8f0',
                    'steps': [
                        {'range': [0, 30],  'color': '#fef2f2'},
                        {'range': [30, 40], 'color': '#fff7ed'},
                        {'range': [40, 60], 'color': '#fefce8'},
                        {'range': [60, 100],'color': '#f0fdf4'},
                    ],
                    'threshold': {
                        'line': {'color': '#1d4ed8', 'width': 3},
                        'thickness': 0.75,
                        'value': 60
                    }
                }
            ))
            fig.update_layout(paper_bgcolor='#ffffff', font={'color': '#1a202c'}, height=280, margin=dict(t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Breadth-Stufen
        st.markdown("**Breadth-Stufen & Positionsregeln**")
        for stand, beschr, f, aktiv in [
            ("≥ 60%",  "Volle Positionsanzahl (× 1.0) — neue Käufe erlaubt",     "#16a34a", ow and ow >= 60),
            ("40–60%", "Reduziert (× 0.6) — neue Käufe noch erlaubt",            "#ca8a04", ow and 40 <= ow < 60),
            ("30–40%", "Stark reduziert (× 0.3) — KEINE neuen Käufe",            "#ea580c", ow and 30 <= ow < 40),
            ("< 30%",  "Positionen abbauen (× 0.0) — alle Positionen reduzieren","#dc2626", ow and ow < 30),
        ]:
            bd = f if aktiv else "#e2e8f0"
            bg = f"{f}12" if aktiv else "#ffffff"
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bd};border-radius:7px;'
                f'padding:9px 14px;margin-bottom:5px;display:flex;gap:16px;align-items:center">'
                f'<span style="font-family:DM Mono,monospace;color:{f};width:65px;font-size:0.8rem">{stand}</span>'
                f'<span style="color:#2d3748;font-size:0.82rem">{beschr}</span>'
                f'{"<span style=color:"+f+";font-size:0.65rem;font-weight:700;margin-left:auto>◀ AKTUELL</span>" if aktiv else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

        if not od.empty:
            with st.expander("📋 Alle Aktien vs. GD200"):
                if 'Name' in champions_df2.columns:
                    od = od.merge(champions_df2[['Ticker','Name']], on='Ticker', how='left')
                cols_od = ['Name','Ticker','Kurs','GD200','Abstand %','Status'] if 'Name' in od.columns else ['Ticker','Kurs','GD200','Abstand %','Status']
                st.dataframe(od[cols_od].sort_values('Abstand %', ascending=False), use_container_width=True, height=400, hide_index=True)

# ═══════════════════════════════════════════════════════
# TAB 6 — CHECKLISTE (unverändert)
# ═══════════════════════════════════════════════════════

with tab6:
    st.markdown("### Wöchentliche Checkliste")
    pos_check = pos_live if 'pos_live' in dir() else vix_pos(vix)
    st.markdown(
        f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
        f'padding:10px 16px;margin-bottom:16px;font-size:0.82rem;color:#1d4ed8">'
        f'KW {datetime.now().isocalendar()[1]} · {datetime.now().strftime("%d.%m.%Y")} · '
        f'VIX: <b>{vt}</b> · Breadth: <b>{osc_txt}</b> · Erlaubte Positionen: <b>{pos_check}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    cl1, cl2 = st.columns(2)
    with cl1:
        st.markdown("**🛰️ Satelliten-Check**")
        c1 = st.checkbox("Alle Positionen noch in Top-N?")
        c2 = st.checkbox("2-Wochen-Bestätigung geprüft?")
        c3 = st.checkbox("−20% vom Hoch geprüft (Teilverkauf)?")
        c4 = st.checkbox("Sektorregel eingehalten (max. 2)?")
        c5 = st.checkbox("Positionslimit eingehalten?")
        c6 = st.checkbox("Wöchentliches Rebalancing durchgeführt?")
        st.markdown("**💼 Core-Check**")
        c7 = st.checkbox("Gewichtungen berechnet?")
        c8 = st.checkbox("Schwächste Position identifiziert?")
        c9 = st.checkbox("Nachkauf-Budget festgelegt?")

    with cl2:
        st.markdown("**📊 Markt-Check**")
        c10 = st.checkbox("VIX abgelesen?")
        c11 = st.checkbox("Breadth-Oszillator abgelesen?")
        c12 = st.checkbox("Positionsanzahl berechnet (Top-N × Breadth − VIX)?")
        st.markdown("**🔍 Neue Kandidaten**")
        c13 = st.checkbox("Ranking-Scan durchgeführt?")
        c14 = st.checkbox("Ranking gespeichert (💾)?")
        c15 = st.checkbox("Branchen-Check (max. 2/Sektor)?")
        c16 = st.checkbox("Neue Käufe erlaubt (Breadth + VIX)?")

    checks = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16]
    done = sum(checks)
    pct_c = done/len(checks)
    fc = "#16a34a" if pct_c>=0.8 else "#ca8a04" if pct_c>=0.5 else "#dc2626"

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin:12px 0">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
        f'<span style="font-size:0.78rem;color:#718096;font-weight:600">FORTSCHRITT</span>'
        f'<span style="font-size:0.85rem;font-weight:700;color:{fc}">{done}/{len(checks)} erledigt</span></div>'
        f'<div style="height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden">'
        f'<div style="width:{pct_c*100:.0f}%;height:100%;background:{fc};border-radius:4px"></div></div></div>',
        unsafe_allow_html=True
    )

    notizen_cl = st.text_area("Notizen", placeholder="Beobachtungen, Entscheidungen...", key="cl_n")
    if st.button("✅ Checkliste speichern"):
        checklist_save(vix, osc_wert, pos_check, notizen_cl)
        st.success("✅ Gespeichert!")

# ═══════════════════════════════════════════════════════
# TAB 7 — JOURNAL (unverändert)
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
        j_name = st.text_input("Name", placeholder="z.B. NVIDIA")
        j_typ = st.selectbox("Typ", ["Satellit — Kauf","Satellit — Verkauf","Core — Nachkauf","Core — Rotation","Notiz"])
        j_kurs = st.number_input("Kurs ($)", value=0.0, step=0.01, format="%.2f")
        j_betrag = st.number_input("Betrag (€)", value=2500.0, step=100.0, format="%.0f")
        j_grund = st.text_area("Einstiegsbegründung", placeholder="Score, GD130-Abstand, MOM260...", height=80)
        j_trigger = st.text_input("Ausstiegs-Trigger", placeholder="z.B. 2W außerhalb Top-N")

        if st.button("💾 Speichern"):
            if j_ticker and j_grund:
                trade_add(j_ticker, j_name, j_typ, j_kurs, j_betrag, j_grund, j_trigger)
                st.success("✅ Gespeichert!")
                st.rerun()
            else:
                st.error("Ticker und Begründung erforderlich.")

    with jc2:
        st.markdown("**Letzte Einträge**")
        if trades.empty:
            st.info("Noch keine Einträge.")
        else:
            for _, row in trades.head(10).iterrows():
                pnl_html = ""
                if row.get('pnl') and not pd.isna(row.get('pnl', float('nan'))):
                    pc = "#16a34a" if row['pnl'] > 0 else "#dc2626"
                    pnl_html = f'<span style="color:{pc};font-weight:600"> € {row["pnl"]:+,.0f}</span>'
                offen = pd.isna(row.get('ausstieg_datum'))
                bd_c = "#2563eb" if offen else "#e2e8f0"
                name_d = f" — {row['name']}" if row.get('name') and not pd.isna(row.get('name','')) else ""
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:3px solid {bd_c};'
                    f'border-radius:8px;padding:12px 14px;margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
                    f'<span style="font-weight:700;color:#1a202c">{row["ticker"]}'
                    f'<span style="font-weight:400;color:#718096;font-size:0.8rem">{name_d}</span></span>'
                    f'<span style="font-size:0.65rem;color:#718096;font-family:DM Mono,monospace">'
                    f'{row["datum"]} · {row["typ"]}</span></div>'
                    f'<p style="font-size:0.78rem;color:#718096;margin:2px 0">{str(row.get("begruendung",""))[:100]}</p>'
                    f'<p style="font-size:0.72rem;color:#718096;margin:2px 0">Exit: {row.get("ausstieg_trigger","—")}{pnl_html}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════

st.markdown(
    '<div style="text-align:center;padding:20px 0 8px;border-top:1px solid #e2e8f0;margin-top:24px">'
    '<p style="font-size:0.68rem;color:#cbd5e0">'
    'HF · System v3.0 — Privates Hedgefonds Dashboard — Streng vertraulich'
    '</p></div>',
    unsafe_allow_html=True
)
