"""v19 data fixes: add Mesozoic mammals (PBDB, Mammaliaformes, Triassic-Cretaceous) to the v19 records.

Inputs: v19/fossils.json, v19/paleo_pts.json, mesozoic_mammals.json (genus|lng*2|lat*2|max*10|min*10|formation|env|n)
Outputs: v19_fixed/fossils.json, v19_fixed/paleo_pts.json (same record order), copied over v19/.
Run once on the v19 data as first published; running it on already-fixed data would add nothing new
(duplicates are skipped) but is unnecessary.
"""
import json, base64, math, re, sys, collections
import numpy as np

src = open('/home/claude/build/build_data_v16.py').read()
exec(src[src.index('ENV_CLASSES = ['):src.index('MARINE_UNITS =')])   # env_class(), ENV_CLASSES

d = json.load(open('v19/fossils.json')); c = d['cols']
T = {'unit': np.uint8, 'lng': np.int16, 'lat': np.int16, 'mx': np.uint16, 'mn': np.uint16, 'g': np.uint16, 'f': np.uint16, 'e': np.uint8, 'r': np.uint8, 'n': np.uint16}
C = {k: np.frombuffer(base64.b64decode(c[k]), t).astype(np.int64) for k, t in T.items()}
pp = json.load(open('v19/paleo_pts.json'))
PL = np.frombuffer(base64.b64decode(pp['plng']), np.int16).astype(np.int64)
PT = np.frombuffer(base64.b64decode(pp['plat']), np.int16).astype(np.int64)

genera, forms = list(d['genera']), list(d['formations'])
uidx = {u['id']: i for i, u in enumerate(d['units'])}
MAM = uidx['mammals']

rows = json.load(open('mesozoic_mammals.json'))
# skip records already in the data (same genus, cell and age)
have = set(zip(C['g'].tolist(), C['lng'].tolist(), C['lat'].tolist(), C['mx'].tolist()))
newg = sorted({r[0] for r in rows} - set(genera)); newf = sorted({r[5] for r in rows if r[5]} - set(forms))
G2 = [''] + sorted(set(genera[1:]) | set(newg)); F2 = [''] + sorted(set(forms[1:]) | set(newf))
gmap = np.array([G2.index(x) if i == 0 else 0 for i, x in enumerate(genera)])
gi2 = {n: i for i, n in enumerate(G2)}; fi2 = {n: i for i, n in enumerate(F2)}
gmap = np.array([gi2[x] for x in genera]); fmap = np.array([fi2[x] for x in forms])
C['g'] = gmap[C['g']]; C['f'] = fmap[C['f']]
have = set(zip(C['g'].tolist(), C['lng'].tolist(), C['lat'].tolist(), C['mx'].tolist()))

add = {k: [] for k in T}; skipped = 0
for g, lng2, lat2, mx10, mn10, fo, env, n in rows:
    lng2, lat2, mx10, mn10, n = int(lng2), int(lat2), int(mx10), int(mn10), int(n)
    if mx10 < mn10: mx10, mn10 = mn10, mx10
    if (gi2[g], lng2, lat2, mx10) in have: skipped += 1; continue
    ec, rl = env_class(env)
    for k, v in zip(T, [MAM, lng2, lat2, mx10, mn10, gi2[g], fi2.get(fo, 0), ec, 0 if rl is None else rl, n]): add[k].append(v)
print('new records', len(add['unit']), 'skipped duplicates', skipped, 'new genera', len(newg), file=sys.stderr)

# palaeo-positions for the new records (same method as build_paleo.py)
import pygplates
P = '/home/claude/src/plates/pyGplates-PALEOMAP-old/PALEOMAP_Global_Plate_Model/'
rm = pygplates.RotationModel(P + 'PALEOMAP_PlateModel.rot')
part = pygplates.PlatePartitioner(pygplates.FeatureCollection(P + 'PALEOMAP_PlatePolygons.gpml'), rm)
def rotpt(lng, lat, age):
    pt = pygplates.PointOnSphere(max(-89.9, min(89.9, lat)), lng)
    pl = part.partition_point(pt); pid = pl.get_feature().get_reconstruction_plate_id() if pl else 0
    q = rm.get_rotation(float(age), pid, anchor_plate_id=0) * pt
    la, lo = q.to_lat_lon(); return lo, la
npl, npt = [], []
for lng2, lat2, mx10, mn10 in zip(add['lng'], add['lat'], add['mx'], add['mn']):
    lo, la = rotpt(lng2 / 2, lat2 / 2, min((mx10 + mn10) / 20, 1100))
    npl.append(round(lo * 10)); npt.append(round(la * 10))

for k in T: C[k] = np.concatenate([C[k], np.array(add[k], dtype=np.int64)])
PL = np.concatenate([PL, npl]); PT = np.concatenate([PT, npt])
order = np.lexsort([C[k] for k in reversed(['unit', 'lng', 'lat', 'mx', 'mn', 'g', 'f', 'e', 'r'])])
for k in T: C[k] = C[k][order]
PL, PT = PL[order], PT[order]

# move synapsids and early mammal relatives that the source files filed with the early tetrapods
eco = json.load(open('pbdb_ecology.json'))
SYN_FAM = set("""Traversodontidae Gorgonopidae Tritylodontidae Varanopidae Caseidae Tapinocephalidae Tritheledontidae Ophiacodontidae Burnetiidae
Galesauridae Sphenacodontidae Brasilodontidae Chiniquodontidae Anteosauridae Edaphosauridae Trirachodontidae Charassognathidae Dromatheriidae
Eothyrididae Phthinosuchidae Therioherpetidae Titanosuchidae Tappenosauridae Rhopalodontidae Diademodontidae Driveriidae Mastersoniidae
Estemmenosuchidae Inostranceviidae Cistecynodontidae Procynosuchidae Lumkuiidae""".split())
MAM_FAM = {'Kuehneotheriidae', 'Haramiyidae', 'Haramiyaviidae'}
AMPH, SYN = uidx['amphibians'], uidx['synapsids']
moved = collections.Counter()
for gi_, name in enumerate(G2):
    fam = (eco.get(name) or {}).get('family')
    to = SYN if fam in SYN_FAM else MAM if fam in MAM_FAM else None
    if to is None: continue
    m = (C['g'] == gi_) & (C['unit'] == AMPH)
    if m.any(): C['unit'][m] = to; moved[d['units'][to]['id']] += int(m.sum())
print('moved records', dict(moved), file=sys.stderr)
order = np.lexsort([C[k] for k in reversed(['unit', 'lng', 'lat', 'mx', 'mn', 'g', 'f', 'e', 'r'])])
for k in T: C[k] = C[k][order]
PL, PT = PL[order], PT[order]

# recompute series and peaks for the groups that changed (same method as build_data_v16.py)
def winH(t): return 2.5 if t <= 541 else 10.0 if t <= 1000 else 25.0
BOUNDS = [66.0, 201.4, 251.9, 358.9, 443.8]
def win(t):
    h = winH(t); lo, hi = t - h, t + h
    for b in BOUNDS:
        if t < b < hi: hi = b
        if lo < b < t: lo = b
    return lo, hi
for UI in (MAM, AMPH, SYN):
    sel = C['unit'] == UI
    m1, m0 = C['mx'][sel] / 10, C['mn'][sel] / 10; sp = np.maximum(m1 - m0, 0.1); n = C['n'][sel].astype(float)
    cell = (np.floor((C['lng'][sel] / 2 + 180) / 5) * 40 + np.floor((C['lat'][sel] / 2 + 90) / 5)).astype(np.int64)
    _, cinv = np.unique(cell, return_inverse=True)
    ser, peak = [], 0.0
    for t in d['T']:
        lo, hi = win(t); ov = np.clip(np.minimum(m1, hi) - np.maximum(m0, lo), 0, None); e = n * np.minimum(ov / sp, 1)
        ser.append(round(float(e.sum()), 2))
        if e.any(): peak = max(peak, float(np.bincount(cinv, weights=e).max()))
    u = d['units'][UI]; u['series'] = ser; u['peak'] = round(peak, 3); u['total'] = int(n.sum())

b64 = lambda a, t: base64.b64encode(np.ascontiguousarray(a.astype(t)).tobytes()).decode()
d['cols'] = {k: b64(C[k], t) for k, t in T.items()}
d['genera'], d['formations'] = G2, F2
d['n'] = int(len(C['unit'])); d['occurrences'] += int(sum(add['n']))
d['trace_genera'] = [x for x in d['trace_genera'] if x in gi2]
import os; os.makedirs('v19_fixed', exist_ok=True)
json.dump(d, open('v19_fixed/fossils.json', 'w'), separators=(',', ':'))
pp['plng'] = b64(PL, np.int16); pp['plat'] = b64(PT, np.int16)
json.dump(pp, open('v19_fixed/paleo_pts.json', 'w'), separators=(',', ':'))
print('records', d['n'], 'genera', len(G2), file=sys.stderr)
