# Wings of Freedom completion tracker

A private local companion for finishing the original game's gallery. Read saves, expose evidence and plan crafting/farming. Public code and factual catalogue only. Approved searchable lists, character counters, manual corrections, raw exports, mission advice, estimated runs and ETA. Estimates must state assumptions and data gaps.

Implementation choice: native PySide6/Qt6 desktop app, with the offline browser version and standard-library Python exporter retained. Both versions use the existing tracker JSON format. Design choice: native desktop workspace with charcoal and warm gold dark mode, a persistent light/dark switch, readable tables, accessible focus and compact layouts. Install a dedicated local app/runtime with a stable menu entry. No accounts, telemetry, network calls or save writing.

The native Equipment map exposes catalogue upgrade trees, development/upgrade recipes, shared material consumers and clickable material sources. Rank quantified farming yields with explicit assumptions; keep unknown body-part drop rates separate.
