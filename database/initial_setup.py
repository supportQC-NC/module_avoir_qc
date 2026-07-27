

# -*- coding: utf-8 -*-
"""
Configuration initiale de la base de données
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module gère le dialogue de première configuration:
- Email et mot de passe administrateur
- Emplacement de la base de données
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
from pathlib import Path

from config.paths import set_base_path, save_admin_config, mark_as_initialized


def show_initial_config_dialog():
    """
    Affiche le dialogue de configuration initiale.
    
    Ce dialogue apparaît au premier lancement pour configurer:
    - L'email de l'administrateur
    - Le mot de passe administrateur (min. 8 caractères)
    - L'emplacement de la base de données
    
    Returns:
        dict: Dictionnaire avec les clés:
            - configured (bool): True si configuration réussie
            - email (str): Email admin (si configuré)
            - password_hash (str): Hash SHA256 du mot de passe (si configuré)
            - db_path (str): Chemin de la BDD (si configuré)
    """
    result = {'configured': False}
    
    def on_validate():
        """Valide et sauvegarde la configuration."""
        email = email_entry.get().strip()
        password = password_entry.get().strip()
        confirm = confirm_entry.get().strip()
        db_path = path_entry.get().strip()
        
        # Validations
        if not email or '@' not in email:
            messagebox.showerror("Erreur", "Veuillez saisir une adresse email valide")
            return
        
        if len(password) < 8:
            messagebox.showerror("Erreur", "Le mot de passe doit contenir au moins 8 caractères")
            return
        
        if password != confirm:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas")
            return
        
        if not db_path:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier pour la base de données")
            return
        
        # Sauvegarder la configuration
        path = Path(db_path)
        path.mkdir(exist_ok=True, parents=True)
        set_base_path(path)
        
        hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
        save_admin_config(email, hashed_pwd)
        mark_as_initialized()
        
        result['configured'] = True
        result['email'] = email
        result['password_hash'] = hashed_pwd
        result['db_path'] = db_path
        
        dialog.destroy()
    
    def browse_folder():
        """Ouvre le sélecteur de dossier."""
        folder = filedialog.askdirectory(title="Sélectionner le dossier pour la base de données")
        if folder:
            path_entry.delete(0, tk.END)
            path_entry.insert(0, folder)
    
    def on_close():
        """Gère la fermeture de la fenêtre."""
        result['configured'] = False
        dialog.destroy()
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CRÉATION DE LA FENÊTRE
    # ══════════════════════════════════════════════════════════════════════════════
    dialog = tk.Tk()
    dialog.title("Configuration initiale - Module Avoirs")
    dialog.geometry("500x550")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    
    # Centrer la fenêtre
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 250
    y = (dialog.winfo_screenheight() // 2) - 275
    dialog.geometry(f'+{x}+{y}')
    
    # ══════════════════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════════════════
    header = tk.Frame(dialog, bg='#fff001', height=60)
    header.pack(fill='x')
    header.pack_propagate(False)
    
    tk.Label(
        header,
        text="Configuration initiale",
        font=('Segoe UI', 14, 'bold'),
        bg='#fff001',
        fg='#000000'
    ).pack(pady=15)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CONTENU
    # ══════════════════════════════════════════════════════════════════════════════
    content = tk.Frame(dialog, padx=30, pady=20)
    content.pack(fill='both', expand=True)
    
    tk.Label(
        content,
        text="Bienvenue ! Configurez votre compte administrateur et\nl'emplacement de la base de données.",
        font=('Segoe UI', 10),
        justify='center'
    ).pack(pady=(0, 20))
    
    # Email admin
    tk.Label(content, text="Email administrateur:", font=('Segoe UI', 10)).pack(anchor='w')
    email_entry = tk.Entry(content, font=('Segoe UI', 11), width=40)
    email_entry.pack(fill='x', pady=(5, 15))
    email_entry.insert(0, "support@quincaillerie.nc")
    
    # Mot de passe
    tk.Label(content, text="Mot de passe (min. 8 caractères):", font=('Segoe UI', 10)).pack(anchor='w')
    password_entry = tk.Entry(content, font=('Segoe UI', 11), width=40, show='•')
    password_entry.pack(fill='x', pady=(5, 15))
    password_entry.insert(0, "Stoyann19031985")
    
    # Confirmation mot de passe
    tk.Label(content, text="Confirmer le mot de passe:", font=('Segoe UI', 10)).pack(anchor='w')
    confirm_entry = tk.Entry(content, font=('Segoe UI', 11), width=40, show='•')
    confirm_entry.pack(fill='x', pady=(5, 15))
    confirm_entry.insert(0, "Stoyann19031985")
    
    # Chemin BDD
    tk.Label(content, text="Dossier de la base de données:", font=('Segoe UI', 10)).pack(anchor='w')
    path_frame = tk.Frame(content)
    path_frame.pack(fill='x', pady=(5, 15))
    
    path_entry = tk.Entry(path_frame, font=('Segoe UI', 11))
    path_entry.pack(side='left', fill='x', expand=True)
    path_entry.insert(0, r"\\serveur\Bases\db_module_avoir_qc")
    
    tk.Button(
        path_frame,
        text="...",
        command=browse_folder,
        font=('Segoe UI', 10),
        width=3
    ).pack(side='right', padx=(5, 0))
    
    # Séparateur
    ttk.Separator(content, orient='horizontal').pack(fill='x', pady=15)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # BOUTON VALIDER
    # ══════════════════════════════════════════════════════════════════════════════
    button_frame = tk.Frame(content)
    button_frame.pack(fill='x', pady=10)
    
    tk.Button(
        button_frame,
        text="Valider et démarrer",
        command=on_validate,
        font=('Segoe UI', 12, 'bold'),
        bg='#4CAF50',
        fg='white',
        bd=0,
        padx=30,
        pady=12,
        cursor='hand2'
    ).pack(expand=True)
    
    dialog.mainloop()
    
    return result