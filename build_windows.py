#!/usr/bin/env python3
"""Build a portable Windows x64 ZIP with Python and Qt, without personal data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
PYTHON_URL = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
PYTHON_SHA256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'


def download(url, target, expected):
    if not target.exists():
        with urllib.request.urlopen(url, timeout=60) as response, target.open('wb') as output:
            shutil.copyfileobj(response, output)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch: {target}. Remove it and retry.')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Build directory outside the source repository')
    args = parser.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error('Keep binary bundles outside the source repository')
    out.mkdir(parents=True, exist_ok=True)
    cache = out/'downloads'
    cache.mkdir(exist_ok=True)
    lock = tomllib.loads((ROOT/'uv.lock').read_text())
    sources = [(PYTHON_URL, PYTHON_SHA256)]
    for name in ('pyside6-essentials', 'shiboken6'):
        package = next(p for p in lock['package'] if p['name'] == name)
        wheel = next(w for w in package['wheels'] if w['url'].endswith('win_amd64.whl'))
        sources.append((wheel['url'], wheel['hash'].removeprefix('sha256:')))
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        bundle = Path(temporary)/'WingsOfFreedomTracker'
        runtime = bundle/'runtime'
        runtime.mkdir(parents=True)
        manifest = []
        for index, (url, digest) in enumerate(sources):
            path = download(url, cache/url.rsplit('/', 1)[1], digest)
            destination = runtime if index == 0 else runtime/'Lib/site-packages'
            with zipfile.ZipFile(path) as archive:
                archive.extractall(destination)
            manifest.append(dict(url=url, sha256=digest))
        (runtime/'python312._pth').write_text('python312.zip\n.\nLib\\site-packages\n..\nimport site\n', encoding='utf8')
        for name in ('desktop_app.py', 'tracker_core.py', 'save_reader.py', 'catalog.json', 'launch-native.cmd', 'WINDOWS.md'):
            shutil.copy2(ROOT/name, bundle/name)
        shutil.copytree(ROOT/'assets', bundle/'assets')
        (bundle/'runtime-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        archive_path = out/'WingsOfFreedomTracker-windows-x64.zip'
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle.parent))
    print(archive_path)
    print('SHA256', hashlib.sha256(archive_path.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
