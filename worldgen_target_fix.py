from __future__ import annotations


_APPLIED = False


def _fixed_next_undercovered_teleport_index(
    config,
    teleport_points,
    *,
    start_index,
    world_path,
    blank_coverage=None,
):
    import worldgen.generator as generator

    if not teleport_points:
        return 0

    normalized_start_index = start_index % len(teleport_points)

    if blank_coverage is not None:
        fallback_index = None
        for offset in range(len(teleport_points)):
            index = (normalized_start_index + offset) % len(teleport_points)
            point = teleport_points[index]
            missing_pixels = generator._teleport_point_missing_pixel_count(
                config,
                point,
                blank_coverage,
            )
            if missing_pixels > generator.TELEPORT_TARGET_MIN_ACTIONABLE_BLANK_PIXELS:
                return index
            if missing_pixels > 0 and fallback_index is None:
                fallback_index = index
        return normalized_start_index if fallback_index is None else fallback_index

    if world_path is None or not world_path.exists():
        return normalized_start_index

    saved_columns = generator._saved_render_chunk_columns(config, world_path)
    if not saved_columns:
        return normalized_start_index

    for offset in range(len(teleport_points)):
        index = (normalized_start_index + offset) % len(teleport_points)
        point = teleport_points[index]
        if generator._teleport_point_missing_chunk_count(config, point, saved_columns) > 0:
            return index

    return normalized_start_index


def apply() -> None:
    global _APPLIED
    if _APPLIED:
        return

    import worldgen.generator as generator
    generator._next_undercovered_teleport_index = _fixed_next_undercovered_teleport_index

    _APPLIED = True
