# Wings of Freedom completion notebook

A local save reader and completion planner for **Attack on Titan / A.O.T. Wings of Freedom (2016), Steam 449800**. This is not an AOT2 tracker or save editor.

## Native Qt6 app

The desktop app uses native Qt Widgets through PySide6. It shares the save decoder and catalogue with the browser version, and reads existing tracker JSON exports.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from this checkout:

```sh
uv sync --locked
./launch-native.sh
# Optional: open a specific save or tracker export.
./launch-native.sh '/path/to/ATWIN0000.dat'
# Linux application menu entry, for the current user only:
uv run --locked python install_desktop.py
```

Open **Wings of Freedom Tracker** in the application menu. The menu entry points to this checkout and its virtual environment; rerun the installer if you move it. No server or browser is needed. Qt requires a working Wayland or X11 desktop; platform libraries are operating-system dependencies.

1. Use **Open save or tracker** to select a `.dat` or exported `.json` file. The app validates the save checksum before loading it.
2. Explore Equipment, Materials, Characters, Gallery, Missions and Requests. Search filters the current section. **Only unfinished** applies to completion lists. Double-click numeric counters or toggle gallery checkboxes to make tracker-only corrections.
3. In **Farming plan**, choose your goal and mode. **Buy shop materials** is enabled for new profiles. Check the shopping/farming list and crafting order; body-part sources remain separate where rates are unknown. Fortified equipment is always protected.
4. Record reward-screen totals and full run times under **Run log** for observed averages.
5. After saving in-game, use **Reload source save**. A new snapshot carries settings and run logs forward, clears manual corrections, and leaves earlier snapshots accessible.
6. Use **Export tracker JSON** to back up corrections and logs or transfer to the browser tracker. CSV exports the currently visible filtered table. Raw decrypted bytes are available under File after importing a `.dat`.

Session data is stored atomically in Qt's platform application-data directory. On Linux this is normally `~/.local/share/WingsOfFreedomNotebook/aot-completion-tracker/profiles.json`; Help → About shows the exact location. Each storage directory permits one running instance to avoid lost updates. `--data-dir /private/folder` selects another session location. The app does not watch saves or modify the source file.

The native app has no accounts, analytics, uploads or network calls. The first dependency installation uses the network. Personal session data and exports belong outside this public repository.

## Windows portable bundle

The same native application runs on Windows. See [WINDOWS.md](WINDOWS.md) for extraction and launch instructions. Build a self-contained x64 ZIP from Linux or Windows with Python 3.11+:

```sh
python build_windows.py --out /private/folder/windows-build
```

The builder downloads embedded Python and the Windows Qt wheels named in `uv.lock`, verifies SHA256 digests, includes upstream licenses and copies only public application files. It excludes personal saves, snapshots and run history. No Wine or Windows cross-compiler is needed to assemble the ZIP. A Wine smoke check is distinct from real Windows testing.

## Browser version and exporter

Open `index.html` in a browser and select an `ATWIN0000.dat`, `ATWIN0001.dat`, exported snapshot or tracker JSON. The page decrypts locally and checks the save checksum. There are no accounts, analytics, uploads or dependencies. No source save is ever written.

## What's included

- Historical gallery unlocks, separate from current inventory: 625 eligible entries in the supported build, including 225 required equipment variants.
- Named material quantities, inventory and fortification, all 14 character records with levels, kills, battles and attributes.
- 91 named base-game missions in normal and True Attack modes; clear, S-rank and Dire reward groups. 81 requests per mode.
- Search, unfinished filters, manual gallery/material/character corrections, JSON and CSV export.
- Crafting order, branch rebuilding and shared-material requirements. Fortified inventory is protected; consuming unfortified inventory is opt-in.
- Mission recommendations, estimated repetitions and farming duration. Whole-run logs replace table assumptions with observed averages. Unknown random rates stay uncovered, with boss/mission hints. Remaining non-farming work has a separate time budget.

The plan is a greedy heuristic, not a guaranteed optimal route. It does not assume body-part drop rates. Saved mission time is treated as a record time with an explicit 25% allowance; enter measured whole-run times for better estimates. The displayed 0.8–1.5 timing range is a scenario allowance, not a statistical confidence interval. A complete ETA is withheld while material sources or cleanup time remain unknown.

## Raw exports

Python 3.10+ standard library only:

```sh
python save_reader.py '/path/to/ATWIN0000.dat' --out '/private/folder/exports'
```

The exporter first creates a timestamped, byte-verified read-only backup. It then writes `snapshot.json`, `decrypted.bin`, full `raw-words.csv`, and CSVs for characters, materials, inventory, gallery, missions and requests. It refuses output inside the public source repository. The raw words include every byte, including fields whose meaning remains unknown.

On Linux/Proton the usual save path is:

```text
~/.local/share/Steam/steamapps/compatdata/449800/pfx/drive_c/users/steamuser/Documents/KoeiTecmo/Attack on Titan/SAVEDATA/
```

On Windows: `Documents/KoeiTecmo/Attack on Titan/SAVEDATA/`.

Build a private standalone page with an initial snapshot:

```sh
python build.py --snapshot /private/exports/snapshot.json --out /private/tracker-personal.html
```

Export tracker JSON to preserve run logs and corrections. A new `.dat` import creates a separate snapshot, carrying forward the active plan settings and run samples but clearing manual progress corrections. Previous slots and their corrections remain available. Browser storage is a convenience, not a backup. A personal standalone HTML contains personal progress and should remain private.

## Coverage and evidence

The save decoder was derived from the installed PC build 1361480 and checked against two real slots. Both checksum validations pass; per-character kills sum to global kills; parsed gallery completion matches both slots' summary percentages. Known Perfected/Rozen recipes and Soldier's Dance rewards also match published guides.

Some rank labels, star-fortification details and individual history model labels remain unconfirmed. Those values are retained raw instead of assigned speculative labels. Extra non-playable character records are exposed as stored, not presented as required playable-character goals. Character levels and all True Attack requests are not prerequisites automatically counted toward gallery 100%.

See [save format research](docs/save-format.md). Factual catalogue names, recipes and reward numbers are extracted from the installed game. Game artwork, executable bytes, full description text and personal saves are not included. This is an unofficial companion.

Sources for cross-checks and farming hints:

- [Material Reward FAQ](https://gamefaqs.gamespot.com/ps4/179664-attack-on-titan/faqs/73843)
- [Gallery checklist](https://steamcommunity.com/sharedfiles/filedetails/?id=754286204)
- [Boss farming discussion](https://www.playstationtrophies.org/forum/topic/277049-psa-easy-glowing-crystals/)
- [TitanUnpacker archive research](https://github.com/TraduSquare/TitanUnpacker)

## Development

Edit `index.template.html`, `app.js`, `planner.js` and `catalog.json`. Run `python build.py` to regenerate the public `index.html`. Use `python -m http.server 8768 --bind 127.0.0.1` if preferred to file opening. All personal files should remain outside this repository. Never commit actual saves, decrypted binaries, snapshots, run history or personal standalone pages.
