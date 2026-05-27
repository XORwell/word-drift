# Wikidata trigger-link re-resolution

After the strict prune (which removed 65 wrong `owl:sameAs` links from a broken
legacy mapping, e.g. Chernobyl -> ladyfinger biscuit, Stonewall -> dinosaur),
only **100** verified-OK trigger links remained and **202** `drift:TriggerEvent`
nodes had no `owl:sameAs`. Many of those unlinked triggers name real
events/entities/people/works that *do* have a correct Wikidata item. This pass
recovers them, strictly verified.

## Method

For every unlinked trigger (label / description / eventDate / category) a
Wikidata QID was sought via `wbsearchentities` + `wbgetentities`
(props `labels|descriptions|claims`, P31), polite (on-disk cache, 0.5 s delay,
UA `word-drift-research/0.4 (...; research@nennemann.de)`), cost $0.

A QID was **accepted only when** it (a) is a real referent (not a Wikimedia
category / disambiguation / list / template, not deleted/empty), (b) has a
label/description matching the trigger, (c) has a P31 type consistent with the
trigger (event for an event, person for an eponym, org/place/work/product as
appropriate and allowed for the trigger's `drift:triggerCategory`), and
(d) passes the existing audit gate verbatim
(`scripts/audit-trigger-qids.py --check`). Each candidate was run through the
audit's own `classify()` before being added; any that came back SUSPECT or BAD
was dropped. A wrong link is worse than none.

## Result

- **Unlinked before:** 202 (of 302 triggers; 100 linked)
- **Recovered (newly linked):** 24
- **Unlinked after:** 178
- **New total verified-OK:** 124 (all pass `audit --check`)

### Recovered links

Inline `owl:sameAs` added to `examples/*.ttl` (19):

| Trigger | QID | Wikidata entity |
|---|---|---|
| `trigger-mauerfall` | [Q69163529](https://www.wikidata.org/wiki/Q69163529) | fall of the Berlin Wall (event, Nov 1989) |
| `trigger-stonewall` | [Q51402](https://www.wikidata.org/wiki/Q51402) | Stonewall riots (1969 LGBT demonstrations) |
| `trigger-filterblase-pariser` | [Q111687183](https://www.wikidata.org/wiki/Q111687183) | The Filter Bubble (Eli Pariser, 2011 book) |
| `trigger-xerox-914` | [Q3570933](https://www.wikidata.org/wiki/Q3570933) | Xerox 914 (paper copier) |
| `trigger-aws-launch` | [Q456157](https://www.wikidata.org/wiki/Q456157) | Amazon Web Services |
| `trigger-monty-python-spam` | [Q1777591](https://www.wikidata.org/wiki/Q1777591) | Spam (Monty Python sketch) |
| `trigger-lesbian-sappho` | [Q17892](https://www.wikidata.org/wiki/Q17892) | Sappho (ancient Greek poet of Lesbos) |
| `trigger-uhu-de-brand` | [Q63281550](https://www.wikidata.org/wiki/Q63281550) | UHU GmbH & Co. KG (the company) |
| `trigger-south-sea-bubble` | [Q18643921](https://www.wikidata.org/wiki/Q18643921) | South Sea Bubble (1720 speculative bubble) |
| `trigger-apple-macintosh` | [Q1137478](https://www.wikidata.org/wiki/Q1137478) | Macintosh 128K (first Macintosh, 1984) |
| `trigger-sus-amongus` | [Q96417649](https://www.wikidata.org/wiki/Q96417649) | Among Us (2018 video game) |
| `trigger-slop-genai` | [Q115564437](https://www.wikidata.org/wiki/Q115564437) | ChatGPT (named catalyst, late 2022) |
| `trigger-queer-nation` | [Q5687582](https://www.wikidata.org/wiki/Q5687582) | Queer Nation (LGBTQ activist organisation) |
| `trigger-stan-eminem` | [Q312122](https://www.wikidata.org/wiki/Q312122) | Stan (2000 Eminem single ft. Dido) |
| `trigger-www-mosaic` | [Q381047](https://www.wikidata.org/wiki/Q381047) | Mosaic (early web browser) |
| `trigger-tank-somme` | [Q1284532](https://www.wikidata.org/wiki/Q1284532) | Mark I (first tank to enter combat) |
| `trigger-fromm-luther` | [Q1571095](https://www.wikidata.org/wiki/Q1571095) | Luther Bible (German Bible translation) |
| `trigger-arbeit-protestant` | [Q12562](https://www.wikidata.org/wiki/Q12562) | Protestant Reformation |
| `trigger-pfaffe-reformation` | [Q12562](https://www.wikidata.org/wiki/Q12562) | Protestant Reformation |

Added to `data/wikidata/trigger-links.ttl` (5, all `data/`-resident triggers):

| Trigger | QID | Wikidata entity |
|---|---|---|
| `trigger-wd-german-reunification` | [Q56039](https://www.wikidata.org/wiki/Q56039) | German reunification (1990 process) |
| `trigger-wd-world-wide-web-invention` | [Q466](https://www.wikidata.org/wiki/Q466) | World Wide Web |
| `trigger-wd-rise-of-funk-music` | [Q164444](https://www.wikidata.org/wiki/Q164444) | funk (music genre, emerged 1960s) |
| `trigger-wd-querdenken-711-protest-movement` | [Q115500066](https://www.wikidata.org/wiki/Q115500066) | Querdenken 711 (German conspiracy movement) |
| `trigger-tierc-chernobyl-1986` | [Q486](https://www.wikidata.org/wiki/Q486) | Chernobyl disaster (1986 nuclear accident) |

## Left unlinked (the honest outcome): 178

- **gfds-* word-of-the-year / Unwort items (~104):** these name a discourse
  moment or a word-of-the-year rather than a single real-world entity. No
  confident single referent -> left unlinked by design.
- **Abstract semantic-process triggers** (polysemous extension, semantic
  bleaching, ironic reversal, intensifier/downtoner shifts, soziale
  Generalisierung, Aufwertung, ...): no real-world referent entity exists.
- **Mythological eponyms** (Pan/panic, Nemesis, Tantalus/tantalize,
  Hercules/herculean): their canonical items are not instance-of human, so the
  person heuristic cannot distinguish the deity from a modern namesake.
- **Brand-vs-generic toponym/product ambiguity** (thermos, tempo, foehn,
  granola, ...): the trigger word *is* the brand and no clean company/person
  referent is unambiguous.
- **Candidates dropped because they would FAIL the audit gate:**
  `proletariat-sozialismus` -> The Communist Manifesto (Q40591) and
  `assassin-crusades` -> Order of Assassins (Q187715) both classify as a "work"
  kind, which the gate rejects for a Political trigger. Left unlinked rather
  than force a link the gate would not accept.
- **No confident single referent:** `draconian-code` (Draco the lawgiver does
  not surface above same-name noise), `stan` had to be resolved via a filtered
  search (the song Q312122 *was* found and linked); `ghosting-datingapps`,
  `hooligan-press`, `jingoism-song`, `ecology-movement` (vague movement, no
  single org) all lacked a clean unambiguous item.
