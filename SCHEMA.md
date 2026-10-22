# Edition data format

Each edition is one JSON file, `editions/YYYY-MM-DD.json` (UTF-8). Turn it into HTML with:

    python render.py editions/YYYY-MM-DD.json

That writes `editions/YYYY-MM-DD.html` and copies it to `latest.html`. The renderer handles all layout, fonts, colours and images, so the JSON holds content only. Never put HTML tags in strings. Plain text only; use real characters (é, —, « ») rather than entities.

```json
{
  "date": "2026-10-22",
  "date_long": "Thursday, October 22, 2026",
  "issue": 1,
  "generated_at": "10:14",

  "quote":  { "text": "…", "speaker": "Geoffrey Hinton", "context": "interview with the Guardian", "url": "https://…" },
  "number": { "value": "49/50", "text": "What the number means, one sentence.", "url": "https://…" },

  "stories": [
    {
      "id": "openai-monitors",            // unique kebab-case; used for the article page anchor
      "section": "safety",                // models | safety | cyber | doom | hardware | bench | math | physics | science
      "lead": true,                       // exactly ONE story is the lead (À la une)
      "featured": true,                   // 3 stories (not the lead, ideally 3 different sections) shown in the row under the hero
      "brief": "Short one-line headline for the En bref sidebar",   // optional; 5–7 stories should have one
      "kicker": "OpenAI",                 // short grey word(s) above the headline on the article page (place, company, topic)
      "suptitle": "Misalignment report",  // short italic line above the headline on cards
      "title": "OpenAI's own agents switched off the monitors watching them",
      "standfirst": "One- or two-sentence summary. Used on cards and as the photo caption.",
      "body": ["Paragraph 1", "Paragraph 2", "…"],   // 3–6 paragraphs written from the source(s); the article page text
      "why": "One or two sentences: why it matters.",  // optional, shown as a highlighted box in the article
      "facts": ["Key fact 1", "Key fact 2"],          // optional, 2–5 bullet points
      "opinion": false,                   // true for essays/interviews/op-eds: headline uses the slab 'chronique' style
      "source":  { "name": "OpenAI Alignment", "url": "https://…", "date": "October 20, 2026" },
      "extra_sources": [ { "name": "The Hacker News", "url": "https://…" } ],
      "image": { "url": "https://…jpg", "credit": "OPENAI" }   // optional; if missing the renderer uses the source page's og:image, else a typographic panel; set to null when the only image is a logo
    }
  ],

  "dossiers": [
    {
      "id": "openai-math",
      "section": "math",
      "title": "OpenAI's 722-manuscript maths dump: what holds up?",
      "status": "new",                    // "new" (development in the last ~48 h) or "nochange"
      "update": "What is new today (or a one-line recap if nothing changed).",
      "background": ["Paragraph", "…"],   // what the story is, including anything that could not be verified
      "timeline": [ { "date": "Oct 6", "text": "What happened", "url": "https://…" } ],
      "image": { "url": "https://…", "credit": "…" }   // optional
    }
  ],

  "sources": [ { "title": "Article title", "outlet": "Outlet", "url": "https://…" } ]
}
```

Rules:
- Each section should have 2–5 stories. If a section has no fresh news, include one story saying so that points to the most recent relevant item.
- The two dossiers `openai-math` (section math) and `astra` (section physics) are always present.
- Every URL must be a real http(s) link taken from research; never invent one.
