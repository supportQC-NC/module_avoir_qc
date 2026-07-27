"""
Script de generation de donnees de test
Module de Gestion des Avoirs Clients - STOYANN

Genere des avoirs dans TOUS les etats afin de tester le tableau de bord
(comptage par statut) et le comportement de l'application :
  - actifs valides
  - actifs proches de l'expiration (rappels)
  - actifs dont la validite est DEJA depassee (cas "silencieusement expire")
  - expires (statut 'expire')
  - bloques (statut 'bloque' + commentaire de blocage)
  - utilises totalement (montant restant = 0)
  - annules

IMPORTANT : ce script utilise les MEMES constantes de statut que
l'application (AVOIR_STATUS), pour eviter tout decalage du type
'expir' vs 'expire' ou 'utilis' vs 'utilise'.

Utilisation :
    python test_data.py                            # base par defaut (celle de l'app)
    python test_data.py "C:\\chemin\\avoirs.db"      # base specifique
    python test_data.py --reset                    # supprime d'abord les avoirs de test
"""

import os
import sys
import sqlite3
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

# Permet d'importer le package (config/, database/) quand le script est lance
# depuis la racine du projet.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────────────────────────────
# Constantes de statut : on reprend EXACTEMENT celles de l'application.
# ──────────────────────────────────────────────────────────────────────────
try:
    from config.settings import AVOIR_STATUS
except Exception:
    AVOIR_STATUS = {
        'ACTIF': 'actif',
        'UTILISE': 'utilise',
        'UTILISE_PARTIELLEMENT': 'utilise_partiellement',
        'EXPIRE': 'expire',
        'ANNULE': 'annule',
        'SUPPRIME': 'supprime',
        'BLOQUE': 'bloque',
    }

TEST_EMAIL = "support@quincaillerie.nc"
TEST_PREFIX_CLIENT = "TST"  # marqueur pour reperer/supprimer les donnees de test


def resolve_db_path(cli_path=None):
    """Determine le chemin de la base a utiliser."""
    if cli_path:
        return Path(cli_path)
    try:
        from database.connection import get_db_path
        return get_db_path()
    except Exception:
        base = Path("./module_avoir_data")
        base.mkdir(exist_ok=True)
        return base / "avoirs.db"


def get_existing_columns(cursor):
    """Retourne l'ensemble des colonnes reelles de la table avoirs."""
    rows = cursor.execute("PRAGMA table_info(avoirs)").fetchall()
    return {r[1] for r in rows}


def insert_avoir(cursor, avoir, existing_columns):
    """Insere un avoir en ne gardant que les colonnes reellement presentes."""
    data = {k: v for k, v in avoir.items() if k in existing_columns and k != 'description'}
    cols = list(data.keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO avoirs ({', '.join(cols)}) VALUES ({placeholders})"
    cursor.execute(sql, [data[c] for c in cols])


NOMS_CLIENTS = [
    "Boulangerie Crémière", "Menuiserie Dubois", "Café de la Plage",
    "Garage Léon", "Épicerie Tournésol", "Atelier Forêt-Noire",
    "Pêcherie du Récif", "Hôtel Bougainville", "Société Calédo-Bât",
    "Quincaillerie Étoilée",
]
TYPES_PRODUITS = [
    "Outillage", "Plomberie", "Électricité", "Peinture", "Jardinage",
    "Quincaillerie", "Bois", "Carrelage", "Sanitaire", "Décoration",
]


def f_dt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def f_d(dt):
    return dt.strftime('%Y-%m-%d')


def build_avoirs(start_num, year):
    """Construit la liste des avoirs de test couvrant tous les etats."""
    avoirs = []
    now = datetime.now()
    n = start_num

    def base_record(statut, jours_validite, montant, **extra):
        nonlocal n
        numero = f"{year}/{n:05d}"
        n += 1
        creation = now - timedelta(days=max(0, 90 - jours_validite))
        validite = now + timedelta(days=jours_validite)
        rec = {
            'numero_avoir': numero,
            'numero_client': f"{TEST_PREFIX_CLIENT}{random.randint(1000, 9999)}",
            'nom_client': random.choice(NOMS_CLIENTS),
            'email_client': TEST_EMAIL,
            'numero_facture': f"F{year}{random.randint(10000, 99999)}",
            'date_facture': f_d(creation - timedelta(days=3)),
            'type_avoir': 'retour',
            'montant': montant,
            'date_creation': f_dt(creation),
            'date_validite': f_dt(validite),
            'statut': statut,
            'utilisateur_creation': 'admin',
            'email_envoye': 1,
            'rappel_envoye': 0,
            'rappel_final_envoye': 0,
            'montant_utilise': 0,
            'montant_restant': montant,
            'est_avoir_enfant': 0,
        }
        rec.update(extra)
        return rec

    # A. Actifs valides
    for _ in range(5):
        avoirs.append(base_record(AVOIR_STATUS['ACTIF'], 60, random.randint(5, 200) * 1000,
                                  description="Actif valide"))

    # B. Actifs proches de l'expiration (rappels 7 / 10 / 14 jours)
    for j in (7, 10, 14):
        avoirs.append(base_record(AVOIR_STATUS['ACTIF'], j, random.randint(10, 150) * 1000,
                                  description=f"Actif - expire dans {j}j"))

    # C. Actifs dont la validite est DEJA depassee (statut encore 'actif').
    for _ in range(2):
        rec = base_record(AVOIR_STATUS['ACTIF'], 1, random.randint(5, 80) * 1000,
                          description="Actif mais validite depassee (forcage)")
        rec['date_validite'] = f_dt(now - timedelta(days=5))
        avoirs.append(rec)

    # D. Expires (statut 'expire')
    for _ in range(3):
        rec = base_record(AVOIR_STATUS['EXPIRE'], 1, random.randint(5, 50) * 1000,
                          description="Expire")
        rec['date_validite'] = f_dt(now - timedelta(days=30))
        rec['email_envoye'] = 0
        avoirs.append(rec)

    # E. Bloques (statut 'bloque' + infos de blocage)
    for _ in range(2):
        rec = base_record(AVOIR_STATUS['BLOQUE'], 30, random.randint(10, 120) * 1000,
                          description="Bloque")
        rec['commentaire_blocage'] = "Litige client - a regulariser a la comptabilite"
        rec['bloque_par'] = 'responsable1'
        rec['date_blocage'] = f_dt(now - timedelta(days=2))
        avoirs.append(rec)

    # F. Utilises totalement (montant restant = 0)
    for _ in range(4):
        montant = random.randint(5, 100) * 1000
        rec = base_record(AVOIR_STATUS['UTILISE'], 30, montant,
                          description="Utilise totalement")
        rec['montant_utilise'] = montant
        rec['montant_restant'] = 0
        rec['date_utilisation'] = f_dt(now - timedelta(days=10))
        rec['utilisateur_validation'] = random.choice(['vendeur1', 'caisse1'])
        rec['numero_facture_utilisation'] = f"FU{year}{random.randint(10000, 99999)}"
        avoirs.append(rec)

    # G. Annules (montant remis a 0) - avec QUI a annule et le MOTIF
    for _ in range(1):
        rec = base_record(AVOIR_STATUS['ANNULE'], 30, 0, description="Annule")
        rec['montant_restant'] = 0
        rec['commentaire_blocage'] = "Erreur de saisie - avoir annule apres verification"
        rec['bloque_par'] = 'responsable1'
        rec['date_blocage'] = f_dt(now - timedelta(days=3))
        avoirs.append(rec)

    # H. Client EN ANOMALIE : beaucoup d'avoirs RECENTS pour un meme client.
    #    3 avoirs normaux + 4 residus -> permet de tester le filtre Type :
    #    "Tous" = 7 (anomalie), "Hors residus" = 3, "Residus" = 4.
    client_anomalie = f"{TEST_PREFIX_CLIENT}9001"
    nom_anomalie = "Menuiserie Dubois"
    for k in range(7):
        rec = base_record(AVOIR_STATUS['ACTIF'], 80, random.randint(5, 60) * 1000,
                          description="Anomalie - client tres actif")
        creation = now - timedelta(days=k * 3)  # repartis sur ~18 jours (fenetre 30j)
        rec['numero_client'] = client_anomalie
        rec['nom_client'] = nom_anomalie
        rec['date_creation'] = f_dt(creation)
        rec['date_validite'] = f_dt(creation + timedelta(days=90))
        rec['est_avoir_enfant'] = 1 if k >= 3 else 0   # 4 residus, 3 normaux
        avoirs.append(rec)

    # I. Avoir SUPPRIME avec motif (pour tester le recap de suppression).
    rec = base_record(AVOIR_STATUS['SUPPRIME'], 30, random.randint(10, 80) * 1000,
                      description="Supprime avec motif")
    rec['commentaire_blocage'] = "Doublon cree par erreur - supprime apres verification"
    rec['bloque_par'] = 'compta1'
    rec['date_blocage'] = f_dt(now - timedelta(days=1))
    avoirs.append(rec)

    return avoirs, n


def create_linked_residus(cursor, existing_columns, year, start_num):
    """
    Cree un avoir PARENT + 2 RESIDUS enfants relies (avoir_parent_id), pour
    tester a la fois le filtre Residu/Hors residus et le rendu PDF d'un residu
    (qui affiche le numero et le montant du parent).

    Retourne (prochain_numero, nb_residus_crees).
    """
    now = datetime.now()
    client = f"{TEST_PREFIX_CLIENT}9002"
    nom = "Quincaillerie Étoilée"
    n = start_num

    parent_num = f"{year}/{n:05d}"
    n += 1
    parent_montant = 50000
    parent_creation = now - timedelta(days=15)
    parent = {
        'numero_avoir': parent_num,
        'numero_client': client,
        'nom_client': nom,
        'email_client': TEST_EMAIL,
        'numero_facture': f"F{year}{random.randint(10000, 99999)}",
        'date_facture': f_d(parent_creation - timedelta(days=3)),
        'type_avoir': 'retour',
        'montant': parent_montant,
        'date_creation': f_dt(parent_creation),
        'date_validite': f_dt(parent_creation + timedelta(days=90)),
        'statut': AVOIR_STATUS.get('UTILISE_PARTIELLEMENT', AVOIR_STATUS['ACTIF']),
        'utilisateur_creation': 'admin',
        'email_envoye': 1,
        'rappel_envoye': 0,
        'rappel_final_envoye': 0,
        'montant_utilise': 30000,
        'montant_restant': 20000,
        'est_avoir_enfant': 0,
    }
    if cursor.execute("SELECT 1 FROM avoirs WHERE numero_avoir = ?",
                      (parent_num,)).fetchone() is None:
        insert_avoir(cursor, parent, existing_columns)
    row = cursor.execute("SELECT id FROM avoirs WHERE numero_avoir = ?",
                         (parent_num,)).fetchone()
    parent_id = row[0] if row else None

    created = 0
    for i in range(2):
        child_num = f"{year}/{n:05d}"
        n += 1
        c_creation = now - timedelta(days=8 - i * 3)
        child_montant = 10000 + i * 5000
        child = {
            'numero_avoir': child_num,
            'numero_client': client,
            'nom_client': nom,
            'email_client': TEST_EMAIL,
            'numero_facture': parent['numero_facture'],
            'date_facture': parent['date_facture'],
            'type_avoir': 'retour',
            'montant': child_montant,
            'date_creation': f_dt(c_creation),
            'date_validite': f_dt(c_creation + timedelta(days=90)),
            'statut': AVOIR_STATUS['ACTIF'],
            'utilisateur_creation': 'admin',
            'email_envoye': 1,
            'rappel_envoye': 0,
            'rappel_final_envoye': 0,
            'montant_utilise': 0,
            'montant_restant': child_montant,
            'est_avoir_enfant': 1,
            'avoir_parent_id': parent_id,
        }
        if cursor.execute("SELECT 1 FROM avoirs WHERE numero_avoir = ?",
                          (child_num,)).fetchone() is None:
            insert_avoir(cursor, child, existing_columns)
            created += 1
    return n, created


def generate_test_data(db_path, reset=False):
    print("\n Generation des donnees de test...")
    print(f" Base de donnees : {db_path}")

    if not Path(db_path).exists():
        print(" ERREUR : la base n'existe pas encore.")
        print("   Lancez d'abord l'application (main.py) pour la creer,")
        print("   ou indiquez le bon chemin : python test_data.py <chemin>")
        return

    # timeout=30 : attend jusqu'a 30 s qu'un verrou se libere avant d'echouer
    # en "database is locked" (utile sur base partagee reseau).
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    cursor = conn.cursor()

    existing_columns = get_existing_columns(cursor)
    if not existing_columns:
        print(" ERREUR : table 'avoirs' introuvable dans cette base.")
        conn.close()
        return

    if reset:
        cursor.execute("DELETE FROM avoirs WHERE numero_client LIKE ?", (f"{TEST_PREFIX_CLIENT}%",))
        conn.commit()
        print("  Donnees de test precedentes supprimees.")

    # 1) Utilisateurs de test (avec un compte comptabilite)
    print("\n Creation des utilisateurs de test...")
    users = [
        ("vendeur1", "vendeur123", TEST_EMAIL, "vendeur"),
        ("responsable1", "resp123", TEST_EMAIL, "responsable"),
        ("compta1", "compta123", TEST_EMAIL, "comptabilite"),
        ("caisse1", "caisse123", TEST_EMAIL, "vendeur"),
    ]
    for username, password, email, role in users:
        try:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                (username, hashed, email, role)
            )
            print(f"   + {username:14} ({role}) - mdp: {password}")
        except sqlite3.IntegrityError:
            print(f"   = {username:14} existe deja")

    # 2) Avoirs de test
    print("\n Creation des avoirs de test...")
    year = datetime.now().strftime("%y")
    last = cursor.execute(
        "SELECT numero_avoir FROM avoirs WHERE numero_avoir LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{year}/%",)
    ).fetchone()
    start_num = (int(last[0].split('/')[1]) + 1) if last else 90000  # plage de test

    avoirs, next_num = build_avoirs(start_num, year)

    inserted = 0
    errors = 0
    for avoir in avoirs:
        try:
            existing = cursor.execute(
                "SELECT 1 FROM avoirs WHERE numero_avoir = ?", (avoir['numero_avoir'],)
            ).fetchone()
            if existing:
                continue
            insert_avoir(cursor, avoir, existing_columns)
            montant_fmt = f"{avoir['montant']:,}".replace(',', ' ')
            print(f"   {avoir['numero_avoir']} [{avoir['statut']:8}] {montant_fmt:>10} XPF - {avoir.get('description','')}")
            inserted += 1
        except Exception as e:
            print(f"   Erreur {avoir['numero_avoir']}: {e}")
            errors += 1

    conn.commit()

    # 2bis) Residus relies a un vrai parent (pour tester le filtre residu + PDF)
    try:
        next_num, residus_crees = create_linked_residus(
            cursor, existing_columns, year, next_num
        )
        conn.commit()
        if residus_crees:
            print(f"   + {residus_crees} residu(s) relie(s) a un parent "
                  f"(client {TEST_PREFIX_CLIENT}9002)")
            inserted += residus_crees
    except Exception as e:
        print(f"   (info) residus relies non crees : {e}")

    # 3) Resume base sur les VRAIES constantes
    print("\n" + "=" * 70)
    print(" RESUME (comptage par statut reel)")
    print("=" * 70)
    rows = cursor.execute("SELECT statut, COUNT(*) FROM avoirs GROUP BY statut").fetchall()
    counts = {r[0]: r[1] for r in rows}
    total = sum(v for k, v in counts.items() if k != AVOIR_STATUS['SUPPRIME'])
    print(f"  Total (hors supprimes) : {total}")
    for label, key in [
        ("Actifs", 'ACTIF'), ("Expires", 'EXPIRE'), ("Bloques", 'BLOQUE'),
        ("Utilises", 'UTILISE'), ("Annules", 'ANNULE'), ("Supprimes", 'SUPPRIME'),
    ]:
        print(f"     {label:10} ({AVOIR_STATUS[key]:8}) : {counts.get(AVOIR_STATUS[key], 0)}")

    print(f"\n  Inseres cette execution : {inserted}    Erreurs : {errors}")

    print("\n" + "=" * 70)
    print(" COMPTES DE CONNEXION DE TEST")
    print("-" * 70)
    print("  ADMIN        : admin / admin123")
    print("  RESPONSABLE  : responsable1 / resp123")
    print("  COMPTABILITE : compta1 / compta123")
    print("  VENDEUR      : vendeur1 / vendeur123")
    print("  CAISSE       : caisse1 / caisse123")

    print("\n" + "=" * 70)
    print(" QUOI TESTER")
    print("-" * 70)
    print(" 1. TABLEAU DE BORD : Total / Actifs / Expires / Bloques / Utilises / Annules")
    print(" 2. FORCAGE         : en caisse, scanner un avoir 'Actif mais validite depassee'")
    print("                      -> le bouton 'Forcer' doit apparaitre (nom du responsable requis)")
    print(" 3. BLOCAGE         : ouvrir un avoir bloque -> onglet Blocage -> Debloquer")
    print("                      puis tenter de l'utiliser en caisse (message comptabilite)")
    print(" 4. VENDEUR         : se connecter en vendeur -> seul 'Utiliser un avoir' est visible")
    print(" 5. PDF             : creer un avoir et verifier les accents")
    print(f" 6. ANOMALIES       : onglet Anomalies (super_user/compta), periode = 30 derniers")
    print(f"                      jours, seuil 5 -> le client {TEST_PREFIX_CLIENT}9001 ressort (7 avoirs).")
    print("                      Filtre Type : 'Hors residus' -> 3, 'Residus' -> 4.")
    print("                      Double-clic : le total doit correspondre au 'Nb avoirs'.")
    print(f" 7. RESIDUS / PDF   : client {TEST_PREFIX_CLIENT}9002 -> 1 parent + 2 residus relies.")
    print("                      Generer le PDF d'un residu : n parent + montant parent affiches.")
    print("                      Verifier que tout rentre dans le cadre 'DETAILS'.")
    print(" 8. SUPPRESSION      : avoir au statut 'supprime' avec motif -> ouvrir ses details,")
    print("                      la section SUPPRESSION (qui / date / motif) doit s'afficher.")

    print("\n Generation terminee.\n")
    conn.close()


if __name__ == "__main__":
    args = list(sys.argv[1:])
    reset = '--reset' in args
    args = [a for a in args if a != '--reset']
    cli_path = args[0] if args else None

    db_path = resolve_db_path(cli_path)
    try:
        generate_test_data(db_path, reset=reset)
    except Exception as e:
        print(f"\n Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()