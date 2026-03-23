import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Champions Auswahl",
    page_icon="🏆",
    layout="wide"
)

# ============================================================
# Helles Layout
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f7f9fc;
    }
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #1f2937;
    }
    [data-testid="stMetricValue"] {
        color: #111827;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        border-bottom: 1px solid #dbe2ea;
        padding: 4px 4px 0 4px;
        border-radius: 10px 10px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: #ffffff;
        border-radius: 8px 8px 0 0;
        color: #4b5563;
        padding: 0 14px;
    }
    .stTabs [aria-selected="true"] {
        color: #111827 !important;
        border-bottom: 3px solid #2563eb !important;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #dbe2ea;
        border-radius: 10px;
        background-color: #ffffff;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Utils
# ============================================================

@st.cache_data(show_spinner=False, ttl=60 * 60)
def fetch_ohlc(ticker_list, start, end):
    """Robuster OHLCV-Download. Bulk -> Fallback per Ticker."""
    if isinstance(ticker_list, str):
        tickers = [t.strip() for t in ticker_list.split(",") if t.strip()]
    else:
        tickers = [str(t).strip() for t in ticker_list if str(t).strip()]
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()

    end_plus = pd.to_datetime(end) + pd.Timedelta(days=1)
    start_dt = pd.to_datetime(start)

    def _extract_close_vol(df_any, t_sym=None):
        if df_any is None or df_any.empty:
            return None, None
        try:
            if isinstance(df_any.columns, pd.MultiIndex):
                if t_sym is None:
                    return None, None
                sub = df_any[t_sym]
                close = sub["Adj Close"] if "Adj Close" in sub.columns else sub.get("Close")
                vol = sub.get("Volume")
            else:
                close = df_any["Adj Close"] if "Adj Close" in df_any.columns else df_any.get("Close")
                vol = df_any.get("Volume")
            if close is None or close.dropna().empty:
                return None, None
            close = close.rename(t_sym if t_sym else close.name)
            if vol is None:
                vol = pd.Series(dtype=float, name=t_sym)
            else:
                vol = vol.rename(t_sym if t_sym else vol.name)
            return close, vol
        except Exception:
            return None, None

    close_cols = {}
    vol_cols = {}

    bulk = None
    try:
        bulk = yf.download(
            tickers=" ".join(tickers),
            start=start_dt,
            end=end_plus,
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        bulk = None

    if bulk is not None and not bulk.empty:
        for t in tickers:
            if isinstance(bulk.columns, pd.MultiIndex):
                if t in bulk.columns.get_level_values(0):
                    c, v = _extract_close_vol(bulk, t)
                else:
                    c, v = None, None
            else:
                c, v = _extract_close_vol(bulk, t)
            if c is not None:
                close_cols[t] = c
                if v is not None:
                    vol_cols[t] = v

    missing = [t for t in tickers if t not in close_cols]
    for t in missing:
        try:
            single = yf.download(
                tickers=t,
                start=start_dt,
                end=end_plus,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            c, v = _extract_close_vol(single, t)
            if c is not None:
                close_cols[t] = c
                if v is not None:
                    vol_cols[t] = v
        except Exception:
            continue

    if not close_cols:
        return pd.DataFrame(), pd.DataFrame()

    price = pd.concat(close_cols.values(), axis=1).sort_index()
    volume = pd.concat(vol_cols.values(), axis=1).reindex(price.index) if vol_cols else pd.DataFrame(index=price.index)

    price = price.dropna(axis=1, how="all")
    volume = volume.drop(columns=[c for c in volume.columns if c not in price.columns], errors="ignore")
    price = price.dropna(how="all")
    volume = volume.reindex(price.index)

    return price, volume


def pct_change_over_window(series: pd.Series, days: int) -> float:
    s = series.dropna()
    if len(s) < days + 1:
        return np.nan
    start_val = s.iloc[-(days + 1)]
    end_val = s.iloc[-1]
    if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0:
        return np.nan
    return (end_val / start_val - 1.0) * 100.0


def safe_sma(series: pd.Series, window: int) -> pd.Series:
    if series is None or series.empty:
        return series
    return series.rolling(window=window, min_periods=max(5, window // 5)).mean()


def zscore_last(value: float, mean: float, std: float) -> float:
    if std is None or std == 0 or np.isnan(std):
        return 0.0
    return (value - mean) / std


def volume_score(vol_series: pd.Series, lookback=60):
    if vol_series is None or vol_series.dropna().empty:
        return np.nan
    cur = vol_series.dropna().iloc[-1]
    base = vol_series.rolling(lookback, min_periods=max(5, lookback // 5)).mean().iloc[-1]
    if base is None or base == 0 or pd.isna(base) or pd.isna(cur):
        return np.nan
    return float(np.clip(cur / base, 0.5, 2.0))


def logp(x):
    if pd.isna(x):
        return np.nan
    return np.sign(x) * np.log1p(abs(x))


# ============================================================
# Indikatoren + Score
# ============================================================

def compute_indicators(price_df: pd.DataFrame, volume_df: pd.DataFrame, benchmark_df=None):
    results = []
    mom130_universe = {t: pct_change_over_window(price_df[t], 130) for t in price_df.columns}
    mom130_series = pd.Series(mom130_universe).astype(float)
    mu, sigma = mom130_series.mean(), mom130_series.std(ddof=0)

    bm_return = None
    if benchmark_df is not None and not benchmark_df.empty:
        bm_return = pct_change_over_window(benchmark_df.iloc[:, 0], 130)

    for t in price_df.columns:
        s = price_df[t].dropna()
        v = volume_df[t].dropna() if (isinstance(volume_df, pd.DataFrame) and t in volume_df) else pd.Series(dtype=float)
        if s.empty or len(s) < 200:
            continue

        last = s.iloc[-1]
        sma50 = safe_sma(s, 50).iloc[-1]
        sma200 = safe_sma(s, 200).iloc[-1]

        mom260 = pct_change_over_window(s, 260)
        mom130 = pct_change_over_window(s, 130)

        rs_130 = mom130
        rs_z = zscore_last(rs_130, mu, sigma) if not np.isnan(rs_130) else np.nan

        vol_sc = volume_score(v, 60)
        avg_vol = v.rolling(60).mean().iloc[-1] if not v.empty else np.nan

        d50 = (last / sma50 - 1.0) * 100.0 if pd.notna(sma50) and sma50 != 0 else np.nan
        d200 = (last / sma200 - 1.0) * 100.0 if pd.notna(sma200) and sma200 != 0 else np.nan

        sig50 = "Über GD50" if pd.notna(sma50) and last >= sma50 else "Unter GD50"
        sig200 = "Über GD200" if pd.notna(sma200) and last >= sma200 else "Unter GD200"

        high52 = s[-260:].max() if len(s) >= 260 else s.max()
        dd52 = (last / high52 - 1.0) * 100.0 if pd.notna(high52) and high52 != 0 else np.nan

        vol = s.pct_change().std() * np.sqrt(252)
        rs_vs_bm = mom130 - bm_return if bm_return is not None else np.nan

        score = (
            0.40 * logp(mom260)
            + 0.30 * logp(mom130)
            + 0.20 * (0 if np.isnan(rs_z) else rs_z)
            + 0.10 * (0 if np.isnan(vol_sc) else (vol_sc - 1.0))
        )
        score = 0.0 if np.isnan(score) else float(score)

        results.append(
            {
                "Ticker": t,
                "Kurs aktuell": round(last, 2),
                "MOM260 (%)": round(mom260, 2),
                "MOM130 (%)": round(mom130, 2),
                "RS (130T) (%)": round(rs_130, 2),
                "RS z-Score": round(rs_z, 2),
                "RS vs Benchmark (%)": round(rs_vs_bm, 2) if not np.isnan(rs_vs_bm) else np.nan,
                "Volumen-Score": round(vol_sc, 2) if not np.isnan(vol_sc) else np.nan,
                "Ø Volumen (60T)": round(avg_vol, 0) if not np.isnan(avg_vol) else np.nan,
                "Abstand GD50 (%)": round(d50, 2),
                "Abstand GD200 (%)": round(d200, 2),
                "GD50-Signal": sig50,
                "GD200-Signal": sig200,
                "52W-Drawdown (%)": round(dd52, 2),
                "Volatilität (ann.)": round(vol, 2) if not np.isnan(vol) else np.nan,
                "Momentum-Score": round(score, 3),
            }
        )

    df = pd.DataFrame(results)
    if df.empty:
        return df
    df = df.sort_values("Momentum-Score", ascending=False).reset_index(drop=True)
    df["Rank"] = np.arange(1, len(df) + 1)
    return df


# ============================================================
# Rebalancing
# ============================================================

def weekly_first_trading_days(idx: pd.DatetimeIndex):
    s = pd.Series(1, index=idx)
    grp = s.groupby(pd.Grouper(freq="W-MON"))
    firsts = []
    for _, g in grp:
        if not g.empty:
            firsts.append(g.index[0])
    return firsts


def monthly_first_trading_days(idx: pd.DatetimeIndex):
    s = pd.Series(1, index=idx)
    grp = s.groupby(pd.Grouper(freq="M"))
    firsts = []
    for _, g in grp:
        if not g.empty:
            firsts.append(g.index[0])
    return firsts


def run_backtest(prices, volumes, benchmark, start_date, end_date,
                 top_n=10, min_volume=5_000_000, max_dd52=-50,
                 max_volatility=2.0, apply_benchmark=True,
                 cost_bps=10.0, slippage_bps=5.0, mode="weekly"):

    idx = prices.index[(prices.index >= pd.to_datetime(start_date)) & (prices.index <= pd.to_datetime(end_date))]
    if len(idx) < 260:
        return pd.DataFrame(), pd.DataFrame()

    rebal_days = weekly_first_trading_days(idx) if mode == "weekly" else monthly_first_trading_days(idx)
    rebal_days = [d for d in rebal_days if d >= idx.min() and d <= idx.max()]
    if len(rebal_days) < 2:
        return pd.DataFrame(), pd.DataFrame()

    port_val = 1.0
    weights_prev = pd.Series(0.0, index=prices.columns)
    equity, logs = [], []
    tc = (cost_bps + slippage_bps) / 10000.0

    for i in range(len(rebal_days) - 1):
        asof, nxt = rebal_days[i], rebal_days[i + 1]
        p_slice = prices.loc[:asof]
        v_slice = volumes.loc[:asof]

        bm_slice = None
        if benchmark is not None:
            bm_slice = pd.DataFrame({"BM": benchmark.loc[:asof].dropna()})
            if bm_slice.empty:
                bm_slice = None

        snap = compute_indicators(p_slice, v_slice, benchmark_df=bm_slice)
        if snap.empty:
            continue

        filt = snap.copy()
        filt = filt[filt["Ø Volumen (60T)"] >= min_volume]
        filt = filt[filt["52W-Drawdown (%)"] >= max_dd52]
        filt = filt[filt["Volatilität (ann.)"] <= max_volatility]
        if apply_benchmark and "RS vs Benchmark (%)" in filt.columns:
            filt = filt[filt["RS vs Benchmark (%)"] > 0]
        filt = filt.sort_values("Momentum-Score", ascending=False).reset_index(drop=True)

        sel = filt.head(top_n).copy()
        new_weights = pd.Series(0.0, index=prices.columns)
        if not sel.empty:
            w = 1.0 / len(sel)
            new_weights.loc[sel["Ticker"].values] = w

        rets = prices.loc[asof:nxt].pct_change().fillna(0)
        gross_return = (rets.iloc[1:] * weights_prev).sum(axis=1).add(1).prod() - 1.0 if len(rets) > 1 else 0.0

        turnover = float((new_weights - weights_prev).abs().sum())
        cost = turnover * tc
        net_return = gross_return - cost
        port_val *= (1.0 + net_return)

        equity.append((nxt, port_val))
        logs.append({
            "Date": asof,
            "NumHold": len(sel),
            "Turnover": turnover,
            "GrossRet": gross_return,
            "Cost": cost,
            "NetRet": net_return,
            "PortVal": port_val,
        })
        weights_prev = new_weights.copy()

    eq_df = pd.DataFrame(equity, columns=["Date", "Equity"]).set_index("Date")
    logs_df = pd.DataFrame(logs)
    return eq_df, logs_df


# ============================================================
# Sidebar
# ============================================================

st.sidebar.header("Einstellungen")
top_n = st.sidebar.number_input("Top-N", min_value=3, max_value=50, value=10, step=1)
start_date = st.sidebar.date_input("Startdatum", value=datetime.today() - timedelta(days=900))
end_date = st.sidebar.date_input("Enddatum", value=datetime.today())

st.sidebar.markdown("### Filter")
min_volume = st.sidebar.number_input("Min. Ø Volumen (60T)", min_value=0, value=4_000_000, step=100_000)
max_dd52 = st.sidebar.slider("Max. Drawdown zum 52W-Hoch (%)", -100, 0, -50, step=5)
max_volatility = st.sidebar.slider("Max. Volatilität (ann.)", 0.0, 3.0, 2.0, step=0.05)
apply_benchmark = st.sidebar.checkbox("Nur Aktien > Benchmark (130T)", value=True)
benchmark_ticker = st.sidebar.text_input("Benchmark-Ticker", "SPY")

st.sidebar.markdown("### Breadth-Steuerung")
breadth_top_x = st.sidebar.number_input(
    "X Aktien für GD200-Breadth",
    min_value=5,
    max_value=500,
    value=20,
    step=1,
)
min_dyn_n = st.sidebar.number_input("Min. Positionen dynamisch", min_value=0, max_value=50, value=3)
max_dyn_n = st.sidebar.number_input("Max. Positionen dynamisch", min_value=0, max_value=50, value=10)

st.sidebar.markdown("### Backtest")
mode = st.sidebar.radio("Rebalancing-Modus", ["weekly", "monthly"], index=1)
cost_bps = st.sidebar.number_input("Kommission (bps)", min_value=0.0, value=10.0, step=1.0)
slip_bps = st.sidebar.number_input("Slippage (bps)", min_value=0.0, value=5.0, step=1.0)

# Grenzen absichern
max_dyn_n = max(min_dyn_n, max_dyn_n)
min_dyn_n = min(min_dyn_n, top_n)
max_dyn_n = min(max_dyn_n, top_n)
breadth_top_x = max(top_n, breadth_top_x)

# ============================================================
# Daten laden
# ============================================================

st.title("Champions Auswahl")
st.caption("Helle Version ohne Dark Mode. Analyse, Handlungsempfehlungen und Backtest.")

uploaded = st.file_uploader("CSV mit Ticker und optional Name", type=["csv"])
tickers_txt = st.text_input("Oder Ticker manuell", "AAPL, MSFT, TSLA, NVDA, META, AVGO")
portfolio_txt = st.text_input("Optional. Aktuelle Portfolio-Ticker", "")

name_map = {}
if uploaded is not None:
    try:
        df_in = pd.read_csv(uploaded)
        if "Ticker" in df_in.columns:
            if "Name" in df_in.columns:
                name_map = dict(zip(df_in["Ticker"].astype(str), df_in["Name"].astype(str)))
            tickers_txt = ", ".join(df_in["Ticker"].astype(str).tolist())
            st.success(f"{len(df_in)} Ticker aus CSV geladen.")
        else:
            st.error("CSV braucht mindestens die Spalte 'Ticker'.")
    except Exception as e:
        st.error(f"CSV konnte nicht gelesen werden: {e}")

tickers = [t.strip().upper() for t in tickers_txt.split(",") if t.strip()]
portfolio = set([t.strip().upper() for t in portfolio_txt.split(",") if t.strip()])

if not tickers:
    st.stop()

with st.spinner("Lade Kursdaten"):
    prices, volumes = fetch_ohlc(tickers, start_date, end_date)
    bm_prices, _ = fetch_ohlc([benchmark_ticker], start_date, end_date)

st.info(f"Geladene Ticker: {len(tickers)}. Preise: {prices.shape}. Volumen: {volumes.shape}.")

if prices.empty:
    st.warning("Keine Kursdaten geladen. Prüfe Ticker, Internet und Datumsspanne.")
    st.stop()

# ============================================================
# Analyse
# ============================================================

df = compute_indicators(prices, volumes, benchmark_df=bm_prices)
if df.empty:
    st.warning("Kennzahlen konnten nicht berechnet werden. Es fehlt Historie.")
    st.stop()

df["Name"] = df["Ticker"].map(name_map).fillna(df["Ticker"])
df["Im Portfolio"] = df["Ticker"].isin(portfolio)

filtered = df.copy()
filtered = filtered[filtered["Ø Volumen (60T)"] >= min_volume]
filtered = filtered[filtered["52W-Drawdown (%)"] >= max_dd52]
filtered = filtered[filtered["Volatilität (ann.)"] <= max_volatility]
if apply_benchmark and "RS vs Benchmark (%)" in filtered.columns:
    filtered = filtered[filtered["RS vs Benchmark (%)"] > 0]
filtered = filtered.sort_values("Momentum-Score", ascending=False).reset_index(drop=True)
filtered["Rank"] = np.arange(1, len(filtered) + 1)

# ============================================================
# Tabs
# ============================================================

tab1, tab2, tab3 = st.tabs(["Analyse", "Handlungsempfehlungen", "Backtest"])

with tab1:
    st.subheader("Analyse")
    st.dataframe(filtered, use_container_width=True)

with tab2:
    st.subheader("Handlungsempfehlungen")

    top_universe = filtered.head(int(breadth_top_x)).copy()
    total = len(top_universe)

    if total > 0:
        gd200_above = int((top_universe["GD200-Signal"] == "Über GD200").sum())
        share = gd200_above / total
    else:
        gd200_above = 0
        share = 0.0

    dyn_n_raw = int(round(share * top_n))
    dyn_n = int(np.clip(dyn_n_raw, min_dyn_n, max_dyn_n)) if total > 0 else 0

    fix_df = filtered.head(top_n).copy()
    fix_df["Handlung"] = np.where(fix_df["Im Portfolio"], "Halten", "Kaufen")

    dyn_df = filtered.head(dyn_n).copy()
    if not dyn_df.empty:
        dyn_df["Handlung"] = np.where(dyn_df["Im Portfolio"], "Halten", "Kaufen")

    c1, c2, c3 = st.columns(3)
    c1.metric("GD200 über Top-X", f"{gd200_above} / {total}")
    c2.metric("Breadth", f"{share:.1%}")
    c3.metric("Dynamische Positionen", str(dyn_n))

    st.divider()

    left, right = st.columns(2)
    cols = ["Rank", "Ticker", "Name", "Momentum-Score", "GD50-Signal", "GD200-Signal", "Handlung"]

    with left:
        st.markdown("#### Strategie A. Fix Top-N")
        st.dataframe(fix_df[cols], use_container_width=True)
        st.download_button(
            "CSV Strategie A",
            fix_df[cols].to_csv(index=False).encode("utf-8"),
            file_name="strategie_fix_topN.csv",
            mime="text/csv",
        )

    with right:
        st.markdown("#### Strategie B. Dynamisch nach GD200-Breadth")
        if dyn_df.empty:
            st.info("Aktuell keine dynamischen Käufe.")
        else:
            st.dataframe(dyn_df[cols], use_container_width=True)
        st.download_button(
            "CSV Strategie B",
            dyn_df[cols].to_csv(index=False).encode("utf-8") if not dyn_df.empty else b"",
            file_name="strategie_dynamisch_breadth.csv",
            mime="text/csv",
        )

    st.markdown("#### Watchlist hinter der Schnittkante")
    watch = filtered.iloc[dyn_n:dyn_n + 10].copy()
    if not watch.empty:
        st.dataframe(watch[["Rank", "Ticker", "Name", "Momentum-Score", "GD200-Signal", "Im Portfolio"]], use_container_width=True)
    else:
        st.info("Keine weiteren Kandidaten.")

with tab3:
    st.subheader(f"Backtest. {mode}")
    if st.button("Backtest starten"):
        with st.spinner("Berechne Backtest"):
            bm_series = bm_prices.iloc[:, 0].copy() if not bm_prices.empty else None
            eq_df, logs_df = run_backtest(
                prices,
                volumes,
                bm_series,
                start_date,
                end_date,
                top_n=top_n,
                min_volume=min_volume,
                max_dd52=max_dd52,
                max_volatility=max_volatility,
                apply_benchmark=apply_benchmark,
                cost_bps=cost_bps,
                slippage_bps=slip_bps,
                mode=mode,
            )

        if eq_df.empty:
            st.warning("Backtest lieferte keine Werte. Prüfe Filter und Zeitraum.")
        else:
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(eq_df.index, eq_df["Equity"], label="Strategie")

            if bm_prices is not None and not bm_prices.empty:
                bm_win = bm_prices.iloc[:, 0].loc[eq_df.index.min():eq_df.index.max()].dropna()
                if len(bm_win) >= 2:
                    bm_curve = bm_win / bm_win.iloc[0]
                    ax.plot(bm_curve.index, bm_curve.values, label=f"Benchmark ({benchmark_ticker})", alpha=0.8)

            ax.set_title(f"Equity-Kurve. {mode}")
            ax.grid(True, alpha=0.3)
            ax.legend()
            st.pyplot(fig)

            st.markdown("#### Rebalance-Log")
            st.dataframe(logs_df, use_container_width=True)
            st.download_button(
                "Logs als CSV",
                logs_df.to_csv(index=False).encode("utf-8"),
                file_name="backtest_logs.csv",
                mime="text/csv",
            )
            st.download_button(
                "Equity als CSV",
                eq_df.to_csv().encode("utf-8"),
                file_name="backtest_equity.csv",
                mime="text/csv",
            )

st.caption("Nur Informations- und Ausbildungszwecke. Keine Anlageempfehlung.")
