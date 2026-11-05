"""Reconstruct the Deep Time Atlas to ancient plate positions with the PALEOMAP model (Scotese 2016).

Outputs (in v18/):
  paleo_pts.json   palaeo-longitude/latitude of every aggregated fossil record, rotated to its mid-age
  land/<age>.json  today's land outlines rotated to each time step
  paleo_meta.json  list of time steps and rotated extinction sites
"""
import json, base64, math, os, sys, time
import numpy as np
import pygplates

P = '/home/claude/src/plates/pyGplates-PALEOMAP-old/PALEOMAP_Global_Plate_Model/'
OUT = '/home/claude/build/v18'
MAXAGE = 1100.0
rm = pygplates.RotationModel(P + 'PALEOMAP_PlateModel.rot')
static = pygplates.FeatureCollection(P + 'PALEOMAP_PlatePolygons.gpml')
partitioner = pygplates.PlatePartitioner(static, rm)

# ---------------------------------------------------------------- fossil records
d = json.load(open('/home/claude/build/v17/fossils.json'))
c = d['cols']
lng = np.frombuffer(base64.b64decode(c['lng']), np.int16) / 2.0
lat = np.frombuffer(base64.b64decode(c['lat']), np.int16) / 2.0
mx = np.frombuffer(base64.b64decode(c['mx']), np.uint16) / 10.0
mn = np.frombuffer(base64.b64decode(c['mn']), np.uint16) / 10.0
N = len(lng)
age = np.clip((mx + mn) / 2, 0, MAXAGE)

t0 = time.time()
# plate id per unique present-day location
locs = {}
for i in range(N):
    k = (lng[i], lat[i])
    if k not in locs: locs[k] = None
print('unique locations', len(locs), file=sys.stderr)
for k in locs:
    pt = pygplates.PointOnSphere(max(-89.9, min(89.9, k[1])), k[0])
    plate = partitioner.partition_point(pt)
    locs[k] = plate.get_feature().get_reconstruction_plate_id() if plate else 0
print('plate ids', round(time.time() - t0, 1), 's', file=sys.stderr)

# rotation per (plate, age to nearest 0.5 Myr); apply as a 3x3 matrix
def quat_to_mat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
rcache = {}
def rot(plate, a):
    k = (plate, a)
    if k not in rcache:
        fr = rm.get_rotation(a, plate, anchor_plate_id=0)
        if fr.represents_identity_rotation(): rcache[k] = np.eye(3)
        else:
            plat_, plon_, ang = fr.get_lat_lon_euler_pole_and_angle_degrees()
            p_, l_, th = math.radians(plat_), math.radians(plon_), math.radians(ang)
            ux, uy, uz = math.cos(p_) * math.cos(l_), math.cos(p_) * math.sin(l_), math.sin(p_)
            K = np.array([[0, -uz, uy], [uz, 0, -ux], [-uy, ux, 0]])
            rcache[k] = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * (K @ K)
    return rcache[k]

plng = np.zeros(N, np.float32); plat = np.zeros(N, np.float32)
phi, lam = np.radians(lat), np.radians(lng)
xyz = np.stack([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)], 1)
groups = {}
for i in range(N):
    groups.setdefault((locs[(lng[i], lat[i])], round(age[i] * 2) / 2), []).append(i)
print('rotation groups', len(groups), file=sys.stderr)
for (plate, a), idx in groups.items():
    idx = np.array(idx)
    v = xyz[idx] @ rot(plate, a).T
    plat[idx] = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
    plng[idx] = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
print('points rotated', round(time.time() - t0, 1), 's', file=sys.stderr)

# sanity check against PBDB's own GPlates palaeocoordinates is not available here; check a known case instead:
k = (np.abs(lng - (-106.5)) < 1) & (np.abs(lat - 47) < 1) & (mx < 70) & (mn > 64)
if k.any(): print('Hell Creek palaeo-lat/lng', float(np.median(plat[k])), float(np.median(plng[k])), file=sys.stderr)

os.makedirs(OUT + '/land', exist_ok=True)
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
json.dump({'plng': b64(np.round(plng * 10).astype(np.int16)), 'plat': b64(np.round(plat * 10).astype(np.int16)), 'maxAge': MAXAGE,
           'model': 'PALEOMAP (Scotese 2016)'}, open(OUT + '/paleo_pts.json', 'w'), separators=(',', ':'))

# ---------------------------------------------------------------- land outlines
# split today's land along plate boundaries in lon/lat (shapely), then rotate each piece with its plate
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
land = make_valid(shape(json.load(open('/tmp/claude-0/land50m.geojson'))['features'][0]['geometry']))
wrapper = pygplates.DateLineWrapper()
feats = []
for f in static:
    pid = f.get_reconstruction_plate_id()
    for g in f.get_geometries():
        if not isinstance(g, pygplates.PolygonOnSphere): continue
        for wp in wrapper.wrap(g, tessellate_degrees=1.0):
            pts = [(p.get_longitude(), p.get_latitude()) for p in wp.get_exterior_points()]
            if len(pts) < 3: continue
            pp = make_valid(Polygon(pts))
            piece = land.intersection(pp)
            if piece.is_empty: continue
            geoms = piece.geoms if hasattr(piece, 'geoms') else [piece]
            for q in geoms:
                if not isinstance(q, Polygon) or q.area < 0.02: continue
                ring = list(q.exterior.coords)
                try: poly = pygplates.PolygonOnSphere([(la, lo) for lo, la in ring[:-1]])
                except Exception: continue
                nf = pygplates.Feature(); nf.set_geometry(poly); nf.set_reconstruction_plate_id(pid); feats.append(nf)
parted = feats
print('land pieces', len(parted), round(time.time() - t0, 1), 's', file=sys.stderr)

STEPS = list(range(0, 545, 5)) + list(range(550, 1001, 10)) + list(range(1025, 1101, 25))
def enc(rings):
    # rings of [lng, lat] -> flat int arrays (x10), first point absolute then deltas
    out = []
    for r in rings:
        a = np.round(np.array(r) * 10).astype(np.int32)
        dlt = np.vstack([a[:1], np.diff(a, axis=0)])
        out.append(dlt.ravel().tolist())
    return out
total = 0
for st in STEPS:
    rec = []
    pygplates.reconstruct(parted, rm, rec, float(st))
    rings = []
    for r in rec:
        g = r.get_reconstructed_geometry()
        pts = [(p.to_lat_lon()[1], p.to_lat_lon()[0]) for p in (g.get_exterior_ring_points() if hasattr(g, "get_exterior_ring_points") else g.get_points())]
        if len(pts) < 3: continue
        # thin very dense rings a little
        if len(pts) > 60: pts = pts[::2]
        rings.append(pts + [pts[0]])
    s = json.dumps(enc(rings), separators=(',', ':'))
    open(f'{OUT}/land/{st}.json', 'w').write(s); total += len(s)
print('land steps', len(STEPS), 'total KB', total // 1024, round(time.time() - t0, 1), 's', file=sys.stderr)

# ---------------------------------------------------------------- extinction sites (rotated to the event age)
SITES = {'Gondwanan ice sheet|445': (5, 26), 'Kellwasser black shales|372.2': (10.4, 51.8), 'Emeishan Traps|259.5': (103, 26),
         'Siberian Traps|251.9': (98, 66), 'CAMP basalts|201.4|0': (-78, 38), 'CAMP basalts|201.4|1': (-7, 31), 'CAMP basalts|201.4|2': (-48, -6),
         'Karoo basalts|183': (27, -30), 'Chicxulub impact|66': (-89.5, 21.3), 'Deccan Traps|66': (74, 19)}
ext = {}
for k, (lo, la) in SITES.items():
    a = float(k.split('|')[1])
    pt = pygplates.PointOnSphere(la, lo)
    pl = partitioner.partition_point(pt); pid = pl.get_feature().get_reconstruction_plate_id() if pl else 0
    q = rm.get_rotation(a, pid) * pt
    ext[k] = [round(q.to_lat_lon()[1], 2), round(q.to_lat_lon()[0], 2)]
json.dump({'steps': STEPS, 'ext': ext, 'maxAge': MAXAGE}, open(OUT + '/paleo_meta.json', 'w'))
print('ext', ext, file=sys.stderr)
