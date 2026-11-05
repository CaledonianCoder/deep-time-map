"""Build climate.json: temperature, CO2, O2 and ice for the Deep Time Atlas.

Sources
- PhanDA (Judd et al. 2024, Science): GMST and CO2 percentiles per stage, 485-0 Ma; latitudinal
  surface-air-temperature profiles per stage; SST profiles per climate state.
- GEOCARBSULFOR Monte Carlo (Krause et al. 2018; 2022 outputs for the 2023 AREPS review): O2 (% of
  atmosphere) median and 1-sigma band, 550-0 Ma; RCO2 used for CO2 before 485 Ma.
- Precambrian: schematic ranges only (Catling & Zahnle 2020; Lyons, Reinhard & Planavsky 2014),
  plus dated glaciations (snowballearth.org).
"""
import csv, glob, json, os
import numpy as np
import openpyxl
import scipy.io as sio

PH = '/home/claude/src/clim/PhanDA/5_Outputs'
GC = '/home/claude/src/clim/gcx/outputs_14_7_2022.mat'

# ---------------- PhanDA stage table
stages = list(csv.DictReader(open(f'{PH}/PhanDA_GMSTandCO2_percentiles.csv')))
files = {os.path.basename(x)[11:-4]: x for x in glob.glob(f'{PH}/PhanDA_LTG_percentiles/PhanDA_SATgradient_percentiles_bystage/*.csv')}
def prof(st):
    s2 = st.replace(' ', '').replace('/', '&')
    f = files.get(s2) or next((v for k, v in files.items() if s2 in k.split('&')), None)
    rows = list(csv.DictReader(open(f)))
    return [float(r['Latitude']) for r in rows], [float(r['LTG_50']) for r in rows]

LATS = list(np.arange(90, -90.1, -5.0))   # coarse output grid, north to south

def resample(lat, val):
    o = np.argsort(lat)
    return list(np.round(np.interp(LATS, np.array(lat)[o], np.array(val)[o]), 1))

# SST by climate state, mapped onto each stage by GMST
wb = openpyxl.load_workbook(f'{PH}/PhanDA_LTG_percentiles/PhanDA_SSTgradient_byclimatestate.xlsx', read_only=True)
rows = list(wb.worksheets[0].iter_rows(values_only=True)); hdr = rows[0]
wb2 = openpyxl.load_workbook(f'{PH}/PhanDA_LTG_percentiles/PhanDA_SATgradient_byclimatestate.xlsx', read_only=True)
rows2 = list(wb2.worksheets[0].iter_rows(values_only=True)); hdr2 = rows2[0]
STATES = ['Coldhouse', 'Coolhouse', 'Transitional', 'Warmhouse', 'Hothouse']
sst_state, gmst_state = {}, {}
for s in STATES:
    i = hdr.index(f'{s} P50'); lat = [r[0] for r in rows[1:] if r[0] is not None and r[i] is not None]
    sst_state[s] = (lat, [r[i] for r in rows[1:] if r[0] is not None and r[i] is not None])
    j = hdr2.index(f'{s} P50'); la2 = np.array([r[0] for r in rows2[1:] if r[0] is not None]); v2 = np.array([r[j] for r in rows2[1:] if r[0] is not None])
    w = np.cos(np.radians(la2)); gmst_state[s] = float((v2 * w).sum() / w.sum())
print('state GMST', {k: round(v, 1) for k, v in gmst_state.items()})
gs_sorted = sorted(STATES, key=lambda s: gmst_state[s])
def sst_for(g):
    xs = [gmst_state[s] for s in gs_sorted]
    if g <= xs[0]: a = b = gs_sorted[0]; f = 0
    elif g >= xs[-1]: a = b = gs_sorted[-1]; f = 0
    else:
        k = next(i for i in range(len(xs) - 1) if xs[i] <= g <= xs[i + 1]); a, b = gs_sorted[k], gs_sorted[k + 1]; f = (g - xs[k]) / (xs[k + 1] - xs[k])
    pa, pb = resample(*sst_state[a]), resample(*sst_state[b])
    return [round(max(-1.8, x + (y - x) * f), 1) for x, y in zip(pa, pb)]

def iceline(T, th=-10.0):
    """latitude (deg) poleward of which mean annual air temperature is below th, per hemisphere"""
    out = []
    for north in (True, False):
        pts = [(abs(la), t) for la, t in zip(LATS, T) if (la >= 0 if north else la <= 0)]
        pts.sort()
        line = None
        for i, (la, t) in enumerate(pts):
            if t <= th:
                if i == 0: line = 0
                else:
                    la0, t0 = pts[i - 1]; line = la0 + (t0 - th) / (t0 - t) * (la - la0)
                break
        out.append(None if line is None else round(line, 1))
    return out

ph = []
for r in stages:
    lat, sat = prof(r['Stage'])
    satc = resample(lat, sat)
    g = float(r['GMST_50'])
    ph.append(dict(stage=r['Stage'], top=float(r['UpperAge']), base=float(r['LowerAge']), age=round(float(r['AverageAge']), 3),
                   gmst=[round(float(r[k]), 2) for k in ('GMST_05', 'GMST_16', 'GMST_50', 'GMST_84', 'GMST_95')],
                   co2=[round(float(r[k])) for k in ('CO2_05', 'CO2_16', 'CO2_50', 'CO2_84', 'CO2_95')],
                   sat=satc, sst=sst_for(g), ice=iceline(satc)))
ph = [p for p in ph if p['stage'] != 'PETM'] + [p for p in ph if p['stage'] == 'PETM']  # PETM is a spike; keep it but flag
for p in ph: p['spike'] = p['stage'] == 'PETM'
ph.sort(key=lambda p: p['age'])

# ---------------- GEOCARBSULFOR O2 (and CO2 before 485 Ma)
m = sio.loadmat(GC, squeeze_me=True, struct_as_record=False)['mc_outputs']
t = -np.array(m.medians.time).ravel()
o2 = np.array(m.medians.O2_percent).ravel(); o2lo = np.array(m.min1.O2_percent).ravel(); o2hi = np.array(m.plus1.O2_percent).ravel()
rco2 = np.array(m.medians.RCO2).ravel(); rlo = np.array(m.min1.RCO2).ravel(); rhi = np.array(m.plus1.RCO2).ravel()
o = np.argsort(t)
gc = dict(t=[int(x) for x in t[o]], o2=[round(float(x), 2) for x in o2[o]], o2lo=[round(float(x), 2) for x in o2lo[o]], o2hi=[round(float(x), 2) for x in o2hi[o]],
          co2=[round(float(x) * 280) for x in rco2[o]], co2lo=[round(float(x) * 280) for x in rlo[o]], co2hi=[round(float(x) * 280) for x in rhi[o]])

# ---------------- Precambrian schematic ranges (log-interpolated between anchors)
# O2 in % of the atmosphere (modern 20.9 %); CO2 in ppm
PRE_O2 = [  # age, low, high
    (4000, 1e-6, 2e-4), (2460, 1e-6, 2e-4), (2400, 2e-3, 0.2), (2300, 0.2, 4), (2080, 0.2, 4), (2000, 2e-3, 2),
    (1800, 2e-4, 2), (850, 2e-4, 2), (750, 0.02, 4), (635, 0.2, 8), (560, 2.6, 10.8)]
PRE_CO2 = [(4000, 30000, 1000000), (3000, 10000, 300000), (2500, 3000, 100000), (1800, 1500, 50000), (1000, 1000, 30000), (750, 600, 20000), (560, 3000, 9000)]

# ---------------- glaciations (ice line latitude in degrees; 0 = ice reaching the equator)
GLACIATIONS = [
    dict(name='Pongola glaciation', a=2950, b=2900, ice=45, kind='regional'),
    dict(name='Huronian glaciations', a=2430, b=2250, ice=40, kind='regional'),
    dict(name='Makganyene snowball Earth', a=2250, b=2200, ice=0, kind='global'),
    dict(name='Sturtian snowball Earth', a=717, b=660, ice=0, kind='global'),
    dict(name='Marinoan snowball Earth', a=650, b=635, ice=0, kind='global'),
    dict(name='Gaskiers glaciation', a=582, b=579, ice=40, kind='regional'),
]

out = dict(stages=ph, gc=gc, pre_o2=PRE_O2, pre_co2=PRE_CO2, glaciations=GLACIATIONS, lats=LATS, ice_threshold=-10)
json.dump(out, open('/home/claude/build/climate.json', 'w'), separators=(',', ':'))
print('stages', len(ph), 'gc', len(gc['t']), 'bytes', os.path.getsize('/home/claude/build/climate.json'))
for p in ph[::12]: print(p['stage'], p['gmst'][2], p['co2'][2], p['ice'], p['sst'][18], p['sat'][18])
