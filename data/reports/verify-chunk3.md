# Verify chunk 3 report

Strict fact-check of 39 example files against cited sources (per `docs/verify-criteria.md`).
Lean-toward-FIX policy applied; no invented dates or sources introduced.

| word | verdict | what the sources did / didn't support | action taken |
|------|---------|----------------------------------------|--------------|
| arbeit | KEEP | DWDS/wissen.de attest OHG "toil" -> NHG "work"; Protestant-ethic trigger is a contested (Speculative, 0.5) hypothesis, already flagged as such. Dates within OHG/early-modern ranges. | none |
| awful | KEEP | etymonline confirms exactly: "worthy of respect/awe" c.1300; weakened "very bad" by 1809. Matches firstAttested 1300/1809. | none |
| based | KEEP (FIX detail) | Dictionary.com: parent slang "basehead" is a 1980s freebasing term; Lil B redefined "based" (Based Boys 2007, Complex interview 2010). Reappropriation + Lil B trigger verified. The 1980 was for the slur sense with no standalone "based" attestation. | Kept 1980 as the sourced 1980s decade-origin of "basehead"; clarified gloss + added comment that 1980 marks the basehead origin, not a precise "based"-slur attestation. Lil B / 2010 / confidence 0.7 left as supported. |
| blase-de | KEEP | DWDS/Duden attest air-bubble -> economic bubble; South Sea Bubble link already dual-flagged LexicographicNote+Speculative (0.7). Cross-lingual trigger node defined in bubble.ttl. | none |
| braille | KEEP | etymonline + Wikipedia confirm Louis Braille devised the raised-dot system (1824, pub. 1829); name became the system. | none |
| chauvinismus | KEEP | DWDS + Wikipedia confirm Nicolas Chauvin / Cogniard 1831 play -> "chauvinisme" 1843 -> German Chauvinismus. | none |
| cringe | FIX | M-W dates the slang adjective to **1983**, not 2015. Sense shift (verb -> predicative adj/noun) verified, but meme culture (2010s) cannot be the coining trigger 30 years later. | firstAttested 2015 -> 1983; drift widened to 1983-2015 interval; trigger reframed as a 2010s spreader (eventDate 2011 = r/cringe founding); evidence LexicographicNote -> Speculative; confidence 0.65 -> 0.45. |
| diesel | KEEP | DWDS + Wikipedia confirm Rudolf Diesel, 1892 patent / 1893 engine; surname -> engine/fuel. | none |
| egregious | KEEP | etymonline confirms positive "distinguished" 1530s, ironic negative "flagrant" late 16c. 1534/1573 sit within those ranges; OED also cited; confidence 0.62. | none |
| fascism | KEEP | etymonline + Wikipedia confirm Mussolini's Fasci (1919) / March on Rome (1922); broadening to far-right authoritarianism. | none |
| fromm | KEEP | DWDS + DiVA scholarly study attest OHG "useful/capable" -> NHG "pious"; Luther's Bible as trigger (LexicographicNote+ScholarlyAttestation, 0.8). | none |
| gargantuan | KEEP | etymonline confirms Rabelais's giant Gargantua (1534) -> adjective "enormous" 1590s. | none |
| gerrymander | KEEP | etymonline confirms 1812 Gov. Elbridge Gerry + salamander blend, Massachusetts redistricting. | none |
| gruen-de | KEEP | DWDS/Duden attest colour -> ecological/political sense; ecology-movement trigger shared with green.ttl; Die Gruenen 1980. | none |
| herculean | KEEP | etymonline + Wikipedia: Hercules / Twelve Labours -> "requiring great strength/effort"; standard eponym. | none |
| influencer | FIX (minor) | M-W gives first use **1662** (entry had 1660); social-media sense undated in M-W but supported by Ngram frequency climb (FrequencyCorrelation in-entry). Trigger (Instagram/creator economy) sound. | firstAttested 1660 -> 1662 to match M-W. Rest unchanged. |
| kamikaze | KEEP | etymonline + Wiktionary: WWII suicide attacks (Leyte Gulf 1944) -> figurative "recklessly self-destructive". | none |
| klimakleber | KEEP | Wiktionary + Tagesspiegel attest 2022 Bild coinage as pejorative for Letzte Generation, partial reappropriation, Duden entry. Dates 2022/2023 verified. | none |
| lesbian | KEEP | etymonline + Wiktionary: Lesbos/Sappho -> female same-sex sense (19c). | none |
| luddite | KEEP | etymonline + Wikipedia: 1811-1816 machine-breaking movement (Ned Ludd) -> "opponent of technology". | none |
| marathon | KEEP | etymonline + Wiktionary: plain of Marathon / 1896 Olympic race -> long-distance race + prolonged effort. | none |
| mentor | KEEP | etymonline + Wikipedia: Homeric Mentor, expanded by Fenelon's Telemaque (1699) -> "trusted adviser" (ScholarlyAttestation, 0.8). | none |
| narcissism | KEEP | etymonline confirms exactly: myth of Narcissus; Ellis 1898 / Naecke 1899 coinage; English by 1905. Matches 1898/1905 + trigger 1899. | none |
| nicotine | KEEP | etymonline + Wikipedia: Jean Nicot / Nicotiana -> alkaloid; standard eponym chain. | none |
| orwellian | KEEP | etymonline + Wikipedia: Nineteen Eighty-Four (1949) -> "oppressive state control". | none |
| philister | KEEP | DWDS + Wiktionary attest Biblical ethnonym -> German student-slang pejorative (late 17c, 1693 Jena sermon cited); confidence 0.75. | none |
| queer | KEEP | OED + Wikipedia: "strange" 1513 -> slur 1894 -> 1990s reappropriation (Queer Nation 1990); worked example, dual-flagged. | none |
| roentgen | KEEP | DWDS + Wikipedia: W.C. Roentgen, 8 Nov 1895 X-ray discovery -> rays/imaging/verb. | none |
| saxophone | KEEP | etymonline + Wikipedia: Adolphe Sax, 1846 patent -> instrument. (1814 = Sax's birth, the name's origin, acceptable.) | none |
| sick | FIX | M-W confirms slang sense "outstandingly good"; etymonline does NOT give a positive-slang date. firstAttested 1983 was unsourced; entry already honestly Speculative (0.55) with "no single datable event" trigger. | firstAttested 1983 -> 1980 (defensible decade, matches drift interval start); trigger eventDate 1983 -> 1980; "representative attestation" -> "representative decade". Confidence/evidence left (already Speculative/0.55). |
| spa | KEEP | etymonline + Wiktionary: Belgian town Spa -> mineral-spring resort -> health establishment. | none |
| stan | KEEP | M-W confirms etymology from Eminem's 2000 song "Stan"; noun first use 2000, verb 2008. Matches entry (fan sense 2008, trigger 2000). | none |
| surfen-de | KEEP | DWDS/Duden attest sport -> internet sense; WWW/Mosaic 1993, Polly 1992 phrase; dates 1975/1994 plausible, confidence 0.88. | none |
| terrific | KEEP | etymonline confirms exactly: "frightful" 1660s (Milton); inverted colloquial "excellent" 1888. Matches 1660/1888. | none |
| trommelfeuer | KEEP | DWDS + Wiktionary attest WWI artillery term -> figurative "relentless barrage"; Verdun/Somme 1916 trigger; confidence 0.7. | none |
| unfriend | FIX | OED citation + Wiktionary date the archaic verb to **1659** (Fuller), noun 1822 - NOT 1275. Modern Facebook sense ~2007-2008, NOAD Word of the Year 2009 (verified via multiple outlets). The cited OUP blog URL redirected to a dead landing page. | archaic firstAttested 1275 -> 1659 (OED/Wiktionary); fixed dead OUP URL to working `?onwardjourney` variant. Trigger/2009-WOTY left as supported. |
| volt | KEEP | etymonline + Wikipedia: Alessandro Volta, 1800 voltaic pile -> SI unit; adopted internationally 1880s. | none |
| wende | KEEP | DWDS + Wikipedia: general "turning point" -> die Wende 1989/90 (Mauerfall); DWDS frequency spike 1990 supports FrequencyCorrelation; confidence 0.95. | none |
| yahoo | KEEP | etymonline + Wikipedia: Swift's Yahoos (Gulliver's Travels, 1726) -> "loutish person". | none |

## Counts

- KEEP: 35
- FIX: 4 (cringe, influencer, sick, unfriend)
- REMOVE: 0

(based counted as KEEP with a clarifying detail fix; not a date change.)

## Removed list

None. Every assigned entry has a verifiable core sense-shift and an attestable trigger; the four problem entries had unsupported/over-precise dates or one dead URL, all fixable down to what the sources support without inventing anything.

## Notes / key findings

- The user-flagged `based` 1980 slur date: the cited Dictionary.com source does support "basehead" as a 1980s term (the parent of "based"), so 1980 is defensible as a decade-origin marker; kept with a clarifying comment and gloss. Lil B reappropriation (2007-2010) and the moderate 0.7 confidence are well sourced.
- `cringe` was the most over-claimed entry in this chunk: the slang adjective is M-W-dated to 1983, three decades before the meme-culture trigger the entry proposed. Downgraded to Speculative / 0.45 and reframed meme culture as a spreader, not the origin.
- `unfriend` had the most clearly invented date (1275) with no source support anywhere; corrected to the 1659 OED/Wiktionary attestation.
- The large historical/eponym set (volt, diesel, roentgen, saxophone, gerrymander, marathon, narcissism, terrific, awful, etc.) verified cleanly against etymonline / OED / DWDS with dates matching to the year.

Validation after edits: `python validate.py` -> All checks passed. `lint-data.py` -> 212 files, 0 problems.
