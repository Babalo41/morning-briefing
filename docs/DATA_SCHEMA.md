# EDITION_DATA schema

`docs/data.js` must set `window.EDITION_DATA` to an object with this exact shape.
`docs/app.js` reads these field names verbatim — keep the pipeline's output in sync with this file.

```js
window.EDITION_DATA = {
  generated_at: "2026-08-27T02:00:00+02:00",  // ISO 8601, string or null
  editions: [ /* Edition, newest first */ ],
  glossary: { /* termId: GlossaryTerm */ },
  charts:   { /* chartId: Chart */ },
  learn:    [ /* Course */ ],
};
```

## Edition

```js
{
  id: "2026-08-27",        // string, unique, sorts newest-first when array order does
  day: "Thu", dnum: "27", mon: "Aug",   // short pieces used in the archive-row date badge
  date: "Thursday 27 August 2026",      // full human date shown in the lede
  headline: "string",       // one-line summary shown large in the lede card
  stand: "string",          // 2-5 sentence standfirst paragraph under the headline
  blocks: [ /* Block */ ]
}
```

Optional: an entire edition can be locked by replacing everything except `id`/`day`/`dnum`/`mon` with
an encrypted envelope (see **Encryption** below): `{ id, day, dnum, mon, encrypted:true, ciphertext, iv, salt }`.
The decrypted JSON must then contain `{ date, headline, stand, blocks }`.

## Block

One block = one section of an edition (e.g. "Weather", "Needs attention").

```js
{
  h: "Weather",              // section title (always plain text, even if the block is encrypted)
  pri: false,                // optional — true marks every item in this block as high-priority (red dot, tinted row)
  stats: [ { n: "27°", l: "today, then it breaks" } ],  // optional stat tiles shown above the item list
  items: [ /* Item */ ],
  chart: "wxtemp",           // optional — a chart id, or an array of chart ids, rendered after the item list
  go: { label: "string", q: "string" }  // optional CTA button; q is a prompt seeded into a "go" link
}
```

**Encrypted block** (whole section locked, e.g. health data): replace `items`/`stats`/`chart`/`go`/`pri` with
an encrypted envelope, keeping `h` and adding a plaintext `count` (used for the chip/badge number before unlock):

```js
{ h: "Diabetes & supplies", encrypted: true, count: 3, ciphertext: "...", iv: "...", salt: "..." }
```

The decrypted JSON must be `{ pri, stats, items, chart, go }` (any subset — same fields as a normal block minus `h`).

## Item

```js
{
  t: "string",               // title
  b: "string (may contain inline HTML: <b>, <i>, <span class=\"jt\" data-g=\"termId\">word</span>)",
  src: "string",             // short source label, e.g. "per wetter.com" or "in your inbox"
  u: "https://...",          // optional — if present, src becomes a link
  teach: { s: "string", b: "string (HTML, one or more <p>)" }  // optional expandable "learn more" block
}
```

`<span class="jt" data-g="termId">word</span>` inside `b` or `teach.b` makes that word tappable — it opens the
glossary sheet for `glossary[termId]`. `termId` must exist in the top-level `glossary` map.

**Encrypted item** (single sensitive story, e.g. a health-specific line inside an otherwise public block):

```js
{ encrypted: true, ciphertext: "...", iv: "...", salt: "..." }
```

The decrypted JSON must be a plain `Item` (`{ t, b, src, u, teach }`).

## GlossaryTerm

```js
{
  t: "MARD",                          // display term
  ipa: "/mɑːd/",                      // IPA pronunciation
  resp: "mard — rhymes with 'card'",  // respelling / rhyme hint
  lang: "en-GB",                      // BCP-47 tag used for text-to-speech voice selection
  d: "string",                        // plain-language definition
  w: "string"                         // "why it matters to you" — personalized context
}
```

## Chart

Three kinds, all keyed by id under `charts`:

```js
// kind: "bar"
{ kind:"bar", title:"string", sub:"string", source:"string", catW:84,
  rows:[ { k:"Thu 27", v:0, lab:"0%", hero:false, tip:"optional tooltip text" } ] }

// kind: "range" (dumbbell / min-max)
{ kind:"range", title:"string", sub:"string", source:"string", ticks:[0,25,50,75,100], catW:150,
  rows:[ { k:"Senior tester", lo:58, hi:80, hero:false } ] }

// kind: "line"
{ kind:"line", title:"string", sub:"string", source:"string",
  xlabels:["27","28","29"], yticks:[0,10,20,30],
  series:[ { name:"Max °C", hero:true, pts:[[0,27],[1,24],[2,23]] } ] }
```

`hero: true` on a row/series renders it in the house red instead of the neutral/blue tone — use it for the one
data point the chart's headline is actually about. Always fill in `source` — every chart shows a source line.

## Course (Learn library)

```js
{
  id: "saurashtra", title: "string", blurb: "string",
  lessons: [
    { t: "string", key: "string (one-line takeaway)", b: "string (HTML, <p> paragraphs, may use <span class=\"jt\">, <p class=\"rem\"><b>Worth holding onto</b>...</p>)",
      chart: "optional chart id" }
  ]
}
```

## Encryption

Encrypted envelopes (`{ encrypted:true, ciphertext, iv, salt }`, all fields except `encrypted` base64 strings)
must be produced with: PBKDF2-HMAC-SHA256, 100000 iterations, a random 16-byte `salt`, AES-256-GCM with a random
12-byte `iv`. The plaintext is `JSON.stringify(...)` of the fields listed above for that node type, UTF-8 encoded,
before encryption. `docs/app.js`'s `deriveKey`/`decryptNode` functions are the reference implementation — the
Python pipeline's encryption must produce byte-for-byte compatible output (same KDF params, same AES mode).

## Minimal example

```json
{
  "generated_at": "2026-08-27T02:00:00+02:00",
  "editions": [
    {
      "id": "2026-08-27", "day": "Thu", "dnum": "27", "mon": "Aug",
      "date": "Thursday 27 August 2026",
      "headline": "Example headline for today",
      "stand": "One or two sentences summarizing the day.",
      "blocks": [
        { "h": "Weather",
          "stats": [ { "n": "18°", "l": "today" } ],
          "items": [
            { "t": "Example City stays mild and dry", "b": "A short paragraph of detail.",
              "src": "per Example Weather Source", "u": "https://example.com" }
          ],
          "chart": "example_temp" }
      ]
    }
  ],
  "glossary": {
    "example_term": { "t": "Example Term", "ipa": "/ɪɡˈzæmpəl/", "resp": "ig-ZAM-pul",
      "lang": "en-GB", "d": "Plain-language definition.", "w": "Why it matters to the reader." }
  },
  "charts": {
    "example_temp": { "kind": "line", "title": "Example finding stated as a headline",
      "sub": "Example City, daily max, °C", "source": "Example Weather Source",
      "xlabels": ["Mon","Tue","Wed"], "yticks": [0,10,20],
      "series": [ { "name": "Max °C", "hero": true, "pts": [[0,18],[1,17],[2,19]] } ] }
  },
  "learn": [
    { "id": "example_course", "title": "Example Course", "blurb": "One line about the course.",
      "lessons": [ { "t": "Example lesson", "key": "One-line takeaway.", "b": "<p>Lesson body.</p>" } ] }
  ]
}
```
