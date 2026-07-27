# -*- coding: utf-8 -*-
"""
Module Database - Gestion de la base de données
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module expose:
- Database: Classe principale de gestion SQLite
- get_db_path: Fonction pour obtenir le chemin de la BDD
- show_initial_config_dialog: Dialogue de configuration initiale
"""

from database.connection import Database, get_db_path
from database.initial_setup import show_initial_config_dialog

__all__ = [
    'Database',
    'get_db_path',
    'show_initial_config_dialog'
]
