"""
Utilitaire de configuration de la base de donnees
Module de Gestion des Avoirs Clients - STOYANN

Permet de VOIR et de CHANGER le dossier de base utilise par l'application,
sans editer le fichier de configuration a la main.

Le chemin est stocke dans le fichier de configuration PARTAGE sur le serveur
(\\192.168.0.250\\Bases\\module_avoir_config.json). Tous les postes lisent ce
fichier : changer le chemin ici le change pour TOUS les postes.

Utilisation (depuis la racine du projet) :
    python config_bdd.py --show
        Affiche la configuration actuelle (dossier + fichier avoirs.db + existence).

    python config_bdd.py --prod
        Bascule sur la base de PRODUCTION du serveur :
        \\192.168.0.250\\Bases\\db_module_avoir_qc

    python config_bdd.py --test
        Bascule sur la base de TEST PARTAGEE du serveur :
        \\192.168.0.250\\Bases\\db_module_avoir_qc_TEST
        (tous les postes pourront tester sur cette meme base)

    python config_bdd.py --test "C:\\AvoirsTest"
        Bascule sur un dossier de TEST specifique (ex. local). Cree si besoin.

    python config_bdd.py --defaut
        Supprime le chemin personnalise : l'app reprend le dossier par defaut
        du serveur (\\192.168.0.250\\Bases\\db_module_avoir_qc).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import (
        NETWORK_BASE, CONFIG_FILE,
        get_base_path, load_persistent_config, save_persistent_config,
        is_dev_test_mode, get_dev_test_base, set_dev_test_mode,
        DEFAULT_TEST_BASE, LOCAL_CONFIG_FILE,
    )
except Exception as e:
    print("ERREUR : impossible d'importer config.paths.")
    print("Lancez ce script depuis la RACINE du projet (la ou se trouve main.py).")
    print(f"Detail : {e}")
    sys.exit(1)

PROD_DIR = NETWORK_BASE / "db_module_avoir_qc"
TEST_DIR = NETWORK_BASE / "db_module_avoir_qc_TEST"   # base de test partagee sur le serveur


def db_file_for(base):
    return Path(base) / "avoirs.db"


def show():
    base = get_base_path()
    dbf = db_file_for(base)
    cfg = load_persistent_config()
    print("=" * 64)
    print(" CONFIGURATION ACTUELLE DE LA BASE")
    print("=" * 64)
    print(f"  Fichier de config partage : {CONFIG_FILE}")
    print(f"  base_path configure        : {cfg.get('base_path', '(non defini -> defaut serveur)')}")
    print(f"  Dossier de base utilise    : {base}")
    print(f"  Fichier base de donnees    : {dbf}")
    try:
        existe = dbf.exists()
    except Exception:
        existe = False
    print(f"  La base existe ?           : {'OUI' if existe else 'NON'}")
    print(f"  Dossier PROD par defaut    : {PROD_DIR}")
    print(f"  Dossier TEST (serveur)     : {TEST_DIR}")
    print("-" * 64)
    # Etat du MODE DEV/TEST LOCAL (propre a CE poste uniquement)
    if is_dev_test_mode():
        print("  MODE DEV/TEST LOCAL        : ACTIF (ce poste uniquement)")
        print(f"  -> Base de test locale     : {get_dev_test_base()}")
        print(f"  Fichier local              : {LOCAL_CONFIG_FILE}")
    else:
        print("  MODE DEV/TEST LOCAL        : inactif (ce poste suit la config partagee)")
    print("=" * 64)


def set_path(new_path, label):
    new_path = Path(new_path)
    # Tente de creer le dossier cible (utile pour un dossier de test local)
    try:
        new_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"  (info) Impossible de creer {new_path} maintenant : {e}")

    config = load_persistent_config()
    config['base_path'] = str(new_path)
    if save_persistent_config(config):
        print(f"  OK -> l'application utilisera la base {label} :")
        print(f"       {db_file_for(new_path)}")
        print("  (Tous les postes liront ce nouveau chemin.)")
    else:
        print("  ECHEC de l'ecriture du fichier de configuration.")
        print(f"  Verifiez l'acces a : {CONFIG_FILE}")


def reset_default():
    config = load_persistent_config()
    if 'base_path' in config:
        del config['base_path']
        if save_persistent_config(config):
            print(f"  OK -> chemin personnalise supprime. Dossier par defaut : {PROD_DIR}")
        else:
            print("  ECHEC de l'ecriture du fichier de configuration.")
    else:
        print("  Aucun chemin personnalise n'etait defini. Rien a faire.")


def main():
    args = sys.argv[1:]
    if not args or '--show' in args:
        show()
        if not args:
            print("\n  Astuce : --prod | --test <dossier> | --defaut (config PARTAGEE)")
            print("           --dev-test [dossier] | --dev-off (mode dev LOCAL, ce poste seulement)")
        return

    if '--prod' in args:
        set_path(PROD_DIR, "de PRODUCTION")
        print()
        show()
        return

    if '--defaut' in args:
        reset_default()
        print()
        show()
        return

    if '--test' in args:
        i = args.index('--test')
        if i + 1 < len(args):
            set_path(args[i + 1], "de TEST")
        else:
            # Sans chemin precis : base de test PARTAGEE sur le serveur
            set_path(TEST_DIR, "de TEST (serveur)")
        print()
        show()
        return

    if '--dev-test' in args:
        i = args.index('--dev-test')
        if i + 1 < len(args) and not args[i + 1].startswith('--'):
            ok = set_dev_test_mode(True, args[i + 1])
            cible = args[i + 1]
        else:
            ok = set_dev_test_mode(True)
            cible = str(DEFAULT_TEST_BASE)
        if ok:
            print("  OK -> MODE DEV/TEST LOCAL ACTIVE sur CE poste uniquement.")
            print(f"       Base de test : {cible}")
            print("       Les AUTRES postes continuent en PRODUCTION normalement.")
            print("       Pour revenir en prod sur ce poste : python config_bdd.py --dev-off")
        else:
            print("  ECHEC : impossible d'ecrire le fichier de config local.")
            print(f"  Fichier : {LOCAL_CONFIG_FILE}")
        print()
        show()
        return

    if '--dev-off' in args:
        if set_dev_test_mode(False):
            print("  OK -> MODE DEV/TEST LOCAL DESACTIVE. Ce poste repasse en PRODUCTION")
            print("       (selon la config partagee).")
        else:
            print("  ECHEC : impossible d'ecrire le fichier de config local.")
        print()
        show()
        return

    print("Option inconnue. Options : --show | --prod | --test <dossier> | --defaut "
          "| --dev-test [dossier] | --dev-off")


if __name__ == "__main__":
    main()