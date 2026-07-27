# -*- coding: utf-8 -*-
"""
Écran de démarrage
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Écran de chargement avec:
- Animation de progression
- Logo QC
- Informations de version
"""

import tkinter as tk
from tkinter import ttk
import time


class SplashScreen:
    """
    Écran de démarrage moderne avec animation.
    
    Affiche une fenêtre de chargement avec barre de progression
    pendant l'initialisation de l'application.
    
    Attributes:
        root: Fenêtre Tkinter racine
        progress: Widget de barre de progression
        status_label: Label pour les messages de statut
        progress_value: Valeur actuelle de progression
        is_loading: Flag indiquant si le chargement est en cours
    """
    
    def __init__(self, root):
        """
        Initialise l'écran de démarrage.
        
        Args:
            root: Fenêtre Tkinter racine
        """
        self.root = root
        self.root.title("Chargement...")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        # Enlever les bordures de la fenêtre
        self.root.overrideredirect(True)
        
        # Centrer la fenêtre
        self.center_window()
        
        # Couleurs de la Quincaillerie
        self.colors = {
            'primary': '#fff001',      # Jaune QC
            'secondary': '#000000',    # Noir
            'white': '#ffffff',
            'text': '#333333'
        }
        
        # Configuration du fond
        self.root.configure(bg=self.colors['primary'])
        
        # Construction de l'interface
        self._build_ui()
        
        # Animation de chargement
        self.progress_value = 0
        self.is_loading = True
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CONSTRUCTION DE L'INTERFACE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def _build_ui(self):
        """Construit l'interface utilisateur."""
        # Container principal
        main_frame = tk.Frame(self.root, bg=self.colors['primary'])
        main_frame.pack(fill='both', expand=True)
        
        # ══════════════════════════════════════════════════════════════════════════
        # LOGO QC
        # ══════════════════════════════════════════════════════════════════════════
        logo_frame = tk.Frame(main_frame, bg=self.colors['primary'])
        logo_frame.pack(pady=(50, 20))
        
        # Cercle avec initiales QC
        logo_canvas = tk.Canvas(
            logo_frame,
            width=100,
            height=100,
            bg=self.colors['primary'],
            highlightthickness=0
        )
        logo_canvas.pack()
        
        # Dessiner le cercle noir
        logo_canvas.create_oval(
            5, 5, 95, 95,
            fill=self.colors['secondary'],
            outline=self.colors['white'],
            width=3
        )
        
        # Texte QC en jaune sur le cercle noir
        logo_canvas.create_text(
            50, 50,
            text="QC",
            font=('Arial', 36, 'bold'),
            fill=self.colors['primary']
        )
        
        # ══════════════════════════════════════════════════════════════════════════
        # TITRE ET SOUS-TITRE
        # ══════════════════════════════════════════════════════════════════════════
        tk.Label(
            main_frame,
            text="QUINCAILLERIE CALÉDONIENNE",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['primary'],
            fg=self.colors['secondary']
        ).pack()
        
        tk.Label(
            main_frame,
            text="Module de Gestion des Avoirs",
            font=('Segoe UI', 12),
            bg=self.colors['primary'],
            fg=self.colors['text']
        ).pack(pady=(5, 20))
        
        # ══════════════════════════════════════════════════════════════════════════
        # BARRE DE PROGRESSION
        # ══════════════════════════════════════════════════════════════════════════
        self.progress = ttk.Progressbar(
            main_frame,
            length=300,
            mode='determinate',
            style='Splash.Horizontal.TProgressbar'
        )
        self.progress.pack(pady=20)
        
        # Style de la barre de progression
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Splash.Horizontal.TProgressbar',
            background=self.colors['secondary'],
            troughcolor=self.colors['white'],
            bordercolor=self.colors['secondary'],
            lightcolor=self.colors['secondary'],
            darkcolor=self.colors['secondary']
        )
        
        # ══════════════════════════════════════════════════════════════════════════
        # LABEL DE STATUT
        # ══════════════════════════════════════════════════════════════════════════
        self.status_label = tk.Label(
            main_frame,
            text="Initialisation...",
            font=('Segoe UI', 10),
            bg=self.colors['primary'],
            fg=self.colors['text']
        )
        self.status_label.pack()
        
        # ══════════════════════════════════════════════════════════════════════════
        # VERSION ET COPYRIGHT
        # ══════════════════════════════════════════════════════════════════════════
        tk.Label(
            main_frame,
            text="Version 2.0",
            font=('Segoe UI', 8),
            bg=self.colors['primary'],
            fg=self.colors['text']
        ).pack(side='bottom', pady=(0, 10))
        
        tk.Label(
            main_frame,
            text="© 2025 SUPPORT QC",
            font=('Segoe UI', 8),
            bg=self.colors['primary'],
            fg=self.colors['text']
        ).pack(side='bottom')
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MÉTHODES DE CONTRÔLE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.root.update_idletasks()
        width = 500
        height = 350
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def update_progress(self, value, message=""):
        """
        Met à jour la barre de progression.
        
        Args:
            value: Valeur de progression (0-100)
            message: Message de statut à afficher (optionnel)
        """
        self.progress_value = value
        self.progress['value'] = value
        if message:
            self.status_label.config(text=message)
        self.root.update()
    
    def close(self):
        """Ferme le splash screen avec animation de fondu."""
        # Animation de fondu (de 100% à 0%)
        for alpha in range(10, -1, -1):
            self.root.attributes('-alpha', alpha / 10)
            self.root.update()
            time.sleep(0.03)
        self.root.destroy()
