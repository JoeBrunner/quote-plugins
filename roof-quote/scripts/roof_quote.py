#!/usr/bin/env python3
"""Price a roof from its measurements and the roofer's own price sheet, then build the quote page.

    python3 roof_quote.py --profile ~/Quotes/settings/roof-pricing.json --roof roof.json \
        --customer "Name" [--customer-address "..."] [--stories 1] [--layers 1] [--quote-number Q-1001] \
        --out ~/Quotes/2026-11-12-name.json

roof.json is measure_roof.py's output, or a hand-made one with at least {"roof_sqft", "faces": [{"sqft", "pitch",
"low_slope"}]} (from a measurement report or the roofer's own numbers; see the skill). Every price comes from the
profile; this script never makes one up. It writes the quote file, builds the page next to it, and prints both paths
and each option's total.
"""
import argparse
import datetime
import json
import math
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_page  # noqa: E402


def auto_waste(face_count):
    """Typical roofer rule of thumb: simple roofs waste less shingle than cut-up ones."""
    if face_count <= 4:
        return 10
    if face_count <= 9:
        return 12
    return 15


def up_to_third(squares):
    """Shingles come three bundles to a square, so order in thirds."""
    return math.ceil(squares * 3 - 1e-9) / 3


def next_number(profile_path):
    counter = pathlib.Path(profile_path).with_name("next-quote-number.txt")
    number = int(counter.read_text().strip()) if counter.exists() else 1001
    counter.write_text(str(number + 1))
    return f"Q-{number}"


def need(profile, key):
    if profile.get(key) in (None, ""):
        sys.exit(f"The price sheet has no '{key}'. Run setup again to fill it in.")
    return profile[key]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--roof", required=True)
    parser.add_argument("--customer", required=True)
    parser.add_argument("--customer-address")
    parser.add_argument("--customer-phone")
    parser.add_argument("--customer-email")
    parser.add_argument("--stories", type=int, default=1)
    parser.add_argument("--layers", type=int, default=1, help="old shingle layers to tear off (0 for a new build)")
    parser.add_argument("--quote-number")
    parser.add_argument("--intro")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    profile = json.load(open(os.path.expanduser(args.profile)))
    roof = json.load(open(args.roof))
    faces = roof.get("faces") or []
    if not faces:
        sys.exit("The roof file has no faces. Measure again or enter the roof by hand.")
    # Satellite sizes run low (on 329 real re-roofs, about 10% under the roofer's own number), so they get a cushion.
    # A report or the roofer's own numbers are used as they are.
    cushion = 0
    if roof.get("size_method"):
        setting = profile.get("size_cushion_percent")
        cushion = 10 if setting in (None, "") else float(setting)
        faces = [dict(f, sqft=round(f["sqft"] * (1 + cushion / 100))) for f in faces]
        roof = dict(roof, roof_sqft=sum(f["sqft"] for f in faces))
    sloped_sq = sum(f["sqft"] for f in faces if not f.get("low_slope")) / 100
    low_sq = sum(f["sqft"] for f in faces if f.get("low_slope")) / 100
    total_sq = sloped_sq + low_sq
    waste = profile.get("waste_percent")
    waste = auto_waste(len(faces)) if waste in (None, "", "auto") else float(waste)
    order_sloped = up_to_third(sloped_sq * (1 + waste / 100)) if sloped_sq else 0
    order_low = round(low_sq * 1.05, 2) if low_sq else 0

    shared = []
    if low_sq:
        low = need(profile, "low_slope")
        shared.append({"item": f"{low['product']} on the low-slope sections ({low_sq:.1f} sq + 5% waste)",
                       "qty": order_low, "unit": "sq", "unit_price": low["price_per_square"]})
    if args.layers > 0:
        shared.append({"item": f"Tear off {args.layers} layer{'s' if args.layers > 1 else ''} of old roofing and haul away",
                       "qty": round(total_sq * args.layers, 2), "unit": "sq",
                       "unit_price": need(profile, "tear_off_per_square")})
    tiers = sorted(profile.get("steep") or [], key=lambda t: t["from_pitch"])
    for index, tier in enumerate(tiers):
        top = tiers[index + 1]["from_pitch"] if index + 1 < len(tiers) else 99
        steep_sq = sum(f["sqft"] for f in faces if not f.get("low_slope") and tier["from_pitch"] <= f["pitch"] < top) / 100
        if steep_sq:
            shared.append({"item": f"Steep-roof work, {tier['from_pitch']}/12 and up ({steep_sq:.1f} sq)",
                           "qty": round(steep_sq, 2), "unit": "sq", "unit_price": tier["per_square"]})
    story_price = (profile.get("stories_extra") or {}).get(str(args.stories))
    if story_price and args.stories > 1:
        shared.append({"item": f"{args.stories}-story access and safety setup", "qty": round(total_sq, 2), "unit": "sq",
                       "unit_price": story_price})
    for fixed in profile.get("fixed") or []:
        shared.append({"item": fixed["item"], "qty": 1, "unit": "", "unit_price": fixed["price"],
                       "taxable": fixed.get("taxable", True)})

    options = []
    for tier in need(profile, "options"):
        lines = []
        if order_sloped:
            lines.append({"item": f"{tier['headline']}, installed ({sloped_sq:.1f} sq + {waste:g}% waste)",
                          "qty": round(order_sloped, 2), "unit": "sq", "unit_price": tier["price_per_square"]})
        lines += [dict(line) for line in shared]
        subtotal = sum(quote_page.cents(l["qty"]) * quote_page.cents(l["unit_price"]) for l in lines)
        minimum = profile.get("minimum_job")
        if minimum and subtotal < quote_page.cents(minimum):
            lines.append({"item": "Minimum job adjustment", "qty": 1, "unit": "",
                          "unit_price": float(quote_page.cents(minimum) - subtotal)})
        options.append({"name": tier["name"], "headline": tier["headline"], "recommended": tier.get("recommended", False),
                        "warranty": tier.get("warranty"), "points": tier.get("points", []), "lines": lines})

    estimated = bool(roof.get("size_method"))
    facts = [{"label": "Roof area (estimated)" if estimated else "Roof area", "value": f"{roof.get('roof_sqft', round(total_sq * 100)):,} sq ft"},
             {"label": "Squares (100 sq ft each)", "value": f"{total_sq:.1f}"},
             {"label": "Main pitch", "value": f"{roof.get('main_pitch', faces[0]['pitch'])}/12"},
             {"label": "Roof sections", "value": str(len(faces))}]
    if low_sq:
        facts.append({"label": "Low-slope area", "value": f"{round(low_sq * 100):,} sq ft"})

    notes = list(profile.get("notes") or [])
    for allowance in profile.get("allowances") or []:
        notes.append(f"{allowance['item']}: {quote_page.money(allowance['unit_price'])} per {allowance.get('unit', 'each')}"
                     f", only if needed. {allowance.get('note', '')}".strip())
    estimate_note = None
    if roof.get("size_method"):
        estimate_note = ("The roof size comes from satellite imagery"
                         + (f" (photo dated {roof['photo_date']})" if roof.get("photo_date") else "")
                         + ". We confirm the final price when we measure on site.")
    elif roof.get("source"):
        notes.append(f"Measured from {roof['source']}. Final measurements are confirmed on site before work starts.")

    quote = {
        "company": profile.get("company", {}),
        "customer": {"name": args.customer, "address": args.customer_address or roof.get("address"),
                     "phone": args.customer_phone, "email": args.customer_email},
        "quote_number": args.quote_number or next_number(os.path.expanduser(args.profile)),
        "date": datetime.date.today().isoformat(),
        "valid_days": profile.get("valid_days", 30),
        "intro": args.intro or profile.get("intro"),
        "tax_percent": profile.get("tax_percent", 0),
        "deposit_percent": profile.get("deposit_percent", 0),
        "sample": bool(profile.get("sample")),
        "facts": facts,
        "faces": faces,
        "drawing_svg": roof.get("drawing_svg", ""),
        "measure_source": "From Google's satellite roof model." if "Google" in str(roof.get("source", "")) else "",
        "title": profile.get("title", "Roof replacement") + (" estimate" if estimated else ""),
        "measure_credit": "Roof measurements include data from Google" if "Google" in str(roof.get("source", "")) else "",
        "options": options,
        "notes": notes,
        "estimate_note": estimate_note,
        "terms": profile.get("terms") or [],
        "waste_percent": waste,
    }
    out = pathlib.Path(os.path.expanduser(args.out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(quote, indent=2))
    page, priced = quote_page.build(quote)
    page_path = out.with_suffix(".html")
    page_path.write_text(page)
    # For the roofer only, never on the quote: things that change what they should sell.
    checks = []
    shallow = sum(f["sqft"] for f in faces if not f.get("low_slope") and f["pitch"] < 4) / 100
    if sloped_sq and shallow / sloped_sq > 0.5:
        checks.append(f"{shallow:.1f} of {sloped_sq:.1f} shingle squares are under 4/12. Most shingle makers require "
                      "extra underlayment there; make sure every option includes it.")
    if low_sq and low_sq / total_sq > 0.25:
        checks.append(f"{low_sq / total_sq:.0%} of the roof measured as low-slope (flat-roof system). If some of it is "
                      "really shingled porch roof, the quote is high.")
    print(json.dumps({"quote_file": str(out), "page": str(page_path), "squares": round(total_sq, 1),
                      "checks_for_the_roofer": checks, "size_cushion_percent": cushion,
                      "waste_percent": waste, "options": [
                          {"name": o["name"], "total": str(p["total"]), "deposit": str(p["deposit"])}
                          for o, p in zip(options, priced)]}, indent=2))


if __name__ == "__main__":
    main()
