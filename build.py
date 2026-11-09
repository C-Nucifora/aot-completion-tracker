#!/usr/bin/env python3
"""Build the public page or a private standalone tracker snapshot."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--snapshot',type=Path)
p.add_argument('--out',type=Path)
a=p.parse_args()
html=(ROOT/'index.template.html').read_text().replace('__CATALOG__',(ROOT/'catalog.json').read_text().replace('</','<\\/'))
if a.snapshot:
 if not a.out:p.error('--snapshot requires a private --out destination')
 if a.out.resolve()==ROOT or ROOT in a.out.resolve().parents:p.error('Personal output must be outside the public repository')
 snapshot=json.loads(a.snapshot.read_text())
 if snapshot.get('schema_version')!=1: p.error('Unsupported snapshot')
 html=html.replace('<script src="planner.js"></script>', '<script>'+ (ROOT/'planner.js').read_text().replace('</','<\\/')+'</script>')
 initial='<script>window.initialAOTProfile='+json.dumps({'name':'Save snapshot','snapshot':snapshot}).replace('</','<\\/')+';</script>'
 html=html.replace('<script src="app.js"></script>',initial+'<script>'+(ROOT/'app.js').read_text().replace('</','<\\/')+'</script>')
 html=html.replace('href="docs/save-format.md"','href="https://github.com/C-Nucifora/aot-completion-tracker/blob/main/docs/save-format.md"')
output=a.out or ROOT/'index.html';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(html);print(output)
