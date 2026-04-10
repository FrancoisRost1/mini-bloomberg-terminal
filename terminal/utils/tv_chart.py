"""TradingView Lightweight Charts embed.

Returns a self-contained HTML document for use with
``st.components.v1.html(...)``. Renders candlesticks + volume + MA50
+ MA200. OHLCV data is serialized to JSON and embedded inline so the
component does not depend on a network round-trip back to Streamlit.
"""

from __future__ import annotations

import json

import pandas as pd


def _to_records(prices: pd.DataFrame) -> dict:
    """Convert a (DateTimeIndex, OHLCV) frame into the JSON shape the
    TradingView library expects.

    lightweight-charts wants ``time`` as integer Unix seconds in UTC.
    Older versions of this helper used ``df.index.view("int64") //
    10**9``; on pandas 2.x that path silently collapses to 0 when the
    index is tz-aware (yfinance returns America/New_York), which shows
    up as "Jan 70" across the whole axis. Per-row ``ts.timestamp()``
    is stable in every pandas version for both tz-aware and naive
    indices.
    """
    df = prices.copy()
    df = df.dropna(how="all")
    if df.empty:
        return {"candles": [], "volume": [], "volume_ma20": [], "ma50": [], "ma200": []}
    idx = pd.DatetimeIndex(pd.to_datetime(df.index))
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    df.index = idx
    times = [int(pd.Timestamp(ts).timestamp()) for ts in idx]

    candles = [
        {"time": t, "open": float(o), "high": float(h), "low": float(l), "close": float(c)}
        for t, o, h, l, c in zip(
            times,
            df.get("open", df["close"]),
            df.get("high", df["close"]),
            df.get("low", df["close"]),
            df["close"],
        )
    ]
    vol_series = df.get("volume")
    if vol_series is not None:
        volume = [
            {"time": t, "value": float(v) if v == v else 0.0,
             "color": "#3D9A50AA" if c2 >= c1 else "#C43D3DAA"}
            for t, v, c1, c2 in zip(times, vol_series, df["close"].shift(1).fillna(df["close"]), df["close"])
        ]
        vol_ma20 = vol_series.astype(float).rolling(20).mean()
        volume_ma20 = [{"time": t, "value": float(v)} for t, v in zip(times, vol_ma20) if v == v]
    else:
        volume = []
        volume_ma20 = []

    close = df["close"].astype(float)
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    ma50_pts = [{"time": t, "value": float(v)} for t, v in zip(times, ma50) if v == v]
    ma200_pts = [{"time": t, "value": float(v)} for t, v in zip(times, ma200) if v == v]
    return {
        "candles": candles,
        "volume": volume,
        "volume_ma20": volume_ma20,
        "ma50": ma50_pts,
        "ma200": ma200_pts,
    }


def build_tv_chart_html(prices: pd.DataFrame, ticker: str, height_px: int = 380) -> str:
    payload = json.dumps(_to_records(prices))
    return f"""
<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:#080808; color:#E8E8EC;
    font-family:'JetBrains Mono','SF Mono',Consolas,monospace; font-size:11px; }}
  #wrap {{ width:100%; height:{height_px}px; position:relative; }}
  #legend {{ position:absolute; top:6px; left:10px; z-index:5;
    font-size:0.7rem; letter-spacing:0.04em; pointer-events:none; }}
  #legend .ttl {{ color:#E07020; font-weight:700; margin-right:0.6rem; }}
  #legend .ma50 {{ color:#E07020; margin-right:0.6rem; }}
  #legend .ma200 {{ color:#4A7FB5; margin-right:0.6rem; }}
  #legend .vma20 {{ color:#C89040; }}
</style>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
<div id="wrap">
  <div id="legend">
    <span class="ttl">{ticker}</span>
    <span class="ma50">MA50</span>
    <span class="ma200">MA200</span>
    <span class="vma20">VOL MA20</span>
  </div>
  <div id="chart" style="width:100%;height:{height_px}px;"></div>
</div>
<script>
const data = {payload};
const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function tickFormat(time) {{
  const d = new Date(time * 1000);
  return MONTH_ABBR[d.getUTCMonth()] + ' ' + String(d.getUTCFullYear()).slice(-2);
}}
const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  layout: {{ background: {{ color: '#080808' }}, textColor: '#8E8E9A', fontSize: 10,
             fontFamily: "JetBrains Mono, SF Mono, Consolas, monospace" }},
  grid:   {{ vertLines: {{ color: 'rgba(255,255,255,0.04)' }},
             horzLines: {{ color: 'rgba(255,255,255,0.04)' }} }},
  rightPriceScale: {{ borderColor: 'rgba(255,255,255,0.08)' }},
  timeScale: {{ borderColor: 'rgba(255,255,255,0.08)', timeVisible: false, secondsVisible: false,
                tickMarkFormatter: tickFormat }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
  localization: {{ timeFormatter: tickFormat }},
  width: document.getElementById('wrap').clientWidth,
  height: {height_px},
}});
const candle = chart.addCandlestickSeries({{
  upColor: '#3D9A50', downColor: '#C43D3D',
  borderUpColor: '#3D9A50', borderDownColor: '#C43D3D',
  wickUpColor: '#3D9A50', wickDownColor: '#C43D3D',
  priceScaleId: 'right',
}});
candle.setData(data.candles);

const vol = chart.addHistogramSeries({{
  priceFormat: {{ type: 'volume' }},
  priceScaleId: '',
  scaleMargins: {{ top: 0.82, bottom: 0 }},
}});
vol.setData(data.volume);

const volMa20 = chart.addLineSeries({{
  color: '#C89040',
  lineWidth: 1,
  priceScaleId: '',
  priceLineVisible: false,
  lastValueVisible: false,
}});
volMa20.applyOptions({{ scaleMargins: {{ top: 0.82, bottom: 0 }} }});
volMa20.setData(data.volume_ma20);

const ma50 = chart.addLineSeries({{ color: '#E07020', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
ma50.setData(data.ma50);
const ma200 = chart.addLineSeries({{ color: '#4A7FB5', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
ma200.setData(data.ma200);

chart.timeScale().fitContent();
window.addEventListener('resize', () => chart.applyOptions({{ width: document.getElementById('wrap').clientWidth }}));
</script>
</body></html>
"""
