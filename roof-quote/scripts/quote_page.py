#!/usr/bin/env python3
"""Turn a quote file (JSON) into a branded, printable quote page with Good, Better and Best options.

    python3 quote_page.py quote.json [--out quote.html]

All the arithmetic happens here, never by hand: each line's amount is quantity times unit price, rounded to the cent;
each option's subtotal, tax, total and deposit come from those. Prints the page's path and every option's total, so
they can be read back and checked against the page.

The quote file:
{
  "company": {"name", "phone", "email", "website", "license", "address", "color": "#hex", "logo": "path or url"},
  "customer": {"name", "address", "phone", "email"},
  "quote_number": "Q-1042", "date": "2026-11-12", "valid_days": 30,
  "title": "Roof replacement",
  "intro": "One or two sentences on the job, in the contractor's voice.",
  "tax_percent": 0, "deposit_percent": 0,
  "sample": false,
  "facts": [{"label": "Roof size", "value": "29.6 squares"}],      # optional strip of key numbers
  "drawing_svg": "<svg ...>", "faces": [{...}],                    # optional (roof quotes)
  "options": [
    {"name": "Good", "headline": "Architectural shingles", "recommended": false,
     "warranty": "...", "points": ["what's included", "..."],
     "lines": [{"item": "...", "qty": 32.6, "unit": "sq", "unit_price": 410, "taxable": true}]}
  ],
  "notes": ["..."], "terms": ["..."]
}
"""
import argparse
import datetime
import html
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal


def cents(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money(value, whole=False):
    value = cents(value)
    sign = "-" if value < 0 else ""
    if whole and value == value.to_integral_value():
        return f"{sign}${abs(value):,.0f}"
    return f"{sign}${abs(value):,.2f}"


def qty_text(value):
    value = Decimal(str(value))
    return f"{value.normalize():f}" if value != value.to_integral_value() else f"{int(value):,}"


def e(text):
    return html.escape(str(text if text is not None else ""))


def safe_svg(svg):
    """Keep only a plain drawing: no scripts, no event handlers, no outside links."""
    if not svg or not svg.lstrip().startswith("<svg"):
        return ""
    if re.search(r"<\s*script|on\w+\s*=|javascript:|<\s*foreignObject|href\s*=", svg, re.I):
        return ""
    return svg


def price(option, tax_percent, deposit_percent):
    lines, subtotal, taxable = [], Decimal("0"), Decimal("0")
    for line in option.get("lines", []):
        amount = cents(Decimal(str(line.get("qty", 1))) * Decimal(str(line.get("unit_price", 0))))
        lines.append({**line, "amount": amount})
        subtotal += amount
        if line.get("taxable", True):
            taxable += amount
    tax = cents(taxable * Decimal(str(tax_percent)) / 100)
    total = subtotal + tax
    deposit = cents(total * Decimal(str(deposit_percent)) / 100)
    return {"lines": lines, "subtotal": subtotal, "tax": tax, "total": total, "deposit": deposit}


CSS = """
:root{--brand:%(color)s;--brand-dark:%(dark)s;--brand-soft:%(soft)s;--ink:#111418;--soft:#5a6270;--line:#e4e7ec;
--tint:#f5f6f8;--ok:#127a46}
*{box-sizing:border-box}html,body{margin:0;background:#eef0f3;color:var(--ink);
font:15px/1.55 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sheet{max-width:1060px;margin:28px auto 64px;background:#fff;border-radius:22px;overflow:hidden;
box-shadow:0 30px 80px -40px rgba(17,20,24,.45)}
.hero{position:relative;background:linear-gradient(135deg,var(--brand) 0%%,var(--brand-dark) 100%%);color:#fff;
padding:34px 44px 86px;overflow:hidden}
.hero:after{content:"";position:absolute;right:-120px;top:-160px;width:460px;height:460px;border-radius:50%%;
background:radial-gradient(circle,rgba(255,255,255,.16),rgba(255,255,255,0) 70%%)}
.top{display:flex;justify-content:space-between;align-items:center;gap:20px;position:relative;z-index:1}
.co{display:flex;align-items:center;gap:14px}.co img{height:54px;max-width:170px;object-fit:contain;
background:#fff;border-radius:12px;padding:6px}
.mono{width:52px;height:52px;border-radius:14px;background:#fff;color:var(--brand-dark);display:grid;place-items:center;
font-weight:800;font-size:19px;letter-spacing:.02em}
.co b{display:block;font-size:20px;letter-spacing:-.01em}.co span{font-size:12.5px;opacity:.85}
.qno{text-align:right;font-size:12.5px;opacity:.9}.qno b{display:block;font-size:13px;letter-spacing:.12em;
text-transform:uppercase;opacity:1}
.title{position:relative;z-index:1;margin-top:38px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.title h1{margin:6px 0 8px;font-size:44px;line-height:1.05;letter-spacing:-.03em;font-weight:800;max-width:720px}
.title p{margin:0;font-size:15.5px;opacity:.92}
.facts{position:relative;z-index:2;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;
margin:-52px 44px 0}
.fact{background:#fff;border-radius:16px;padding:16px 18px;box-shadow:0 14px 34px -20px rgba(17,20,24,.5);
border:1px solid var(--line)}.fact b{display:block;font-size:24px;letter-spacing:-.02em;line-height:1.1}
.fact span{color:var(--soft);font-size:12.5px}
.body{padding:30px 44px 40px}
.intro{font-size:16px;max-width:720px;margin:4px 0 0}
.estimate{display:flex;gap:12px;align-items:flex-start;margin:18px 0 0;padding:13px 16px;border-radius:12px;
background:var(--brand-soft);font-size:13.5px}.estimate i{font-style:normal;font-weight:800;color:var(--brand-dark)}
.sample{margin:16px 0 18px;padding:10px 14px;border-radius:10px;background:#fff6dc;border:1px solid #f0d27d;font-size:13px}
h2{margin:40px 0 16px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--soft)}
.options{display:grid;grid-template-columns:repeat(%(cols)d,1fr);gap:16px;align-items:stretch}
.opt{position:relative;border:1.5px solid var(--line);border-radius:20px;padding:24px 22px 20px;background:#fff;
display:flex;flex-direction:column}
.opt.rec{border:2px solid var(--brand);box-shadow:0 24px 50px -28px var(--brand);transform:translateY(-6px)}
.flag{position:absolute;top:-14px;left:50%%;transform:translateX(-50%%);background:var(--brand);color:#fff;
font-size:11.5px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;padding:6px 14px;border-radius:999px;
white-space:nowrap}
.tier{display:inline-block;align-self:flex-start;font-size:11.5px;font-weight:800;letter-spacing:.12em;
text-transform:uppercase;color:var(--brand-dark);background:var(--brand-soft);padding:4px 10px;border-radius:999px}
.opt h3{margin:12px 0 14px;font-size:20px;line-height:1.2;letter-spacing:-.01em}
.price{font-size:40px;font-weight:800;letter-spacing:-.03em;line-height:1}
.price small{font-size:18px;font-weight:700;vertical-align:top;margin-right:1px}
.dep{color:var(--soft);font-size:13px;margin-top:8px}
.opt ul{margin:18px 0 0;padding:0;list-style:none;flex:1}
.opt li{display:flex;gap:10px;padding:7px 0;font-size:14px;border-top:1px solid var(--line)}
.opt li:before{content:"";flex:0 0 18px;height:18px;margin-top:2px;border-radius:50%%;background:var(--brand-soft)
url("data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 18 18'%%3E%%3Cpath d='M5 9.4l2.6 2.5L13 6.4' fill='none' stroke='%%23111' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%%3E%%3C/svg%%3E") center/18px no-repeat}
.warranty{display:flex;gap:9px;margin-top:16px;padding:11px 12px;background:var(--tint);border-radius:12px;
font-size:12.5px;color:var(--soft)}.warranty b{color:var(--ink)}
.choose{margin-top:14px;display:flex;align-items:center;gap:10px;border:1.5px dashed #c9ced6;border-radius:12px;
padding:11px 13px;font-size:13.5px;font-weight:600}.choose span{width:18px;height:18px;border:2px solid #9aa2ad;
border-radius:5px}.opt.rec .choose{border-color:var(--brand);color:var(--brand-dark)}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.step{background:var(--tint);border-radius:16px;padding:16px}.step b{display:grid;place-items:center;width:30px;
height:30px;border-radius:50%%;background:var(--brand);color:#fff;font-size:14px;margin-bottom:10px}
.step strong{display:block;font-size:14.5px}.step span{font-size:13px;color:var(--soft)}
.roof{display:grid;grid-template-columns:minmax(220px,340px) 1fr;gap:24px;align-items:start}
.pic{background:var(--tint);border-radius:18px;padding:16px}.pic svg{width:100%%;height:auto;display:block}
.pic p{margin:10px 0 0;font-size:12.5px;color:var(--soft)}
table{width:100%%;border-collapse:collapse;font-size:13.5px}th,td{text-align:left;padding:8px 8px;
border-bottom:1px solid var(--line)}th{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--soft)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
details{border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-top:10px}
summary{cursor:pointer;font-weight:700;list-style:none;display:flex;justify-content:space-between;gap:12px}
summary::-webkit-details-marker{display:none}summary:before{content:"+";color:var(--brand);font-weight:800;margin-right:8px}
details[open] summary:before{content:"\\2013"}summary em{font-style:normal;margin-right:auto}
summary span{font-variant-numeric:tabular-nums}details table{margin-top:12px}tr.sum td{border-bottom:0;font-weight:700}
.small{color:var(--soft);font-size:13px;padding-left:18px}.small li{margin:5px 0}
.sign{display:grid;grid-template-columns:2fr 1fr;gap:28px;margin-top:44px}
.sign div{border-top:2px solid var(--ink);padding-top:7px;font-size:12.5px;color:var(--soft)}
footer{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:18px 44px;background:var(--tint);
color:var(--soft);font-size:12px}
.actions{position:fixed;right:20px;bottom:20px}.actions button{font:700 14px/1 inherit;background:var(--ink);color:#fff;
border:0;border-radius:999px;padding:14px 20px;cursor:pointer;box-shadow:0 12px 30px -12px rgba(0,0,0,.6)}
@media screen and (max-width:820px){.sheet{margin:0;border-radius:0}.hero{padding:24px 18px 74px}.title h1{font-size:32px}
.facts{margin:-50px 16px 0;grid-template-columns:1fr 1fr}.body{padding:24px 16px 32px}.options{grid-template-columns:1fr;
gap:22px}.opt.rec{transform:none}.roof{grid-template-columns:1fr}.sign{grid-template-columns:1fr}footer{padding:16px}
.top{align-items:flex-start}.qno{display:none}}
@media screen and (max-width:720px){html{scrollbar-width:none}html::-webkit-scrollbar{display:none}}
@media print{html,body{background:#fff}.sheet{margin:0;box-shadow:none;border-radius:0;max-width:none;zoom:.62}
.actions{display:none}.opt.rec{transform:none;box-shadow:none}.opt{break-inside:avoid}.options{break-inside:avoid}
details{break-inside:avoid;margin-top:6px;padding:8px 14px}summary{display:flex}summary:before{display:none}
.hero{padding-bottom:70px}.roof{grid-template-columns:260px 1fr;break-inside:avoid}h2{margin:26px 0 12px;break-after:avoid}.sign{break-inside:avoid}
@page{size:letter;margin:9mm}}
"""


def shade(color, factor):
    """Darken (factor < 1) or mix with white (factor > 1) a #rrggbb color."""
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    if factor <= 1:
        r, g, b = (int(v * factor) for v in (r, g, b))
    else:
        mix = min(factor - 1, 1)
        r, g, b = (int(v + (255 - v) * mix) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def big_price(value):
    text = money(value)
    dollars, cents_part = text.split(".")
    return f"<small>$</small>{dollars.lstrip('-$')}<small>.{cents_part}</small>"


def build(quote):
    company = quote.get("company", {})
    customer = quote.get("customer", {})
    tax_percent = quote.get("tax_percent", 0) or 0
    deposit_percent = quote.get("deposit_percent", 0) or 0
    options = quote.get("options") or []
    if not 1 <= len(options) <= 4:
        sys.exit("A quote needs between 1 and 4 options.")
    priced = [price(o, tax_percent, deposit_percent) for o in options]
    color = company.get("color") or "#0f5132"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}", color):
        color = "#0f5132"
    date_text = quote.get("date") or datetime.date.today().isoformat()
    try:
        made = datetime.date.fromisoformat(date_text)
    except ValueError:
        made = datetime.date.today()
    valid_until = made + datetime.timedelta(days=int(quote.get("valid_days", 30) or 30))
    name = company.get("name", "")
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z0-9]+", name)[:2]).upper() or "Q"

    out = ["<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
           f"<title>{e(name or 'Quote')} · {e(quote.get('title', 'Quote'))}</title>",
           "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
           "<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap\" rel=\"stylesheet\">",
           f"<style>{CSS % {'color': color, 'dark': shade(color, .62), 'soft': shade(color, 1.88), 'cols': len(options)}}</style>",
           "</head><body><div class=\"sheet\">"]
    logo = company.get("logo")
    mark = f"<img src=\"{e(logo)}\" alt=\"\">" if logo else f"<div class=\"mono\">{e(initials)}</div>"
    contact = " · ".join(e(company[k]) for k in ("phone", "email", "website") if company.get(k))
    extra = " · ".join(e(x) for x in (company.get("address"), f"License {company['license']}" if company.get("license") else None) if x)
    out.append(f"<header class=\"hero\"><div class=\"top\"><div class=\"co\">{mark}<div><b>{e(name)}</b>"
               f"<span>{contact}</span>" + (f"<br><span>{extra}</span>" if extra else "") + "</div></div>"
               f"<div class=\"qno\"><b>Quote {e(quote.get('quote_number', ''))}</b>{made.strftime('%B %-d, %Y')}"
               f"<br>Good until {valid_until.strftime('%B %-d, %Y')}</div></div>")
    who = " · ".join(e(w) for w in (customer.get("name"), customer.get("address")) if w)
    out.append(f"<div class=\"title\"><div class=\"eyebrow\">Prepared for you</div><h1>{e(quote.get('title', 'Your quote'))}</h1>"
               f"<p>{who}</p></div></header>")
    if quote.get("facts"):
        out.append("<div class=\"facts\">" + "".join(
            f"<div class=\"fact\"><b>{e(f.get('value'))}</b><span>{e(f.get('label'))}</span></div>"
            for f in quote["facts"]) + "</div>")
    out.append("<main class=\"body\">")
    if quote.get("sample"):
        out.append("<p class=\"sample\"><b>Sample quote.</b> The company, customer and prices on this page are made up "
                   "to show how the quote works. They aren't real prices.</p>")
    if quote.get("intro"):
        out.append(f"<p class=\"intro\">{e(quote['intro'])}</p>")
    if quote.get("estimate_note"):
        out.append(f"<div class=\"estimate\"><i>Estimate</i><span>{e(quote['estimate_note'])}</span></div>")

    out.append("<h2>Choose your option</h2><div class=\"options\">")
    for option, numbers in zip(options, priced):
        rec = bool(option.get("recommended"))
        dep = (f"{money(numbers['deposit'])} deposit to get on the schedule" if numbers["deposit"] else "Total, installed")
        out.append(f"<div class=\"opt{' rec' if rec else ''}\">" + ("<span class=\"flag\">Recommended</span>" if rec else "") +
                   f"<span class=\"tier\">{e(option.get('name', ''))}</span><h3>{e(option.get('headline', ''))}</h3>"
                   f"<div class=\"price\">{big_price(numbers['total'])}</div><div class=\"dep\">{dep}</div>"
                   "<ul>" + "".join(f"<li>{e(p)}</li>" for p in option.get("points", [])) + "</ul>" +
                   (f"<div class=\"warranty\"><span>&#128737;</span><span><b>Warranty</b><br>{e(option['warranty'])}</span></div>"
                    if option.get("warranty") else "") +
                   "<div class=\"choose\"><span></span>I choose this option</div></div>")
    out.append("</div>")

    steps = [("Pick your option", "Tick it and sign below.")]
    if deposit_percent:
        steps.append(("Place the deposit", f"{e(deposit_percent)}% gets you on the schedule."))
    if quote.get("estimate_note"):
        steps.append(("We confirm on site", "A quick measure locks in your final price."))
    steps.append(("Work day", "We do the job and clean up after."))
    out.append("<h2>What happens next</h2><div class=\"steps\">" + "".join(
        f"<div class=\"step\"><b>{i}</b><strong>{t}</strong><span>{d}</span></div>" for i, (t, d) in enumerate(steps, 1)) + "</div>")

    if quote.get("faces") or quote.get("drawing_svg"):
        out.append("<h2>Your roof</h2><div class=\"roof\">")
        svg = safe_svg(quote.get("drawing_svg", ""))
        out.append(f"<div class=\"pic\">{svg}<p>Top view, each roof section numbered. "
                   f"{e(quote.get('measure_source', ''))}</p></div>" if svg else "<div></div>")
        faces = quote.get("faces") or []
        if faces:
            out.append("<div><table><thead><tr><th>Section</th><th class=\"n\">Area (sq ft)</th><th class=\"n\">Pitch</th>"
                       "<th>Type</th></tr></thead><tbody>" + "".join(
                           f"<tr><td>{e(f.get('face'))}</td><td class=\"n\">{int(f.get('sqft', 0)):,}</td>"
                           f"<td class=\"n\">{e(f.get('pitch'))}/12</td><td>{'Low slope (flat-roof system)' if f.get('low_slope') else 'Sloped'}</td></tr>"
                           for f in faces) + "</tbody></table></div>")
        out.append("</div>")

    out.append("<h2>What's in each price</h2>")
    for option, numbers in zip(options, priced):
        rows = "".join(f"<tr><td>{e(l.get('item'))}</td><td class=\"n\">{qty_text(l.get('qty', 1))} {e(l.get('unit', ''))}</td>"
                       f"<td class=\"n\">{money(l.get('unit_price', 0))}</td><td class=\"n\">{money(l['amount'])}</td></tr>"
                       for l in numbers["lines"])
        rows += f"<tr class=\"sum\"><td colspan=\"3\">Subtotal</td><td class=\"n\">{money(numbers['subtotal'])}</td></tr>"
        if numbers["tax"]:
            rows += f"<tr class=\"sum\"><td colspan=\"3\">Sales tax ({e(tax_percent)}%)</td><td class=\"n\">{money(numbers['tax'])}</td></tr>"
        rows += f"<tr class=\"sum\"><td colspan=\"3\">Total</td><td class=\"n\">{money(numbers['total'])}</td></tr>"
        out.append(f"<details><summary><em>{e(option.get('name'))}: {e(option.get('headline'))}</em><span>{money(numbers['total'])}</span></summary>"
                   "<table><thead><tr><th>Item</th><th class=\"n\">Qty</th><th class=\"n\">Price</th><th class=\"n\">Amount</th></tr></thead>"
                   f"<tbody>{rows}</tbody></table></details>")

    for heading, key in (("Good to know", "notes"), ("Terms", "terms")):
        if quote.get(key):
            out.append(f"<h2>{heading}</h2><ul class=\"small\">" + "".join(f"<li>{e(t)}</li>" for t in quote[key]) + "</ul>")
    out.append("<div class=\"sign\"><div>Customer signature</div><div>Date</div></div></main>")
    out.append(f"<footer><span>{e(name)} · Quote {e(quote.get('quote_number', ''))}</span>" +
               (f"<span>{e(quote['measure_credit'])}</span>" if quote.get("measure_credit") else "") + "</footer>")
    out.append("</div><div class=\"actions\"><button onclick=\"window.print()\">Save as PDF</button></div>"
               "<script>addEventListener('beforeprint',()=>document.querySelectorAll('details').forEach(d=>d.open=true))</script></body></html>")
    return "".join(out), priced


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("quote")
    parser.add_argument("--out")
    args = parser.parse_args()
    quote = json.load(open(args.quote))
    page, priced = build(quote)
    out = args.out or re.sub(r"\.json$", "", args.quote) + ".html"
    with open(out, "w") as handle:
        handle.write(page)
    print(json.dumps({"page": out, "options": [
        {"name": o.get("name"), "subtotal": str(p["subtotal"]), "tax": str(p["tax"]), "total": str(p["total"]),
         "deposit": str(p["deposit"])} for o, p in zip(quote["options"], priced)]}, indent=2))


if __name__ == "__main__":
    main()
