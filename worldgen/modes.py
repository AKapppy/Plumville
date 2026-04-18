from __future__ import annotations

from dataclasses import dataclass


LOCAL_SEED_SURFACE = 'local_seed_surface'
LAN_SURFACE = 'lan_surface'
LAN_Y40 = 'lan_y40'
DEFAULT_WORLDGEN_MODE = LOCAL_SEED_SURFACE


@dataclass(frozen=True, slots=True)
class WorldgenMode:
    key: str
    label: str
    source: str
    fixed_y: int | None = None

    @property
    def is_lan(self) -> bool:
        return self.source == 'lan'


WORLDGEN_MODES: dict[str, WorldgenMode] = {
    LOCAL_SEED_SURFACE: WorldgenMode(
        key=LOCAL_SEED_SURFACE,
        label='Local Worldgen',
        source='local_seed',
    ),
    LAN_SURFACE: WorldgenMode(
        key=LAN_SURFACE,
        label='LAN Surface',
        source='lan',
    ),
    LAN_Y40: WorldgenMode(
        key=LAN_Y40,
        label='LAN Y=40',
        source='lan',
        fixed_y=40,
    ),
}

WORLDGEN_MODE_LABELS: dict[str, str] = {
    mode.key: mode.label for mode in WORLDGEN_MODES.values()
}
WORLDGEN_MODE_KEYS_BY_LABEL: dict[str, str] = {
    mode.label: mode.key for mode in WORLDGEN_MODES.values()
}


def worldgen_mode(mode_key: str | None) -> WorldgenMode:
    if mode_key in WORLDGEN_MODES:
        return WORLDGEN_MODES[mode_key]
    return WORLDGEN_MODES[DEFAULT_WORLDGEN_MODE]


def worldgen_mode_key_for_label(label: str | None) -> str:
    if label in WORLDGEN_MODE_KEYS_BY_LABEL:
        return WORLDGEN_MODE_KEYS_BY_LABEL[label]
    return DEFAULT_WORLDGEN_MODE
