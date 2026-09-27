"""Parse and resubmit Indico's server-rendered WTForms.

Indico's management dialogs return a form as HTML (usually wrapped in JSON).
Posting only the fields we want to change is unsafe: WTForms treats an
omitted checkbox as False and some widgets as empty. So every edit here reads
the form first, keeps what a browser would submit, then overrides the fields
the caller asked to change.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

_SKIPPED_INPUT_TYPES = {"submit", "button", "reset", "image", "file"}

FormValue = str | list[str]


@dataclass
class ParsedForm:
    """Field values in submission order, plus any validation errors shown."""

    fields: list[tuple[str, str]] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    #: every field name in the form, including unchecked checkboxes and radios
    known: set[str] = field(default_factory=set)

    def get(self, name: str) -> list[str]:
        return [value for key, value in self.fields if key == name]

    def merged(self, overrides: Mapping[str, FormValue]) -> list[tuple[str, str]]:
        """Return the fields with `overrides` replacing existing values.

        A list value submits the key several times (Indico's datetime fields
        expect the date and the time as two values under one name). Override
        keys missing from the form are appended at the end.
        """
        result: list[tuple[str, str]] = []
        done: set[str] = set()
        for name, value in self.fields:
            if name not in overrides:
                result.append((name, value))
            elif name not in done:
                result.extend(_expand(name, overrides[name]))
                done.add(name)
        for name, value in overrides.items():
            if name not in done:
                result.extend(_expand(name, value))
        return result


def _expand(name: str, value: FormValue) -> list[tuple[str, str]]:
    if isinstance(value, list):
        return [(name, v) for v in value]
    return [(name, value)]


def parse_form(html: str) -> ParsedForm:
    """Extract what a browser would submit from the first form in `html`.

    If there is no <form> element (some dialogs render bare fields), the whole
    document is scanned.
    """
    soup = BeautifulSoup(html, "html.parser")
    root: Tag = soup.find("form") or soup
    parsed = ParsedForm()

    for element in root.find_all(["input", "textarea", "select"]):
        name = element.get("name")
        if not name or element.has_attr("disabled"):
            continue
        parsed.known.add(name)
        if element.name == "textarea":
            parsed.fields.append((name, element.get_text()))
        elif element.name == "select":
            parsed.fields.extend((name, v) for v in _selected_options(element))
        else:
            input_type = (element.get("type") or "text").lower()
            if input_type in _SKIPPED_INPUT_TYPES:
                parsed.known.discard(name)
                continue
            if input_type in {"checkbox", "radio"}:
                if element.has_attr("checked"):
                    parsed.fields.append((name, element.get("value", "on")))
                continue
            parsed.fields.append((name, element.get("value", "")))

    for wrapper in root.select("[data-error]"):
        message = BeautifulSoup(wrapper["data-error"], "html.parser").get_text(" ", strip=True)
        target = wrapper.find(["input", "textarea", "select"], attrs={"name": True})
        parsed.errors[target["name"] if target else f"field{len(parsed.errors)}"] = message
    return parsed


def _selected_options(select: Tag) -> Iterable[str]:
    options = select.find_all("option")
    selected = [o for o in options if o.has_attr("selected")]
    if not selected and options and not select.has_attr("multiple"):
        selected = options[:1]
    return [o.get("value", o.get_text()) for o in selected]
