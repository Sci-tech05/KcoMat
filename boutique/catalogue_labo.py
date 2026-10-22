"""
Catégorie « Équipements de laboratoire » du catalogue de la boutique.

Liste établie d'après la catégorie Équipements de laboratoire de components.youpilab.com (octobre 2026) :
`prix_source` est le prix affiché là-bas ; le prix de vente KcoMat est majoré de 30 %
(voir `catalogue.prix_majore`). Textes rédigés pour KcoMat à partir des caractéristiques techniques.
"""


def _veroboard(couleur, motif, faces, prix, slug, nom=None):
    pastilles = "pastilles individuelles (pointillé)" if motif == 'pointillé' else "bandes de cuivre continues (lignes)"
    return {
        'nom': nom or f"Veroboard {couleur} {motif} 9 × 15 cm",
        'prix_source': prix, 'ref': f"9 × 15 cm, {faces}", 'slug': slug,
        'courte': f"Plaque à trous {couleur} 9 × 15 cm à {pastilles}, pour souder vos montages définitifs.",
        'texte': "Une fois le circuit validé sur protoboard, on le soude sur le veroboard pour obtenir un montage solide, "
                 "sans fabriquer de circuit imprimé.",
        'specs': ["Dimensions : 9 × 15 cm", f"Cuivre {faces}", f"Perforation : {motif}", "Pas de 2,54 mm"],
    }


def _protoboard(points, prix, slug, nom=None, alias=None, specs=None):
    fiche = {
        'nom': nom or f"Protoboard {points} points",
        'prix_source': prix, 'ref': f"{points} points", 'slug': slug,
        'courte': f"Plaque d'essai sans soudure de {points} points pour tester vos circuits avant de les souder.",
        'texte': "Les composants et les fils s'enfichent sans soudure : on monte, on teste et on modifie le circuit autant "
                 "de fois que nécessaire.",
        'specs': specs or [f"{points} points de connexion", "Sans soudure, réutilisable", "Rails d'alimentation",
                           "Fils de 20 à 29 AWG", "Dos adhésif"],
    }
    if alias:
        fiche['alias'] = alias
    return fiche


LABO = [
    # ── Plaques d'essai ──
    _protoboard(830, 995, 'protoboard-830-points', alias=['protoboard']),
    _protoboard(830, 1900, 'protoboard-transparente-830-points', nom='Protoboard transparente 830 points',
                specs=["830 points de connexion", "Plastique transparent : connexions internes visibles", "Rails d'alimentation",
                       "Fils de 20 à 29 AWG", "Dimensions : 165 × 55 mm"]),
    _protoboard(400, 595, 'protoboard-400-points',
                specs=["400 points (300 + 4 rails de 25)", "Sans soudure, réutilisable", "Clips d'assemblage avec d'autres plaques",
                       "Dimensions : 84 × 55 mm"]),
    {'nom': 'Protoboard ZY-208 MB-102 3220 points', 'prix_source': 13000, 'ref': 'ZY-208 / MB-102', 'slug': 'protoboard-zy-208-3220-points',
     'courte': "Grande plaque d'essai de 3220 points sur socle aluminium avec bornes d'alimentation, pour les gros montages.",
     'texte': "La surface idéale pour l'enseignement et les projets complexes : plusieurs cartes et modules se câblent côte à côte.",
     'specs': ["3220 points de connexion", "4 bandes de 630 points + 7 bandes de 100 points", "Socle aluminium",
               "Bornes d'alimentation à vis"]},
    _veroboard('vert', 'pointillé', 'double face', 1000, 'veroboard-vert-pointille-double-face',
               nom='Veroboard vert pointillé 9 × 15 cm double face'),
    _veroboard('vert', 'pointillé', 'simple face', 780, 'veroboard-vert-pointille'),
    _veroboard('marron', 'pointillé', 'simple face', 360, 'veroboard-marron-pointille'),
    _veroboard('marron', 'lignes', 'simple face', 395, 'veroboard-marron-lignes', nom='Veroboard marron à lignes 9 × 15 cm'),
    {'nom': 'Plaque cuivrée 15 × 20 cm', 'prix_source': 1850, 'ref': '15 × 20 cm', 'slug': 'plaque-cuivree-15x20',
     'courte': "Plaque époxy recouverte de cuivre pour graver vos propres circuits imprimés.",
     'texte': "Dessinez ou transférez votre circuit, gravez au perchlorure de fer, percez : vous obtenez un vrai circuit imprimé.",
     'specs': ["Dimensions : 15 × 20 cm", "Support recouvert de cuivre", "Pour gravure chimique ou fraisage"]},
    {'nom': 'Plaque cuivrée 20 × 30 cm', 'prix_source': 3800, 'ref': '20 × 30 cm', 'slug': 'plaque-cuivree-20x30',
     'courte': "Grande plaque cuivrée pour graver plusieurs circuits imprimés ou un grand montage.",
     'texte': "À découper selon vos besoins, pour la gravure chimique ou le fraisage de circuits imprimés.",
     'specs': ["Dimensions : 20 × 30 cm", "Support recouvert de cuivre", "Pour gravure chimique ou fraisage"]},

    # ── Soudure ──
    {'nom': "Rouleau d'étain 1 mm", 'prix_source': 2500, 'ref': 'Ø 1 mm', 'slug': 'rouleau-etain-1mm',
     'courte': "Rouleau de fil d'étain de 1 mm avec flux intégré pour des soudures solides et brillantes.",
     'texte': "Le flux intégré facilite l'accroche de la soudure et évite les faux contacts.",
     'specs': ["Diamètre : 1 mm", "Flux intégré", "Pour soudure électronique au fer"]},
    {'nom': 'Tresse à dessouder 1,5 mm', 'prix_source': 560, 'ref': '1,5 mm × 1,5 m', 'slug': 'tresse-a-dessouder',
     'courte': "Tresse de cuivre qui absorbe l'étain en trop : corrige un pont de soudure ou retire un composant.",
     'texte': "Posez la tresse sur la soudure et chauffez avec le fer : l'étain fondu est aspiré dans le cuivre.",
     'specs': ["Largeur : 1,5 mm", "Longueur : 1,5 m", "Cuivre pur"]},
    {'nom': 'Support métallique pour fer à souder', 'prix_source': 2500, 'ref': '', 'slug': 'support-fer-a-souder',
     'courte': "Support stable pour poser le fer à souder chaud en toute sécurité, avec éponge de nettoyage.",
     'texte': "Évite les brûlures et protège le plan de travail ; l'éponge humide nettoie la panne du fer.",
     'specs': ["Support métallique à spirale", "Socle stable", "Emplacement pour éponge"]},

    # ── Rangement et fixation ──
    {'nom': 'Boîte de rangement transparente à compartiments', 'prix_source': 2900, 'ref': '', 'slug': 'boite-rangement-compartiments',
     'courte': "Boîte en plastique transparent à compartiments pour ranger et retrouver vite vos composants.",
     'texte': "Résistances, LED, vis, petits modules : chaque référence dans sa case, visible sans ouvrir la boîte.",
     'specs': ["Plastique transparent", "Plusieurs compartiments", "Couvercle à fermeture"]},
    {'nom': 'Ruban adhésif double face nano', 'prix_source': 3000, 'ref': '3 m × 6 cm', 'slug': 'ruban-adhesif-double-face-nano',
     'courte': "Ruban gel double face transparent ultra-adhésif, lavable et réutilisable, sans trace.",
     'texte': "Fixez un module, une batterie ou un boîtier sans vis ni perçage ; se retire sans abîmer les surfaces.",
     'specs': ["Longueur : 3 m", "Largeur : 6 cm, épaisseur 2 mm", "Acrylique transparent", "Tient jusqu'à environ 1 kg sur surface lisse"]},
]
