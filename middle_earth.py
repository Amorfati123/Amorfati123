"""Lord of the Rings touches for the profile card.

Road to Mordor: this year's commits drawn as Frodo's journey from the Shire to
Mount Doom, with the landmark you've reached so far. It starts over every January.

The Ring inscription: once the card finishes typing, the One Ring's inscription
heats up along the bottom of the card and flickers like it's sitting in the fire.
"""
import datetime

from lxml.etree import SubElement

SVG_NS = "http://www.w3.org/2000/svg"

# How many commits in a year count as reaching Mount Doom. Roughly one a day.
QUEST_GOAL = 365
BAR_WIDTH = 39
QUEST_COUNT_WIDTH = 17
QUEST_PLACE_WIDTH = 15

# Rough spots along the Fellowship's (and then Frodo's) route, by share of the journey.
LANDMARKS = (
    (0.00, "Bag End"),
    (0.06, "Bree"),
    (0.12, "Weathertop"),
    (0.20, "Rivendell"),
    (0.33, "Moria"),
    (0.40, "Lothlórien"),
    (0.52, "Amon Hen"),
    (0.66, "Dead Marshes"),
    (0.78, "Cirith Ungol"),
    (0.90, "Mordor"),
    (1.00, "Mount Doom!"),
)

RING_INSCRIPTION = (
    "Ash nazg durbatulûk, ash nazg gimbatul, "
    "ash nazg thrakatulûk, agh burzum-ishi krimpatul."
)
RING_Y = 637
RING_HEAT_UP = 3.0
RING_FLICKER = 2.6
RING_ID = "ring_inscription"
RING_STYLE_ID = "ring_style"
RING_DEFS_ID = "ring_defs"

COMMITS_THIS_YEAR_QUERY = """
query ($login: String!, $from: DateTime!) {
    user(login: $login) {
        contributionsCollection(from: $from) {
            totalCommitContributions
        }
    }
}"""


def tag(name):
    return f"{{{SVG_NS}}}{name}"


def commits_this_year(graphql_request, login, today=None):
    today = today or datetime.date.today()
    data = graphql_request(
        "commits_this_year",
        COMMITS_THIS_YEAR_QUERY,
        {"login": login, "from": f"{today.year}-01-01T00:00:00Z"},
    )
    return data["user"]["contributionsCollection"]["totalCommitContributions"]


def quest_progress(commits, goal=QUEST_GOAL):
    return max(0.0, min(1.0, commits / goal))


def quest_bar(commits, goal=QUEST_GOAL, width=BAR_WIDTH):
    done = round(quest_progress(commits, goal) * width)
    return "█" * done, "░" * (width - done)


def quest_place(commits, goal=QUEST_GOAL):
    progress = quest_progress(commits, goal)
    reached = [name for share, name in LANDMARKS if progress >= share]
    return reached[-1]


# Fill in the Road to Mordor lines. justify_format comes from today.py so the dot
# padding here works exactly like the rest of the card.
def update_quest(root, commits, justify_format, find_and_replace, today=None, goal=QUEST_GOAL):
    today = today or datetime.date.today()
    done, left = quest_bar(commits, goal)
    find_and_replace(root, "quest_done", done)
    find_and_replace(root, "quest_left", left)
    find_and_replace(root, "quest_year", str(today.year))
    justify_format(root, "quest_count", f"{commits}/{goal}", QUEST_COUNT_WIDTH)
    justify_format(root, "quest_place", quest_place(commits, goal), QUEST_PLACE_WIDTH)


def remove_old_ring(root):
    for element_id in (RING_ID, RING_STYLE_ID, RING_DEFS_ID):
        for element in root.findall(f".//*[@id='{element_id}']"):
            element.getparent().remove(element)


def is_dark(color):
    color = color.lstrip("#")
    red, green, blue = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return (red * 299 + green * 587 + blue * 114) / 1000 < 128


# Add the inscription along the bottom of the card. start is when the typing finishes.
def add_ring_inscription(root, start):
    remove_old_ring(root)

    background = root.find(tag("rect")).get("fill")
    if is_dark(background):
        colors = ("#ff4d00", "#ffb000", "#ff4d00")
        glow = "2.2"
    else:
        colors = ("#c2410c", "#e8590c", "#b91c1c")
        glow = "1.2"

    width = float(root.get("width").replace("px", ""))

    defs = SubElement(root, tag("defs"), id=RING_DEFS_ID)
    gradient = SubElement(defs, tag("linearGradient"), id="ring_fire", x1="0", y1="0", x2="1", y2="0")
    for offset, color in zip(("0", "0.5", "1"), colors):
        SubElement(gradient, tag("stop"), offset=offset, attrib={"stop-color": color})
    glow_filter = SubElement(defs, tag("filter"), id="ring_glow", x="-5%", y="-80%", width="110%", height="260%")
    SubElement(glow_filter, tag("feGaussianBlur"), stdDeviation=glow, result="blur")
    merge = SubElement(glow_filter, tag("feMerge"))
    SubElement(merge, tag("feMergeNode"), attrib={"in": "blur"})
    SubElement(merge, tag("feMergeNode"), attrib={"in": "SourceGraphic"})

    # Two layers: the outer group heats up once, the text inside keeps flickering after.
    group = SubElement(root, tag("g"), attrib={"class": "ring_heat"})
    text = SubElement(group, tag("text"), attrib={
        "id": RING_ID,
        "class": "ring_flicker",
        "x": f"{width / 2:g}",
        "y": str(RING_Y),
        "text-anchor": "middle",
        "font-family": "Georgia, 'Times New Roman', serif",
        "font-style": "italic",
        "font-size": "17px",
        "letter-spacing": "0.5",
        "fill": "url(#ring_fire)",
        "filter": "url(#ring_glow)",
    })
    text.text = RING_INSCRIPTION

    style = SubElement(root, tag("style"), id=RING_STYLE_ID)
    style.text = "\n".join((
        "",
        "@keyframes ring_heat {from {opacity: 0;} to {opacity: 1;}}",
        "@keyframes ring_flicker {0%, 100% {opacity: 1;} 30% {opacity: 0.72;} 55% {opacity: 0.95;} 75% {opacity: 0.8;}}",
        f".ring_heat {{animation: ring_heat {RING_HEAT_UP}s ease-in {start:.2f}s backwards;}}",
        f".ring_flicker {{animation: ring_flicker {RING_FLICKER}s ease-in-out "
        f"{start + RING_HEAT_UP:.2f}s infinite;}}",
        "@media (prefers-reduced-motion: reduce) {.ring_heat, .ring_flicker {animation: none;}}",
        "",
    ))
    root.remove(style)
    root.insert(1, style)
    style.tail = "\n"
    defs.tail = "\n"
    group.tail = "\n"
