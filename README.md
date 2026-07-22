# Minecraft Metro Map

[Open interactive map](https://akapppy.github.io/Plumville/)

This repo now has two active tracks:

- the existing Tk metro-planning app in `metro_stops.py`
- a new Bedrock world generation backend in `worldgen/`
- a static read-only browser viewer in `docs/`

The browser viewer is built for GitHub Pages. After these files are pushed to GitHub, enable Pages from the `main` branch `/docs` folder.

`docs/metro_network.json` is the canonical metro dataset. The desktop app and browser viewer both read that same file so station, line, and pathing changes do not need a separate sync step.

The worldgen work is intentionally modular. It does not try to generate Minecraft terrain itself. Instead, it manages a Bedrock Docker container, waits for a world to exist on disk, caches the resolved world path, and writes a Blackport-centered starter render plan for the next rendering phase.

## Requirements

- macOS
- Python 3.11 or newer
- Docker Desktop with `docker compose` available
- Python dependencies from `requirements.txt`

On macOS, `plyvel` usually needs LevelDB installed first:

```bash
brew install leveldb
python3 -m pip install -r requirements.txt
```

If `plyvel` builds but fails to import with a LevelDB symbol error, rebuild it with Homebrew's paths:

```bash
python3 -m pip uninstall -y plyvel
ARCHFLAGS='-arch arm64' CPPFLAGS='-I/opt/homebrew/include' CXXFLAGS='-fno-rtti' LDFLAGS='-L/opt/homebrew/lib' python3 -m pip install --no-cache-dir --no-binary=:all: plyvel
```

## Config

Edit `worldgen_config.toml` to change the seed, level name, storage folders, or starter render area.

The default config turns Bedrock `online_mode` off for the local Docker server so the headless loader can connect without an Xbox login. It also enables cheats/operator defaults so the loader can be teleported to Blackport from the server console.

The Bedrock server is pinned to the matching headless-loader protocol. If the Docker image cannot look up that exact server package from Minecraft's download page, `direct_download_url` supplies the known BDS zip URL directly.

The Bedrock Docker `/data` folder defaults to `~/Library/Application Support/Plumville/worldgen/bedrock-data` instead of this repo. The repo lives in iCloud Drive, and Docker can hit filesystem read/write errors when Bedrock's live server files are bind-mounted from a cloud-synced folder.

The default starter render area is centered on Blackport:

- `center_x = 294`
- `center_z = 390`
- `radius = 2000`

## Files

- `docker-compose.worldgen.yml`: static Compose definition for the Bedrock container and one-shot chunk-loader container
- `worldgen_config.toml`: editable worldgen settings
- `worldgen/`: Python package for config loading, Docker orchestration, cache management, and render-plan scaffolding

Generated local state is kept out of git:

- `.worldgen/`: generated env file for Compose
- `~/Library/Application Support/Plumville/worldgen/bedrock-data`: Bedrock server data
- `worldgen_data/`: cache files
- `worldgen_output/`: future render output
- `node_modules/`: local Node dependencies if installed on the host

The Docker chunk loader keeps its own Linux Node dependencies in a named Docker volume.

## Commands

Show the current config, cache, and Docker status:

```bash
python3 -m worldgen status
```

Start the Bedrock container:

```bash
python3 -m worldgen start
```

Wait until the world is ready, then write cache metadata and a render plan:

```bash
python3 -m worldgen wait
```

Do the whole flow in one command:

```bash
python3 -m worldgen prepare
```

Stop the container cleanly with a timeout:

```bash
python3 -m worldgen stop
```

Print the resolved world folder path:

```bash
python3 -m worldgen world-path
```

Write or refresh the Blackport-centered starter render plan:

```bash
python3 -m worldgen render-plan
```

Render already-generated Bedrock chunks into a first-pass top-down PNG:

```bash
python3 -m worldgen render
```

Each successful render writes `worldgen_output/blackport_topdown.png` and refreshes the web viewer copy at `docs/assets/blackport_topdown.png`.

If rendering reports a LevelDB read/corruption error after chunk loading, build a backed-up repaired copy for inspection:

```bash
python3 -m worldgen repair-db
```

Load chunks near Blackport without opening Minecraft:

```bash
python3 -m worldgen load-chunks
```

The first run may pull a Node Docker image and build a native RakNet dependency inside a Docker volume.

## What Is Implemented

- config loading from `worldgen_config.toml`
- Docker Compose orchestration around `itzg/minecraft-bedrock-server`
- persistent world storage in a repo-local folder
- `start`, `wait`, `stop`, `prepare`, and `world-path` backend commands
- cache metadata for the last prepared world
- a starter render plan centered on Blackport
- first-pass Bedrock subchunk reader and top-down PNG renderer for generated chunks
- a headless Bedrock loader that joins the local Docker server and loads chunks without the game client
- a LevelDB repair command that writes a backup and repaired copy for render-read debugging
- crash-aware Load Chunks reporting when the Bedrock server closes before the headless player spawns
- coverage-aware blank-space chunk-loading targets centered on Blackport, plus app Auto Fill controls

## What Is Still Next

- improving the rendered-image underlay once real terrain chunks are available

## Notes

- The first render pass should only expect to color chunks that Bedrock has actually generated and saved.
- The renderer also reads recoverable `db/lost` LevelDB table files, because `repair-db` may move older saved chunk tables there.
- The app's Auto Fill runs the backend load/render flow in order. It scans saved chunk columns, chooses the closest blank map space to Blackport, then picks the target covering the most remaining blank chunks before rendering after each batch.
- Before the headless loader joins, the backend sets the Bedrock world spawn to Blackport with spawn radius zero so the initial join chunks land in the render area.
- Auto Fill simulates each planned target against the remaining blank chunks, so later targets avoid already-covered space and do not leave holes in the middle. Avoid manually chaining repeated Generate/Load/Render cycles unless debugging, because repeated Bedrock restarts can be fragile while the server is saving terrain.
- The first render pass does not start Docker. For manual CLI use, run `python3 -m worldgen load-chunks` first, then run `python3 -m worldgen render`.
- If the render says `Chunk columns read: 0/...`, the saved world exists but Bedrock has not saved terrain in the requested area yet. Run the headless loader, stop the server, and render again.
- If Load Chunks reports `free(): invalid next size (normal)`, the Bedrock server crashed during headless-player connection before chunks could be saved.
- If the render reports a LevelDB read/corruption error, run `python3 -m worldgen repair-db`. The command leaves the live Bedrock DB in place, writes a backup under `worldgen_data/cache/leveldb_backups/`, and writes a repaired copy under `worldgen_data/cache/leveldb_repaired_copies/`.
- Because this repo lives inside iCloud Drive, large Docker bind mounts may be slower than ideal. If world data gets heavy, moving the data folder outside iCloud may be worth it later.
