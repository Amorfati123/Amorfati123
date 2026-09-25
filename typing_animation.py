"""Adds a terminal-style typing animation to the profile card SVGs.

Each line of the info panel gets a small "cover" block in the background color
with a cursor on its left edge. The cover slides right one character at a time,
which makes the line look like it's being typed out.

The covers sit just past the right edge of the card by default and only move over
the text while their animation runs. So if a viewer doesn't run CSS animations
(or asks for reduced motion), the card simply shows up fully drawn.
"""
from lxml.etree import SubElement

SVG_NS = "http://www.w3.org/2000/svg"

# Rough width of one character at 16px in the card's monospace font.
CHAR_WIDTH = 9.6
LINE_HEIGHT = 20
# Where the covers rest when they aren't animating: just outside the 985px card.
PARKED_X = 990

# Timing, in seconds.
PORTRAIT_FADE = 0.8
SECONDS_PER_CHAR = 0.006
PAUSE_BETWEEN_LINES = 0.04
CURSOR_BLINK = 1.0

TYPING_GROUP_ID = "typing"
TYPING_STYLE_ID = "typing_style"


def tag(name):
    return f"{{{SVG_NS}}}{name}"


# Pull the text lines out of the info panel. A line starts at every tspan that has
# its own x/y position, and runs until the next one.
def panel_lines(panel):
    lines = []
    for child in panel:
        if child.get("y") is not None:
            lines.append({"x": float(child.get("x")), "y": float(child.get("y")), "text": ""})
        if not lines:
            continue
        lines[-1]["text"] += "".join(child.itertext()) + (child.tail or "")
    for line in lines:
        line["chars"] = len(line["text"].split("\n")[0].rstrip())
    return lines


# Remove whatever an earlier run added, so running this again doesn't stack animations.
def remove_old_animation(root):
    for element_id in (TYPING_GROUP_ID, TYPING_STYLE_ID):
        for element in root.findall(f".//*[@id='{element_id}']"):
            element.getparent().remove(element)


def add_typing_animation(root):
    remove_old_animation(root)

    background = root.find(tag("rect")).get("fill")
    texts = root.findall(tag("text"))
    portrait, panel = texts[0], texts[-1]
    cursor_color = panel.get("fill")
    lines = panel_lines(panel)
    if not lines:
        return

    # The portrait fades in first, then the panel types itself out line by line.
    portrait.set("class", "ascii")
    css = [
        "@keyframes fade_in {from {opacity: 0;} to {opacity: 1;}}",
        "@keyframes blink {0%, 49% {opacity: 0;} 50%, 100% {opacity: 1;}}",
        "@keyframes show {from, to {opacity: 1;}}",
        f".ascii {{animation: fade_in {PORTRAIT_FADE}s ease-out backwards;}}",
    ]

    group = SubElement(root, tag("g"), id=TYPING_GROUP_ID)
    start = PORTRAIT_FADE
    for index, line in enumerate(lines):
        chars = max(line["chars"], 1)
        duration = chars * SECONDS_PER_CHAR
        # Slide from the start of the line to just past its last character.
        start_shift = line["x"] - PARKED_X
        end_shift = start_shift + chars * CHAR_WIDTH

        css.append(
            f"@keyframes type_{index} {{"
            f"from {{transform: translateX({start_shift:.1f}px);}} "
            f"to {{transform: translateX({end_shift:.1f}px);}}}}"
        )
        css.append(
            f".line_{index} {{animation: type_{index} {duration:.2f}s steps({chars}) "
            f"{start:.2f}s backwards;}}"
        )
        # The cursor is hidden by default and only shows while its own line is typing,
        # otherwise every line still waiting its turn would have a cursor sitting on it.
        css.append(f".line_{index} .caret {{animation: show {duration:.2f}s {start:.2f}s;}}")

        cover = SubElement(group, tag("g"), attrib={"class": f"line_{index}"})
        top = line["y"] - 16
        SubElement(cover, tag("rect"), x=str(PARKED_X), y=f"{top:g}",
                   width="620", height=str(LINE_HEIGHT), fill=background)
        SubElement(cover, tag("rect"), attrib={
            "class": "caret", "x": str(PARKED_X), "y": f"{top + 2:g}",
            "width": "9", "height": "17", "fill": cursor_color, "opacity": "0",
        })
        start += duration + PAUSE_BETWEEN_LINES

    # Once everything is typed, leave a blinking cursor after the last line.
    last = lines[-1]
    cursor_x = last["x"] + (last["chars"] + 1) * CHAR_WIDTH
    SubElement(group, tag("rect"), attrib={
        "class": "cursor",
        "x": f"{cursor_x:.1f}",
        "y": f"{last['y'] - 14:g}",
        "width": "9",
        "height": "17",
        "fill": cursor_color,
    })
    css.append(f".cursor {{animation: blink {CURSOR_BLINK}s step-end {start:.2f}s infinite backwards;}}")

    # Anyone who prefers less motion gets the finished card straight away.
    css.append(
        "@media (prefers-reduced-motion: reduce) {"
        f".ascii, #{TYPING_GROUP_ID} * {{animation: none;}}}}"
    )

    style = SubElement(root, tag("style"), id=TYPING_STYLE_ID)
    style.text = "\n" + "\n".join(css) + "\n"
    # Keep the style block near the top of the file where the other styles live.
    root.remove(style)
    root.insert(1, style)
    style.tail = "\n"
    group.tail = "\n"


if __name__ == "__main__":
    # Lets you apply the animation by hand: python typing_animation.py
    from lxml.etree import parse

    for filename in ("dark_mode.svg", "light_mode.svg"):
        tree = parse(filename)
        add_typing_animation(tree.getroot())
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"Added typing animation to {filename}")
