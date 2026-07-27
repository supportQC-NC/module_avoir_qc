

# # -*- coding: utf-8 -*-
# """
# Point d'entrée principal
# Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

# Ce fichier gère:
# - La vérification de l'accessibilité du réseau
# - La configuration initiale au premier lancement (super-user + chemin BDD)
# - Le splash screen de chargement
# - L'authentification
# - Le lancement de l'application principale
# """

# import tkinter as tk
# from tkinter import messagebox
# import sys
# import os
# from pathlib import Path
# import threading
# import time
# from datetime import datetime
# from shutil import copy2
# import configparser

# # Ajouter le répertoire courant au path Python
# sys.path.insert(0, str(Path(__file__).parent))

# # ══════════════════════════════════════════════════════════════════════════════
# # CONFIGURATION INITIALE
# # ══════════════════════════════════════════════════════════════════════════════

# from config.paths import (
#     is_first_run, init_paths, get_paths,
#     get_current_db_path, get_base_path
# )


# def do_initial_config():
#     """
#     Effectue la configuration initiale si nécessaire.

#     - Si c'est le premier lancement (pas de config.json réseau) :
#       affiche le dialogue de configuration (chemin BDD + super-user).
#     - Sinon : logue simplement le chemin de la BDD active.

#     Returns:
#         dict | None: Résultat de la configuration initiale, ou None si
#                      déjà configuré.

#     Raises:
#         SystemExit: Si le réseau est inaccessible ou si l'utilisateur
#                     annule la configuration initiale.
#     """
#     try:
#         first = is_first_run()
#     except RuntimeError as e:
#         # Réseau inaccessible — on ne peut pas continuer
#         root = tk.Tk()
#         root.withdraw()
#         messagebox.showerror(
#             "Erreur réseau",
#             f"{e}\n\nL'application ne peut pas démarrer sans accès au serveur."
#         )
#         root.destroy()
#         sys.exit(1)

#     if first:
#         print("\n*** PREMIER LANCEMENT - CONFIGURATION INITIALE ***\n")
#         from database.initial_setup import show_initial_config_dialog
#         result = show_initial_config_dialog()

#         if not result.get('configured'):
#             print("Configuration annulée. Fermeture de l'application.")
#             sys.exit(0)

#         print(f"\n✓ Configuration initiale terminée.")
#         print(f"   Base de données  : {result['db_path']}")
#         print(f"   Super-utilisateur : {result['email']}\n")
#         return result

#     else:
#         # Lancement normal — on trace la BDD utilisée
#         db_path = get_current_db_path()
#         print(f"\n→ Base de données active : {db_path.resolve()}")
#         return None


# # Faire la configuration initiale AVANT tout autre import dépendant des chemins
# initial_config_result = do_initial_config()

# # Initialiser les chemins (crée les dossiers si nécessaire)
# init_paths()

# # Récupérer les chemins après initialisation
# _paths    = get_paths()
# BASE_PATH = _paths['BASE_PATH']
# DB_PATH   = _paths['DB_PATH']
# LOG_PATH  = _paths['LOG_PATH']

# # Imports des modules applicatifs (après init_paths)
# from gui.login_window import LoginWindow
# from gui.splash_screen import SplashScreen
# from models.avoir_manager import AvoirManager
# from database.connection import Database

# # Si premier lancement : mettre à jour les credentials admin en base
# if initial_config_result and initial_config_result.get('configured'):
#     db = Database()
#     if initial_config_result.get('email') and initial_config_result.get('password_hash'):
#         db.update_admin_credentials(
#             initial_config_result['email'],
#             initial_config_result['password_hash']
#         )
#         print(f"✓ Compte super-utilisateur configuré : {initial_config_result['email']}")
#     db.close()


# # ══════════════════════════════════════════════════════════════════════════════
# # GESTIONNAIRE D'APPLICATION
# # ══════════════════════════════════════════════════════════════════════════════

# class ApplicationManager:
#     """
#     Gestionnaire principal de l'application.

#     Gère le cycle de vie complet :
#     - Splash screen de chargement
#     - Authentification
#     - Fenêtre principale
#     """

#     def __init__(self):
#         self.splash               = None
#         self.login_window         = None
#         self.main_window          = None
#         self.current_user         = None
#         self.initialization_success = False

#     def start(self):
#         """Démarre l'application avec splash screen."""
#         splash_root = tk.Tk()
#         self.splash = SplashScreen(splash_root)

#         loading_thread = threading.Thread(
#             target=self.load_application, args=(splash_root,), daemon=True
#         )
#         loading_thread.start()

#         splash_root.mainloop()

#         if self.initialization_success:
#             self.run_sessions()
#         else:
#             sys.exit(1)

#     def run_sessions(self):
#         """Boucle de sessions : login -> application -> deconnexion -> login...

#         Permet de revenir a l'ecran de connexion apres une deconnexion sans
#         fermer le programme. Le programme ne se termine que si l'utilisateur
#         quitte explicitement l'application (bouton Quitter / fermeture de la
#         fenetre) ou ferme la fenetre de connexion sans se connecter.
#         """
#         while True:
#             self.current_user = None
#             self.show_login()
#             if not self.current_user:
#                 # Fenetre de connexion fermee sans connexion -> on quitte
#                 break
#             relogin = self.show_main_application()
#             if not relogin:
#                 # L'utilisateur a quitte l'application -> on quitte
#                 break

#     # ──────────────────────────────────────────────────────────────────────────
#     # CHARGEMENT
#     # ──────────────────────────────────────────────────────────────────────────

#     def load_application(self, splash_root):
#         """Charge l'application en arrière-plan et met à jour le splash."""
#         try:
#             self.splash.update_progress(10,  "Vérification des dépendances...")
#             time.sleep(0.3)
#             self.check_dependencies()

#             self.splash.update_progress(25,  "Configuration de l'environnement...")
#             time.sleep(0.3)
#             self.setup_environment()

#             self.splash.update_progress(40,  "Vérification de la base de données...")
#             time.sleep(0.3)
#             self.verify_database()

#             self.splash.update_progress(60,  "Chargement des modules...")
#             time.sleep(0.3)
#             self.load_modules()

#             self.splash.update_progress(80,  "Initialisation des services...")
#             time.sleep(0.3)
#             self.initialize_services()

#             self.splash.update_progress(100, "Prêt !")
#             time.sleep(0.5)

#             self.initialization_success = True

#         except Exception as e:
#             print(f"❌ Erreur lors du chargement : {e}")
#             self.initialization_success = False
#             messagebox.showerror("Erreur", f"Erreur lors du démarrage :\n{str(e)}")

#         finally:
#             splash_root.after(100, self.splash.close)

#     def check_dependencies(self):
#         """Vérifie les dépendances nécessaires."""
#         missing_deps  = []
#         optional_deps = []

#         for module in ['sqlite3', 'tkinter', 'hashlib', 'datetime', 'csv']:
#             try:
#                 __import__(module)
#                 print(f"✓ Module {module} disponible")
#             except ImportError:
#                 missing_deps.append(module)
#                 print(f"✗ Module {module} manquant")

#         for module, label, install in [
#             ('reportlab',  'Génération PDF',  'pip install reportlab'),
#             ('tkcalendar', 'DatePicker',       'pip install tkcalendar'),
#             ('openpyxl',   'Export Excel',     'pip install openpyxl'),
#             ('PIL',        'Images',           'pip install Pillow'),
#         ]:
#             try:
#                 __import__(module)
#                 print(f"✓ Module {module} installé — {label} disponible")
#             except ImportError:
#                 print(f"○ Module {module} non installé — {label} indisponible")
#                 print(f"   Installation : {install}")
#                 optional_deps.append(module)

#         if missing_deps:
#             raise Exception(f"Modules manquants critiques : {', '.join(missing_deps)}")

#         return True

#     def setup_environment(self):
#         """Configure l'environnement de l'application."""
#         print("\n→ Configuration de l'environnement...")

#         directories = [BASE_PATH, LOG_PATH] + [
#             BASE_PATH / sub for sub in ('backups', 'exports', 'temp', 'reports')
#         ]

#         for directory in directories:
#             directory.mkdir(exist_ok=True, parents=True)
#             print(f"✓ Dossier créé/vérifié : {directory}")

#         # Vérifier les permissions d'écriture
#         test_file = BASE_PATH / "test_write.tmp"
#         try:
#             test_file.touch()
#             test_file.unlink()
#             print("✓ Permissions d'écriture OK")
#         except Exception as e:
#             raise Exception(f"Impossible d'écrire dans {BASE_PATH} : {e}")

#         # Fichier de configuration INI applicatif
#         config_file = BASE_PATH / "app_config.ini"
#         if not config_file.exists():
#             self.create_default_config(config_file)

#         return True

#     def create_default_config(self, config_file):
#         """Crée un fichier de configuration INI par défaut."""
#         config = configparser.ConfigParser()

#         config['APPLICATION'] = {
#             'version':  '3.0',
#             'company':  'STOYANN',
#             'name':     'Quincaillerie Calédonienne'
#         }
#         config['DATABASE'] = {
#             'type':            'sqlite',
#             'backup_enabled':  'true',
#             'backup_interval': '24'
#         }
#         config['EMAIL'] = {
#             'enabled':            'true',
#             'send_confirmations': 'true',
#             'send_reminders':     'true'
#         }
#         config['INTERFACE'] = {
#             'theme':         'modern',
#             'animations':    'true',
#             'sound_effects': 'true'
#         }

#         with open(config_file, 'w', encoding='utf-8') as f:
#             config.write(f)

#         print(f"✓ Fichier de configuration créé : {config_file}")

#     def verify_database(self):
#         """Vérifie et répare la base de données si nécessaire."""
#         print("\n→ Vérification de la base de données...")
#         print(f"   Fichier : {DB_PATH.resolve()}")

#         try:
#             db = Database()
#             avoir_manager = AvoirManager(db)
#             avoir_manager.verify_database_structure()

#             avoirs_count = db.cursor.execute(
#                 "SELECT COUNT(*) FROM avoirs"
#             ).fetchone()[0]
#             users_count  = db.cursor.execute(
#                 "SELECT COUNT(*) FROM users"
#             ).fetchone()[0]

#             print(f"✓ Base de données OK")
#             print(f"   - {avoirs_count} avoirs")
#             print(f"   - {users_count} utilisateurs")

#             self.check_database_integrity(db)
#             self.backup_database()
#             db.close()
#             return True

#         except Exception as e:
#             print(f"⚠ Problème détecté : {e}")
#             if self.repair_database():
#                 print("✓ Base de données réparée")
#                 return True
#             else:
#                 raise Exception("Impossible de réparer la base de données")

#     def check_database_integrity(self, db):
#         """Vérifie l'intégrité de la base de données."""
#         result = db.cursor.execute("PRAGMA integrity_check").fetchone()
#         if result[0] != "ok":
#             raise Exception(f"Problème d'intégrité : {result[0]}")
#         db.cursor.execute("REINDEX")
#         db.cursor.execute("VACUUM")
#         print("✓ Intégrité de la base vérifiée")

#     def backup_database(self):
#         """Crée une sauvegarde horodatée de la base de données."""
#         backup_dir = BASE_PATH / "backups"
#         backup_dir.mkdir(exist_ok=True)

#         timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
#         backup_file = backup_dir / f"avoirs_backup_{timestamp}.db"

#         try:
#             copy2(DB_PATH, backup_file)
#             print(f"✓ Sauvegarde créée : {backup_file.name}")
#             self.clean_old_backups(backup_dir)
#         except Exception as e:
#             print(f"⚠ Erreur lors de la sauvegarde : {e}")

#     def clean_old_backups(self, backup_dir, keep=10):
#         """Supprime les sauvegardes excédentaires (garde les {keep} dernières)."""
#         backups = sorted(backup_dir.glob("avoirs_backup_*.db"))
#         for old in backups[:-keep]:
#             old.unlink()
#             print(f"✓ Ancienne sauvegarde supprimée : {old.name}")

#     def repair_database(self):
#         """Tente une réparation automatique de la base de données."""
#         import sqlite3

#         try:
#             print("→ Tentative de réparation automatique...")
#             conn   = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()

#             cursor.execute("""
#                 UPDATE avoirs
#                 SET montant = CAST(REPLACE(REPLACE(montant, ' ', ''), ',', '.') AS REAL)
#                 WHERE typeof(montant) = 'text'
#             """)
#             cursor.execute("""
#                 UPDATE avoirs SET statut = 'actif'
#                 WHERE statut IS NULL OR statut = ''
#             """)
#             cursor.execute("""
#                 UPDATE avoirs SET statut = 'expiré'
#                 WHERE statut = 'actif' AND date_validite < datetime('now')
#             """)

#             cursor.execute("PRAGMA table_info(avoirs)")
#             columns = [col[1] for col in cursor.fetchall()]
#             for col in ('email_client', 'email_envoye', 'rappel_envoye'):
#                 if col not in columns:
#                     default = "INTEGER DEFAULT 0" if col != 'email_client' else "TEXT"
#                     cursor.execute(f"ALTER TABLE avoirs ADD COLUMN {col} {default}")

#             cursor.execute("PRAGMA table_info(users)")
#             user_columns = [col[1] for col in cursor.fetchall()]
#             if 'email' not in user_columns:
#                 cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

#             conn.commit()
#             conn.close()
#             print("✓ Réparation effectuée avec succès")
#             return True

#         except Exception as e:
#             print(f"✗ Échec de la réparation : {e}")
#             return False

#     def load_modules(self):
#         """Charge les modules de l'application."""
#         print("\n→ Chargement des modules...")

#         for module in [
#             'database.connection',
#             'models.user_manager',
#             'models.avoir_manager',
#             'services.email_service',
#             'config.settings',
#             'gui.login_window',
#         ]:
#             try:
#                 __import__(module)
#                 print(f"✓ Module {module} chargé")
#             except Exception as e:
#                 print(f"⚠ Erreur lors du chargement de {module} : {e}")

#         return True

#     def initialize_services(self):
#         """Initialise les services de l'application."""
#         print("\n→ Initialisation des services...")

#         try:
#             db = Database()
#             db.cursor.execute("SELECT 1")
#             db.close()
#             print("✓ Service base de données OK")
#         except Exception as e:
#             print(f"⚠ Erreur service base de données : {e}")

#         try:
#             from services.email_service import EmailService
#             EmailService()
#             print("✓ Service email initialisé")
#         except Exception as e:
#             print(f"○ Service email non disponible : {e}")

#         return True

#     # ──────────────────────────────────────────────────────────────────────────
#     # FENÊTRES
#     # ──────────────────────────────────────────────────────────────────────────

#     def show_login(self):
#         """Affiche la fenêtre de connexion."""
#         def on_login_success(user):
#             self.current_user = user
#             login_root.quit()
#             login_root.destroy()

#         login_root = tk.Tk()
#         LoginWindow(login_root, on_login_success)

#         # Animation d'ouverture
#         login_root.attributes('-alpha', 0)
#         login_root.update()
#         for i in range(1, 11):
#             login_root.attributes('-alpha', i / 10)
#             login_root.update()
#             time.sleep(0.03)

#         login_root.mainloop()

#     def show_main_application(self):
#         """Affiche l'application principale."""
#         try:
#             from gui_main import MainWindow

#             main_root = tk.Tk()
#             app = MainWindow(main_root, self.current_user)
#             main_root.protocol("WM_DELETE_WINDOW", app.quit_app)
#             main_root.minsize(1200, 700)

#             if os.name == 'nt':
#                 main_root.state('zoomed')
#             else:
#                 main_root.attributes('-zoomed', True)

#             print(f"\n✓ Application démarrée pour {self.current_user[1]}")
#             print("=" * 60)

#             main_root.mainloop()

#             # Apres la fermeture de la boucle : determiner s'il s'agit d'une
#             # deconnexion (retour au login) ou d'une fermeture de l'application.
#             relogin = bool(getattr(app, 'relogin', False))

#             try:
#                 main_root.destroy()
#             except Exception:
#                 pass

#             return relogin

#         except Exception as e:
#             print(f"❌ Erreur lors du lancement de l'application : {e}")
#             messagebox.showerror(
#                 "Erreur",
#                 f"Impossible de lancer l'application :\n{str(e)}"
#             )
#             sys.exit(1)


# # ══════════════════════════════════════════════════════════════════════════════
# # UTILITAIRES
# # ══════════════════════════════════════════════════════════════════════════════

# def show_startup_banner():
#     """Affiche la bannière de démarrage dans la console."""
#     print("""
#     ╔══════════════════════════════════════════════════════════╗
#     ║                                                          ║
#     ║      MODULE DE GESTION DES AVOIRS CLIENTS v3.0           ║
#     ║                                                          ║
#     ║              QUINCAILLERIE CALÉDONIENNE                  ║
#     ║                                                          ║
#     ║                     © 2025 STOYANN                       ║
#     ║                                                          ║
#     ╚══════════════════════════════════════════════════════════╝

#     → Adresse  : 13 Rue Ampère - Ducos, Nouvelle-Calédonie
#     → Téléphone: 27 47 22
#     → Email    : support@robot-nc.com
#     → Serveur  : \\\\192.168.0.250\\Bases
#     """)


# # ══════════════════════════════════════════════════════════════════════════════
# # POINT D'ENTRÉE
# # ══════════════════════════════════════════════════════════════════════════════

# def main():
#     """Point d'entrée principal de l'application."""
#     try:
#         show_startup_banner()
#         # La config initiale a déjà été traitée en haut du fichier
#         ApplicationManager().start()

#     except KeyboardInterrupt:
#         print("\n\n→ Application interrompue par l'utilisateur")
#         sys.exit(0)

#     except Exception as e:
#         print(f"\n\n❌ Erreur fatale : {e}")
#         import traceback
#         traceback.print_exc()

#         root = tk.Tk()
#         root.withdraw()
#         messagebox.showerror(
#             "Erreur Fatale",
#             f"Une erreur critique s'est produite :\n\n{str(e)}\n\n"
#             "L'application va se fermer."
#         )
#         sys.exit(1)


# if __name__ == "__main__":
#     main()

# -*- coding: utf-8 -*-
"""
Point d'entrée principal
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce fichier gère:
- La vérification de l'accessibilité du réseau
- La configuration initiale au premier lancement (super-user + chemin BDD)
- Le splash screen de chargement
- L'authentification
- Le lancement de l'application principale
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
from pathlib import Path
import threading
import time
from datetime import datetime
from shutil import copy2
import configparser

# Ajouter le répertoire courant au path Python
sys.path.insert(0, str(Path(__file__).parent))

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION INITIALE
# ══════════════════════════════════════════════════════════════════════════════

from config.paths import (
    is_first_run, init_paths, get_paths,
    get_current_db_path, get_base_path
)


def do_initial_config():
    """
    Effectue la configuration initiale si nécessaire.

    - Si c'est le premier lancement (pas de config.json réseau) :
      affiche le dialogue de configuration (chemin BDD + super-user).
    - Sinon : logue simplement le chemin de la BDD active.

    Returns:
        dict | None: Résultat de la configuration initiale, ou None si
                     déjà configuré.

    Raises:
        SystemExit: Si le réseau est inaccessible ou si l'utilisateur
                    annule la configuration initiale.
    """
    try:
        first = is_first_run()
    except RuntimeError as e:
        # Réseau inaccessible — on ne peut pas continuer
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erreur réseau",
            f"{e}\n\nL'application ne peut pas démarrer sans accès au serveur."
        )
        root.destroy()
        sys.exit(1)

    if first:
        print("\n*** PREMIER LANCEMENT - CONFIGURATION INITIALE ***\n")
        from database.initial_setup import show_initial_config_dialog
        result = show_initial_config_dialog()

        if not result.get('configured'):
            print("Configuration annulée. Fermeture de l'application.")
            sys.exit(0)

        print(f"\n✓ Configuration initiale terminée.")
        print(f"   Base de données  : {result['db_path']}")
        print(f"   Super-utilisateur : {result['email']}\n")
        return result

    else:
        # Lancement normal — on trace la BDD utilisée
        db_path = get_current_db_path()
        print(f"\n→ Base de données active : {db_path.resolve()}")
        return None


# Faire la configuration initiale AVANT tout autre import dépendant des chemins
initial_config_result = do_initial_config()

# Initialiser les chemins (crée les dossiers si nécessaire)
init_paths()

# Récupérer les chemins après initialisation
_paths    = get_paths()
BASE_PATH = _paths['BASE_PATH']
DB_PATH   = _paths['DB_PATH']
LOG_PATH  = _paths['LOG_PATH']

# Imports des modules applicatifs (après init_paths)
from gui.login_window import LoginWindow
from gui.splash_screen import SplashScreen
from models.avoir_manager import AvoirManager
from database.connection import Database

# Si premier lancement : mettre à jour les credentials admin en base
if initial_config_result and initial_config_result.get('configured'):
    db = Database()
    if initial_config_result.get('email') and initial_config_result.get('password_hash'):
        db.update_admin_credentials(
            initial_config_result['email'],
            initial_config_result['password_hash']
        )
        print(f"✓ Compte super-utilisateur configuré : {initial_config_result['email']}")
    db.close()


# ══════════════════════════════════════════════════════════════════════════════
# GESTIONNAIRE D'APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class ApplicationManager:
    """
    Gestionnaire principal de l'application.

    Gère le cycle de vie complet :
    - Splash screen de chargement
    - Authentification
    - Fenêtre principale
    """

    def __init__(self):
        self.splash               = None
        self.login_window         = None
        self.main_window          = None
        self.current_user         = None
        self.initialization_success = False

    def start(self):
        """Démarre l'application avec splash screen."""
        splash_root = tk.Tk()
        self.splash = SplashScreen(splash_root)

        loading_thread = threading.Thread(
            target=self.load_application, args=(splash_root,), daemon=True
        )
        loading_thread.start()

        splash_root.mainloop()

        if self.initialization_success:
            self.run_sessions()
        else:
            sys.exit(1)

    def run_sessions(self):
        """Boucle de sessions : login -> application -> deconnexion -> login...

        Permet de revenir a l'ecran de connexion apres une deconnexion sans
        fermer le programme. Le programme ne se termine que si l'utilisateur
        quitte explicitement l'application (bouton Quitter / fermeture de la
        fenetre) ou ferme la fenetre de connexion sans se connecter.
        """
        while True:
            self.current_user = None
            self.show_login()
            if not self.current_user:
                # Fenetre de connexion fermee sans connexion -> on quitte
                break
            relogin = self.show_main_application()
            if not relogin:
                # L'utilisateur a quitte l'application -> on quitte
                break

    # ──────────────────────────────────────────────────────────────────────────
    # CHARGEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def load_application(self, splash_root):
        """Charge l'application en arrière-plan et met à jour le splash."""
        try:
            self.splash.update_progress(10,  "Vérification des dépendances...")
            time.sleep(0.3)
            self.check_dependencies()

            self.splash.update_progress(25,  "Configuration de l'environnement...")
            time.sleep(0.3)
            self.setup_environment()

            self.splash.update_progress(40,  "Vérification de la base de données...")
            time.sleep(0.3)
            self.verify_database()

            self.splash.update_progress(60,  "Chargement des modules...")
            time.sleep(0.3)
            self.load_modules()

            self.splash.update_progress(80,  "Initialisation des services...")
            time.sleep(0.3)
            self.initialize_services()

            self.splash.update_progress(100, "Prêt !")
            time.sleep(0.5)

            self.initialization_success = True

        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            self.initialization_success = False
            messagebox.showerror("Erreur", f"Erreur lors du démarrage :\n{str(e)}")

        finally:
            splash_root.after(100, self.splash.close)

    def check_dependencies(self):
        """Vérifie les dépendances nécessaires."""
        missing_deps  = []
        optional_deps = []

        for module in ['sqlite3', 'tkinter', 'hashlib', 'datetime', 'csv']:
            try:
                __import__(module)
                print(f"✓ Module {module} disponible")
            except ImportError:
                missing_deps.append(module)
                print(f"✗ Module {module} manquant")

        for module, label, install in [
            ('reportlab',  'Génération PDF',  'pip install reportlab'),
            ('tkcalendar', 'DatePicker',       'pip install tkcalendar'),
            ('openpyxl',   'Export Excel',     'pip install openpyxl'),
            ('PIL',        'Images',           'pip install Pillow'),
        ]:
            try:
                __import__(module)
                print(f"✓ Module {module} installé — {label} disponible")
            except ImportError:
                print(f"○ Module {module} non installé — {label} indisponible")
                print(f"   Installation : {install}")
                optional_deps.append(module)

        if missing_deps:
            raise Exception(f"Modules manquants critiques : {', '.join(missing_deps)}")

        return True

    def setup_environment(self):
        """Configure l'environnement de l'application."""
        print("\n→ Configuration de l'environnement...")

        directories = [BASE_PATH, LOG_PATH] + [
            BASE_PATH / sub for sub in ('backups', 'exports', 'temp', 'reports')
        ]

        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)
            print(f"✓ Dossier créé/vérifié : {directory}")

        # Vérifier les permissions d'écriture
        test_file = BASE_PATH / "test_write.tmp"
        try:
            test_file.touch()
            test_file.unlink()
            print("✓ Permissions d'écriture OK")
        except Exception as e:
            raise Exception(f"Impossible d'écrire dans {BASE_PATH} : {e}")

        # Fichier de configuration INI applicatif
        config_file = BASE_PATH / "app_config.ini"
        if not config_file.exists():
            self.create_default_config(config_file)

        return True

    def create_default_config(self, config_file):
        """Crée un fichier de configuration INI par défaut."""
        config = configparser.ConfigParser()

        config['APPLICATION'] = {
            'version':  '3.0',
            'company':  'STOYANN',
            'name':     'Quincaillerie Calédonienne'
        }
        config['DATABASE'] = {
            'type':            'sqlite',
            'backup_enabled':  'true',
            'backup_interval': '24'
        }
        config['EMAIL'] = {
            'enabled':            'true',
            'send_confirmations': 'true',
            'send_reminders':     'true'
        }
        config['INTERFACE'] = {
            'theme':         'modern',
            'animations':    'true',
            'sound_effects': 'true'
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

        print(f"✓ Fichier de configuration créé : {config_file}")

    def verify_database(self):
        """Vérifie et répare la base de données si nécessaire."""
        print("\n→ Vérification de la base de données...")
        print(f"   Fichier : {DB_PATH.resolve()}")

        db = None
        try:
            db = Database()
            avoir_manager = AvoirManager(db)
            avoir_manager.verify_database_structure()

            avoirs_count = db.cursor.execute(
                "SELECT COUNT(*) FROM avoirs"
            ).fetchone()[0]
            users_count  = db.cursor.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            print(f"✓ Base de données OK")
            print(f"   - {avoirs_count} avoirs")
            print(f"   - {users_count} utilisateurs")

            self.check_database_integrity(db)
            self.backup_database()
            return True

        except Exception as e:
            print(f"⚠ Problème détecté : {e}")
            # IMPORTANT : fermer la connexion courante AVANT toute tentative de
            # reparation. Sinon repair_database() ouvre une 2e connexion
            # concurrente alors que celle-ci detient encore un verrou, et
            # echoue a son tour en "database is locked".
            try:
                if db is not None:
                    db.close()
                    db = None
            except Exception:
                pass
            if self.repair_database():
                print("✓ Base de données réparée")
                return True
            else:
                raise Exception("Impossible de réparer la base de données")
        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def check_database_integrity(self, db):
        """Vérifie l'intégrité de la base de données."""
        import sqlite3
        result = db.cursor.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            raise Exception(f"Problème d'intégrité : {result[0]}")
        # REINDEX et VACUUM sont des operations de MAINTENANCE qui exigent un
        # verrou EXCLUSIF. Sur une base partagee en reseau, elles peuvent
        # echouer en "database is locked" si un autre poste est connecte. Ce
        # n'est PAS une corruption : on ignore alors le verrou et on continue,
        # au lieu de declencher une "reparation" inutile.
        try:
            db.cursor.execute("REINDEX")
            db.cursor.execute("VACUUM")
            print("✓ Intégrité de la base vérifiée")
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                print("ℹ Maintenance (REINDEX/VACUUM) ignoree : base en cours "
                      "d'utilisation par un autre poste. Integrite OK.")
            else:
                raise

    def backup_database(self):
        """Crée une sauvegarde horodatée de la base de données."""
        backup_dir = BASE_PATH / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"avoirs_backup_{timestamp}.db"

        try:
            copy2(DB_PATH, backup_file)
            print(f"✓ Sauvegarde créée : {backup_file.name}")
            self.clean_old_backups(backup_dir)
        except Exception as e:
            print(f"⚠ Erreur lors de la sauvegarde : {e}")

    def clean_old_backups(self, backup_dir, keep=10):
        """Supprime les sauvegardes excédentaires (garde les {keep} dernières)."""
        backups = sorted(backup_dir.glob("avoirs_backup_*.db"))
        for old in backups[:-keep]:
            old.unlink()
            print(f"✓ Ancienne sauvegarde supprimée : {old.name}")

    def repair_database(self):
        """Tente une réparation automatique de la base de données."""
        import sqlite3

        try:
            print("→ Tentative de réparation automatique...")
            conn   = sqlite3.connect(DB_PATH, timeout=30)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE avoirs
                SET montant = CAST(REPLACE(REPLACE(montant, ' ', ''), ',', '.') AS REAL)
                WHERE typeof(montant) = 'text'
            """)
            cursor.execute("""
                UPDATE avoirs SET statut = 'actif'
                WHERE statut IS NULL OR statut = ''
            """)
            cursor.execute("""
                UPDATE avoirs SET statut = 'expiré'
                WHERE statut = 'actif' AND date_validite < datetime('now')
            """)

            cursor.execute("PRAGMA table_info(avoirs)")
            columns = [col[1] for col in cursor.fetchall()]
            for col in ('email_client', 'email_envoye', 'rappel_envoye'):
                if col not in columns:
                    default = "INTEGER DEFAULT 0" if col != 'email_client' else "TEXT"
                    cursor.execute(f"ALTER TABLE avoirs ADD COLUMN {col} {default}")

            cursor.execute("PRAGMA table_info(users)")
            user_columns = [col[1] for col in cursor.fetchall()]
            if 'email' not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

            conn.commit()
            conn.close()
            print("✓ Réparation effectuée avec succès")
            return True

        except Exception as e:
            print(f"✗ Échec de la réparation : {e}")
            return False

    def load_modules(self):
        """Charge les modules de l'application."""
        print("\n→ Chargement des modules...")

        for module in [
            'database.connection',
            'models.user_manager',
            'models.avoir_manager',
            'services.email_service',
            'config.settings',
            'gui.login_window',
        ]:
            try:
                __import__(module)
                print(f"✓ Module {module} chargé")
            except Exception as e:
                print(f"⚠ Erreur lors du chargement de {module} : {e}")

        return True

    def initialize_services(self):
        """Initialise les services de l'application."""
        print("\n→ Initialisation des services...")

        try:
            db = Database()
            db.cursor.execute("SELECT 1")
            db.close()
            print("✓ Service base de données OK")
        except Exception as e:
            print(f"⚠ Erreur service base de données : {e}")

        try:
            from services.email_service import EmailService
            EmailService()
            print("✓ Service email initialisé")
        except Exception as e:
            print(f"○ Service email non disponible : {e}")

        return True

    # ──────────────────────────────────────────────────────────────────────────
    # FENÊTRES
    # ──────────────────────────────────────────────────────────────────────────

    def show_login(self):
        """Affiche la fenêtre de connexion."""
        def on_login_success(user):
            self.current_user = user
            login_root.quit()
            login_root.destroy()

        login_root = tk.Tk()
        LoginWindow(login_root, on_login_success)

        # Animation d'ouverture
        login_root.attributes('-alpha', 0)
        login_root.update()
        for i in range(1, 11):
            login_root.attributes('-alpha', i / 10)
            login_root.update()
            time.sleep(0.03)

        login_root.mainloop()

    def show_main_application(self):
        """Affiche l'application principale."""
        try:
            from gui_main import MainWindow

            main_root = tk.Tk()
            app = MainWindow(main_root, self.current_user)
            main_root.protocol("WM_DELETE_WINDOW", app.quit_app)
            main_root.minsize(1200, 700)

            if os.name == 'nt':
                main_root.state('zoomed')
            else:
                main_root.attributes('-zoomed', True)

            print(f"\n✓ Application démarrée pour {self.current_user[1]}")
            print("=" * 60)

            main_root.mainloop()

            # Apres la fermeture de la boucle : determiner s'il s'agit d'une
            # deconnexion (retour au login) ou d'une fermeture de l'application.
            relogin = bool(getattr(app, 'relogin', False))

            try:
                main_root.destroy()
            except Exception:
                pass

            return relogin

        except Exception as e:
            print(f"❌ Erreur lors du lancement de l'application : {e}")
            messagebox.showerror(
                "Erreur",
                f"Impossible de lancer l'application :\n{str(e)}"
            )
            sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def show_startup_banner():
    """Affiche la bannière de démarrage dans la console."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║      MODULE DE GESTION DES AVOIRS CLIENTS v3.0           ║
    ║                                                          ║
    ║              QUINCAILLERIE CALÉDONIENNE                  ║
    ║                                                          ║
    ║                     © 2025 STOYANN                       ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝

    → Adresse  : 13 Rue Ampère - Ducos, Nouvelle-Calédonie
    → Téléphone: 27 47 22
    → Email    : support@robot-nc.com
    → Serveur  : \\\\192.168.0.250\\Bases
    """)


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée principal de l'application."""
    try:
        show_startup_banner()
        # La config initiale a déjà été traitée en haut du fichier
        ApplicationManager().start()

    except KeyboardInterrupt:
        print("\n\n→ Application interrompue par l'utilisateur")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n❌ Erreur fatale : {e}")
        import traceback
        traceback.print_exc()

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erreur Fatale",
            f"Une erreur critique s'est produite :\n\n{str(e)}\n\n"
            "L'application va se fermer."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()