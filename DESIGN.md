# Native desktop interface

The tracker is a native Qt6 desktop companion for checking progress between game sessions. Dark mode is the default. The replacement interface uses charcoal surfaces, warm gold controls and readable tables, as approved by the user.

## Appearance

`ui_theme.py` owns both palettes and all common widget styling. Dark surfaces are #14171a for navigation, #191d21 for the workspace and #20252a for tables and controls. Primary text is #edf0f2, secondary text #a9b2bc and the action accent #d9b66f. Light mode uses a soft neutral workspace, white tables and a darker gold accent for contrast. Qt's platform title bar remains system-controlled.

The sidebar theme switch persists its preference in `appearance.ini` beside the existing session store. Theme preference is separate from imported/exported snapshots. Dialogs, menus, inputs, selection, tooltips and scrollbars follow the application palette. All icons are locally drawn SVG paths with the same stroke weight; no network imagery or external icon font is used.

## Composition

A 216 px sidebar holds the app identity, nine named sections, compact gallery progress and appearance/help actions. The workspace puts a section heading and description beside Open save, Reload save and Export. Snapshot selection, search and completion filters sit directly above the content.

Tables have 42 px rows, aligned numeric columns, restrained alternating surfaces, native sorting, keyboard navigation and full-value tooltips. Long recipes and evidence remain accessible through horizontal scrolling. The Overview leads with remaining gallery entries and shortcuts to equipment and farming rather than decorative statistics.

The farming view separates settings from results and keeps shopping, crafting, route recommendations and unquantified body-part sources in native tabs. When only unknown drops remain, sources are the initial view. Timing and inventory assumptions live under More options. Unknown rates and incomplete ETA remain explicit.

## Verification and installation

Inspect both themes and compact/native desktop sizes in a private session. Preserve every import, correction, run-log and export flow. Read saves without modifying them. Install an independent application copy and runtime under the user application-data directory; the menu entry must not depend on Downloads. Retain the existing session storage path and leave any running user window untouched during upgrades.

## Equipment map

Use a native QGraphicsView for a pannable, zoomable tree with 225 equipment variants and 188 real catalogue upgrade edges. Separate direct-development roots rather than drawing implied upgrade paths. A group selector limits visual density; All equipment is available for the large overview. A keyboard equipment selector mirrors mouse selection. Global search and Only unfinished dim unrelated items while preserving route context.

Keep the graph beside a native inspector: equipment recipes in a tree, then clickable material sources in a second tab. Materials show need/held counts, shop availability first, body-part hints separately, and quantified missions sorted by estimated yield per minute. The current mode, S-rank and Dire conditions are visible. Unknown drop rates never receive a fabricated efficiency rank. Highlight consumers exposes shared material dependencies across the full map.
