#!/usr/bin/env python3
"""Read original Wings of Freedom PC saves. Never writes to the source file."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct

SIZE = 0xBBE20
ROOT = Path(__file__).resolve().parent

def decrypt(data):
    if len(data) != SIZE:
        raise ValueError(f'Expected {SIZE} bytes for the original PC game; got {len(data)}')
    expected, state = struct.unpack_from('<HH', data)
    result = bytearray(data)
    for offset in range(4, len(data), 4):
        for _ in range(3):
            state = (state * 0x5B1A7851 + 0xCE4E) & 0xFFFFFFFF
        struct.pack_into('<I', result, offset, struct.unpack_from('<I', data, offset)[0] ^ state)
    actual = sum(v[0] for v in struct.iter_unpack('<H', result[4:])) & 65535
    if actual != expected:
        raise ValueError('Checksum mismatch: unsupported, incomplete or corrupt save')
    return bytes(result)

def parse(data, catalog):
    b = decrypt(data)
    u32 = lambda o: struct.unpack_from('<I', b, o)[0]
    result = {'schema_version': 1, 'game': catalog['game'], 'checksum_valid': True,
              'sha256': hashlib.sha256(data).hexdigest(), 'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'summary': {'funds': u32(0x654), 'total_kills': u32(0x64C),
                          'save_summary_raw': b[4:0x40].split(b'\0')[0].decode('ascii', 'replace')},
              'characters': [], 'materials': [], 'inventory': [], 'gallery': [], 'missions': [], 'requests': []}
    for i, name in enumerate(catalog['characters']):
        o = 0x249F0 + i * 240
        result['characters'].append({'id': i, 'name': name, 'level': 1 + u32(o+0x84) + u32(o+0xD8),
                                    'kills': u32(o+0x40), 'missions': u32(o+0x48), 'xp': u32(o+0x80),
                                    'extra_xp': u32(o+0xD4), 'attributes': list(struct.unpack_from('<6H', b, o+0x70)),
                                    'offset': hex(o), 'raw': b[o:o+240].hex()})
    result['character_kills_match_global'] = sum(x['kills'] for x in result['characters']) == result['summary']['total_kills']
    for i, name in enumerate(catalog['materials']):
        if not name or name.lower() == 'dummy':
            continue
        o = 0x362C0 + i*48
        result['materials'].append({'id': i, 'name': name, 'count': u32(o), 'shop_state': u32(o+4), 'offset': hex(o)})
    equipment = {e['key']: e for e in catalog['equipment']}
    for group in range(3):
        for slot in range(100):
            o = 0x257C0 + group*0x1900 + slot*64
            i = b[o]
            if i == 255:
                continue
            e = equipment.get(f'{group}:{i}', {})
            result['inventory'].append({'key': f'{group}:{i}', 'group': group, 'slot': slot, 'id': i,
                                        'name': e.get('name', f'Unknown item {i}'), 'fortification': b[o+1],
                                        'offset': hex(o), 'raw': b[o:o+64].hex()})
    for e in catalog['gallery']:
        flag = b[e['offset']]
        result['gallery'].append({**e, 'acquired': bool(flag & (35 if e.get('accept_bit32') else 3)), 'raw_flag': flag})
    for mode in range(2):
        for mission in catalog['missions']:
            o = 0xA70 + mode*0xE880 + mission['id']*96
            result['missions'].append({'id': mission['id'], 'mode': ['normal', 'true'][mode], 'name': mission['name'],
                                       'completed': bool(b[o] & 32), 'time_seconds': None if u32(o+8) == 0xFFFFFFFF else u32(o+8),
                                       'raw_flag': b[o], 'raw_rank': b[o+2], 'offset': hex(o), 'raw': b[o:o+96].hex()})
        for i, name in enumerate(catalog['requests']):
            o = 0x40AC8+i*2+mode
            result['requests'].append({'id': i, 'mode': ['normal', 'true'][mode], 'name': name,
                                      'completed': b[o] == 3, 'state': b[o], 'offset': hex(o)})
    done = sum(e['acquired'] for e in result['gallery'])
    result['summary'].update(gallery_done=done, gallery_total=len(result['gallery']), gallery_percent=done*100//len(result['gallery']))
    result['coverage'] = {'verified': ['decryption checksum', 'material quantities', 'inventory and gallery acquisition',
                                      'character levels kills and battles', 'request completion', 'mission completion flags'],
                          'needs_confirmation': ['mission time may be personal best rather than average', 'star fortification',
                                                 'rank names', 'some history model labels'],
                          'not_in_save': ['future random drop rate', 'real completion ETA without run samples']}
    return result, b

def csv_export(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            safe = {}
            for k,v in row.items():
                v = json.dumps(v) if isinstance(v, (dict, list)) else v
                # Spreadsheet formula injection protection for user-edited snapshots.
                if isinstance(v, str) and v[:1] in ('=', '+', '-', '@'):
                    v = "'" + v
                safe[k] = v
            writer.writerow(safe)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('save', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='Private output folder outside the public repository')
    args = parser.parse_args()
    source = args.save.resolve()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error('Keep personal exports outside the public source repository')
    if out == source.parent or out in source.parents:
        parser.error('Output must not contain the source save')
    original = source.read_bytes()
    if original != source.read_bytes():
        parser.error('Save changed while reading; retry after the game finishes saving')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = out / stamp
    out.mkdir(parents=True, exist_ok=False)
    backup = out / source.name
    backup.write_bytes(original)
    if backup.read_bytes() != original:
        raise OSError('Backup verification failed')
    backup.chmod(0o400)
    catalog = json.loads((ROOT/'catalog.json').read_text())
    result, raw = parse(original, catalog)
    (out/'snapshot.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'decrypted.bin').write_bytes(raw)
    for section in ['characters', 'materials', 'inventory', 'gallery', 'missions', 'requests']:
        csv_export(out/(section+'.csv'), result[section])
    csv_export(out/'missing-gallery.csv', [x for x in result['gallery'] if not x['acquired']])
    with (out/'raw-list.txt').open('w', encoding='utf8') as f:
        f.write(json.dumps(result['summary'], indent=2)+'\n\n')
        for section in ['characters', 'materials', 'inventory', 'gallery', 'missions', 'requests']:
            f.write(section.upper()+'\n')
            for row in result[section]:
                f.write(json.dumps({k:v for k,v in row.items() if k != 'raw'}, ensure_ascii=False)+'\n')
            f.write('\n')
    with (out/'raw-words.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['offset_hex', 'bytes_hex', 'u32_le'])
        for o in range(0, len(raw), 4):
            writer.writerow([hex(o), raw[o:o+4].hex(), struct.unpack_from('<I', raw, o)[0]])
    (out/'manifest.json').write_text(json.dumps({'source': str(source), 'backup': str(backup), 'sha256': result['sha256'],
                                              'checksum_valid': True, 'bytes': len(original)}, indent=2))
    print(json.dumps({'output': str(out), 'summary': result['summary'], 'character_kills_match_global': result['character_kills_match_global']}, indent=2))

if __name__ == '__main__':
    main()
