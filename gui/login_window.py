

# -*- coding: utf-8 -*-
"""
Interface de connexion
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Fenêtre de connexion avec:
- Authentification par username ou email
- Interface aux couleurs de la Quincaillerie (jaune/noir)
- Support optionnel des logos PIL
"""

import tkinter as tk
from tkinter import messagebox, ttk
import os

from database.connection import Database
from models.user_manager import UserManager
from config.settings import UI_CONFIG

# Import optionnel de PIL pour les logos
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class LoginWindow:
    """
    Fenêtre de connexion de l'application.
    
    Attributes:
        root: Fenêtre Tkinter racine
        on_success: Callback appelé après connexion réussie
        db: Instance de Database
        user_manager: Instance de UserManager
    """
    
    def __init__(self, root, on_success):
        """
        Initialise la fenêtre de connexion.
        
        Args:
            root: Fenêtre Tkinter racine
            on_success: Fonction callback(user) appelée après connexion réussie
        """
        self.root = root
        self.on_success = on_success
        self.db = Database()
        self.user_manager = UserManager(self.db)
        
        self.setup_ui()
        
        # Bind Enter key pour connexion rapide
        self.root.bind('<Return>', lambda e: self.login())
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CONSTRUCTION DE L'INTERFACE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def setup_ui(self):
        """Configure l'interface de connexion."""
        self.root.title("Connexion - Quincaillerie Calédonienne")
        self.root.geometry(f"{UI_CONFIG['LOGIN_WIDTH']}x{UI_CONFIG['LOGIN_HEIGHT']}")
        
        # Couleur de fond
        self.root.configure(bg='#ffffff')
        
        # Centrer la fenêtre
        self.center_window()
        
        # Frame principale avec fond jaune/noir
        main_container = tk.Frame(self.root, bg='#fff001')
        main_container.pack(fill='both', expand=True)
        
        # ══════════════════════════════════════════════════════════════════════════
        # BANDE NOIRE EN HAUT
        # ══════════════════════════════════════════════════════════════════════════
        top_band = tk.Frame(main_container, bg='#000000', height=60)
        top_band.pack(fill='x')
        top_band.pack_propagate(False)
        
        tk.Label(top_band, text="Quincaillerie Calédonienne", 
                font=('Arial', 14, 'bold'), 
                bg='#000000', fg='#fff001').pack(pady=15)
        
        # ══════════════════════════════════════════════════════════════════════════
        # FRAME CENTRALE BLANCHE
        # ══════════════════════════════════════════════════════════════════════════
        center_frame = tk.Frame(main_container, bg='white', relief='raised', bd=2)
        center_frame.place(relx=0.5, rely=0.55, anchor='center', width=350, height=320)
        
        # Logo ou icône
        self._setup_logo(center_frame)
        
        # Titre du module
        tk.Label(center_frame, text="Module Gestion des Avoirs", 
                font=('Arial', 14, 'bold'), 
                bg='white', fg='#333').pack(pady=(0, 20))
        
        # ══════════════════════════════════════════════════════════════════════════
        # FORMULAIRE
        # ══════════════════════════════════════════════════════════════════════════
        form_frame = tk.Frame(center_frame, bg='white')
        form_frame.pack(pady=10)
        
        # Username (menu déroulant des utilisateurs disponibles)
        user_frame = tk.Frame(form_frame, bg='white')
        user_frame.grid(row=0, column=0, columnspan=2, pady=5)
        tk.Label(user_frame, text="User:", font=('Arial', 10), bg='white').pack(side='left', padx=(0, 5))

        # Récupérer la liste des utilisateurs actifs pour le menu déroulant
        try:
            usernames = self.user_manager.get_active_usernames()
        except Exception:
            usernames = []

        self.username_var = tk.StringVar()
        self.username_combo = ttk.Combobox(
            user_frame,
            textvariable=self.username_var,
            values=usernames,
            width=18,
            font=('Arial', 12),
            state='readonly'
        )
        self.username_combo.pack(side='left')
        # Quand un utilisateur est choisi, placer le focus sur le mot de passe
        self.username_combo.bind(
            '<<ComboboxSelected>>',
            lambda e: self.password_entry.focus()
        )
        
        # Password
        pass_frame = tk.Frame(form_frame, bg='white')
        pass_frame.grid(row=1, column=0, columnspan=2, pady=5)
        tk.Label(pass_frame, text="Pass:", font=('Arial', 10), bg='white').pack(side='left', padx=(0, 5))
        self.password_entry = tk.Entry(pass_frame, width=20, show='•', font=('Arial', 12), relief='solid', bd=1)
        self.password_entry.pack(side='left')

        # Focus initial sur le menu déroulant des utilisateurs
        self.username_combo.focus()

        # Bouton connexion
        login_button = tk.Button(form_frame, text="SE CONNECTER", 
                                command=self.login,
                                bg='#000000', fg='#fff001', 
                                font=('Arial', 11, 'bold'),
                                width=20, height=2,
                                cursor='hand2',
                                relief='raised', bd=2)
        login_button.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Effet hover sur le bouton
        def on_enter(e):
            login_button['bg'] = '#333333'
        def on_leave(e):
            login_button['bg'] = '#000000'
        
        login_button.bind("<Enter>", on_enter)
        login_button.bind("<Leave>", on_leave)
        
        # Message d'état
        self.status_label = tk.Label(center_frame, text="", 
                                     font=('Arial', 9), 
                                     bg='white', fg='red')
        self.status_label.pack(pady=5)
        
        # ══════════════════════════════════════════════════════════════════════════
        # BANDE NOIRE EN BAS
        # ══════════════════════════════════════════════════════════════════════════
        bottom_frame = tk.Frame(main_container, bg='#000000', height=80)
        bottom_frame.pack(side='bottom', fill='x')
        bottom_frame.pack_propagate(False)
        
        contact_info = tk.Frame(bottom_frame, bg='#000000')
        contact_info.pack(expand=True)
        
        tk.Label(contact_info, text="13 Rue Ampère - Ducos", 
                font=('Arial', 9), fg='white', bg='#000000').pack()
        tk.Label(contact_info, text="Tél: 27 47 22", 
                font=('Arial', 9), fg='white', bg='#000000').pack()
        tk.Label(contact_info, text="Du lundi au vendredi : 7h-17h | Samedi : 7h30-16h", 
                font=('Arial', 8), fg='#fff001', bg='#000000').pack(pady=(5, 0))
    
    def _setup_logo(self, parent):
        """Configure le logo ou l'icône par défaut."""
        if PIL_AVAILABLE:
            try:
                logo_path = "assets/logo.png"
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    img = img.resize((80, 80), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    logo_label = tk.Label(parent, image=photo, bg='white')
                    logo_label.image = photo
                    logo_label.pack(pady=(20, 10))
                else:
                    self._show_default_logo(parent)
            except:
                self._show_default_logo(parent)
        else:
            self._show_default_logo(parent)
    
    def _show_default_logo(self, parent):
        """Affiche le logo par défaut (texte)."""
        tk.Label(parent, text="[AVOIRS]", 
                font=('Arial', 20, 'bold'), bg='white', fg='#000000').pack(pady=(20, 10))
    
    def center_window(self):
        """Centre la fenêtre sur l'écran."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    # ══════════════════════════════════════════════════════════════════════════════
    # AUTHENTIFICATION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def login(self):
        """Gère la connexion de l'utilisateur."""
        username = self.username_var.get().strip()
        password = self.password_entry.get()

        if not username:
            self.show_error("Veuillez sélectionner un utilisateur")
            return

        if not password:
            self.show_error("Veuillez saisir votre mot de passe")
            return
        
        # Afficher un message de connexion en cours
        self.status_label.config(text="Connexion en cours...", fg='#000000')
        self.root.update()
        
        user = self.user_manager.authenticate(username, password)
        if user:
            self.db.add_log(username, "LOGIN", "Connexion réussie")
            self.status_label.config(text="Connexion réussie!", fg='green')
            self.root.update()
            
            # Attendre un peu avant de fermer
            self.root.after(500, lambda: self.login_success(user))
        else:
            self.show_error("Identifiants incorrects")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
    
    def login_success(self, user):
        """Appelé après une connexion réussie."""
        self.on_success(user)
    
    def show_error(self, message):
        """Affiche un message d'erreur temporaire."""
        self.status_label.config(text=f"ERREUR: {message}", fg='red')
        # Effacer le message après 3 secondes
        self.root.after(3000, lambda: self.status_label.config(text=""))
    
    # ══════════════════════════════════════════════════════════════════════════════
    # NETTOYAGE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def cleanup(self):
        """Nettoyage avant fermeture."""
        if hasattr(self, 'db'):
            self.db.close()