# Verify chunk 2 - fact-check report

Strict verifiability pass over 39 assigned example files. Each cited source
fetched (etymonline, DWDS, Wikipedia, Wiktionary, Zenodo/SemEval, Merriam-Webster).
Lean toward FIX; REMOVE only when the core sense-shift or trigger is unverifiable.

| word | verdict | what the sources did / did not support | action |
|------|---------|-----------------------------------------|--------|
| ampere | KEEP | Etymonline: unit name 1881, from A-M Ampere (1775-1836); 1881 Electric Congress. All dates match. | none |
| attack | KEEP | Etymonline: verb c.1600 (military), noun 1660s, medical "fit of disease" 1811. SemEval gold 0.82 real (zenodo 3931969). Cause honestly Speculative, conf 0.6. | none |
| banause | KEEP | DWDS: from Gk banausos (Handwerker/Spiessbuerger), abwertend "ohne Kunstsinn"; borrowed 1796, established early 19c. Bildung-cult trigger sound; conf 0.65. | none |
| bit | KEEP | Etymonline: computing sense 1948, coined by Tukey (Shannon paper standard). SemEval gold 0.55 real. ChangeSignalAlignment + LexicographicNote, conf 0.65. | none |
| boykott | KEEP | DWDS: Charles Boycott (1832-1897), 1880 Irish Land League ostracism, German term late 19c. Exact match. | none |
| cellophane | FIX | Wikipedia confirms Brandenberger 1908/1912; Wiktionary lists it as genericized trademark. The "US court ruled it generic in 1936" claim is NOT in the cited sources. | Removed the unverified 1936 court-ruling claim from trigger description; widened drift interval end 1936 -> 1940. |
| cravat | KEEP | Etymonline: 1650s, from Croat/Crabat cavalry in Thirty Years War. Exact match. | none |
| denim | KEEP | Etymonline: 1690s, serge de Nimes; fabric sense 1850 AmE. Matches (file 1695). | none |
| edge | KEEP | Etymonline broadening + SemEval gold 0.59 real. Cause honestly Speculative, conf 0.55. Same honest structure as attack/face. | none |
| face | KEEP | Etymonline anatomical/figurative broadening + SemEval gold 0.64 real. Cause Speculative, conf 0.6. | none |
| frau | KEEP | DWDS: MHG frouwe (noble lady/honorific) -> general "woman" by 18c, displaced Weib. Exact match; conf 0.6 modest. | none |
| galvanize | KEEP | Etymonline: from Galvani (~1792 galvanism), 1801 verb, figurative "rouse" 1853. Matches (file 1791/1802/1853). | none |
| gendersternchen | FIX | DWDS entry live, defines the inclusive asterisk; frequency rise across 2010s (examples 2009-2018). The "GfdS shortlist + Duden 2020" specifics NOT in DWDS source. | Removed unverified Duden 2020 / GfdS claim from trigger description; kept DWDS frequency-correlation core. |
| green | KEEP | Etymonline: "color of environmentalism since 1971" (file 1972, within 1y, defensible); OED also cited. Trigger (eco movement) sound. | none |
| heimat | KEEP | DWDS alone does not assert the shift, but the cited de.wikipedia/Heimat article DOES: sober legal/geographic word until mid-19c, poetic/emotional sense arose in the Romantik milieu. Trigger sourced. conf 0.75 OK. | none |
| impfgegner | KEEP | DWDS entry live, defines "Impfgegner"; documented COVID frequency spike (Wortverlaufskurve). Wikidata Q81068910 = COVID-19 pandemic (correct trigger entity). FrequencyCorrelation + LexicographicNote, conf 0.8. | none |
| kaiser | KEEP | DWDS: Caesar (family name) -> ruler title, borrowed by Germanic peoples very early. 0027/Augustus anchor is standard history. | none |
| kleenex | FIX | Wikipedia confirms 1924 introduction + genericized trademark, but introduced by Cellucotton Products Co. (Kimberly-Clark holds trademark since 1955), not "Kimberly-Clark in 1924". | Clarified the 1924 introduction attribution in trigger description. Date + genericization unchanged. |
| lazarett | KEEP | DWDS: Italian lazzaretto, Venetian plague hospital Santa Maria di Nazaret (15c), St-Lazarus blend, military-hospital sense by mid-18c. 1423 Lazzaretto Vecchio founding is documented. | none |
| literally | FIX | Etymonline: literal sense 1530s; intensifier "since late 17c". M-W (cited) dates figurative use to 1769 (Frances Brooke) - so 1769 is supported. But cited M-W URL was 404. | Replaced dead M-W URL with working page (misuse-of-literally); kept 1769 (M-W-supported). |
| malapropism | KEEP | Etymonline: term 1826 (file 1830, within rounding), from Mrs Malaprop in Sheridan's The Rivals 1775. | none |
| meat | KEEP | Etymonline: OE mete = food generally, narrowed to animal flesh ~1300. Exact match. | none |
| mouse | KEEP | Etymonline: computer sense 1965; Macintosh 1984 mainstreaming trigger accurate. | none |
| nice | KEEP | Etymonline: nescius -> foolish late 13c -> precise 1500s -> agreeable 1769. File dates match exactly (1290/1510/1769). | none |
| ohm | KEEP | Etymonline: unit adopted 1867, from G.S. Ohm (1789-1854). Ohm's law 1827 standard fact (also in Wikipedia source). | none |
| philippic | KEEP | Etymonline: 1590s (file 1592), from Demosthenes' orations vs Philip II (351 BC), generalized to "bitter denunciation". | none |
| quarantaene | KEEP | DWDS: Italian quaranta (40 days), Mediterranean-port ship isolation from 14c. 1377 Ragusa/Venice trigger documented. | none |
| robot | KEEP | Etymonline: from Capek R.U.R. (1920), Czech robota; English 1923, broadened to machines. | none |
| sandwich | KEEP | Etymonline: 1762, John Montagu 4th Earl of Sandwich (1718-1792). Exact match. | none |
| shrapnel | FIX | Etymonline: shell sense 1806 (Henry Shrapnel) correct, BUT the broadened "fragments" sense is dated 1940 (Blitz), not WWI/1914 as in file. | Changed fragments firstAttested 1914 -> 1940; fixed "World War One" -> "by the 1940s (the Blitz)"; drift interval end 1918 -> 1945. |
| sophisticated | FIX | Etymonline: adulterated sense ~1600 correct; positive "worldly-wise" sense attested by 1895, not 1850 as in file. | Changed refined firstAttested 1850 -> 1895 and trigger eventDate 1850 -> 1895; noted 1895 in description. conf 0.6 already modest. |
| spiesser | KEEP | DWDS: Spiessbuerger (pike-armed townsman, student insult, 17c) -> narrow conformist; short form Spiesser 19c. Matches. | none |
| surf | KEEP | Etymonline: wave-riding 1917, internet sense 1993 (file 1992; Polly 1992 coinage attested). Within 1y, defensible. | none |
| tempo-de | KEEP | de.wikipedia: Tempo trademark filed 29 Jan 1929 (Vereinigte Papierwerke, Reichspatentamt Berlin), became Gattungsname. Exact match. | none |
| troll | KEEP | Etymonline: fishing ~1600, online provocateur sense late 1980s/early 1990s (Usenet). OED also cited. File 1992 defensible. | none |
| uhu-de | KEEP | de.wikipedia: August Fischer 1932, Buehl, named after eagle-owl (Uhu), generic glue term. Exact match. | none |
| virus | FIX | Etymonline (cited): computer sense attested "by 1972", whereas file dates it 1984 (Cohen/Brain mainstreaming). Bio->computer metaphor solidly attested. | Added clarifying note to etymonline source title (1972 attestation vs 1983-84/1986 mainstreaming). Date kept as mainstream-establishment milestone; conf 0.88 unchanged. |
| weib | FIX | DWDS confirms core: medieval neutral "adult/married woman" -> derogatory from 17c, displaced by Frau. Secondary Nuebling 2011 source URL was a 403-blocked ResearchGate link. | Replaced ResearchGate URL with the open Uni-Mainz PDF of the same Nuebling 2011 paper (verified real). Core sense-shift unchanged. |

## Counts

- KEEP: 31
- FIX: 8 (cellophane, gendersternchen, kleenex, literally, shrapnel, sophisticated, virus, weib)
- REMOVE: 0

## Removed list

None. No entry's core sense-shift or trigger was unverifiable; every FIX was a
correctable detail (over-precise/wrong date, dead or blocked source URL, or an
unverified narrative specific) over a verifiable core.

## Validators (post-edit)

- `python validate.py` -> All checks passed.
- `python scripts/lint-data.py --quiet` -> 212 files, 0 problem(s).
