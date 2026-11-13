---
name: quote
description: Makes a roof replacement quote with Good, Better and Best options from a street address (Google's satellite roof measurements), a measurement report (EagleView, Hover, Roofr, GAF QuickMeasure and the like) or the roofer's own numbers, priced from their own price sheet, as a branded page they can save as a PDF and send. Use when a roofer asks for a quote, estimate or bid on a roof, or gives an address and a customer name.
argument-hint: "<address> for <customer name> [2-story] [2 layers]"
---

# Roof quote

The roofer wants a quote they can send today. Be quick and plain; ask only what you need.

**The rules that make the quote trustworthy:**
- **Every price comes from their price sheet** (`~/Quotes/settings/roof-pricing.json`). Never invent, adjust or
  "round" a price. If something the job needs isn't on the sheet, ask them for the price and offer to add it.
- **All math is done by the scripts**, never in your head: areas, squares, waste, line amounts, totals, deposit.
- **Never guess a measurement.** It comes from Google's roof model, a report, or the roofer. Say which on the quote.

## 1. Price sheet

Read `~/Quotes/settings/roof-pricing.json`. If it's missing, say so in one line and run the setup
(`/roof-quote:setup`) first. If it has `"sample": true`, remind them in one line that this quote will be marked as a
sample with made-up prices.

## 2. The job

From what they typed, pull out: the address, the customer's name (and phone or email if given), stories (default 1),
layers to tear off (default 1; 0 for a new build), and anything unusual they mention. Ask only for the address and name
if they're missing.

## 3. Measure the roof

Use the first that works:

**a. From the address (if Google is set up):**
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure_roof.py" "<address>" --out "<job folder>/roof.json"`
where the job folder is `~/Quotes/<YYYY-MM-DD>-<customer-last-name>/`. Don't stop to ask about the size: go straight on
to pricing. The size is an estimate and the quote says so ("we confirm the final price when we measure on site").
- The price adds a 10% size cushion (their sheet's `size_cushion_percent`), since satellite sizes run about 10% low.
  Say so in the hand-over in half a sentence.
- Tell the roofer in the hand-over (step 5), not before: the squares, main pitch, faces, low-slope area, the photo date,
  and every warning it printed. A warning means "look before you send", not "stop".
- If it says no key, no roof model or a limit, say so in one line and fall back to b or c.

**b. From a measurement report** they attach: read the report's totals and its facets or pitch table. Write
`roof.json` yourself in this shape, copying their numbers exactly:
`{"source": "<report name and date>", "address": "...", "roof_sqft": <total>, "main_pitch": <x>, "faces": [{"face": 1, "sqft": <area>, "pitch": <x/12 as a number>, "low_slope": <true if under 2/12>}]}`.
If the report only gives totals per pitch, make one face per pitch. Show them the totals you read and get a yes.

**c. From their own numbers:** ask for the total squares (or square feet) and the main pitch, plus any flat or
low-slope area. Write `roof.json` the same way with one face per pitch, `"source": "the roofer's own measurements"`.

## 4. Price it and build the page

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/roof_quote.py" --profile ~/Quotes/settings/roof-pricing.json \
  --roof "<job folder>/roof.json" --customer "<name>" [--customer-address "<address>"] [--customer-phone ...] \
  [--customer-email ...] [--stories N] [--layers N] [--intro "<one or two sentences>"] --out "<job folder>/quote.json"
```

Only write `--intro` if they told you something about this job worth saying (a leak, storm damage, an insurance claim,
what they want); in their voice, one or two sentences, no sales talk. Otherwise leave it out and the sheet's own intro is
used.

## 5. Check it, then hand it over

- Tell the roofer every line under `checks_for_the_roofer`, in plain words.
- Read the totals the script printed and open the page file to confirm the same totals appear on it.
- Sanity-check against the roof: if any total works out under the sheet's cheapest option times the squares, or a line
  looks wrong (a steep charge on a flat roof, tear-off on a new build), say so before they send it.
- Open the page for them (on a Mac: `open "<page>"`). Tell them: the three totals in one line, where the file is, and
  "Save as PDF" (the button on the page, or Print, Save as PDF) to send it.
- Ask if they want any change: a different option, a discount line, removing the deposit, a note. Make changes by
  editing `quote.json` and rebuilding with
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/quote_page.py" "<job folder>/quote.json"`, never by editing the page.
- If a price they give you now should apply to every job, offer to save it to their price sheet.

Never send the quote yourself, email the customer or post it anywhere. The roofer sends it.
