"""Shared native Qt palettes, typography and line icons."""
from pathlib import Path
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer

DARK = dict(window='#191d21', rail='#14171a', panel='#20252a', alternate='#242a30',
            field='#151a1e', border='#353d45', text='#edf0f2', muted='#a9b2bc',
            accent='#d9b66f', hover='#2d343b', selected='#393329', ink='#191b1e')
LIGHT = dict(window='#f3f4f2', rail='#e6e9e5', panel='#ffffff', alternate='#f4f6f3',
             field='#ffffff', border='#c5ccc5', text='#202923', muted='#526056',
             accent='#795518', hover='#e3e8e2', selected='#e5dbc8', ink='#ffffff')

# One consistent 24 px line-icon set, drawn locally rather than loaded from a network.
PATHS = {
    'overview': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'pathways': '<rect x="2" y="8" width="6" height="8" rx="1"/><rect x="16" y="2" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M8 12h4V5h4m-4 7v7h4"/>',
    'equipment': '<path d="m5 3 14 14m-2-14L3 17m1-1 4 4m8-4 4 4M3 21l3-3m12 0 3 3"/>',
    'materials': '<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm-9 5 9 5 9-5m-9 5v9m-5-17 10 5"/>',
    'characters': '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    'gallery': '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-7 5 7"/>',
    'missions': '<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2V5Zm6-2v16m6-14v16"/>',
    'requests': '<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="m8 13 3 3 5-6"/>',
    'farming': '<path d="M4 20h16M7 16V9m5 7V4m5 12v-5"/><path d="m4 7 6-4m4 6 6-4"/>',
    'log': '<rect x="5" y="3" width="16" height="18" rx="2"/><path d="M3 7h4m-4 5h4m-4 5h4m4-9h6m-6 4h6m-6 4h4"/>',
    'open': '<path d="M3 8V5a2 2 0 0 1 2-2h5l3 3h6a2 2 0 0 1 2 2v1M3 9h18l-3 11H3L1 11a2 2 0 0 1 2-2Z"/>',
    'reload': '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 6a8 8 0 0 1 14 6M4 12a8 8 0 0 0 14 6"/>',
    'export': '<path d="M12 3v12m-4-8 4-4 4 4M4 14v6h16v-6"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2"/>',
    'moon': '<path d="M21 14a9 9 0 0 1-11-11 9 9 0 1 0 11 11Z"/>',
    'help': '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-2 1-2 2-2 3m0 3v.1"/>',
    'search': '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
}


def icon(name, dark=True, primary=False):
    colors = DARK if dark else LIGHT
    result = QIcon()
    for mode, color in ((QIcon.Mode.Normal, colors['ink'] if primary else colors['muted']),
                        (QIcon.Mode.Selected, colors['accent']), (QIcon.Mode.Disabled, colors['muted'])):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        QSvgRenderer(QByteArray(svg.encode())).render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(2)
        result.addPixmap(pixmap, mode)
    return result


def apply_theme(app, dark=True):
    c = DARK if dark else LIGHT
    app.setStyle('Fusion')
    palette = QPalette()
    roles = {'Window': 'window', 'WindowText': 'text', 'Base': 'panel', 'AlternateBase': 'alternate',
             'Text': 'text', 'Button': 'panel', 'ButtonText': 'text', 'Highlight': 'selected',
             'HighlightedText': 'text', 'ToolTipBase': 'panel', 'ToolTipText': 'text',
             'PlaceholderText': 'muted', 'Light': 'border', 'Mid': 'border', 'Dark': 'rail',
             'Link': 'accent', 'LinkVisited': 'accent', 'BrightText': 'text'}
    for role, key in roles.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(c[key]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c['muted']))
    app.setPalette(palette)
    font = QFont(app.font())
    font.setPointSizeF(10)
    app.setFont(font)
    check = (Path(__file__).parent/('assets/check.svg' if dark else 'assets/check-light.svg')).as_posix()
    app.setStyleSheet(f'''
        QWidget {{ color: {c['text']}; font-size: 13px; }}
        QMainWindow, QDialog, QWidget#workspace {{ background: {c['window']}; }}
        QFrame#sidebar {{ background: {c['rail']}; border-right: 1px solid {c['border']}; }}
        QLabel {{ background: transparent; }}
        QLabel#brand {{ font-size: 18px; font-weight: 650; }}
        QLabel#pageTitle {{ font-size: 27px; font-weight: 650; }}
        QLabel#muted, QLabel#pageDescription, QLabel#summary {{ color: {c['muted']}; }}
        QLabel#sectionTitle {{ font-size: 19px; font-weight: 600; }}
        QLabel#notice {{ background: {c['selected']}; padding: 12px 14px; border-radius: 6px; }}
        QLabel#emptyTitle {{ font-size: 23px; font-weight: 600; }}
        QListWidget#navigation {{ background: transparent; border: none; outline: none; padding: 0; }}
        QListWidget#navigation::item {{ padding: 0 12px; border: 1px solid transparent; border-radius: 6px; color: {c['muted']}; }}
        QListWidget#navigation::item:hover {{ background: {c['hover']}; color: {c['text']}; }}
        QListWidget#navigation::item:selected {{ background: {c['selected']}; color: {c['accent']}; border-color: {c['selected']}; }}
        QListWidget#navigation::item:focus {{ border-color: {c['accent']}; }}
        QPushButton, QToolButton {{ background: {c['panel']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 8px 12px; min-height: 16px; }}
        QPushButton:hover, QToolButton:hover {{ background: {c['hover']}; }}
        QPushButton:pressed, QToolButton:pressed {{ background: {c['selected']}; }}
        QPushButton#primary {{ background: {c['accent']}; color: {c['ink']}; border-color: {c['accent']}; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {c['accent']}; border-color: {c['text']}; }}
        QPushButton#quiet {{ background: transparent; border-color: transparent; text-align: left; color: {c['muted']}; }}
        QPushButton#quiet:hover {{ background: {c['hover']}; color: {c['text']}; }}
        QPushButton:disabled, QToolButton:disabled {{ color: {c['muted']}; background: {c['rail']}; }}
        QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{ border: 1px solid {c['accent']}; }}
        QLineEdit, QComboBox, QAbstractSpinBox {{ background: {c['field']}; border: 1px solid {c['border']}; border-radius: 5px; padding: 7px 9px; min-height: 18px; selection-background-color: {c['selected']}; }}
        QComboBox::drop-down {{ border: none; width: 22px; }}
        QComboBox QAbstractItemView {{ background: {c['panel']}; border: 1px solid {c['border']}; selection-background-color: {c['selected']}; padding: 4px; }}
        QCheckBox {{ spacing: 8px; padding: 3px 0; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; background: {c['field']}; border: 1px solid {c['border']}; border-radius: 3px; }}
        QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; image: url("{check}"); }}
        QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
        QCheckBox:focus {{ color: {c['accent']}; }}
        QCheckBox:disabled {{ color: {c['muted']}; }}
        QCheckBox::indicator:disabled {{ background: {c['rail']}; border-color: {c['border']}; }}
        QScrollArea {{ background: transparent; border: none; }}
        QWidget#inspectorContent {{ background: {c['window']}; }}
        QTreeWidget, QGraphicsView {{ background: {c['panel']}; alternate-background-color: {c['alternate']}; border: 1px solid {c['border']}; border-radius: 6px; selection-background-color: {c['selected']}; selection-color: {c['text']}; }}
        QTreeWidget::item {{ padding: 7px 3px; }}
        QTreeWidget::item:selected {{ background: {c['selected']}; }}
        QTableView {{ background: {c['panel']}; alternate-background-color: {c['alternate']}; border: 1px solid {c['border']}; border-radius: 6px; selection-background-color: {c['selected']}; selection-color: {c['text']}; outline: none; }}
        QTableView::item {{ padding: 6px 10px; border-bottom: 1px solid {c['border']}; }}
        QTableView::item:focus {{ border: 1px solid {c['accent']}; }}
        QHeaderView::section {{ background: {c['panel']}; color: {c['muted']}; border: none; border-bottom: 1px solid {c['border']}; padding: 10px; font-size: 12px; font-weight: 600; text-align: left; }}
        QTableCornerButton::section {{ background: {c['panel']}; border: none; }}
        QTabWidget::pane {{ border: none; background: transparent; padding-top: 10px; }}
        QTabBar::tab {{ background: transparent; color: {c['muted']}; padding: 10px 14px; border-bottom: 2px solid transparent; }}
        QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; }}
        QTabBar::tab:hover {{ background: {c['hover']}; }}
        QGroupBox {{ border: 1px solid {c['border']}; border-radius: 6px; margin-top: 10px; padding: 12px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; color: {c['muted']}; }}
        QScrollBar:vertical {{ background: {c['panel']}; width: 10px; margin: 1px; }}
        QScrollBar:horizontal {{ background: {c['panel']}; height: 10px; margin: 1px; }}
        QScrollBar::handle {{ background: {c['border']}; border-radius: 4px; min-height: 28px; min-width: 28px; }}
        QScrollBar::handle:hover {{ background: {c['muted']}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QProgressBar {{ background: {c['border']}; border: none; border-radius: 3px; height: 6px; max-height: 6px; }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
        QMenu {{ background: {c['panel']}; border: 1px solid {c['border']}; padding: 6px; }}
        QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 4px; }}
        QMenu::item:selected {{ background: {c['selected']}; }}
        QMenu::separator {{ height: 1px; background: {c['border']}; margin: 6px; }}
        QToolTip {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px; }}
        QStatusBar {{ background: {c['rail']}; color: {c['muted']}; border-top: 1px solid {c['border']}; padding: 3px 12px; font-size: 11px; }}
        QStatusBar::item {{ border: none; }}
        QFrame#separator {{ background: {c['border']}; max-height: 1px; border: none; }}
    ''')
