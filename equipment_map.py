"""Native equipment paths and an inspectable recipe/material-source view."""
import copy
from collections import defaultdict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QGraphicsItem,
    QGraphicsObject, QGraphicsScene, QGraphicsView, QHBoxLayout, QHeaderView, QLabel, QLayout, QScrollArea,
    QPushButton, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from tracker_core import DROP_HINTS, effective_missions, recipe_text
from ui_theme import DARK, LIGHT

NODE_WIDTH, NODE_HEIGHT = 240, 86


def equipment_layout(catalog, group=None):
    """Use actual parent/upgrade recipes; direct development does not invent an edge."""
    positions, edges, headings = {}, [], []
    y_cursor = 45
    for group_id, title in enumerate(('Blades', 'Scabbards', 'ODM gear')):
        if group is not None and group != group_id:
            continue
        items = [e for e in catalog['equipment'] if e['required'] and e['group_id'] == group_id]
        by_key = {e['key']: e for e in items}
        children, roots = defaultdict(list), []
        for item in items:
            parent = f'{group_id}:{item["parent"]}'
            if parent in by_key and item['upgrade']:
                children[parent].append(item['key'])
                edges.append((parent, item['key']))
            else:
                roots.append(item['key'])
        headings.append((title, y_cursor-34))
        next_row = y_cursor
        visited = set()

        def place(key, depth):
            nonlocal next_row
            if key in visited:
                return positions[key][1]
            visited.add(key)
            descendants = [place(child, depth+1) for child in children[key]]
            y = sum(descendants)/len(descendants) if descendants else next_row
            if not descendants:
                next_row += 114
            positions[key] = (depth*306, y)
            return y

        for key in roots:
            place(key, 0)
            next_row += 26
        # A malformed catalogue must not silently hide an item.
        for item in items:
            if item['key'] not in visited:
                place(item['key'], 0)
                next_row += 26
        y_cursor = next_row+54
    return positions, edges, headings


def material_sources(catalog, snapshot, settings, material):
    rows = []
    for mission in effective_missions(catalog, snapshot, settings):
        quantity = mission['yields'].get(material, 0)
        if quantity > 0:
            rows.append(dict(mission, quantity=quantity, per_minute=quantity/mission['minutes']))
    return sorted(rows, key=lambda row: (-row['per_minute'], row['mode'], row['name']))


def text_label(text='', name='muted'):
    label = QLabel(text)
    label.setObjectName(name)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class EquipmentNode(QGraphicsObject):
    def __init__(self, item, acquired, dark):
        super().__init__()
        self.equipment, self.acquired, self.dark = item, acquired, dark
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(1)
        self.setToolTip(item['name']+'\n'+('Acquired previously' if acquired else 'Not yet acquired')+'\nClick to inspect recipes and material sources.')

    def boundingRect(self):
        return QRectF(-2, -2, NODE_WIDTH+4, NODE_HEIGHT+4)

    def paint(self, painter, option, widget=None):
        c = DARK if self.dark else LIGHT
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(c['selected'] if self.isSelected() else c['panel']))
        painter.setPen(QPen(QColor(c['accent'] if self.isSelected() or self.hasFocus() else c['border']), 2 if self.isSelected() else 1))
        painter.drawRoundedRect(QRectF(0, 0, NODE_WIDTH, NODE_HEIGHT), 8, 8)
        font = QFont('Sans Serif', 10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(c['text']))
        painter.drawText(QRectF(14, 10, NODE_WIDTH-28, 44), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, self.equipment['name'])
        font.setPointSizeF(8.5)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(c['accent'] if self.acquired else c['muted']))
        kind = 'Develop' if self.equipment['develop'] else 'Upgrade'
        painter.drawText(QRectF(14, 61, NODE_WIDTH-28, 18), Qt.AlignmentFlag.AlignLeft, f'{"Acquired" if self.acquired else "Missing"} · {kind}')


class MapView(QGraphicsView):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1/1.15)
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom(self, factor):
        scale = self.transform().m11()*factor
        # Fitting a large tree can start outside the usual range; allow moving back in.
        if (factor > 1 and scale <= 2.5) or (0 < factor < 1 and scale >= 0.02):
            self.scale(factor, factor)


class EquipmentMap(QWidget):
    def __init__(self, catalog, snapshot, settings, dark=True, parent=None):
        super().__init__(parent)
        self.catalog, self.snapshot = catalog, snapshot
        self.settings, self.dark = copy.deepcopy(settings), dark
        self.items = {e['key']: e for e in catalog['equipment'] if e['required']}
        self.acquired = {r['key'].removeprefix('equipment:') for r in snapshot['gallery'] if r['acquired']}
        self.materials = {r['id']: r for r in snapshot['materials']}
        self.selected_key = None
        self.material_id = None
        self.query, self.unfinished, self.consumer_keys = '', False, None
        self._selecting = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        self.group = QComboBox()
        self.group.setAccessibleName('Equipment map group')
        for title, value in [('Blades', 0), ('Scabbards', 1), ('ODM gear', 2), ('All equipment', None)]:
            self.group.addItem(title, value)
        toolbar.addWidget(self.group)
        self.jump = QComboBox()
        self.jump.setAccessibleName('Select equipment in map')
        self.jump.setMinimumContentsLength(15)
        self.jump.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        toolbar.addWidget(self.jump, 1)
        for title, callback in [('−', lambda: self.view.zoom(1/1.25)), ('+', lambda: self.view.zoom(1.25)), ('Fit tree', self.fit_tree), ('Clear highlight', self.clear_material_highlight)]:
            control = QPushButton(title)
            control.setAccessibleName({'−': 'Zoom out', '+': 'Zoom in'}.get(title, title))
            control.clicked.connect(callback)
            toolbar.addWidget(control)
        layout.addLayout(toolbar)
        split = QSplitter()
        self.scene = QGraphicsScene(self)
        self.view = MapView(self.scene)
        self.view.setAccessibleName('Equipment upgrade tree. Drag to pan. Control and wheel to zoom.')
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setMinimumWidth(240)
        split.addWidget(self.view)
        self.inspector = QTabWidget()
        self.inspector.setMinimumWidth(320)
        split.addWidget(self.inspector)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        split.setSizes([640, 360])
        layout.addWidget(split, 1)
        self.build_inspector()
        self.footer = text_label('Arrows show actual upgrade paths. Items with direct development can be separate roots. Click an item, then a recipe material to inspect sources.')
        layout.addWidget(self.footer)
        self.scene.selectionChanged.connect(self.selection_changed)
        self.group.currentIndexChanged.connect(self.rebuild)
        self.jump.activated.connect(lambda index: self.select_equipment(self.jump.itemData(index), True))
        self.rebuild()

    def build_inspector(self):
        item_page = QWidget()
        item_page.setObjectName('inspectorContent')
        item_layout = QVBoxLayout(item_page)
        item_layout.setContentsMargins(8, 10, 8, 8)
        item_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.item_title = text_label('Select equipment', 'sectionTitle')
        self.item_title.setMinimumHeight(50)
        self.item_info = text_label('')
        self.item_info.setMinimumHeight(38)
        item_layout.addWidget(self.item_title)
        item_layout.addWidget(self.item_info)
        self.recipes = QTreeWidget()
        self.recipes.setHeaderLabels(['Recipe / material', 'Need / held'])
        self.recipes.setAccessibleName('Development and upgrade materials. Activate a material for farming sources.')
        self.recipes.setAlternatingRowColors(True)
        self.recipes.setMinimumHeight(220)
        self.recipes.header().setStretchLastSection(False)
        self.recipes.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recipes.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.recipes.setColumnWidth(1, 96)
        self.recipes.itemClicked.connect(self.recipe_clicked)
        self.recipes.itemActivated.connect(self.recipe_clicked)
        item_layout.addWidget(self.recipes, 1)
        item_layout.addWidget(text_label('Click or activate a material to see where to buy or farm it. Acquired means ever owned, not currently held.'))
        item_scroll = QScrollArea()
        item_scroll.setWidgetResizable(True)
        item_scroll.setWidget(item_page)
        self.inspector.addTab(item_scroll, 'Equipment')
        material_page = QWidget()
        material_page.setObjectName('inspectorContent')
        material_layout = QVBoxLayout(material_page)
        material_layout.setContentsMargins(8, 10, 8, 8)
        material_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.material_title = text_label('Choose a recipe material', 'sectionTitle')
        self.material_title.setMinimumHeight(50)
        self.shop_info, self.drop_info = text_label(''), text_label('')
        self.shop_info.setMinimumHeight(54)
        self.drop_info.setMinimumHeight(62)
        material_layout.addWidget(self.material_title)
        material_layout.addWidget(self.shop_info)
        material_layout.addWidget(self.drop_info)
        options = QHBoxLayout()
        self.source_mode = QComboBox()
        self.source_mode.setAccessibleName('Material farming mode')
        for title, value in [('Both modes', 'both'), ('Normal', 'normal'), ('True Attack', 'true')]:
            self.source_mode.addItem(title, value)
        self.source_mode.setCurrentIndex(self.source_mode.findData(self.settings['mode']))
        self.source_mode.currentIndexChanged.connect(self.update_sources)
        options.addWidget(self.source_mode)
        self.rank = QCheckBox('S rank')
        self.rank.setChecked(self.settings['sRank'])
        self.rank.toggled.connect(self.update_sources)
        options.addWidget(self.rank)
        self.dire = QCheckBox('Dire')
        self.dire.setChecked(self.settings['dire'])
        self.dire.toggled.connect(self.update_sources)
        options.addWidget(self.dire)
        material_layout.addLayout(options)
        self.sources = QTreeWidget()
        self.sources.setRootIsDecorated(False)
        self.sources.setHeaderLabels(['Best quantified missions', 'Yield / min'])
        self.sources.setAccessibleName('Material farming sources ranked by estimated yield per minute')
        self.sources.setAlternatingRowColors(True)
        self.sources.setMinimumHeight(140)
        self.sources.header().setStretchLastSection(False)
        self.sources.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sources.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.sources.setColumnWidth(1, 96)
        material_layout.addWidget(self.sources, 1)
        self.source_note = text_label('Select a material to rank available sources.')
        self.source_note.setMinimumHeight(62)
        material_layout.addWidget(self.source_note)
        consumers = QPushButton('Highlight equipment using material')
        consumers.clicked.connect(self.highlight_consumers)
        material_layout.addWidget(consumers)
        material_scroll = QScrollArea()
        material_scroll.setWidgetResizable(True)
        material_scroll.setWidget(material_page)
        self.inspector.addTab(material_scroll, 'Material sources')

    def rebuild(self, *_):
        previous = self.selected_key
        self._selecting = True
        self.scene.clear()
        self.nodes, self.lines = {}, []
        c = DARK if self.dark else LIGHT
        self.scene.setBackgroundBrush(QColor(c['field']))
        positions, edges, headings = equipment_layout(self.catalog, self.group.currentData())
        for title, y in headings:
            heading = self.scene.addSimpleText(title, QFont('Sans Serif', 13, QFont.Weight.DemiBold))
            heading.setBrush(QColor(c['muted']))
            heading.setPos(0, y)
        for parent, child in edges:
            px, py = positions[parent]
            cx, cy = positions[child]
            start, end = QPointF(px+NODE_WIDTH, py+NODE_HEIGHT/2), QPointF(cx, cy+NODE_HEIGHT/2)
            path = QPainterPath(start)
            path.cubicTo(start+QPointF(32, 0), end-QPointF(32, 0), end)
            self.lines.append(self.scene.addPath(path, QPen(QColor(c['border']), 2)))
            arrow = QPolygonF([end, end+QPointF(-8, -4), end+QPointF(-8, 4)])
            self.lines.append(self.scene.addPolygon(arrow, QPen(Qt.PenStyle.NoPen), QColor(c['border'])))
        for key, position in positions.items():
            node = EquipmentNode(self.items[key], key in self.acquired, self.dark)
            node.setPos(*position)
            self.scene.addItem(node)
            self.nodes[key] = node
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-30, -20, 30, 30))
        self.jump.blockSignals(True)
        self.jump.clear()
        for key in self.nodes:
            self.jump.addItem(self.items[key]['name'], key)
        self.jump.blockSignals(False)
        self._selecting = False
        self.view.resetTransform()
        self.set_filter(self.query, self.unfinished, center=False)
        key = previous if previous in self.nodes else next((k for k in self.nodes if k not in self.acquired), next(iter(self.nodes), None))
        if key:
            self.select_equipment(key, True)

    def select_equipment(self, key, center=False):
        if key not in self.nodes:
            return
        self._selecting = True
        self.scene.clearSelection()
        self.nodes[key].setSelected(True)
        self.selected_key = key
        self.jump.setCurrentIndex(self.jump.findData(key))
        self._selecting = False
        if center:
            self.view.centerOn(self.nodes[key])
        item = self.items[key]
        self.item_title.setText(item['name'])
        self.item_info.setText(f'{item["group"]} · {"Acquired previously" if key in self.acquired else "Not yet acquired"}\nStats: '+ ' / '.join(map(str, item['stats'])))
        self.recipes.clear()
        for route, recipe, cost in [('Develop directly', item['develop'], item['price']), ('Upgrade', item['upgrade'], item['upgrade_price'])]:
            if not recipe:
                continue
            title = f'{route} · {cost:,} funds' if cost is not None else f'{route} · fee unknown'
            root = QTreeWidgetItem([title, ''])
            root.setToolTip(0, title)
            self.recipes.addTopLevelItem(root)
            if route == 'Upgrade':
                parent = self.items.get(f'{item["group_id"]}:{item["parent"]}')
                if parent:
                    source = QTreeWidgetItem([f'From {parent["name"]}', '1 item'])
                    source.setData(0, Qt.ItemDataRole.UserRole, ('equipment', parent['key']))
                    source.setToolTip(0, source.text(0))
                    root.addChild(source)
            for reward in recipe:
                material, quantity = reward['material'], reward['quantity']
                if material == 255 or quantity <= 0:
                    continue
                held = self.materials.get(material, {}).get('count', 0)
                row = QTreeWidgetItem([self.catalog['materials'][material], f'{quantity} / {held}'])
                row.setData(0, Qt.ItemDataRole.UserRole, ('material', material, quantity))
                row.setToolTip(0, f'{self.catalog["materials"][material]}\nNeed {quantity}; held {held}; missing {max(0, quantity-held)}. Activate for sources.')
                root.addChild(row)
            root.setExpanded(True)
        self.inspector.setCurrentIndex(0)

    def selection_changed(self):
        if self._selecting:
            return
        selected = self.scene.selectedItems()
        if selected and isinstance(selected[0], EquipmentNode):
            self.select_equipment(selected[0].equipment['key'])

    def recipe_clicked(self, row, column=0):
        data = row.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data[0] == 'equipment':
            self.select_equipment(data[1], True)
        else:
            self.show_material(data[1], data[2])

    def show_material(self, material, needed=None):
        self.material_id = material
        held = self.materials.get(material, {}).get('count', 0)
        price = self.catalog['material_prices'][material]
        available = self.materials.get(material, {}).get('shop_state', 0) >= 9 and price > 0
        self.material_title.setText(self.catalog['materials'][material])
        info = f'Held {held:,}'
        if needed is not None:
            info += f' · Recipe needs {needed:,} · Missing {max(0, needed-held):,}'
        info += f'\nBuy in the material shop for {price:,} each. Confirm stock in-game.' if available else '\nNot currently buyable in this snapshot.'
        self.shop_info.setText(info)
        self.drop_info.setText(DROP_HINTS.get(material, ''))
        self.drop_info.setVisible(material in DROP_HINTS)
        self.inspector.setCurrentIndex(1)
        self.update_sources()

    def update_sources(self, *_):
        if self.material_id is None:
            return
        settings = dict(self.settings, mode=self.source_mode.currentData(), sRank=self.rank.isChecked(), dire=self.dire.isChecked())
        rows = material_sources(self.catalog, self.snapshot, settings, self.material_id)
        self.sources.clear()
        for mission in rows:
            mode = 'True Attack' if mission['mode'] == 'true' else 'Normal'
            row = QTreeWidgetItem([f'{mission["name"]}\n{mode}', f'{mission["per_minute"]:.2f}'])
            description = f'{mission["quantity"]:g} per run · {mission["minutes"]:.1f} min/run\n{mission["evidence"]}'
            row.setToolTip(0, description)
            row.setToolTip(1, description)
            self.sources.addTopLevelItem(row)
        if rows:
            self.source_note.setText('Estimated materials/minute. Hover for run totals and timing evidence. Checked bonuses require their conditions. Unknown limb drops are excluded.')
        else:
            self.source_note.setText('No quantified rewards for these settings. Use the limb-drop hint above or record full runs. A best farming rate is not known.')

    def highlight_consumers(self):
        if self.material_id is None:
            return
        self.consumer_keys = {key for key, item in self.items.items() if any(r['material'] == self.material_id and r['quantity'] > 0 for r in item['develop']+item['upgrade'])}
        self.group.setCurrentIndex(self.group.findData(None))
        self.inspector.setCurrentIndex(1)
        self.set_filter(self.query, self.unfinished, center=False)
        self.fit_tree()

    def set_filter(self, query, unfinished=False, center=True):
        self.query, self.unfinished = query.casefold(), unfinished
        matches = []
        for key, node in self.nodes.items():
            item = self.items[key]
            haystack = item['name']+' '+recipe_text(item['develop']+item['upgrade'], self.catalog)
            matches_query = not self.query or self.query in haystack.casefold()
            match = matches_query and (not unfinished or key not in self.acquired) and (self.consumer_keys is None or key in self.consumer_keys)
            node.setOpacity(1 if match else 0.18)
            if match:
                matches.append(key)
        if center and self.query and matches:
            self.select_equipment(matches[0], True)
        if self.query and not matches:
            self.footer.setText('No matching equipment. Clear search or turn off Only unfinished to see the tree again.')
        elif self.consumer_keys is not None:
            self.footer.setText(f'{len(matches)} equipment recipes use this material in the current view. Use Clear highlight to restore all equipment.')
        else:
            self.footer.setText('Arrows are catalogue upgrade paths; direct-development items can be separate roots. Drag to pan, Ctrl+wheel to zoom. Select a material in the recipe to find sources.')

    def clear_material_highlight(self):
        self.consumer_keys = None
        self.set_filter(self.query, self.unfinished, center=False)

    def fit_tree(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_dark_mode(self, dark):
        self.dark = dark
        self.rebuild()
