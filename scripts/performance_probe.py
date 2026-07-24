from __future__ import annotations

import argparse
import gc
import importlib
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]


def _time_call(callback: Callable[[], Any], *, repeat: int) -> tuple[float, Any]:
    samples: list[float] = []
    result: Any = None
    for _index in range(repeat):
        gc.collect()
        started = time.perf_counter()
        result = callback()
        samples.append(time.perf_counter() - started)
    return statistics.median(samples), result


def _record(
    rows: list[dict[str, object]],
    name: str,
    callback: Callable[[], Any],
    *,
    repeat: int,
    details: dict[str, object] | None = None,
) -> Any:
    elapsed, result = _time_call(callback, repeat=repeat)
    rows.append(
        {
            "name": name,
            "median_ms": round(elapsed * 1000, 3),
            "repeat": repeat,
            "details": details or {},
        }
    )
    return result


def _route_target(base: Any) -> str:
    costs = base._route_costs_from_endpoint_key(
        base.BLACKPORT_VAR,
        allow_connector=True,
        allow_walk=False,
    )
    if not costs:
        return next(stop.var for stop in base.METRO_STOPS if stop.var != base.BLACKPORT_VAR)
    return max(costs.items(), key=lambda item: item[1][0])[0]


def run_probe(*, repeat: int) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    sys.path.insert(0, str(REPO_ROOT))

    base = _record(rows, "desktop_import_legacy_core", lambda: importlib.import_module("legacy_core"), repeat=1)
    _record(rows, "network_payload_load", base._load_network_payload, repeat=repeat)

    graph = _record(
        rows,
        "route_graph_open_metro",
        lambda: base._build_route_graph(allow_connector=True, allow_walk=False, include_planned_metro=False),
        repeat=repeat,
    )
    target = _route_target(base)
    _record(
        rows,
        "route_blackport_to_farthest_reachable",
        lambda: base._find_route(base.BLACKPORT_VAR, target, allow_connector=True, allow_walk=False, allow_flying=False),
        repeat=repeat,
        details={"target": target},
    )
    _record(
        rows,
        "route_costs_from_blackport",
        lambda: base._route_costs_from_endpoint_key(base.BLACKPORT_VAR, allow_connector=True, allow_walk=False),
        repeat=repeat,
    )
    _record(rows, "plot_transform", base._plot_transform, repeat=repeat)

    worldgen_config = importlib.import_module("worldgen.config")
    worldgen_generator = importlib.import_module("worldgen.generator")
    worldgen_render = importlib.import_module("worldgen.render")
    config = _record(rows, "worldgen_config_load", worldgen_config.load_config, repeat=repeat)
    _record(
        rows,
        "worldgen_render_plan_build",
        lambda: worldgen_render.build_render_plan(config),
        repeat=repeat,
    )
    _record(
        rows,
        "worldgen_target_planning",
        lambda: worldgen_generator._render_area_teleport_points(config),
        repeat=repeat,
    )

    docs_network_path = REPO_ROOT / "docs" / "metro_network.json"
    docs_app_path = REPO_ROOT / "docs" / "app.js"
    terrain_path = REPO_ROOT / "docs" / "assets" / "blackport_topdown.png"
    terrain_metadata_path = REPO_ROOT / "docs" / "assets" / "blackport_topdown.render.json"
    _record(rows, "web_network_json_parse", lambda: json.loads(docs_network_path.read_text(encoding="utf-8")), repeat=repeat)
    _record(rows, "web_app_js_read", lambda: docs_app_path.read_text(encoding="utf-8"), repeat=repeat)
    _record(rows, "terrain_metadata_parse", lambda: json.loads(terrain_metadata_path.read_text(encoding="utf-8")), repeat=repeat)

    def copy_public_asset() -> None:
        with tempfile.TemporaryDirectory(prefix="plumville-probe-") as temp_dir:
            destination = Path(temp_dir) / terrain_path.name
            worldgen_generator._copy_file_best_effort(terrain_path, destination)

    _record(rows, "public_asset_copy_png_to_temp", copy_public_asset, repeat=repeat)

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repeat": repeat,
        "route_graph_nodes": len(graph),
        "route_graph_edges": sum(len(edges) for edges in graph.values()),
        "measurements": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opt-in Plumville architecture audit performance probes.")
    parser.add_argument("--repeat", type=int, default=5, help="Median sample count for short probes.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown table.")
    parser.add_argument("--output", type=Path, help="Write probe results to a local JSON baseline file.")
    args = parser.parse_args()

    result = run_probe(repeat=max(1, args.repeat))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print("| Probe | Median ms | Repeat | Details |")
    print("| --- | ---: | ---: | --- |")
    for row in result["measurements"]:
        details = row["details"]
        detail_text = json.dumps(details, sort_keys=True) if details else ""
        print(f"| {row['name']} | {row['median_ms']} | {row['repeat']} | {detail_text} |")
    print()
    print(f"Route graph: {result['route_graph_nodes']} nodes, {result['route_graph_edges']} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
