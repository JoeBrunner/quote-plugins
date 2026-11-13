---
name: quote
description: Turns a tech's job notes, photos or voice notes into a Good, Better, Best quote priced only from the business's own price book (plumbing, HVAC, electrical and other flat-rate service trades), as a branded page they can save as a PDF and send. Use when a service tech or owner asks for a quote, estimate, options or a price for a job.
argument-hint: "<what's wrong, what you found, customer name>"
---

# Price book quote

A tech is standing in a customer's house, or just left it, and wants options they can show or send now. Be fast. Ask
only what you can't work out.

**The rules that make the quote trustworthy:**
- **Every price comes from their price book.** You choose items by code; the script looks up the prices. Never type a
  price yourself. Anything not in the book is a custom line with a price the tech gave you in this chat, and you read
  each one back before they send.
- **All math is done by the script**, never in your head.
- **Recommend what the job needs, not the most expensive thing.** Good must fix the problem properly. Never put an item
  in an option the situation doesn't call for (a pressure valve with no sign of high pressure, a membership the tech
  doesn't sell).

## 1. Load their setup

`~/Quotes/settings/price-book.csv` and `~/Quotes/settings/business.json`. Missing: say so in one line and run
`/price-book-quote:setup`. `"sample": true`: remind them in one line that the quote is marked as a sample.

## 2. Understand the job

From their words, photos (a data plate, a leak, a panel) or voice note, work out: the problem, what they found, the
equipment and its age if visible, and the customer's name. Read a data plate for model, size and fuel when there is one.
Ask at most two short questions, only for things that change the options (gas or electric? still working at all?).

## 3. Find the items

Search their book for each piece of the job:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_quote.py" find --book ~/Quotes/settings/price-book.csv <words>`
(every word must match; try a shorter search if nothing comes back). Use only codes it lists.

## 4. Build up to three options

Usually Good, Better, Best, each a complete fix on its own:
- **Good:** fixes the problem properly at the lowest sensible price (repair, or standard replacement).
- **Better:** the one you'd pick for your own house: longer warranty, the add-ons that prevent the next call. Mark it
  `"recommended": true`.
- **Best:** the top choice in their book for this job (premium or high-efficiency equipment, a membership).
If the book only supports one or two honest options, make one or two. For each: a headline a homeowner understands,
3 or 4 short points on what they get (from the book's descriptions and the tech's words, never promises the book doesn't
make), and the warranty only if the tech or the book states one.

Write `job.json` in the job folder `~/Quotes/<YYYY-MM-DD>-<customer-last-name>/` in the shape shown at the top of
`${CLAUDE_PLUGIN_ROOT}/scripts/price_quote.py` (items by code and quantity). Add an intro of one or two sentences in the
tech's voice about what they found, no sales talk. Then:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/price_quote.py" build --business ~/Quotes/settings/business.json \
  --book ~/Quotes/settings/price-book.csv --job "<job folder>/job.json" --out "<job folder>/quote.json"
```

If it says a code isn't in the book, look it up again with `find` or ask the tech for a price; never guess one.

## 5. Check it, then hand it over

- Read back every custom line it lists, with its price, and get a yes.
- Open the page (on a Mac: `open "<page>"`) and confirm the totals on it match what the script printed.
- Tell the tech: the option totals in one line, where the file is, and "Save as PDF" (the button on the page) to send
  it or show it on their phone.
- Changes (swap an item, a discount, drop an option): edit `job.json` and run build again. Never edit the page.
- If a custom price should be in the book for next time, offer to add it.

Never send the quote yourself, email or text the customer, or post it anywhere. The tech sends it.
