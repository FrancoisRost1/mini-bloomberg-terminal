"""Custom HTML/JS scrolling ticker marquee.

Returns a self-contained HTML document for use with
``st.components.v1.html(...)``. Uses pure CSS @keyframes for the
scroll, so the page does not rerun on every tick. The track is
duplicated end-to-end so the loop is seamless.
"""

from __future__ import annotations

import json
from typing import Any


def build_marquee_html(items: list[dict[str, Any]], height_px: int = 34, scroll_seconds: int = 60) -> str:
    """Build the marquee HTML.

    Each item: ``label`` (str), ``price`` (str), ``change_pct``
    (signed float or None). Color comes from sign; up arrow / down
    arrow drawn in monospace.
    """
    safe = json.dumps(items)
    return f"""
<!doctype html>
<html><head><meta charset="utf-8"><style>
  html, body {{ margin:0; padding:0; background:#080808; }}
  .wrap {{
    overflow:hidden; width:100%; height:{height_px}px;
    background:#080808;
    border-top:1px solid rgba(255,255,255,0.06);
    border-bottom:1px solid rgba(255,255,255,0.06);
    position:relative;
  }}
  .track {{
    display:inline-block; white-space:nowrap;
    padding-left:100%;
    animation: scroll {scroll_seconds}s linear infinite;
  }}
  .cell {{
    display:inline-flex; align-items:center; gap:0.45rem;
    padding:0 1.0rem; height:{height_px}px;
    font-family:'JetBrains Mono','SF Mono',Consolas,monospace;
    font-size:0.74rem; font-weight:600;
    border-right:1px solid rgba(255,255,255,0.05);
  }}
  .lbl {{ color:#8E8E9A; letter-spacing:0.04em; }}
  .px  {{ color:#E8E8EC; }}
  .up  {{ color:#3D9A50; }}
  .dn  {{ color:#C43D3D; }}
  .flat{{ color:#55555F; }}
  @keyframes scroll {{
    from {{ transform: translateX(0); }}
    to   {{ transform: translateX(-100%); }}
  }}
  .wrap:hover .track {{ animation-play-state: paused; }}
</style></head>
<body>
<div class="wrap"><div class="track" id="t"></div></div>
<script>
const items = {safe};
function render(items) {{
  const parts = [];
  for (const it of items) {{
    const lbl = it.label || '';
    const px  = it.price || 'n/a';
    const c   = it.change_pct;
    let cls = 'flat', arrow = '\u00B7', pct = '';
    if (c !== null && c !== undefined && !isNaN(c)) {{
      if (c > 0) {{ cls = 'up'; arrow = '\u25B2'; }}
      else if (c < 0) {{ cls = 'dn'; arrow = '\u25BC'; }}
      pct = (Math.abs(c) * 100).toFixed(2) + '%';
    }}
    parts.push(
      '<span class="cell">' +
      '<span class="lbl">' + lbl + '</span>' +
      '<span class="px">' + px + '</span>' +
      '<span class="' + cls + '">' + arrow + pct + '</span>' +
      '</span>'
    );
  }}
  // Duplicate the track so the marquee loops seamlessly.
  const html = parts.join('') + parts.join('');
  document.getElementById('t').innerHTML = html;
}}
render(items);
</script></body></html>
"""
