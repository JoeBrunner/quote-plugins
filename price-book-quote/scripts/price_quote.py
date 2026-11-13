#!/usr/bin/env python3
"""Price a service job from the owner's own price book, then build the quote page.

    python3 price_quote.py check  --book ~/Quotes/settings/price-book.csv
    python3 price_quote.py find   --book ~/Quotes/settings/price-book.csv "water heater" ["gas" ...]
    python3 price_quote.py build  --business ~/Quotes/settings/business.json --book ~/Quotes/settings/price-book.csv \
                                  --job job.json --out ~/Quotes/2026-11-12-name/quote.json

check: reads the price book and reports problems (missing or repeated codes, prices that aren't numbers).
find:  lists the book's items whose code, name, category or description contain every word given.
build: job.json names items by their code and quantity; every price is looked up in the book here. A line that isn't
       in the book must be marked {"custom": true} with the price the owner gave, and is listed in the output so it
       can be read back to them. Prints the quote file, the page and each option's total.

job.json:
{
  "customer": {"name", "address", "phone", "email"},
  "title": "Water heater replacement", "intro": "...",
  "options": [
    {"name": "Good", "headline": "...", "recommended": false, "warranty": "...", "points": ["..."],
     "items": [{"code": "WH-50G", "qty": 1}],
     "custom": [{"item": "...", "qty": 1, "unit": "each", "unit_price": 120, "custom": true}],
     "discount_percent": 0}
  ],
  "notes": ["..."]
}
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_page  # noqa: E402

REQUIRED = ("code", "item", "price")


def load_book(path):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        sys.exit(f"No price book at {path}. Run setup first.")
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [h for h in REQUIRED if h not in headers]
        if missing:
            sys.exit(f"The price book is missing the column(s): {', '.join(missing)}.")
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]
    book, problems = {}, []
    for number, row in enumerate(rows, 2):
        code = row.get("code", "").upper()
        if not code and not row.get("item"):
            continue
        if not code:
            problems.append(f"Row {number} ({row.get('item')}) has no code.")
            continue
        if code in book:
            problems.append(f"Code {code} is used twice (row {number}).")
            continue
        try:
            price = Decimal(row.get("price", "").replace("$", "").replace(",", ""))
        except InvalidOperation:
            problems.append(f"Row {number} ({code}) has a price that isn't a number: '{row.get('price')}'.")
            continue
        book[code] = {**row, "code": code, "price": price}
    return book, problems, len(rows)


def check(args):
    book, problems, rows = load_book(args.book)
    categories = {}
    for item in book.values():
        categories[item.get("category") or "Other"] = categories.get(item.get("category") or "Other", 0) + 1
    print(json.dumps({"rows": rows, "usable_items": len(book), "problems": problems, "categories": categories}, indent=2))


def find(args):
    book, _, _ = load_book(args.book)
    words = [w.lower() for w in args.words]
    hits = [item for item in book.values()
            if all(w in " ".join([item["code"], item.get("item", ""), item.get("category", ""),
                                  item.get("description", "")]).lower() for w in words)]
    for item in hits:
        print(f"{item['code']}\t{quote_page.money(item['price'])}\t{item.get('item')}\t{item.get('description', '')}")
    if not hits:
        print("No items match.")


def next_number(settings_dir):
    counter = pathlib.Path(settings_dir) / "next-quote-number.txt"
    number = int(counter.read_text().strip()) if counter.exists() else 1001
    counter.write_text(str(number + 1))
    return f"Q-{number}"


def build(args):
    business = json.load(open(os.path.expanduser(args.business)))
    book, problems, _ = load_book(args.book)
    job = json.load(open(args.job))
    unknown, custom_lines, options = [], [], []
    for option in job.get("options") or []:
        lines = []
        for entry in option.get("items") or []:
            code = str(entry.get("code", "")).upper()
            item = book.get(code)
            if not item:
                unknown.append(code or "(blank)")
                continue
            lines.append({"item": item["item"], "qty": entry.get("qty", 1), "unit": item.get("unit") or "",
                          "unit_price": str(item["price"]), "code": code})
        for entry in option.get("custom") or []:
            if not entry.get("custom") or entry.get("unit_price") in (None, ""):
                sys.exit(f"Custom line '{entry.get('item')}' needs \"custom\": true and the price the owner gave.")
            lines.append({"item": entry["item"], "qty": entry.get("qty", 1), "unit": entry.get("unit", ""),
                          "unit_price": str(entry["unit_price"])})
            custom_lines.append(f"{option.get('name')}: {entry['item']} at {quote_page.money(entry['unit_price'])}")
        for code in business.get("always_add") or []:
            item = book.get(code.upper())
            if item:
                lines.append({"item": item["item"], "qty": 1, "unit": item.get("unit") or "", "unit_price": str(item["price"])})
        discount = Decimal(str(option.get("discount_percent") or 0))
        if discount:
            subtotal = sum(quote_page.cents(Decimal(str(l["qty"])) * Decimal(l["unit_price"])) for l in lines)
            lines.append({"item": f"{option.get('discount_label') or 'Discount'} ({discount:g}%)", "qty": 1, "unit": "",
                          "unit_price": str(-quote_page.cents(subtotal * discount / 100)), "taxable": True})
        options.append({k: option.get(k) for k in ("name", "headline", "recommended", "warranty", "points")} | {"lines": lines})
    if unknown:
        sys.exit("These codes aren't in the price book: " + ", ".join(sorted(set(unknown))) +
                 ". Use `find` to look up the right code, or ask the owner for a price and add it as a custom line.")
    if not options:
        sys.exit("The job has no options.")

    settings_dir = os.path.dirname(os.path.expanduser(args.business))
    quote = {
        "company": business.get("company", {}),
        "customer": job.get("customer", {}),
        "quote_number": job.get("quote_number") or next_number(settings_dir),
        "date": datetime.date.today().isoformat(),
        "valid_days": business.get("valid_days", 30),
        "title": job.get("title", "Your quote"),
        "intro": job.get("intro"),
        "tax_percent": business.get("tax_percent", 0),
        "deposit_percent": business.get("deposit_percent", 0),
        "sample": bool(business.get("sample")),
        "facts": job.get("facts") or [],
        "options": options,
        "notes": job.get("notes") or [],
        "terms": business.get("terms") or [],
    }
    out = pathlib.Path(os.path.expanduser(args.out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(quote, indent=2))
    page, priced = quote_page.build(quote)
    page_path = out.with_suffix(".html")
    page_path.write_text(page)
    print(json.dumps({"quote_file": str(out), "page": str(page_path),
                      "custom_lines_to_confirm": custom_lines, "price_book_problems": problems,
                      "options": [{"name": o["name"], "total": str(p["total"]),
                                   "lines": [f"{l['qty']} x {l['item']} @ {quote_page.money(l['unit_price'])}" for l in o["lines"]]}
                                  for o, p in zip(options, priced)]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("check"); one.add_argument("--book", required=True)
    two = sub.add_parser("find"); two.add_argument("--book", required=True); two.add_argument("words", nargs="+")
    three = sub.add_parser("build")
    for flag in ("--business", "--book", "--job", "--out"):
        three.add_argument(flag, required=True)
    args = parser.parse_args()
    {"check": check, "find": find, "build": build}[args.command](args)


if __name__ == "__main__":
    main()
