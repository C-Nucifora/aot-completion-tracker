#!/usr/bin/env python3
"""Native Qt6 completion notebook. Source saves are opened read-only."""
import argparse
import copy
import json
import math
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QLockFile, QModelIndex, QSaveFile, QIODevice, QSize, QSortFilterProxyModel, QStandardPaths, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QSplitter, QStackedWidget, QStyledItemDelegate, QTabWidget, QTableView,
    QToolBar, QVBoxLayout, QWidget)

from save_reader import csv_export, parse
from tracker_core import (DROP_HINTS, corrected, defaults, farming_plan, integer,
                          load_profile, recipe_text, valid_settings)

ROOT = Path(__file__).resolve().parent
SAVE_DIR = (Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))/'KoeiTecmo/Attack on Titan/SAVEDATA' if sys.platform == 'win32' else Path.home()/'.local/share/Steam/steamapps/compatdata/449800/pfx/drive_c/users/steamuser/Documents/KoeiTecmo/Attack on Titan/SAVEDATA')
TABS = ('Overview', 'Equipment', 'Materials', 'Characters', 'Gallery', 'Missions', 'Requests', 'Farming plan', 'Run log')


def atomic_write(path, content):
    file = QSaveFile(str(path))
    if not file.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(file.errorString())
    if file.write(content) != len(content) or not file.commit():
        raise OSError(file.errorString())


def label(text, style=''):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if style:
        widget.setStyleSheet(style)
    return widget


def button(text, callback):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    return widget


class TableModel(QAbstractTableModel):
    def __init__(self, rows, columns, edit=None, parent=None):
        super().__init__(parent)
        self.rows, self.columns, self.edit = rows, columns, edit

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return self.columns[section][0] if orientation == Qt.Orientation.Horizontal else section+1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        value = row.get(self.columns[index.column()][1], '')
        if role == Qt.ItemDataRole.UserRole:
            return value
        if role == Qt.ItemDataRole.CheckStateRole and type(value) is bool:
            return Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            if type(value) is bool:
                return None
            if isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=False)
            return value
        if role == Qt.ItemDataRole.EditRole:
            return value
        if role == Qt.ItemDataRole.ToolTipRole:
            hint = '\nDouble-click to correct this tracker value.' if self.columns[index.column()][1] in row.get('_edits', {}) else ''
            return str(value)+hint
        if role == Qt.ItemDataRole.TextAlignmentRole and type(value) in (int, float):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid():
            row = self.rows[index.row()]
            key = self.columns[index.column()][1]
            if self.edit and key in row.get('_edits', {}):
                flags |= Qt.ItemFlag.ItemIsUserCheckable if type(row.get(key)) is bool else Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        row = self.rows[index.row()]
        key = self.columns[index.column()][1]
        path = row.get('_edits', {}).get(key)
        if not path or not self.edit:
            return False
        if role == Qt.ItemDataRole.CheckStateRole and type(row.get(key)) is bool:
            value = value == Qt.CheckState.Checked.value
        elif role == Qt.ItemDataRole.EditRole:
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False
            if not integer(value, 10**9):
                return False
        else:
            return False
        self.edit(path, value)
        row[key] = value
        self.dataChanged.emit(index, index)
        return True


class FilterModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query, self.unfinished = '', False
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def filterAcceptsRow(self, row, parent):
        record = self.sourceModel().rows[row]
        done = record.get('acquired', record.get('completed', record.get('_done', False)))
        text = ' '.join(str(v) for k, v in record.items() if not k.startswith('_')).casefold()
        return (not self.unfinished or not done) and self.query in text

    def update_filter(self, query, unfinished):
        self.query, self.unfinished = query.casefold(), unfinished
        self.invalidateFilter()


class CounterDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if type(index.data(Qt.ItemDataRole.EditRole)) is int:
            editor = QSpinBox(parent)
            editor.setRange(0, 10**9)
            return editor
        return super().createEditor(parent, option, index)


class RunDialog(QDialog):
    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Record a farming run')
        self.resize(670, 540)
        self.catalog = catalog
        layout = QVBoxLayout(self)
        layout.addWidget(label('Record total materials from the reward screen and full time including loading. A sample replaces table yields for that mission. Include zero for a rare drop that failed.'))
        form = QFormLayout()
        self.mission = QComboBox()
        for mode in ('normal', 'true'):
            for mission in catalog['missions']:
                self.mission.addItem(f'{"True Attack" if mode == "true" else "Normal"} · {mission["name"]}', f'{mode}:{mission["id"]}')
        self.minutes = QDoubleSpinBox()
        self.minutes.setRange(0.1, 1440)
        self.minutes.setValue(10)
        self.minutes.setSuffix(' min')
        form.addRow('Mission', self.mission)
        form.addRow('Whole-run time', self.minutes)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.material = QComboBox()
        for i, name in enumerate(catalog['materials']):
            if name and name.lower() != 'dummy':
                self.material.addItem(f'{name} · ID {i}', i)
        self.quantity = QSpinBox()
        self.quantity.setRange(0, 1000000)
        self.quantity.setValue(1)
        row.addWidget(self.material, 1)
        row.addWidget(self.quantity)
        row.addWidget(button('Add material', self.add_material))
        layout.addLayout(row)
        self.drops = {}
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)
        layout.addWidget(button('Remove selected material', self.remove_material))
        self.error = label('')
        layout.addWidget(self.error)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
        self.refresh()

    def add_material(self):
        self.drops[str(self.material.currentData())] = self.quantity.value()
        self.refresh()

    def remove_material(self):
        index = self.table.currentIndex()
        if index.isValid():
            self.drops.pop(self.table.model().rows[index.row()]['id'], None)
            self.refresh()

    def refresh(self):
        old = self.table.model()
        self.table.setModel(TableModel([dict(id=k, name=self.catalog['materials'][int(k)], quantity=v) for k, v in self.drops.items()], [('Material', 'name'), ('Gained', 'quantity')], parent=self.table))
        if old:
            old.deleteLater()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def accept(self):
        if not self.drops:
            self.error.setText('Add at least one material. Use zero when a rare drop did not appear.')
            return
        super().accept()

    def sample(self):
        return dict(id=uuid.uuid4().hex, key=self.mission.currentData(), minutes=self.minutes.value(), materials=self.drops)


class MainWindow(QMainWindow):
    def __init__(self, data_dir=None):
        super().__init__()
        self.catalog = json.loads((ROOT/'catalog.json').read_text())
        self.profiles, self.active, self.raws = [], 0, {}
        self.restore_failed = False
        self.current_tables = []
        self.plan_tab = 0
        self.data_dir = Path(data_dir) if data_dir else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        self.state_path = self.data_dir/'profiles.json'
        self.setWindowTitle('Wings of Freedom · Completion notebook')
        self.setWindowIcon(QIcon(str(ROOT/'assets/notebook.svg')))
        self.resize(1250, 820)
        self.setMinimumSize(860, 560)
        self.build_ui()
        try:
            if self.state_path.exists():
                data = self.read_json(self.state_path, 256*1024*1024)
                if not isinstance(data, dict) or not isinstance(data.get('profiles'), list):
                    raise ValueError('Invalid saved tracker session')
                self.profiles = [load_profile(p, 'Saved snapshot', self.catalog) for p in data['profiles']]
                index = data.get('active', 0)
                self.active = min(index, len(self.profiles)-1) if integer(index) and self.profiles else 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.restore_failed = True
            QMessageBox.warning(self, 'Could not restore tracker', f'{exc}\n\nImport a save or tracker JSON to continue. The unreadable session will be preserved in a separate recovery file before saving a new session.')
        self.refresh_slots()
        self.refresh()

    def build_ui(self):
        toolbar = QToolBar('Files', self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        file_menu = self.menuBar().addMenu('&File')
        for title, shortcut, callback in (
            ('Open save or tracker…', QKeySequence.StandardKey.Open, self.open_dialog),
            ('Reload source save', 'Ctrl+R', self.reload_save),
            ('Export tracker JSON…', 'Ctrl+Shift+S', self.export_json),
            ('Export current table CSV…', 'Ctrl+Shift+E', self.export_csv),
            ('Export decrypted bytes…', '', self.export_raw),
        ):
            action = QAction(title, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(callback)
            file_menu.addAction(action)
            if title != 'Export decrypted bytes…':
                toolbar.addAction(action)
        file_menu.addSeparator()
        quit_action = file_menu.addAction('Quit', self.close)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        help_menu = self.menuBar().addMenu('&Help')
        help_menu.addAction('About this tracker', self.about)
        base = QWidget()
        self.setCentralWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(12)
        layout.addWidget(label('Completion notebook', 'font-size: 25px; font-weight: 600;'))
        layout.addWidget(label('A.O.T. Wings of Freedom · Original PC game · Offline save reader and farming planner'))
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Snapshot'))
        self.slots = QComboBox()
        self.slots.setMinimumContentsLength(24)
        self.slots.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.slots.currentIndexChanged.connect(self.select_slot)
        controls.addWidget(self.slots, 2)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search items, materials, missions…')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('Search current section')
        self.search.textChanged.connect(self.filter_tables)
        controls.addWidget(self.search, 2)
        self.missing = QCheckBox('Only unfinished')
        self.missing.toggled.connect(self.filter_tables)
        controls.addWidget(self.missing)
        layout.addLayout(controls)
        self.summary = label('')
        layout.addWidget(self.summary)
        split = QSplitter()
        self.nav = QListWidget()
        self.nav.addItems(TABS)
        for i in range(self.nav.count()):
            self.nav.item(i).setSizeHint(QSize(160, 38))
        self.nav.setMinimumWidth(160)
        self.nav.setMaximumWidth(210)
        self.nav.setAccessibleName('Tracker sections')
        self.nav.currentRowChanged.connect(self.change_page)
        split.addWidget(self.nav)
        self.pages = QStackedWidget()
        split.addWidget(self.pages)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage('Open a save to begin. Source saves are never modified.')

    @staticmethod
    def read_json(path, maximum=12*1024*1024):
        if path.stat().st_size > maximum:
            raise ValueError(f'File is too large. Maximum {maximum//(1024*1024)} MB.')
        return json.loads(path.read_text(encoding='utf8'))

    def profile(self):
        return self.profiles[self.active] if self.profiles else None

    def persist(self):
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            content = json.dumps(dict(profiles=self.profiles, active=self.active), ensure_ascii=False).encode()
            if len(content) > 256*1024*1024:
                raise OSError('Session exceeds 256 MB; export the active tracker before closing')
            if self.restore_failed and self.state_path.exists():
                backup = self.state_path.with_name(f'profiles-recovery-{uuid.uuid4().hex}.json')
                self.state_path.replace(backup)
                self.restore_failed = False
            atomic_write(self.state_path, content)
            self.state_path.chmod(0o600)
            return True
        except OSError as exc:
            self.statusBar().showMessage(f'Could not save tracker session: {exc}. Export tracker JSON to preserve changes.')
            return False

    def refresh_slots(self):
        self.slots.blockSignals(True)
        self.slots.clear()
        for profile in self.profiles:
            captured = str(profile['snapshot'].get('captured_at', ''))[:16].replace('T', ' ')
            self.slots.addItem(f'{profile["name"]} · {captured}')
        if not self.profiles:
            self.slots.addItem('No save loaded')
        self.slots.setCurrentIndex(self.active)
        self.slots.blockSignals(False)

    def select_slot(self, index):
        if 0 <= index < len(self.profiles):
            self.active = index
            self.persist()
            self.refresh()

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open save or tracker', str(SAVE_DIR if SAVE_DIR.exists() else Path.home()), 'Saves and snapshots (*.dat *.json);;All files (*)')
        if path:
            self.import_file(Path(path))

    def import_file(self, path):
        try:
            path = Path(path).resolve()
            if path.stat().st_size > 12*1024*1024:
                raise ValueError('File is too large. Maximum 12 MB.')
            raw = None
            if path.suffix.lower() == '.dat':
                original = path.read_bytes()
                if original != path.read_bytes():
                    raise ValueError('Save changed while reading. Retry after the game finishes saving.')
                snapshot, raw = parse(original, self.catalog)
                settings = copy.deepcopy(self.profile()['settings']) if self.profile() else defaults()
                settings['overrides'] = {}
                profile = dict(name=path.name, snapshot=snapshot, settings=settings, source_path=str(path))
            else:
                profile = self.read_json(path)
            profile = load_profile(profile, path.name, self.catalog)
            self.profiles.append(profile)
            self.active = len(self.profiles)-1
            if raw is not None:
                self.raws[id(profile)] = raw
            saved = self.persist()
            self.refresh_slots()
            self.refresh()
            if saved:
                self.statusBar().showMessage(f'Loaded {path.name}. Source save unchanged. Tracker changes saved locally.')
            return True
        except (OSError, ValueError, KeyError, TypeError, IndexError, RecursionError) as exc:
            QMessageBox.warning(self, 'Could not open file', f'{exc}\n\nThe current snapshot has been kept. Choose a supported .dat save or tracker JSON.')
            return False

    def reload_save(self):
        profile = self.profile()
        if profile and profile.get('source_path'):
            self.import_file(Path(profile['source_path']))
        else:
            self.statusBar().showMessage('Open a .dat save first, then use Reload source save after saving in-game.')

    def safe_export_path(self, title, suggested, file_filter):
        path, _ = QFileDialog.getSaveFileName(self, title, str(Path.home()/'Downloads'/suggested), file_filter)
        if not path:
            return None
        target = Path(path).resolve()
        sources = {Path(p['source_path']).resolve() for p in self.profiles if p.get('source_path')}
        if target.suffix.lower() == '.dat' or target in sources or target == self.state_path.resolve():
            raise ValueError('Choose an export filename outside the source save and tracker session files.')
        return target

    def export_json(self):
        if not self.profile():
            return
        try:
            path = self.safe_export_path('Export tracker JSON', 'aot-tracker.json', 'Tracker JSON (*.json)')
            if path:
                atomic_write(path, (json.dumps(self.profile(), indent=2, ensure_ascii=False)+'\n').encode())
                self.statusBar().showMessage(f'Exported tracker, corrections and run logs to {path}')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))

    def visible_table(self):
        return next((t for t in self.current_tables if t.isVisible()), None)

    def export_csv(self):
        table = self.visible_table()
        if table is None:
            return
        try:
            path = self.safe_export_path('Export current table', 'aot-table.csv', 'CSV (*.csv)')
            if path:
                proxy = table.model()
                columns = proxy.sourceModel().columns
                rows = [proxy.sourceModel().rows[proxy.mapToSource(proxy.index(i, 0)).row()] for i in range(proxy.rowCount())]
                # Use the shared CSV writer's spreadsheet formula protection.
                csv_export(path, [{title: row.get(key, '') for title, key in columns} for row in rows] or [{title: '' for title, _ in columns}])
                self.statusBar().showMessage(f'Exported current filtered table to {path}')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))

    def export_raw(self):
        raw = self.raws.get(id(self.profile()))
        if raw is None:
            self.statusBar().showMessage('Import or reload a .dat save to export its decrypted bytes.')
            return
        try:
            path = self.safe_export_path('Export decrypted bytes', 'aot-decrypted.bin', 'Binary (*.bin)')
            if path:
                atomic_write(path, raw)
                self.statusBar().showMessage(f'Exported decrypted copy to {path}. Source save unchanged.')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))

    def change_page(self, index):
        self.search.clear()
        self.refresh()

    def update_summary(self):
        if not self.profile():
            self.summary.setText('')
            return
        snapshot = corrected(self.profile())
        acquired = sum(r['acquired'] for r in snapshot['gallery'])
        self.summary.setText(f'Gallery {acquired} / {len(snapshot["gallery"])}    ·    Funds {snapshot["summary"]["funds"]:,}    ·    Titans slain {snapshot["summary"]["total_kills"]:,}')

    def correct_value(self, path, value):
        self.profile()['settings']['overrides'][path] = value
        saved = self.persist()
        self.update_summary()
        if saved:
            self.statusBar().showMessage('Tracker correction saved locally. Source save unchanged; JSON export preserves corrections.')

    def filter_tables(self, *_):
        for table in self.current_tables:
            table.model().update_filter(self.search.text(), self.missing.isChecked() and self.missing.isEnabled())

    def add_table(self, layout, rows, columns, edit=False):
        table = QTableView()
        table.setAccessibleName(TABS[max(0, self.nav.currentRow())]+' table')
        model = TableModel(rows, columns, self.correct_value if edit else None, table)
        proxy = FilterModel(table)
        proxy.setSourceModel(model)
        table.setModel(proxy)
        table.setItemDelegate(CounterDelegate(table))
        table.setSortingEnabled(True)
        table.sortByColumn(-1, Qt.SortOrder.AscendingOrder)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(34)
        table.horizontalHeader().setStretchLastSection(True)
        for i, (title, _) in enumerate(columns):
            table.setColumnWidth(i, 270 if i == 0 else 105)
        layout.addWidget(table, 1)
        self.current_tables.append(table)
        return table

    def refresh(self):
        self.current_tables = []
        while self.pages.count():
            old = self.pages.widget(0)
            self.pages.removeWidget(old)
            old.deleteLater()
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(12)
        self.pages.addWidget(page)
        tab = TABS[max(0, self.nav.currentRow())]
        self.missing.setEnabled(tab in ('Overview', 'Equipment', 'Gallery', 'Missions', 'Requests'))
        self.update_summary()
        if not self.profile():
            layout.addWidget(label('Open your save to see what is left to collect.', 'font-size: 20px; font-weight: 600;'))
            layout.addWidget(label('Choose ATWIN0000.dat or ATWIN0001.dat, or import an existing tracker JSON. The app checks the save checksum and keeps all data on this computer.'))
            layout.addWidget(button('Open save or tracker…', self.open_dialog))
            layout.addStretch()
            return
        snapshot = corrected(self.profile())
        C = self.catalog
        if tab == 'Overview':
            groups = list(dict.fromkeys(r['section'] for r in snapshot['gallery']))
            rows = []
            for section in groups:
                entries = [r for r in snapshot['gallery'] if r['section'] == section]
                done = sum(r['acquired'] for r in entries)
                rows.append(dict(name=section, done=done, total=len(entries), remaining=len(entries)-done, _done=done == len(entries)))
            layout.addWidget(label('Historical unlocks are separate from your current inventory. Use Equipment to inspect recipes and Farming plan to cover shared shortages.'))
            self.add_table(layout, rows, [('Category', 'name'), ('Collected', 'done'), ('Total', 'total'), ('Remaining', 'remaining')])
            normal = sum(r['completed'] for r in snapshot['requests'] if r['mode'] == 'normal')
            true = sum(r['completed'] for r in snapshot['requests'] if r['mode'] == 'true')
            layout.addWidget(label(f'Requests: Normal {normal}/81 · True Attack {true}/81. Character levels and True Attack requests are tracked separately from gallery completion.'))
            layout.addWidget(label(f'Captured {snapshot.get("captured_at", "unknown")}. Checksum verified. Saved mission times may be personal bests. Star fortification and rank labels remain unconfirmed.'))
            layout.addWidget(label('Re-import or reload after saving in-game. Tracker corrections never modify a game save.'))
        elif tab == 'Equipment':
            gallery = {r['key']: r['acquired'] for r in snapshot['gallery']}
            rows = []
            for e in C['equipment']:
                if e['required']:
                    rows.append(dict(name=e['name'], group=e['group'], acquired=gallery.get('equipment:'+e['key'], False),
                        held=', '.join(f'+{r["fortification"]}' for r in snapshot['inventory'] if r['key'] == e['key']) or 'None',
                        stats=' / '.join(map(str, e['stats'])), recipe='; '.join(text for text in [('Develop: '+self.recipe(e['develop'])) if e['develop'] else '', ('Upgrade: '+self.recipe(e['upgrade'])) if e['upgrade'] else ''] if text),
                        _edits={'acquired': f'gallery|equipment:{e["key"]}|acquired'}))
            layout.addWidget(label('Acquired means ever owned. Held shows current inventory fortification. Change checkboxes to correct the tracker only. Horses are under Gallery.'))
            self.add_table(layout, rows, [('Item', 'name'), ('Group', 'group'), ('Acquired', 'acquired'), ('Held', 'held'), ('Stats', 'stats'), ('Materials', 'recipe')], True)
        elif tab == 'Materials':
            rows = [dict(r, shop='Available' if r['shop_state'] >= 9 else 'Not unlocked', _edits={'count': f'materials|{r["id"]}|count'}) for r in snapshot['materials']]
            layout.addWidget(label('Double-click Held to correct a tracker count. Shop availability comes from the save flag; confirm stock in-game.'))
            self.add_table(layout, rows, [('Material', 'name'), ('ID', 'id'), ('Held', 'count'), ('Shop', 'shop'), ('Save offset', 'offset')], True)
        elif tab == 'Characters':
            rows = [dict(r, attributes=' / '.join(map(str, r['attributes'])), _edits={k: f'characters|{r["id"]}|{k}' for k in ('level', 'kills', 'missions')}) for r in snapshot['characters']]
            layout.addWidget(label('Double-click Level, Kills or Battles for tracker corrections. Attributes: strength, dexterity, concentration, stamina, health, leadership.'))
            self.add_table(layout, rows, [('Character', 'name'), ('Level', 'level'), ('Kills', 'kills'), ('Battles', 'missions'), ('XP', 'xp'), ('Attributes', 'attributes')], True)
        elif tab == 'Gallery':
            rows = [dict(r, evidence=f'0x{r["offset"]:x} · flag {r["raw_flag"]}', _edits={'acquired': f'gallery|{r["key"]}|acquired'}) for r in snapshot['gallery']]
            self.add_table(layout, rows, [('Entry', 'name'), ('Section', 'section'), ('Acquired', 'acquired'), ('Save evidence', 'evidence')], True)
        elif tab == 'Missions':
            missions = {m['id']: m for m in C['missions']}
            rows = []
            for record in snapshot['missions']:
                info = missions[record['id']]
                mode = record['mode']
                rows.append(dict(record, mode_label='True Attack' if mode == 'true' else 'Normal',
                    time=f'{record["time_seconds"]/60:.1f} min' if record['time_seconds'] else 'Unknown',
                    clear=self.recipe(info['rewards'][mode]), rank=self.recipe([info['s_rank'][mode]]), dire=self.recipe([info['dire'][mode]])))
            layout.addWidget(label('S-rank and Dire rewards are conditional. Body-part drops are separate. Saved time may be a personal best; log full runs for farming estimates.'))
            self.add_table(layout, rows, [('Mission', 'name'), ('Mode', 'mode_label'), ('Cleared', 'completed'), ('Saved time', 'time'), ('Clear rewards', 'clear'), ('S-rank rewards', 'rank'), ('Dire rewards', 'dire')])
        elif tab == 'Requests':
            self.add_table(layout, snapshot['requests'], [('Request', 'name'), ('Mode', 'mode'), ('Complete', 'completed'), ('Raw state', 'state')])
        elif tab == 'Farming plan':
            self.build_plan(layout, snapshot)
        elif tab == 'Run log':
            self.build_log(layout)
        self.filter_tables()

    def recipe(self, values):
        return recipe_text(values, self.catalog)

    def set_setting(self, key, value):
        settings = copy.deepcopy(self.profile()['settings'])
        settings[key] = value
        try:
            self.profile()['settings'] = valid_settings(settings, self.catalog)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))
            return
        self.persist()
        self.refresh()

    def setting_combo(self, row, title, key, options):
        row.addWidget(QLabel(title))
        combo = QComboBox()
        for text, value in options:
            combo.addItem(text, value)
        combo.setCurrentIndex(combo.findData(self.profile()['settings'][key]))
        combo.currentIndexChanged.connect(lambda _: self.set_setting(key, combo.currentData()))
        row.addWidget(combo)
        return combo

    def build_plan(self, layout, snapshot):
        settings = self.profile()['settings']
        row = QHBoxLayout()
        self.setting_combo(row, 'Goal', 'goal', [('All missing equipment', 'all'), ('Perfected set', 'perfected'), ('Rozen set', 'rozen')])
        self.setting_combo(row, 'Mode', 'mode', [('Both', 'both'), ('Normal', 'normal'), ('True Attack', 'true')])
        row.addStretch()
        layout.addLayout(row)
        checks = QHBoxLayout()
        for text, key in [('Buy shop materials', 'buyShop'), ('Assume S rank', 'sRank'), ('Include Dire rewards', 'dire'), ('Consume unfortified inventory', 'useInventory')]:
            check = QCheckBox(text)
            check.setChecked(settings[key])
            check.toggled.connect(lambda value, k=key: self.set_setting(k, value))
            checks.addWidget(check)
        layout.addLayout(checks)
        duration = QHBoxLayout()
        duration.addWidget(QLabel('Fallback minutes/run'))
        minutes = QDoubleSpinBox()
        minutes.setRange(0.1, 1440)
        minutes.setValue(settings['defaultMinutes'])
        minutes.setKeyboardTracking(False)
        minutes.valueChanged.connect(lambda value: self.set_setting('defaultMinutes', value))
        duration.addWidget(minutes)
        duration.addWidget(QLabel('Other cleanup hours'))
        cleanup = QDoubleSpinBox()
        cleanup.setRange(-0.5, 10000)
        cleanup.setSingleStep(0.5)
        cleanup.setSpecialValueText('Unknown')
        cleanup.setValue(-0.5 if settings['cleanupHours'] is None else settings['cleanupHours'])
        cleanup.setKeyboardTracking(False)
        cleanup.valueChanged.connect(lambda value: self.set_setting('cleanupHours', None if value < 0 else value))
        duration.addWidget(cleanup)
        duration.addStretch()
        layout.addLayout(duration)
        result = farming_plan(self.catalog, snapshot, settings)
        craft, plan = result['craft'], result['plan']
        time = plan['minutes']/60
        estimate = f'At least {time:.1f} h covered farming; {len(plan["uncovered"])} material types need a source or run samples.' if plan['uncovered'] else f'Modelled farming {time:.1f} h. Planning range {time*.8:.1f}–{time*1.5:.1f} h; timing allowance, not a confidence interval.'
        if settings['cleanupHours'] is None or plan['uncovered']:
            estimate += ' Full completion ETA remains unknown.'
        else:
            estimate += f' With cleanup: {time+settings["cleanupHours"]:.1f} h modelled total.'
        layout.addWidget(label(estimate, 'font-weight: 600;'))
        costs = f'{result["goals"]} missing equipment goals · {len(craft["steps"])} craft steps · Craft fees {craft["craftingFunds"]:,} · Shop costs {result["shopCost"]:,}'
        if result['fundsGap']:
            costs += f' · Funds shortfall {result["fundsGap"]:,}'
        layout.addWidget(label(costs))
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        def section(title):
            widget = QWidget()
            child = QVBoxLayout(widget)
            tabs.addTab(widget, title)
            return child
        missions = section('Mission route')
        if not plan['rows']:
            missions.addWidget(label('No quantified mission route yet. Check Body-part sources for the remaining drops, or record full runs to estimate repetitions.'))
        rows = [dict(r, duration=round(r['runs']*r['minutes'], 1), drops=self.recipe([dict(material=i, quantity=round(q, 2)) for i, q in r['yields'].items()])) for r in plan['rows']]
        self.add_table(missions, rows, [('Mission', 'name'), ('Mode', 'mode'), ('Runs', 'runs'), ('Minutes', 'duration'), ('Materials/run', 'drops'), ('Basis', 'evidence')])
        shopping = section('Shopping and farming')
        rows = [dict(r, action='Buy in shop' if settings['buyShop'] and r['id'] in result['buyable'] else 'Farm') for r in craft['deficits'] if r['need']]
        self.add_table(shopping, rows, [('Material', 'name'), ('Required', 'total'), ('Held', 'held'), ('Missing', 'need'), ('Action', 'action')])
        order = section('Crafting order')
        if craft['blocked']:
            order.addWidget(label('Unresolved crafting routes: '+', '.join(craft['blocked'])))
        self.add_table(order, [dict(r, recipe=self.recipe(r['materials'])) for r in craft['steps']], [('Item', 'name'), ('Action', 'route'), ('Fee', 'price'), ('Materials', 'recipe')])
        drops = section('Body-part sources')
        drops.addWidget(label('Break material-bearing limbs before the nape. Random drops are not included in estimated runs until you log full-run samples.'))
        self.add_table(drops, [dict(name=self.catalog['materials'][r['id']], remaining=math.ceil(r['need']), source=DROP_HINTS.get(r['id'], 'Check mission rewards or record a source in Run log')) for r in plan['uncovered']], [('Material', 'name'), ('Still needed', 'remaining'), ('Where to get it', 'source')])
        tabs.setCurrentIndex(self.plan_tab)
        tabs.currentChanged.connect(lambda index: setattr(self, 'plan_tab', index))
        layout.addWidget(label('Greedy shared-reward plan; not a proven minimum. Fortified inventory is protected. Confirm shop stock in-game. Horses and missing scenes/models need separate cleanup.'))

    def build_log(self, layout):
        layout.addWidget(label('Log whole runs including loading and every useful reward-screen material. Observed averages replace table assumptions for that mission; rare drops are never guaranteed.'))
        controls = QHBoxLayout()
        controls.addWidget(button('Record run…', self.record_run))
        controls.addWidget(button('Remove selected run', self.remove_run))
        controls.addStretch()
        layout.addLayout(controls)
        mission_names = {f'{mode}:{m["id"]}': f'{"True Attack" if mode == "true" else "Normal"} · {m["name"]}' for mode in ('normal', 'true') for m in self.catalog['missions']}
        rows = [dict(r, _sample_index=index, name=mission_names[r['key']], drops=self.recipe([dict(material=int(i), quantity=q) for i, q in r['materials'].items()])) for index, r in enumerate(self.profile()['settings']['samples'])]
        self.run_table = self.add_table(layout, rows, [('Mission', 'name'), ('Minutes', 'minutes'), ('Materials gained', 'drops')])

    def record_run(self):
        dialog = RunDialog(self.catalog, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = copy.deepcopy(self.profile()['settings'])
            settings['samples'].append(dialog.sample())
            self.profile()['settings'] = valid_settings(settings, self.catalog)
            self.persist()
            self.refresh()

    def remove_run(self):
        index = self.run_table.currentIndex()
        if index.isValid():
            proxy = self.run_table.model()
            row = proxy.mapToSource(index).row()
            sample = proxy.sourceModel().rows[row]
            self.profile()['settings']['samples'].pop(sample['_sample_index'])
            self.persist()
            self.refresh()

    def about(self):
        QMessageBox.about(self, 'Wings of Freedom completion notebook',
            'Native Qt6 / PySide6 companion for the original 2016 PC game.\n\nReads saves locally and checks their checksum. No uploads, accounts or save writing. Supports the verified build 1361480.\n\nJSON exports are compatible with the browser tracker. Re-import saves after playing. Run-log averages and saved record times are estimates, not guaranteed rates.\n\nSession storage: '+str(self.state_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('save', nargs='?', type=Path, help='Optional save or tracker JSON to open')
    parser.add_argument('--data-dir', type=Path, help='Override private session storage')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('aot-completion-tracker')
    app.setApplicationDisplayName('Wings of Freedom completion notebook')
    app.setOrganizationName('WingsOfFreedomNotebook')
    app.setDesktopFileName('aot-completion-tracker')
    app.setStyle('Fusion')
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, '#f6f3e9'), (QPalette.ColorRole.WindowText, '#23392f'),
        (QPalette.ColorRole.Base, '#ffffff'), (QPalette.ColorRole.AlternateBase, '#edf0e6'),
        (QPalette.ColorRole.Text, '#23392f'), (QPalette.ColorRole.Button, '#e5eadc'),
        (QPalette.ColorRole.ButtonText, '#23392f'), (QPalette.ColorRole.Highlight, '#315d47'),
        (QPalette.ColorRole.HighlightedText, '#ffffff'), (QPalette.ColorRole.ToolTipBase, '#ffffff'),
        (QPalette.ColorRole.ToolTipText, '#23392f')]:
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor('#697263'))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor('#65705f'))
    app.setPalette(palette)
    app.setStyleSheet('QToolBar { spacing: 8px; padding: 7px; } QListWidget { padding: 5px; } QListWidget::item { padding: 10px 7px; } QHeaderView::section { padding: 8px; } QPushButton { padding: 7px 12px; } QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { padding: 5px; } QTabBar::tab { padding: 8px 12px; }')
    data_dir = args.data_dir or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    try:
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        QMessageBox.critical(None, 'Cannot open tracker storage', str(exc))
        return 1
    session_lock = QLockFile(str(data_dir/'session.lock'))
    if not session_lock.tryLock(100):
        QMessageBox.information(None, 'Tracker already open', 'Use the existing tracker window to open another save. A second instance cannot write to the same session storage.')
        return 1
    window = MainWindow(data_dir)
    if args.save:
        window.import_file(args.save)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    sys.exit(main())
