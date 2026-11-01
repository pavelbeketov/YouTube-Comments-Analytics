"""Build a standalone dark dashboard from analyze.py chart data."""

import json
import html
import math
from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "analysis_data.json"
OUTPUT_FILE = ROOT / "data" / "graphs.html"
IMAGE_DIR = ROOT / "data" / "graphs"

PAGE = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Аналитика комментариев YouTube</title>
  <style>
    :root { color-scheme: dark; --bg:#08090b; --panel:#111317; --text:#e8e9eb;
      --muted:#898d96; --grid:#25282e; --blue:#3c5da8; --green:#548746;
      --orange:#a65723; }
    * { box-sizing:border-box }
    body { margin:0; padding:32px; background:var(--bg); color:var(--text);
      font:16px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif }
    main { max-width:1180px; margin:auto }
    h1 { margin:0 0 8px; font-size:26px }
    .sub { color:var(--muted); margin-bottom:26px }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px }
    section { min-width:0; padding:20px; background:var(--panel); border:1px solid #202329;
      border-radius:14px }
    section.wide { grid-column:1/-1 }
    h2 { margin:0 0 18px; font-size:18px }
    svg { width:100%; height:auto; display:block; overflow:visible }
    .legend { display:flex; flex-wrap:wrap; justify-content:center; gap:12px 24px;
      color:#d5d7db; font-size:14px; margin-top:10px }
    .key { display:inline-flex; align-items:center; gap:8px }
    .dot { width:12px; height:12px; border-radius:50%; display:inline-block }
    .error { color:#ff9f9f; padding:16px; border:1px solid #743d3d; border-radius:8px }
    @media(max-width:760px) { body{padding:18px} .grid{grid-template-columns:1fr}
      section.wide{grid-column:auto} }
  </style>
</head>
<body>
<main>
  <h1>Аналитика комментариев YouTube</h1>
  <div class="sub" id="summary"></div>
  <div class="grid">
    <section><h2>1. Распределение тональности</h2><div id="sentiment"></div></section>
    <section><h2>2. Основные темы обсуждения</h2><div id="topics"></div></section>
    <section class="wide"><h2>3. Средние лайки и ответы по тональности</h2><div id="comparison"></div></section>
  </div>
</main>
<script>
const DATA = __DATA__;
const COLORS = {negative:'#3c5da8', neutral:'#548746', positive:'#a65723'};
const ORDER = ['negative','neutral','positive'];
const NAMES = {negative:'Негативные',neutral:'Нейтральные',positive:'Позитивные'};
const NS='http://www.w3.org/2000/svg';
function el(tag,attrs={},text='') { const n=document.createElementNS(NS,tag);
  for(const [k,v] of Object.entries(attrs)) n.setAttribute(k,v);
  if(text) n.textContent=text; return n; }
function svgBox(w,h) { return el('svg',{viewBox:`0 0 ${w} ${h}`,role:'img'}); }
function addLegend(host,keys) { const d=document.createElement('div'); d.className='legend';
  keys.forEach(k=>{const item=document.createElement('span');item.className='key';
    const dot=document.createElement('i');dot.className='dot';dot.style.background=COLORS[k];
    item.append(dot,document.createTextNode(NAMES[k]));d.append(item);});host.append(d); }
function donut(host,datasets) {
  const wrap=document.createElement('div');
  const w=600, h=datasets.length>1?260:340, r=92, inner=52;
  const svg=svgBox(w,h); const centers=datasets.length>1?[165,435]:[300];
  datasets.forEach((ds,idx)=>{
    const cx=centers[idx],cy=datasets.length>1?128:155;
    const values=ORDER.map(k=>Number(ds.sentiment_counts[k]||0));
    const total=values.reduce((a,b)=>a+b,0); let angle=-Math.PI/2;
    values.forEach((value,i)=>{
      if(!value||!total)return;
      const next=angle+value/total*2*Math.PI, large=next-angle>Math.PI?1:0;
      const x1=cx+r*Math.cos(angle),y1=cy+r*Math.sin(angle);
      const x2=cx+r*Math.cos(next),y2=cy+r*Math.sin(next);
      const ix2=cx+inner*Math.cos(next),iy2=cy+inner*Math.sin(next);
      const ix1=cx+inner*Math.cos(angle),iy1=cy+inner*Math.sin(angle);
      const path=`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${inner} ${inner} 0 ${large} 0 ${ix1} ${iy1} Z`;
      svg.append(el('path',{d:path,fill:COLORS[ORDER[i]],stroke:'#17191d','stroke-width':2}));
      angle=next;
    });
    svg.append(el('text',{x:cx,y:cy-3,fill:'#f0f1f3','font-size':20,'font-weight':700,'text-anchor':'middle'},String(total)));
    svg.append(el('text',{x:cx,y:cy+19,fill:'#9296a0','font-size':12,'text-anchor':'middle'},'комментариев'));
    if(datasets.length>1) svg.append(el('text',{x:cx,y:250,fill:'#d9dbe0','font-size':14,'text-anchor':'middle'},ds.label));
  });
  wrap.append(svg); addLegend(wrap,ORDER); host.replaceChildren(wrap);
}
function topicBars(host,datasets) {
  const sums={};
  datasets.forEach(ds=>(ds.topics||[]).forEach(t=>{sums[t.topic]=(sums[t.topic]||0)+Number(t.count)}));
  const topics=Object.entries(sums).sort((a,b)=>b[1]-a[1]).slice(0,8);
  const w=700,row=42,top=18,left=170,right=44,h=top+topics.length*row+12;
  const max=Math.max(1,...topics.map(t=>t[1])); const svg=svgBox(w,h);
  topics.forEach(([name,value],i)=>{
    const y=top+i*row,barW=(w-left-right)*value/max;
    svg.append(el('text',{x:left-12,y:y+21,fill:'#c9cbd0','font-size':13,'text-anchor':'end'},name.length>24?name.slice(0,23)+'…':name));
    svg.append(el('rect',{x:left,y,width:barW,height:25,rx:7,fill:'#3c5da8'}));
    svg.append(el('text',{x:left+barW+8,y:y+18,fill:'#dfe1e5','font-size':13},String(value)));
  });
  if(!topics.length) svg.append(el('text',{x:20,y:35,fill:'#aaa'},'Нет данных о темах'));
  host.replaceChildren(svg);
}
function compare(host,datasets) {
  const ds=datasets[0],w=900,h=350,left=62,right=20,top=25,bottom=52,plotH=h-top-bottom;
  const svg=svgBox(w,h),metrics=['likes','replies'];
  const means=Object.fromEntries(ORDER.map(k=>{const rows=ds.comments.filter(c=>c.sentiment===k);
    return [k,Object.fromEntries(metrics.map(m=>[m,rows.length?rows.reduce((s,c)=>s+Number(c[m]||0),0)/rows.length:0]))];}));
  const max=Math.max(1,...ORDER.flatMap(k=>metrics.map(m=>means[k][m])));
  for(let i=0;i<=4;i++){const y=top+plotH*(1-i/4);
    svg.append(el('line',{x1:left,y1:y,x2:w-right,y2:y,stroke:'#292c32','stroke-dasharray':'4 5'}));
    svg.append(el('text',{x:left-10,y:y+4,fill:'#8e929a','font-size':12,'text-anchor':'end'},(max*i/4).toFixed(1)));}
  const groupW=(w-left-right)/ORDER.length,barW=44;
  ORDER.forEach((k,i)=>{const gx=left+i*groupW+groupW/2;
    metrics.forEach((m,j)=>{const value=means[k][m],bh=plotH*value/max,x=gx-barW+j*barW;
      svg.append(el('rect',{x,y:top+plotH-bh,width:barW-5,height:bh,rx:7,fill:j?'#548746':'#3c5da8'}));
      svg.append(el('text',{x:x+(barW-5)/2,y:top+plotH-bh-7,fill:'#cdd0d6','font-size':11,'text-anchor':'middle'},value.toFixed(1)));});
    svg.append(el('text',{x:gx,y:h-20,fill:'#e1e2e5','font-size':14,'text-anchor':'middle'},NAMES[k]));});
  const wrap=document.createElement('div');wrap.append(svg);const legend=document.createElement('div');legend.className='legend';
  [['#3c5da8','Средние лайки'],['#548746','Средние ответы']].forEach(([color,name])=>{const item=document.createElement('span');item.className='key';
    const dot=document.createElement('i');dot.className='dot';dot.style.background=color;item.append(dot,document.createTextNode(name));legend.append(item);});
  wrap.append(legend);host.replaceChildren(wrap);
}
const sourceDatasets=Object.entries(DATA.datasets||{}).map(([label,value])=>({...value,label}));
const datasets=sourceDatasets.length?[{label:'Итого по обоим CSV',
  sentiment_counts:Object.fromEntries(ORDER.map(k=>[k,sourceDatasets.reduce((s,d)=>s+Number(d.sentiment_counts[k]||0),0)])),
  metrics:{comments:sourceDatasets.reduce((s,d)=>s+Number(d.metrics.comments||0),0)},
  topics:Object.entries(sourceDatasets.flatMap(d=>d.topics||[]).reduce((a,t)=>{a[t.topic]=(a[t.topic]||0)+Number(t.count);return a;},{})).map(([topic,count])=>({topic,count})),
  comments:sourceDatasets.flatMap(d=>d.comments||[])}]:[];
if(!datasets.length){document.querySelector('main').innerHTML='<p class="error">Нет наборов данных. Сначала запустите analyze.py.</p>';}
else {
  const total=datasets[0].metrics.comments;
  document.getElementById('summary').textContent=`Модель: ${DATA.model} · Всего комментариев: ${total}`;
  donut(document.getElementById('sentiment'),datasets);
  topicBars(document.getElementById('topics'),datasets);
  compare(document.getElementById('comparison'),datasets);
}
</script>
</body>
</html>
"""

COLORS = {"negative": "#3c5da8", "neutral": "#548746", "positive": "#a65723"}
SENTIMENT_NAMES = {
    "negative": "Negative", "neutral": "Neutral", "positive": "Positive"
}
BG = "#08090b"
FG = "#e8e9eb"
MUTED = "#9296a0"
GRID = "#292c32"


def svg_start(width: int, height: int, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f'<title>{html.escape(title)}</title>'
        f'<rect width="100%" height="100%" fill="{BG}"/>'
        f'<text x="36" y="46" fill="{FG}" font-family="Arial,sans-serif" '
        f'font-size="24" font-weight="700">{html.escape(title)}</text>'
    )


def svg_legend(items: list[str], x: int, y: int) -> str:
    parts = []
    cursor = x
    for key in items:
        parts.append(
            f'<circle cx="{cursor}" cy="{y}" r="7" fill="{COLORS[key]}"/>'
            f'<text x="{cursor + 14}" y="{y + 5}" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="16">'
            f'{html.escape(SENTIMENT_NAMES[key])}</text>'
        )
        cursor += 170
    return "".join(parts)


def donut_image(datasets: list[tuple[str, dict]]) -> str:
    width, height = 900, 520
    parts = [svg_start(width, height, "1. Overall sentiment distribution")]
    centers = [450]
    radius, inner = 142, 82
    for index, (label, data) in enumerate(datasets[:1]):
        cx, cy = centers[index], 260
        values = [int(data["sentiment_counts"].get(key, 0)) for key in COLORS]
        total = sum(values)
        angle = -math.pi / 2
        for key, value in zip(COLORS, values):
            if value <= 0 or total == 0:
                continue
            next_angle = angle + 2 * math.pi * value / total
            large = 1 if next_angle - angle > math.pi else 0
            x1, y1 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            x2, y2 = cx + radius * math.cos(next_angle), cy + radius * math.sin(next_angle)
            ix2, iy2 = cx + inner * math.cos(next_angle), cy + inner * math.sin(next_angle)
            ix1, iy1 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
            d = (f"M {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large} 1 {x2:.2f} {y2:.2f} "
                 f"L {ix2:.2f} {iy2:.2f} A {inner} {inner} 0 {large} 0 {ix1:.2f} {iy1:.2f} Z")
            parts.append(f'<path d="{d}" fill="{COLORS[key]}" stroke="#17191d" stroke-width="3"/>')
            angle = next_angle
        parts.append(
            f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="30" font-weight="700">{total}</text>'
            f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" fill="{MUTED}" '
            f'font-family="Arial,sans-serif" font-size="15">total comments</text>'
            f'<text x="{cx}" y="445" text-anchor="middle" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="18">{html.escape(label)}</text>'
        )
    parts.extend([svg_legend(list(COLORS), 205, 495), "</svg>"])
    return "".join(parts)


def topic_image(datasets: list[tuple[str, dict]]) -> str:
    totals: dict[str, int] = {}
    for _, data in datasets:
        for item in data.get("topics", []):
            topic = str(item["topic"])
            totals[topic] = totals.get(topic, 0) + int(item["count"])
    topics = sorted(totals, key=lambda topic: (-totals[topic], topic))[:8]
    width, row_height, top = 1000, 58, 82
    height = max(220, top + len(topics) * row_height + 50)
    left, right = 280, 58
    max_value = max((totals[t] for t in topics), default=1)
    parts = [svg_start(width, height, "2. Main discussion topics")]
    for i, topic in enumerate(topics):
        y = top + i * row_height
        title = topic if len(topic) <= 30 else topic[:27] + "..."
        parts.append(
            f'<text x="{left - 16}" y="{y + 22}" text-anchor="end" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="15">{html.escape(title)}</text>'
        )
        for j, (label, data) in enumerate(datasets[:2]):
            count = next((int(x["count"]) for x in data.get("topics", [])
                          if x["topic"] == topic), 0)
            bar_width = (width - left - right) * count / max_value
            bar_y = y + j * 23
            color = "#3c5da8" if j == 0 else "#548746"
            parts.append(
                f'<rect x="{left}" y="{bar_y}" width="{bar_width:.1f}" height="17" '
                f'rx="6" fill="{color}"/><text x="{left + bar_width + 8:.1f}" '
                f'y="{bar_y + 14}" fill="{FG}" font-family="Arial,sans-serif" '
                f'font-size="13">{count}</text>'
            )
    for j, (label, _) in enumerate(datasets[:2]):
        color = "#3c5da8" if j == 0 else "#548746"
        x = left + j * 210
        parts.append(
            f'<rect x="{x}" y="{height - 28}" width="12" height="12" rx="6" fill="{color}"/>'
            f'<text x="{x + 19}" y="{height - 17}" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="14">{html.escape(label)}</text>'
        )
    if not topics:
        parts.append(f'<text x="40" y="120" fill="{MUTED}">No topic data</text>')
    parts.append("</svg>")
    return "".join(parts)


def comparison_image(datasets: list[tuple[str, dict]]) -> str:
    width, height = 1000, 560
    left, right, top, bottom = 80, 35, 85, 85
    plot_height = height - top - bottom
    plot_width = width - left - right
    parts = [svg_start(width, height, "3. Average likes and replies by sentiment")]
    comments = datasets[0][1].get("comments", [])
    metrics = ["likes", "replies"]
    averages = {}
    for sentiment in COLORS:
        rows = [row for row in comments if row["sentiment"] == sentiment]
        averages[sentiment] = {
            metric: sum(int(row.get(metric, 0)) for row in rows) / len(rows) if rows else 0
            for metric in metrics
        }
    max_value = max((value for values in averages.values() for value in values.values()), default=0) or 1
    for tick in range(0, 6):
        value = max_value * tick / 5
        y = top + plot_height * (1 - value / max_value)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-dasharray="5 6"/>'
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" fill="{MUTED}" '
            f'font-family="Arial,sans-serif" font-size="14">{value:.1f}</text>'
        )
    group_width = plot_width / len(COLORS)
    bar_width = 64
    for index, key in enumerate(COLORS):
        center = left + index * group_width + group_width / 2
        for j, metric in enumerate(metrics):
            value = averages[key][metric]
            bar_h = plot_height * value / max_value
            x = center - bar_width + j * bar_width
            y = top + plot_height - bar_h
            color = "#3c5da8" if metric == "likes" else "#548746"
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 7:.1f}" '
                f'height="{bar_h:.1f}" rx="8" fill="{color}"/>'
                f'<text x="{x + (bar_width - 7) / 2:.1f}" y="{y - 8:.1f}" '
                f'text-anchor="middle" fill="{FG}" font-family="Arial,sans-serif" '
                f'font-size="13">{value:.1f}</text>'
            )
        parts.append(
            f'<text x="{center:.1f}" y="{height - 42}" text-anchor="middle" fill="{FG}" '
            f'font-family="Arial,sans-serif" font-size="17">{html.escape(SENTIMENT_NAMES[key])}</text>'
        )
    parts.append(
        f'<circle cx="350" cy="{height - 13}" r="7" fill="#3c5da8"/>'
        f'<text x="364" y="{height - 8}" fill="{FG}" font-family="Arial,sans-serif" font-size="16">Average likes</text>'
        f'<circle cx="550" cy="{height - 13}" r="7" fill="#548746"/>'
        f'<text x="564" y="{height - 8}" fill="{FG}" font-family="Arial,sans-serif" font-size="16">Average replies</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def save_individual_images(datasets: list[tuple[str, dict]]) -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "sentiment_distribution.svg": donut_image(datasets),
        "topic_distribution.svg": topic_image(datasets),
        "engagement_by_sentiment.svg": comparison_image(datasets),
    }
    paths = []
    for filename, svg in charts.items():
        path = IMAGE_DIR / filename
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
        png_path = path.with_suffix(".png")
        png_path.write_bytes(resvg_py.svg_to_bytes(svg_string=svg))
        paths.append(png_path)
    return paths


def combine_datasets(source_datasets: list[tuple[str, dict]]) -> dict:
    combined = {
        "sentiment_counts": {key: 0 for key in COLORS},
        "metrics": {},
        "topics": {},
        "comments": [],
    }
    for _, data in source_datasets:
        for sentiment in COLORS:
            combined["sentiment_counts"][sentiment] += int(
                data.get("sentiment_counts", {}).get(sentiment, 0)
            )
        for metric, value in data.get("metrics", {}).items():
            combined["metrics"][metric] = combined["metrics"].get(metric, 0) + int(value)
        for item in data.get("topics", []):
            topic = str(item["topic"])
            combined["topics"][topic] = combined["topics"].get(topic, 0) + int(item["count"])
        combined["comments"].extend(data.get("comments", []))
    combined["topics"] = [
        {"topic": topic, "count": count}
        for topic, count in sorted(combined["topics"].items(), key=lambda item: (-item[1], item[0]))
    ]
    return combined


def main() -> int:
    if not DATA_FILE.is_file():
        print(f"Chart data not found: {DATA_FILE}. Run analyze.py first.")
        return 1
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    source_datasets = list(data.get("datasets", {}).items())
    if not source_datasets:
        print("No chart datasets found. Run analyze.py first.")
        return 1
    datasets = [("Overall total", combine_datasets(source_datasets))]
    images = save_individual_images(datasets)
    html = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Dashboard created: {OUTPUT_FILE}")
    for path in images:
        print(f"Image created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
