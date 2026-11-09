# Wings of Freedom completion notebook

A local save reader and completion planner for **Attack on Titan / A.O.T. Wings of Freedom (2016), Steam 449800**. This is not an AOT2 tracker or save editor.

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
