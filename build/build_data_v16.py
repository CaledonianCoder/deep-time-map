"""Merge PBDB-derived exports into compact per-group fossil occurrence data for the map."""
import csv, gzip, json, base64, collections, sys
import numpy as np

SRC = '/home/claude/src'
csv.field_size_limit(10**9)

# ---------------------------------------------------------------- display units
# id, label, section, icon, colour, default-on, kind
UNITS = [
 # Dinosaurs, grouped at the "Option B" level (PBDB taxonomy); tracks, eggs and teeth go to their clade
 ('diplodocoids','Diplodocoids','Dinosaurs','delapouite_diplodocus','#2f7d5b',1,'group'),
 ('macronarians','Brachiosaurs, camarasaurs & titanosaurs','Dinosaurs','delapouite_sauropod-head','#4e8f3a',1,'group'),
 ('sauropodomorphs','Early & other sauropodomorphs','Dinosaurs','caro-asercion_sauropod-skeleton','#7aa88a',1,'group'),
 ('stegosaurs','Stegosaurs','Dinosaurs','delapouite_stegosaurus-scales','#b5532d',1,'group'),
 ('ankylosaurs','Ankylosaurs & early armoured','Dinosaurs','delapouite_armadillo','#8f6a4a',1,'group'),
 ('ceratosaurs','Ceratosaurs & abelisaurs','Dinosaurs','lorc_dinosaur-rex','#c7703a',1,'group'),
 ('carnosaurs','Allosaurs, megalosaurs & spinosaurs','Dinosaurs','delapouite_t-rex-skull','#a8322d',1,'group'),
 ('tyrannosaurs','Tyrannosaurs','Dinosaurs','lorc_dinosaur-rex','#c0262b',1,'group'),
 ('raptors','Raptors: dromaeosaurs & troodontids','Dinosaurs','delapouite_velociraptor','#d0582a',1,'group'),
 ('coelurosaurs','Ostrich mimics, oviraptors & kin','Dinosaurs','delapouite_ostrich','#c4864a',1,'group'),
 ('theropods','Other theropods & theropod tracks','Dinosaurs','delapouite_velociraptor-tracks','#d97a6a',1,'group'),
 ('ceratopsians','Ceratopsians','Dinosaurs','delapouite_triceratops-head','#8a5a2b',1,'group'),
 ('pachys','Pachycephalosaurs','Dinosaurs','darkzaitzev_ram','#9a7a6a',1,'group'),
 ('hadrosaurs','Hadrosaurs','Dinosaurs','delapouite_parasaurolophus','#c98a1e',1,'group'),
 ('ornithopods','Iguanodonts & small ornithischians','Dinosaurs','delapouite_parasaurolophus','#d9b56a',1,'group'),
 ('otherdinos','Earliest & unplaced dinosaurs','Dinosaurs','lorc_dinosaur-egg','#a89a8a',1,'group'),
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
 ('birds','Birds','Mammals & birds','delapouite_eagle-head','#6d7fa6',1,'group'),
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
 ('ediacarans','Ediacaran biota','Invertebrates','lorc_leaf-skeleton','#8a6f9a',1,'group'),
 # Plants (all off by default)
 ('earlyplants','Early land plants','Plants','lorc_sprout','#7fa34a',0,'group'),
 ('lycopsids','Clubmosses & scale trees','Plants','delapouite_tree-roots','#4f7a3a',0,'group'),
 ('horsetails','Horsetails','Plants','delapouite_bamboo','#6b9a3c',0,'group'),
 ('ferns','Ferns','Plants','delapouite_fern','#3f8a4f',0,'group'),
 ('glossopteris','Glossopteris','Plants','delapouite_solid-leaf','#8a7a2a',0,'genus'),
 ('seedferns','Other seed ferns','Plants','lorc_leaf-swirl','#9a8f3f',0,'group'),
 ('cycads','Cycads & bennettites','Plants','delapouite_palm-tree','#5f8f2f',0,'group'),
 ('ginkgos','Ginkgos','Plants','delapouite_ginkgo-leaf','#a6a21f',0,'group'),
 ('conifers','Conifers & kin','Plants','lorc_pine-tree','#2f6a4a',0,'group'),
 ('angiosperms','Flowering plants','Plants','lorc_lotus-flower','#c0567f',0,'group'),
 ('mosses','Mosses & liverworts','Plants','delapouite_grass','#7a9a5a',0,'group'),
 # Microbes, algae and plankton (all off by default)
 ('stromatolites','Stromatolites & microbial reefs','Microbes & plankton','delapouite_stone-stack','#7d8a5a',0,'group'),
 ('cyanobacteria','Cyanobacteria & microbes','Microbes & plankton','delapouite_stone-pile','#4f9a8a',0,'group'),
 ('algae','Red & green algae','Microbes & plankton','delapouite_algae','#3f9a6a',0,'group'),
 ('fungi','Fungi','Microbes & plankton','delapouite_mushrooms','#9a7a5a',0,'group'),
 ('acritarchs','Acritarchs','Microbes & plankton','lorc_barbed-sun','#8a7aa0',0,'group'),
 ('dinoflagellates','Dinoflagellates','Microbes & plankton','lorc_pollen-dust','#a0705a',0,'group'),
 ('radiolarians','Radiolarians','Microbes & plankton','lorc_snowflake-2','#5a7ab0',0,'group'),
 ('diatoms','Diatoms','Microbes & plankton','lorc_radial-balance','#6a9ab0',0,'group'),
 ('forams','Foraminifera','Microbes & plankton','lorc_spiked-shell','#b08a5a',0,'group'),
 ('coccoliths','Coccolithophores','Microbes & plankton','lorc_cog','#9aa0b0',0,'group'),
]
UIDX = {u[0]: i for i, u in enumerate(UNITS)}
PARENT = {'glossopteris':'seedferns', 
 'pteranodon':'pterosaurs','dimetrodon':'synapsids','mammoth':'proboscideans','smilodon':'carnivorans','archaeopteryx':'birds'}

GENUS_UNIT = {
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
    if cls in ('Saurischia','Ornithischia'): ch = chain_of(genus) or chain_of(family); return clade_unit(ch) if ch is not None else 'otherdinos'
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
ENV_CLASSES = ['', 'rivers & floodplains', 'lakes', 'swamps', 'deserts', 'caves & fissures', 'tar seeps', 'glacial',
               'coasts & lagoons', 'reefs', 'shallow seas', 'offshore & deep water']
ENV_REALM = [None, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
def env_class(e):
    e = (e or '').strip('" ').lower()
    if not e: return 0, None
    if e == 'terrestrial indet.': return 0, 0
    if e == 'marine indet.': return 0, 1
    if e == 'tar': return 6, 0
    if e == 'glacial': return 7, 0
    if 'reef' in e or 'bioherm' in e: return 9, 1
    if e.startswith('lacustrine') or e in ('pond', 'crater lake', 'spring'): return 2, 0
    if e == 'mire/swamp': return 3, 0
    if e in ('eolian indet.', 'dune', 'interdune', 'loess'): return 4, 0
    if e in ('cave', 'fissure fill', 'sinkhole', 'karst indet.'): return 5, 0
    if any(k in e for k in ('fluvial', 'channel', 'floodplain', 'crevasse', 'levee', 'alluvial')) or e == 'delta plain': return 1, 0
    if any(k in e for k in ('estuary', 'bay', 'lagoonal', 'paralic', 'marginal', 'coastal', 'peritidal', 'foreshore', 'delta', 'sand shoal')):
        return (10 if 'subtidal' in e else 8), 1
    if any(k in e for k in ('offshore', 'deep', 'slope', 'basinal', 'submarine')): return 11, 1
    if any(k in e for k in ('subtidal', 'shoreface', 'transition', 'carbonate')): return 10, 1
    return 0, None
MARINE_UNITS = {'plesiosaurs','ichthyosaurs','mosasaurs','whales','sharks','armourfish','bonyfish','conodonts','trilobites',
  'eurypterids','ammonites','nautiloids','belemnites','corals','brachiopods','bivalves','snails','echinoderms'}
ENVS = {}
ALWAYS_LAND = {'diplodocus','brachiosaurus','stegosaurus','allosaurus','tyrannosaurus','velociraptor','triceratops','parasaurolophus',
  'sauropods','theropods','hadrosaurs','ornithopods','ceratopsians','armoured','dimetrodon','synapsids','insects','mammoth',
  'proboscideans','smilodon','carnivorans','hoofed','mammals','archaeopteryx','squamates'}
ALWAYS_SEA = {'plesiosaurs','ichthyosaurs','mosasaurs','whales','trilobites','ammonites','nautiloids','belemnites','corals',
  'brachiopods','echinoderms','conodonts'}
FORM = {}
for fn in ('pbdb_data_dino.csv', 'pbdb_data_reptilia.csv'):
    for r in csv.DictReader(open(f'{SRC}/dinotime/scripts/data/' + fn)):
        f = (r.get('formation') or '').strip()
        if f and f.lower() not in ('unknown', 'unnamed'): FORM['o' + r['occurrence_no']] = f
        if r.get('environment'): ENVS['o' + r['occurrence_no']] = r['environment']
print('formations', len(FORM), file=sys.stderr)
MARFLAG = {}
DINO_UNITS = {'diplodocoids','macronarians','sauropodomorphs','stegosaurs','ankylosaurs','ceratosaurs','carnosaurs','tyrannosaurs','raptors',
  'coelurosaurs','theropods','ceratopsians','pachys','hadrosaurs','ornithopods','otherdinos'}
NOT_DINOSAURS = {'Ancistrodon'}   # enigmatic teeth once thought to be dinosaurian
RECLASSED = collections.Counter()
def add(no, unit, genus, lng, lat, mx, mn, src):
    if unit in DINO_UNITS and genus in NOT_DINOSAURS: unit = None
    # anything on the dinosaur list that is wholly younger than the end-Cretaceous extinction is a bird
    if unit in DINO_UNITS and mx is not None and mx <= 66.0:
        RECLASSED[genus or '(no genus)'] += 1; unit = 'birds'
    if unit is None or lng is None or lat is None or mx is None or mn is None: return
    if mx > 4000 or mx < mn or abs(lat) > 85: return
    if no in occ: return
    ec, realm = env_class(ENVS.get(no, ''))
    if realm is None: realm = MARFLAG.get(no)
    if realm is None: realm = 1 if unit in MARINE_UNITS else 0
    if unit in ALWAYS_LAND: realm = 0
    elif unit in ALWAYS_SEA: realm = 1
    occ[no] = (unit, genus, lng, lat, mx, mn, FORM.get(no, ''), ec, realm)

HADRO_FAM={'Hadrosauridae','Lambeosaurinae','Saurolophinae','Hadrosauroidea','Hadrosaurinae'}
HADRO_GEN={'Telmatosaurus','Eolambia','Bactrosaurus','Gobihadros','Tanius','Probactrosaurus','Tethyshadros','Protohadros','Plesiohadros','Levnesovia','Claosaurus','Hadrosauridae','Lambeosaurinae','Hadrosauroidea'}
CERA_FAM={'Ceratopsidae','Protoceratopsidae','Psittacosauridae','Leptoceratopsidae','Chaoyangsauridae','Bagaceratopsidae','Pachycephalosauridae','Centrosaurinae','Chasmosaurinae'}
CERA_GEN={'Psittacosaurus','Asiaceratops','Turanoceratops','Stegoceras','Pachycephalosaurus','Prenocephale','Ceratopsia','Ceratopsidae','Pachycephalosauria','Neoceratopsia','Marginocephalia','Yinlong','Leptoceratops','Protoceratops','Zuniceratops'}
ARM_FAM={'Stegosauridae','Huayangosauridae','Ankylosauridae','Nodosauridae','Scelidosauridae','Polacanthidae'}
ARM_GEN={'Kentrosaurus','Deltapodus','Scutellosaurus','Scelidosaurus','Ankylosauria','Stegosauria','Thyreophora','Ankylosauridae','Nodosauridae','Stegosauridae','Dacentrurus','Hylaeosaurus','Polacanthus','Gastonia','Sauropelta','Edmontonia','Euoplocephalus','Ankylosaurus'}
CLADES = json.load(open('/home/claude/build/dino_clades.json'))
def clade_unit(chain):
    c = set(chain)
    if 'Avialae' in c: return 'birds'
    if 'Diplodocoidea' in c: return 'diplodocoids'
    if 'Macronaria' in c: return 'macronarians'
    if 'Sauropodomorpha' in c: return 'sauropodomorphs'
    if 'Stegosauria' in c: return 'stegosaurs'
    if 'Thyreophora' in c: return 'ankylosaurs'
    if 'Ceratosauria' in c: return 'ceratosaurs'
    if 'Allosauroidea' in c or 'Megalosauroidea' in c: return 'carnosaurs'
    if 'Tyrannosauroidea' in c: return 'tyrannosaurs'
    if 'Paraves' in c: return 'raptors'
    if 'Coelurosauria' in c: return 'coelurosaurs'
    if 'Theropoda' in c: return 'theropods'
    if 'Pachycephalosauria' in c: return 'pachys'
    if 'Marginocephalia' in c: return 'ceratopsians'
    if 'Hadrosauroidea' in c: return 'hadrosaurs'
    if 'Ornithischia' in c: return 'ornithopods'
    return 'otherdinos'
PETRA_FALLBACK = {'sauropod':'sauropodomorphs','theropod':'theropods','oviraptorosaur':'coelurosaurs','ornithomimosaur':'coelurosaurs',
  'ornithopod':'ornithopods','hadrosaur':'hadrosaurs','ceratopsian':'ceratopsians','pachycephalosaur':'pachys','stegosaur':'stegosaurs',
  'ankylosaur':'ankylosaurs','bird':'birds','trace':'otherdinos','unknown':'otherdinos'}
CLADE_ANC = {}
for _ch in CLADES.values():
    for _i, _c in enumerate(_ch): CLADE_ANC.setdefault(_c, _ch[_i:])
ALIAS = {'Prosauropoda': ['Sauropodomorpha'], 'Eusauropoda': ['Sauropoda', 'Sauropodomorpha'], 'Titanosauridae': ['Titanosauria', 'Macronaria'],
  'Rebbachisaurinae': ['Diplodocoidea'], 'Neosauropoda': ['Sauropoda', 'Sauropodomorpha'], 'Iguanodontipodidae': ['Ornithopoda', 'Ornithischia'],
  'Faveoloolithidae': ['Sauropoda', 'Sauropodomorpha'], 'Megaloolithidae': ['Sauropoda', 'Sauropodomorpha'], 'Spheroolithidae': ['Hadrosauroidea', 'Ornithischia'],
  'Elongatoolithidae': ['Oviraptorosauria', 'Coelurosauria', 'Theropoda'], 'Prismatoolithidae': ['Troodontidae', 'Paraves', 'Theropoda'],
  'Koreanaornis': ['Avialae'], 'Aquatilavipes': ['Avialae'], 'Ignotornis': ['Avialae'], 'Uhangrichnus': ['Avialae'], 'Jindongornipes': ['Avialae'],
  'Goseongornipes': ['Avialae'], 'Hwangsanipes': ['Avialae'], 'Gruipeda': ['Avialae'], 'Limiavipes': ['Avialae'], 'Shandongornipes': ['Avialae'],
  'Saurischia': ['Saurischia'], 'Ornithischia': ['Ornithischia'], 'Dinosauria': []}
def chain_of(name):
    if name in CLADES: return CLADES[name]
    if name in CLADE_ANC: return CLADE_ANC[name]
    if name in ALIAS: return ALIAS[name]
    return None
def dino_unit(grp, fam, genus, mx):
    ch = chain_of(genus)
    if ch is None and fam and fam not in ('NO_FAMILY_SPECIFIED', 'Unknown'): ch = chain_of(fam)
    if grp == 'bird' and ch is None: return 'birds'
    if ch is not None: u = clade_unit(ch)
    else: u = PETRA_FALLBACK.get(grp)
    # birds after the end-Cretaceous are not dinosaurs on this map's dinosaur list
    if u in ('theropods', 'coelurosaurs', 'raptors') and mx is not None and mx <= 66.5 and grp == 'bird': return 'birds'
    return u

# 1) classified dinosaur + bird export (petra)
g = json.load(open(f'{SRC}/petra/public/data/dinosaurs.geojson'))['features']
for f in g:
    p = f['properties']; lng, lat = f['geometry']['coordinates'][:2]
    genus = p.get('taxonomyGenus') or (p.get('name') or '').split(' ')[0]
    if genus in ('NO_GENUS_SPECIFIED', ''): genus = ''
    unit = dino_unit(p['group'], p.get('taxonomyFamily') or '', genus, fnum(p['max_ma']))
    add('o' + str(p['id']), unit, genus, lng, lat, fnum(p['max_ma']), fnum(p['min_ma']), 'dino')
print('after dinosaurs', len(occ), file=sys.stderr)

# 2) broad PBDB export with taxonomy (Heim lab)
gtax = {}
for r in csv.DictReader(gzip.open(f'{SRC}/pbs/PBDB_Occurrences/pbdb_occs.csv.gz', 'rt')):
    genus = r['genus_name'] or ''
    if r['class'] == 'Reptilia' and genus: gtax[genus] = (r['order'], r['family'])
    u = class_unit(r['phylum'], r['class'], r['order'], r['family'], genus)
    no = 'o' + r['occurrence_no']
    if r.get('environment') and no not in ENVS: ENVS[no] = r['environment']
    if r['marine'] in ('marine', 'likely_marine', 'assumed_marine'): MARFLAG[no] = 1
    elif r['marine'] in ('non_marine', 'likely_non_marine'): MARFLAG[no] = 0
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

print('reclassified as birds', dict(RECLASSED), file=sys.stderr)
cnt = collections.Counter(v[0] for v in occ.values())
for u in UNITS: print(f'{u[0]:16s}{cnt[u[0]]:8d}', file=sys.stderr)

# ---------------------------------------------------------------- plants, microbes, plankton
import gzip, struct, re
EXTRA = []   # (unit, lng2, lat2, mx10, mn10, genus, formation, env_string, n)
b = gzip.open('/mnt/user-data/uploads/Downloads/pbdb_plants_microbes.gz').read()
L = struct.unpack('<I', b[:4])[0]; meta = json.loads(b[4:4 + L].decode()); n = meta['n']; T = meta['T']
off = 4 + L; cols = {}
for name, dt in zip(meta['order'], [np.uint8, np.int16, np.int16, np.uint16, np.uint16, np.uint32, np.uint32, np.uint8, np.uint16]):
    a = np.frombuffer(b, dtype=dt, count=n, offset=off); cols[name] = a; off += a.nbytes
for i in range(n):
    EXTRA.append((T['u'][cols['u'][i]], int(cols['lng'][i]), int(cols['lat'][i]), int(cols['mx'][i]), int(cols['mn'][i]),
                  T['g'][cols['g'][i]], T['f'][cols['f'][i]], T['e'][cols['e'][i]], int(cols['n'][i])))
print('pbdb plant/microbe records', len(EXTRA), file=sys.stderr)
# microbial reefs from PaleoReefs (palaeoverse), ages resolved from interval names
import rdata
reefs = rdata.conversion.convert(rdata.parser.parse_file(f'{SRC}/palaeoverse/data/reefs.rda'))['reefs']
gts = rdata.conversion.convert(rdata.parser.parse_file(f'{SRC}/palaeoverse/data/GTS2020.rda'))['GTS2020']
ikey = rdata.conversion.convert(rdata.parser.parse_file(f'{SRC}/palaeoverse/data/interval_key.rda'))['interval_key']
G = {str(r.interval_name).lower(): (float(r.max_ma), float(r.min_ma)) for r in gts.itertuples()}
for r in ikey.itertuples():
    e, l = G.get(str(r.early_stage).lower()), G.get(str(r.late_stage).lower())
    if e and l: G.setdefault(str(r.interval_name).lower(), (e[0], l[1]))
G.update({'recent': (0.0117, 0), 'holocene': (0.0117, 0), 'botomian': (514, 509), 'atdabanian': (521, 514), 'tommotian': (529, 521),
          'toyonian': (511, 509), 'nemakit-daldynian': (538.8, 529), 'wenlock': (433.4, 427.4), 'llandovery': (443.8, 433.4), 'ludlow': (427.4, 423),
          'pridoli': (423, 419.2), 'upper miocene': (11.63, 5.333), 'middle miocene': (15.98, 11.63), 'lower miocene': (23.03, 15.98)})
def age_of(txt):
    t = str(txt or '').strip().lower()
    if not t: return None
    if '/' in t or '-' in t[1:]:
        sp = re.split(r'[/]|(?<=\w)-(?=\w)', t)
        if len(sp) == 1: return G.get(t)
        parts = [age_of(p) for p in sp]
        parts = [p for p in parts if p]
        return (max(p[0] for p in parts), min(p[1] for p in parts)) if parts else None
    if t in G: return G[t]
    m = re.match(r'(lower|early|middle|upper|late|lowermost|uppermost|basal|top)\s+(.+)', t)
    if m and m.group(2) in G:
        a0, a1 = G[m.group(2)]; d = (a0 - a1) / 3; q = m.group(1)
        return (a0, a0 - d) if q in ('lower', 'early', 'lowermost', 'basal') else (a1 + d, a1) if q in ('upper', 'late', 'uppermost', 'top') else (a0 - d, a1 + d)
    if t.capitalize() in ('Upper', 'Lower'): return None
    for k in (t.title(), t.capitalize()):
        if k.lower() in G: return G[k.lower()]
    return None
nreef = 0
for r in reefs.itertuples():
    if 'Microbes' not in (str(r.biota_main), str(r.biota_sec)): continue
    ag = age_of(r.interval) or age_of(r.series) or age_of(r.system)
    try: lng, lat = float(r.lng), float(r.lat)
    except: continue
    if not ag or ag[0] > 4000 or lng != lng: continue
    EXTRA.append(('stromatolites', round(lng * 2), round(lat * 2), round(ag[0] * 10), round(ag[1] * 10), '', str(r.formation or ''), 'reef, buildup or bioherm', 1))
    nreef += 1
print('microbial reefs', nreef, file=sys.stderr)
pre = json.loads(gzip.open('/mnt/user-data/uploads/Downloads/pbdb_precambrian.gz').read().decode())
for (u, lng, lat, mx, mn, ge, fo, env) in pre:
    if mx is None or lng is None: continue
    EXTRA.append((u, round(lng * 2), round(lat * 2), round(mx * 10), round(mn * 10), ge, fo, env, 1))
print('precambrian records', len(pre), file=sys.stderr)
PLANT_UNITS = {'earlyplants','lycopsids','horsetails','ferns','glossopteris','seedferns','cycads','ginkgos','conifers','angiosperms','mosses','fungi'}
EXTRA_SEA = {'ediacarans', 'forams','coccoliths','radiolarians','dinoflagellates','acritarchs','stromatolites'}
for e in EXTRA: cnt[e[0]] += e[8]

# ---------------------------------------------------------------- aggregate
genera = collections.Counter([v[1] for v in occ.values() if v[1]] + [e[5] for e in EXTRA if e[5]])
gnames = [''] + sorted(genera)
gid = {n: i for i, n in enumerate(gnames)}
agg = collections.Counter()
fnames = [''] + sorted({v[6] for v in occ.values() if v[6]} | {e[6] for e in EXTRA if e[6]})
fid = {n: i for i, n in enumerate(fnames)}
for (u, ge, lng, lat, mx, mn, fo, ec, rl) in occ.values():
    key = (UIDX[u], round(lng * 2) , round(lat * 2), round(mx * 10), round(mn * 10), gid.get(ge, 0), fid.get(fo, 0), ec, rl)
    agg[key] += 1
for (u, lng2, lat2, mx10, mn10, ge, fo, env, n) in EXTRA:
    ec, rl = env_class(env)
    if u in PLANT_UNITS: rl = 0
    elif u in EXTRA_SEA: rl = 1
    elif rl is None: rl = 1
    if mx10 < mn10: mx10, mn10 = mn10, mx10
    key = (UIDX[u], lng2, lat2, mx10, mn10, gid.get(ge, 0), fid.get(fo, 0), ec, rl)
    agg[key] += n
keys = sorted(agg)
A = np.array(keys, dtype=np.int64); N = np.array([agg[k] for k in keys], dtype=np.int64)
print('aggregated records', len(A), 'genera', len(gnames), 'formations', len(fnames), file=sys.stderr)

unit = A[:, 0].astype(np.uint8)
lngq = A[:, 1].astype(np.int16)   # lng*2
latq = A[:, 2].astype(np.int16)   # lat*2
mxq = A[:, 3].astype(np.uint16)   # Ma*10
mnq = A[:, 4].astype(np.uint16)
gq = A[:, 5].astype(np.uint16)
fq = A[:, 6].astype(np.uint16)
eq = A[:, 7].astype(np.uint8)
rq = A[:, 8].astype(np.uint8)
nq = np.minimum(N, 65535).astype(np.uint16)

# ---------------------------------------------------------------- time series & peaks
def winH(t): return 2.5 if t <= 541 else 10.0 if t <= 1000 else 25.0
BOUNDS = [66.0, 201.4, 251.9, 358.9, 443.8]
def win(t):
    h = winH(t); lo, hi = t - h, t + h
    for b in BOUNDS:
        if t < b < hi: hi = b
        if lo < b < t: lo = b
    return lo, hi
T = np.concatenate([np.arange(0, 542), np.arange(550, 4001, 10)])
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
        wlo, whi = win(t)
        ov = np.clip(np.minimum(m1, whi) - np.maximum(m0, wlo), 0, None)
        e = n * np.minimum(ov / s, 1.0)
        series[ui, ti] = e.sum()
        if e.any():
            peak5[ui] = max(peak5[ui], np.bincount(cinv, weights=e).max())

def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
out = {
  'units': [dict(id=u[0], label=u[1], section=u[2], icon=u[3], color=u[4], on=u[5], kind=u[6],
                 total=int(cnt[u[0]]), parent=PARENT.get(u[0], u[0]), peak=round(float(peak5[i]), 3),
                 series=[round(float(x), 2) for x in series[i]]) for i, u in enumerate(UNITS)],
  'genera': gnames, 'formations': fnames, 'trace_genera': sorted({(f['properties'].get('taxonomyGenus') or (f['properties'].get('name') or '').split(' ')[0]) for f in g if f['properties']['group'] == 'trace'} & set(gnames)), 'envs': ENV_CLASSES,
  'n': int(len(A)), 'H': 2.5, 'T': [int(x) for x in T],
  'cols': {k: b64(v) for k, v in dict(unit=unit, lng=lngq, lat=latq, mx=mxq, mn=mnq, g=gq, f=fq, e=eq, r=rq, n=nq).items()},
  'occurrences': int(len(occ)),
}
json.dump(out, open('/home/claude/build/v16/fossils.json', 'w'), separators=(',', ':'))
print('written', len(json.dumps(out)) // 1024, 'KB', file=sys.stderr)
