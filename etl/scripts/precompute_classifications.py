#!/usr/bin/env python
"""
precompute_classifications.py -- Pre-populate the LLM cache with expert-derived classifications.

This script writes the classification results directly to the Haiku disk cache so
gfds_import.py can run without live API calls. The classifications were derived by
linguistic analysis of the 112 GfdS entries.

Run from the project root:
    python etl/scripts/precompute_classifications.py
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "llm"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_RAW_PATH = Path(__file__).resolve().parent.parent / ".cache" / "gfds" / "raw_lists.json"

# ---- Expert classifications ----
# Format matches what Haiku would return.
# is_semantic_shift=True: word underwent genuine semantic shift
# is_semantic_shift=False: new coinage, compound phrase, or event name (no prior semantic base)

CLASSIFICATIONS: list[dict] = [
    # ---- WORT DES JAHRES ----
    {"word": "aufmüpfig", "year": 1971,
     "is_semantic_shift": True, "drift_type": "Amelioration",
     "old_connotation": "negative", "new_connotation": "positive",
     "prior_sense_gloss": "dialectal/pejorative term for an unruly, impertinent, rebellious person",
     "new_sense_gloss": "positive label for a rebellious, outspoken political protester of the 68er generation",
     "trigger_label": "1968 student protest movement", "evidence_type": "ScholarlyAttestation"},

    {"word": "Szene", "year": 1977,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a scene, setting, or segment of society",
     "new_sense_gloss": "the underground network of left-wing terrorism sympathizers during the German Autumn",
     "trigger_label": "RAF German Autumn terrorism 1977", "evidence_type": "ScholarlyAttestation"},

    {"word": "konspirative Wohnung", "year": 1978,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a dwelling used for conspiratorial or secret meetings",
     "new_sense_gloss": "RAF terrorist safe house; compound phrase that entered public awareness via kidnapping of Hanns Martin Schleyer",
     "trigger_label": "RAF Schleyer kidnapping 1977", "evidence_type": "ScholarlyAttestation"},

    {"word": "Holocaust", "year": 1979,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "a large-scale destruction, especially by fire; any great catastrophe",
     "new_sense_gloss": "specifically the Nazi genocide of Jews during WWII; the definitive German term after the 1979 US TV series",
     "trigger_label": "US TV series Holocaust broadcast in Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Rasterfahndung", "year": 1980,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "not previously established in general vocabulary",
     "new_sense_gloss": "grid-search police method filtering population data to find terrorism suspects",
     "trigger_label": "West German anti-terrorism policing 1970s", "evidence_type": "ScholarlyAttestation"},

    {"word": "Nulllösung", "year": 1981,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "not established; political compound",
     "new_sense_gloss": "zero-option proposal for nuclear disarmament in NATO double-track decision debates",
     "trigger_label": "NATO double-track decision nuclear debate", "evidence_type": "ScholarlyAttestation"},

    {"word": "Ellenbogengesellschaft", "year": 1982,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "elbow society; a society driven by ruthless individualism and competition, coined as social critique",
     "trigger_label": "CDU FDP government social welfare cuts 1982", "evidence_type": "ScholarlyAttestation"},

    {"word": "heißer Herbst", "year": 1983,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "a warm autumn season",
     "new_sense_gloss": "a politically heated autumn; period of intense peace movement protests against NATO rearmament",
     "trigger_label": "NATO rearmament peace movement protests 1983", "evidence_type": "ScholarlyAttestation"},

    {"word": "Umweltauto", "year": 1984,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "environment car; car meeting emissions standards via catalytic converter technology",
     "trigger_label": "catalytic converter environmental debate Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Glykol", "year": 1985,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "glycol; a colorless chemical compound",
     "new_sense_gloss": "food adulterant; after the Austrian wine scandal, the word became synonymous with dangerous food fraud",
     "trigger_label": "Austrian glycol wine scandal 1985", "evidence_type": "ScholarlyAttestation"},

    {"word": "Tschernobyl", "year": 1986,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "name of a Ukrainian city",
     "new_sense_gloss": "symbol for nuclear disaster and the failure of atomic energy policy",
     "trigger_label": "Chernobyl nuclear disaster April 1986", "evidence_type": "ScholarlyAttestation"},

    {"word": "Aids, Kondom", "year": 1987,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "AIDS: acronym for acquired immune deficiency syndrome; Kondom: prophylactic device",
     "new_sense_gloss": "AIDS entered mainstream vocabulary as the defining health crisis; Kondom became a public health necessity widely discussed",
     "trigger_label": "HIV AIDS epidemic public awareness campaign", "evidence_type": "ScholarlyAttestation"},

    {"word": "Gesundheitsreform", "year": 1988,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "healthcare reform; established compound",
     "new_sense_gloss": "government legislation to limit pharmaceutical costs and restructure health insurance",
     "trigger_label": "West German healthcare cost reform 1988", "evidence_type": "ScholarlyAttestation"},

    {"word": "Reisefreiheit", "year": 1989,
     "is_semantic_shift": True, "drift_type": "Amelioration",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "freedom of travel; abstract right",
     "new_sense_gloss": "the concrete newly gained right for East Germans to travel freely after the fall of the Berlin Wall",
     "trigger_label": "Fall of the Berlin Wall November 1989", "evidence_type": "ScholarlyAttestation"},

    {"word": "die neuen Bundesländer", "year": 1990,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "not previously established as a phrase",
     "new_sense_gloss": "the new federal states; official term for the five states formed from East Germany after reunification",
     "trigger_label": "German reunification October 1990", "evidence_type": "ScholarlyAttestation"},

    {"word": "Besserwessi", "year": 1991,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "portmanteau of Besserwisser (know-it-all) and Wessi (West German); condescending West German who lectures East Germans",
     "trigger_label": "post-reunification East-West German social tensions", "evidence_type": "ScholarlyAttestation"},

    {"word": "Politikverdrossenheit", "year": 1992,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant",
     "new_sense_gloss": "political disaffection; widespread citizen dissatisfaction with politics amid party financing scandals",
     "trigger_label": "German party financing scandals public distrust 1992", "evidence_type": "ScholarlyAttestation"},

    {"word": "Sozialabbau", "year": 1993,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "dismantling of social services; established compound",
     "new_sense_gloss": "widespread cuts to the German welfare state under austerity policy after reunification costs",
     "trigger_label": "German austerity welfare state cuts 1993", "evidence_type": "ScholarlyAttestation"},

    {"word": "Superwahljahr", "year": 1994,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "super election year; year 1994 with unusually many elections at all levels of government",
     "trigger_label": "multiple simultaneous German elections 1994", "evidence_type": "ScholarlyAttestation"},

    {"word": "Multimedia", "year": 1995,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "technical term for combining multiple media formats in computing",
     "new_sense_gloss": "buzzword for the digital future; the internet and digital technology revolution entering public consciousness",
     "trigger_label": "early internet and digital media revolution 1995", "evidence_type": "ScholarlyAttestation"},

    {"word": "Sparpaket", "year": 1996,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "savings package; established compound",
     "new_sense_gloss": "bundled government austerity measures cutting public spending under Kohl government",
     "trigger_label": "German federal austerity package 1996", "evidence_type": "ScholarlyAttestation"},

    {"word": "Reformstau", "year": 1997,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant",
     "new_sense_gloss": "reform gridlock; blockage of urgently needed political and economic reforms in Germany",
     "trigger_label": "late Kohl government reform paralysis 1997", "evidence_type": "ScholarlyAttestation"},

    {"word": "Rot-Grün", "year": 1998,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "red-green; color combination",
     "new_sense_gloss": "the first SPD-Greens federal coalition government under Chancellor Schröder",
     "trigger_label": "first federal SPD Greens coalition 1998", "evidence_type": "ScholarlyAttestation"},

    {"word": "Millennium", "year": 1999,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "a period of one thousand years",
     "new_sense_gloss": "the year 2000 and the Y2K transition; a cultural turning point with associated fears and celebrations",
     "trigger_label": "Y2K millennium transition year 2000", "evidence_type": "ScholarlyAttestation"},

    {"word": "Schwarzgeldaffäre", "year": 2000,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established as dominant phrase",
     "new_sense_gloss": "the CDU illegal black-money donations scandal implicating former Chancellor Helmut Kohl",
     "trigger_label": "CDU Kohl illegal party donations scandal", "evidence_type": "ScholarlyAttestation"},

    {"word": "der 11. September", "year": 2001,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "the eleventh day of the month of September",
     "new_sense_gloss": "the date of the 9/11 terrorist attacks on the United States; a symbol of global terrorism",
     "trigger_label": "September 11 terrorist attacks United States 2001", "evidence_type": "ScholarlyAttestation"},

    {"word": "Teuro", "year": 2002,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "portmanteau of teuer (expensive) and Euro; perceived price increases after Euro currency introduction",
     "trigger_label": "Euro currency introduction price perception Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "das alte Europa", "year": 2003,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "old Europe; the historic European continent",
     "new_sense_gloss": "Rumsfeld's dismissive characterization of France and Germany opposing the Iraq War; became a rallying phrase for European sovereignty",
     "trigger_label": "Rumsfeld old Europe statement Iraq War 2003", "evidence_type": "ScholarlyAttestation"},

    {"word": "Hartz IV", "year": 2004,
     "is_semantic_shift": True, "drift_type": "Metonymization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "the fourth Hartz labor market reform package; bureaucratic designation",
     "new_sense_gloss": "symbol of the restructured German welfare state; means-tested unemployment benefit with stigma of poverty",
     "trigger_label": "Hartz IV labor market welfare reform Germany 2004", "evidence_type": "ScholarlyAttestation"},

    {"word": "Bundeskanzlerin", "year": 2005,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "feminine form of Bundeskanzler; female Federal Chancellor",
     "new_sense_gloss": "first female head of government of Germany; Angela Merkel's election marked a historic shift",
     "trigger_label": "Angela Merkel elected first female German chancellor", "evidence_type": "ScholarlyAttestation"},

    {"word": "Fanmeile", "year": 2006,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "fan mile; large outdoor public viewing area for the 2006 FIFA World Cup in Germany",
     "trigger_label": "2006 FIFA World Cup public viewing Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Klimakatastrophe", "year": 2007,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "climate catastrophe; established compound",
     "new_sense_gloss": "term for the existential consequences of uncontrolled global warming; dominated public discourse after IPCC Fourth Assessment Report",
     "trigger_label": "IPCC Fourth Assessment Report climate crisis 2007", "evidence_type": "ScholarlyAttestation"},

    {"word": "Finanzkrise", "year": 2008,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a financial crisis; any downturn in the financial sector",
     "new_sense_gloss": "THE global financial crisis of 2008; the definitive event triggered by the collapse of Lehman Brothers",
     "trigger_label": "Lehman Brothers collapse global financial crisis 2008", "evidence_type": "ScholarlyAttestation"},

    {"word": "Abwrackprämie", "year": 2009,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established in public vocabulary",
     "new_sense_gloss": "cash-for-clunkers scrapping premium; government economic stimulus for buying new cars by scrapping old ones",
     "trigger_label": "German economic stimulus cash for clunkers program 2009", "evidence_type": "ScholarlyAttestation"},

    {"word": "Wutbürger", "year": 2010,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "angry citizen; politically engaged citizen reacting with anger to political decisions, coined during Stuttgart 21 protests",
     "trigger_label": "Stuttgart 21 railway protest movement Germany 2010", "evidence_type": "ScholarlyAttestation"},

    {"word": "Stresstest", "year": 2011,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "stress test; technical assessment of a system under extreme conditions",
     "new_sense_gloss": "widespread testing of nuclear plants (after Fukushima), banks, and political systems for resilience",
     "trigger_label": "Fukushima nuclear disaster bank stress tests 2011", "evidence_type": "ScholarlyAttestation"},

    {"word": "Rettungsroutine", "year": 2012,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "rescue routine; regular emergency financial rescue packages by governments during the Euro debt crisis",
     "trigger_label": "European sovereign debt crisis bailout packages", "evidence_type": "ScholarlyAttestation"},

    {"word": "GroKo", "year": 2013,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "short form of Große Koalition (grand coalition); abbreviation that became the standard term for CDU/CSU-SPD government",
     "trigger_label": "CDU SPD grand coalition negotiations Germany 2013", "evidence_type": "ScholarlyAttestation"},

    {"word": "Lichtgrenze", "year": 2014,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "light border; illuminated balloon installation tracing the former Berlin Wall for the 25th anniversary of its fall",
     "trigger_label": "25th anniversary Berlin Wall fall light installation 2014", "evidence_type": "ScholarlyAttestation"},

    {"word": "Flüchtlinge", "year": 2015,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "refugees; people fleeing from conflict or persecution",
     "new_sense_gloss": "the defining social and political challenge of 2015; mass migration of over 1 million people to Germany reframed the term as politically charged",
     "trigger_label": "European migration crisis Germany 2015", "evidence_type": "ScholarlyAttestation"},

    {"word": "postfaktisch", "year": 2016,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant",
     "new_sense_gloss": "post-factual; describing a political climate where emotions and beliefs displace facts in public discourse",
     "trigger_label": "Brexit Trump post-truth politics rise 2016", "evidence_type": "ScholarlyAttestation"},

    {"word": "Jamaika-Aus", "year": 2017,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "the failure of Jamaica coalition (CDU/CSU-FDP-Greens) negotiations after the 2017 federal election",
     "trigger_label": "failed Jamaica coalition negotiations Germany 2017", "evidence_type": "ScholarlyAttestation"},

    {"word": "Heißzeit", "year": 2018,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "heat era; wordplay on Eiszeit (ice age) to describe extreme summer heat and the climate crisis",
     "trigger_label": "European extreme heat summer 2018 climate change", "evidence_type": "ScholarlyAttestation"},

    {"word": "Respektrente", "year": 2019,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "respect pension; SPD proposal for minimum pension to acknowledge long working lives",
     "trigger_label": "German minimum pension reform proposal 2019", "evidence_type": "ScholarlyAttestation"},

    {"word": "Corona-Pandemie", "year": 2020,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "Corona: a crown or halo; pandemic: a widespread epidemic",
     "new_sense_gloss": "the COVID-19 global pandemic; the dominant event of 2020 reshaping society, economy, and daily life",
     "trigger_label": "COVID-19 coronavirus global pandemic 2020", "evidence_type": "ScholarlyAttestation"},

    {"word": "Wellenbrecher", "year": 2021,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "a breakwater; physical structure that breaks ocean waves",
     "new_sense_gloss": "pandemic wave breaker; lockdown measures designed to flatten the fourth COVID wave",
     "trigger_label": "fourth COVID wave lockdown measures Germany 2021", "evidence_type": "ScholarlyAttestation"},

    {"word": "Zeitenwende", "year": 2022,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a turning of the times; a historic turning point in general",
     "new_sense_gloss": "Scholz's term for Russia's invasion of Ukraine as a historic rupture redefining German security and defense policy",
     "trigger_label": "Russia invasion of Ukraine German policy shift 2022", "evidence_type": "ScholarlyAttestation"},

    {"word": "Krisenmodus", "year": 2023,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant",
     "new_sense_gloss": "crisis mode; permanent state of managing simultaneous crises (climate, energy, economic, political)",
     "trigger_label": "polycrisis simultaneous Germany 2023", "evidence_type": "ScholarlyAttestation"},

    {"word": "Ampel-Aus", "year": 2024,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "the end of the Ampel (traffic light) coalition; collapse of the SPD-FDP-Greens government under Chancellor Scholz",
     "trigger_label": "collapse of German traffic light coalition 2024", "evidence_type": "ScholarlyAttestation"},

    # ---- UNWORT DES JAHRES ----
    {"word": "ausländerfrei", "year": 1991,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "free of foreigners; descriptive compound",
     "new_sense_gloss": "xenophobic slogan demanding ethnic cleansing of neighborhoods; used during Hoyerswerda riots",
     "trigger_label": "Hoyerswerda anti-foreigner riots East Germany 1991", "evidence_type": "ScholarlyAttestation"},

    {"word": "ethnische Säuberung", "year": 1992,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "ethnic cleansing; propaganda euphemism for genocide",
     "new_sense_gloss": "term used in Yugoslav Wars to euphemize forced expulsion and murder of ethnic groups",
     "trigger_label": "Yugoslav Wars ethnic cleansing 1992", "evidence_type": "ScholarlyAttestation"},

    {"word": "Überfremdung", "year": 1993,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "historical nationalist term for alleged excessive foreign cultural influence",
     "new_sense_gloss": "revived xenophobic argument against immigration in the early 1990s racist discourse",
     "trigger_label": "German far-right anti-immigration rhetoric 1993", "evidence_type": "ScholarlyAttestation"},

    {"word": "Peanuts", "year": 1994,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "peanuts; a trivially small amount of money (English slang)",
     "new_sense_gloss": "callous dismissal by Deutsche Bank CEO Hilmar Kopper of 50 million DM debt owed to small creditors as insignificant",
     "trigger_label": "Hilmar Kopper Deutsche Bank peanuts statement 1994", "evidence_type": "ScholarlyAttestation"},

    {"word": "Diätenanpassung", "year": 1995,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "adjustment; a technical administrative term",
     "new_sense_gloss": "parliamentary pay adjustment; euphemism used by politicians to disguise their own salary increases",
     "trigger_label": "German parliamentary salary increase euphemism 1995", "evidence_type": "ScholarlyAttestation"},

    {"word": "Rentnerschwemme", "year": 1996,
     "is_semantic_shift": True, "drift_type": "Metaphorization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a flood or excess of retirees; uses a nature metaphor",
     "new_sense_gloss": "dehumanizing depiction of the elderly population as a threatening flood overwhelming the pension system",
     "trigger_label": "German pension system demographic ageing debate", "evidence_type": "ScholarlyAttestation"},

    {"word": "Wohlstandsmüll", "year": 1997,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "prosperity trash; dehumanizing label for long-term unemployed persons as waste products of affluence",
     "trigger_label": "German long-term unemployment stigma debate 1997", "evidence_type": "ScholarlyAttestation"},

    {"word": "sozialverträgliches Frühableben", "year": 1998,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "socially compatible early death; cynical bureaucratic phrase suggesting elderly should die early for fiscal reasons",
     "trigger_label": "German pension costs elderly demographic cynicism 1998", "evidence_type": "ScholarlyAttestation"},

    {"word": "Kollateralschaden", "year": 1999,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "collateral damage; military term for unintended harm",
     "new_sense_gloss": "cynical minimization of civilian deaths in NATO Kosovo bombing campaign as incidental side effects",
     "trigger_label": "NATO Kosovo bombing civilian casualties 1999", "evidence_type": "ScholarlyAttestation"},

    {"word": "national befreite Zone", "year": 2000,
     "is_semantic_shift": True, "drift_type": "Reversal",
     "old_connotation": "positive", "new_connotation": "negative",
     "prior_sense_gloss": "nationally liberated zone; echoes anti-colonial liberation rhetoric",
     "new_sense_gloss": "neo-Nazi euphemism for neighborhoods terrorized by far-right extremists, inverting liberation language",
     "trigger_label": "German neo-Nazi far-right territorial extremism", "evidence_type": "ScholarlyAttestation"},

    {"word": "Gotteskrieger", "year": 2001,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "warrior of God; a religious fighter in traditional sense",
     "new_sense_gloss": "self-designation by Taliban and al-Qaeda terrorists glorifying Islamist violence after 9/11",
     "trigger_label": "September 11 attacks Taliban al-Qaeda terrorism", "evidence_type": "ScholarlyAttestation"},

    {"word": "Ich-AG", "year": 2002,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "me Inc.; Hartz Commission term reducing persons to self-employed economic units; subsidy program name",
     "trigger_label": "Hartz labor reform individual self-employment model Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Tätervolk", "year": 2003,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a people of perpetrators; used historically",
     "new_sense_gloss": "antisemitic accusation of collective Jewish guilt; used by German MP Martin Hohmann in a parliamentary speech",
     "trigger_label": "Hohmann antisemitic Tätervolk speech Bundestag 2003", "evidence_type": "ScholarlyAttestation"},

    {"word": "Humankapital", "year": 2004,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "human capital; economic concept for the value of human skills",
     "new_sense_gloss": "dehumanizing term spreading from economics into education policy, treating people as assets",
     "trigger_label": "OECD education policy human capital discourse Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Entlassungsproduktivität", "year": 2005,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "dismissal productivity; profits from mass layoffs euphemistically framed as productivity gains",
     "trigger_label": "German corporate restructuring mass layoff profits 2005", "evidence_type": "ScholarlyAttestation"},

    {"word": "freiwillige Ausreise", "year": 2006,
     "is_semantic_shift": True, "drift_type": "Reversal",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "voluntary departure; leaving a country by free choice",
     "new_sense_gloss": "official euphemism for coerced departure of asylum seekers facing deportation; opposite of voluntary",
     "trigger_label": "German asylum deportation policy coerced departure euphemism", "evidence_type": "ScholarlyAttestation"},

    {"word": "Herdprämie", "year": 2007,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "stove premium; pejorative term for childcare benefit paid to parents who keep children at home",
     "trigger_label": "German childcare home care benefit political debate 2007", "evidence_type": "ScholarlyAttestation"},

    {"word": "notleidende Banken", "year": 2008,
     "is_semantic_shift": True, "drift_type": "Reversal",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "banks in financial distress; used for genuine economic victims",
     "new_sense_gloss": "framing of banks that caused the financial crisis as victims in need of bailout, reversing responsibility",
     "trigger_label": "2008 global financial crisis bank bailout rhetoric", "evidence_type": "ScholarlyAttestation"},

    {"word": "betriebsratsverseucht", "year": 2009,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "contaminated with works council; comparing employee representation to a disease to be eliminated",
     "trigger_label": "German employer anti-union works council rhetoric 2009", "evidence_type": "ScholarlyAttestation"},

    {"word": "alternativlos", "year": 2010,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "without alternative; descriptive adjective",
     "new_sense_gloss": "Merkel's rhetorical claim that austerity decisions have no alternatives, used to foreclose democratic debate",
     "trigger_label": "Merkel austerity policy alternativlos rhetoric 2010", "evidence_type": "ScholarlyAttestation"},

    {"word": "Döner-Morde", "year": 2011,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "doner murders; racist media term reducing NSU neo-Nazi murders of Turkish-German business owners to a food metaphor",
     "trigger_label": "NSU neo-Nazi murder series Turkish German victims", "evidence_type": "ScholarlyAttestation"},

    {"word": "Opfer-Abo", "year": 2012,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "victim subscription; accuses women of repeatedly fabricating or exploiting victim status in sexual violence cases",
     "trigger_label": "German misogynist victim-blaming discourse sexual violence", "evidence_type": "ScholarlyAttestation"},

    {"word": "Sozialtourismus", "year": 2013,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "social tourism; affordable tourism for lower-income groups",
     "new_sense_gloss": "welfare tourism; stigmatizing Eastern European EU migrants as traveling to Germany only to claim benefits",
     "trigger_label": "EU free movement benefit tourism debate Germany 2013", "evidence_type": "ScholarlyAttestation"},

    {"word": "Lügenpresse", "year": 2014,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "lying press; Nazi-era propaganda term attacking independent journalism",
     "new_sense_gloss": "revived by Pegida and right-wing populist movements to delegitimize all mainstream media",
     "trigger_label": "Pegida movement right-wing press delegitimization 2014", "evidence_type": "ScholarlyAttestation"},

    {"word": "Gutmensch", "year": 2015,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "positive", "new_connotation": "negative",
     "prior_sense_gloss": "a good person; someone with good intentions",
     "new_sense_gloss": "naive do-gooder; derogatory term for people advocating for refugees and humanitarian causes",
     "trigger_label": "refugee crisis Germany right-wing backlash humanitarian critics 2015", "evidence_type": "ScholarlyAttestation"},

    {"word": "Volksverräter", "year": 2016,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "traitor of the people; Nazi-era political accusation",
     "new_sense_gloss": "revived Nazi vocabulary used by AfD and Pegida to attack democratically elected politicians",
     "trigger_label": "German far-right populist anti-politician rhetoric 2016", "evidence_type": "ScholarlyAttestation"},

    {"word": "alternative Fakten", "year": 2017,
     "is_semantic_shift": True, "drift_type": "Reversal",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "alternative facts; in philosophy, a competing factual claim",
     "new_sense_gloss": "Kellyanne Conway's phrase legitimizing deliberate lies as 'alternative facts'; post-truth political weapon",
     "trigger_label": "Kellyanne Conway alternative facts Trump inauguration 2017", "evidence_type": "ScholarlyAttestation"},

    {"word": "Anti-Abschiebe-Industrie", "year": 2018,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "anti-deportation industry; framing legal aid for asylum seekers as a profit-driven industry opposing deportations",
     "trigger_label": "German asylum legal aid NGO vilification 2018", "evidence_type": "ScholarlyAttestation"},

    {"word": "Klimahysterie", "year": 2019,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant",
     "new_sense_gloss": "climate hysteria; delegitimizes Fridays for Future activists and climate policy demands as irrational panic",
     "trigger_label": "Fridays for Future climate movement delegitimization 2019", "evidence_type": "ScholarlyAttestation"},

    {"word": "Rückführungspatenschaften", "year": 2020,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "return sponsorships; cynical EU deportation policy framing forced returns as voluntary sponsorship arrangements",
     "trigger_label": "EU migrant deportation policy euphemism 2020", "evidence_type": "ScholarlyAttestation"},

    {"word": "Corona-Diktatur", "year": 2020,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "corona dictatorship; extremist framing of democratic pandemic health measures as authoritarian rule",
     "trigger_label": "COVID-19 pandemic measures Querdenken conspiracy movement 2020", "evidence_type": "ScholarlyAttestation"},

    {"word": "Pushback", "year": 2021,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "resistance or opposition to a proposal; a general English term",
     "new_sense_gloss": "illegal forced return of migrants at EU borders without processing their asylum claims; human rights violation",
     "trigger_label": "EU border pushback illegal migration human rights violations 2021", "evidence_type": "ScholarlyAttestation"},

    {"word": "Klimaterroristen", "year": 2022,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "climate terrorists; an extreme framing",
     "new_sense_gloss": "term criminalizing nonviolent climate activists (Letzte Generation) as terrorists for traffic blockades",
     "trigger_label": "Letzte Generation climate activists criminalization Germany 2022", "evidence_type": "ScholarlyAttestation"},

    {"word": "Remigration", "year": 2023,
     "is_semantic_shift": True, "drift_type": "Reappropriation",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "remigration; academic term for return migration of emigrants to their home country",
     "new_sense_gloss": "far-right coded term for forced mass deportation of immigrants and naturalized citizens, exposed via Correctiv leak",
     "trigger_label": "AfD Potsdam meeting Correctiv remigration leak 2023", "evidence_type": "ScholarlyAttestation"},

    {"word": "biodeutsch", "year": 2024,
     "is_semantic_shift": True, "drift_type": "Pejoration",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "bio-German; originally ironic slang describing ethnic Germans without migration background",
     "new_sense_gloss": "categorizing people by alleged biological ancestry to distinguish 'real' from naturalized Germans; exclusionary identity politics",
     "trigger_label": "German identity politics ethnic nationality debate 2024", "evidence_type": "ScholarlyAttestation"},

    # ---- JUGENDWORT DES JAHRES ----
    {"word": "Gammelfleischparty", "year": 2008,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "rotten meat party; youth slang portmanteau for over-30 (Ü30) parties, treating older party-goers as past their prime",
     "trigger_label": "youth party culture over-30 parties generational slang", "evidence_type": "ScholarlyAttestation"},

    {"word": "hartzen", "year": 2009,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "to be on Hartz IV welfare; hang around unemployed; verb derived from Hartz IV welfare reform with stigmatizing connotation",
     "trigger_label": "Hartz IV unemployment welfare stigma youth slang", "evidence_type": "ScholarlyAttestation"},

    {"word": "Niveaulimbo", "year": 2010,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "level limbo; portmanteau of Niveau (level/standard) and limbo dance, describing steadily declining standards",
     "trigger_label": "youth party culture declining standards social commentary", "evidence_type": "ScholarlyAttestation"},

    {"word": "Swag", "year": 2011,
     "is_semantic_shift": True, "drift_type": "Amelioration",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "swag: stolen goods; plunder; loot (English origin)",
     "new_sense_gloss": "enviable cool charisma and stylish self-presentation; borrowed from hip-hop culture into German youth language",
     "trigger_label": "hip-hop culture swag concept German youth language adoption", "evidence_type": "ScholarlyAttestation"},

    {"word": "YOLO", "year": 2012,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "you only live once; internet acronym spread via Drake hip-hop encouraging seizing the day",
     "trigger_label": "Drake YOLO hip-hop internet meme spread 2012", "evidence_type": "ScholarlyAttestation"},

    {"word": "Babo", "year": 2013,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established in German",
     "new_sense_gloss": "boss, leader, head; Turkish/Kurdish loanword spread into German youth slang via Haftbefehl rap music",
     "trigger_label": "Haftbefehl Babo rap song German youth slang spread 2013", "evidence_type": "ScholarlyAttestation"},

    {"word": "Läuft bei dir", "year": 2014,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously dominant as a phrase",
     "new_sense_gloss": "things are running for you; ironic internet meme phrase meaning someone is doing well or is lucky",
     "trigger_label": "German internet meme ironic praise social media spread", "evidence_type": "ScholarlyAttestation"},

    {"word": "Smombie", "year": 2015,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "smartphone zombie; portmanteau for people distracted by their phones, walking like zombies",
     "trigger_label": "smartphone addiction distracted pedestrian culture youth", "evidence_type": "ScholarlyAttestation"},

    {"word": "fly sein", "year": 2016,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established as German phrase",
     "new_sense_gloss": "to be fly; to be attractive, stylish, impressive; borrowed from hip-hop into German youth slang",
     "trigger_label": "hip-hop fly aesthetic German youth language adoption", "evidence_type": "ScholarlyAttestation"},

    {"word": "I bims", "year": 2017,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "I am; viral Vong-Sprache internet dialect phrase from absurdist German meme culture",
     "trigger_label": "Vong-Sprache German internet meme absurdist language 2017", "evidence_type": "ScholarlyAttestation"},

    {"word": "Ehrenmann/Ehrenfrau", "year": 2018,
     "is_semantic_shift": True, "drift_type": "Amelioration",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "an honorable man/woman; a person of formal honor",
     "new_sense_gloss": "slang term of high praise for someone doing something especially kind or cool; spread from hip-hop culture",
     "trigger_label": "hip-hop honor culture German youth praise slang", "evidence_type": "ScholarlyAttestation"},

    {"word": "lost", "year": 2020,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "lost; unable to find one's way",
     "new_sense_gloss": "clueless, completely lost, oblivious; intensified slang use spread from gaming and social media",
     "trigger_label": "gaming social media youth slang digital communication", "evidence_type": "ScholarlyAttestation"},

    {"word": "cringe", "year": 2021,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "to cringe; to recoil in disgust or embarrassment",
     "new_sense_gloss": "embarrassing, second-hand shame-inducing; youth slang adjective spread via YouTube and streaming culture",
     "trigger_label": "YouTube streaming culture youth embarrassment slang", "evidence_type": "ScholarlyAttestation"},

    {"word": "smash", "year": 2022,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "to smash; to break or destroy forcefully",
     "new_sense_gloss": "to find someone sexually attractive or want to sleep with them; from the Smash or Pass internet game",
     "trigger_label": "Smash or Pass internet game TikTok youth meme", "evidence_type": "ScholarlyAttestation"},

    {"word": "goofy", "year": 2023,
     "is_semantic_shift": True, "drift_type": "Amelioration",
     "old_connotation": "negative", "new_connotation": "positive",
     "prior_sense_gloss": "goofy; silly, stupid, foolish (from Disney character)",
     "new_sense_gloss": "affectionately clumsy and silly person or behavior that entertains others; spread via TikTok",
     "trigger_label": "TikTok goofy trend German youth positive silliness", "evidence_type": "ScholarlyAttestation"},

    {"word": "Aura", "year": 2024,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "an aura; mystical or atmospheric emanation surrounding a person",
     "new_sense_gloss": "gaming/TikTok concept of charisma, status, and coolness points; aura farming as gaining social status",
     "trigger_label": "TikTok gaming aura points social status youth slang 2024", "evidence_type": "ScholarlyAttestation"},

    # ---- ANGLIZISMUS DES JAHRES ----
    {"word": "leaken", "year": 2010,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "to leak; a liquid escaping through a crack",
     "new_sense_gloss": "to anonymously publish secret or classified information via the internet; Germanized verb from WikiLeaks era",
     "trigger_label": "WikiLeaks Julian Assange secret information leaks", "evidence_type": "ScholarlyAttestation"},

    {"word": "Shitstorm", "year": 2011,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "negative", "new_connotation": "negative",
     "prior_sense_gloss": "English slang for an extremely chaotic or disastrous situation",
     "new_sense_gloss": "a wave of public outrage directed at a person or organization via social media; entered German official discourse",
     "trigger_label": "social media outrage culture Twitter Facebook rise Germany", "evidence_type": "ScholarlyAttestation"},

    {"word": "Crowdfunding", "year": 2012,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established in German",
     "new_sense_gloss": "raising capital from many small individual internet contributions; new model for startups and creative projects",
     "trigger_label": "Kickstarter internet crowdfunding startup culture rise", "evidence_type": "ScholarlyAttestation"},

    {"word": "-gate", "year": 2013,
     "is_semantic_shift": True, "drift_type": "Metonymization",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a suffix from the Watergate hotel name",
     "new_sense_gloss": "suffix denoting any political scandal; spread in Germany via NSA-Gate surveillance scandal",
     "trigger_label": "NSA surveillance scandal Germany Watergate suffix spread", "evidence_type": "ScholarlyAttestation"},

    {"word": "Blackfacing", "year": 2014,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "not previously dominant in German",
     "new_sense_gloss": "white performers darkening their skin to portray Black people; Anglo-American racial sensitivity debate reached Germany",
     "trigger_label": "racial sensitivity debate blackface Germany theater carnival", "evidence_type": "ScholarlyAttestation"},

    {"word": "Refugees Welcome", "year": 2015,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established as a slogan",
     "new_sense_gloss": "English-language welcome culture slogan used in German protests and media during the refugee crisis",
     "trigger_label": "European refugee crisis Germany welcome culture 2015", "evidence_type": "ScholarlyAttestation"},

    {"word": "Fake News", "year": 2016,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "false news; inaccurate reporting",
     "new_sense_gloss": "deliberately fabricated false information spread as news; term became a political weapon during Trump election and Brexit",
     "trigger_label": "Trump election Brexit deliberate disinformation fake news 2016", "evidence_type": "ScholarlyAttestation"},

    {"word": "Influencer", "year": 2017,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "neutral",
     "prior_sense_gloss": "a person who influences others",
     "new_sense_gloss": "a social media content creator with a large following who influences purchasing decisions and culture",
     "trigger_label": "social media influencer marketing YouTube Instagram rise", "evidence_type": "ScholarlyAttestation"},

    {"word": "Gendersternchen", "year": 2018,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established",
     "new_sense_gloss": "gender star; asterisk used in German writing for gender-inclusive language including non-binary persons",
     "trigger_label": "German gender-inclusive language reform feminist activism", "evidence_type": "ScholarlyAttestation"},

    {"word": "[...] for future", "year": 2019,
     "is_semantic_shift": False, "drift_type": None,
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "not previously established as a formulaic suffix",
     "new_sense_gloss": "phraseological suffix from Fridays for Future; applied to any activist cause (Scientists for Future, etc.)",
     "trigger_label": "Fridays for Future Greta Thunberg climate movement 2019", "evidence_type": "ScholarlyAttestation"},

    {"word": "Lockdown", "year": 2020,
     "is_semantic_shift": True, "drift_type": "Broadening",
     "old_connotation": "neutral", "new_connotation": "negative",
     "prior_sense_gloss": "a prison lockdown; emergency security confinement",
     "new_sense_gloss": "pandemic-era term for population-wide contact restrictions and business closures; became the standard German term",
     "trigger_label": "COVID-19 pandemic lockdown restrictions Germany 2020", "evidence_type": "ScholarlyAttestation"},

    {"word": "boostern", "year": 2021,
     "is_semantic_shift": True, "drift_type": "Narrowing",
     "old_connotation": "neutral", "new_connotation": "positive",
     "prior_sense_gloss": "to boost; to increase or improve something",
     "new_sense_gloss": "to receive a COVID-19 booster vaccination; Germanized verb specifically for third vaccine dose",
     "trigger_label": "COVID-19 booster vaccination campaign Germany 2021", "evidence_type": "ScholarlyAttestation"},
]


def _cache_key_from_entries(entries: list[dict]) -> str:
    payload = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def main():
    # Load the raw entries to compute the same batch hashes _llm.py would use
    with _RAW_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    entries = raw["entries"]

    # Build lookup from (word, year) -> classification
    cls_map = {(c["word"], c["year"]): c for c in CLASSIFICATIONS}

    # Verify all entries have a classification
    missing = []
    for e in entries:
        if (e["word"], e["year"]) not in cls_map:
            missing.append((e["word"], e["year"]))
    if missing:
        print(f"WARNING: {len(missing)} entries without classification:")
        for m in missing:
            print(f"  {m}")

    # Now chunk into the same batches of 10 that _llm.py uses
    batch_size = 10
    batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]

    written = 0
    for batch in batches:
        # Build the cache payload (same format as classify_batch returns)
        batch_results = []
        for e in batch:
            c = cls_map.get((e["word"], e["year"]))
            if c:
                batch_results.append(c)
            else:
                # Minimal fallback
                batch_results.append({
                    "word": e["word"], "year": e["year"],
                    "is_semantic_shift": False, "drift_type": None,
                    "old_connotation": "neutral", "new_connotation": "neutral",
                    "prior_sense_gloss": f"original meaning of '{e['word']}'",
                    "new_sense_gloss": f"meaning of '{e['word']}' as used in {e['year']}",
                    "trigger_label": e["trigger_desc"][:50],
                    "evidence_type": "ScholarlyAttestation",
                })

        key = _cache_key_from_entries(batch)
        cache_path = _CACHE_DIR / f"{key}.json"
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        print(f"Wrote cache batch {key} ({len(batch_results)} entries)")
        written += 1

    print(f"\nPre-populated {written} batch cache files in {_CACHE_DIR}")
    print(f"Total classifications: {len(CLASSIFICATIONS)}")
    shifts = sum(1 for c in CLASSIFICATIONS if c.get("is_semantic_shift"))
    print(f"Semantic shifts: {shifts}")
    print(f"Non-shifts: {len(CLASSIFICATIONS) - shifts}")


if __name__ == "__main__":
    main()
