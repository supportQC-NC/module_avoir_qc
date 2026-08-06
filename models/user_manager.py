# # # -*- coding: utf-8 -*-
# # """
# # Gestionnaire des utilisateurs
# # Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

# # Ce module gère toutes les opérations liées aux utilisateurs:
# # - Authentification (par username ou email)
# # - Création, modification, suppression
# # - Gestion des statuts actif/inactif
# # """

# # import sqlite3
# # import hashlib


# # class UserManager:
# #     """
# #     Gestionnaire des utilisateurs.
    
# #     Gère l'authentification et les opérations CRUD sur les utilisateurs.
    
# #     Attributes:
# #         db: Instance de Database pour les opérations SQL
# #     """
    
# #     def __init__(self, db):
# #         """
# #         Initialise le gestionnaire avec une connexion à la base.
        
# #         Args:
# #             db: Instance de Database
# #         """
# #         self.db = db
    
# #     # ══════════════════════════════════════════════════════════════════════════════
# #     # AUTHENTIFICATION
# #     # ══════════════════════════════════════════════════════════════════════════════
    
# #     def authenticate(self, username, password):
# #         """
# #         Authentifie un utilisateur par username OU email.
        
# #         Args:
# #             username: Nom d'utilisateur ou adresse email
# #             password: Mot de passe en clair
            
# #         Returns:
# #             tuple: Données utilisateur si authentifié, None sinon
# #         """
# #         hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
        
# #         # Essayer d'abord par username
# #         user = self.db.cursor.execute(
# #             "SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1",
# #             (username, hashed_pwd)
# #         ).fetchone()
        
# #         # Si pas trouvé, essayer par email
# #         if not user:
# #             user = self.db.cursor.execute(
# #                 "SELECT * FROM users WHERE email = ? AND password = ? AND is_active = 1",
# #                 (username, hashed_pwd)
# #             ).fetchone()
        
# #         return user
    
# #     # ══════════════════════════════════════════════════════════════════════════════
# #     # CRÉATION
# #     # ══════════════════════════════════════════════════════════════════════════════
    
# #     def add_user(self, username, password, email, role):
# #         """
# #         Ajoute un nouvel utilisateur.
        
# #         Args:
# #             username: Nom d'utilisateur unique
# #             password: Mot de passe en clair (sera hashé)
# #             email: Adresse email
# #             role: Rôle (admin, super_user, user, viewer)
            
# #         Returns:
# #             bool: True si créé, False si username existe déjà
# #         """
# #         try:
# #             hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
# #             self.db.cursor.execute(
# #                 "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
# #                 (username, hashed_pwd, email, role)
# #             )
# #             self.db.conn.commit()
# #             return True
# #         except sqlite3.IntegrityError:
# #             return False
    
# #     # ══════════════════════════════════════════════════════════════════════════════
# #     # MODIFICATION
# #     # ══════════════════════════════════════════════════════════════════════════════
    
# #     def update_user(self, user_id, email=None, password=None, role=None, is_active=None):
# #         """
# #         Met à jour un utilisateur existant.
        
# #         Seuls les paramètres non-None sont modifiés.
        
# #         Args:
# #             user_id: ID de l'utilisateur
# #             email: Nouvelle adresse email (optionnel)
# #             password: Nouveau mot de passe (optionnel)
# #             role: Nouveau rôle (optionnel)
# #             is_active: Nouveau statut actif (optionnel)
            
# #         Returns:
# #             bool: True si mis à jour, False sinon
# #         """
# #         try:
# #             current = self.db.cursor.execute(
# #                 "SELECT * FROM users WHERE id = ?", (user_id,)
# #             ).fetchone()
            
# #             if not current:
# #                 return False
            
# #             updates = []
# #             params = []
            
# #             if email is not None:
# #                 updates.append("email = ?")
# #                 params.append(email)
            
# #             if password and password.strip():
# #                 updates.append("password = ?")
# #                 params.append(hashlib.sha256(password.encode()).hexdigest())
            
# #             if role is not None:
# #                 updates.append("role = ?")
# #                 params.append(role)
            
# #             if is_active is not None:
# #                 updates.append("is_active = ?")
# #                 params.append(1 if is_active else 0)
            
# #             if not updates:
# #                 return True
            
# #             query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
# #             params.append(user_id)
            
# #             self.db.cursor.execute(query, params)
# #             self.db.conn.commit()
# #             return True
            
# #         except Exception as e:
# #             print(f"Erreur lors de la mise à jour: {e}")
# #             return False
    
# #     def update_password(self, username, new_password):
# #         """
# #         Met à jour le mot de passe d'un utilisateur.
        
# #         Args:
# #             username: Nom d'utilisateur
# #             new_password: Nouveau mot de passe en clair
# #         """
# #         hashed_pwd = hashlib.sha256(new_password.encode()).hexdigest()
# #         self.db.cursor.execute(
# #             "UPDATE users SET password = ? WHERE username = ?",
# #             (hashed_pwd, username)
# #         )
# #         self.db.conn.commit()
    
# #     def toggle_user_status(self, user_id):
# #         """
# #         Active/désactive un utilisateur.
        
# #         Args:
# #             user_id: ID de l'utilisateur
            
# #         Returns:
# #             bool: True si basculé, False si utilisateur non trouvé
# #         """
# #         user = self.db.cursor.execute(
# #             "SELECT is_active FROM users WHERE id = ?", (user_id,)
# #         ).fetchone()
        
# #         if user:
# #             new_status = 0 if user[0] == 1 else 1
# #             self.db.cursor.execute(
# #                 "UPDATE users SET is_active = ? WHERE id = ?",
# #                 (new_status, user_id)
# #             )
# #             self.db.conn.commit()
# #             return True
# #         return False
    
# #     # ══════════════════════════════════════════════════════════════════════════════
# #     # SUPPRESSION
# #     # ══════════════════════════════════════════════════════════════════════════════
    
# #     def delete_user(self, user_id):
# #         """
# #         Supprime un utilisateur.
        
# #         Note: L'utilisateur 'admin' ne peut pas être supprimé.
        
# #         Args:
# #             user_id: ID de l'utilisateur
            
# #         Returns:
# #             bool: True si supprimé, False sinon
# #         """
# #         try:
# #             user = self.db.cursor.execute(
# #                 "SELECT username FROM users WHERE id = ?", (user_id,)
# #             ).fetchone()
            
# #             # Protection: ne pas supprimer l'admin
# #             if user and user[0] == 'admin':
# #                 return False
            
# #             self.db.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
# #             self.db.conn.commit()
# #             return True
# #         except Exception as e:
# #             print(f"Erreur lors de la suppression: {e}")
# #             return False
    
# #     # ══════════════════════════════════════════════════════════════════════════════
# #     # LECTURE
# #     # ══════════════════════════════════════════════════════════════════════════════
    
# #     def get_all_users(self):
# #         """
# #         Récupère tous les utilisateurs (sans email).
        
# #         Returns:
# #             list: Liste des utilisateurs (id, username, password, role, created_at, is_active)
# #         """
# #         try:
# #             users = self.db.cursor.execute(
# #                 """SELECT id, username, password, role, 
# #                    datetime(created_at) as created_at, is_active 
# #                    FROM users 
# #                    ORDER BY id DESC"""
# #             ).fetchall()
# #             return users
# #         except Exception as e:
# #             print(f"Erreur lors de la récupération des utilisateurs: {e}")
# #             return []
    
# #     def get_all_users_with_email(self):
# #         """
# #         Récupère tous les utilisateurs avec leur email.
        
# #         Returns:
# #             list: Liste des utilisateurs (id, username, email, role, created_at, is_active)
# #         """
# #         try:
# #             users = self.db.cursor.execute(
# #                 """SELECT id, username, email, role, 
# #                    datetime(created_at) as created_at, is_active 
# #                    FROM users 
# #                    ORDER BY id DESC"""
# #             ).fetchall()
# #             return users
# #         except Exception as e:
# #             print(f"Erreur lors de la récupération des utilisateurs: {e}")
# #             return []


# # -*- coding: utf-8 -*-
# """
# Gestionnaire des utilisateurs
# Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

# Ce module gère toutes les opérations liées aux utilisateurs:
# - Authentification (par username ou email)
# - Création, modification, suppression
# - Gestion des statuts actif/inactif
# """

# import sqlite3
# import hashlib


# class UserManager:
#     """
#     Gestionnaire des utilisateurs.
    
#     Gère l'authentification et les opérations CRUD sur les utilisateurs.
    
#     Attributes:
#         db: Instance de Database pour les opérations SQL
#     """
    
#     def __init__(self, db):
#         """
#         Initialise le gestionnaire avec une connexion à la base.
        
#         Args:
#             db: Instance de Database
#         """
#         self.db = db
    
#     # ══════════════════════════════════════════════════════════════════════════════
#     # AUTHENTIFICATION
#     # ══════════════════════════════════════════════════════════════════════════════
    
#     def authenticate(self, username, password):
#         """
#         Authentifie un utilisateur par username OU email.
        
#         Args:
#             username: Nom d'utilisateur ou adresse email
#             password: Mot de passe en clair
            
#         Returns:
#             tuple: Données utilisateur si authentifié, None sinon
#         """
#         hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
        
#         # Essayer d'abord par username
#         user = self.db.cursor.execute(
#             "SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1",
#             (username, hashed_pwd)
#         ).fetchone()
        
#         # Si pas trouvé, essayer par email
#         if not user:
#             user = self.db.cursor.execute(
#                 "SELECT * FROM users WHERE email = ? AND password = ? AND is_active = 1",
#                 (username, hashed_pwd)
#             ).fetchone()
        
#         return user
    
#     # ══════════════════════════════════════════════════════════════════════════════
#     # CRÉATION
#     # ══════════════════════════════════════════════════════════════════════════════
    
#     def add_user(self, username, password, email, role):
#         """
#         Ajoute un nouvel utilisateur.
        
#         Args:
#             username: Nom d'utilisateur unique
#             password: Mot de passe en clair (sera hashé)
#             email: Adresse email
#             role: Rôle (admin, super_user, user, viewer)
            
#         Returns:
#             bool: True si créé, False si username existe déjà
#         """
#         try:
#             hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
#             self.db.cursor.execute(
#                 "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
#                 (username, hashed_pwd, email, role)
#             )
#             self.db.conn.commit()
#             return True
#         except sqlite3.IntegrityError:
#             return False
    
#     # ══════════════════════════════════════════════════════════════════════════════
#     # MODIFICATION
#     # ══════════════════════════════════════════════════════════════════════════════
    
#     def update_user(self, user_id, email=None, password=None, role=None, is_active=None):
#         """
#         Met à jour un utilisateur existant.
        
#         Seuls les paramètres non-None sont modifiés.
        
#         Args:
#             user_id: ID de l'utilisateur
#             email: Nouvelle adresse email (optionnel)
#             password: Nouveau mot de passe (optionnel)
#             role: Nouveau rôle (optionnel)
#             is_active: Nouveau statut actif (optionnel)
            
#         Returns:
#             bool: True si mis à jour, False sinon
#         """
#         try:
#             current = self.db.cursor.execute(
#                 "SELECT * FROM users WHERE id = ?", (user_id,)
#             ).fetchone()
            
#             if not current:
#                 return False
            
#             updates = []
#             params = []
            
#             if email is not None:
#                 updates.append("email = ?")
#                 params.append(email)
            
#             if password and password.strip():
#                 updates.append("password = ?")
#                 params.append(hashlib.sha256(password.encode()).hexdigest())
            
#             if role is not None:
#                 updates.append("role = ?")
#                 params.append(role)
            
#             if is_active is not None:
#                 updates.append("is_active = ?")
#                 params.append(1 if is_active else 0)
            
#             if not updates:
#                 return True
            
#             query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
#             params.append(user_id)
            
#             self.db.cursor.execute(query, params)
#             self.db.conn.commit()
#             return True
            
#         except Exception as e:
#             print(f"Erreur lors de la mise à jour: {e}")
#             return False
    
#     def update_password(self, username, new_password):
#         """
#         Met à jour le mot de passe d'un utilisateur.
        
#         Args:
#             username: Nom d'utilisateur
#             new_password: Nouveau mot de passe en clair
#         """
#         hashed_pwd = hashlib.sha256(new_password.encode()).hexdigest()
#         self.db.cursor.execute(
#             "UPDATE users SET password = ? WHERE username = ?",
#             (hashed_pwd, username)
#         )
#         self.db.conn.commit()
    
#     def toggle_user_status(self, user_id):
#         """
#         Active/désactive un utilisateur.
        
#         Args:
#             user_id: ID de l'utilisateur
            
#         Returns:
#             bool: True si basculé, False si utilisateur non trouvé
#         """
#         user = self.db.cursor.execute(
#             "SELECT is_active FROM users WHERE id = ?", (user_id,)
#         ).fetchone()
        
#         if user:
#             new_status = 0 if user[0] == 1 else 1
#             self.db.cursor.execute(
#                 "UPDATE users SET is_active = ? WHERE id = ?",
#                 (new_status, user_id)
#             )
#             self.db.conn.commit()
#             return True
#         return False
    
#     # ══════════════════════════════════════════════════════════════════════════════
#     # SUPPRESSION
#     # ══════════════════════════════════════════════════════════════════════════════
    
#     def delete_user(self, user_id):
#         """
#         Supprime un utilisateur.
        
#         Note: L'utilisateur 'admin' ne peut pas être supprimé.
        
#         Args:
#             user_id: ID de l'utilisateur
            
#         Returns:
#             bool: True si supprimé, False sinon
#         """
#         try:
#             user = self.db.cursor.execute(
#                 "SELECT username FROM users WHERE id = ?", (user_id,)
#             ).fetchone()
            
#             # Protection: ne pas supprimer l'admin
#             if user and user[0] == 'admin':
#                 return False
            
#             self.db.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
#             self.db.conn.commit()
#             return True
#         except Exception as e:
#             print(f"Erreur lors de la suppression: {e}")
#             return False
    
#     # ══════════════════════════════════════════════════════════════════════════════
#     # LECTURE
#     # ══════════════════════════════════════════════════════════════════════════════
    
#     def get_all_users(self):
#         """
#         Récupère tous les utilisateurs (sans email).
        
#         Returns:
#             list: Liste des utilisateurs (id, username, password, role, created_at, is_active)
#         """
#         try:
#             users = self.db.cursor.execute(
#                 """SELECT id, username, password, role, 
#                    datetime(created_at) as created_at, is_active 
#                    FROM users 
#                    ORDER BY id DESC"""
#             ).fetchall()
#             return users
#         except Exception as e:
#             print(f"Erreur lors de la récupération des utilisateurs: {e}")
#             return []
    
#     def get_all_users_with_email(self):
#         """
#         Récupère tous les utilisateurs avec leur email.
        
#         Returns:
#             list: Liste des utilisateurs (id, username, email, role, created_at, is_active)
#         """
#         try:
#             users = self.db.cursor.execute(
#                 """SELECT id, username, email, role, 
#                    datetime(created_at) as created_at, is_active 
#                    FROM users 
#                    ORDER BY id DESC"""
#             ).fetchall()
#             return users
#         except Exception as e:
#             print(f"Erreur lors de la récupération des utilisateurs: {e}")
#             return []
    
#     def get_active_usernames_by_roles(self, roles):
#         """
#         Récupère les noms d'utilisateur (username) des comptes ACTIFS
#         appartenant à l'un des rôles fournis.
        
#         Utilisé notamment pour alimenter la liste déroulante des responsables
#         autorisés à forcer l'utilisation d'un avoir expiré.
        
#         Args:
#             roles (list): Liste des rôles à inclure
#                           (ex: ['responsable', 'comptabilite'])
            
#         Returns:
#             list: Liste des usernames (str), triés par ordre alphabétique
#         """
#         try:
#             if not roles:
#                 return []
#             placeholders = ", ".join("?" for _ in roles)
#             query = (
#                 f"SELECT username FROM users "
#                 f"WHERE is_active = 1 AND role IN ({placeholders}) "
#                 f"ORDER BY username COLLATE NOCASE ASC"
#             )
#             rows = self.db.cursor.execute(query, tuple(roles)).fetchall()
#             return [row[0] for row in rows if row and row[0]]
#         except Exception as e:
#             print(f"Erreur lors de la récupération des responsables: {e}")
#             return []

# -*- coding: utf-8 -*-
"""
Gestionnaire des utilisateurs
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module gère toutes les opérations liées aux utilisateurs:
- Authentification (par username ou email)
- Création, modification, suppression
- Gestion des statuts actif/inactif
"""

import sqlite3
import hashlib


class UserManager:
    """
    Gestionnaire des utilisateurs.
    
    Gère l'authentification et les opérations CRUD sur les utilisateurs.
    
    Attributes:
        db: Instance de Database pour les opérations SQL
    """
    
    def __init__(self, db):
        """
        Initialise le gestionnaire avec une connexion à la base.
        
        Args:
            db: Instance de Database
        """
        self.db = db
    
    # ══════════════════════════════════════════════════════════════════════════════
    # AUTHENTIFICATION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def authenticate(self, username, password):
        """
        Authentifie un utilisateur par username OU email.
        
        Args:
            username: Nom d'utilisateur ou adresse email
            password: Mot de passe en clair
            
        Returns:
            tuple: Données utilisateur si authentifié, None sinon
        """
        hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
        
        # Essayer d'abord par username
        user = self.db.cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1",
            (username, hashed_pwd)
        ).fetchone()
        
        # Si pas trouvé, essayer par email
        if not user:
            user = self.db.cursor.execute(
                "SELECT * FROM users WHERE email = ? AND password = ? AND is_active = 1",
                (username, hashed_pwd)
            ).fetchone()
        
        return user
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CRÉATION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def add_user(self, username, password, email, role):
        """
        Ajoute un nouvel utilisateur.
        
        Args:
            username: Nom d'utilisateur unique
            password: Mot de passe en clair (sera hashé)
            email: Adresse email
            role: Rôle (admin, super_user, user, viewer)
            
        Returns:
            bool: True si créé, False si username existe déjà
        """
        try:
            hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
            self.db.cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                (username, hashed_pwd, email, role)
            )
            self.db.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MODIFICATION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def update_user(self, user_id, email=None, password=None, role=None, is_active=None):
        """
        Met à jour un utilisateur existant.
        
        Seuls les paramètres non-None sont modifiés.
        
        Args:
            user_id: ID de l'utilisateur
            email: Nouvelle adresse email (optionnel)
            password: Nouveau mot de passe (optionnel)
            role: Nouveau rôle (optionnel)
            is_active: Nouveau statut actif (optionnel)
            
        Returns:
            bool: True si mis à jour, False sinon
        """
        try:
            current = self.db.cursor.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            
            if not current:
                return False
            
            updates = []
            params = []
            
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            
            if password and password.strip():
                updates.append("password = ?")
                params.append(hashlib.sha256(password.encode()).hexdigest())
            
            if role is not None:
                updates.append("role = ?")
                params.append(role)
            
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(1 if is_active else 0)
            
            if not updates:
                return True
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            params.append(user_id)
            
            self.db.cursor.execute(query, params)
            self.db.conn.commit()
            return True
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour: {e}")
            return False
    
    def update_password(self, username, new_password):
        """
        Met à jour le mot de passe d'un utilisateur.
        
        Args:
            username: Nom d'utilisateur
            new_password: Nouveau mot de passe en clair
        """
        hashed_pwd = hashlib.sha256(new_password.encode()).hexdigest()
        self.db.cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed_pwd, username)
        )
        self.db.conn.commit()
    
    def toggle_user_status(self, user_id):
        """
        Active/désactive un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si basculé, False si utilisateur non trouvé
        """
        user = self.db.cursor.execute(
            "SELECT is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        
        if user:
            new_status = 0 if user[0] == 1 else 1
            self.db.cursor.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (new_status, user_id)
            )
            self.db.conn.commit()
            return True
        return False
    
    # ══════════════════════════════════════════════════════════════════════════════
    # SUPPRESSION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def delete_user(self, user_id):
        """
        Supprime un utilisateur.
        
        Note: L'utilisateur 'admin' ne peut pas être supprimé.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si supprimé, False sinon
        """
        try:
            user = self.db.cursor.execute(
                "SELECT username FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            
            # Protection: ne pas supprimer l'admin
            if user and user[0] == 'admin':
                return False
            
            self.db.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression: {e}")
            return False
    
    # ══════════════════════════════════════════════════════════════════════════════
    # LECTURE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def get_all_users(self):
        """
        Récupère tous les utilisateurs (sans email).
        
        Returns:
            list: Liste des utilisateurs (id, username, password, role, created_at, is_active)
        """
        try:
            users = self.db.cursor.execute(
                """SELECT id, username, password, role, 
                   datetime(created_at) as created_at, is_active 
                   FROM users 
                   ORDER BY id DESC"""
            ).fetchall()
            return users
        except Exception as e:
            print(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []
    
    def get_all_users_with_email(self):
        """
        Récupère tous les utilisateurs avec leur email.
        
        Returns:
            list: Liste des utilisateurs (id, username, email, role, created_at, is_active)
        """
        try:
            users = self.db.cursor.execute(
                """SELECT id, username, email, role, 
                   datetime(created_at) as created_at, is_active 
                   FROM users 
                   ORDER BY id DESC"""
            ).fetchall()
            return users
        except Exception as e:
            print(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []
    
    def get_active_usernames_by_roles(self, roles):
        """
        Récupère les noms d'utilisateur (username) des comptes ACTIFS
        appartenant à l'un des rôles fournis.
        
        Utilisé notamment pour alimenter la liste déroulante des responsables
        autorisés à forcer l'utilisation d'un avoir expiré.
        
        Args:
            roles (list): Liste des rôles à inclure
                          (ex: ['responsable', 'comptabilite'])
            
        Returns:
            list: Liste des usernames (str), triés par ordre alphabétique
        """
        try:
            if not roles:
                return []
            placeholders = ", ".join("?" for _ in roles)
            query = (
                f"SELECT username FROM users "
                f"WHERE is_active = 1 AND role IN ({placeholders}) "
                f"ORDER BY username COLLATE NOCASE ASC"
            )
            rows = self.db.cursor.execute(query, tuple(roles)).fetchall()
            return [row[0] for row in rows if row and row[0]]
        except Exception as e:
            print(f"Erreur lors de la récupération des responsables: {e}")
            return []

    def get_active_usernames(self):
        """
        Récupère les noms d'utilisateur (username) de TOUS les comptes ACTIFS.

        Utilisé pour alimenter le menu déroulant de la fenêtre de connexion,
        afin que l'utilisateur choisisse son nom au lieu de le saisir.

        Returns:
            list: Liste des usernames (str), triés par ordre alphabétique
        """
        try:
            rows = self.db.cursor.execute(
                "SELECT username FROM users "
                "WHERE is_active = 1 "
                "ORDER BY username COLLATE NOCASE ASC"
            ).fetchall()
            return [row[0] for row in rows if row and row[0]]
        except Exception as e:
            print(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []