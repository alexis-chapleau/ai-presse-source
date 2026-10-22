# Le Quotidien IA: project brief

A complete summary of the project as of **October 22, 2026**, written so a new Claude session (or you) can pick it up cold or rebuild it from scratch.

---

## 1. What it is

**Today:** a personal AI-news newspaper that Claude researches and writes every morning. It looks like **lapresse.ca** on desktop and like the **La Presse iPhone app** on a phone. It's published to a private website you open from an iPhone home-screen icon.

**Where it could go:** a news and continuing-education app for **internal medicine physicians**. It would have accounts, comments, @mentions, "what's hot" rankings, articles released through the day, CPD credit logging, accredited quizzes and a Pro subscription. See sections 8–10.

---

## 2. What exists right now

| Piece | Where | Notes |
|---|---|---|
| Daily task | Claude desktop app → Scheduled → `daily-ai-newsletter` | Runs at **06:00** local time (the app adds a few minutes, about 06:09). The app must be open and the PC awake; otherwise it runs at the next launch. The full prompt is in `C:\Users\agervaischapleau\.claude\scheduled-tasks\daily-ai-newsletter\SKILL.md`. |
| Project folder | `C:\Users\agervaischapleau\Documents\Newsletter-IA\` | Everything below lives here. |
| `render.py` | project folder | **The heart of the project** (about 1,000 lines of Python, standard library only; Pillow optional for the icons). It turns one edition JSON into the full HTML and rebuilds `site\`. |
| `SCHEMA.md` | project folder | The edition JSON format the daily task must follow. |
| `state.md` | project folder | Memory between runs: last issue number, stories used in the last 7 days, and the dossier timelines. |
| `editions\YYYY-MM-DD.json` / `.html` | project folder | One data file and one page per day. Issue No. 1 = 2026-10-22. |
| `.cache\og-images.json` | project folder | Cache of each source page's preview image (og:image). |
| `site\` | project folder | **The only thing on GitHub.** Private repo `github.com/alexis-chapleau/ai-presse`, branch `master`. Contains `index.html` (newest edition), `editions\`, `archive.html`, `manifest.webmanifest`, `icons\`, `_headers`, `robots.txt`. |
| Hosting | Cloudflare (a Worker built from the GitHub repo) | Rebuilds automatically on every push to `master`. |
| Privacy | Cloudflare Zero Trust → Access app `ai-presse` | Covers the production and preview URLs; a policy allows only listed emails; sessions last 2 weeks. |
| Phone | Safari → Share → Add to Home Screen | Opens full screen with the red "IA." icon. |

> **Two repos.** The project folder itself is a **source repo** (branch `main`, private): `render.py`, `SCHEMA.md`, `state.md`, `editions\*.json`, this brief, and `task\daily-ai-newsletter.SKILL.md`. That last file is a snapshot of the scheduled task's prompt; recreate the task from it on a new machine. Its `.gitignore` excludes `site\` (the published repo, cloned separately), the generated HTML and caches. To rebuild elsewhere: clone the source repo, clone `ai-presse` into `site\` inside it, run `python render.py editions\<latest>.json`, and recreate the scheduled task from the snapshot (update the paths).

**Hard rule from you:** never connect this PC to Cloudflare (no `wrangler`, no API tokens). Publishing happens only through `git push`; Cloudflare pulls from GitHub.

---

## 3. How the daily run works

```
06:00  Claude (scheduled task)
  1. read SCHEMA.md, state.md, the previous edition's JSON
  2. WebSearch + WebFetch each topic (last 24–72 h); read every source it uses
  3. write editions\YYYY-MM-DD.json (content only, no HTML)
  4. python render.py editions\YYYY-MM-DD.json
       → editions\YYYY-MM-DD.html + latest.html
       → rebuilds site\ (index, archive, icons, manifest, headers)
       → fills missing images from each source's og:image, skipping logos
  5. update state.md
  6. git add/commit in site\ → git push origin master
  7. open the page locally, reply with a 3–5 line summary
Cloudflare: push → build → live behind Access
```

**Key design decision:** **content is separate from layout.** Claude writes only JSON, and `render.py` owns all the HTML and CSS, so every edition looks identical. To change the look, edit `render.py` only.

### Sections (in this order; key, name, colour, decorative glyph)
`models` New Models #FFAF00 "LLM" · `safety` AI Safety #5A79A0 "AI" · `cyber` Cyber #D25F68 "</>" · `doom` Doom Watch #840132 "p(doom)" · `hardware` Hardware #207FB7 "GPU" · `bench` Benchmarks #14A574 "%" · `math` Mathematics #A05FA8 "∑" · `physics` Physics #FF6C00 "Ψ" · `science` AI Science #6B9500 "DNA"

The colours are La Presse's real section colours, taken from their stylesheets.

### Two ongoing "Dossiers" (always present, with a timeline that grows each day)
- **`openai-math`:** OpenAI's October 2026 release of 722 AI-generated maths manuscripts (github.com/openai/math): withdrawals, Lean-verification problems, mathematicians' reactions. You call it "the OpenAI 700-page maths paper". No single ~700-page paper was found; the longest manuscript is 199 pages.
- **`astra`:** GPT-6 Astra on TheoPhysEval (arXiv 2610.16733), 50 unpublished physics problems. The model stuck to its answers, the experts found errors in their own answer keys, and the corrected score was 49/50. Related: the Grad's-conjecture counterexamples in plasma physics.

### Content rules
- Never invent facts, quotes, numbers, dates or URLs; every story links to a real source it actually read.
- Each story has: kicker, italic suptitle, headline, standfirst, 3–5 body paragraphs, "why it matters", 2–4 key facts, source plus extra sources, and an optional image.
- Each edition has exactly one `lead`, 3 `featured` (from different sections), 6–8 `brief` lines, a quote and a number of the day, and a sources list.
- Mark interviews and op-eds `opinion: true`; they use the slab "chronique" headline font.
- Images: the source's og:image is used unless the URL matches `logo|default|placeholder|gravatar|blavatar|favicon|icon|avatar`. Without one, a dark typographic panel in the section colour is shown.

---

## 4. Design spec (to rebuild the look)

### Desktop (lapresse.ca)
- **Fonts:** La Presse's are Verlag, Rubrik and Sentinel (all paid) plus Roboto Serif. The free stand-ins used: **Figtree** (headlines, nav, badges), **Rubik** (dates, menus), **Roboto Slab** (opinion headlines), **Roboto Serif** (article text, italic suptitles), all from Google Fonts.
- **Colours:** red `#e12929`, ink `#000`/`#232325`, grey `#686868`/`#8d8d8d`, page `#f8f8f8`.
- **Layout, top to bottom:**
  - thin utility bar
  - white header: red 100×100 logo block "LE QUOTIDIEN / IA.", date, Montréal weather (from wttr.in), issue number, grey box with a yellow pill "Read today's lead"
  - black sticky section nav (uppercase; the active section is underlined in its colour)
  - hero: 66% photo + 34% dark panel with a blurred copy of the photo, badge, suptitle, white 34px headline
  - sidebar (300px): "The number" box and "Today's essentials" (red top line)
  - three featured cards
  - black "Dossiers" band
  - big centred quote
  - one block per section: big card + compact list with thumbnails
  - black footer with numbered sources
- **Article page:** a sub-menu bar in the section colour, a centred 740px column plus a 300px sticky sidebar, badge, grey kicker, 46px headline, 3:2 photo with an uppercase "PHOTO: OUTLET" credit, byline, bold intro, serif body, "Why it matters" box, numbered key facts, a source box with a "Read the original ›" pill, and "More in this section".
- **Badges:** rounded 5px, uppercase, white on the section colour; the dossier badge reads "DOSSIER | N updates" on navy.
- **Routing:** a single HTML file; `#story-id` shows the article and hides the front page.

### Phone (La Presse app) at widths ≤ 700px
- **Top:** red sticky app bar with a yellow ★ circle (opens the lead), "LE QUOTIDIEN IA" in the centre, and a calendar icon (archive). The status bar is red (`black-translucent` plus safe-area padding).
- **Feed:** "THE HEADLINES / What you need to know this morning." then white rounded cards (10px radius, soft shadow). Each card has a 16:10 photo with the section badge on it, suptitle, 21px headline, a 3-line summary, a blue `#1eaefd` dot with the date, and bookmark and share icons. Compact cards (text left, square thumbnail right) are used inside sections. Further down: the dossier cards (dark), quote, number, section chips, and sources in a collapsible list.
- **Floating frosted tab bar:** Front page · Dossiers · Saved · Sections · Archive.
- **Article = native iOS sheet:**
  - slides up with `transform` over 0.5s on `cubic-bezier(.32,.72,0,1)`
  - the feed behind it recedes to 93% scale and darkens (scrim)
  - a sticky colour bar with a grab handle, then the photo with its credit overlaid, the meta row (dot, date, 📖 N min) and a grey source box
  - **drag to dismiss:** the sheet follows the finger; it closes beyond 25% of the screen height or on a flick (faster than 1 px/ms and more than 40px); otherwise it springs back
  - closing is animated too, and the feed's scroll position is kept
- **Bookmarks:** saved in `localStorage` (`qia-saved`) and shown on the Saved page. **Share** uses `navigator.share` with the **source** URL, since the private site's own link wouldn't open for anyone else.
- **Home-screen app:** manifest, `apple-touch-icon` and icons generated with Pillow (red square, Arial Black), theme colour `#e12929`, `noindex` everywhere.
- **Implementation note:** the feed and header sit in `#stage` (scaled behind the sheet); the sheets sit in `#sheets` outside it, because a CSS transform on an ancestor breaks `position:fixed`. On desktop, `#stage{display:contents}`.

### Gotchas learned
- **Headless screenshots:** Chrome won't make a window narrower than about 500px. To test phone layouts, load the page in a 390px `<iframe>`, or use the preview tool's mobile preset.
- **Shell:** large heredocs with quotes break the Windows Git Bash tool; write files with the Write tool instead.
- **Python 3.11:** f-strings can't reuse the same quote character in nested expressions.
- **Phone tap bugs:** you reported articles sometimes not opening on tap. A later commit, "Make whole cards tappable", addressed it; re-check it on a real iPhone.

---

## 5. Legal and safety notes (current newsletter)
- **The La Presse look:** a layout and colour scheme can't really be owned; the code is original and the name is different. The red-square logo is the only close resemblance. It's fine while the site is private; **rebrand before going public or commercial**.
- **Photos:** loaded directly from the source sites (some are Reuters/AP). This is acceptable only because the site is private behind Access. A public site would need licensed or original images.
- **Privacy:** keep `noindex` and Access on.

---

## 6. Proposed architecture for the multi-user version

```
Claude (once a day) → JSON with a release time per article → git push
Cloudflare:
  static files (app shell, article JSON)      cached at the edge, almost free
  Worker /api  ── D1 (SQLite)                 accounts, comments, likes, mentions, notifications
  Cron trigger (every 5 min)                  release drip, hot scores, push notifications
```
- **Drip release ("dopamine hits"):** generate the whole day once at 06:00 and give each article a random `release_at`; the Worker's feed only returns articles already released. This avoids extra Claude runs and doesn't need the PC on. Add a "N new stories ↑" pill that appears when articles land while someone is reading.
- **Accounts (when open to the public):** **Better Auth** on Workers + D1, offering email + password (slow salted hashes, a check against leaked-password lists), **two-factor login** with an authenticator app plus backup codes, and **passkeys** (Face ID). Also:
  - Turnstile (Cloudflare's free invisible CAPTCHA) on sign-up and login, plus rate limits
  - secure session cookies that page scripts can't read (HttpOnly, Secure, SameSite)
  - 2FA required for admins
  - email via Resend or Postmark
  - the **$5/month Workers paid plan**, because the free plan's processing limit is too tight for password hashing
  - Cloudflare Access kept for admin pages only
- **Database tables:** `users(id,email,handle,display_name,tier,verified)`, `comments(id,article_id,user_id,body,parent_id,created_at,deleted_at)`, `likes(user_id,article_id)`, `mentions(comment_id,user_id)`, `notifications(user_id,type,link,read_at)`. Article IDs never change, e.g. `2026-10-22/openai-monitors`, so comments stay attached in the archive.
- **Comment security:**
  - plain text only, shown as text and never as HTML
  - prepared statements for every query
  - 5 comments a minute per user, 2,000 characters maximum
  - `@handle` links only to users that exist
  - users delete their own comments, admins delete any
  - a strict content security policy (no inline scripts)
- **"Hot" ranking** (recalculated by the cron job, then cached):
  `score = (likes + 3×comments + 2×saves + 0.2×reads) / (hours since release + 2)^1.5`
  Tabs: À la une (your editorial pick) · Hot · Most discussed · Latest. Don't show *Hot* until an article has some minimum activity.
- **Push notifications:** iPhone home-screen web apps support them (iOS 16.4+) through a service worker. Send them for releases and @mentions, and use them sparingly.
- **Cost:**
  - Cloudflare's free tier covers dozens of users: Workers 100k requests/day, D1 5 GB, cron triggers, Access ≤50 users. Add the $5/month paid plan once passwords are involved.
  - The main cost is **one Claude run a day**.

---

## 7. The doctor version (internal medicine)

### Audience tiers and verification
| Tier | Verified by | Can |
|---|---|---|
| Interested public | email | read free headlines |
| Students / residents | university or hospital email (@umontreal.ca, @mail.mcgill.ca, @ulaval.ca, @usherbrooke.ca…) | read, comment with a "Student" badge, reduced price |
| Verified physician | hospital/CIUSSS email **or** licence number checked against the Collège des médecins' public directory | everything, with a "Verified MD" badge |

Verification is optional for reading and required for commenting. In Quebec the permit number is already public and printed on prescriptions, but offer the work-email option first.

### Content format ("AI rewrites nothing")
- A small **labelled "AI summary"** at the top ("Generated by AI, may contain errors").
- Then the **verbatim abstract, only when its licence allows it**, plus journal, authors, DOI and link.
- **A physician reviews articles before release.** The release schedule makes room for that.
- Sources: trials (NEJM, Lancet, JAMA, Annals, BMJ), guideline updates, Health Canada and FDA approvals and safety alerts, and AI in medicine.

### Copyright and scraping (verified)
- PubMed's operator (the NLM) doesn't own the abstracts in PubMed; **publishers or authors may**, and the NLM can't grant reuse.
- **CC BY open access:** copy word for word with attribution, including in a paid app.
- **CC BY-NC:** not allowed in a paid product (several big medical journals use it).
- **Closed journals:** show only the title, journal, key trial numbers (facts aren't copyrighted), maybe one short attributed quote, the labelled AI summary and the link. Anything more needs a licence from the publisher or the Copyright Clearance Center.
- **Don't scrape publisher sites.** Use the official data services: **PubMed E-utilities** (free API key), **Europe PMC** (it reports each article's licence), **Crossref**, and the journals' **RSS** feeds.
- Get one review from an IP lawyer before launch.

### CPD / MOC facts (verified)
- **Royal College MOC:** since 2024, **250 credits per 5-year cycle**, at least **25 a year**, and at least **25 Section 3 credits per cycle**.
- **Section 2 reading:** **0.5 credits/hour**, capped at **30 credits/year**.
- **Reading to answer a specific clinical question** ("activity preparation"): **2 credits/hour**.
- **Accredited Section 3 self-assessment:** **3 credits/hour**; each program stays accredited for 3 years.
- **Quebec (CMQ):** **250 hours per 5 years**, at least 25 a year, of which 125 must be accredited activities and 10 practice evaluation. **My MOC credits are mapped to CMQ hours automatically** for Quebec-based Fellows.
- **MAINPORT was replaced by "My MOC" in August 2024.** **There's no public API** for third-party apps to submit credits; doctors enter Section 2 credits themselves. Only accredited systems connect: ACCME activities sync into My MOC daily, and the US ACCME has a "PARS" API for accredited providers. Ask cpd@royalcollege.ca whether a provider data feed exists.

### CPD features (no visible timer)
- **Time comes from the word count:** the estimate is pre-filled and editable. Doctors self-report, so nothing tracks them.
- **"Log to my CPD record"** sheet at the end of each article:
  - a toggle, "I also read the full paper"
  - a toggle, "I read this for a clinical question" (2 credits/hour), which asks for the question in one line
  - one key takeaway
- **Weekly or monthly batch:** "This week: 14 articles, about 1h40. Log 0.8 credits?"
- **Monthly My MOC entry:** pre-filled for copying, plus a **PDF transcript and certificate** to attach, a button that opens My MOC, and a reminder notification on the 1st of each month.
- **Keeping them in the app:** the in-app page is good enough that most never leave. The original paper opens in an in-app browser; when they come back, "I read the full paper" is already switched on.

### Accredited quizzes (Section 3), the strongest Pro feature
1. Co-develop the quizzes with a **"physician organization"**, for example the Quebec internists' association (AMIQ), a university medicine department or a specialist federation. It provides the scientific planning committee; a private company can't apply on its own.
2. Have the program reviewed by an **accredited CPD provider**: the **FMSQ** or a university CPD office. At the FMSQ:
   - the application must come from a physician organization recognised by the Royal College and be signed by a specialist
   - documents: needs assessment, committee members, conflict-of-interest disclosures, funding agreements, evaluation form, budget
   - submit **at least 8 weeks** before launch; review takes 10–15 business days
   - **at least $500 plus tax** for organizations not affiliated with the FMSQ
3. Format: a monthly quiz of about 10 questions built from that month's articles. Each answer gives feedback and links back to the article. Accredited programs then appear in My MOC's list of accredited activities.

### Monetization, best first
1. **CPD value:** automatic reading logs, the clinical-question mode, export, accredited quizzes.
2. **Subscription:** a free plan for reading; **Pro (~$10–15/month or $99–149/year)** for CPD logging, export, quizzes, archive search and comments. Offer annual billing with GST/QST receipts.
   - **Tax-deductible:** the CRA lets self-employed professionals deduct subscriptions to publications (T2125 line 8760). Most Quebec physicians are self-employed or incorporated; salaried residents generally can't deduct.
   - Quebec specialists also have RAMQ professional-development programs (mostly per-diems and travel); check whether a subscription could ever qualify.
3. **Group licences:** departments, residency programs, hospitals.
4. **Sponsorships:** start with non-pharma sponsors (banks and insurers for doctors, medical software, recruiters). Pharma ads aimed at doctors need **PAAB clearance** and verified-doctor gating, and they risk your credibility.
5. **Job board:** hospitals and locum postings.

Never sell personal data.

### Legal checklist
- **Privacy:** Quebec **Law 25** (privacy officer, consent, breach reporting) and **CASL** (Canada's anti-spam law) for emails.
- **Contracts:** terms of use and a privacy policy.
- **Comment rules:** no patient-identifying information.
- **Disclaimer:** a medical disclaimer.
- **Branding:** rebrand away from La Presse.

### App Store (verified guidelines)
- **4.2 Minimum functionality:** the app must be more than a "repackaged website". Under **4.2.2**, apps mustn't be mainly "content aggregators, or a collection of links". Native extras answer both: push, a widget, offline reading, Face ID, CPD tools, comments, quizzes.
- **1.4.1 Medical:** apps get "greater scrutiny" and must remind users to check with a doctor.
- **5.1.1(v):** if users can create an account, they must be able to **delete it from inside the app**.
- **3.1.1 Payments:** in Canada, subscriptions sold in the app must use in-app purchase; Apple takes 15% under its Small Business Program. The **3.1.3(a) "reader app"** exception (magazines, newspapers…) allows login-only apps, but CPD tracking is a feature, so Apple will probably still require in-app purchase for Pro.
- **Path:** an Apple Developer account ($99/year; a company account needs a D-U-N-S number, 1–2 weeks), then **Capacitor** to wrap the web app plus native features (3–6 weeks part-time), then TestFlight, then review (usually 1–3 days, expect one or two rejections). **About 1.5–3 months in total.**

---

## 8. Roadmap
1. **Now (personal):** keep the daily AI newsletter running; check the tap fix on the iPhone; back up the source to a private repo.
2. **Beta for doctors:**
   - change the topics to internal medicine
   - switch the article format to AI summary + abstract when licensed, with a physician review step
   - drip release, the "new stories" pill, offline reading
   - invite **10–20 internists for a month**; success = they open it most mornings unprompted
3. **Social:** accounts (Better Auth), tiers and verification, comments, likes, @mentions, the Hot tab, push notifications.
4. **Pro:** Stripe (with GST/QST), the CPD log and exports, the clinical-question mode.
5. **Accreditation:** partner with AMIQ or a university and submit the Section 3 quiz program through the FMSQ.
6. **App Store** with Capacitor, once the beta shows people come back every day.

### Open questions
- Product name and branding (to replace the La Presse look-alike).
- French, English or both? The target market is Quebec, so French is likely needed.
- Who reviews the medical content, and how fast each day?
- Does My MOC have a data feed for accredited providers?
- Which journals' licences allow showing abstracts word for word?

---

## 9. Starter prompt for a new session
> I'm continuing a project described in PROJECT_BRIEF.md (attached or in this folder). Read it fully first. The source files are render.py, SCHEMA.md and state.md, plus editions/*.json; the published site is the git repo alexis-chapleau/ai-presse (branch master), hosted on Cloudflare behind Access. Never install wrangler or add Cloudflare credentials on my machine; publishing is git push only. Today I want to: <your goal>.

---

## Sources (verified on 2026-10-22)
- Royal College, Refreshed MOC framework: https://www.royalcollege.ca/content/dam/document/cpd/refreshed-moc-framework-e.pdf
- Royal College, The MOC Program: https://www.royalcollege.ca/content/rcpsc-site-v2/ca/en/cpd/moc-program.html
- CAPA, Evolution of the MOC Program in 2024: https://capa-acam.ca/paccc/continuing-professional-development/evolution-of-the-moc-program-in-2024
- Royal College, Quebec-based Fellows and the MOC Program: https://collegeroyal.ca/content/rcpsc-site-v2/ca/en/cpd/moc-program/quebec-based-fellows-and-the-moc-program.html
- Royal College, Self-Assessment Programs (Section 3): https://www.royalcollege.ca/en/standards-and-accreditation/cpd-accreditation/standards/self-assessment-programs.html
- FMSQ, Accréditer une activité de formation: https://fmsq.org/fr/accrediter-une-activite-de-formation
- LégisQuébec, Règlement sur la formation continue obligatoire des médecins: https://www.legisquebec.gouv.qc.ca/fr/document/rc/M-9,%20r.%2022.1%20/
- CRA, T2125 line 8760: https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/sole-proprietorships-partnerships/report-business-income-expenses/completing-form-t2125/line-8760-business-tax-fees-licenses-dues-memberships-subscriptions.html
- ACCME, Royal College MOC: https://accme.org/data-reporting/maintenance-of-certification/royal-college-moc/
- ACCME, Learner credit data in PARS: https://www.accme.org/learner-credit-data
- PubMed Help (abstracts and copyright): https://pubmed.ncbi.nlm.nih.gov/help/
- PMC Copyright Notice: https://pmc.ncbi.nlm.nih.gov/about/copyright/
- Initiative for Open Abstracts: https://force11.org/post/introducing-the-initiative-for-open-abstracts-i4oa/
- Apple App Store Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
