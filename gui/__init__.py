# -*- coding: utf-8 -*-
"""
Module GUI - Interfaces graphiques
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module expose:
- LoginWindow: Fenêtre de connexion
- MainWindow: Fenêtre principale de l'application
- SplashScreen: Écran de démarrage
"""

from gui.login_window import LoginWindow
from gui.splash_screen import SplashScreen

# MainWindow sera importée depuis gui/main_window.py quand elle sera créée

__all__ = [
    'LoginWindow',
    'SplashScreen'
]
