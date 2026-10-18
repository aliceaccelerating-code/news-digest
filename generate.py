"""每日財經簡報產生器：Claude 搜尋 -> 驗證連結 -> 輸出雙語網頁到 docs/。
需要環境變數 ANTHROPIC_API_KEY。  pip install anthropic
"""
import json, re, html, datetime, pathlib
import anthropic

MODEL = "claude-sonnet-5-5"
TZ = datetime.timezone(datetime.timedelta(hours=8))  # 台北 / 伯斯
TODAY = datetime.datetime.now(TZ).date().isoformat()
DOCS = pathlib.Path("docs")
SECTIONS = [
    ("fed", "美國 Fed", "US Federal Reserve"),
    ("rba", "澳洲央行 RBA", "Reserve Bank of Australia"),
    ("cbc", "台灣央行", "Central Bank of Taiwan"),
    ("oil", "油價", "Oil prices"),
    ("mining", "礦業", "Mining"),
    ("economy", "總體經濟", "Economy"),
]

PROMPT = f"""今天是 {TODAY}。請用網路搜尋過去 24~48 小時的新聞，為以下主題各挑 2~4 則最重要的：
{", ".join(f"{k}（{zh}）" for k, zh, _ in SECTIONS)}。
規則：
- 只使用搜尋結果中真實出現的網址，不可自行編造；沒有新聞的主題回傳空陣列。
- 優先使用央行官網、Reuters、Bloomberg、EIA、Mining.com 等原始或權威來源。
- 繁體中文與英文摘要各 1~2 句，內容一致，只寫事實與數字。
只輸出 JSON，不要任何其他文字或 Markdown，格式：
{{"sections": {{"<key>": [{{"headline_zh": "", "headline_en": "", "summary_zh": "",
"summary_en": "", "source": "媒體名稱", "url": "", "published": "YYYY-MM-DD"}}]}}}}"""


def fetch_digest():
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}],
        messages=[{"role": "user", "content": PROMPT}],
    )
    # 收集搜尋實際回傳過的網址，用來擋掉編造的連結
    seen = set()
    for b in resp.content:
        if b.type == "web_search_tool_result" and isinstance(b.content, list):
            seen.update(getattr(r, "url", None) for r in b.content)
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    for key, items in data["sections"].items():
        data["sections"][key] = [i for i in items if i.get("url") in seen]
    return data


def esc(s):
    return html.escape(str(s or ""))


def render(data, date, dates):
    parts = []
    for key, zh, en in SECTIONS:
        items = data["sections"].get(key, [])
        cards = "".join(
            f"""<article>
<h3><span class="zh">{esc(i['headline_zh'])}</span><span class="en">{esc(i['headline_en'])}</span></h3>
<p class="zh">{esc(i['summary_zh'])}</p><p class="en">{esc(i['summary_en'])}</p>
<a href="{esc(i['url'])}" target="_blank" rel="noopener noreferrer">{esc(i['source'])} · {esc(i.get('published',''))}</a>
</article>""" for i in items
        ) or '<p class="empty"><span class="zh">今日無重大消息</span><span class="en">Nothing significant today</span></p>'
        parts.append(f'<section><h2><span class="zh">{zh}</span><span class="en">{en}</span></h2>{cards}</section>')
    archive = " ".join(
        f'<a href="{"index.html" if d == dates[0] else d + ".html"}"{" aria-current=page" if d == date else ""}>{d}</a>'
        for d in dates[:30]
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日財經簡報 {date}</title><style>
:root{{--bg:#eef1f4;--ink:#14202b;--mute:#5b6b7a;--line:#cfd7de;--acc:#0f6b6b;--card:#fff}}
@media(prefers-color-scheme:dark){{:root{{--bg:#10171d;--ink:#e6edf3;--mute:#93a4b3;--line:#2a3743;--acc:#4fc1b8;--card:#17212a}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.7 "Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px 64px}}
header{{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;align-items:baseline;margin-bottom:8px}}
h1{{font-size:1.6rem;margin:0}}header span{{color:var(--mute)}}
.tools button{{font:inherit;padding:4px 14px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}}
.tools button[aria-pressed=true]{{background:var(--acc);border-color:var(--acc);color:#fff}}
.tools button:focus-visible,a:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
section{{margin-top:32px}}h2{{font-size:1.15rem;border-bottom:2px solid var(--acc);padding-bottom:4px}}
h2 span+span::before,h3 span+span::before{{content:" / ";color:var(--mute);font-weight:400}}
article{{background:var(--card);border:1px solid var(--line);padding:14px 16px;margin-top:12px}}
h3{{font-size:1rem;margin:0 0 6px}}article p{{margin:4px 0}}.en{{color:var(--mute)}}h3 .en{{font-weight:400}}
article a{{color:var(--acc);font-size:.9rem}}.empty{{color:var(--mute)}}
body[data-lang=zh] .en,body[data-lang=en] .zh{{display:none}}
body[data-lang=zh] h2 span+span::before,body[data-lang=en] h2 span+span::before,
body[data-lang=zh] h3 span+span::before,body[data-lang=en] h3 span+span::before{{content:""}}
nav{{margin-top:40px;font-size:.9rem;display:flex;flex-wrap:wrap;gap:10px}}nav a{{color:var(--mute)}}
nav a[aria-current]{{color:var(--ink);font-weight:700}}
</style></head><body data-lang="both"><main>
<header><h1>每日財經簡報 / Daily Briefing</h1><span>{date}</span></header>
<div class="tools" role="group" aria-label="語言 Language">
<button data-l="both" aria-pressed="true">中 + EN</button><button data-l="zh" aria-pressed="false">中文</button><button data-l="en" aria-pressed="false">English</button></div>
{"".join(parts)}
<nav aria-label="Archive">{archive}</nav>
<p class="en" style="font-size:.85rem;margin-top:24px">AI 自動整理，請以原文連結為準。 AI-generated summaries; verify with the original links.</p>
</main><script>
document.querySelectorAll('.tools button').forEach(b=>b.onclick=()=>{{
document.body.dataset.lang=b.dataset.l;
document.querySelectorAll('.tools button').forEach(x=>x.setAttribute('aria-pressed',x===b));
try{{localStorage.lang=b.dataset.l}}catch(e){{}}}});
try{{const l=localStorage.lang;if(l)document.querySelector(`[data-l=${{l}}]`).click()}}catch(e){{}}
</script></body></html>"""


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data").mkdir(exist_ok=True)
    data = fetch_digest()
    (DOCS / "data" / f"{TODAY}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    dates = sorted((p.stem for p in (DOCS / "data").glob("*.json")), reverse=True)
    for d in dates[:30]:
        day = json.loads((DOCS / "data" / f"{d}.json").read_text(encoding="utf-8"))
        page = render(day, d, dates)
        (DOCS / f"{d}.html").write_text(page, encoding="utf-8")
        if d == dates[0]:
            (DOCS / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
