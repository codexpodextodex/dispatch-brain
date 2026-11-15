"""Reads a dealer's note, in Finnish, Swedish or English, for the facts that change how a car can move.

The world acts on what the note says whether or not we read it, so a missed fact is a failed visit or a late
car. The reader works in four steps:

1. repair typos: a word one letter away from a word we know becomes that word ("vamis" -> "valmis");
2. split the note into clauses;
3. find the times in each clause;
4. let the words around a time say what it is: when the car is ready, when a site closes, or when the car
   must be there.

lab/notes_score.py measures the reader against what the reveal says each note meant.

How days and times read is in the rules: a time without a day is on the day the request arrives; a weekday
name is that weekday 2 to 6 days later; digits are a 24-hour clock unless am or pm follows; an hour in words
is a working hour from 9 to 17, so "two" is 14:00, and "half three" is 14:30. A correction counts ("21, ei
kun 20"), and a time that the note denies ("not 9:30") does not."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

HOUR, DAY = 60, 24 * 60


@dataclass
class Facts:
    plates: bool = False  # the car has no plates: the pickup needs `withPlates`
    manual: bool = False  # only a driver with a manual licence can drive it
    summer_tyres: bool = False  # it cannot be collected or delivered while snow falls there
    pickup_from: Optional[int] = None  # world minute: not ready, or not handed over, before
    pickup_opens: Optional[int] = None  # minute of the day: the pickup site's real hours
    pickup_closes: Optional[int] = None
    delivery_opens: Optional[int] = None
    delivery_closes: Optional[int] = None
    deadline: Optional[int] = None  # world minute: must be at the destination by


# Step 1. The words that carry meaning, and a few harmless words that look like them. A word of five letters
# or more that is one edit away from one of these (two edits for ten letters or more) is read as that word.
VOCABULARY = """
huomenna ylihuomenna tänään tomorrow today imorgon morgon övermorgon
maanantai maanantaina tiistai tiistaina keskiviikko keskiviikkona torstai torstaina perjantai perjantaina lauantai lauantaina
måndag tisdag onsdag torsdag fredag lördag monday tuesday wednesday thursday friday saturday
valmis valmiina noudettavissa haettavissa noutaa nouto noudon haettava alkaen aikaisintaan luovutus luovutetaan maksun maksettu maksaa
ready payment released pickup collect before after earliest latest until workshop available
klar först tidigast betalning hämtas hämtning framåt klockan
viimeistään mennessä perillä toimitus kohde kohteen vastaanotto vastaanottava destination receiving delivery
framme senast mottagning mottagaren leverans
kiinni sulkee sulkeutuu aukioloajat arkisin arkipäivisin closes closed opening weekdays vardagar stänger öppet öppettider nobody
kesärenkailla kesärenkaat kesäkumit talvirenkaita talvirenkaat summer winter tyres winters sommardäck vinterdäck fitted
manuaali manuaalia manuaalivaihteinen manuaalivaihteet käsivaihteet käsivaihteinen manual automatic automaatti manuell
kilvet kilpiä siirtokilvet koekilvet rekisterikilvet rekkareita rekisteristä plates
yhdeksältä kymmeneltä yhdeltätoista kahdeltatoista yhdeltä kahdelta kolmelta neljältä viideltä
yhdeksästä kymmenestä yhdestätoista kahdestatoista yhdestä kahdesta kolmesta neljästä viidestä
yhdeksään kymmeneen yhteentoista kahteentoista yhteen kahteen kolmeen neljään viiteen
yhdeksää kymmentä kolmea neljää viittä kahta kahden kolmen neljän viiden yhden puoli puolta
correction korjaus rättelse sorry skyltar
plats rekisteriote huoltokirja kiitos thanks avaimet nyckeln please
""".split()
BY_LENGTH: dict[int, list[str]] = {}
for _word in VOCABULARY:
    BY_LENGTH.setdefault(len(_word), []).append(_word)
KNOWN = set(VOCABULARY)


def edits(a: str, b: str, limit: int) -> int:
    """Edit distance between two words, where swapping two neighbouring letters is one edit; stops above `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    before, row = None, list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            cost = min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (x != y))
            if before is not None and i > 1 and j > 1 and x == b[j - 2] and a[i - 2] == y:
                cost = min(cost, before[j - 2] + 1)
            new.append(cost)
        before, row = row, new
        if min(row) > limit:
            return limit + 1
    return row[-1]


REPAIRED: dict[str, str] = {}  # a word we have repaired once: notes use few words, and comparing one with the whole vocabulary is slow


def repair(text: str) -> str:
    def fix(match: re.Match) -> str:
        word = match.group(0)
        if word in KNOWN or len(word) < 5:
            return word
        if word not in REPAIRED:
            limit = 2 if len(word) >= 10 else 1
            near = sorted((edits(word, known, limit), known) for n in range(len(word) - limit, len(word) + limit + 1) for known in BY_LENGTH.get(n, ()))
            near = [(distance, known) for distance, known in near if distance <= limit]
            REPAIRED[word] = near[0][1] if near and (len(near) == 1 or near[0][0] < near[1][0]) else word  # the nearest word, unless two are as near
        return REPAIRED[word]
    return re.sub(r"[a-zåäö]+", fix, text)


# Step 4. What the words around a time say.
PLATES = re.compile(r"kilv|kilpi|kilpe|rekkar|rekisterist|plates\b|\bplate\b|skylt|avst[aä]ll|unregist")
MANUAL = re.compile(r"manuaal|k[aä]sivaih|manual|manuell|stick\s?shift|ei automaatti|not (?:an )?automatic|inte automat")
NOT_MANUAL = re.compile(r"not (?:a )?manual|ei manuaal|inte manuell")
TYRES_ON = re.compile(r"kes[aä](?:renk|kumi)\w*\s+alla|kes[aä]renkailla|sommard[aä]ck\s+p[aå]|summers?\s+(?:tyres?\s+)?(?:still\s+)?on\b|on\s+summer|"
                      r"talvirenk\w*\s+ei|ei\s+talvirenk|no\s+winters?|winter\s+tyres?\s+not|inga\s+vinterd")
DELIVERY = re.compile(r"kohde|kohtee|perill|vastaanot|toimit|destination|receiv|deliver|arriv|mottag|framme|levere|p[aå] plats")
PICKUP = re.compile(r"nou[dt]|haett|haku|hake|hae\b|liike|pick\s?up|collect|shop|t[aä][aä]ll[aä]|\bhere\b|h[aä]mt|butik|\bvi\b|\bwe\b|\bme\b")
READY = re.compile(r"valmi|noudettavis|haettavis|voi noutaa|voi hakea|alkaen|aikaisint|ei ennen|ready|not before|available|earliest|maksu|makset|maksaa|payment|pays?\b|"
                   r"\bfrom\s+(?:\d|tom|tod|mon|tue|wed|thu|fri|noon|the day)|luovut|l[aä]mnas|released?|\bsaa\b|klar|f[oö]rst|tidigast|inte f[oö]re|betal|fram[aå]t|"
                   r"kan h[aä]mtas|workshop|huolto|korjaamo|pesu|kesken")
CLOSES = re.compile(r"kiinni|sulke|sulje|close|shut|until|\btill\b|asti|saakka|st[aä]ng|ei ket[aä][aä]n|nobody|no one|ingen")
OPENS = re.compile(r"aukeaa|avataan|\bopens\b|[oö]ppnar")
HOURS = re.compile(r"auki|aukiolo|open|only|[oö]ppet|arkisin|arkip[aä]iv|weekdays|vardagar|mon\S?fri|ma\S?pe|m[aå]n\S?fre|onnistuu")
BY = re.compile(r"viim|menness|latest|\bby\b|senast|must be|oltava|pit[aä][aä]|before|ennen|f[oö]re|innan")
BACK = re.compile(r"ennen sit[aä]|before (?:that|then)|innan dess|sit[aä] ennen")  # points back at the clause before
CORRECTION = re.compile(r"\bcorrection\b:?|\bkorjaus\b:?|\br[aä]ttelse\b:?|,?\s*\bsorry\b,?(?:\s*i mean)?|,?\s*\bi mean\b|,?\s*\bei\s?kun\b|,?\s*\beiku\b|,?\s*\bor rather\b")

TODAY = re.compile(r"t[aä]n[aä][aä]n|\bidag\b|\btoday\b")
TOMORROW = re.compile(r"\bhuomen\w*|\bi\s?morgon\b|\btomorrow\b|\btmrw\b|\btmr\b|\btmw\b")
DAY_AFTER = re.compile(r"ylihuomen\w*|i\s?[oö]vermorgon|(?:the )?day after tomorrow")
WEEKDAY = [re.compile(pattern) for pattern in (
    r"maanantai\w*|\bma\b|m[aå]ndag\w*|\bm[aå]n\b|monday|\bmon\b",
    r"tiistai\w*|\bti\b|tisdag\w*|\btis\b|tuesday|\btues?\b",
    r"keskiviik\w*|\bke\b|onsdag\w*|\bons\b|wednesday|\bweds?\b",
    r"torstai\w*|\bto\b(?=\s+(?:klo|kello|\d|puol))|torsdag\w*|\btors?\b|thursday|\bthu(?:rs?)?\b",
    r"perjantai\w*|\bpe\b|fredag\w*|\bfre\b|friday|\bfri\b",
    r"lauantai\w*|\bla\b|l[oö]rdag\w*|\bl[oö]r\b|saturday|\bsat\b",
    r"sunnuntai\w*|\bsu\b|s[oö]ndag\w*|\bs[oö]n\b|sunday|\bsun\b",
)]
ANY_DAY = "|".join([TODAY.pattern, TOMORROW.pattern, DAY_AFTER.pattern] + [w.pattern for w in WEEKDAY])
DENIED_DAY = re.compile(rf"(?:\bnot|\bei|\binte)\s+(?:{ANY_DAY})")

# Hours in words, by the hour they name: an hour in words is a working hour, 9 to 17. Longer words first.
WORD_HOURS = {
    11: r"(?:yksi|yhde\w*|yht\w*)toista|elva|eleven", 12: r"(?:kaksi|kahde\w*|kaht\w*)toista|tolv|twelve|noon|keskip[aä]iv\w*",
    9: r"yhdeks\w*|nio|nine", 10: r"kymmen\w*|tio|ten",
    13: r"yksi|yhden|yht[aä]|yhteen|yhdelt[aä]|yhdest[aä]|ett|one", 14: r"kaksi|kahden|kahta|kahteen|kahdelta|kahdesta|tv[aå]|two",
    15: r"kolme\w*|tre|three", 16: r"nelj[aä]\w*|fyra|four", 17: r"viisi|viide\w*|viitt[aä]|viiteen|fem|five",
}
WORD = "|".join(f"(?P<w{hour}>{pattern})" for hour, pattern in WORD_HOURS.items())
PRE = r"klo|kello|klockan|kl|at|by|before|after|from|until|around|ennen|j[aä]lkeen|asti|vid|efter|f[oö]re|innan|till"
POST = r"\s+(?:j[aä]lkeen|asti|menness[aä]|saakka|alkaen|o.?clock)"
CLOCK = re.compile(
    rf"(?:\b(?P<pre>{PRE})\s*)?\b(?P<h>\d{{1,2}})(?:[.:](?P<m>\d{{2}})|(?P<m4>\d{{2}}))?(?P<fi>:?st[aä]|:?[aä][aä]n|:?een|:?lt[aä])?(?:\s*(?P<ap>am|pm))?\b(?P<post>{POST})?"
    rf"|(?:\b(?P<wpre>{PRE})\s+)?(?:(?P<half>puol\w*|halv|half(?:\s+past)?)\s+)?\b(?P<word>{WORD})\b(?P<wpost>{POST})?"
)
RANGE = re.compile(r"(?P<a>\d{1,2})(?:[.:](?P<am>\d{2}))?\s*(?P<aap>am|pm)?\s*(?:-|to|till|:?st[aä])\s*(?:klo\s*|kl\s*)?(?P<b>\d{1,2})(?:[.:](?P<bm>\d{2}))?\s*(?P<bap>am|pm)?(?::?[aä][aä]n|:?een)?")
NOT_A_TIME = re.compile(r"^\s*(?:min|tunti|tuntia|hours?|h\b|timme|sarja|set|reng|d[aä]ck|tyres?|wheels?|avain|key)")
FINNISH_CASE = re.compile(r"(?:lt[aä]|st[aä]|een|[aä][aä]n|aan|toista)$")
BEFORE_WORDS = ("before", "ennen", "före", "fore", "innan")
# A dot after these is no end of a sentence. After a short weekday it is one, unless a time follows: "pe. klo 16".
ABBREVIATIONS = re.compile(r"\b(viim|klo|kl|n|nro|esim|puh|tel|ref)\.|\b(to|ti|ke|ma|pe|la|su|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun|tors|tis|ons|fre)\.(?=\s*(?:klo|kello|kl|at|by|puol|\d))")
SHORT_DAY = [re.compile(rf"^\W*(?:{names})\W*$") for names in ("ma|mon|m[aå]n", "ti|tue|tues|tis", "ke|wed|ons", "to|thu|thur|thurs|tors?", "pe|fri|fre", "la|sat|l[oö]r", "su|sun|s[oö]n")]


def minutes(hour: int, minute: int, ampm: Optional[str]) -> Optional[int]:
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return hour * HOUR + minute if hour <= 24 and minute < 60 else None


def clock(match: re.Match) -> Optional[int]:
    """The minute of the day that a CLOCK match names; None when the match is a number or a word that is no time."""
    g = match.groupdict()
    if g["h"]:
        if not (g["pre"] or g["m"] or g["ap"] or g["fi"] or g["post"]) or (g["m4"] and not g["pre"]):
            return None  # a bare number: a bay, a count, a reference
        return minutes(int(g["h"]), int(g["m"] or g["m4"] or 0), g["ap"])
    for hour in WORD_HOURS:
        if g[f"w{hour}"]:
            if not (g["wpre"] or g["half"] or g["wpost"] or hour == 12 or FINNISH_CASE.search(g["word"])):
                return None  # "ett", "one", "two" as plain words
            return (hour - 1) * HOUR + 30 if g["half"] else hour * HOUR  # "half three" is 14:30
    return None


def day_offset(text: str, arrived: int) -> Optional[int]:
    """The days from the arrival day that a text names; None when it names no day."""
    if DAY_AFTER.search(text):
        return 2
    if TOMORROW.search(text):
        return 1
    if TODAY.search(text):
        return 0
    for weekday in range(7):  # that weekday, 2 to 6 days after the request arrives
        if WEEKDAY[weekday].search(text) or SHORT_DAY[weekday].match(text):
            return (weekday - arrived // DAY - 2) % 7 + 2
    return None


def times_in(text: str) -> list[int]:
    """The times that a text states. A time that it denies is left out: "not 9:30", "ei klo 12". "Not before 13" is no denial."""
    stated = []
    for match in CLOCK.finditer(text):
        time = clock(match)
        if time is None or NOT_A_TIME.match(text[match.end():]):
            continue
        denied = re.search(r"(?:\bnot|\bei|\binte)\s+$", text[: match.start()]) and (match["pre"] or match["wpre"]) not in BEFORE_WORDS
        if not denied:
            stated.append(time)
    return stated


def clauses(text: str) -> list[str]:
    text = ABBREVIATIONS.sub(lambda m: (m.group(1) or m.group(2)) + " ", text)
    text = re.sub(r"(\d)\.(\d{2})\b", r"\1:\2", text)  # 15.30 is a time, not the end of a sentence
    text = re.sub(r"[.!?;]+\s*(?=(?:correction|korjaus|r[aä]ttelse|sorry|i mean|ei\s?kun|eiku)\b)", " ", text)  # a correction belongs to its sentence
    return [c.strip() for c in re.split(r"[.!?;]+(?=\s|$)|\s/\s", text) if c.strip()]


def read(note: Optional[dict], arrived: int) -> Facts:
    facts = Facts()
    if not note or not note.get("text"):
        return facts
    text = repair(note["text"].lower().replace("–", "-").replace("—", "-"))
    facts.plates = bool(PLATES.search(text))
    facts.manual = bool(MANUAL.search(text)) and not NOT_MANUAL.search(text)
    facts.summer_tyres = bool(TYRES_ON.search(text))
    today = arrived // DAY * DAY
    last_site = "pickup"
    parts: list[tuple[str, list[str]]] = []  # each clause, with the corrections that follow it
    for sentence in clauses(text):
        sentence = DENIED_DAY.sub(" ", sentence)  # a day that the note denies: "not tomorrow"
        sentence, *corrections = CORRECTION.split(sentence)
        pieces = [piece for piece in sentence.split(",") if piece.strip()] or [sentence]
        timed = [i for i, piece in enumerate(pieces) if times_in(piece)]
        parts += [(piece, corrections if timed and i == timed[-1] else []) for i, piece in enumerate(pieces)]
    for clause, corrections in parts:
        site = "delivery" if DELIVERY.search(clause) else "pickup" if PICKUP.search(clause) else last_site if BACK.search(clause) else None
        span = RANGE.search(clause)
        if span and (HOURS.search(clause) or CLOSES.search(clause) or READY.search(clause) or site):  # hours as a range: "arkisin 7-16", "9am-4pm"
            opens = minutes(int(span["a"]), int(span["am"] or 0), span["aap"])
            closes = minutes(int(span["b"]), int(span["bm"] or 0), span["bap"])
            if opens is not None and closes is not None and opens < closes:
                setattr(facts, f"{site or 'pickup'}_opens", opens)
                setattr(facts, f"{site or 'pickup'}_closes", closes)
            clause = clause[: span.start()] + " " + clause[span.end():]
        times = times_in(clause)
        if times:
            time, day = times[-1], day_offset(clause, arrived) or 0  # a clause that states two times keeps the last
            for fix in corrections:  # "tomorrow 13:00, correction: 12:00", "huomenna klo 19, eikun torstaina"
                fixed_times, fixed_day = times_in(fix), day_offset(fix, arrived)
                time = fixed_times[-1] if fixed_times else time
                day = fixed_day if fixed_day is not None else day
            at = today + day * DAY + time
            if READY.search(clause) and not CLOSES.search(clause.replace("until", "")):
                facts.pickup_from = max(facts.pickup_from or 0, at)
                site = "pickup"
            elif CLOSES.search(clause) or (HOURS.search(clause) and not BY.search(clause)):
                setattr(facts, f"{site or 'pickup'}_{'opens' if OPENS.search(clause) else 'closes'}", time)
            elif site == "pickup" and BY.search(clause):  # "nouto ennen klo 14", "collect before 17:00"
                facts.pickup_closes = time
            elif site == "delivery" or BY.search(clause):
                facts.deadline = at
                site = "delivery"
        last_site = site or last_site
    return facts


def apply(leg: dict, facts: Facts) -> dict:
    """The leg as the note changes it: the car is ready later, and a site keeps shorter hours than it states.
    Drivers plan by the stated hours, so the real hours are the stated ones cut by the note."""
    def site(stop: dict, opens: Optional[int], closes: Optional[int]) -> dict:
        if stop["hours"] is None or (opens is None and closes is None):
            return stop
        hours = dict(stop["hours"])
        hours["opens"] = max(hours["opens"], opens) if opens is not None else hours["opens"]
        hours["closes"] = min(hours["closes"], closes) if closes is not None else hours["closes"]
        return {**stop, "hours": hours}

    pickup = site(leg["pickup"], facts.pickup_opens, facts.pickup_closes)
    if facts.pickup_from is not None and facts.pickup_from > pickup["window"]["from"]:
        pickup = {**pickup, "window": {"from": facts.pickup_from, "to": max(facts.pickup_from, pickup["window"]["to"])}}
    return {**leg, "pickup": pickup, "delivery": site(leg["delivery"], facts.delivery_opens, facts.delivery_closes)}
