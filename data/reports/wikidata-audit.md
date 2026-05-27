# Wikidata trigger-link audit

Audit of every `owl:sameAs` link from a `drift:TriggerEvent` to a Wikidata Q-item. Each QID was verified against the live entity (`wbgetentities`, P31 instance-of) and classified.

- **Total links audited:** 121 (105 distinct QIDs)
- **OK:** 121
- **BAD (removed):** 0 (dry run, not yet removed)
- **SUSPECT (flagged for human review):** 0

## Full audit table

| Trigger | Cat | QID | Entity label | P31 | Verdict |
|---|---|---|---|---|---|
| `trigger-akademie-plato` | Cultural | [Q859](https://www.wikidata.org/wiki/Q859) | Plato | Q5 | OK |
| `trigger-ampere-electrodynamics` | Technology | [Q675](https://www.wikidata.org/wiki/Q675) | André-Marie Ampère | Q5 | OK |
| `trigger-apple-macintosh` | Technology | [Q1137478](https://www.wikidata.org/wiki/Q1137478) | Macintosh 128K | Q55990535 | OK |
| `trigger-arbeit-protestant` | Cultural | [Q12562](https://www.wikidata.org/wiki/Q12562) | Protestant Reformation | Q1128340, Q126288065 | OK |
| `trigger-aspirin-bayer` | Commercial | [Q152051](https://www.wikidata.org/wiki/Q152051) | Bayer | Q4830453, Q6881511, Q891723 | OK |
| `trigger-atlas-mercator` | Cultural | [Q6353](https://www.wikidata.org/wiki/Q6353) | Gerardus Mercator | Q5 | OK |
| `trigger-aws-launch` | Technology | [Q456157](https://www.wikidata.org/wiki/Q456157) | Amazon Web Services | Q241317, Q1210425, Q1153767 | OK |
| `trigger-bakelite-baekeland` | Commercial | [Q243442](https://www.wikidata.org/wiki/Q243442) | Leo Baekeland | Q5 | OK |
| `trigger-bikini-tests` | Cultural | [Q569545](https://www.wikidata.org/wiki/Q569545) | Operation Crossroads | Q98391050 | OK |
| `trigger-biro-patent` | Commercial | [Q312680](https://www.wikidata.org/wiki/Q312680) | László Bíró | Q5 | OK |
| `trigger-blitz-london` | Political | [Q6900329](https://www.wikidata.org/wiki/Q6900329) | the Blitz | Q4688003 | OK |
| `trigger-blm-movement` | Political | [Q19600530](https://www.wikidata.org/wiki/Q19600530) | Black Lives Matter | Q49773, Q123531451 | OK |
| `trigger-bowdlerize-shakespeare` | Cultural | [Q1333546](https://www.wikidata.org/wiki/Q1333546) | Thomas Bowdler | Q5 | OK |
| `trigger-boykott-landleague` | Political | [Q455534](https://www.wikidata.org/wiki/Q455534) | Charles Boycott | Q5 | OK |
| `trigger-braille-system` | Technology | [Q93182](https://www.wikidata.org/wiki/Q93182) | Louis Braille | Q5 | OK |
| `trigger-cellophane-brand` | Commercial | [Q117187](https://www.wikidata.org/wiki/Q117187) | Jacques E. Brandenberger | Q5 | OK |
| `trigger-chauvinismus-play` | Cultural | [Q1798716](https://www.wikidata.org/wiki/Q1798716) | La Cocarde tricolore | Q7725634 | OK |
| `trigger-cologne-eau` | Commercial | [Q365](https://www.wikidata.org/wiki/Q365) | Cologne | Q707813, Q200250, Q2202509 | OK |
| `trigger-computer-virus` | Technology | [Q14001](https://www.wikidata.org/wiki/Q14001) | malware | Q17155032 | OK |
| `trigger-covid` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-currant-corinth` | Commercial | [Q103011](https://www.wikidata.org/wiki/Q103011) | Corinth | Q515 | OK |
| `trigger-damast-damaskus` | Commercial | [Q3766](https://www.wikidata.org/wiki/Q3766) | Damascus | Q515, Q1549591, Q16127605 | OK |
| `trigger-denim-nimes` | Commercial | [Q42807](https://www.wikidata.org/wiki/Q42807) | Nîmes | Q484170, Q1549591 | OK |
| `trigger-diesel-patent` | Technology | [Q12674](https://www.wikidata.org/wiki/Q12674) | Rudolf Diesel | Q5 | OK |
| `trigger-doomscrolling-covid` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-escalator-otis` | Commercial | [Q1134069](https://www.wikidata.org/wiki/Q1134069) | Otis Worldwide Corporation | Q4830453, Q891723 | OK |
| `trigger-facebook-like` | Technology | [Q355](https://www.wikidata.org/wiki/Q355) |  | Q3220391, Q35127, Q620615 | OK |
| `trigger-fascism-mussolini` | Political | [Q468823](https://www.wikidata.org/wiki/Q468823) | March on Rome | Q45382, Q15631336, Q657449 | OK |
| `trigger-filterblase-pariser` | Media | [Q111687183](https://www.wikidata.org/wiki/Q111687183) | The Filter Bubble: How the New Personalized Web Is Changing What We Read and How We Think | Q3331189 | OK |
| `trigger-frankenstein-shelley` | Cultural | [Q150827](https://www.wikidata.org/wiki/Q150827) | Frankenstein; or, The Modern Prometheus | Q7725634 | OK |
| `trigger-fromm-luther` | Cultural | [Q1571095](https://www.wikidata.org/wiki/Q1571095) | Luther Bible | Q3331189 | OK |
| `trigger-front-wwi` | Political | [Q361](https://www.wikidata.org/wiki/Q361) | World War I | Q103495, Q11514315 | OK |
| `trigger-funk-genre` | Cultural | [Q164444](https://www.wikidata.org/wiki/Q164444) | funk | Q188451 | OK |
| `trigger-galvanisieren-frogleg` | Technology | [Q1589](https://www.wikidata.org/wiki/Q1589) | Luigi Galvani | Q5 | OK |
| `trigger-galvanize-frogleg` | Technology | [Q1589](https://www.wikidata.org/wiki/Q1589) | Luigi Galvani | Q5 | OK |
| `trigger-gargantuan-rabelais` | Cultural | [Q822290](https://www.wikidata.org/wiki/Q822290) | Gargantua and Pantagruel | Q1667921, Q17710986 | OK |
| `trigger-gerrymander-redistricting` | Political | [Q1325397](https://www.wikidata.org/wiki/Q1325397) | Elbridge Gerry | Q5 | OK |
| `trigger-gfds-trigger-boostern-2021` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-gfds-trigger-bundeskanzlerin-2005` | Political | [Q567](https://www.wikidata.org/wiki/Q567) | Angela Merkel | Q5 | OK |
| `trigger-gfds-trigger-corona-pandemie-2020` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-gfds-trigger-der-11-september-2001` | Political | [Q40231](https://www.wikidata.org/wiki/Q40231) | public election | Q3249551 | OK |
| `trigger-gfds-trigger-kollateralschaden-1999` | Political | [Q46083](https://www.wikidata.org/wiki/Q46083) | Franco-Prussian War | Q198 | OK |
| `trigger-gfds-trigger-lockdown-2020` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-gfds-trigger-wellenbrecher-2021` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-gfds-trigger-wutburger-2010` | Political | [Q574459](https://www.wikidata.org/wiki/Q574459) | Ausleben | Q116457956 | OK |
| `trigger-guillotine-revolution` | Political | [Q220650](https://www.wikidata.org/wiki/Q220650) | Joseph-Ignace Guillotin | Q5 | OK |
| `trigger-guy-gunpowder` | Political | [Q13898](https://www.wikidata.org/wiki/Q13898) | Guy Fawkes | Q5 | OK |
| `trigger-hertz-waves` | Technology | [Q41257](https://www.wikidata.org/wiki/Q41257) | Heinrich Hertz | Q5 | OK |
| `trigger-impfgegner-covid` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-influencer-instagram` | Commercial | [Q209330](https://www.wikidata.org/wiki/Q209330) |  | Q3220391, Q35127, Q2721136 | OK |
| `trigger-jeans-genoa` | Commercial | [Q1449](https://www.wikidata.org/wiki/Q1449) | Genoa | Q747074, Q1549591, Q2264924 | OK |
| `trigger-kafkaesque-prozess` | Cultural | [Q905](https://www.wikidata.org/wiki/Q905) | Franz Kafka | Q5 | OK |
| `trigger-kaiser-augustus` | Political | [Q1405](https://www.wikidata.org/wiki/Q1405) | Augustus | Q5 | OK |
| `trigger-kamikaze-leyte` | Political | [Q308999](https://www.wikidata.org/wiki/Q308999) | Battle of Leyte Gulf | Q1261499, Q830494 | OK |
| `trigger-ketzer-albigensian` | Cultural | [Q51657](https://www.wikidata.org/wiki/Q51657) | Albigensian Crusade | Q1827102, Q831663 | OK |
| `trigger-klasse-marx` | Political | [Q9061](https://www.wikidata.org/wiki/Q9061) | Karl Marx | Q5 | OK |
| `trigger-kleenex-kc` | Commercial | [Q1741634](https://www.wikidata.org/wiki/Q1741634) | Kimberly-Clark | Q4830453, Q6881511, Q891723 | OK |
| `trigger-klimakleber-lg` | Political | [Q110819215](https://www.wikidata.org/wiki/Q110819215) | Last Generation | Q1785733, Q163740 | OK |
| `trigger-labello-de-brand` | Commercial | [Q201691](https://www.wikidata.org/wiki/Q201691) | Beiersdorf | Q4830453, Q891723 | OK |
| `trigger-lesbian-sappho` | Cultural | [Q17892](https://www.wikidata.org/wiki/Q17892) | Sappho | Q5 | OK |
| `trigger-linoleum-walton` | Commercial | [Q907886](https://www.wikidata.org/wiki/Q907886) | Frederick Walton | Q5 | OK |
| `trigger-luddite-uprising` | Technology | [Q1159675](https://www.wikidata.org/wiki/Q1159675) | Luddite movement | Q2738074, Q49780, Q208701 | OK |
| `trigger-luegenpresse-pegida` | Political | [Q18762431](https://www.wikidata.org/wiki/Q18762431) | lying press | Q2101619, Q7281 | OK |
| `trigger-mach-de-shockwave` | Technology | [Q93996](https://www.wikidata.org/wiki/Q93996) | Ernst Mach | Q5 | OK |
| `trigger-machiavellian-principe` | Political | [Q1399](https://www.wikidata.org/wiki/Q1399) | Niccolò Machiavelli | Q5 | OK |
| `trigger-malapropism-rivals` | Cultural | [Q7760957](https://www.wikidata.org/wiki/Q7760957) | The Rivals | Q116476516 | OK |
| `trigger-marathon-olympics` | Cultural | [Q8080](https://www.wikidata.org/wiki/Q8080) | 1896 Summer Olympics | Q135976384, Q14547231 | OK |
| `trigger-mauerfall` | Political | [Q69163529](https://www.wikidata.org/wiki/Q69163529) | fall of the Berlin Wall | Q13418847, Q331483 | OK |
| `trigger-mausoleum-halicarnassus` | Cultural | [Q296857](https://www.wikidata.org/wiki/Q296857) | Mausolus | Q5 | OK |
| `trigger-maverick-cattle` | Cultural | [Q346455](https://www.wikidata.org/wiki/Q346455) | Samuel Maverick | Q5 | OK |
| `trigger-mentor-telemaque` | Cultural | [Q421615](https://www.wikidata.org/wiki/Q421615) | Les Aventures de Télémaque | Q7725634 | OK |
| `trigger-mesmerize-mesmer` | Cultural | [Q160202](https://www.wikidata.org/wiki/Q160202) | Franz Anton Mesmer | Q5 | OK |
| `trigger-monty-python-spam` | Cultural | [Q1777591](https://www.wikidata.org/wiki/Q1777591) | Spam | Q16909656 | OK |
| `trigger-morse-code-telegraph` | Technology | [Q75698](https://www.wikidata.org/wiki/Q75698) | Samuel Finley Breese Morse | Q5 | OK |
| `trigger-narcissism-coinage` | Cultural | [Q552983](https://www.wikidata.org/wiki/Q552983) | Havelock Ellis | Q5 | OK |
| `trigger-nicotine-tobacco` | Cultural | [Q318368](https://www.wikidata.org/wiki/Q318368) | Jean Nicot | Q5 | OK |
| `trigger-nylon-dupont` | Commercial | [Q221062](https://www.wikidata.org/wiki/Q221062) | DuPont | Q4830453, Q891723 | OK |
| `trigger-ohm-de-law` | Technology | [Q1585](https://www.wikidata.org/wiki/Q1585) | Georg Simon Ohm | Q5 | OK |
| `trigger-ohm-law` | Technology | [Q1585](https://www.wikidata.org/wiki/Q1585) | Georg Simon Ohm | Q5 | OK |
| `trigger-pasteurize-heat` | Technology | [Q529](https://www.wikidata.org/wiki/Q529) | Louis Pasteur | Q5 | OK |
| `trigger-pfaffe-reformation` | Cultural | [Q12562](https://www.wikidata.org/wiki/Q12562) | Protestant Reformation | Q1128340, Q126288065 | OK |
| `trigger-philippic-demosthenes` | Political | [Q117253](https://www.wikidata.org/wiki/Q117253) | Demosthenes | Q5 | OK |
| `trigger-propaganda-congregatio` | Cultural | [Q386359](https://www.wikidata.org/wiki/Q386359) | Congregation for the Evangelization of Peoples | Q1365916 | OK |
| `trigger-queer-nation` | Political | [Q5687582](https://www.wikidata.org/wiki/Q5687582) | Queer Nation | Q64606659 | OK |
| `trigger-querdenken-711` | Political | [Q115500066](https://www.wikidata.org/wiki/Q115500066) | Querdenken 711 | Q79913 | OK |
| `trigger-quisling-invasion` | Political | [Q151364](https://www.wikidata.org/wiki/Q151364) | Vidkun Quisling | Q5 | OK |
| `trigger-quixotic-cervantes` | Cultural | [Q480](https://www.wikidata.org/wiki/Q480) | Don Quixote | Q7725634 | OK |
| `trigger-robot-rur` | Cultural | [Q1164094](https://www.wikidata.org/wiki/Q1164094) | R.U.R. | Q116476516 | OK |
| `trigger-roentgen-discovery` | Technology | [Q35149](https://www.wikidata.org/wiki/Q35149) | Wilhelm Conrad Röntgen | Q5 | OK |
| `trigger-rugby-school` | Cultural | [Q1143281](https://www.wikidata.org/wiki/Q1143281) | Rugby School | Q1972829, Q2418495, Q269770 | OK |
| `trigger-saxophone-patent` | Technology | [Q181995](https://www.wikidata.org/wiki/Q181995) | Adolphe Sax | Q5 | OK |
| `trigger-schuetzengraben-wwi` | Political | [Q361](https://www.wikidata.org/wiki/Q361) | World War I | Q103495, Q11514315 | OK |
| `trigger-schwurbler-covid` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-shrapnel-shell` | Technology | [Q941215](https://www.wikidata.org/wiki/Q941215) | Henry Shrapnel | Q5 | OK |
| `trigger-silhouette-minister` | Cultural | [Q290240](https://www.wikidata.org/wiki/Q290240) | Étienne de Silhouette | Q5 | OK |
| `trigger-slop-genai` | Technology | [Q115564437](https://www.wikidata.org/wiki/Q115564437) | ChatGPT | Q133284163, Q116777014, Q115305900 | OK |
| `trigger-south-sea-bubble` | Commercial | [Q18643921](https://www.wikidata.org/wiki/Q18643921) | South Sea Bubble | Q1020018, Q290178 | OK |
| `trigger-spa-town` | Commercial | [Q39865](https://www.wikidata.org/wiki/Q39865) | Spa | Q493522, Q15273785, Q4946461 | OK |
| `trigger-stan-eminem` | Media | [Q312122](https://www.wikidata.org/wiki/Q312122) | Stan | Q134556 | OK |
| `trigger-stonewall` | Political | [Q51402](https://www.wikidata.org/wiki/Q51402) | Stonewall riots | Q125506609 | OK |
| `trigger-streaming-services` | Technology | [Q866](https://www.wikidata.org/wiki/Q866) |  | Q59152282, Q559856, Q122759350 | OK |
| `trigger-sus-amongus` | Cultural | [Q96417649](https://www.wikidata.org/wiki/Q96417649) | Among Us | Q112144412, Q7889, Q2927074 | OK |
| `trigger-tank-somme` | Technology | [Q1284532](https://www.wikidata.org/wiki/Q1284532) | Mark I | Q100710213 | OK |
| `trigger-trommelfeuer-wwi` | Political | [Q361](https://www.wikidata.org/wiki/Q361) | World War I | Q103495, Q11514315 | OK |
| `trigger-tuxedo-park` | Cultural | [Q3273900](https://www.wikidata.org/wiki/Q3273900) | Tuxedo Park | Q751708, Q55237813 | OK |
| `trigger-twitter-launch` | Technology | [Q918](https://www.wikidata.org/wiki/Q918) | X | Q3220391, Q92438, Q122759350 | OK |
| `trigger-uhu-de-brand` | Commercial | [Q63281550](https://www.wikidata.org/wiki/Q63281550) | UHU GmbH & Co. KG | Q6881511 | OK |
| `trigger-unfriend-facebook` | Technology | [Q355](https://www.wikidata.org/wiki/Q355) |  | Q3220391, Q35127, Q620615 | OK |
| `trigger-vandalismus-gregoire` | Political | [Q561218](https://www.wikidata.org/wiki/Q561218) | Henri Grégoire | Q5 | OK |
| `trigger-volt-pile` | Technology | [Q680](https://www.wikidata.org/wiki/Q680) | Alessandro Volta | Q5 | OK |
| `trigger-watt-engine` | Technology | [Q9041](https://www.wikidata.org/wiki/Q9041) | James Watt | Q5 | OK |
| `trigger-wd-covid-19-pandemic` | Pandemic | [Q81068910](https://www.wikidata.org/wiki/Q81068910) | COVID-19 pandemic | Q12184, Q17076801, Q3241045 | OK |
| `trigger-wd-german-reunification` | Political | [Q56039](https://www.wikidata.org/wiki/Q56039) | German reunification | Q1140229, Q1190554, Q50844387 | OK |
| `trigger-wd-querdenken-711-protest-movement` | Political | [Q115500066](https://www.wikidata.org/wiki/Q115500066) | Querdenken 711 | Q79913 | OK |
| `trigger-wd-rise-of-funk-music` | Cultural | [Q164444](https://www.wikidata.org/wiki/Q164444) | funk | Q188451 | OK |
| `trigger-wd-world-wide-web-invention` | Technology | [Q466](https://www.wikidata.org/wiki/Q466) | World Wide Web | Q121182, Q65966993 | OK |
| `trigger-www-mosaic` | Technology | [Q381047](https://www.wikidata.org/wiki/Q381047) | Mosaic | Q6368, Q56273712, Q218616 | OK |
| `trigger-xerox-914` | Commercial | [Q3570933](https://www.wikidata.org/wiki/Q3570933) | Xerox 914 | Q10929058 | OK |
| `trigger-yahoo-gulliver` | Cultural | [Q181488](https://www.wikidata.org/wiki/Q181488) | Gulliver's Travels | Q7725634 | OK |
| `trigger-zeppelin-lz1` | Technology | [Q75780](https://www.wikidata.org/wiki/Q75780) | Ferdinand von Zeppelin | Q5 | OK |
| `trigger-zipper-goodrich` | Commercial | [Q1537591](https://www.wikidata.org/wiki/Q1537591) | Goodrich Corporation | Q4830453, Q6881511 | OK |
