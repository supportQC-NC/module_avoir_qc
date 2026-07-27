# -*- coding: utf-8 -*-
"""
Module Models - Gestionnaires métier
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module expose:
- UserManager: Gestion des utilisateurs (CRUD, authentification)
- AvoirManager: Gestion des avoirs (création, utilisation, statistiques)
"""

from models.user_manager import UserManager
from models.avoir_manager import AvoirManager

__all__ = [
    'UserManager',
    'AvoirManager'
]
