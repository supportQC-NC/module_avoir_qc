# -*- coding: utf-8 -*-
"""
=============================================================================
                    GESTION DE LA BASE DE DONNEES
=============================================================================
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne
Entreprise: STOYANN
Version: 1.5 - Configuration initiale et gestion avoirs partiels

Ce fichier contient la classe Database qui gère toutes les opérations
sur la base de données SQLite.
=============================================================================
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
import threading
from pathlib import Path

# Imports depuis le module config
from config.paths import get_base_path, get_admin_config
from config.settings import USER_ROLES


def get_db_path():
    """
    Retourne le chemin de la base de données.
    
    Returns:
        Path: Chemin vers le fichier avoirs.db
    """
    base = get_base_path()
    return base / "avoirs.db"


class Database:
    """
    Classe de gestion de la base de données SQLite.
    
    Gère toutes les opérations CRUD sur les tables:
    - users: Utilisateurs de l'application
    - avoirs: Avoirs clients
    - historique_utilisation: Historique des utilisations d'avoirs
    - logs: Journal des actions
    - email_history: Historique des emails envoyés
    
    Attributes:
        thread_safe (bool): Si True, utilise des connexions séparées par requête
        db_path (Path): Chemin vers la base de données
        conn: Connexion SQLite (None si thread_safe)
        cursor: Curseur SQLite (None si thread_safe)
    """
    
    def __init__(self, thread_safe=False):
        """
        Initialise la connexion à la base de données.
        
        Args:
            thread_safe (bool): Active le mode thread-safe pour utilisation
                               avec le service d'email en arrière-plan
        """
        self.thread_safe = thread_safe
        self.db_path = get_db_path()
        
        # Ne PAS créer le dossier ici - il doit être créé par init_paths()
        
        if thread_safe:
            self.conn = None
            self.cursor = None
        else:
            # timeout=30 : attend jusqu'a 30 s qu'un verrou se libere avant
            # d'echouer en "database is locked" (utile sur base partagee reseau).
            self.conn = sqlite3.connect(str(self.db_path), timeout=30)
            try:
                self.conn.execute("PRAGMA busy_timeout = 30000")
            except Exception:
                pass
            self.cursor = self.conn.cursor()
            
        self.create_tables()
        self.init_admin()
    
    # =========================================================================
    # GESTION DES CONNEXIONS
    # =========================================================================
    
    def get_connection(self):
        """
        Obtient une connexion thread-safe si nécessaire.
        
        Returns:
            sqlite3.Connection: Connexion à la base de données
        """
        if self.thread_safe:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30
            )
            try:
                conn.execute("PRAGMA busy_timeout = 30000")
            except Exception:
                pass
            return conn
        return self.conn
    
    def execute_thread_safe(self, query, params=()):
        """
        Exécute une requête de manière thread-safe.
        
        Args:
            query (str): Requête SQL à exécuter
            params (tuple): Paramètres de la requête
            
        Returns:
            list: Résultats de la requête
        """
        if self.thread_safe:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                result = cursor.fetchall()
                return result
            finally:
                conn.close()
        else:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.fetchall()
    
    # =========================================================================
    # UTILITAIRES DE DATE
    # =========================================================================
    
    @staticmethod
    def format_date_for_db(dt):
        """
        Formate une date pour la base de données (format texte ISO).
        
        Args:
            dt: Date à formater (datetime, str ou autre)
            
        Returns:
            str: Date formatée ou None
        """
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(dt, str):
            return dt
        else:
            return str(dt)
    
    @staticmethod
    def parse_date_from_db(date_str):
        """
        Parse une date depuis la base de données.
        
        Args:
            date_str: Chaîne de date ou objet datetime
            
        Returns:
            datetime: Date parsée ou None
        """
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        if isinstance(date_str, str):
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        
        return None
    
    # =========================================================================
    # CREATION DES TABLES
    # =========================================================================
    
    def create_tables(self):
        """
        Création des tables de la base de données.
        
        Crée les tables si elles n'existent pas:
        - users: Gestion des utilisateurs
        - avoirs: Avoirs clients avec gestion partielle
        - historique_utilisation: Traçabilité des utilisations
        - logs: Journal des actions
        - email_history: Historique des emails
        """
        if self.thread_safe:
            conn = self.get_connection()
            cursor = conn.cursor()
        else:
            cursor = self.cursor
            conn = self.conn
        
        try:
            # Table des utilisateurs avec email inclus
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    role TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Table des avoirs avec colonnes pour gestion partielle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS avoirs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_avoir TEXT UNIQUE NOT NULL,
                    numero_client TEXT NOT NULL,
                    nom_client TEXT,
                    email_client TEXT,
                    numero_facture TEXT NOT NULL,
                    date_facture TEXT,
                    type_avoir TEXT NOT NULL,
                    montant REAL NOT NULL,
                    numero_facture_avoir TEXT,
                    date_creation TEXT DEFAULT CURRENT_TIMESTAMP,
                    date_validite TEXT,
                    statut TEXT DEFAULT 'actif',
                    date_utilisation TEXT,
                    utilisateur_creation TEXT,
                    utilisateur_validation TEXT,
                    signature TEXT,
                    email_envoye INTEGER DEFAULT 0,
                    rappel_envoye INTEGER DEFAULT 0,
                    montant_utilise REAL DEFAULT 0,
                    montant_restant REAL,
                    numero_facture_utilisation TEXT,
                    avoir_parent_id INTEGER,
                    est_avoir_enfant INTEGER DEFAULT 0,
                    forcage_autorise_par TEXT,
                    commentaire_blocage TEXT,
                    bloque_par TEXT,
                    date_blocage TEXT,
                    FOREIGN KEY (avoir_parent_id) REFERENCES avoirs (id)
                )
            ''')
            
            # Table des historiques d'utilisation pour traçabilité
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historique_utilisation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    avoir_id INTEGER NOT NULL,
                    numero_avoir TEXT NOT NULL,
                    date_utilisation TEXT DEFAULT CURRENT_TIMESTAMP,
                    montant_utilise REAL NOT NULL,
                    numero_facture TEXT NOT NULL,
                    utilisateur TEXT NOT NULL,
                    type_utilisation TEXT,
                    avoir_enfant_id INTEGER,
                    FOREIGN KEY (avoir_id) REFERENCES avoirs (id),
                    FOREIGN KEY (avoir_enfant_id) REFERENCES avoirs (id)
                )
            ''')
            
            # Table des logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    user TEXT,
                    action TEXT,
                    details TEXT
                )
            ''')
            
            # Table pour les emails envoyés
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_avoir TEXT,
                    email_to TEXT,
                    email_type TEXT,
                    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    error_message TEXT
                )
            ''')
            
            conn.commit()
            
            # Mise à jour des tables existantes si nécessaire
            self.update_existing_tables(cursor, conn)
            
        finally:
            if self.thread_safe:
                conn.close()
    
    def update_existing_tables(self, cursor=None, conn=None):
        """
        Met à jour les tables existantes avec les nouveaux champs.
        
        Cette méthode ajoute les colonnes manquantes aux tables existantes
        pour permettre les migrations de base de données.
        
        Args:
            cursor: Curseur SQLite (optionnel)
            conn: Connexion SQLite (optionnel)
        """
        if cursor is None:
            if self.thread_safe:
                conn = self.get_connection()
                cursor = conn.cursor()
                close_after = True
            else:
                cursor = self.cursor
                conn = self.conn
                close_after = False
        else:
            close_after = False
        
        try:
            # MISE A JOUR DE LA TABLE USERS
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [column[1] for column in cursor.fetchall()]
            
            if 'email' not in user_columns:
                print("[+] Ajout de la colonne 'email' a la table users...")
                cursor.execute('ALTER TABLE users ADD COLUMN email TEXT')
                print("[OK] Colonne 'email' ajoutee avec succes")
            
            # MISE A JOUR DE LA TABLE AVOIRS
            cursor.execute("PRAGMA table_info(avoirs)")
            avoir_columns = [column[1] for column in cursor.fetchall()]
            
            # Liste des colonnes à ajouter si absentes
            columns_to_add = [
                ('email_client', 'TEXT', None),
                ('email_envoye', 'INTEGER DEFAULT 0', None),
                ('rappel_envoye', 'INTEGER DEFAULT 0', None),
                ('rappel_final_envoye', 'INTEGER DEFAULT 0', None),
                ('montant_utilise', 'REAL DEFAULT 0', None),
                ('montant_restant', 'REAL', 'UPDATE avoirs SET montant_restant = montant WHERE montant_restant IS NULL'),
                ('numero_facture_utilisation', 'TEXT', None),
                ('avoir_parent_id', 'INTEGER', None),
                ('est_avoir_enfant', 'INTEGER DEFAULT 0', None),
                ('forcage_autorise_par', 'TEXT', None),
                ('commentaire_blocage', 'TEXT', None),
                ('bloque_par', 'TEXT', None),
                ('date_blocage', 'TEXT', None)
            ]
            
            for col_name, col_type, post_update in columns_to_add:
                if col_name not in avoir_columns:
                    print(f"[+] Ajout de la colonne '{col_name}' a la table avoirs...")
                    cursor.execute(f'ALTER TABLE avoirs ADD COLUMN {col_name} {col_type}')
                    if post_update:
                        cursor.execute(post_update)
                    print(f"[OK] Colonne '{col_name}' ajoutee")
            
            # Créer la table historique_utilisation si elle n'existe pas
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='historique_utilisation'
            """)
            if not cursor.fetchone():
                print("[+] Creation de la table 'historique_utilisation'...")
                cursor.execute('''
                    CREATE TABLE historique_utilisation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        avoir_id INTEGER NOT NULL,
                        numero_avoir TEXT NOT NULL,
                        date_utilisation TEXT DEFAULT CURRENT_TIMESTAMP,
                        montant_utilise REAL NOT NULL,
                        numero_facture TEXT NOT NULL,
                        utilisateur TEXT NOT NULL,
                        type_utilisation TEXT,
                        avoir_enfant_id INTEGER,
                        FOREIGN KEY (avoir_id) REFERENCES avoirs (id),
                        FOREIGN KEY (avoir_enfant_id) REFERENCES avoirs (id)
                    )
                ''')
                print("[OK] Table 'historique_utilisation' creee")
                
            conn.commit()
            print("[OK] Mise a jour de la structure de base de donnees terminee")
            
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"[!] Avertissement lors de la mise a jour des tables: {e}")
        except Exception as e:
            print(f"[X] Erreur lors de la mise a jour des tables: {e}")
        finally:
            if close_after and self.thread_safe:
                conn.close()
    
    # =========================================================================
    # GESTION DE L'ADMINISTRATEUR
    # =========================================================================
    
    def init_admin(self):
        """
        Crée ou met à jour le compte admin.
        
        Utilise les credentials de la configuration persistante si disponibles,
        sinon utilise les valeurs par défaut.
        """
        if self.thread_safe:
            conn = self.get_connection()
            cursor = conn.cursor()
        else:
            cursor = self.cursor
            conn = self.conn
        
        try:
            # Vérifier si on a une config admin sauvegardée
            admin_config = get_admin_config()
            if admin_config:
                email = admin_config.get('email', 'admin@quincaillerie-nc.com')
                hashed_pwd = admin_config.get('password_hash', hashlib.sha256("admin123".encode()).hexdigest())
            else:
                email = "admin@quincaillerie-nc.com"
                hashed_pwd = hashlib.sha256("admin123".encode()).hexdigest()
            
            admin_exists = cursor.execute(
                "SELECT * FROM users WHERE username = 'admin'"
            ).fetchone()
            
            if not admin_exists:
                # Créer l'admin
                cursor.execute(
                    "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                    ("admin", hashed_pwd, email, USER_ROLES['SUPER_USER'])
                )
                conn.commit()
                print("[OK] Compte admin cree avec succes")
            else:
                # Mettre à jour l'admin avec les credentials configurés
                cursor.execute(
                    "UPDATE users SET password = ?, email = ? WHERE username = 'admin'",
                    (hashed_pwd, email)
                )
                conn.commit()
                print("[OK] Compte admin mis a jour")
        finally:
            if self.thread_safe:
                conn.close()
    
    def update_admin_credentials(self, email, password_hash):
        """
        Met à jour les credentials de l'admin.
        
        Args:
            email (str): Nouvel email admin
            password_hash (str): Nouveau hash du mot de passe
        """
        if self.thread_safe:
            self.execute_thread_safe(
                "UPDATE users SET email = ?, password = ? WHERE username = 'admin'",
                (email, password_hash)
            )
        else:
            self.cursor.execute(
                "UPDATE users SET email = ?, password = ? WHERE username = 'admin'",
                (email, password_hash)
            )
            self.conn.commit()
    
    # =========================================================================
    # GESTION DES LOGS
    # =========================================================================
    
    def add_log(self, user, action, details=""):
        """
        Ajoute une entrée dans les logs.
        
        Args:
            user (str): Nom de l'utilisateur
            action (str): Action effectuée
            details (str): Détails supplémentaires
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if self.thread_safe:
            self.execute_thread_safe(
                "INSERT INTO logs (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
                (timestamp, user, action, details)
            )
        else:
            self.cursor.execute(
                "INSERT INTO logs (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
                (timestamp, user, action, details)
            )
            self.conn.commit()
    
    # =========================================================================
    # HISTORIQUE D'UTILISATION
    # =========================================================================
    
    def add_utilisation_history(self, avoir_id, numero_avoir, montant_utilise, 
                               numero_facture, utilisateur, type_utilisation='total', 
                               avoir_enfant_id=None):
        """
        Enregistre l'historique d'utilisation d'un avoir.
        
        Args:
            avoir_id (int): ID de l'avoir utilisé
            numero_avoir (str): Numéro de l'avoir
            montant_utilise (float): Montant utilisé
            numero_facture (str): Numéro de facture d'utilisation
            utilisateur (str): Utilisateur ayant effectué l'opération
            type_utilisation (str): 'total' ou 'partiel'
            avoir_enfant_id (int, optional): ID de l'avoir enfant créé
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        query = """INSERT INTO historique_utilisation 
                   (avoir_id, numero_avoir, date_utilisation, montant_utilise, 
                    numero_facture, utilisateur, type_utilisation, avoir_enfant_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (avoir_id, numero_avoir, timestamp, montant_utilise, 
                 numero_facture, utilisateur, type_utilisation, avoir_enfant_id)
        
        if self.thread_safe:
            self.execute_thread_safe(query, params)
        else:
            self.cursor.execute(query, params)
            self.conn.commit()
    
    # =========================================================================
    # HISTORIQUE DES EMAILS
    # =========================================================================
    
    def add_email_log(self, numero_avoir, email_to, email_type, status, error_message=None):
        """
        Enregistre l'historique des emails envoyés.
        
        Args:
            numero_avoir (str): Numéro de l'avoir concerné
            email_to (str): Adresse email du destinataire
            email_type (str): Type d'email (CREATION, RAPPEL, etc.)
            status (str): Statut (SUCCESS, ERROR)
            error_message (str, optional): Message d'erreur si échec
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        query = """INSERT INTO email_history 
                   (numero_avoir, email_to, email_type, sent_at, status, error_message) 
                   VALUES (?, ?, ?, ?, ?, ?)"""
        params = (numero_avoir, email_to, email_type, timestamp, status, error_message)
        
        if self.thread_safe:
            self.execute_thread_safe(query, params)
        else:
            self.cursor.execute(query, params)
            self.conn.commit()
    
    # =========================================================================
    # REQUETES SUR LES AVOIRS
    # =========================================================================
    
    def get_avoirs_to_remind(self, days_before_expiry=15):
        """
        Récupère les avoirs à rappeler avant expiration.
        
        Args:
            days_before_expiry (int): Nombre de jours avant expiration
            
        Returns:
            list: Liste des avoirs à rappeler
        """
        date_limite = (datetime.now() + timedelta(days=days_before_expiry)).strftime('%Y-%m-%d')
        date_now = datetime.now().strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM avoirs 
            WHERE statut IN ('actif', 'utilise_partiellement')
            AND email_client IS NOT NULL 
            AND email_client != ''
            AND rappel_envoye = 0
            AND date_validite <= ?
            AND date_validite > ?
        """
        
        if self.thread_safe:
            return self.execute_thread_safe(query, (date_limite, date_now))
        else:
            return self.cursor.execute(query, (date_limite, date_now)).fetchall()
    
    def get_avoirs_for_final_reminder(self, days_before_expiry=1):
        """
        Récupère les avoirs pour le rappel FINAL (juste avant expiration).

        Indépendant du rappel normal : on se base sur rappel_final_envoye, afin
        qu'un avoir ayant déjà reçu un rappel normal puisse tout de même recevoir
        son rappel final, et sans jamais de doublon.

        Args:
            days_before_expiry (int): Fenêtre (en jours) avant expiration.

        Returns:
            list: Avoirs encore valides expirant dans la fenêtre et n'ayant pas
                  encore reçu de rappel final.
        """
        date_limite = (datetime.now() + timedelta(days=days_before_expiry)).strftime('%Y-%m-%d')
        date_now = datetime.now().strftime('%Y-%m-%d')

        query = """
            SELECT * FROM avoirs
            WHERE statut IN ('actif', 'utilise_partiellement')
            AND email_client IS NOT NULL
            AND email_client != ''
            AND (rappel_final_envoye = 0 OR rappel_final_envoye IS NULL)
            AND date_validite <= ?
            AND date_validite > ?
        """

        if self.thread_safe:
            return self.execute_thread_safe(query, (date_limite, date_now))
        else:
            return self.cursor.execute(query, (date_limite, date_now)).fetchall()
    
    def get_avoir_enfants(self, avoir_parent_id):
        """
        Récupère tous les avoirs enfants d'un avoir parent.
        
        Args:
            avoir_parent_id (int): ID de l'avoir parent
            
        Returns:
            list: Liste des avoirs enfants
        """
        query = """
            SELECT * FROM avoirs 
            WHERE avoir_parent_id = ? 
            ORDER BY date_creation DESC
        """
        
        if self.thread_safe:
            return self.execute_thread_safe(query, (avoir_parent_id,))
        else:
            return self.cursor.execute(query, (avoir_parent_id,)).fetchall()
    
    def get_historique_utilisation(self, avoir_id):
        """
        Récupère l'historique d'utilisation d'un avoir.
        
        Args:
            avoir_id (int): ID de l'avoir
            
        Returns:
            list: Historique des utilisations
        """
        query = """
            SELECT * FROM historique_utilisation 
            WHERE avoir_id = ? 
            ORDER BY date_utilisation DESC
        """
        
        if self.thread_safe:
            return self.execute_thread_safe(query, (avoir_id,))
        else:
            return self.cursor.execute(query, (avoir_id,)).fetchall()
    
    # =========================================================================
    # MARQUAGE DES AVOIRS
    # =========================================================================
    
    def mark_reminder_sent(self, numero_avoir):
        """
        Marque un avoir comme ayant reçu un rappel.
        
        Args:
            numero_avoir (str): Numéro de l'avoir
        """
        query = "UPDATE avoirs SET rappel_envoye = 1 WHERE numero_avoir = ?"
        
        if self.thread_safe:
            self.execute_thread_safe(query, (numero_avoir,))
        else:
            self.cursor.execute(query, (numero_avoir,))
            self.conn.commit()
    
    def claim_reminder(self, numero_avoir, final=False):
        """
        « Réserve » l'envoi d'un rappel pour un avoir de façon ATOMIQUE, afin
        d'éviter tout doublon — y compris lorsque plusieurs postes tournent en
        même temps.

        Met le drapeau (rappel_envoye ou rappel_final_envoye) à 1 UNIQUEMENT
        s'il valait 0. La réservation réussit pour un seul appelant.

        Args:
            numero_avoir (str): Numéro de l'avoir.
            final (bool): True pour le rappel FINAL, False pour le rappel normal.

        Returns:
            bool: True si CET appel a réservé l'envoi (donc doit envoyer),
                  False si un rappel a déjà été (ou est en train d'être) envoyé.
        """
        col = 'rappel_final_envoye' if final else 'rappel_envoye'
        query = (f"UPDATE avoirs SET {col} = 1 "
                 f"WHERE numero_avoir = ? AND ({col} = 0 OR {col} IS NULL)")
        conn = self.get_connection()
        try:
            try:
                conn.execute("PRAGMA busy_timeout = 30000")
            except Exception:
                pass
            cur = conn.cursor()
            cur.execute(query, (numero_avoir,))
            conn.commit()
            return cur.rowcount == 1
        except Exception as e:
            print(f"Erreur claim_reminder ({numero_avoir}): {e}")
            return False
        finally:
            if self.thread_safe:
                conn.close()

    def release_reminder(self, numero_avoir, final=False):
        """
        Annule une réservation de rappel (remet le drapeau à 0). À utiliser
        uniquement si l'envoi de l'email a ÉCHOUÉ, pour permettre une nouvelle
        tentative au prochain cycle.
        """
        col = 'rappel_final_envoye' if final else 'rappel_envoye'
        query = f"UPDATE avoirs SET {col} = 0 WHERE numero_avoir = ?"
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (numero_avoir,))
            conn.commit()
        except Exception as e:
            print(f"Erreur release_reminder ({numero_avoir}): {e}")
        finally:
            if self.thread_safe:
                conn.close()

    def reminder_already_logged(self, numero_avoir, final=False):
        """
        Indique si un rappel (normal ou final) a déjà été envoyé AVEC SUCCÈS
        pour cet avoir, d'après l'historique des emails (email_history).

        C'est une sécurité supplémentaire contre les doublons, indépendante des
        drapeaux de la table avoirs.
        """
        etype = 'RAPPEL_FINAL' if final else 'RAPPEL'
        query = ("SELECT COUNT(*) FROM email_history "
                 "WHERE numero_avoir = ? AND email_type = ? AND status = 'SUCCESS'")
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (numero_avoir, etype))
            row = cur.fetchone()
            return bool(row and row[0] > 0)
        except Exception as e:
            print(f"Erreur reminder_already_logged ({numero_avoir}): {e}")
            return False
        finally:
            if self.thread_safe:
                conn.close()
    
    def mark_email_sent(self, numero_avoir):
        """
        Marque un avoir comme ayant reçu l'email de création.
        
        Args:
            numero_avoir (str): Numéro de l'avoir
        """
        query = "UPDATE avoirs SET email_envoye = 1 WHERE numero_avoir = ?"
        
        if self.thread_safe:
            self.execute_thread_safe(query, (numero_avoir,))
        else:
            self.cursor.execute(query, (numero_avoir,))
            self.conn.commit()
    
    # =========================================================================
    # FERMETURE
    # =========================================================================
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if not self.thread_safe and self.conn:
            self.conn.close()