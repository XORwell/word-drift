# Verify chunk 4 — report

Strict source-fetch verification of 38 example files against `docs/verify-criteria.md`.
Sources fetched: etymonline, DWDS, Merriam-Webster, Wikipedia, GfdS (per word).

| word | verdict | what the sources did / didn't support | action taken |
|------|---------|----------------------------------------|--------------|
| aspirin | KEEP | Wiktionary/Wikipedia: Bayer brand 1899, US ruled generic 1921; broadening sound | none |
| backfisch | FIX | DWDS attests figurative "adolescent girl" as **mid-16c student slang**, NOT a 19c coinage; file said firstAttested 1850 | firstAttested 1850→1550; drift interval start 1800→1550; trigger reframed as older sense + 19c Backfischroman spread |
| bikini | KEEP | etymonline/Wiktionary: Bikini Atoll tests July 1946, Reard swimsuit same year | none |
| blitz | KEEP | etymonline/Wiktionary: clipped from Blitzkrieg, "the Blitz" 1940, broadened to intensive effort | none |
| brutal | FIX | etymonline earliest = mid-15c (not 1640); neither etymonline nor MW attests an "admiring intensifier"; MW does attest weakened "harsh/severe/unpleasant" (brutal weather, brutal truth) | firstAttested 1640→1450; gloss/header/trigger tightened to drop unsupported "admiring" claim; kept Speculative 0.55 |
| circle | KEEP | SemEval detection-benchmark word; ChangeSignalAlignment + honest Speculative 0.6, in-repo semeval.ttl; cause correctly flagged undetermined | none |
| currant | KEEP | etymonline/Wiktionary: raisins of Corinth, -s reanalysed as plural; metonymization sound | none |
| dirne | KEEP | DWDS + Nübling (2011): girl→maid→prostitute pejoration; classic, well-sourced | none |
| elend | KEEP | DWDS/Wikipedia: OHG eli-lenti "exile" → "misery"; no overclaimed trigger (no hypothesis) | none |
| filterblase | KEEP | DWDS examples cite Pariser as originator (US-Autor); loan-translation + 2011 book widely documented; Wortverlaufskurve URL works | none |
| front | KEEP | DWDS/Wiktionary: military line → WWI war-zone → figurative; WWI trigger sound | none |
| gaslighting | FIX | WOTY 2022 + 1740% lookup rise + politics/misinformation framing all confirmed, but cited MW URL now resolves to the 2025 WOTY page | source URL `/word-of-the-year` → `/word-of-the-year-2022` (working specific page) |
| ghosting | FIX | MW attests the relationship sense but does NOT tie it to dating apps; the dating-app trigger is curator inference, only corroborated by a frequency spike | evidenceType LexicographicNote→Speculative (kept FrequencyCorrelation); confidence 0.8→0.6; comment corrected |
| guillotine | KEEP | etymonline/Wikipedia: Guillotin proposed 1789, machine adopted 1792, eponym | none |
| hertz | KEEP | etymonline/Wikipedia: Heinrich Hertz, EM waves 1888, unit ratified later; metonymization sound | none |
| jeans | KEEP | etymonline/Wiktionary: jean cloth ex Genoa, then trousers; metonymization sound | none |
| kavalier | KEEP | DWDS/Wiktionary: mounted noble → courteous gentleman via baroque court culture; modest 0.65 | none |
| krass | KEEP | DWDS confirms Jugendsprache positive intensifier + Latin crassus; no date given but file already Speculative 0.55 with explicit "anchor year not a cause" caveat | none |
| like | KEEP | etymonline/Wikipedia: Facebook Like button Feb 2009; metonymization sound, mixed Lexicographic+Speculative | none |
| luegenpresse | FIX | Core (1848 polemic → 2014 PEGIDA far-right reactivation) sound on Wikipedia+GfdS; but file claimed FrequencyCorrelation with NO frequency observations/corpus in the file | dropped FrequencyCorrelation (kept LexicographicNote); confidence 0.9→0.85; added GfdS as second hypothesis source |
| maus-de | KEEP | DWDS/Duden: rodent → computer mouse, Macintosh 1984; metaphorization sound | none |
| mesmerize | KEEP | etymonline/Wikipedia: Mesmer's animal magnetism 1780s → hypnotise → captivate | none |
| naughty | KEEP | etymonline confirms late-14c "evil/immoral" and 1630s weakened "mischievous"; matches file (1380/1630), modest 0.6 | none |
| notorious | KEEP | etymonline confirms neutral 1540s + pejorative 17c "by frequent association with derogatory nouns" — matches collocation trigger | none |
| panic | KEEP | etymonline/Wikipedia: god Pan → sudden contagious fright; metaphorization sound | none |
| pretty | KEEP | etymonline confirms OE prættig "cunning/wily" + 1560s adverbial downtoner; matches file (1000/1565) | none |
| querdenker | FIX | Movement (founded April 2020, Stuttgart, Querdenken-711, lateral-thinker→pejorative) well documented, but cited de.wikipedia URL `Querdenken_(Bewegung)` returns 404 | source URL → working `https://de.wikipedia.org/wiki/Querdenken` (has "Querdenker als Bezeichnung" section) |
| rugby | KEEP | etymonline/Wiktionary: Rugby School handling code → sport; metonymization sound | none |
| schuetzengraben | KEEP | DWDS/Wiktionary: fortification term → WWI emblem → figurative entrenchment | none |
| silhouette | KEEP | etymonline confirms Étienne de Silhouette (finance min. 1759) eponym; outline sense late-18c/1843; metonymization sound | none |
| spam | KEEP | etymonline confirms Hormel 1937, Monty Python 1970, digital sense "after March 31, 1993" — exact match | none |
| stream | KEEP | etymonline/OED: water → media streaming; YouTube/Netflix/Spotify trigger sound | none |
| sus | FIX | MW dates the clipped "suspicious" sense to **1955** (not 1936) and does NOT attribute the surge to Among Us; the Among Us 2020 link is on Wikipedia (general source) only | clipping firstAttested 1936→1955; evidenceType LexicographicNote→Speculative; confidence 0.8→0.6; added Wikipedia source; comment corrected |
| thermos | KEEP | Wiktionary/Wikipedia: Thermos brand 1904, ruled generic US 1963; broadening sound | none |
| turkey | KEEP | etymonline/Wiktionary: guinea fowl via Turkish merchants → New World bird; metonymization sound | none |
| vandalismus | KEEP | etymonline/Wikipedia: Grégoire coined "vandalisme" 1794; ScholarlyAttestation sound | none |
| wahnsinn | KEEP | DWDS confirms positive exclamatory sense (3a) "toll/fantastisch"; no date given but file already Speculative 0.55 with "anchor year not a cause" caveat | none |
| woke | FIX | etymonline gives almost nothing (only a parenthetical noting the 2010s political sense as "an exception", no date, no BLM/culture-war link); senses real via OED/Wikipedia but triggers are curator inference, not lexicographically attested | hyp-blm: added Speculative, confidence 0.85→0.6; hyp-culturewars: LexicographicNote→Speculative-only, 0.8→0.6; comments corrected |
| zeppelin | KEEP | DWDS/Wikipedia: Graf von Zeppelin, LZ 1 first flight 2 July 1900; metonymization sound | none |

## Counts

- KEEP: 30
- FIX: 8 (backfisch, brutal, gaslighting, ghosting, luegenpresse, querdenker, sus, woke)
- REMOVE: 0

## Removed list

None. Every entry's core sense-shift was attestable from an authority; the
problems were over-precise/invented dates, overstated evidence types, dead/wrong
source URLs, and one false "the dictionary attributes X" claim — all fixable
without deleting an entry.

## Notable corrections (folk-etymology / invented-date scrutiny)

- **sus**: invented firstAttested 1936 (MW says 1955) + false claim that MW
  attributes the surge to Among Us. Down to Speculative 0.6.
- **brutal**: invented "admiring intensifier" sense (folk; not in etymonline or
  MW) + wrong firstAttested 1640 (etymonline: mid-15c). Tightened to the
  attested "harsh/unpleasant" weakening.
- **woke**: flagship word; etymonline barely substantiates and does not connect
  BLM/culture-war triggers. Both causal hypotheses downgraded to Speculative 0.6.
- **backfisch**: figurative sense is mid-16c student slang per DWDS, not an 1850
  coinage; firstAttested and drift interval widened, trigger reframed.

## Validation

- `python validate.py` → All checks passed.
- `python scripts/lint-data.py --quiet` → 212 files, 0 problem(s).
- No em-dashes introduced; gYears 4-digit zero-padded; SHACL-valid
  (Speculative-only hypotheses kept confidence < 0.66).
