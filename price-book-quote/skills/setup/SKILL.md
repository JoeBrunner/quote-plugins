---
name: setup
description: One-time setup for Price Book Quote. Turns whatever price list a service business already has (a spreadsheet, a PDF, a photo of a price sheet, old invoices, an export from Housecall Pro, Jobber or ServiceTitan) into a clean price book, and saves their company details, tax, deposit and terms. Run it before the first quote, or when prices change.
disable-model-invocation: true
---

# Price Book Quote setup

You're setting up quoting for a service business: plumbing, HVAC, electrical, garage doors, appliance repair, pest,
pool, or any trade that charges a set price per task. Talk like someone on their team: short, plain, no jargon.

**Where things live.** `~/Quotes/settings/price-book.csv` (their prices) and `~/Quotes/settings/business.json` (company
details). Quotes go in `~/Quotes/`. Create the folders if missing. If either file exists, show a short summary and ask
what changed instead of starting over.

**The one hard rule: never make up a price.** Every price in the book is one they gave you. Never add an item with a
"typical" price, never fill a blank, never change a price you read unless they tell you to.

## 1. The price book

Ask once: "Send me your price list however you have it: a spreadsheet, a PDF, a photo of your price sheet, a few old
invoices or estimates, or an export from your field software. Or just tell me your common jobs and prices."

Turn it into a CSV with these columns, in this order: `code,item,category,unit,price,description`.
- **code:** short and unique, capitals and dashes (`WH-50G`, `DR-MAIN`). Keep their own codes if they have them.
- **item:** what the customer reads on the quote ("50-gal gas water heater, installed").
- **category:** their own groups (Water heater, Drains, HVAC...).
- **unit:** each, hour, foot, fixture...
- **price:** a plain number, no dollar sign. Copy it exactly.
- **description:** what's included, in a few words (optional).

From invoices or estimates, take each distinct line item and its price; if the same item shows different prices, list
the differences and ask which is current. Then run:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_quote.py" check --book ~/Quotes/settings/price-book.csv`
Fix every problem it reports. Read back the count of items by category and 5 sample lines, and ask "anything missing
or wrong?". Mention that they can add items any time just by telling you.

Good, Better, Best quotes work best when the book has tiers of the same job (a standard and a premium tank, a repair and
a replacement, a basic and a high-efficiency system) and add-ons (expansion tank, surge protector, a membership). If
their book has few of those, say so in one line; don't invent them.

## 2. Company details

Ask for what's missing: company name, phone, email, website, license number, city, logo file (optional; copy it into
`~/Quotes/settings/`), brand color (optional; read it off the logo), sales tax percent on quotes (ask; it varies by
state and trade), deposit percent (0 if none), how many days a quote holds, and terms they always include (payment
terms, flat-rate promise, warranty basics). Any item they put on every quote (like a trip charge) goes in
`always_add` as its code.

Write `business.json` in the same shape as `${CLAUDE_PLUGIN_ROOT}/templates/sample-business.json` with
`"sample": false`, and read it back as a short plain list.

**Just want to try it first?** Copy both sample files (`sample-price-book.csv` to `price-book.csv`,
`sample-business.json` to `business.json`) into `~/Quotes/settings/`. It's a made-up plumbing and HVAC company; every
quote it makes says "Sample quote" and its prices are made up. Say so in one line.

## 3. Done

Two lines: what's set up, and "Type `/price-book-quote:quote` and tell me about the job: what's wrong, what you found,
the customer's name. Photos and voice notes work too."

If `python3` isn't installed: on a Mac, `python3 --version` in Terminal offers to install it; on Windows, install
Python from python.org (tick "Add to PATH").
