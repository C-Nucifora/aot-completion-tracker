"""Data validation and planning shared by the native tracker views."""
import copy
import math
import re
from collections import defaultdict

SECTIONS = ('characters', 'materials', 'inventory', 'gallery', 'missions', 'requests')
DROP_HINTS = {
    52: 'Ordinary Titans in late True Attack missions; harvest material-bearing limbs. Try Provide Relief to the Forward Town!',
    57: 'Normal-mode Dire Titans, including early story missions',
    58: 'Higher-level normal-mode Dire Titans',
    59: 'True Attack Dire Titans; try Sign of a Counterattack',
    60: 'Female Titan in normal Choices and Consequences or Soldiers Dance',
    61: 'Female Titan in True Attack Choices and Consequences or Soldiers Dance',
    62: 'Armored Titan in normal All Men, Move Out!',
    63: 'Armored Titan in True Attack All Men, Move Out!; sever limbs before the nape',
    64: 'Beast Titan Dire target in normal Choices and Consequences',
    65: 'Beast Titan Dire target in True Attack Choices and Consequences',
    66: 'Colossal Titan in normal Last Line of Defense',
    67: 'Colossal Titan in True Attack Last Line of Defense',
}


def defaults():
    return dict(sRank=True, dire=False, useInventory=False, defaultMinutes=10,
                cleanupHours=None, buyShop=True, mode='both', goal='all', samples=[], overrides={})


def integer(value, maximum=0xFFFFFFFF):
    return type(value) is int and 0 <= value <= maximum


def finite(value, minimum, maximum):
    return type(value) in (int, float) and minimum <= value <= maximum and math.isfinite(value)


def validate_snapshot(snapshot, catalog):
    if not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1 or snapshot.get('game') != catalog['game'] or snapshot.get('checksum_valid') is not True:
        raise ValueError('Unsupported snapshot. Open an original Wings of Freedom save or tracker export.')
    for section in SECTIONS:
        rows = snapshot.get(section)
        if not isinstance(rows, list) or len(rows) > 2000 or any(not isinstance(r, dict) for r in rows):
            raise ValueError(f'Invalid {section} list')
    summary = snapshot.get('summary', {})
    if not isinstance(summary, dict) or not all(integer(summary.get(k)) for k in ('funds', 'total_kills')):
        raise ValueError('Invalid save summary')
    gallery_keys = {r['key'] for r in catalog['gallery']}
    mission_ids = {m['id'] for m in catalog['missions']}
    for section in SECTIONS:
        seen = set()
        for row in snapshot[section]:
            identity = (row.get('mode'), row.get('key', row.get('id')))
            if section == 'inventory':
                identity = (row.get('group'), row.get('slot'))
            try:
                if identity in seen:
                    raise ValueError(f'Duplicate {section} record')
                seen.add(identity)
            except TypeError as exc:
                raise ValueError(f'Invalid {section} identity') from exc
            if not isinstance(row.get('name'), str) or len(row['name']) > 1000:
                raise ValueError(f'Invalid {section} name')
            if section == 'characters':
                if not all(integer(row.get(k)) for k in ('id', 'level', 'kills', 'missions', 'xp')) or not isinstance(row.get('attributes'), list) or len(row['attributes']) != 6 or not all(integer(n) for n in row['attributes']):
                    raise ValueError('Invalid character counters')
            elif section == 'materials':
                if not all(integer(row.get(k)) for k in ('id', 'count', 'shop_state')) or row['id'] >= len(catalog['materials']):
                    raise ValueError('Invalid material counters')
            elif section == 'inventory':
                if not all(integer(row.get(k)) for k in ('id', 'fortification', 'group', 'slot')) or row.get('key') not in {e['key'] for e in catalog['equipment']}:
                    raise ValueError('Invalid inventory record')
            elif section == 'gallery':
                if row.get('key') not in gallery_keys or type(row.get('acquired')) is not bool or not all(integer(row.get(k)) for k in ('offset', 'raw_flag')) or not isinstance(row.get('section'), str):
                    raise ValueError('Invalid gallery record')
            elif section == 'missions':
                if 'time_seconds' not in row or row.get('id') not in mission_ids or row.get('mode') not in ('normal', 'true') or type(row.get('completed')) is not bool or (row.get('time_seconds') is not None and not integer(row['time_seconds'])):
                    raise ValueError('Invalid mission record')
            elif section == 'requests':
                if not integer(row.get('id')) or not integer(row.get('state')) or row.get('mode') not in ('normal', 'true') or type(row.get('completed')) is not bool:
                    raise ValueError('Invalid request record')


def valid_settings(value, catalog):
    if not isinstance(value, dict):
        raise ValueError('Invalid tracker settings')
    settings = defaults()
    settings.update(value)
    if settings['goal'] not in ('all', 'perfected', 'rozen') or settings['mode'] not in ('both', 'normal', 'true'):
        raise ValueError('Invalid planning selection')
    for key in ('sRank', 'dire', 'useInventory', 'buyShop'):
        if type(settings[key]) is not bool:
            raise ValueError(f'Invalid setting: {key}')
    if not finite(settings['defaultMinutes'], 0.1, 1440) or (settings['cleanupHours'] is not None and not finite(settings['cleanupHours'], 0, 10000)):
        raise ValueError('Invalid planning duration')
    samples = settings['samples']
    if not isinstance(samples, list) or len(samples) > 10000:
        raise ValueError('Invalid run history')
    keys = {f'{mode}:{m["id"]}' for mode in ('normal', 'true') for m in catalog['missions']}
    for sample in samples:
        if not isinstance(sample, dict) or sample.get('key') not in keys or not finite(sample.get('minutes'), 0.1, 1440) or not isinstance(sample.get('materials'), dict) or not sample['materials']:
            raise ValueError('Invalid run sample')
        for key, amount in sample['materials'].items():
            if not isinstance(key, str) or not key.isdecimal() or int(key) >= len(catalog['materials']) or not catalog['materials'][int(key)] or not finite(amount, 0, 1000000):
                raise ValueError('Invalid run material or quantity')
    overrides = settings['overrides']
    if not isinstance(overrides, dict) or len(overrides) > 10000:
        raise ValueError('Invalid corrections')
    for key, value in overrides.items():
        if not re.fullmatch(r'gallery\|[^|]+\|acquired|materials\|\d+\|count|characters\|\d+\|(level|kills|missions)', key) or not (type(value) is bool if key.endswith('|acquired') else integer(value, 10**9)):
            raise ValueError('Invalid tracker correction')
    return settings


def load_profile(data, name, catalog):
    if not isinstance(data, dict):
        raise ValueError('Expected a tracker JSON object')
    profile = copy.deepcopy(data if 'snapshot' in data else dict(name=name, snapshot=data, settings=defaults()))
    validate_snapshot(profile['snapshot'], catalog)
    profile['settings'] = valid_settings(profile.get('settings', {}), catalog)
    if not isinstance(profile.get('name'), str):
        profile['name'] = name
    return profile


def corrected(profile):
    snapshot = copy.deepcopy(profile['snapshot'])
    for path, value in profile['settings']['overrides'].items():
        group, key, field = path.split('|')
        row = next((r for r in snapshot[group] if str(r.get('key', r.get('id'))) == key), None)
        if row is not None:
            row[field] = value
    return snapshot


def recipe_text(recipe, catalog):
    return ', '.join(f'{r["quantity"]:g} {catalog["materials"][r["material"]]}' for r in recipe if r['material'] != 255 and r['quantity'] > 0) or 'None'


def crafting(catalog, snapshot, selected, allow_inventory=False):
    items = {e['key']: e for e in catalog['equipment']}
    done = {r['key'].removeprefix('equipment:') for r in snapshot['gallery'] if r['acquired']}
    pool, totals = defaultdict(int), defaultdict(int)
    steps, blocked = [], []
    if allow_inventory:
        for row in snapshot['inventory']:
            if not row['fortification']:
                pool[row['key']] += 1

    def make(key, trail=()):
        if pool[key] > 0:
            return True
        item = items.get(key)
        if item is None or key in trail:
            blocked.append(key)
            return False
        if item['develop']:
            recipe, route = item['develop'], 'Develop'
        elif item['parent'] != 255 and item['upgrade']:
            parent = f'{item["group_id"]}:{item["parent"]}'
            if not make(parent, (*trail, key)):
                return False
            pool[parent] -= 1
            recipe, route = item['upgrade'], 'Upgrade'
        else:
            blocked.append(item['name'])
            return False
        for row in recipe:
            totals[row['material']] += row['quantity']
        steps.append(dict(key=key, name=item['name'], route=route, materials=recipe,
                          price=item['price'] if route == 'Develop' else item['upgrade_price']))
        done.add(key)
        pool[key] += 1
        return True

    for key in selected:
        if key not in done:
            make(key)
    held = {r['id']: r['count'] for r in snapshot['materials']}
    deficits = [dict(id=i, name=catalog['materials'][i], total=n, held=held.get(i, 0), need=max(0, n-held.get(i, 0))) for i, n in sorted(totals.items())]
    return dict(steps=steps, deficits=deficits, blocked=list(dict.fromkeys(blocked)),
                fundsKnown=all(s['price'] is not None for s in steps), craftingFunds=sum(s['price'] or 0 for s in steps))


def effective_missions(catalog, snapshot, settings):
    records = {(m['mode'], m['id']): m for m in snapshot['missions']}
    rows = []
    for mode in ('normal', 'true'):
        if settings['mode'] not in ('both', mode):
            continue
        for mission in catalog['missions']:
            key = f'{mode}:{mission["id"]}'
            samples = [s for s in settings['samples'] if s['key'] == key]
            record = records.get((mode, mission['id']), {})
            yields = defaultdict(float)
            if samples:
                minutes = sum(s['minutes'] for s in samples)/len(samples)
                for sample in samples:
                    for material, quantity in sample['materials'].items():
                        yields[int(material)] += quantity/len(samples)
                evidence = f'{len(samples)} observed whole runs'
            else:
                minutes = record['time_seconds']/60*1.25 if record.get('time_seconds') else settings['defaultMinutes']
                rewards = [*mission['rewards'][mode]]
                if settings['sRank']:
                    rewards.append(mission['s_rank'][mode])
                if settings['dire']:
                    rewards.append(mission['dire'][mode])
                for reward in rewards:
                    if reward['material'] != 255 and reward['quantity'] > 0:
                        yields[reward['material']] += reward['quantity']
                evidence = 'saved time × 1.25; table yields' if record.get('time_seconds') else 'default duration; table yields'
            rows.append(dict(key=key, name=mission['name'], mode=mode, minutes=minutes, yields=dict(yields), evidence=evidence))
    return rows


def allocate(deficits, missions):
    left = {r['id']: r['need'] for r in deficits if r['need'] > 0}
    rows = {}
    for _ in range(100000):
        if not any(n > 1e-8 for n in left.values()):
            break
        best, score = None, 0
        for mission in missions:
            if not finite(mission['minutes'], 0.000001, 1440):
                continue
            gain = sum(min(left.get(i, 0), q)/max(1, left.get(i, 0)) for i, q in mission['yields'].items() if math.isfinite(q) and q > 0)
            value = gain/mission['minutes']
            if value > score:
                best, score = mission, value
        if best is None:
            break
        row = rows.setdefault(best['key'], dict(best, runs=0))
        row['runs'] += 1
        for material, quantity in best['yields'].items():
            if quantity > 0 and material in left:
                left[material] = max(0, left[material]-quantity)
    return dict(rows=list(rows.values()), minutes=sum(r['runs']*r['minutes'] for r in rows.values()),
                uncovered=[dict(id=i, need=q) for i, q in left.items() if q > 1e-8])


def farming_plan(catalog, snapshot, settings):
    missing = {r['key'] for r in snapshot['gallery'] if not r['acquired']}
    selected = [e for e in catalog['equipment'] if e['required'] and 'equipment:'+e['key'] in missing and (settings['goal'] == 'all' or e['name'].startswith(settings['goal'].capitalize()))]
    craft = crafting(catalog, snapshot, [e['key'] for e in selected], settings['useInventory'])
    buyable = {r['id'] for r in snapshot['materials'] if r['shop_state'] >= 9}
    plan = allocate([r for r in craft['deficits'] if not settings['buyShop'] or r['id'] not in buyable], effective_missions(catalog, snapshot, settings))
    cost = sum(r['need']*catalog['material_prices'][r['id']] for r in craft['deficits'] if settings['buyShop'] and r['id'] in buyable)
    return dict(craft=craft, plan=plan, buyable=buyable, shopCost=cost,
                fundsGap=max(0, craft['craftingFunds']+cost-snapshot['summary']['funds']), goals=len(selected))
