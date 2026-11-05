"""Merge PBDB-derived exports into compact per-group fossil occurrence data for the map."""
import csv, gzip, json, base64, collections, sys
import numpy as np

SRC = '/home/claude/src'
csv.field_size_limit(10**9)

# ---------------------------------------------------------------- display units
# id, label, section, icon, colour, default-on, kind
UNITS = [
 # Dinosaurs: iconic genera
 ('diplodocus','Diplodocus','Dinosaurs','delapouite_diplodocus','#2f7d5b',1,'genus'),
 ('brachiosaurus','Brachiosaurus & Giraffatitan','Dinosaurs','delapouite_sauropod-head','#4e8f3a',1,'genus'),
 ('stegosaurus','Stegosaurus','Dinosaurs','delapouite_stegosaurus-scales','#b5532d',1,'genus'),
 ('allosaurus','Allosaurus','Dinosaurs','delapouite_t-rex-skull','#a8322d',1,'genus'),
 ('tyrannosaurus','Tyrannosaurus','Dinosaurs','lorc_dinosaur-rex','#c0262b',1,'genus'),
 ('velociraptor','Velociraptor','Dinosaurs','delapouite_velociraptor','#d0582a',1,'genus'),
 ('triceratops','Triceratops','Dinosaurs','delapouite_triceratops-head','#8a5a2b',1,'genus'),
 ('parasaurolophus','Parasaurolophus','Dinosaurs','delapouite_parasaurolophus','#a77a1d',1,'genus'),
 # Dinosaurs: wider groups
 ('sauropods','Other sauropods','Dinosaurs','caro-asercion_sauropod-skeleton','#5f9c7d',1,'group'),
 ('theropods','Other theropods','Dinosaurs','lorc_dinosaur-rex','#d97a6a',1,'group'),
 ('ornithopods','Ornithopods & hadrosaurs','Dinosaurs','delapouite_parasaurolophus','#c99a45',1,'group'),
 ('ceratopsians','Horned & dome-headed dinosaurs','Dinosaurs','delapouite_triceratops-head','#a98463',1,'group'),
 ('armoured','Stegosaurs & ankylosaurs','Dinosaurs','delapouite_stegosaurus-scales','#c98a6a',1,'group'),
 # Sea and sky reptiles
 ('pteranodon','Pteranodon','Sea & sky reptiles','delapouite_pterodactylus','#6a4fa3',1,'genus'),
 ('pterosaurs','Other pterosaurs','Sea & sky reptiles','delapouite_pterodactylus','#9a87c9',1,'group'),
 ('plesiosaurs','Plesiosaurs & kin','Sea & sky reptiles','delapouite_plesiosaurus','#2a6fa8',1,'group'),
 ('ichthyosaurs','Ichthyosaurs','Sea & sky reptiles','delapouite_dolphin','#3f8fbf',1,'group'),
 ('mosasaurs','Mosasaurs','Sea & sky reptiles','delapouite_fish-monster','#1f5a87',1,'group'),
 ('crocs','Crocodile relatives','Sea & sky reptiles','lorc_croc-jaws','#5b7a3a',1,'group'),
 ('turtles','Turtles','Sea & sky reptiles','lorc_turtle','#6d8b5e',1,'group'),
 ('squamates','Lizards & snakes','Sea & sky reptiles','lorc_gecko','#8fa35a',0,'group'),
 # Early land animals
 ('dimetrodon','Dimetrodon','Early land animals','delapouite_dimetrodon','#b0413e',1,'genus'),
 ('synapsids','Other synapsids','Early land animals','delapouite_dimetrodon','#c9806b',1,'group'),
 ('amphibians','Amphibians & early tetrapods','Early land animals','lorc_salamander','#6f9a4a',1,'group'),
 ('insects','Insects','Early land animals','lorc_dragonfly','#7d6f2c',1,'group'),
 # Mammals and birds
 ('mammoth','Mammoths','Mammals & birds','delapouite_mammoth','#7a4a2a',1,'genus'),
 ('proboscideans','Elephants & mastodons','Mammals & birds','delapouite_mammoth','#a07858',1,'group'),
 ('smilodon','Smilodon','Mammals & birds','delapouite_saber-toothed-cat-head','#b26a1e',1,'genus'),
 ('carnivorans','Carnivores','Mammals & birds','lorc_wolf-head','#8c6d4f',1,'group'),
 ('hoofed','Hoofed mammals','Mammals & birds','delapouite_bison','#9b7d4a',1,'group'),
 ('whales','Whales & sea cows','Mammals & birds','delapouite_sperm-whale','#2c6e8a',1,'group'),
 ('mammals','Other mammals','Mammals & birds','delapouite_mouse','#a3927c',1,'group'),
 ('archaeopteryx','Archaeopteryx','Mammals & birds','caro-asercion_archaeopteryx-fossil','#7b5ea7',1,'genus'),
 ('birds','Birds','Mammals & birds','delapouite_ostrich','#6d7fa6',1,'group'),
 # Fish
 ('sharks','Sharks & rays','Fish','delapouite_shark-fin','#3d6b8f',1,'group'),
 ('armourfish','Armoured & jawless fish','Fish','lorc_angler-fish','#6b5a8f',1,'group'),
 ('bonyfish','Bony fish','Fish','delapouite_tropical-fish','#3f8f8a',1,'group'),
 ('conodonts','Conodonts','Fish','delapouite_eel','#7d8c95',0,'group'),
 # Invertebrates
 ('trilobites','Trilobites','Invertebrates','lorc_trilobite','#8f5b2e',1,'group'),
 ('eurypterids','Sea scorpions','Invertebrates','lorc_scorpion','#9a3c55',1,'group'),
 ('ammonites','Ammonites','Invertebrates','lorc_ammonite','#b07a2a',1,'group'),
 ('nautiloids','Nautiloids','Invertebrates','faithtoken_nautilus-shell','#9c6b4e',1,'group'),
 ('belemnites','Belemnites & squid','Invertebrates','delapouite_giant-squid','#a5566f',1,'group'),
 ('corals','Corals','Invertebrates','delapouite_coral','#c5604f',0,'group'),
 ('brachiopods','Brachiopods','Invertebrates','lorc_gold-shell','#a08a52',0,'group'),
 ('bivalves','Clams & oysters','Invertebrates','delapouite_oyster','#8a8f6a',0,'group'),
 ('snails','Snails','Invertebrates','lorc_snail','#8f7a6a',0,'group'),
 ('echinoderms','Sea urchins & crinoids','Invertebrates','delapouite_sea-urchin','#b0647a',0,'group'),
]
UIDX = {u[0]: i for i, u in enumerate(UNITS)}

GENUS_UNIT = {
 'Diplodocus':'diplodocus','Brachiosaurus':'brachiosaurus','Giraffatitan':'brachiosaurus',
 'Stegosaurus':'stegosaurus','Allosaurus':'allosaurus','Tyrannosaurus':'tyrannosaurus',
 'Velociraptor':'velociraptor','Triceratops':'triceratops','Parasaurolophus':'parasaurolophus',
 'Pteranodon':'pteranodon','Dimetrodon':'dimetrodon','Mammuthus':'mammoth','Smilodon':'smilodon',
 'Archaeopteryx':'archaeopteryx',
}
PETRA_GROUP = {'sauropod':'sauropods','theropod':'theropods','oviraptorosaur':'theropods',
 'ornithomimosaur':'theropods','ornithopod':'ornithopods','hadrosaur':'ornithopods',
 'ceratopsian':'ceratopsians','pachycephalosaur':'ceratopsians','stegosaur':'armoured',
 'ankylosaur':'armoured','bird':'birds'}

AMMON = {'Ammonitida','Goniatitida','Ceratitida','Prolecanitida','Phylloceratida','Agoniatitida',
 'Clymeniida','Lytoceratida','Ancyloceratida','Anarcestida','Ammonoidea','Tornoceratida'}
BELEM = {'Belemnitida','Aulacoceratida','Teuthida','Sepiida','Octopoda','Phragmoteuthida',
 'Diplobelida','Vampyromorpha','Spirulida','Belemnoidea','Hematitida'}
SYNAPSID_ORD = {'Dicynodontia','Therocephalia','Cynodontia','Biarmosuchia','Dinocephalia','Gorgonopsia',
 'Eupelycosauria','Pelycosauria','Theromorpha','Caseasauria','Ophiacodontia','Sphenacodontia',
 'Edaphosauria','Therapsida','Anomodontia','Synapsida','Cryptodontia'}
EARLYTET_ORD = {'Temnospondyli','Anthracosauria','Anthracosauromorpha','Cotylosauria','Seymouriamorpha',
 'Lepospondyli','Microsauria','Nectridea','Aistopoda','Embolomeri','Diadectomorpha','Ichthyostegalia'}
PLESIO = {'Plesiosauria','Eosauropterygia','Nothosauria','Placodontia','Sauropterygia','Pistosauroidea'}
ARMOURFISH = {'Placodermi','Pteraspidomorpha','Osteostraci','Cephalaspidomorphi','Agnatha','Acanthodii',
 'Galeaspida','Thelodonti','Anaspida','Heterostraci','Cephalaspidomorpha','Pteraspidomorphi'}
HOOFED = {'Artiodactyla','Perissodactyla','Notoungulata','Litopterna','Condylarthra','Astrapotheria',
 'Pyrotheria','Embrithopoda','Hyracoidea','Panameriungulata','Dinocerata','Desmostylia','Tillodontia',
 'Pantodonta','Procreodi','Acreodi','Mesonychia','Arctocyonia'}

# clade names used as accepted_name in the reptile export
NAME_UNIT = {}
for n in ['Plesiosauria','Elasmosauridae','Pliosauridae','Polycotylidae','Cryptoclididae','Plesiosauroidea',
          'Pliosauroidea','Sauropterygia','Nothosauria','Nothosauridae','Placodontia','Eosauropterygia',
          'Leptocleididae','Rhomaleosauridae','Pistosauroidea','Plesiosauridae']: NAME_UNIT[n]='plesiosaurs'
for n in ['Ichthyosauria','Ichthyosauridae','Ophthalmosauridae','Ichthyopterygia','Ichthyosauromorpha',
          'Shastasauridae','Mixosauridae','Leptonectidae','Stenopterygiidae','Platypterygiinae','Parvipelvia']: NAME_UNIT[n]='ichthyosaurs'
for n in ['Mosasauridae','Mosasaurinae','Tylosaurinae','Plioplatecarpinae','Mosasauroidea','Halisaurinae','Mosasauria']: NAME_UNIT[n]='mosasaurs'
for n in ['Pterosauria','Pterodactyloidea','Pteranodontidae','Azhdarchidae','Rhamphorhynchidae','Ornithocheiridae',
          'Ornithocheiroidea','Pteranodontoidea','Azhdarchoidea','Ctenochasmatidae','Rhamphorhynchoidea',
          'Anhangueridae','Tapejaridae','Dsungaripteridae','Pterodactylidae','Nyctosauridae','Pteranodontia']: NAME_UNIT[n]='pterosaurs'
for n in ['Crocodylia','Crocodyliformes','Crocodylomorpha','Eusuchia','Alligatoridae','Crocodylidae','Gavialidae',
          'Goniopholididae','Mesoeucrocodylia','Notosuchia','Thalattosuchia','Neosuchia','Alligatoroidea',
          'Crocodyloidea','Atoposauridae','Pholidosauridae','Dyrosauridae','Teleosauridae','Metriorhynchidae',
          'Crocodylinae','Alligatorinae','Caimaninae','Gavialoidea','Tomistominae','Sebecidae','Peirosauridae',
          'Paralligatoridae','Bernissartiidae','Allodaposuchidae','Phytosauria','Parasuchidae']: NAME_UNIT[n]='crocs'
for n in ['Testudines','Testudinata','Trionychidae','Cryptodira','Pleurodira','Baenidae','Chelidae','Testudinidae',
          'Emydidae','Cheloniidae','Adocidae','Kinosternidae','Chelydridae','Geoemydidae','Bothremydidae',
          'Podocnemididae','Pelomedusidae','Dermochelyidae','Nanhsiungchelyidae','Macrobaenidae','Trionychinae',
          'Testudinoidea','Chelonioidea','Trionychoidea','Pan-Testudines','Testudo','Trionyx','Chelonia']: NAME_UNIT[n]='turtles'
for n in ['Lacertilia','Squamata','Serpentes','Anguidae','Iguanidae','Varanidae','Scincidae','Lacertidae','Gekkonidae',
          'Colubridae','Boidae','Viperidae','Elapidae','Teiidae','Amphisbaenia','Agamidae','Madtsoiidae','Booidea',
          'Anguimorpha','Iguania','Scincomorpha','Colubroidea','Natricinae','Polyglyphanodontinae']: NAME_UNIT[n]='squamates'

def class_unit(phylum, cls, order, family, genus):
    if genus in GENUS_UNIT: return GENUS_UNIT[genus]
    if family == 'Mosasauridae': return 'mosasaurs'
    if order in SYNAPSID_ORD or cls in ('Synapsida','Therapsida'): return 'synapsids'
    if order in EARLYTET_ORD or cls == 'Amphibia': return 'amphibians'
    if cls == 'Mammalia':
        if order == 'Proboscidea': return 'proboscideans'
        if order in ('Carnivora','Hyaenodonta','Creodonta'): return 'carnivorans'
        if order in ('Cetacea','Sirenia'): return 'whales'
        if order in HOOFED: return 'hoofed'
        return 'mammals'
    if cls == 'Aves': return 'birds'
    if cls == 'Reptilia':
        if order == 'Pterosauria': return 'pterosaurs'
        if order in PLESIO: return 'plesiosaurs'
        if order == 'Ichthyosauria': return 'ichthyosaurs'
        if order == 'Crocodylia' or order == 'Phytosauria': return 'crocs'
        if order == 'Testudines': return 'turtles'
        if order == 'Squamata': return 'squamates'
        if family in NAME_UNIT: return NAME_UNIT[family]
        return None
    if cls in ('Saurischia','Ornithischia'): return None  # dinosaurs come from the classified dinosaur export
    if cls == 'Chondrichthyes': return 'sharks'
    if cls in ARMOURFISH: return 'armourfish'
    if cls in ('Osteichthyes','Actinopterygii','Sarcopterygii','Actinistia','Dipnoi'): return 'bonyfish'
    if cls == 'Conodonta': return 'conodonts'
    if cls == 'Trilobita': return 'trilobites'
    if order == 'Eurypterida': return 'eurypterids'
    if cls == 'Insecta': return 'insects'
    if cls == 'Cephalopoda':
        if order in AMMON: return 'ammonites'
        if order in BELEM: return 'belemnites'
        return 'nautiloids'
    if cls == 'Anthozoa': return 'corals'
    if phylum == 'Brachiopoda': return 'brachiopods'
    if cls == 'Bivalvia': return 'bivalves'
    if cls == 'Gastropoda': return 'snails'
    if phylum == 'Echinodermata': return 'echinoderms'
    return None

def fnum(x):
    try: return float(x)
    except: return None

occ = {}  # occurrence_no -> (unit, genus, lng, lat, max, min, source)
def add(no, unit, genus, lng, lat, mx, mn, src):
    if unit is None or lng is None or lat is None or mx is None or mn is None: return
    if mx > 541 or mx < mn or abs(lat) > 85: return
    if no in occ: return
    occ[no] = (unit, genus, lng, lat, mx, mn, src)

# 1) classified dinosaur + bird export (petra)
g = json.load(open(f'{SRC}/petra/public/data/dinosaurs.geojson'))['features']
for f in g:
    p = f['properties']; lng, lat = f['geometry']['coordinates'][:2]
    genus = p.get('taxonomyGenus') or (p.get('name') or '').split(' ')[0]
    if genus in ('NO_GENUS_SPECIFIED', ''): genus = ''
    unit = GENUS_UNIT.get(genus) or PETRA_GROUP.get(p['group'])
    add('o' + str(p['id']), unit, genus, lng, lat, fnum(p['max_ma']), fnum(p['min_ma']), 'dino')
print('after dinosaurs', len(occ), file=sys.stderr)

# 2) broad PBDB export with taxonomy (Heim lab)
gtax = {}
for r in csv.DictReader(gzip.open(f'{SRC}/pbs/PBDB_Occurrences/pbdb_occs.csv.gz', 'rt')):
    genus = r['genus_name'] or ''
    if r['class'] == 'Reptilia' and genus: gtax[genus] = (r['order'], r['family'])
    u = class_unit(r['phylum'], r['class'], r['order'], r['family'], genus)
    add('o' + r['occurrence_no'], u, genus, fnum(r['lng']), fnum(r['lat']), fnum(r['max_ma']), fnum(r['min_ma']), 'pbdb')
print('after broad', len(occ), file=sys.stderr)

# 3) reptile export (dinotime): marine reptiles, pterosaurs, crocs, turtles
for r in csv.DictReader(open(f'{SRC}/dinotime/scripts/data/pbdb_data_reptilia.csv')):
    name = r['accepted_name']; rank = r['accepted_rank']
    genus = name.split(' ')[0] if rank in ('genus','species','subgenus','subspecies') else ''
    u = GENUS_UNIT.get(genus) if genus in ('Pteranodon','Dimetrodon') else None
    if not u: u = NAME_UNIT.get(name)
    if not u and genus in gtax:
        o, fam = gtax[genus]
        u = class_unit('Chordata', 'Reptilia', o, fam, genus)
    add('o' + r['occurrence_no'], u, genus, fnum(r['lng']), fnum(r['lat']), fnum(r['max_ma']), fnum(r['min_ma']), 'rept')
print('after reptiles', len(occ), file=sys.stderr)

cnt = collections.Counter(v[0] for v in occ.values())
for u in UNITS: print(f'{u[0]:16s}{cnt[u[0]]:8d}', file=sys.stderr)

# ---------------------------------------------------------------- aggregate
genera = collections.Counter(v[1] for v in occ.values() if v[1])
gnames = [''] + sorted(genera)
gid = {n: i for i, n in enumerate(gnames)}
agg = collections.Counter()
for (u, ge, lng, lat, mx, mn, src) in occ.values():
    key = (UIDX[u], round(lng * 2) , round(lat * 2), round(mx * 10), round(mn * 10), gid.get(ge, 0))
    agg[key] += 1
keys = sorted(agg)
A = np.array(keys, dtype=np.int64); N = np.array([agg[k] for k in keys], dtype=np.int64)
print('aggregated records', len(A), file=sys.stderr)

unit = A[:, 0].astype(np.uint8)
lngq = A[:, 1].astype(np.int16)   # lng*2
latq = A[:, 2].astype(np.int16)   # lat*2
mxq = A[:, 3].astype(np.uint16)   # Ma*10
mnq = A[:, 4].astype(np.uint16)
gq = A[:, 5].astype(np.uint16)
nq = np.minimum(N, 65535).astype(np.uint16)

# ---------------------------------------------------------------- time series & peaks
H = 2.5  # half window, Myr
T = np.arange(0, 542)
mx = mxq / 10.0; mn = mnq / 10.0
span = np.maximum(mx - mn, 0.1)
series = np.zeros((len(UNITS), len(T)), dtype=np.float64)
peak5 = np.zeros(len(UNITS))
cell5 = ((np.floor((lngq / 2.0 + 180) / 5)).astype(np.int64) * 40 + np.floor((latq / 2.0 + 90) / 5).astype(np.int64))
for ui in range(len(UNITS)):
    sel = unit == ui
    if not sel.any(): continue
    m1, m0, s, n, c = mx[sel], mn[sel], span[sel], nq[sel].astype(float), cell5[sel]
    _, cinv = np.unique(c, return_inverse=True)
    for ti, t in enumerate(T):
        ov = np.clip(np.minimum(m1, t + H) - np.maximum(m0, t - H), 0, None)
        e = n * np.minimum(ov / s, 1.0)
        series[ui, ti] = e.sum()
        if e.any():
            peak5[ui] = max(peak5[ui], np.bincount(cinv, weights=e).max())

def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
out = {
  'units': [dict(id=u[0], label=u[1], section=u[2], icon=u[3], color=u[4], on=u[5], kind=u[6],
                 total=int(cnt[u[0]]), peak=round(float(peak5[i]), 3),
                 series=[round(float(x), 2) for x in series[i]]) for i, u in enumerate(UNITS)],
  'genera': gnames,
  'n': int(len(A)), 'H': H,
  'cols': {k: b64(v) for k, v in dict(unit=unit, lng=lngq, lat=latq, mx=mxq, mn=mnq, g=gq, n=nq).items()},
  'occurrences': int(len(occ)),
}
json.dump(out, open('/home/claude/build/fossils.json', 'w'), separators=(',', ':'))
print('written', len(json.dumps(out)) // 1024, 'KB', file=sys.stderr)
