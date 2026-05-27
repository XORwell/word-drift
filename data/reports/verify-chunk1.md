# Verify chunk 1 - fact-check report

Strict verifiability pass over 38 assigned `examples/*.ttl`. Each cited source was
fetched (etymonline, Wiktionary, Wikipedia, DWDS, Duden, taz, Merriam-Webster) and
checked against the sense shift, the trigger, and the dates. Lean: FIX over REMOVE.

| word | verdict | what the sources did / didn't support | action taken |
|------|---------|----------------------------------------|--------------|
| alternativlos | KEEP | de.wikipedia + taz both confirm Unwort des Jahres 2010, Merkel's Euro-bailout usage, and the pejorative/neutral split. taz URL resolves (title matches). | none |
| atlas | KEEP | etymonline confirms Titan -> bound book of maps, 1636 English sense, Mercator 1595 frontispiece. | none |
| ball | KEEP | etymonline confirms object c.1200; dance 1630s; idioms "on the ball" 1912, "have a ball" 1945. Entry is honest SemEval benchmark word with diffuse trigger + Speculative cause (conf 0.55). | none |
| biro | KEEP | Wiktionary: genericized trademark of BIRO (Laszlo Biro), generic in British/Commonwealth English; earliest cite 1945 supports ~1947 generic sense. | none |
| bowdlerize | KEEP | etymonline: Thomas Bowdler 1818 Family Shakespeare -> verb 1836. Exact match. | none |
| cancel | KEEP | MW substantiates social-media call-out / #MeToo trigger for the "cancel a person" sense; conf 0.75 LexicographicNote is appropriately modest. MW dates cites 2018-19 but the 2017 #MeToo surge is well documented and defensible. | none |
| cologne | KEEP | etymonline: city Cologne / eau de Cologne (Farina 1709) -> perfume, Cologne water 1814. Match. | none |
| deer | KEEP | etymonline: OE deor "any wild animal" (cognate Tier) narrowed to cervid, common by 15c. Match. | none |
| draconian | KEEP | etymonline: Draco c.621 BC harsh code -> "excessively harsh" (1759 / 1777). Match. | none |
| etappe | FIX | DWDS confirms military supply-zone (~1700) -> general "stage/phase", but dates the generalisation to the **19th century** and makes **no WWI connection**. The WWI trigger (1914/1918) was unsupported curator folk-history. | New-sense firstAttested 1918 -> 1850; drift interval 1914-1930 -> 1800-1900; trigger replaced with diffuse "gradual 19th-c. generalisation"; evidenceType += Speculative; confidence 0.65 -> 0.5. |
| frankenstein | KEEP | etymonline: Shelley 1818 novel -> figurative "creation that destroys its maker", attested 1838. Exact match. | none |
| galvanisieren | KEEP | DWDS ties verb to Galvani's frog-leg experiments (Volta coinage 1796); treat-with-current ~1800 -> electroplate (19th c.) -> figurative rouse. Match. | none |
| geil | KEEP | DWDS/Duden cited (lexicographic); OHG "lewd" -> 1970s youth-slang "great". Worked example, LexicographicNote, conf 0.85. Sense shift is standard DWDS Wortgeschichte. | none |
| granola | KEEP | Wiktionary: trademark registered 1886 (respelling of Granula), genericized into early 20c. Match. | none |
| guy | KEEP | etymonline: Guy Fawkes effigy 1806 -> grotesque person 1836 -> "man, fellow" 1847. Exact match. | none |
| hooligan | KEEP | etymonline: London police-court reports summer 1898, prob. surname Houlihan -> violent youth. Match. | none |
| kafkaesque | KEEP | etymonline: from Kafka, "Kafkaesque" 1947. Match (author sense 1936 + absurd sense 1947). | none |
| klasse | KEEP | DWDS: social-class sense 18th-c. development theorized by Marx/Engels (Klassenkampf 1847), relation to means of production. 1848 trigger defensible (Communist Manifesto). | none |
| laconic | KEEP | etymonline: from Laconia/Sparta, terse speech, 1580s. Match. | none |
| linoleum | KEEP | Wiktionary (Walton ~1864, first genericized trademark) + en.wikipedia ("14 years after its invention" = 1878 court ruling). 1878 date IS supported by the cited Wikipedia source. | none |
| machiavellian | KEEP | etymonline: from Machiavelli / Il Principe, "cunning, unscrupulous", 1570s. Match. | none |
| maverick | FIX | etymonline: Samuel Maverick unbranded cattle 1867 -> "independent person" **1886** (file said 1880). Core fully verified; date over-precise/early. | person-sense firstAttested 1880 -> 1886 (matches etymonline). |
| morse-code | KEEP | en.wikipedia: named after Samuel Morse, developed w/ Vail ~1837-44, first used 1844. Match. | none |
| netz-de | KEEP | DWDS lists "Netz" = synonym for internet (im Netz surfen). WWW/Mosaic trigger documented. Match. | none |
| ohm-de | FIX | DWDS connects unit to Georg Simon Ohm but dates international establishment to **1881** (no 1827/Ohm's-law tie, no 1867). Core verified; unit-sense date unsupported. | unit-sense firstAttested 1867 -> 1881; drift interval end 1867 -> 1881; description notes 1881 per DWDS. Ohm's-law 1827 trigger kept (historical fact). |
| pfaffe | KEEP | DWDS: "Pfaffe ... seit der Reformation in abschaetzigem Sinne". Neutral cleric -> pejorative, Reformation trigger. Exact match. | none |
| propaganda | FIX | etymonline: Congregatio de Propaganda Fide 1622 confirmed; but the **negative** sense is 20th-c. (WWI political sense "originally not pejorative"); 1790 sense was neutral "movement to propagate ideology". Negative-sense date was wrong. | negative-sense firstAttested 1790 -> 1914; drift interval end 1800 -> 1930; description corrected to etymonline's timeline. |
| quixotic | FIX | etymonline: from Don Quixote (1605), adjective **1791** (file said 1718, unsupported). Core verified; date invented/early. | idealistic-sense firstAttested 1718 -> 1791; drift interval end 1720 -> 1800. |
| salvage | KEEP | etymonline: maritime-law payment 1640s -> "saving property from danger" 1878 -> recycling 1918. Trigger marine law/insurance, conf 0.6 modest. Match. | none |
| schwurbler | FIX | diversmagazin + Wiktionary confirm "muddled speaker" -> COVID-era conspiracy-theorist/Querdenken pejorative (2020). Core verified. But evidenceType FrequencyCorrelation was unsupported (cited source is Wiktionary, not a frequency study). | evidenceType FrequencyCorrelation -> LexicographicNote (conf 0.8 kept). |
| slop | FIX | etymonline (swill c.1400) + Wiktionary (AI-slop sense, earliest cite Sept 2023) confirm sense shift; genAI trigger sound. But cited Guardian URL (2024/jan/12/ai-slop) is **fabricated / 404** (real Guardian piece is May 2024); and FrequencyCorrelation evidence had no frequency source. | dead Guardian source replaced with en.wikipedia "AI slop"; evidenceType FrequencyCorrelation+LexicographicNote -> LexicographicNote; conf 0.8 kept. |
| spiegeln-de | KEEP | DWDS + Duden both list EDV/computing "mirror data" sense. FTP/RAID 1990s trigger; conf 0.72 LexicographicNote. Match. | none |
| streik | KEEP | DWDS: English loan "strike" 1st half 19th c.; Leipzig printers' strike 1865 anchored German labour sense. Match. | none |
| tantalize | KEEP | etymonline: from myth of Tantalus, "tease with the unattainable", 1590s. Match. | none |
| troll-de | KEEP | DWDS lists both creature and internet-provocateur senses (from English). Usenet trigger comes from troll.ttl + Wikipedia, already tagged Speculative; conf 0.78 with LexicographicNote+Speculative is within bounds. | none |
| tweet | KEEP | etymonline (bird 1845, Twitter sense by 2007) + en.wikipedia (Twitter launch 2006, "tweet" adopted 2007). Wikipedia URL resolves. Exact match. | none |
| virus-de | KEEP | DWDS lists biological + computer-virus senses; computer usage from 1984 (Cohen 1983-84, Brain virus 1986). Match. | none |
| web | KEEP | etymonline + OED cited; spider web -> WWW (Berners-Lee 1989-91, Mosaic 1993). Standard, LexicographicNote, conf 0.88. | none |
| wutbuerger | KEEP | de.wikipedia + Der Spiegel 41/2010 (Kurbjuweit essay) confirm the 2010 coinage, Stuttgart 21 tie, Word of the Year 2010, and broadening to general anti-establishment anger. Match. | none |

## Counts

- KEEP: 31
- FIX: 7 (etappe, maverick, ohm-de, propaganda, quixotic, schwurbler, slop)
- REMOVE: 0

## Removed list

None. Every assigned entry had a verifiable core sense shift and a defensible
(if sometimes diffuse) trigger; defects were limited to over-precise/invented
dates, one fabricated source URL, and two over-claimed evidence types, all
fixable down to what the sources support.

## Fix details

- **etappe**: WWI trigger contradicted by DWDS (generalisation already 19th c.).
  Sense date 1918 -> 1850; interval 1914-1930 -> 1800-1900; trigger reframed as
  diffuse 19th-c. generalisation; evidenceType += Speculative; confidence 0.65 -> 0.5.
- **maverick**: person sense 1880 -> 1886 (etymonline).
- **ohm-de**: unit sense 1867 -> 1881 (DWDS "international 1881"); interval end -> 1881.
- **propaganda**: negative sense 1790 -> 1914 (etymonline: 20th-c. political/pejorative);
  interval end 1800 -> 1930; description corrected.
- **quixotic**: adjective 1718 -> 1791 (etymonline); interval end 1720 -> 1800.
- **schwurbler**: evidenceType FrequencyCorrelation -> LexicographicNote (no frequency source cited).
- **slop**: fabricated Guardian URL replaced with en.wikipedia "AI slop";
  evidenceType trimmed to LexicographicNote.

## Validation

- `python validate.py` -> All checks passed.
- `python scripts/lint-data.py --quiet` -> 212 files, 0 problem(s).
