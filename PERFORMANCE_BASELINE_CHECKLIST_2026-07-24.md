# Plumville Manual Performance Baseline Checklist

Use this file for local-only baseline notes. Do not publish it under `docs/`.

Automated baseline command:

```bash
python3 scripts/performance_probe.py --repeat 5 --output performance_baselines/local-$(date +%Y%m%d-%H%M%S).json
```

Manual timings to capture when the desktop app, browser, or live world is available:

- Desktop startup to first visible map:
- Desktop initial render after network load:
- Desktop pan at worst known zoom:
- Desktop zoom in/out at worst known zoom:
- Desktop station/path add dialog open:
- Desktop path-node sidebar refresh:
- Village path detection preview generation:
- Browser initial GitHub Pages render:
- Browser pan at fully zoomed-out view:
- Browser zoom with labels visible:
- Browser station search:
- Browser route search:
- Live-world chunk loading around target area:
- Live-world terrain render:

Record the machine, browser, worldgen mode, map asset date, and any obvious visual jank beside each timing.
