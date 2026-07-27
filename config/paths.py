# -*- coding: utf-8 -*-
"""
=============================================================================
                    GESTION DES CHEMINS - PATHS
=============================================================================
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne
Entreprise: STOYANN

Ce fichier gère:
- Les chemins de fichiers et dossiers
- La configuration persistante (sauvegardée en JSON sur le réseau)
- L'initialisation des répertoires de travail

CONFIG.JSON est stocké sur le serveur réseau partagé, PAS en local.
Tous les postes partagent le même fichier de configuration.
=============================================================================
"""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CHEMINS RÉSEAU
# =============================================================================

# Dossier réseau fixe — toujours accessible sur le LAN
NETWORK_BASE = Path(r"\\192.168.0.250\Bases")

# Fichier de configuration partagé entre tous les postes
CONFIG_FILE = NETWORK_BASE / "module_avoir_config.json"

# =============================================================================
# OVERRIDE LOCAL — MODE DEV / BASE DE TEST (PROPRE À CHAQUE POSTE)
# =============================================================================
# Ce fichier est stocké LOCALEMENT sur le poste (profil de l'utilisateur
# Windows), JAMAIS sur le réseau. S'il active le mode test, SEUL ce poste
# utilise la base de test : tous les autres postes continuent normalement sur
# la base de PRODUCTION (ils n'ont pas ce fichier).
LOCAL_CONFIG_FILE = Path.home() / ".module_avoir_local.json"

# Dossier de test partagé par défaut (sur le serveur)
DEFAULT_TEST_BASE = NETWORK_BASE / "db_module_avoir_qc_TEST"


def load_local_config():
    """Charge la config LOCALE (propre au poste). {} si absente/illisible."""
    try:
        if LOCAL_CONFIG_FILE.exists():
            with open(LOCAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Config locale illisible (%s) : %s", LOCAL_CONFIG_FILE, e)
    return {}


def save_local_config(config):
    """Sauvegarde la config LOCALE (propre au poste)."""
    try:
        with open(LOCAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("Impossible de sauvegarder la config locale : %s", e)
        return False


def is_dev_test_mode():
    """True si CE poste est en mode test/dev (override local actif)."""
    cfg = load_local_config()
    return bool(cfg.get('dev_test')) and bool(cfg.get('dev_test_base'))


def get_dev_test_base():
    """Retourne le dossier de base de test local, ou None si inactif."""
    cfg = load_local_config()
    if cfg.get('dev_test') and cfg.get('dev_test_base'):
        return Path(cfg['dev_test_base'])
    return None


def set_dev_test_mode(enabled, test_path=None):
    """
    Active/désactive le mode test LOCAL (uniquement ce poste).

    Args:
        enabled (bool): True pour basculer CE poste sur la base de test.
        test_path (str|Path, optionnel): dossier de test ; par défaut la base
            de test partagée du serveur (DEFAULT_TEST_BASE).

    Returns:
        bool: True si l'écriture a réussi.
    """
    cfg = load_local_config()
    if enabled:
        base = Path(test_path) if test_path else DEFAULT_TEST_BASE
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        cfg['dev_test'] = True
        cfg['dev_test_base'] = str(base)
    else:
        cfg['dev_test'] = False
        cfg.pop('dev_test_base', None)
    return save_local_config(cfg)

# =============================================================================
# VARIABLES GLOBALES - Initialisées par init_paths()
# =============================================================================
BASE_PATH = None
DB_PATH   = None
LOG_PATH  = None


# =============================================================================
# FONCTIONS DE CONFIGURATION PERSISTANTE
# =============================================================================

def load_persistent_config():
    """
    Charge la configuration persistante depuis le fichier JSON réseau.

    Returns:
        dict: La configuration chargée, ou {} si le fichier n'existe pas encore
              ou en cas d'erreur de lecture.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Impossible de lire %s : %s", CONFIG_FILE, e)
    return {}


def save_persistent_config(config):
    """
    Sauvegarde la configuration persistante dans le fichier JSON réseau.

    Args:
        config (dict): La configuration à sauvegarder

    Returns:
        bool: True si succès, False sinon
    """
    try:
        # S'assurer que le dossier réseau existe
        NETWORK_BASE.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.debug("Config sauvegardée dans %s", CONFIG_FILE)
        return True
    except Exception as e:
        logger.error("Impossible de sauvegarder la config : %s", e)
        return False


# =============================================================================
# GESTION DU CHEMIN DE BASE
# =============================================================================

def get_base_path():
    """
    Récupère le chemin de base pour les données applicatives.
    NE CRÉE PAS de dossier — retourne simplement le chemin configuré.

    Returns:
        Path: Le chemin configuré, ou le chemin réseau par défaut.
    """
    # 0) Override LOCAL (mode dev/test) — prioritaire et propre à CE poste.
    #    Permet de développer sur la base de test sans impacter la production
    #    des autres postes (qui n'ont pas ce fichier local).
    local_base = get_dev_test_base()
    if local_base is not None:
        return local_base
    # 1) Config partagée (réseau)
    config = load_persistent_config()
    if 'base_path' in config:
        return Path(config['base_path'])
    # 2) Valeur par défaut : sous-dossier dédié sur le partage réseau (PRODUCTION)
    return NETWORK_BASE / "db_module_avoir_qc"


def set_base_path(new_path):
    """
    Définit le chemin de base pour les données applicatives.

    Args:
        new_path (str | Path): Nouveau chemin de base
    """
    config = load_persistent_config()
    config['base_path'] = str(new_path)
    save_persistent_config(config)
    logger.info("Chemin de base défini : %s", new_path)


# =============================================================================
# GESTION DE LA PREMIÈRE EXÉCUTION
# =============================================================================

def is_first_run():
    """
    Détermine si c'est le premier lancement de l'application.

    Le premier lancement est détecté par l'ABSENCE du fichier
    config.json sur le réseau partagé.

    Returns:
        bool: True si premier lancement, False sinon.

    Raises:
        RuntimeError: Si le dossier réseau est inaccessible.
    """
    # Vérifier l'accessibilité du partage réseau
    try:
        accessible = NETWORK_BASE.exists()
    except PermissionError:
        raise RuntimeError(
            f"Accès refusé au partage réseau : {NETWORK_BASE}\n"
            "Vérifiez vos droits sur le partage."
        )
    except Exception as e:
        raise RuntimeError(
            f"Dossier réseau inaccessible : {NETWORK_BASE}\n"
            f"Vérifiez la connexion au serveur 192.168.0.250\n"
            f"Détail : {e}"
        )

    if not accessible:
        raise RuntimeError(
            f"Dossier réseau introuvable : {NETWORK_BASE}\n"
            "Vérifiez que le serveur 192.168.0.250 est allumé et accessible."
        )

    first = not CONFIG_FILE.exists()
    if first:
        logger.info("Premier lancement détecté — config.json absent de %s", NETWORK_BASE)
    else:
        logger.info("Config trouvée : %s", CONFIG_FILE)
    return first


def mark_as_initialized():
    """
    Marque l'application comme initialisée (première config terminée).
    Écrit le flag dans le config.json réseau.
    """
    config = load_persistent_config()
    config['initialized'] = True
    save_persistent_config(config)
    logger.info("Application marquée comme initialisée.")


# =============================================================================
# GESTION DE LA CONFIGURATION ADMIN
# =============================================================================

def get_admin_config():
    """
    Récupère la configuration admin sauvegardée.

    Returns:
        dict: {email, password_hash} ou {} si absent
    """
    config = load_persistent_config()
    return config.get('admin', {})


def save_admin_config(email, password_hash):
    """
    Sauvegarde la configuration du super-utilisateur.

    Args:
        email (str): Email de l'administrateur
        password_hash (str): Hash SHA-256 du mot de passe
    """
    config = load_persistent_config()
    config['admin'] = {
        'email': email,
        'password_hash': password_hash
    }
    save_persistent_config(config)
    logger.info("Config admin sauvegardée pour : %s", email)


# =============================================================================
# RÉCUPÉRATION DES CHEMINS
# =============================================================================

def get_paths():
    """
    Retourne tous les chemins applicatifs sous forme de dictionnaire.
    NE CRÉE PAS les dossiers — retourne uniquement les chemins.

    Returns:
        dict: Clés BASE_PATH, DB_PATH, LOG_PATH, EXPORT_PATH, PDF_PATH
    """
    base = get_base_path()
    return {
        'BASE_PATH':   base,
        'DB_PATH':     base / "avoirs.db",
        'LOG_PATH':    base / "logs",
        'EXPORT_PATH': base / "exports",
        'PDF_PATH':    base / "pdf",
    }


def get_current_db_path():
    """
    Retourne le chemin complet du fichier avoirs.db.

    Returns:
        Path: Chemin vers avoirs.db
    """
    return get_paths()['DB_PATH']


# =============================================================================
# INITIALISATION DES CHEMINS ET DOSSIERS
# =============================================================================

def init_paths():
    """
    Initialise les chemins et crée les dossiers nécessaires.

    Doit être appelée APRÈS la configuration initiale (show_initial_config_dialog).
    Met à jour les variables globales et crée les dossiers manquants.

    Returns:
        dict: Les chemins initialisés
    """
    global BASE_PATH, DB_PATH, LOG_PATH

    # Import local pour éviter les imports circulaires
    from config.settings import EXPORT_CONFIG, PDF_CONFIG

    paths = get_paths()
    BASE_PATH = paths['BASE_PATH']
    DB_PATH   = paths['DB_PATH']
    LOG_PATH  = paths['LOG_PATH']

    # Créer les dossiers (le dossier réseau est déjà accessible à ce stade)
    BASE_PATH.mkdir(exist_ok=True, parents=True)
    LOG_PATH.mkdir(exist_ok=True)
    paths['EXPORT_PATH'].mkdir(exist_ok=True)
    paths['PDF_PATH'].mkdir(exist_ok=True)

    # Mettre à jour les configs dépendantes des chemins
    EXPORT_CONFIG['EXPORT_PATH'] = paths['EXPORT_PATH']
    PDF_CONFIG['LOGO_PATH']      = BASE_PATH / 'assets' / 'logo.png'
    PDF_CONFIG['OUTPUT_PATH']    = paths['PDF_PATH']

    logger.info("=== CHEMINS INITIALISÉS ===")
    logger.info("Base       : %s", BASE_PATH.resolve())
    logger.info("Base de données : %s", DB_PATH.resolve())
    logger.info("Logs       : %s", LOG_PATH.resolve())

    return paths


# =============================================================================
# FONCTION UTILITAIRE
# =============================================================================

def get_file_path(filename, folder=''):
    """
    Retourne le chemin complet d'un fichier dans le répertoire de base.

    Args:
        filename (str): Nom du fichier
        folder (str, optional): Sous-dossier éventuel

    Returns:
        Path: Chemin complet du fichier
    """
    if BASE_PATH is None:
        raise RuntimeError(
            "BASE_PATH non initialisé — appelez init_paths() avant get_file_path()."
        )
    if folder:
        return BASE_PATH / folder / filename
    return BASE_PATH / filename