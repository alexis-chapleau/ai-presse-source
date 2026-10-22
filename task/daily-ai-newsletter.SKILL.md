---
name: daily-ai-newsletter
description: Every morning at 6am, research AI news and publish a La Presse-style newsletter with article pages
---

Produce today's edition of "Le Quotidien IA", a personal morning AI newsletter laid out like lapresse.ca (desktop) and the La Presse iPhone app (phone), then publish it.

## Files (base folder C:\Users\agervaischapleau\Documents\Newsletter-IA\)
- SCHEMA.md: the edition data format. READ IT FIRST and follow it exactly.
- render.py: turns an edition JSON into the finished HTML (desktop La Presse layout + phone app layout with slide-up article sheets) and rebuilds the publishable site\ folder (index.html = newest edition, editions\, archive.html, app icon, manifest). Do not edit render.py or write any HTML yourself. Your job is the content.
- editions\YYYY-MM-DD.json: write today's edition here (today's local date).
- site\: a git repository (branch master) that Cloudflare Pages publishes when it is pushed. Never edit files in it by hand; render.py writes it.
- state.md: memory between runs. It holds the last issue number, the headlines and URLs used in the last 7 editions (to avoid repeating stories), and a running timeline for the two ongoing dossiers. Read it before researching; update it at the end (drop editions older than 7 days).
- The previous edition's JSON in editions\ is a good reference for tone, length and the dossier timelines. Carry the dossier timelines forward and add to them.

## Topics (nine sections, keys in brackets, in this order)
1. New Models [models]: frontier and open-weight model releases: launches, model cards, pricing, notable capabilities, API and product launches (OpenAI, Anthropic, Google DeepMind, Meta, xAI, DeepSeek, Qwen/Alibaba, Mistral…).
2. AI Safety Research [safety]: alignment, interpretability, evaluations, frontier lab safety reports and policies, AI safety institute work, notable papers (Anthropic, OpenAI, Google DeepMind, METR, Apollo, Redwood, UK AISI, arXiv…).
3. AI and Cybersecurity [cyber]: AI-discovered vulnerabilities and zero-days, AI-enabled attacks, agents escaping sandboxes or disabling monitoring, cyber-capability evaluations and lab cyber ratings, defensive AI, notable incidents.
4. Doom Watch [doom]: "AI doomer" news and existential-risk debate: warnings from prominent figures (Yudkowsky, Hinton, Bengio…), p(doom) discourse, pause/ban campaigns and bills, catastrophic-risk incidents, high-profile essays and rebuttals.
5. AI Hardware [hardware]: GPUs/accelerators (NVIDIA, AMD, Google TPU, custom silicon, Cerebras, Groq…), datacenters and power, export controls, chip supply, on-device AI.
6. Benchmarks [bench]: new results and records, new benchmarks, leaderboard changes (FrontierMath, Humanity's Last Exam, SWE-bench, ARC-AGI, LMArena, METR time horizons…), contamination and grading controversies.
7. Mathematics [math]: AI doing research mathematics. Dossier "openai-math" always present: OpenAI's October 2026 release of 722 AI-generated maths manuscripts (github.com/openai/math, "Sharing AI progress in mathematics"), what holds up, withdrawals, Lean verification, and mathematicians' reactions. The user calls it "the OpenAI 700-page mathematics paper(s)".
8. Physics [physics]: AI in physics. Dossier "astra" always present: OpenAI's GPT-6 Astra on the TheoPhysEval benchmark (arXiv 2610.16733), where the model stood by answers that disagreed with the experts' reference solutions, and the experts later found their own keys were wrong (49/50). Also related Astra physics work (e.g. the Grad's-conjecture counterexamples).
9. AI Science [science]: AI as a scientist beyond maths and physics: biology, chemistry, materials, medicine, climate. AI catching errors in published research, AI-designed proteins and drugs, automated labs, and especially cases where an AI contradicted experts and turned out to be right (the user loves these).

Put each story in exactly one section; a story that fits two (e.g. a cyber incident at a lab) goes where it is most useful and is not repeated.

Dossiers: add only new developments to the timeline. Use status "new" when something happened in the last ~48 hours, otherwise "nochange" with a one-line recap in "update". Keep the "could not verify" notes in the background until a detail is confirmed.

## Research
- Use WebSearch for each topic, focusing on the last 24–72 hours (up to 7 days for slower topics), and include the current month and year in queries. Use WebFetch to read every story you include: the "body" paragraphs must come from the actual source.
- Prefer primary sources (lab blogs, papers, announcements) and reputable outlets (Reuters, AP, The Verge, Ars Technica, Wired, MIT Technology Review, FT, Nature, Science, Quanta, IEEE Spectrum, The Register, La Presse…).
- Skip stories already in state.md unless there is a real new development.
- Never invent facts, quotes, numbers, dates or URLs. If a section has no fresh news, include one story that says so and points to the most recent relevant item.

## Writing
- English, crisp newspaper voice. Short concrete headlines. Each story: a 1–2 sentence standfirst, 3–5 body paragraphs (what happened, details, reactions, context), "why" (1–2 sentences), 2–4 "facts". Mark interviews, essays, op-eds and political statements "opinion": true.
- 2–4 stories per section. Exactly one "lead" story (the most important of the day), 3 "featured" stories from 3 different sections, and 6–8 stories with a "brief" line.
- "quote" and "number": one real quote and one striking figure from today's sources, with links.
- Images: when you fetch a source, you may note its og:image URL in "image" (credit = outlet name in capitals) if it is a real photo or illustration, not a logo. render.py fills in missing images itself and rejects logo-like ones, so leave "image" out rather than guess.
- issue = previous issue number in state.md + 1. generated_at = the current local time (HH:MM). date_long like "Friday, October 23, 2026".

## Finish
1. Validate: `python -c "import json;json.load(open(r'<path to today's json>',encoding='utf-8'))"`.
2. Render: `python "C:\Users\agervaischapleau\Documents\Newsletter-IA\render.py" "C:\Users\agervaischapleau\Documents\Newsletter-IA\editions\YYYY-MM-DD.json"`. This writes editions\YYYY-MM-DD.html, latest.html and updates site\. Fix the JSON and re-run if it errors.
3. Update state.md.
4. Publish: in C:\Users\agervaischapleau\Documents\Newsletter-IA\site run `git add -A`, then commit with the message "Edition YYYY-MM-DD (No. N)" followed by a blank line and "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>". Then, only if `git remote get-url origin` succeeds, run `git push origin master`. If there is no remote yet, skip the push and say so. If the push fails, report the error; do not change the remote, credentials or git config, and do not force-push.
5. Open the local page in the default browser: `cmd //c start "" "C:\Users\agervaischapleau\Documents\Newsletter-IA\editions\YYYY-MM-DD.html"` from Git Bash.
6. Reply with a 3–5 line summary: the lead story, the status of both dossiers, whether it was pushed, and the file path.