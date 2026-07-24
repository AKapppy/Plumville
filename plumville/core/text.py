from __future__ import annotations

import re

SUBSCRIPT_TRANSLATION: dict[int, int] = str.maketrans("0123456789-", "₀₁₂₃₄₅₆₇₈₉₋")


def display_label(label: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)_\{?([0-9-]+)\}?", label)
    if not match:
        return label
    return f"{match.group(1)}{match.group(2).translate(SUBSCRIPT_TRANSLATION)}"


def is_placeholder_station_label(label: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9_{}]+", label.strip()))


def normalize_stop_identity(text: str) -> str:
    return "".join(char for char in text.upper() if char.isalnum())


def normalize_line_color(color_text: str) -> str:
    normalized = color_text.strip()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    if re.fullmatch(r"#[0-9a-fA-F]{3}", normalized):
        return "#" + "".join(char * 2 for char in normalized[1:]).lower()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", normalized):
        return normalized.lower()
    raise ValueError("Line color must be a hex color like #2f80ed.")


def normalize_line_name(line_name: str) -> str:
    normalized = line_name.strip().upper()
    if not re.fullmatch(r"[A-Z]", normalized):
        raise ValueError("Line names must be a single letter.")
    return normalized
