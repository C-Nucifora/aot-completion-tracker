#!/usr/bin/env python3
"""Install the Linux app and its runtime independently of this checkout."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
APP_FILES = ('desktop_app.py', 'ui_theme.py', 'equipment_map.py', 'tracker_core.py', 'save_reader.py',
             'catalog.json', 'pyproject.toml', 'uv.lock', 'README.md')


def quote_exec(value):
    # Desktop Entry exec quoting is not shell quoting. Percent signs are field codes.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\'+char)
    return '"'+value+'"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-dir', type=Path, help='Optional application directory')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('This installer is for Linux. Use the portable ZIP on Windows.')
    uv = shutil.which('uv')
    if not uv:
        parser.error('Install uv first, then run this installer again.')
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    destination = (args.install_dir or data/'aot-completion-tracker/app').resolve()
    if destination == ROOT or ROOT in destination.parents:
        parser.error('Choose an installation directory outside the source checkout.')
    destination.mkdir(parents=True, exist_ok=True)
    for name in APP_FILES:
        shutil.copy2(ROOT/name, destination/name)
    shutil.copytree(ROOT/'assets', destination/'assets', dirs_exist_ok=True)
    environment = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(destination/'.venv'))
    environment.pop('VIRTUAL_ENV', None)
    subprocess.run([uv, 'sync', '--locked', '--no-dev', '--project', str(destination)],
                   env=environment, check=True)
    interpreter = destination/'.venv/bin/python'
    applications = data/'applications'
    applications.mkdir(parents=True, exist_ok=True)
    target = applications/'aot-completion-tracker.desktop'
    target.write_text('\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Name=Wings of Freedom Tracker',
        'Comment=Plan your next expedition and complete the Wings of Freedom gallery',
        f'Exec={quote_exec(interpreter)} {quote_exec(destination/"desktop_app.py")} %f',
        f'Icon={destination/"assets/notebook.svg"}', 'Terminal=false',
        'Categories=Game;', 'StartupNotify=false', 'Keywords=AOT;Titan;Completion;Farming;', '',
    ]), encoding='utf8')
    bin_dir = Path.home()/'.local/bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir/'aot-tracker'
    launcher.write_text(f'#!/bin/sh\nexec {shlex.quote(str(interpreter))} {shlex.quote(str(destination/"desktop_app.py"))} "$@"\n')
    launcher.chmod(0o755)
    update = shutil.which('update-desktop-database')
    if update:
        subprocess.run([update, str(applications)], check=False)
    print(f'Installed application: {destination}')
    print(f'Application menu: {target}')
    print(f'Command launcher: {launcher}')
    print('Existing saves and tracker sessions are unchanged. Reopen the app to use the update.')


if __name__ == '__main__':
    main()
