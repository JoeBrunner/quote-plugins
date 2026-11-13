---
name: setup
description: One-time setup for Roof Quote. Builds the roofer's price sheet (their company details, their Good, Better and Best options with price per square, tear-off, steep and story charges, fees, deposit, terms) from whatever they already have, and optionally connects Google's free roof measurements. Run it before the first quote, or any time prices change.
disable-model-invocation: true
---

# Roof Quote setup

You're setting up a roofer's quoting. Talk like a person on their crew, not a software manual: short questions, plain
words, no jargon. They may be on a phone between jobs.

**Where things live.** Their price sheet: `~/Quotes/settings/roof-pricing.json`. Their quotes: `~/Quotes/`. Create the
folders if they're missing. If a price sheet already exists, read it, show what's there in a short list and ask what
changed; don't start over.

**The one hard rule: never make up a price.** Every number in the sheet comes from them. If they don't know one yet,
leave that part out (a missing steep charge just means no steep line) or ask again later. Never fill a gap with a
"typical" price, and never suggest one unless they ask; then say plainly it's a rough market guess they must check.

## 1. Get what they already have

Ask once: "Do you have a price sheet, an old quote or an estimate you've sent before? Paste it, attach a photo or PDF,
or just tell me your prices." Read whatever comes back and pull out everything you can. Then ask only for what's still
missing, a few things at a time:

- **Company:** name, phone, email, website, license number, city, a logo file (optional; copy it into
  `~/Quotes/settings/` and use that path), a brand color (optional; read it off the logo if there is one).
- **Options:** up to three, usually Good, Better and Best. For each: what it is (the headline a homeowner reads, like
  "Architectural shingles"), the installed **price per square** (100 sq ft of roof), 3 or 4 short lines on what's
  included, and the warranty. Ask which one they recommend most.
- **Tear-off** price per square per layer (most quotes assume one layer).
- **Low-slope / flat sections:** what they put on them and the price per square. Faces under 2/12 get this instead of
  shingles.
- **Steep charges:** from which pitch, and the extra per square (often two tiers, like 7/12 and up, 10/12 and up).
- **Extra stories:** extra per square for a 2-story and a 3-story roof, if they charge it.
- **Flat fees:** permit, dumpster, anything else on every job.
- **Only-if-needed items:** like plywood per sheet. These show as a price on the quote, not in the total.
- **Minimum job** price, **deposit** percent, **sales tax** percent on the total (usually 0 for a roofing contract; ask),
  how many days a quote is good for, and any terms they always include.
- **Size cushion:** satellite roof sizes come in about 10% low, so quotes measured from an address add 10% to the roof
  size (`size_cushion_percent`). Mention it in one line; change it only if they ask. Reports and their own numbers are
  never cushioned.
- **Waste:** leave it on "auto" (10% simple roofs, 12% medium, 15% cut-up roofs) unless they use their own number.

Write `roof-pricing.json` in the same shape as `${CLAUDE_PLUGIN_ROOT}/templates/sample-roof-pricing.json`, with
`"sample": false`. Then read it back to them as a short, plain list (not JSON) and fix anything they correct.

**Just want to see it work first?** Copy the sample sheet to `~/Quotes/settings/roof-pricing.json` as it is. Every
quote it makes says "Sample quote" at the top and its prices are made up. Tell them that in one line, and that running
setup again replaces it with theirs.

## 2. Roof measurements from an address (optional, recommended)

Roof Quote can measure a roof from the street address using Google's satellite roof model: total area, every roof face
and its pitch. That needs their own free Google key. Explain it in three lines:

- Google gives **10,000 roof lookups a month free**. Past that it's about a penny each. Google needs a card on file
  even for the free part. (Prices can change; their current list is at developers.google.com/maps/billing-and-pricing/pricing.)
- Setup takes about 10 minutes in Google's console. You'll walk them through it.
- Without it, quotes still work: they can attach a measurement report (EagleView, Hover, Roofr and the like) or give
  the size and pitch themselves.

If they want it, walk them through, one step at a time, waiting for "done" each time:
1. Go to console.cloud.google.com and sign in with any Google account.
2. Create a project (top bar, project picker, New project), name it "Roof quotes".
3. Billing: Menu, Billing, link a billing account (this is where the card goes).
4. Menu, APIs and Services, Library: search "Solar API", open it, click Enable.
5. Menu, APIs and Services, Credentials: Create credentials, API key. Then Edit the key, under API restrictions
   choose "Restrict key" and tick only Solar API, and Save.

**Never ask them to paste the key into this chat.** Keys pasted in a chat are kept in the chat history. Instead:
- **Mac:** give them this to paste into the Terminal app, then paste the key at its prompt (nothing shows as they paste,
  that's normal), and press Return:
  `security add-generic-password -U -s roof-quote-google-key -a "$USER" -w`
- **Windows or Linux:** have them set an environment variable named `GOOGLE_SOLAR_API_KEY` to the key (Windows: Start,
  search "environment variables", Edit environment variables for your account, New), then restart Claude.

Then test it on their own shop or home address:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure_roof.py" "<address>"`
Show the squares and main pitch in one line. If it fails, read the error to them in plain words and fix it together.
If `python3` isn't installed: on a Mac, `python3 --version` in Terminal offers to install it; on Windows, install
Python from python.org (tick "Add to PATH").

## 3. Done

Say in two lines what's set up, and how to quote: "Type `/roof-quote:quote` with an address and the customer's name."
