# Quote plugins for Claude

**Send a customer a clean Good, Better, Best quote in a few minutes, priced only from your own prices.**

Two plugins, install one or both:

- **Roof Quote** (roofing): type an address and the customer's name. It measures the roof from Google's satellite roof
  model (total area, every roof face and its pitch, flat sections), prices it from your price sheet (per square, tear-off,
  steep and story charges, permit, dumpster) and builds three options. No address data? Attach your EagleView, Hover or
  Roofr report, or give it the size and pitch.
- **Price Book Quote** (plumbing, HVAC, electrical and other flat-rate trades): tell it what you found, or send a photo of
  the data plate or a voice note. It picks the right items from your own price book and builds up to three options.

Both make a branded quote page with your logo and colors, a "Save as PDF" button, a signature line, and the line-by-line
math folded underneath. Claude never makes up a price: every price comes from your sheet or your book, and all the math
is done by code, not by the AI.

## What you need

- Claude Code (Anthropic's assistant; it runs in the Claude desktop app's Code tab, or in a terminal) on a paid Claude
  plan. Setup steps: [code.claude.com/docs/en/quickstart](https://code.claude.com/docs/en/quickstart).
- Python 3 (Macs offer to install it the first time it's needed; on Windows, install it from python.org).
- For roof measurements from an address: your own free Google key (10,000 roof lookups a month free; Google needs a card
  on file). Setup walks you through it in about 10 minutes. US addresses work directly; elsewhere, give a map point.

## Install (about two minutes)

1. Open Claude Code (the Claude desktop app's Code tab, or type `claude` in a terminal) and type:
   ```
   /plugin marketplace add JoeBrunner/quote-plugins
   ```
2. Then one or both:
   ```
   /plugin install roof-quote@quote-plugins
   /plugin install price-book-quote@quote-plugins
   ```
3. Restart Claude Code, then run setup once:
   ```
   /roof-quote:setup
   /price-book-quote:setup
   ```
   Send it your price sheet, an old quote, invoices, or a photo of your price list, and it builds your sheet from that.
   Want to try it first? Say "use the sample" and it loads a made-up company, clearly marked as a sample.

## Make a quote

```
/roof-quote:quote 123 Main St, Tampa FL 33601 for Dana Whitfield, 2-story
/price-book-quote:quote 14-year-old 50-gal gas water heater leaking from the tank, Marcus Hale
```

Quotes are saved in a `Quotes` folder in your home folder. Open one, press "Save as PDF", and send it your usual way.
Claude never emails or texts a customer for you.

## Good to know

- **Roof quotes are estimates.** Each one says so, and that you confirm the final price when you measure on site.
  Satellite sizes run a little low and can miss on unusual houses, so measure before you order materials.
- Your prices stay on your computer, in `~/Quotes/settings/`.
- Changes are made by asking ("drop Best", "add a 5% discount to Better"); the quote is rebuilt from your prices.
