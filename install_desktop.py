#!/usr/bin/env python3
"""Install a user-local application menu entry for this checkout."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def quote_exec(value):
    # Desktop Entry exec quoting is not shell quoting. Percent signs are field codes.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\'+char)
    return '"'+value+'"'


def main():
    from PySide6 import __version__
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    applications = data/'applications'
    applications.mkdir(parents=True, exist_ok=True)
    target = applications/'aot-completion-tracker.desktop'
    # Keep the venv path: resolving its symlink would bypass installed PySide6.
    interpreter = Path(sys.executable).absolute()
    target.write_text('\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Name=Wings of Freedom Tracker',
        'Comment=Read saves and plan crafting and farming for A.O.T. Wings of Freedom',
        f'Exec={quote_exec(interpreter)} {quote_exec(ROOT/"desktop_app.py")} %f',
        f'Icon={ROOT/"assets/notebook.svg"}', 'Terminal=false',
        'Categories=Game;', 'StartupNotify=true', 'Keywords=AOT;Titan;Completion;Farming;', '',
    ]), encoding='utf8')
    print(f'Installed {target} using Qt bindings {__version__}')
    print('Open Wings of Freedom Tracker from your application menu.')


if __name__ == '__main__':
    main()
