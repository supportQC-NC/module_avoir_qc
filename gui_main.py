"""
Interface principale moderne et amelioree
Module de Gestion des Avoirs Clients - STOYANN
Version: 3.1 - Avec gestion avoirs partiels
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import hashlib
import os
from datetime import datetime, timedelta
import csv
import re
import threading
import time
from database.connection import Database
from models.user_manager import UserManager
from models.avoir_manager import AvoirManager
from services.email_service import EmailService
from config.settings import *
from config.paths import get_base_path, get_file_path, is_dev_test_mode, get_dev_test_base

# Pour compatibilité avec l'ancien code
BASE_PATH = get_base_path()

from services.pdf_creator import PDFCreator

# Import pour le DatePicker
try:
    from tkcalendar import DateEntry
    DATEPICKER_AVAILABLE = True
except ImportError:
    DATEPICKER_AVAILABLE = False
    print(" Module tkcalendar non installe. Installation: pip install tkcalendar")

def format_montant_simple(montant):
    """Formate un montant en XPF (espace comme separateur de milliers)"""
    try:
        return f"{float(montant or 0):,.0f} XPF".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 XPF"


class ModernButton(tk.Button):
    """Bouton personnalise avec effets modernes"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.default_bg = kwargs.get('bg', '#000000')
        self.configure(
            relief='flat',
            bd=0,
            cursor='hand2',
            font=kwargs.get('font', ('Segoe UI', 10, 'bold'))
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, e):
        self['bg'] = '#333333' if self.default_bg == '#000000' else self.default_bg
    
    def on_leave(self, e):
        self['bg'] = self.default_bg

class UtilisationDialog:
    """Dialogue simplifie pour l'utilisation d'un avoir - saisie montant facture uniquement"""
    def __init__(self, parent, avoir_numero, avoir_montant_restant, is_expired=False,
                 responsables=None):
        self.result = None
        self.is_expired = is_expired
        # Liste des responsables (usernames) autorises a valider un forcage.
        # Alimente la liste deroulante affichee lorsque l'avoir est expire.
        self.responsables = responsables or []
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Utilisation de l'avoir {avoir_numero}")
        self.dialog.geometry("500x450" if not is_expired else "500x560")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenetre
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 225
        self.dialog.geometry(f'+{x}+{y}')
        
        # Variables
        self.montant_avoir = avoir_montant_restant
        self.avoir_numero = avoir_numero
        
        # Interface
        self.create_interface()

        # Forcer le focus clavier sur la fenetre + le premier champ.
        # Sur certains postes, sans cela, le focus clavier ne passe pas a la
        # fenetre modale et l'on ne peut pas taper dans les champs (alors que
        # ca fonctionne sur les autres postes). On le force, puis on retente
        # juste apres l'affichage complet de la fenetre.
        self._forcer_focus_saisie()

    def _forcer_focus_saisie(self):
        """Donne le focus clavier a la fenetre et au premier champ de saisie."""
        def _appliquer():
            try:
                if not self.dialog.winfo_exists():
                    return
                self.dialog.lift()
                self.dialog.focus_force()
                if hasattr(self, 'facture_entry') and self.facture_entry.winfo_exists():
                    self.facture_entry.focus_set()
            except Exception:
                pass
        _appliquer()
        # Nouvelle tentative apres le mapping complet de la fenetre
        try:
            self.dialog.after(150, _appliquer)
            self.dialog.after(400, _appliquer)
        except Exception:
            pass
    
    def create_interface(self):
        """Cree l'interface du dialogue simplifie"""
        # Header
        header_frame = tk.Frame(self.dialog, bg='#fff001', height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="Utilisation de l'avoir",
            font=('Segoe UI', 14, 'bold'),
            bg='#fff001',
            fg='#000000'
        ).pack(pady=15)
        
        # Contenu principal
        main_frame = tk.Frame(self.dialog, bg='white', padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Montant de l'avoir
        tk.Label(
            main_frame,
            text=f"Montant de l'avoir: {format_montant(self.montant_avoir)} XPF",
            font=('Segoe UI', 14, 'bold'),
            bg='white',
            fg='#4CAF50'
        ).pack(pady=(0, 25))
        
        # Numero de facture
        tk.Label(
            main_frame,
            text="Numero de facture: *",
            font=('Segoe UI', 10),
            bg='white',
            fg='#f44336'
        ).pack(anchor='w')
        
        self.facture_entry = tk.Entry(
            main_frame,
            font=('Segoe UI', 11),
            bd=1,
            relief='solid'
        )
        self.facture_entry.pack(fill='x', pady=(5, 20))
        
        # Montant de la facture
        tk.Label(
            main_frame,
            text="Montant de la facture (XPF): *",
            font=('Segoe UI', 10),
            bg='white',
            fg='#f44336'
        ).pack(anchor='w')
        
        self.montant_entry = tk.Entry(
            main_frame,
            font=('Segoe UI', 11),
            bd=1,
            relief='solid'
        )
        self.montant_entry.pack(fill='x', pady=5)
        
        # Message d'info
        info_frame = tk.Frame(main_frame, bg='#e3f2fd', relief='flat')
        info_frame.pack(fill='x', pady=20)
        
        tk.Label(
            info_frame,
            text="Info: Si le montant de la facture est inferieur a l'avoir, un nouveau bon d'avoir sera automatiquement cree pour le solde.",
            font=('Segoe UI', 9),
            bg='#e3f2fd',
            fg='#1976d2',
            wraplength=400,
            justify='left'
        ).pack(padx=10, pady=10)
        
        # Section forcage : visible uniquement si l'avoir est expire.
        # Le nom du responsable ayant autorise le forcage est desormais CHOISI
        # dans une LISTE DEROULANTE (responsables + comptabilite actifs) et non
        # plus saisi librement au clavier.
        self.forcage_var = None
        self.forcage_combo = None
        if self.is_expired:
            forcage_frame = tk.Frame(main_frame, bg='#ffebee', relief='solid', bd=1)
            forcage_frame.pack(fill='x', pady=(0, 10))
            tk.Label(
                forcage_frame,
                text="AVOIR EXPIRE",
                font=('Segoe UI', 10, 'bold'),
                bg='#ffebee',
                fg='#c62828'
            ).pack(anchor='w', padx=10, pady=(10, 0))
            tk.Label(
                forcage_frame,
                text="Pour forcer l'utilisation, selectionnez le responsable ayant autorise : *",
                font=('Segoe UI', 9),
                bg='#ffebee',
                fg='#c62828',
                wraplength=420,
                justify='left'
            ).pack(anchor='w', padx=10)
            self.forcage_var = tk.StringVar(self.dialog, value="")
            self.forcage_combo = ttk.Combobox(
                forcage_frame,
                textvariable=self.forcage_var,
                values=self.responsables,
                state='readonly',
                font=('Segoe UI', 11)
            )
            self.forcage_combo.pack(fill='x', padx=10, pady=(5, 10))
            # Aide si aucun responsable disponible
            if not self.responsables:
                tk.Label(
                    forcage_frame,
                    text="(Aucun responsable actif disponible : creez un compte "
                         "'responsable' ou 'comptabilite' pour autoriser un forcage.)",
                    font=('Segoe UI', 8, 'italic'),
                    bg='#ffebee',
                    fg='#c62828',
                    wraplength=420,
                    justify='left'
                ).pack(anchor='w', padx=10, pady=(0, 10))
        
        # Boutons
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        tk.Button(
            button_frame,
            text="Forcer l'utilisation" if self.is_expired else "Valider",
            command=self.validate,
            font=('Segoe UI', 10, 'bold'), 
            bg='#ff9800' if self.is_expired else '#4CAF50',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        ).pack(side='right', padx=(10, 0))
        
        tk.Button(
            button_frame,
            text="Annuler",
            command=self.cancel,
            font=('Segoe UI', 10, 'bold'),
            bg='#f44336',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        ).pack(side='right')
        
        # Focus
        self.facture_entry.focus()
    
    def validate(self):
        """Valide les donnees saisies"""
        # Verifier le numero de facture
        numero_facture = self.facture_entry.get().strip()
        if not numero_facture:
            messagebox.showerror("Erreur", "Le numero de facture est obligatoire")
            self.facture_entry.focus()
            return
        
        # Recuperer le montant de la facture
        try:
            montant_str = self.montant_entry.get().strip()
            if not montant_str:
                messagebox.showerror("Erreur", "Le montant de la facture est obligatoire")
                self.montant_entry.focus()
                return
            
            montant_facture = float(montant_str.replace(' ', '').replace(',', '.'))
            
            if montant_facture <= 0:
                messagebox.showerror("Erreur", "Le montant doit etre positif")
                return
                
        except ValueError:
            messagebox.showerror("Erreur", "Montant invalide")
            return
        
        # Si l'avoir est expire, le responsable autorisant le forcage doit etre
        # SELECTIONNE dans la liste deroulante.
        forcage_autorise_par = None
        if self.is_expired:
            forcage_autorise_par = self.forcage_var.get().strip() if self.forcage_var else ""
            if not forcage_autorise_par:
                messagebox.showerror(
                    "Forcage refuse",
                    "L'avoir est expire.\nVous devez selectionner le responsable "
                    "ayant autorise le forcage pour continuer."
                )
                if self.forcage_combo:
                    self.forcage_combo.focus()
                return
        
        # Retourner le resultat
        self.result = {
            'montant_facture': montant_facture,
            'numero_facture': numero_facture,
            'force': bool(self.is_expired),
            'forcage_autorise_par': forcage_autorise_par
        }
        self.dialog.destroy()
    
    def cancel(self):
        """Annule l'operation"""
        self.result = None
        self.dialog.destroy()

class MultiAvoirDialog:
    """
    Dialogue d'utilisation de PLUSIEURS avoirs cumules sur une meme facture.

    Le vendeur scanne / saisit plusieurs bons d'avoir (les clients peuvent etre
    DIFFERENTS), leurs montants restants sont cumules, puis imputes sur une
    seule et meme facture.

    Regles appliquees :
      - Les avoirs sont consommes dans l'ordre de la liste.
      - Si le total des avoirs > montant de la facture, le dernier avoir
        partiellement consomme genere automatiquement un avoir residu (enfant).
      - Si le total des avoirs < montant de la facture, tous les avoirs sont
        consommes et le client regle la difference.
      - Un avoir expire ne peut etre utilise que par forcage (selection du
        responsable ayant autorise, comme pour l'utilisation simple).
      - Les avoirs utilises / bloques / annules / supprimes sont refuses.
    """

    def __init__(self, parent, avoir_manager, responsables=None):
        self.result = None
        self.avoir_manager = avoir_manager
        # Responsables autorises a valider un forcage (avoirs expires)
        self.responsables = responsables or []
        # Liste des avoirs retenus : dict(numero, client, montant_restant, expire)
        self.avoirs = []
        # Le cadre de forcage n'est affiche que si un avoir expire est ajoute
        self.forcage_affiche = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Utilisation de plusieurs avoirs")
        self.dialog.geometry("780x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Centrer la fenetre
        self.dialog.update_idletasks()
        x = max(0, (self.dialog.winfo_screenwidth() // 2) - 390)
        y = max(0, (self.dialog.winfo_screenheight() // 2) - 350)
        self.dialog.geometry(f'+{x}+{y}')

        self.create_interface()

        # Meme correctif de focus que pour l'utilisation simple : sur certains
        # postes le focus clavier ne passe pas automatiquement a la modale.
        self._forcer_focus_saisie()

    def _forcer_focus_saisie(self):
        """Donne le focus clavier a la fenetre et au champ de scan."""
        def _appliquer():
            try:
                if not self.dialog.winfo_exists():
                    return
                self.dialog.lift()
                self.dialog.focus_force()
                if hasattr(self, 'scan_entry') and self.scan_entry.winfo_exists():
                    self.scan_entry.focus_set()
            except Exception:
                pass
        _appliquer()
        try:
            self.dialog.after(150, _appliquer)
            self.dialog.after(400, _appliquer)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------
    def create_interface(self):
        """Construit l'interface du dialogue multi-avoirs"""
        # Header
        header_frame = tk.Frame(self.dialog, bg='#fff001', height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Utilisation de plusieurs avoirs (cumul)",
            font=('Segoe UI', 14, 'bold'),
            bg='#fff001',
            fg='#000000'
        ).pack(pady=15)

        main_frame = tk.Frame(self.dialog, bg='white', padx=25, pady=15)
        main_frame.pack(fill='both', expand=True)

        # ---------------- Zone de scan / ajout ----------------
        scan_frame = tk.Frame(main_frame, bg='white')
        scan_frame.pack(fill='x')

        tk.Label(
            scan_frame,
            text="Scanner ou saisir un numero d'avoir, puis 'Ajouter' :",
            font=('Segoe UI', 10),
            bg='white',
            fg='#212121'
        ).pack(anchor='w')

        scan_row = tk.Frame(scan_frame, bg='white')
        scan_row.pack(fill='x', pady=(5, 10))

        self.scan_entry = tk.Entry(
            scan_row,
            font=('Segoe UI', 12),
            bd=1,
            relief='solid'
        )
        self.scan_entry.pack(side='left', fill='x', expand=True, ipady=4)
        self.scan_entry.bind('<Return>', lambda e: self.add_avoir())

        tk.Button(
            scan_row,
            text="+ Ajouter",
            command=self.add_avoir,
            font=('Segoe UI', 10, 'bold'),
            bg='#2196F3',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=15,
            pady=5
        ).pack(side='left', padx=(10, 0))

        # ---------------- Liste des avoirs ----------------
        liste_frame = tk.Frame(main_frame, bg='white')
        liste_frame.pack(fill='both', expand=True)

        columns = ('numero', 'client', 'montant', 'etat')
        self.tree = ttk.Treeview(
            liste_frame,
            columns=columns,
            show='headings',
            height=7
        )
        self.tree.heading('numero', text="N Avoir")
        self.tree.heading('client', text="Client")
        self.tree.heading('montant', text="Montant restant")
        self.tree.heading('etat', text="Etat")
        self.tree.column('numero', width=110, anchor='center')
        self.tree.column('client', width=280, anchor='w')
        self.tree.column('montant', width=140, anchor='e')
        self.tree.column('etat', width=150, anchor='center')

        scroll = ttk.Scrollbar(liste_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        # Les avoirs expires (forcage necessaire) apparaissent en rouge
        self.tree.tag_configure('expire', foreground='#c62828')

        actions_frame = tk.Frame(main_frame, bg='white')
        actions_frame.pack(fill='x', pady=(8, 0))

        tk.Button(
            actions_frame,
            text="Retirer de la liste",
            command=self.remove_avoir,
            font=('Segoe UI', 9, 'bold'),
            bg='#9e9e9e',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=12,
            pady=4
        ).pack(side='left')

        tk.Button(
            actions_frame,
            text="Vider la liste",
            command=self.clear_avoirs,
            font=('Segoe UI', 9, 'bold'),
            bg='#9e9e9e',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=12,
            pady=4
        ).pack(side='left', padx=(8, 0))

        self.total_label = tk.Label(
            actions_frame,
            text="Total des avoirs : 0 XPF  (0 avoir)",
            font=('Segoe UI', 12, 'bold'),
            bg='white',
            fg='#4CAF50'
        )
        self.total_label.pack(side='right')

        # ---------------- Facture ----------------
        facture_frame = tk.Frame(main_frame, bg='white')
        facture_frame.pack(fill='x', pady=(12, 0))

        col_gauche = tk.Frame(facture_frame, bg='white')
        col_gauche.pack(side='left', fill='x', expand=True, padx=(0, 10))

        tk.Label(
            col_gauche,
            text="Numero de facture : *",
            font=('Segoe UI', 10),
            bg='white',
            fg='#f44336'
        ).pack(anchor='w')

        self.facture_entry = tk.Entry(
            col_gauche,
            font=('Segoe UI', 11),
            bd=1,
            relief='solid'
        )
        self.facture_entry.pack(fill='x', pady=(3, 0))

        col_droite = tk.Frame(facture_frame, bg='white')
        col_droite.pack(side='left', fill='x', expand=True)

        tk.Label(
            col_droite,
            text="Montant de la facture (XPF) : *",
            font=('Segoe UI', 10),
            bg='white',
            fg='#f44336'
        ).pack(anchor='w')

        self.montant_entry = tk.Entry(
            col_droite,
            font=('Segoe UI', 11),
            bd=1,
            relief='solid'
        )
        self.montant_entry.pack(fill='x', pady=(3, 0))
        self.montant_entry.bind('<KeyRelease>', lambda e: self.update_recap())

        # ---------------- Forcage (avoirs expires) ----------------
        # Cadre cree une seule fois, affiche uniquement si la liste contient
        # au moins un avoir expire.
        self.forcage_frame = tk.Frame(main_frame, bg='#ffebee', relief='solid', bd=1)
        tk.Label(
            self.forcage_frame,
            text="Un ou plusieurs avoirs de la liste sont EXPIRES.\n"
                 "Selectionnez le responsable ayant autorise le forcage : *",
            font=('Segoe UI', 9, 'bold'),
            bg='#ffebee',
            fg='#c62828',
            justify='left'
        ).pack(anchor='w', padx=10, pady=(8, 0))

        self.forcage_var = tk.StringVar(self.dialog, value="")
        self.forcage_combo = ttk.Combobox(
            self.forcage_frame,
            textvariable=self.forcage_var,
            values=self.responsables,
            state='readonly',
            font=('Segoe UI', 11)
        )
        self.forcage_combo.pack(fill='x', padx=10, pady=(5, 8))

        # ---------------- Recapitulatif ----------------
        self.recap_frame = tk.Frame(main_frame, bg='#e3f2fd')
        self.recap_frame.pack(fill='x', pady=(12, 0))

        self.recap_label = tk.Label(
            self.recap_frame,
            text="Ajoutez les avoirs a cumuler puis saisissez le montant de la facture.",
            font=('Segoe UI', 10),
            bg='#e3f2fd',
            fg='#1976d2',
            wraplength=680,
            justify='left'
        )
        self.recap_label.pack(padx=10, pady=8, anchor='w')

        # ---------------- Boutons ----------------
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(side='bottom', fill='x', pady=(15, 0))

        tk.Button(
            button_frame,
            text="Valider l'utilisation",
            command=self.validate,
            font=('Segoe UI', 10, 'bold'),
            bg='#4CAF50',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        ).pack(side='right', padx=(10, 0))

        tk.Button(
            button_frame,
            text="Annuler",
            command=self.cancel,
            font=('Segoe UI', 10, 'bold'),
            bg='#f44336',
            fg='white',
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        ).pack(side='right')

        self.scan_entry.focus()

    # ------------------------------------------------------------------
    # GESTION DE LA LISTE
    # ------------------------------------------------------------------
    def add_avoir(self):
        """Controle puis ajoute un avoir a la liste cumulee"""
        saisie = self.scan_entry.get().strip()
        if not saisie:
            return

        # Meme reconnaissance de code-barres que pour l'utilisation simple
        numero_avoir = saisie
        if '/' not in saisie and len(saisie) == 7:
            numero_avoir = f"{saisie[:2]}/{saisie[2:]}"

        details = self.avoir_manager.get_avoir_details(numero_avoir)
        if not details:
            messagebox.showerror(
                " AVOIR INTROUVABLE",
                f"L'avoir {numero_avoir} n'existe pas!\n\n"
                f"Verifiez le numero saisi ou le code-barres scanne.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        avoir = details if not isinstance(details, dict) else details['avoir']
        numero_reel = avoir[1]

        # Doublon ?
        if any(a['numero'] == numero_reel for a in self.avoirs):
            messagebox.showwarning(
                "Avoir deja dans la liste",
                f"L'avoir {numero_reel} est deja present dans la liste.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        statut = avoir[12]

        if statut == AVOIR_STATUS['UTILISE']:
            messagebox.showerror(
                " AVOIR DEJA UTILISE",
                f"ERREUR : L'avoir {numero_reel} a deja ete utilise!\n\n"
                f"Cet avoir ne peut pas etre valide une seconde fois.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        if statut == AVOIR_STATUS['BLOQUE']:
            messagebox.showwarning(
                " AVOIR BLOQUE",
                f"L'avoir {numero_reel} est BLOQUE.\n\n"
                f"Demandez au client de passer a la COMPTABILITE.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        if statut == AVOIR_STATUS['SUPPRIME']:
            motif = avoir[25] if (len(avoir) > 25 and avoir[25]) else ''
            message = (f"L'avoir {numero_reel} a ete SUPPRIME.\n\n"
                       f"Il ne peut plus etre utilise.")
            if motif:
                message += f"\n\nMotif : {motif}"
            messagebox.showwarning(" AVOIR SUPPRIME", message, parent=self.dialog)
            self._reset_scan()
            return

        if statut == AVOIR_STATUS['ANNULE']:
            motif = avoir[25] if (len(avoir) > 25 and avoir[25]) else ''
            annule_par = avoir[26] if (len(avoir) > 26 and avoir[26]) else ''
            message = (f"L'avoir {numero_reel} a ete ANNULE.\n\n"
                       f"Il ne peut plus etre utilise.")
            if annule_par:
                message += f"\n\nAnnule par : {annule_par}"
            if motif:
                message += f"\nMotif : {motif}"
            messagebox.showwarning(" AVOIR ANNULE", message, parent=self.dialog)
            self._reset_scan()
            return

        # Montant encore disponible sur l'avoir
        montant_restant = avoir[20] if avoir[20] is not None else avoir[8]
        try:
            montant_restant = float(montant_restant or 0)
        except (TypeError, ValueError):
            montant_restant = 0

        if montant_restant <= 0:
            messagebox.showwarning(
                "Solde nul",
                f"L'avoir {numero_reel} n'a plus de solde disponible.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        # Expiration : meme regle metier que l'utilisation simple (90 jours
        # apres la date de creation). Necessite un forcage par un responsable.
        expire = self.avoir_manager.is_avoir_expire(avoir)
        if expire and not self.responsables:
            messagebox.showerror(
                " AVOIR EXPIRE",
                f"L'avoir {numero_reel} est expire et aucun responsable actif "
                f"n'est disponible pour autoriser un forcage.",
                parent=self.dialog
            )
            self._reset_scan()
            return

        self.avoirs.append({
            'numero': numero_reel,
            'numero_client': avoir[2] or '',
            'client': avoir[3] or '',
            'montant_restant': montant_restant,
            'expire': bool(expire)
        })

        self._reset_scan()
        self.refresh_liste()

    def remove_avoir(self):
        """Retire le ou les avoirs selectionnes de la liste"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Aucune selection",
                "Selectionnez d'abord un avoir dans la liste.",
                parent=self.dialog
            )
            return
        numeros = {self.tree.item(item, 'values')[0] for item in selection}
        self.avoirs = [a for a in self.avoirs if a['numero'] not in numeros]
        self.refresh_liste()

    def clear_avoirs(self):
        """Vide completement la liste"""
        self.avoirs = []
        self.refresh_liste()

    def _reset_scan(self):
        """Vide le champ de scan et lui redonne le focus"""
        try:
            self.scan_entry.delete(0, tk.END)
            self.scan_entry.focus_set()
        except Exception:
            pass

    def refresh_liste(self):
        """Redessine la liste, le total et le recapitulatif"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for avoir in self.avoirs:
            libelle_client = avoir['client']
            if avoir['numero_client']:
                libelle_client = f"{avoir['numero_client']} - {libelle_client}"
            self.tree.insert(
                '', 'end',
                values=(
                    avoir['numero'],
                    libelle_client,
                    format_montant_simple(avoir['montant_restant']),
                    "EXPIRE (forcage)" if avoir['expire'] else "Utilisable"
                ),
                tags=('expire',) if avoir['expire'] else ()
            )

        # Afficher / masquer le cadre de forcage selon la presence d'un expire.
        # On suit l'etat avec un indicateur (et non winfo_ismapped, qui reste
        # a 0 tant que Tk n'a pas traite les taches d'affichage en attente).
        doit_forcer = any(a['expire'] for a in self.avoirs)
        if doit_forcer and not self.forcage_affiche:
            self.forcage_frame.pack(fill='x', pady=(10, 0), before=self.recap_frame)
            self.forcage_affiche = True
        elif not doit_forcer and self.forcage_affiche:
            self.forcage_frame.pack_forget()
            self.forcage_affiche = False
        if not doit_forcer:
            self.forcage_var.set("")

        self.update_recap()

    def total_avoirs(self):
        """Somme des montants restants des avoirs de la liste"""
        return sum(a['montant_restant'] for a in self.avoirs)

    def _lire_montant_facture(self):
        """Retourne le montant de la facture saisi, ou None si invalide"""
        montant_str = self.montant_entry.get().strip()
        if not montant_str:
            return None
        try:
            return float(montant_str.replace(' ', '').replace(',', '.'))
        except ValueError:
            return None

    def update_recap(self):
        """Met a jour le total cumule et le recapitulatif de repartition"""
        total = self.total_avoirs()
        nb = len(self.avoirs)
        self.total_label.config(
            text=f"Total des avoirs : {format_montant_simple(total)}"
                 f"  ({nb} avoir{'s' if nb > 1 else ''})"
        )

        montant_facture = self._lire_montant_facture()

        if nb == 0:
            self.recap_frame.config(bg='#e3f2fd')
            self.recap_label.config(
                bg='#e3f2fd', fg='#1976d2',
                text="Ajoutez les avoirs a cumuler puis saisissez le montant de la facture."
            )
            return

        if montant_facture is None or montant_facture <= 0:
            self.recap_frame.config(bg='#e3f2fd')
            self.recap_label.config(
                bg='#e3f2fd', fg='#1976d2',
                text="Saisissez le montant de la facture pour voir la repartition des avoirs."
            )
            return

        impute = min(total, montant_facture)
        lignes = [
            f"Facture : {format_montant_simple(montant_facture)}"
            f"   |   Avoirs imputes : {format_montant_simple(impute)}"
        ]

        if montant_facture > total:
            lignes.append(
                "RESTANT A PAYER PAR LE CLIENT : "
                f"{format_montant_simple(montant_facture - total)}"
            )
            bg, fg = '#fff3e0', '#e65100'
        elif montant_facture < total:
            lignes.append(
                f"Un avoir residu de {format_montant_simple(total - montant_facture)} "
                "sera cree automatiquement (a remettre au client)."
            )
            bg, fg = '#e8f5e9', '#2e7d32'
        else:
            lignes.append("Les avoirs couvrent exactement la facture. Rien a payer.")
            bg, fg = '#e8f5e9', '#2e7d32'

        # Information : avoirs de clients differents (autorise)
        clients = {(a['numero_client'] or a['client']) for a in self.avoirs}
        if len(clients) > 1:
            lignes.append("Note : les avoirs de la liste appartiennent a des CLIENTS DIFFERENTS.")

        self.recap_frame.config(bg=bg)
        self.recap_label.config(bg=bg, fg=fg, text="\n".join(lignes))

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------
    def validate(self):
        """Controle la saisie et prepare le resultat"""
        if not self.avoirs:
            messagebox.showerror(
                "Erreur",
                "Ajoutez au moins un avoir a la liste.",
                parent=self.dialog
            )
            self.scan_entry.focus()
            return

        numero_facture = self.facture_entry.get().strip()
        if not numero_facture:
            messagebox.showerror(
                "Erreur",
                "Le numero de facture est obligatoire",
                parent=self.dialog
            )
            self.facture_entry.focus()
            return

        montant_facture = self._lire_montant_facture()
        if montant_facture is None:
            messagebox.showerror("Erreur", "Montant invalide", parent=self.dialog)
            self.montant_entry.focus()
            return
        if montant_facture <= 0:
            messagebox.showerror(
                "Erreur", "Le montant doit etre positif", parent=self.dialog
            )
            self.montant_entry.focus()
            return

        # Forcage obligatoire si la liste contient au moins un avoir expire
        forcage_autorise_par = None
        if any(a['expire'] for a in self.avoirs):
            forcage_autorise_par = self.forcage_var.get().strip()
            if not forcage_autorise_par:
                messagebox.showerror(
                    "Forcage refuse",
                    "La liste contient au moins un avoir expire.\n"
                    "Vous devez selectionner le responsable ayant autorise "
                    "le forcage pour continuer.",
                    parent=self.dialog
                )
                self.forcage_combo.focus()
                return

        # Recapitulatif de confirmation avec la repartition avoir par avoir
        reste = montant_facture
        lignes = []
        avoirs_non_utilises = []
        for avoir in self.avoirs:
            if reste <= 0:
                avoirs_non_utilises.append(avoir['numero'])
                continue
            impute = min(avoir['montant_restant'], reste)
            ligne = f"  - {avoir['numero']} : {format_montant_simple(impute)}"
            if impute < avoir['montant_restant']:
                solde = avoir['montant_restant'] - impute
                ligne += f"  (residu de {format_montant_simple(solde)})"
            if avoir['expire']:
                ligne += "  [FORCAGE]"
            lignes.append(ligne)
            reste -= impute

        message = (
            f"Facture {numero_facture} : {format_montant_simple(montant_facture)}\n\n"
            "Repartition sur les avoirs :\n" + "\n".join(lignes)
        )
        if reste > 0:
            message += f"\n\nRESTANT A PAYER : {format_montant_simple(reste)}"
        if avoirs_non_utilises:
            message += ("\n\nAvoirs NON utilises (facture deja couverte) : "
                        + ", ".join(avoirs_non_utilises))
        message += "\n\nConfirmer l'utilisation de ces avoirs ?"

        if not messagebox.askyesno("Confirmation", message, parent=self.dialog):
            return

        self.result = {
            'avoirs': list(self.avoirs),
            'montant_facture': montant_facture,
            'numero_facture': numero_facture,
            'total_avoirs': self.total_avoirs(),
            'forcage_autorise_par': forcage_autorise_par
        }
        self.dialog.destroy()

    def cancel(self):
        """Annule l'operation"""
        self.result = None
        self.dialog.destroy()


class MainWindow:
    def __init__(self, root, user):
        self.root = root
        self.user = user
        self.relogin = False  # True => deconnexion (retour au login sans fermer le programme)
        print(f" Utilisateur connecte: {user[1]}, Role: {user[4]}, Email: {user[3]}")
        
        # Configuration du theme
        self.setup_theme()
        
        # Initialisation des services
        self.db = Database()
        self.db_thread_safe = Database(thread_safe=True)
        self.email_service = EmailService(self.db_thread_safe)
        self.avoir_manager = AvoirManager(self.db, self.email_service)
        self.user_manager = UserManager(self.db)
        
        # Variables Tkinter
        self.setup_tk_vars()
        
        # Configuration de l'interface
        self.setup_ui()
        self.center_window()
        
        # Animation d'ouverture
        self.fade_in()
    
    def setup_theme(self):
        """Configure le theme de couleurs"""
        self.colors = {
            'primary': '#fff001',        # Jaune signature
            'secondary': '#000000',       # Noir
            'accent': '#ffd700',         # Or
            'success': '#4CAF50',        # Vert
            'warning': '#FF9800',        # Orange
            'error': '#f44336',          # Rouge
            'info': '#2196F3',           # Bleu
            'bg_light': "#979797",       # Fond clair
            'bg_dark': '#212121',        # Fond sombre
            'text_primary': '#212121',    # Texte principal
            'text_secondary': "#222222",  # Texte secondaire
            'white': '#ffffff',
            'sidebar_bg': '#1a1a1a',    # Fond sidebar
            'card_bg': '#ffffff',        # Fond des cartes
            'hover': '#f5f5f5'           # Hover effet
        }
        
        # Configuration du style ttk
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_ttk_styles()
    
    def configure_ttk_styles(self):
        """Configure les styles ttk personnalises"""
        # Style pour les onglets
        self.style.configure(
            'Modern.TNotebook',
            background=self.colors['bg_light'],
            borderwidth=0
        )
        self.style.configure(
            'Modern.TNotebook.Tab',
            padding=[20, 12],
            background=self.colors['white'],
            foreground=self.colors['text_primary'],
            font=('Segoe UI', 10)
        )
        self.style.map(
            'Modern.TNotebook.Tab',
            background=[('selected', self.colors['primary'])],
            foreground=[('selected', self.colors['secondary'])]
        )
        
        # Style pour les boutons
        self.style.configure(
            'Modern.TButton',
            relief='flat',
            background=self.colors['primary'],
            foreground=self.colors['secondary'],
            borderwidth=0,
            focuscolor='none',
            font=('Segoe UI', 10, 'bold')
        )
        
        # Style pour les Treeview
        self.style.configure(
            'Modern.Treeview',
            background=self.colors['white'],
            foreground=self.colors['text_primary'],
            rowheight=30,
            fieldbackground=self.colors['white'],
            borderwidth=0
        )
        self.style.configure(
            'Modern.Treeview.Heading',
            background=self.colors['primary'],
            foreground=self.colors['secondary'],
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        )
    
    def setup_tk_vars(self):
        """Initialise les variables Tkinter"""
        self.type_avoir = tk.StringVar(self.root, value="retour")
        self.send_email_var = tk.BooleanVar(self.root, value=False)
        self.filter_status = tk.StringVar(self.root, value='Tous')
        self.search_var = tk.StringVar(self.root)
    
    def setup_ui(self):
        """Configure l'interface principale moderne"""
        # Indicateur visible quand CE poste tourne sur la base de test (mode dev)
        suffixe_test = ""
        try:
            if is_dev_test_mode():
                suffixe_test = "   *** BASE DE TEST (DEV) ***"
        except Exception:
            suffixe_test = ""
        self.root.title(
            f"Module Avoirs - Quincaillerie Caledonienne | "
            f"{self.user[1]} ({self.user[4]}){suffixe_test}"
        )
        self.root.geometry("1400x800")
        self.root.configure(bg=self.colors['bg_light'])
        
        # Icone de la fenetre (si disponible)
        try:
            if os.path.exists('assets/icon.ico'):
                self.root.iconbitmap('assets/icon.ico')
        except:
            pass
        
        # Layout principal avec sidebar
        self.create_main_layout()
        
        # Menu superieur moderne
        self.create_modern_menu()
        
        # Sidebar de navigation
        self.create_sidebar()
        
        # Zone de contenu principal
        self.create_content_area()
        
        # Barre de statut
        self.create_status_bar()
        
        # Vue par defaut : le vendeur n'a acces qu'a l'utilisation d'avoir
        if self.user[4] == USER_ROLES['VENDEUR']:
            self.show_use_avoir()
        else:
            self.show_dashboard()
        
        # Raccourcis clavier
        self.setup_keyboard_shortcuts()
    
    def create_main_layout(self):
        """Cree le layout principal avec sidebar"""
        # Container principal
        self.main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        self.main_container.pack(fill='both', expand=True)
        
        # Sidebar a gauche
        self.sidebar_frame = tk.Frame(
            self.main_container,
            bg=self.colors['sidebar_bg'],
            width=250
        )
        self.sidebar_frame.pack(side='left', fill='y')
        self.sidebar_frame.pack_propagate(False)
        
        # Zone de contenu a droite
        self.content_container = tk.Frame(
            self.main_container,
            bg=self.colors['bg_light']
        )
        self.content_container.pack(side='left', fill='both', expand=True)
    
    def create_modern_menu(self):
        """Cree un menu moderne"""
        menubar = tk.Menu(self.root, bg=self.colors['white'], fg=self.colors['text_primary'])
        self.root.config(menu=menubar)
        
        # ──────────────────────────────────────────────────────────────────────
        # Cas du VENDEUR : menu reduit a l'utilisation d'un avoir uniquement
        # ──────────────────────────────────────────────────────────────────────
        if self.user[4] == USER_ROLES['VENDEUR']:
            caisse_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
            menubar.add_cascade(label=" Caisse", menu=caisse_menu)
            caisse_menu.add_command(label=" Utiliser un avoir", command=self.show_use_avoir, accelerator="Ctrl+U")
            caisse_menu.add_separator()
            caisse_menu.add_command(label=" Deconnexion", command=self.logout, accelerator="Ctrl+L")
            caisse_menu.add_command(label=" Quitter", command=self.quit_app, accelerator="Ctrl+Q")
            return
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
        menubar.add_cascade(label=" Fichier", menu=file_menu)
        file_menu.add_command(label=" Tableau de bord", command=self.show_dashboard, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label=" Rafraichir", command=self.refresh_current_view, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label=" Deconnexion", command=self.logout, accelerator="Ctrl+L")
        file_menu.add_command(label=" Quitter", command=self.quit_app, accelerator="Ctrl+Q")
        
        # Menu Gestion (selon les permissions)
        if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
            gestion_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
            menubar.add_cascade(label=" Gestion", menu=gestion_menu)
            gestion_menu.add_command(label=" Creer un avoir", command=self.show_create_avoir, accelerator="Ctrl+N")
            gestion_menu.add_command(label=" Liste des avoirs", command=self.show_avoirs_list)
            gestion_menu.add_command(label=" Envoyer des rappels", command=self.send_reminders_manually)
            
            # Anomalies : super_user et comptabilite
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['COMPTABILITE']]:
                gestion_menu.add_command(label=" Anomalies clients", command=self.show_anomalies)
            
            if self.user[4] == USER_ROLES['SUPER_USER']:
                gestion_menu.add_separator()
                gestion_menu.add_command(label=" Gerer les utilisateurs", command=self.show_user_management)
                gestion_menu.add_command(label=" Configuration", command=self.show_configuration)
        
        # Menu Caisse
        caisse_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
        menubar.add_cascade(label=" Caisse", menu=caisse_menu)
        caisse_menu.add_command(label=" Utiliser un avoir", command=self.show_use_avoir, accelerator="Ctrl+U")
        caisse_menu.add_command(label=" Rechercher un avoir", command=self.show_search_avoir)
        caisse_menu.add_command(label=" Historique d'utilisation", command=self.show_utilisation_history)
        
        # Menu Rapports
        reports_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
        menubar.add_cascade(label=" Rapports", menu=reports_menu)
        reports_menu.add_separator()
        reports_menu.add_command(label=" Exporter CSV", command=self.export_csv)
        if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
            reports_menu.add_command(label=" Exporter Excel", command=self.export_excel)
        reports_menu.add_separator()
        reports_menu.add_command(label=" Imprimer rapport", command=self.print_report)
        
        # Menu Outils
        tools_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
        menubar.add_cascade(label=" Outils", menu=tools_menu)
        tools_menu.add_command(label=" Tester connexion email", command=self.test_email_connection)
        
        # Logs uniquement pour super_user et responsable
        if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
            tools_menu.add_command(label=" Logs systeme", command=self.show_logs)
        
        tools_menu.add_command(label=" Verifier base de donnees", command=self.verify_database)
        
        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['white'])
        menubar.add_cascade(label=" Aide", menu=help_menu)
        help_menu.add_command(label=" Documentation", command=self.show_documentation)
        help_menu.add_command(label=" Raccourcis clavier", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label=" A propos", command=self.show_about)
    
    def create_sidebar(self):
        """Cree la sidebar de navigation moderne"""
        # Logo/Header de la sidebar
        header_frame = tk.Frame(self.sidebar_frame, bg=self.colors['primary'], height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Logo et titre
        tk.Label(
            header_frame,
            text="QC",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['primary'],
            fg=self.colors['secondary']
        ).pack(pady=(15, 0))
        
        # Informations utilisateur
        user_frame = tk.Frame(self.sidebar_frame, bg=self.colors['sidebar_bg'])
        user_frame.pack(fill='x', pady=20, padx=15)
        
        # Avatar utilisateur (cercle avec initiales)
        avatar_canvas = tk.Canvas(
            user_frame,
            width=50,
            height=50,
            bg=self.colors['sidebar_bg'],
            highlightthickness=0
        )
        avatar_canvas.pack()
        avatar_canvas.create_oval(2, 2, 48, 48, fill=self.colors['accent'], outline='')
        initials = self.user[1][0].upper() if self.user[1] else "U"
        avatar_canvas.create_text(25, 25, text=initials, font=('Segoe UI', 18, 'bold'), fill=self.colors['secondary'])
        
        tk.Label(
            user_frame,
            text=self.user[1],
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['sidebar_bg'],
            fg=self.colors['white']
        ).pack(pady=(10, 0))
        
        tk.Label(
            user_frame,
            text=self.user[4].replace('_', ' ').title(),
            font=('Segoe UI', 9),
            bg=self.colors['sidebar_bg'],
            fg=self.colors['accent']
        ).pack()
        
        # Separateur
        tk.Frame(self.sidebar_frame, height=1, bg=self.colors['accent']).pack(fill='x', padx=20, pady=10)
        
        # Menu de navigation
        nav_frame = tk.Frame(self.sidebar_frame, bg=self.colors['sidebar_bg'])
        nav_frame.pack(fill='both', expand=True, padx=10)
        
        # Boutons de navigation
        if self.user[4] == USER_ROLES['VENDEUR']:
            # Le vendeur n'a acces qu'a l'utilisation d'un avoir
            nav_items = [
                ("", "Utiliser avoir", self.show_use_avoir),
            ]
        else:
            nav_items = [
                ("", "Tableau de bord", self.show_dashboard),
                ("", "Utiliser avoir", self.show_use_avoir),
                ("", "Liste avoirs", self.show_avoirs_list),
                ("", "Historique", self.show_utilisation_history),
            ]
            
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
                nav_items.insert(2, ("", "Creer avoir", self.show_create_avoir))
            
            if self.user[4] == USER_ROLES['SUPER_USER']:
                nav_items.append(("", "Utilisateurs", self.show_user_management))
            
            # Onglet Anomalies : super_user et comptabilite uniquement
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['COMPTABILITE']]:
                nav_items.append(("", "Anomalies", self.show_anomalies))
            
            # Ajouter les logs seulement pour super_user, responsable et comptabilite
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
                nav_items.append(("", "Logs", self.show_logs))
        
        self.nav_buttons = []
        for icon, text, command in nav_items:
            btn = self.create_nav_button(nav_frame, icon, text, command)
            self.nav_buttons.append(btn)
        
        # Bouton de deconnexion en bas
        logout_frame = tk.Frame(self.sidebar_frame, bg=self.colors['sidebar_bg'])
        logout_frame.pack(side='bottom', fill='x', pady=20, padx=20)
        
        logout_btn = tk.Button(
            logout_frame,
            text=" Deconnexion",
            command=self.logout,
            font=('Segoe UI', 10),
            bg=self.colors['error'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        )
        logout_btn.pack(fill='x')
    
    def create_nav_button(self, parent, icon, text, command):
        """Cree un bouton de navigation pour la sidebar"""
        btn_frame = tk.Frame(parent, bg=self.colors['sidebar_bg'])
        btn_frame.pack(fill='x', pady=2)
        
        btn = tk.Button(
            btn_frame,
            text=f"{icon}  {text}",
            command=command,
            font=('Segoe UI', 11),
            bg=self.colors['sidebar_bg'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            anchor='w',
            padx=15,
            pady=12
        )
        btn.pack(fill='x')
        
        # Effets hover
        def on_enter(e):
            btn.configure(bg=self.colors['accent'], fg=self.colors['secondary'])
        
        def on_leave(e):
            btn.configure(bg=self.colors['sidebar_bg'], fg=self.colors['white'])
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def create_content_area(self):
        """Cree la zone de contenu principal"""
        # Header de contenu
        self.content_header = tk.Frame(
            self.content_container,
            bg=self.colors['white'],
            height=70
        )
        self.content_header.pack(fill='x')
        self.content_header.pack_propagate(False)
        
        # Titre du contenu
        self.content_title = tk.Label(
            self.content_header,
            text="Tableau de bord",
            font=('Segoe UI', 20, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['text_primary']
        )
        self.content_title.pack(side='left', padx=30, pady=20)
        
        # # Barre de recherche
        # search_frame = tk.Frame(self.content_header, bg=self.colors['white'])
        # search_frame.pack(side='right', padx=30, pady=20)
        
        # search_entry = tk.Entry(
        #     search_frame,
        #     textvariable=self.search_var,
        #     font=('Segoe UI', 10),
        #     width=30,
        #     bd=1,
        #     relief='solid'
        # )
        # search_entry.pack(side='left', padx=(0, 10))
        
        # search_btn = tk.Button(
        #     search_frame,
        #     text=" Rechercher",
        #     font=('Segoe UI', 10),
        #     bg=self.colors['primary'],
        #     fg=self.colors['secondary'],
        #     bd=0,
        #     cursor='hand2',
        #     padx=15
        # )
        # search_btn.pack(side='left')
        
        # Zone de contenu avec scrollbar
        self.content_frame = tk.Frame(
            self.content_container,
            bg=self.colors['bg_light']
        )
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=10)
    
    def create_status_bar(self):
        """Cree la barre de statut en bas"""
        self.status_bar = tk.Frame(
            self.root,
            bg=self.colors['secondary'],
            height=30
        )
        self.status_bar.pack(side='bottom', fill='x')
        
        # Message de statut
        self.status_message = tk.Label(
            self.status_bar,
            text="Pret",
            font=('Segoe UI', 9),
            bg=self.colors['secondary'],
            fg=self.colors['white']
        )
        self.status_message.pack(side='left', padx=10)
        
        # Heure actuelle
        self.time_label = tk.Label(
            self.status_bar,
            text="",
            font=('Segoe UI', 9),
            bg=self.colors['secondary'],
            fg=self.colors['accent']
        )
        self.time_label.pack(side='right', padx=10)
        self.update_time()
        
        # Indicateur de connexion
        connection_indicator = tk.Label(
            self.status_bar,
            text=" En ligne",
            font=('Segoe UI', 9),
            bg=self.colors['secondary'],
            fg=self.colors['success']
        )
        connection_indicator.pack(side='right', padx=20)
    
    def update_time(self):
        """Met a jour l'heure dans la barre de statut"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.root.after(1000, self.update_time)
    
    def clear_content_frame(self):
        """Efface le contenu actuel"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_content_title(self, title):
        """Met a jour le titre du contenu"""
        self.content_title.configure(text=title)
    
    def show_dashboard(self):
        """Affiche le tableau de bord moderne avec statistiques avoirs partiels"""
        self.clear_content_frame()
        self.update_content_title("Tableau de bord")
        self.update_status("Chargement du tableau de bord...")
        
        # Recuperation des statistiques
        stats = self.avoir_manager.get_statistics()
        
        # Container principal avec scrollbar
        canvas = tk.Canvas(self.content_frame, bg=self.colors['bg_light'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_light'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Cartes de statistiques
        stats_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'])
        stats_frame.pack(pady=20, padx=20, fill='x')
        
        # Creation des cartes - Vue d'ensemble par statut
        cards_data = [
            ("Total avoirs", stats.get('total_avoirs', 0),
             "hors supprimes", self.colors['secondary'], ""),
            ("Avoirs actifs", stats.get('avoirs_valides_count', stats.get('avoirs_actifs_count', 0)),
             self.format_montant_xpf(stats['avoirs_actifs_montant']),
             self.colors['success'], ""),
            ("Avoirs expires", stats.get('avoirs_expires_count', 0),
             "avoirs", self.colors['warning'], ""),
            ("Avoirs bloques", stats.get('avoirs_bloques_count', 0),
             "a regulariser", self.colors['error'], "")
        ]
        
        for i, (title, value, subtitle, color, icon) in enumerate(cards_data):
            self.create_stat_card(stats_frame, title, value, subtitle, color, icon, i)
        
        # Section utilisation
        utilisation_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'])
        utilisation_frame.pack(pady=20, padx=20, fill='x')
        
        # Cartes d'utilisation / autres etats
        util_cards_data = [
            ("Avoirs utilises", stats.get('avoirs_utilises_count', 0),
             "totalement", self.colors['info'], ""),
            ("Avoirs annules", stats.get('avoirs_annules_count', 0),
             "avoirs", self.colors['text_secondary'], ""),
            ("A expirer (7j)", len(stats['avoirs_peremption']),
             "avoirs actifs", self.colors['warning'], ""),
            ("Montant restant", "-",
             self.format_montant_xpf(stats.get('montant_total_restant', 0)),
             self.colors['accent'], "")
        ]
        
        for i, (title, value, subtitle, color, icon) in enumerate(util_cards_data):
            self.create_stat_card(utilisation_frame, title, value, subtitle, color, icon, i)
        
        # Graphiques (placeholder)
        chart_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_light'])
        chart_frame.pack(pady=20, padx=20, fill='both', expand=True)
        
        # Avoirs a peremption
        if stats['avoirs_peremption']:
            self.create_expiring_avoirs_section(chart_frame, stats['avoirs_peremption'])
        
        # Top clients
        # if stats['top_clients']:
        #     self.create_top_clients_section(chart_frame, stats['top_clients'])
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.update_status("Tableau de bord charge")
    
    def create_stat_card(self, parent, title, value, subtitle, color, icon, column):
        """Cree une carte de statistique moderne"""
        card = tk.Frame(
            parent,
            bg=self.colors['white'],
            relief='flat',
            bd=0
        )
        card.grid(row=0, column=column, padx=10, pady=5, sticky='nsew')
        parent.grid_columnconfigure(column, weight=1)
        
        # Ombre de la carte
        card.configure(highlightbackground=self.colors['hover'], highlightthickness=1)
        
        # Container interne
        inner = tk.Frame(card, bg=self.colors['white'])
        inner.pack(padx=20, pady=20)
        
        # Icone et titre
        header = tk.Frame(inner, bg=self.colors['white'])
        header.pack(fill='x')
        
        tk.Label(
            header,
            text=icon,
            font=('Segoe UI', 24),
            bg=self.colors['white'],
            fg=color
        ).pack(side='left', padx=(0, 10))
        
        tk.Label(
            header,
            text=title,
            font=('Segoe UI', 11),
            bg=self.colors['white'],
            fg=self.colors['text_secondary']
        ).pack(side='left')
        
        # Valeur
        tk.Label(
            inner,
            text=str(value),
            font=('Segoe UI', 32, 'bold'),
            bg=self.colors['white'],
            fg=color
        ).pack(pady=(10, 0))
        
        # Sous-titre
        tk.Label(
            inner,
            text=subtitle,
            font=('Segoe UI', 10),
            bg=self.colors['white'],
            fg=self.colors['text_secondary']
        ).pack()
        
        # Effet hover sur la carte
        def on_enter(e):
            card.configure(highlightbackground=color)
        
        def on_leave(e):
            card.configure(highlightbackground=self.colors['hover'])
        
        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
    
    def create_expiring_avoirs_section(self, parent, avoirs):
        """Cree la section des avoirs a expiration avec montant restant"""
        frame = tk.LabelFrame(
            parent,
            text=" Avoirs bientot expires",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['warning'],
            relief='flat',
            bd=1
        )
        frame.pack(fill='x', pady=10)
        
        # Tableau moderne
        columns = ('N Avoir', 'Client', 'Montant restant', 'Expire dans')
        tree = ttk.Treeview(
            frame,
            columns=columns,
            show='headings',
            height=8,
            style='Modern.Treeview'
        )
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200)
        
        # Tags pour coloration
        tree.tag_configure('urgent', background='#ffebee')
        tree.tag_configure('warning', background='#fff3e0')
        
        for avoir in avoirs[:10]:
            if isinstance(avoir[11], str):
                date_validite = datetime.fromisoformat(avoir[11])
            else:
                date_validite = avoir[11]
            
            jours_restants = (date_validite - datetime.now()).days
            montant_restant = avoir[13] if len(avoir) > 13 else avoir[8]
            
            tag = 'urgent' if jours_restants <= 2 else 'warning'
            
            tree.insert('', 'end', values=(
                avoir[1],
                f"{avoir[2]} - {avoir[3]}",
                self.format_montant_xpf(montant_restant),
                f"{jours_restants} jour{'s' if jours_restants > 1 else ''}"
            ), tags=(tag,))
        
        tree.pack(padx=20, pady=20)
    
    # def create_top_clients_section(self, parent, clients):
    #     """Cree la section des top clients"""
    #     frame = tk.LabelFrame(
    #         parent,
    #         text=" Top 10 Clients",
    #         font=('Segoe UI', 12, 'bold'),
    #         bg=self.colors['white'],
    #         fg=self.colors['accent'],
    #         relief='flat',
    #         bd=1
    #     )
    #     frame.pack(fill='x', pady=10)
        
    #     # Tableau moderne
    #     columns = ('N Client', 'Nom', 'Nb Avoirs', 'Montant Total')
    #     tree = ttk.Treeview(
    #         frame,
    #         columns=columns,
    #         show='headings',
    #         height=10,
    #         style='Modern.Treeview'
    #     )
        
    #     for col in columns:
    #         tree.heading(col, text=col)
    #         tree.column(col, width=200)
        
    #     # Alternance de couleurs
    #     tree.tag_configure('odd', background=self.colors['hover'])
        
    #     for i, client in enumerate(clients):
    #         tag = 'odd' if i % 2 else ''
    #         tree.insert('', 'end', values=(
    #             client[0], client[1], client[2], 
    #             self.format_montant_xpf(client[3])
    #         ), tags=(tag,))
        
    #     tree.pack(padx=20, pady=20)
    
    def show_use_avoir(self):
        """Interface d'utilisation d'avoir avec gestion partielle"""
        self.clear_content_frame()
        self.update_content_title("Utiliser un avoir")
        self.update_status("Scanner ou saisir un avoir")
        
        # Container principal
        main_container = tk.Frame(self.content_frame, bg=self.colors['white'])
        main_container.pack(fill='both', expand=True, padx=40, pady=20)
        
        # Carte centrale.
        # La HAUTEUR n'est PAS figee : elle s'adapte au contenu, sinon les
        # boutons du bas se retrouvent coupes (la carte etait limitee a 500 px
        # alors que son contenu en demande davantage).
        card = tk.Frame(main_container, bg=self.colors['white'], relief='flat')
        card.place(relx=0.5, rely=0.5, anchor='center', width=700)

        # Bordure coloree
        top_border = tk.Frame(card, bg=self.colors['primary'], height=5)
        top_border.pack(fill='x')

        # Titre
        tk.Label(
            card,
            text="Scanner ou Saisir l'Avoir",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['text_primary']
        ).pack(pady=(20, 10))

        # Instructions
        instructions = tk.Frame(card, bg=self.colors['info'], relief='flat')
        instructions.pack(pady=12, padx=50, fill='x')
        
        tk.Label(
            instructions,
            text=" INSTRUCTIONS",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['info'],
            fg=self.colors['white']
        ).pack(pady=(10, 5))
        
        tk.Label(
            instructions,
            text="Scannez le code-barres du bon d'avoir\n" +
                 "OU saisissez manuellement le numero (ex: 2500001)\n" +
                 "Le systeme reconnait automatiquement les deux formats\n" +
                 "Saisissez ensuite le numero et montant de la facture",
            font=('Segoe UI', 10),
            bg=self.colors['info'],
            fg=self.colors['white'],
            justify='left'
        ).pack(pady=(0, 10), padx=20)
        
        # Zone de saisie
        input_frame = tk.Frame(card, bg=self.colors['white'])
        input_frame.pack(pady=10)
        
        # Animation de scan
        scan_canvas = tk.Canvas(
            input_frame,
            width=80,
            height=80,
            bg=self.colors['white'],
            highlightthickness=0
        )
        scan_canvas.pack()
        
        # Dessiner l'icone de scan
        scan_canvas.create_rectangle(20, 20, 60, 60, outline=self.colors['primary'], width=3)
        scan_canvas.create_line(10, 40, 70, 40, fill=self.colors['error'], width=2)
        
        tk.Label(
            input_frame,
            text="Scanner ou saisir:",
            font=('Segoe UI', 13),
            bg=self.colors['white'],
            fg=self.colors['text_secondary']
        ).pack(pady=(15, 8))
        
        # Champ de saisie grand format
        self.avoir_input = tk.Entry(
            input_frame,
            font=('Segoe UI', 10, 'bold'),
            width=20,
            justify='center',
            bd=0.2,
            relief='solid'
        )
        self.avoir_input.pack(pady=6, ipady=12)
        self.avoir_input.bind('<Return>', lambda e: self.validate_avoir())
        self.avoir_input.bind('<KeyRelease>', self.detect_format)
        self.avoir_input.focus()
        
        # Indicateur de format
        self.format_label = tk.Label(
            input_frame,
            text="",
            font=('Segoe UI', 10, 'italic'),
            bg=self.colors['white'],
            fg=self.colors['text_secondary']
        )
        self.format_label.pack()
        
        # Boutons : validation d'un seul avoir OU cumul de plusieurs avoirs
        buttons_row = tk.Frame(input_frame, bg=self.colors['white'])
        buttons_row.pack(pady=14)

        validate_btn = tk.Button(
            buttons_row,
            text="VALIDER",
            command=self.validate_avoir,
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['success'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=40,
            pady=15
        )
        validate_btn.pack(side='left')

        # Cumul de plusieurs bons d'avoir sur une meme facture
        multi_btn = tk.Button(
            buttons_row,
            text="PLUSIEURS AVOIRS",
            command=self.validate_multi_avoirs,
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['info'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=30,
            pady=15
        )
        multi_btn.pack(side='left', padx=(15, 0))
    
    def validate_avoir(self):
        """Valide l'utilisation d'un avoir avec dialogue pour montant et facture"""
        input_value = self.avoir_input.get().strip()
        if not input_value:
            messagebox.showerror(
                "Erreur de saisie", 
                "Veuillez saisir un numero d'avoir ou scanner le code-barres"
            )
            return
        
        # Determiner le format et traiter
        numero_avoir = input_value
        
        # Si c'est un code-barres (format sans slash)
        if '/' not in input_value and len(input_value) >= 6:
            if len(input_value) == 7:  # Format YYXXXXX
                numero_avoir = f"{input_value[:2]}/{input_value[2:]}"
                print(f" Code-barres detecte: {input_value}  N avoir: {numero_avoir}")
        
        # Recuperer les details de l'avoir
        avoir_details = self.avoir_manager.get_avoir_details(numero_avoir)
        if not avoir_details:
            messagebox.showerror(
                " AVOIR INTROUVABLE",
                f"L'avoir {numero_avoir} n'existe pas!\n\n"
                f"Verifiez le numero saisi ou le code-barres scanne."
            )
            self.reset_avoir_input()
            return
        
        avoir = avoir_details if not isinstance(avoir_details, dict) else avoir_details['avoir']
        
        # Verifier le statut
        statut = avoir[12]
        if statut == AVOIR_STATUS['UTILISE']:
            self.play_sound('error')
            messagebox.showerror(
                " AVOIR DEJA UTILISE",
                f"ERREUR : L'avoir {numero_avoir} a deja ete utilise!\n\n"
                f"Cet avoir ne peut pas etre valide une seconde fois."
            )
            self.reset_avoir_input()
            return
        
        if statut == AVOIR_STATUS['EXPIRE']:
            self.play_sound('error')
            messagebox.showerror(
                " AVOIR EXPIRE",
                f"ERREUR : L'avoir {numero_avoir} est expire!"
            )
            self.reset_avoir_input()
            return
        
        # Recuperer le montant restant
        montant_restant = avoir[20] if avoir[20] is not None else avoir[8]
        
        # Ouvrir le dialogue pour saisir le montant et la facture
        dialog = UtilisationDialog(self.root, numero_avoir, montant_restant)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            # Utiliser l'avoir avec les parametres saisis
            self.update_status(f"Validation de l'avoir {numero_avoir}...")
            
            result = self.avoir_manager.use_avoir(
                numero_avoir, 
                self.user[1],
                dialog.result['montant_facture'],
                dialog.result['numero_facture']
            )
            
            # Affichage du resultat
            if result['status'] == 'success':
                self.play_sound('success')
                
                # Message detaille selon le type d'utilisation
                if result.get('type_utilisation') == 'insuffisant':
                    # CAS: Avoir insuffisant - afficher le restant a payer
                    restant_a_payer = result.get('restant_a_payer', 0)
                    messagebox.showwarning(
                        "⚠️ RESTANT À PAYER",
                        f"L'avoir a été utilisé en totalité.\n\n"
                        f"Montant de l'avoir: {self.format_montant_xpf(result['montant_avoir'])}\n"
                        f"Montant de la facture: {self.format_montant_xpf(result['montant_facture'])}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💰 RESTANT À PAYER: {self.format_montant_xpf(restant_a_payer)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"Le client doit régler ce montant."
                    )
                elif result.get('type_utilisation') == 'partielle':
                    messagebox.showinfo(
                        " UTILISATION PARTIELLE REUSSIE",
                        f"{result['message']}\n\n"
                        f"Un nouvel avoir a ete cree pour le solde restant.\n"
                        f"N'oubliez pas de remettre le nouvel avoir au client."
                    )
                else:
                    messagebox.showinfo(
                        " VALIDATION REUSSIE",
                        f"{result['message']}\n\n"
                        f"L'avoir a ete marque comme UTILISE dans le systeme."
                    )
                
                # Enregistrer dans les logs
                self.db.add_log(
                    self.user[1], 
                    f"VALIDATION_AVOIR_{result.get('type_utilisation', 'TOTALE').upper()}", 
                    f"Avoir {numero_avoir} - Facture: {dialog.result['numero_facture']}"
                )
            else:
                self.play_sound('error')
                messagebox.showerror(" ERREUR", result['message'])
        
        # Reinitialiser le champ de saisie
        self.reset_avoir_input()
    
    def show_create_avoir(self):
        """Affiche le formulaire de creation d'avoir (toujours type retour) - mise en page 2 colonnes"""
        if self.user[4] not in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
            messagebox.showerror("Erreur", "Acces non autorise")
            return
        
        self.clear_content_frame()
        self.update_content_title("Creer un avoir")
        self.update_status("Formulaire de creation d'avoir")
        
        # Container avec scrollbar (filet de securite sur tres petit ecran)
        canvas = tk.Canvas(self.content_frame, bg=self.colors['bg_light'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        form_container = tk.Frame(canvas, bg=self.colors['bg_light'])
        
        form_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=form_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # La carte du formulaire suit la largeur disponible (occupe la place a droite)
        def _resize_form(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _resize_form)
        
        # Carte du formulaire
        form_card = tk.Frame(
            form_container,
            bg=self.colors['white'],
            relief='flat',
            bd=0
        )
        form_card.pack(pady=20, padx=40, fill='both', expand=True)
        
        # Bordure coloree en haut
        top_border = tk.Frame(form_card, bg=self.colors['primary'], height=5)
        top_border.pack(fill='x')
        
        # Container du formulaire
        form_frame = tk.Frame(form_card, bg=self.colors['white'])
        form_frame.pack(pady=30, padx=40, fill='both', expand=True)
        
        # Titre du formulaire + numero d'avoir qui va etre cree (a cote du titre)
        title_frame = tk.Frame(form_frame, bg=self.colors['white'])
        title_frame.pack(pady=(0, 20))

        tk.Label(
            title_frame,
            text="Nouveau Bon d'Avoir",
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['text_primary']
        ).pack(side='left')

        # Numero d'avoir previsionnel (le prochain numero disponible au moment de l'ouverture)
        try:
            self.numero_avoir_prevu = self.avoir_manager.generate_numero_avoir()
        except Exception:
            self.numero_avoir_prevu = None

        self.numero_avoir_label = tk.Label(
            title_frame,
            text=(f"N° {self.numero_avoir_prevu}" if self.numero_avoir_prevu else ""),
            font=('Segoe UI', 13, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['secondary']
        )
        self.numero_avoir_label.pack(side='left', padx=(12, 0), pady=(6, 0))
        
        # Champs du formulaire
        self.avoir_entries = {}
        
        # Helper local : ajoute un champ (label + entry) dans une colonne
        def _add_field(parent, key, label):
            f = tk.Frame(parent, bg=self.colors['white'])
            f.pack(fill='x', pady=(0, 15))
            tk.Label(
                f, text=label, font=('Segoe UI', 10),
                bg=self.colors['white'], fg=self.colors['text_secondary']
            ).pack(anchor='w', pady=(0, 5))
            entry = tk.Entry(f, font=('Segoe UI', 10), bd=1, relief='solid')
            entry.pack(fill='x')
            self.avoir_entries[key] = entry
            return entry
        
        # ─── Deux colonnes cote a cote ───
        columns_frame = tk.Frame(form_frame, bg=self.colors['white'])
        columns_frame.pack(fill='both', expand=True)
        
        left_col = tk.Frame(columns_frame, bg=self.colors['white'])
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 25), anchor='n')
        
        right_col = tk.Frame(columns_frame, bg=self.colors['white'])
        right_col.pack(side='left', fill='both', expand=True, padx=(25, 0), anchor='n')
        
        # ===== COLONNE GAUCHE : Client + Facture =====
        self.create_form_section(left_col, " Informations Client")
        _add_field(left_col, 'numero_client', "Numero client *")
        _add_field(left_col, 'nom_client', "Nom client *")
        email_entry = _add_field(left_col, 'email_client', "Email client")
        email_entry.bind('<FocusOut>', lambda e: self.validate_email(e, 'email_client'))
        
        self.create_form_section(left_col, " Informations Facture")
        _add_field(left_col, 'numero_facture', "Numero facture achat *")
        
        # Date facture achat
        date_frame = tk.Frame(left_col, bg=self.colors['white'])
        date_frame.pack(fill='x', pady=(0, 15))
        tk.Label(
            date_frame, text="Date facture achat", font=('Segoe UI', 10),
            bg=self.colors['white'], fg=self.colors['text_secondary']
        ).pack(anchor='w', pady=(0, 5))
        
        if DATEPICKER_AVAILABLE:
            self.date_facture_picker = DateEntry(
                date_frame,
                width=20,
                background=self.colors['primary'],
                foreground=self.colors['secondary'],
                borderwidth=1,
                date_pattern='dd/mm/yyyy',
                locale='fr_FR',
                font=('Segoe UI', 10),
                maxdate=datetime.now().date()
            )
            self.date_facture_picker.pack(fill='x')
        else:
            self.avoir_entries['date_facture'] = tk.Entry(
                date_frame, font=('Segoe UI', 10), bd=1, relief='solid'
            )
            self.avoir_entries['date_facture'].pack(fill='x')
            tk.Label(
                date_frame, text="Format: JJ/MM/AAAA", font=('Segoe UI', 8),
                bg=self.colors['white'], fg=self.colors['text_secondary']
            ).pack(anchor='w')
        
        # ===== COLONNE DROITE : Details + Signature =====
        self.create_form_section(right_col, " Details de l'Avoir")
        montant_entry = _add_field(right_col, 'montant', "Montant TTC (XPF) *")
        montant_entry.bind('<FocusOut>', lambda e: self.validate_montant(e, 'montant'))

        # N facture avoir : place dans les details de l'avoir, sous le montant TTC
        _add_field(right_col, 'numero_facture_avoir', "N facture avoir")
        
        # Option email
        email_option = tk.Frame(right_col, bg=self.colors['white'])
        email_option.pack(fill='x', pady=(0, 15))
        tk.Checkbutton(
            email_option,
            text=" Envoyer email de confirmation au client",
            variable=self.send_email_var,
            font=('Segoe UI', 10),
            bg=self.colors['white'],
            activebackground=self.colors['white'],
            command=self.toggle_email_field
        ).pack(anchor='w')
        
        # Signature
        self.create_form_section(right_col, " Signature")
        signature_frame = tk.Frame(right_col, bg=self.colors['white'])
        signature_frame.pack(fill='x', pady=(0, 20))
        tk.Label(
            signature_frame,
            text="Mot de passe pour signature *",
            font=('Segoe UI', 10),
            bg=self.colors['white'],
            fg=self.colors['text_secondary']
        ).pack(anchor='w', pady=(0, 5))
        self.signature_entry = tk.Entry(
            signature_frame,
            font=('Segoe UI', 10),
            show='•',
            bd=1,
            relief='solid'
        )
        self.signature_entry.pack(fill='x')
        
        # ===== Boutons d'action (sous les deux colonnes) =====
        button_frame = tk.Frame(form_frame, bg=self.colors['white'])
        button_frame.pack(pady=25)
        
        create_btn = tk.Button(
            button_frame,
            text=" Creer et Imprimer",
            command=self.create_avoir,
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['success'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=30,
            pady=12
        )
        create_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(
            button_frame,
            text=" Annuler",
            command=self.show_dashboard,
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['error'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=30,
            pady=12
        )
        cancel_btn.pack(side='left', padx=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Focus sur le premier champ
        if 'numero_client' in self.avoir_entries:
            self.avoir_entries['numero_client'].focus()
    
    # def create_avoir(self):
    #     """Cree un nouvel avoir (toujours type retour)"""
    #     # Validation de la signature
    #     signature = self.signature_entry.get()
    #     if not self.user_manager.authenticate(self.user[1], signature):
    #         messagebox.showerror("Erreur", "Signature incorrecte")
    #         return
        
    #     # Recuperation et validation des donnees
    #     try:
    #         email_client = self.avoir_entries['email_client'].get().strip()
            
    #         # Si l'option email est cochee, verifier qu'il y a un email
    #         if self.send_email_var.get() and not email_client:
    #             messagebox.showerror("Erreur", "L'email client est requis si l'option d'envoi est activee")
    #             return
            
    #         # Recuperation de la date
    #         date_facture = ''
    #         if DATEPICKER_AVAILABLE and hasattr(self, 'date_facture_picker'):
    #             date_facture = self.date_facture_picker.get()
    #         elif 'date_facture' in self.avoir_entries:
    #             date_facture = self.avoir_entries['date_facture'].get().strip()
            
    #         # Nettoyage du montant
    #         montant_str = self.avoir_entries['montant'].get().strip()
    #         montant_clean = montant_str.replace(' ', '').replace(',', '.')
            
    #         data = {
    #             'numero_client': self.avoir_entries['numero_client'].get().strip(),
    #             'nom_client': self.avoir_entries['nom_client'].get().strip(),
    #             'email_client': email_client,
    #             'numero_facture': self.avoir_entries['numero_facture'].get().strip(),
    #             'date_facture': date_facture,
    #             'type_avoir': AVOIR_CONFIG['TYPE_DEFAUT'],  # Toujours 'retour'
    #             'montant': float(montant_clean),
    #             'numero_facture_avoir': self.avoir_entries.get('numero_facture_avoir', tk.Entry()).get().strip() if 'numero_facture_avoir' in self.avoir_entries else '',
    #             'utilisateur': self.user[1],
    #             'signature': hashlib.sha256(signature.encode()).hexdigest(),
    #             'send_email': self.send_email_var.get()
    #         }
            
    #         # Validation des champs obligatoires
    #         if not all([data['numero_client'], data['nom_client'], 
    #                    data['numero_facture'], data['montant']]):
    #             messagebox.showerror("Erreur", "Tous les champs obligatoires doivent etre remplis")
    #             return
            
    #         # Creation de l'avoir
    #         self.update_status("Creation de l'avoir en cours...")
    #         numero_avoir = self.avoir_manager.create_avoir(data)
            
    #         # Generation du PDF
    #         self.update_status("Generation du PDF...")
    #         self.generate_pdf(numero_avoir, data)
            
    #         # Message de succes
    #         success_msg = f" Avoir {numero_avoir} cree avec succes!\n Le PDF a ete genere et ouvert."
    #         success_msg += f"\n\nType: RETOUR (automatique)"
    #         if self.send_email_var.get() and email_client:
    #             success_msg += f"\n Email envoye a {email_client}"
            
    #         messagebox.showinfo("Succes", success_msg)
    #         self.update_status(f"Avoir {numero_avoir} cree avec succes")
    #         self.show_dashboard()
            
    #     except ValueError as e:
    #         messagebox.showerror("Erreur", f"Erreur dans les donnees: {str(e)}")
    #     except Exception as e:
    #         messagebox.showerror("Erreur", f"Erreur inattendue: {str(e)}")
    #         self.update_status("Erreur lors de la creation")


    def create_avoir(self):
            """Cree un nouvel avoir (toujours type retour)"""
            # Validation de la signature
            signature = self.signature_entry.get()
            if not self.user_manager.authenticate(self.user[1], signature):
                messagebox.showerror("Erreur", "Signature incorrecte")
                return
            
            # Recuperation et validation des donnees
            try:
                email_client = self.avoir_entries['email_client'].get().strip()
                
                # Si l'option email est cochee, verifier qu'il y a un email
                if self.send_email_var.get() and not email_client:
                    messagebox.showerror("Erreur", "L'email client est requis si l'option d'envoi est activee")
                    return
                
                # Recuperation de la date
                date_facture = ''
                if DATEPICKER_AVAILABLE and hasattr(self, 'date_facture_picker'):
                    date_facture = self.date_facture_picker.get()
                elif 'date_facture' in self.avoir_entries:
                    date_facture = self.avoir_entries['date_facture'].get().strip()
                
                # Nettoyage du montant
                montant_str = self.avoir_entries['montant'].get().strip()
                montant_clean = montant_str.replace(' ', '').replace(',', '.')
                
                data = {
                    'numero_client': self.avoir_entries['numero_client'].get().strip(),
                    'nom_client': self.avoir_entries['nom_client'].get().strip(),
                    'email_client': email_client,
                    'numero_facture': self.avoir_entries['numero_facture'].get().strip(),
                    'date_facture': date_facture,
                    'type_avoir': AVOIR_CONFIG['TYPE_DEFAUT'],  # Toujours 'retour'
                    'montant': float(montant_clean),
                    'numero_facture_avoir': self.avoir_entries.get('numero_facture_avoir', tk.Entry()).get().strip() if 'numero_facture_avoir' in self.avoir_entries else '',
                    'utilisateur': self.user[1],
                    'signature': hashlib.sha256(signature.encode()).hexdigest(),
                    'send_email': self.send_email_var.get()
                }
                
                # Validation des champs obligatoires
                if not all([data['numero_client'], data['nom_client'],
                        data['numero_facture'], data['montant']]):
                    messagebox.showerror("Erreur", "Tous les champs obligatoires doivent etre remplis")
                    return

                # Verifier que le numero d'avoir previsionnel n'a pas change
                # (un autre utilisateur a pu creer un avoir entre l'ouverture du
                #  formulaire et la validation, ce qui decale le numero).
                try:
                    numero_actuel = self.avoir_manager.generate_numero_avoir()
                except Exception:
                    numero_actuel = None

                if (numero_actuel and getattr(self, 'numero_avoir_prevu', None)
                        and numero_actuel != self.numero_avoir_prevu):
                    ancien_numero = self.numero_avoir_prevu
                    # Mettre a jour le numero previsionnel et son affichage
                    self.numero_avoir_prevu = numero_actuel
                    if hasattr(self, 'numero_avoir_label'):
                        try:
                            self.numero_avoir_label.config(text=f"N° {numero_actuel}")
                        except Exception:
                            pass

                    continuer = messagebox.askokcancel(
                        "Numero d'avoir modifie",
                        f"Attention : le numero de votre bon d'avoir a change.\n\n"
                        f"Un autre avoir a ete cree entre-temps.\n"
                        f"Ancien numero prevu : {ancien_numero}\n"
                        f"Nouveau numero      : {numero_actuel}\n\n"
                        f"Voulez-vous continuer la creation avec le nouveau numero ?"
                    )
                    if not continuer:
                        self.update_status("Creation annulee (numero d'avoir modifie)")
                        return

                # Creation de l'avoir
                self.update_status("Creation de l'avoir en cours...")
                numero_avoir = self.avoir_manager.create_avoir(data)
                
                # CORRECTION: Utiliser PDFCreator au lieu de generate_pdf
                self.update_status("Generation du PDF...")
                
                try:
                    from services.pdf_creator import PDFCreator
                    
                    # Calculer la date de validite
                    date_validite = datetime.now() + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
                    
                    # Preparer les donnees pour le PDF
                    pdf_data = {
                        'numero_client': data['numero_client'],
                        'nom_client': data['nom_client'],
                        'email_client': email_client or '',
                        'numero_facture': data['numero_facture'],
                        'date_facture': date_facture or '',
                        'montant': data['montant'],
                        'numero_facture_avoir': data.get('numero_facture_avoir', ''),
                        'date_creation': datetime.now().strftime('%d/%m/%Y'),
                        'date_validite': date_validite.strftime('%d/%m/%Y')
                    }
                    
                    print(f"Generation PDF pour avoir {numero_avoir}")
                    print(f"   Montant: {pdf_data['montant']} XPF")
                    
                    pdf_creator = PDFCreator()
                    success_pdf, pdf_result = pdf_creator.generate(
                        numero_avoir,
                        pdf_data,
                        self.user[1]
                    )
                    
                    if success_pdf:
                        print(f"PDF genere: {pdf_result}")
                        pdf_status = "PDF genere et ouvert"
                    else:
                        print(f"Erreur PDF: {pdf_result}")
                        pdf_status = f"Erreur PDF: {pdf_result}"
                        messagebox.showwarning("Avertissement", f"L'avoir a ete cree mais le PDF n'a pas pu etre genere:\n{pdf_result}")
                
                except ImportError:
                    print("Module PDFCreator non disponible")
                    pdf_status = "Module reportlab non installe"
                    messagebox.showwarning(
                        "Module manquant",
                        "Le module reportlab n'est pas installe.\n"
                        "L'avoir a ete cree mais le PDF n'a pas ete genere.\n\n"
                        "Installez-le avec: pip install reportlab Pillow"
                    )
                except Exception as e:
                    print(f"Erreur generation PDF: {e}")
                    import traceback
                    traceback.print_exc()
                    pdf_status = f"Erreur: {str(e)}"
                    messagebox.showwarning("Avertissement", f"L'avoir a ete cree mais erreur PDF:\n{str(e)}")
                
                # Message de succes
                success_msg = f"Avoir {numero_avoir} cree avec succes!\n{pdf_status}"
                success_msg += f"\n\nType: RETOUR (automatique)"
                if self.send_email_var.get() and email_client:
                    success_msg += f"\nEmail envoye a {email_client}"
                
                messagebox.showinfo("Succes", success_msg)
                self.update_status(f"Avoir {numero_avoir} cree avec succes")
                self.show_dashboard()
                
            except ValueError as e:
                messagebox.showerror("Erreur", f"Erreur dans les donnees: {str(e)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur inattendue: {str(e)}")
                import traceback
                traceback.print_exc()
                self.update_status("Erreur lors de la creation")
    def show_utilisation_history(self):
        """Affiche l'historique d'utilisation des avoirs"""
        self.clear_content_frame()
        self.update_content_title("Historique d'utilisation")
        self.update_status("Chargement de l'historique...")
        
        # Container principal
        main_container = tk.Frame(self.content_frame, bg=self.colors['white'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Tableau de l'historique
        columns = ('Date', 'N Avoir', 'Type', 'Montant utilise', 'N Facture', 'Utilisateur', 'Avoir enfant')
        tree = ttk.Treeview(
            main_container,
            columns=columns,
            show='headings',
            height=20,
            style='Modern.Treeview'
        )
        
        # Configuration des colonnes
        column_widths = {
            'Date': 150,
            'N Avoir': 100,
            'Type': 100,
            'Montant utilise': 120,
            'N Facture': 150,
            'Utilisateur': 100,
            'Avoir enfant': 100
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths.get(col, 100))
        
        # Recuperer l'historique depuis la base
        try:
            historique = self.db.cursor.execute(
                """SELECT h.date_utilisation, h.numero_avoir, h.type_utilisation,
                          h.montant_utilise, h.numero_facture, h.utilisateur,
                          a.numero_avoir as avoir_enfant_numero
                   FROM historique_utilisation h
                   LEFT JOIN avoirs a ON h.avoir_enfant_id = a.id
                   ORDER BY h.date_utilisation DESC
                   LIMIT 500"""
            ).fetchall()
            
            for entry in historique:
                tree.insert('', 'end', values=(
                    entry[0],
                    entry[1],
                    entry[2] or 'Totale',
                    self.format_montant_xpf(entry[3]),
                    entry[4],
                    entry[5],
                    entry[6] or '-'
                ))
            
        except Exception as e:
            print(f"Erreur lors du chargement de l'historique: {e}")
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(main_container, orient='vertical', command=tree.yview)
        x_scrollbar = ttk.Scrollbar(main_container, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        y_scrollbar.pack(side='right', fill='y')
        
        self.update_status("Historique charge")
    
    def show_avoirs_list(self):
        """Affiche la liste des avoirs avec montants restants et filtres avances"""
        self.clear_content_frame()
        self.update_content_title("Liste des avoirs")
        self.update_status("Chargement de la liste des avoirs...")
        
        # ════════════════════════════════════════════════════════════════
        # BARRE DE FILTRES (deux rangees)
        # ════════════════════════════════════════════════════════════════
        filter_bar = tk.Frame(self.content_frame, bg=self.colors['white'])
        filter_bar.pack(fill='x', padx=20, pady=(0, 10))
        
        # --- Rangee 1 : statut + plage de dates de creation ---
        row1 = tk.Frame(filter_bar, bg=self.colors['white'])
        row1.pack(fill='x', pady=(10, 4))
        
        tk.Label(
            row1, text="Statut:", font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(side='left', padx=(20, 5))
        
        # Liste des filtres (ajout Annules et Supprimes pour super_user)
        filter_values = ['Tous', 'Actif', 'Utilise', 'Utilise partiellement', 'Expire']
        if self.user[4] == USER_ROLES['SUPER_USER']:
            filter_values.extend(['Annules', 'Supprimes'])
        
        filter_combo = ttk.Combobox(
            row1,
            textvariable=self.filter_status,
            values=filter_values,
            width=18,
            state='readonly'
        )
        filter_combo.pack(side='left', padx=5)
        
        # Plage de dates sur la DATE DE CREATION (format jj/mm/aaaa ; vide = pas de borne)
        tk.Label(
            row1, text="Cree du (jj/mm/aaaa):", font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(side='left', padx=(15, 5))
        self.filter_date_from = tk.Entry(row1, width=12, font=('Segoe UI', 10), bd=1, relief='solid')
        self.filter_date_from.pack(side='left', padx=5)
        
        tk.Label(
            row1, text="au:", font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(side='left', padx=(10, 5))
        self.filter_date_to = tk.Entry(row1, width=12, font=('Segoe UI', 10), bd=1, relief='solid')
        self.filter_date_to.pack(side='left', padx=5)
        
        # --- Rangee 2 : filtres responsables + boutons d'action ---
        row2 = tk.Frame(filter_bar, bg=self.colors['white'])
        row2.pack(fill='x', pady=(4, 10))
        
        # Filtre "Autorise par" (responsables ayant autorise un forcage)
        tk.Label(
            row2, text="Autorise par:", font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(side='left', padx=(20, 5))
        autorise_values = ['Tous'] + self.avoir_manager.get_distinct_autorise_par()
        self.filter_autorise_par = ttk.Combobox(
            row2, values=autorise_values, width=18, state='readonly'
        )
        self.filter_autorise_par.set('Tous')
        self.filter_autorise_par.pack(side='left', padx=5)
        
        # Filtre "Utilise par" (utilisateur ayant utilise l'avoir, tous roles)
        tk.Label(
            row2, text="Utilise par:", font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(side='left', padx=(15, 5))
        utilise_values = ['Tous'] + self.avoir_manager.get_distinct_utilise_par()
        self.filter_utilise_par = ttk.Combobox(
            row2, values=utilise_values, width=18, state='readonly'
        )
        self.filter_utilise_par.set('Tous')
        self.filter_utilise_par.pack(side='left', padx=5)
        
        # Boutons d'action
        filter_btn = tk.Button(
            row2, text=" Filtrer", command=self.refresh_avoirs_list,
            font=('Segoe UI', 10), bg=self.colors['primary'],
            fg=self.colors['secondary'], bd=0, cursor='hand2', padx=15
        )
        filter_btn.pack(side='left', padx=(20, 5))
        
        reset_btn = tk.Button(
            row2, text=" Reinitialiser", command=self.reset_avoirs_filters,
            font=('Segoe UI', 10), bg=self.colors['hover'],
            fg=self.colors['text_primary'], bd=0, cursor='hand2', padx=15
        )
        reset_btn.pack(side='left', padx=5)
        
        refresh_btn = tk.Button(
            row2, text=" Rafraichir", command=self.refresh_avoirs_list,
            font=('Segoe UI', 10), bg=self.colors['info'],
            fg=self.colors['white'], bd=0, cursor='hand2', padx=15
        )
        refresh_btn.pack(side='left', padx=5)
        
        export_btn = tk.Button(
            row2, text=" Exporter", command=self.export_csv,
            font=('Segoe UI', 10), bg=self.colors['success'],
            fg=self.colors['white'], bd=0, cursor='hand2', padx=15
        )
        export_btn.pack(side='left', padx=5)
        
        # ════════════════════════════════════════════════════════════════
        # TABLEAU DES AVOIRS
        # ════════════════════════════════════════════════════════════════
        table_frame = tk.Frame(self.content_frame, bg=self.colors['white'])
        table_frame.pack(fill='both', expand=True, padx=20)
        
        # Colonnes (ajout de "Autorise par", "Utilise par" et "Commentaire")
        columns = (
            'N Avoir', 'Client', 'Email', 'Montant', 'Utilise', 'Restant',
            'Date Creation', 'Date Validite', 'Statut',
            'Autorise par', 'Utilise par', 'Parent', 'Commentaire'
        )
        
        self.avoirs_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=20,
            style='Modern.Treeview'
        )
        
        # Configuration des colonnes
        column_widths = {
            'N Avoir': 100,
            'Client': 170,
            'Email': 140,
            'Montant': 95,
            'Utilise': 95,
            'Restant': 95,
            'Date Creation': 95,
            'Date Validite': 95,
            'Statut': 115,
            'Autorise par': 120,
            'Utilise par': 120,
            'Parent': 80,
            'Commentaire': 220
        }
        
        for col in columns:
            self.avoirs_tree.heading(col, text=col)
            self.avoirs_tree.column(col, width=column_widths.get(col, 100))
        
        # Menu "Colonnes" : permet d'afficher / masquer chaque colonne du tableau.
        # Place a la fin de la 2e rangee de la barre de filtres.
        self.avoirs_col_vars = {}
        col_menubtn = tk.Menubutton(
            row2, text=" Colonnes \u25be", font=('Segoe UI', 10),
            bg=self.colors['secondary'], fg=self.colors['white'],
            bd=0, cursor='hand2', padx=15, relief='flat'
        )
        col_menu = tk.Menu(col_menubtn, tearoff=0)
        col_menubtn.config(menu=col_menu)
        for col in columns:
            var = tk.BooleanVar(value=True)
            self.avoirs_col_vars[col] = var
            col_menu.add_checkbutton(
                label=col, variable=var, onvalue=True, offvalue=False,
                command=self.update_avoirs_columns
            )
        col_menubtn.pack(side='left', padx=5)
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.avoirs_tree.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.avoirs_tree.xview)
        self.avoirs_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack
        self.avoirs_tree.pack(side='left', fill='both', expand=True)
        y_scrollbar.pack(side='right', fill='y')
        x_scrollbar.pack(side='bottom', fill='x')
        
        # Tags pour coloration
        self.avoirs_tree.tag_configure('actif', background='#e8f5e9')
        self.avoirs_tree.tag_configure('expire', background='#fff3e0')
        self.avoirs_tree.tag_configure('utilise', background='#f3e5f5')
        self.avoirs_tree.tag_configure('partiel', background='#e3f2fd')
        self.avoirs_tree.tag_configure('enfant', foreground='#1976d2')
        self.avoirs_tree.tag_configure('annule', background='#ffcdd2')
        self.avoirs_tree.tag_configure('supprime', background='#ef9a9a', foreground='#b71c1c')
        
        # Double-clic pour details
        self.avoirs_tree.bind('<Double-Button-1>', self.show_avoir_details)

        # Clic droit : menu contextuel de reimpression PDF (super_user uniquement)
        if self.user[4] == USER_ROLES['SUPER_USER']:
            self.avoirs_tree.bind('<Button-3>', self.show_avoirs_context_menu)

        # Charger les donnees
        self.refresh_avoirs_list()
        self.update_status("Liste des avoirs chargee")
    
    def reset_avoirs_filters(self):
        """Reinitialise tous les filtres de la liste des avoirs puis rafraichit."""
        self.filter_status.set('Tous')
        try:
            if getattr(self, 'filter_autorise_par', None) is not None:
                self.filter_autorise_par.set('Tous')
            if getattr(self, 'filter_utilise_par', None) is not None:
                self.filter_utilise_par.set('Tous')
            for attr in ('filter_date_from', 'filter_date_to'):
                widget = getattr(self, attr, None)
                if widget is not None:
                    widget.delete(0, 'end')
        except Exception as e:
            print(f"Erreur reinitialisation des filtres: {e}")
        self.refresh_avoirs_list()
    
    def update_avoirs_columns(self):
        """Affiche ou masque les colonnes du tableau des avoirs (menu 'Colonnes')."""
        try:
            if not hasattr(self, 'avoirs_tree') or not hasattr(self, 'avoirs_col_vars'):
                return
            shown = [c for c, v in self.avoirs_col_vars.items() if v.get()]
            if not shown:
                # Toujours garder au moins une colonne visible
                shown = ['N Avoir']
                if 'N Avoir' in self.avoirs_col_vars:
                    self.avoirs_col_vars['N Avoir'].set(True)
            self.avoirs_tree['displaycolumns'] = shown
        except Exception as e:
            print(f"Erreur affichage/masquage colonnes: {e}")
    
    def refresh_avoirs_list(self):
        """Rafraichit la liste des avoirs (filtres statut / dates / responsables)"""
        # Effacer le tableau
        for item in self.avoirs_tree.get_children():
            self.avoirs_tree.delete(item)
        
        # --- Filtre statut ---
        # Les valeurs affichees ('Annules'/'Supprimes') sont converties vers le
        # statut reel stocke en base ('annule'/'supprime'). get_avoirs_list sait
        # interpreter ces valeurs (avec ou sans accent).
        filter_map = {
            'Utilise partiellement': AVOIR_STATUS['UTILISE_PARTIELLEMENT'],
            'Annules': 'annule',
            'Supprimes': 'supprime'
        }
        filter_value = filter_map.get(self.filter_status.get(), self.filter_status.get())
        
        # --- Filtre plage de dates sur la date de creation ---
        def _parse_filter_date(widget):
            if widget is None:
                return None
            try:
                txt = widget.get().strip()
            except Exception:
                return None
            if not txt:
                return None
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(txt, fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return None
        
        date_from = _parse_filter_date(getattr(self, 'filter_date_from', None))
        date_to = _parse_filter_date(getattr(self, 'filter_date_to', None))
        
        # --- Filtres responsables ('Tous' ou vide => pas de filtre) ---
        autorise_par = None
        utilise_par = None
        try:
            if getattr(self, 'filter_autorise_par', None) is not None:
                val = self.filter_autorise_par.get().strip()
                autorise_par = None if val in ('', 'Tous') else val
            if getattr(self, 'filter_utilise_par', None) is not None:
                val = self.filter_utilise_par.get().strip()
                utilise_par = None if val in ('', 'Tous') else val
        except Exception as e:
            print(f"Erreur lecture des filtres responsables: {e}")
        
        # Recuperer les avoirs filtres
        avoirs = self.avoir_manager.get_avoirs_list(
            filter_value,
            date_from=date_from,
            date_to=date_to,
            autorise_par=autorise_par,
            utilise_par=utilise_par
        )
        
        # Ajouter au tableau
        for avoir in avoirs:
            try:
                # Formatage des dates
                date_creation = avoir[10][:10] if avoir[10] else ''
                date_validite = avoir[11][:10] if avoir[11] else ''
                
                # Statut
                statut = avoir[12].upper() if avoir[12] else 'ACTIF'
                
                # Montants
                montant = avoir[8] or 0
                montant_utilise = avoir[19] if len(avoir) > 19 else 0
                montant_restant = avoir[20] if len(avoir) > 20 else montant
                
                # Qui a utilise (utilisateur_validation) / qui a autorise le forcage
                utilise_par_val = avoir[15] if (len(avoir) > 15 and avoir[15]) else ''
                autorise_par_val = avoir[24] if (len(avoir) > 24 and avoir[24]) else ''
                # Commentaire (motif de blocage OU de suppression, stocke dans
                # commentaire_blocage, index 25)
                commentaire_val = avoir[25] if (len(avoir) > 25 and avoir[25]) else ''
                
                # Colonne "Parent" : numero de l'avoir dont celui-ci depend.
                # On resout via l'id de l'avoir courant (avoir[0], TOUJOURS la 1re
                # colonne) avec une jointure, pour ne dependre d'aucun autre index.
                est_enfant = avoir[23] if len(avoir) > 23 else False
                parent_indicator = ''
                try:
                    row = self.avoir_manager.db.cursor.execute(
                        """SELECT p.numero_avoir
                           FROM avoirs c
                           LEFT JOIN avoirs p ON c.avoir_parent_id = p.id
                           WHERE c.id = ?""",
                        (avoir[0],)
                    ).fetchone()
                    parent_indicator = row[0] if (row and row[0]) else ''
                except Exception as e:
                    print(f"   (parent introuvable pour avoir id={avoir[0]}: {e})")
                    parent_indicator = ''
                
                # Tag selon statut
                tag = 'actif'
                if statut == 'EXPIRE':
                    tag = 'expire'
                elif statut == 'UTILISE':
                    tag = 'utilise'
                elif statut == 'UTILISE_PARTIELLEMENT':
                    tag = 'partiel'
                elif statut == 'ANNULE':
                    tag = 'annule'
                elif statut == 'SUPPRIME':
                    tag = 'supprime'
                
                if est_enfant:
                    tag = 'enfant'
                
                self.avoirs_tree.insert('', 'end', values=(
                    avoir[1],  # numero_avoir
                    f"{avoir[2]} - {avoir[3]}",  # client
                    avoir[4] or '',  # email
                    self.format_montant_xpf(montant),
                    self.format_montant_xpf(montant_utilise or 0),
                    self.format_montant_xpf(montant_restant or 0),
                    date_creation,
                    date_validite,
                    statut,
                    autorise_par_val,  # Autorise par (forcage)
                    utilise_par_val,   # Utilise par
                    parent_indicator,
                    commentaire_val    # Commentaire (blocage / suppression)
                ), tags=(tag,))
            except Exception as e:
                print(f"Erreur affichage avoir {avoir[1] if len(avoir) > 1 else '?'}: {e}")
                continue
        
        self.update_status(f"{len(avoirs)} avoir(s) affiche(s)")

    def show_avoirs_context_menu(self, event):
        """Menu contextuel (clic droit) sur le tableau des avoirs.

        Reserve au super_user (le bind n'est pose que pour ce role) : propose de
        reimprimer le PDF d'un avoir qui n'a pas encore ete utilise.
        """
        # Selectionner la ligne sous le curseur avant d'ouvrir le menu
        row_id = self.avoirs_tree.identify_row(event.y)
        if not row_id:
            return
        self.avoirs_tree.selection_set(row_id)
        self.avoirs_tree.focus(row_id)

        menu = tk.Menu(self.avoirs_tree, tearoff=0)
        menu.add_command(label="Reimprimer le PDF", command=self.reprint_avoir_pdf)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def reprint_avoir_pdf(self, numero_avoir=None):
        """Regenere et enregistre le PDF d'un avoir NON UTILISE (super_user).

        - Verifie le role et l'eligibilite (montant utilise = 0, avoir ni annule
          ni supprime).
        - Reconstruit les donnees du PDF depuis la base en conservant les dates
          d'ORIGINE (pour ne pas reediter une validite prolongee).
        - Demande ou enregistrer le fichier sur le poste, le genere et l'ouvre.

        Args:
            numero_avoir: Numero de l'avoir a reimprimer. Si None, on prend
                l'avoir actuellement selectionne dans le tableau.
        """
        # Securite : super_user uniquement
        if self.user[4] != USER_ROLES['SUPER_USER']:
            messagebox.showwarning(
                "Acces refuse",
                "Seul un super utilisateur peut reimprimer un avoir."
            )
            return

        # A defaut de numero fourni, on prend la selection du tableau
        if not numero_avoir:
            selection = self.avoirs_tree.selection()
            if not selection:
                messagebox.showinfo(
                    "Reimpression", "Selectionnez d'abord un avoir dans le tableau."
                )
                return
            numero_avoir = self.avoirs_tree.item(selection[0])['values'][0]

        # Recuperer l'avoir complet
        try:
            details = self.avoir_manager.get_avoir_details(numero_avoir)
        except Exception as e:
            messagebox.showerror(
                "Erreur", f"Impossible de charger l'avoir {numero_avoir} :\n{e}"
            )
            return
        if not details or not details.get('avoir'):
            messagebox.showerror("Erreur", f"Avoir {numero_avoir} introuvable.")
            return

        avoir = details['avoir']
        statut = (avoir[12] or '').lower()
        montant_utilise = avoir[19] if (len(avoir) > 19 and avoir[19] is not None) else 0

        # Eligibilite : uniquement les avoirs jamais entames (montant utilise = 0)
        # et ni annules ni supprimes.
        if montant_utilise and float(montant_utilise) > 0:
            messagebox.showwarning(
                "Reimpression impossible",
                f"L'avoir {avoir[1]} a deja ete utilise (partiellement ou en totalite).\n"
                "Seuls les avoirs non utilises peuvent etre reimprimes."
            )
            return
        if statut in (AVOIR_STATUS['ANNULE'], AVOIR_STATUS['SUPPRIME']):
            messagebox.showwarning(
                "Reimpression impossible",
                f"L'avoir {avoir[1]} est {statut}. Il ne peut pas etre reimprime."
            )
            return

        # Reconstruire les donnees du PDF a partir de la base
        est_residu = (bool(avoir[23]) if len(avoir) > 23 else False) or (
            bool(avoir[22]) if len(avoir) > 22 else False
        )
        pdf_data = {
            'numero_client': avoir[2] or '',
            'nom_client': avoir[3] or '',
            'email_client': avoir[4] or '',
            'numero_facture': avoir[5] or '',
            'date_facture': avoir[6] or '',
            'montant': avoir[8] or 0,
            'numero_facture_avoir': avoir[9] or '',
            # Dates d'ORIGINE (surtout pas la date du jour) pour ne pas reediter
            # une validite prolongee sur le papier.
            'date_creation': avoir[10] or '',
            'date_validite': avoir[11] or '',
            'est_residu': est_residu,
        }
        # Pour un residu : reference et montant de l'avoir parent
        if est_residu:
            parent = self.avoir_manager.get_avoir_parent(avoir[0])
            pdf_data['avoir_parent_numero'] = parent[1] if parent else ''
            pdf_data['avoir_parent_montant'] = parent[8] if parent else None

        # Demander ou enregistrer le PDF sur le poste
        nom_defaut = f"avoir_{str(avoir[1]).replace('/', '_')}.pdf"
        save_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF de l'avoir",
            defaultextension=".pdf",
            initialfile=nom_defaut,
            filetypes=[("Fichier PDF", "*.pdf")]
        )
        if not save_path:
            return  # Annule par l'utilisateur

        # Generer le PDF a l'emplacement choisi. On conserve le createur d'ORIGINE
        # de l'avoir sur le document (avoir[14]), et non le super_user qui reimprime.
        try:
            createur = avoir[14] or self.user[1]
            pdf_creator = PDFCreator()
            success_pdf, pdf_result = pdf_creator.generate(
                avoir[1], pdf_data, createur, output_path=save_path
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la generation du PDF :\n{e}")
            return

        if success_pdf:
            try:
                self.avoir_manager.db.add_log(
                    self.user[1], "REIMPRESSION_AVOIR",
                    f"Reimpression PDF de l'avoir {avoir[1]} -> {pdf_result}"
                )
            except Exception:
                pass
            self.update_status(f"PDF de l'avoir {avoir[1]} enregistre")
            messagebox.showinfo(
                "PDF reimprime",
                f"Le PDF de l'avoir {avoir[1]} a ete enregistre :\n{pdf_result}"
            )
        else:
            messagebox.showerror(
                "Erreur", f"Le PDF n'a pas pu etre genere :\n{pdf_result}"
            )

    def show_avoir_details(self, event):
        """Affiche les details d'un avoir avec historique"""
        selection = self.avoirs_tree.selection()
        if not selection:
            return
        
        item = self.avoirs_tree.item(selection[0])
        numero_avoir = item['values'][0]
        
        # Fenetre de details
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Details de l'avoir {numero_avoir}")
        details_window.geometry("800x650")
        details_window.transient(self.root)
        details_window.grab_set()
        
        # Centrer la fenetre
        details_window.update_idletasks()
        x = (details_window.winfo_screenwidth() // 2) - 400
        y = (details_window.winfo_screenheight() // 2) - 325
        details_window.geometry(f'+{x}+{y}')
        
        # Recuperer les details complets (garde anti "fenetre vide")
        try:
            details = self.avoir_manager.get_avoir_details(numero_avoir)
        except Exception as e:
            import traceback
            traceback.print_exc()
            tk.Label(
                details_window,
                text=f"Erreur lors du chargement des details de l'avoir {numero_avoir} :\n{e}",
                bg='white', fg=self.colors['error'], font=('Segoe UI', 11),
                justify='left', wraplength=740
            ).pack(padx=20, pady=20)
            return
        
        if not details:
            tk.Label(
                details_window,
                text=f"Aucun detail trouve pour l'avoir {numero_avoir}.",
                bg='white', fg=self.colors['text_primary'], font=('Segoe UI', 12)
            ).pack(padx=20, pady=20)
            return
        
        if details:
            # Creer l'interface des details
            notebook = ttk.Notebook(details_window, style='Modern.TNotebook')
            notebook.pack(fill='both', expand=True, padx=10, pady=10)
            
            avoir = details['avoir']
            statut = avoir[12]

            # Libelle lisible du statut
            statut_labels = {
                AVOIR_STATUS['ACTIF']: 'Actif',
                AVOIR_STATUS['UTILISE']: 'Utilise',
                AVOIR_STATUS.get('UTILISE_PARTIELLEMENT', 'utilise_partiellement'): 'Utilise partiellement',
                AVOIR_STATUS['EXPIRE']: 'Expire',
                AVOIR_STATUS['ANNULE']: 'Annule',
                AVOIR_STATUS['SUPPRIME']: 'Supprime',
                AVOIR_STATUS['BLOQUE']: 'Bloque',
            }
            statut_label = statut_labels.get(statut, statut)

            # Couleur du badge selon le statut
            statut_couleurs = {
                AVOIR_STATUS['ACTIF']: self.colors['success'],
                AVOIR_STATUS['UTILISE']: self.colors['info'],
                AVOIR_STATUS.get('UTILISE_PARTIELLEMENT', 'utilise_partiellement'): self.colors['warning'],
                AVOIR_STATUS['EXPIRE']: self.colors['warning'],
                AVOIR_STATUS['ANNULE']: self.colors['error'],
                AVOIR_STATUS['SUPPRIME']: self.colors['error'],
                AVOIR_STATUS['BLOQUE']: '#c62828',
            }
            badge_bg = statut_couleurs.get(statut, self.colors['text_secondary'])

            def _fdate(v):
                if not v:
                    return "-"
                s = str(v)[:10]
                if len(s) == 10 and s[4] == '-' and s[7] == '-':
                    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
                return s

            # ═══════════════════════════════════════════════════════════════
            # ONGLET INFORMATIONS (design "cartes")
            # ═══════════════════════════════════════════════════════════════
            info_frame = tk.Frame(notebook, bg=self.colors['hover'])
            notebook.add(info_frame, text='Informations')

            # Zone defilante (le contenu peut depasser la hauteur de la fenetre)
            info_canvas = tk.Canvas(info_frame, bg=self.colors['hover'], highlightthickness=0)
            info_scroll = ttk.Scrollbar(info_frame, orient='vertical', command=info_canvas.yview)
            info_body = tk.Frame(info_canvas, bg=self.colors['hover'])
            info_body.bind(
                '<Configure>',
                lambda e: info_canvas.configure(scrollregion=info_canvas.bbox('all'))
            )
            _info_win = info_canvas.create_window((0, 0), window=info_body, anchor='nw')
            info_canvas.bind('<Configure>', lambda e: info_canvas.itemconfig(_info_win, width=e.width))
            info_canvas.configure(yscrollcommand=info_scroll.set)
            info_canvas.pack(side='left', fill='both', expand=True)
            info_scroll.pack(side='right', fill='y')

            # Molette de la souris (active seulement au survol, fenetre modale)
            def _info_wheel(e):
                info_canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
            info_canvas.bind('<Enter>', lambda e: info_canvas.bind_all('<MouseWheel>', _info_wheel))
            info_canvas.bind('<Leave>', lambda e: info_canvas.unbind_all('<MouseWheel>'))

            # --- Helpers de mise en page ---
            def _make_card(titre, accent):
                card = tk.Frame(info_body, bg='white')
                card.pack(fill='x', padx=16, pady=(0, 12))
                head = tk.Frame(card, bg='white')
                head.pack(fill='x', padx=14, pady=(10, 2))
                tk.Label(head, bg=accent, width=2).pack(side='left', padx=(0, 8), fill='y')
                tk.Label(
                    head, text=titre, font=('Segoe UI', 11, 'bold'),
                    bg='white', fg=self.colors['text_primary']
                ).pack(side='left')
                tk.Frame(card, bg='#ececec', height=1).pack(fill='x', padx=14, pady=(4, 6))
                body = tk.Frame(card, bg='white')
                body.pack(fill='x', padx=16, pady=(0, 12))
                return body

            def _row(body, label, valeur, valeur_couleur=None, big=False, bold=False):
                r = tk.Frame(body, bg='white')
                r.pack(fill='x', pady=3)
                tk.Label(
                    r, text=label, font=('Segoe UI', 9),
                    bg='white', fg=self.colors['text_secondary'],
                    width=24, anchor='w'
                ).pack(side='left')
                tk.Label(
                    r, text=str(valeur),
                    font=('Segoe UI', 13 if big else 10, 'bold' if (bold or big) else 'normal'),
                    bg='white', fg=valeur_couleur or self.colors['text_primary'],
                    anchor='w', justify='left', wraplength=430
                ).pack(side='left', fill='x', expand=True)

            # --- Banniere : numero d'avoir + badge de statut ---
            banner = tk.Frame(info_body, bg=self.colors['secondary'])
            banner.pack(fill='x', padx=16, pady=(14, 12))
            tk.Label(
                banner, text=f"AVOIR  {avoir[1]}", font=('Segoe UI', 16, 'bold'),
                bg=self.colors['secondary'], fg=self.colors['primary']
            ).pack(side='left', padx=16, pady=14)
            tk.Label(
                banner, text=f"  {statut_label.upper()}  ", font=('Segoe UI', 10, 'bold'),
                bg=badge_bg, fg='white'
            ).pack(side='right', padx=16, pady=14)

            # --- Bouton "Reimprimer le PDF" : super_user + avoir non utilise ---
            _mt_utilise = avoir[19] if (len(avoir) > 19 and avoir[19] is not None) else 0
            _reimprimable = (not (_mt_utilise and float(_mt_utilise) > 0)) and \
                statut not in (AVOIR_STATUS['ANNULE'], AVOIR_STATUS['SUPPRIME'])
            if self.user[4] == USER_ROLES['SUPER_USER'] and _reimprimable:
                action_bar = tk.Frame(info_body, bg=self.colors['hover'])
                action_bar.pack(fill='x', padx=16, pady=(0, 12))
                reimpr_btn = tk.Button(
                    action_bar, text="Reimprimer le PDF",
                    command=lambda n=avoir[1]: self.reprint_avoir_pdf(n),
                    font=('Segoe UI', 10, 'bold'), bg=self.colors['info'], fg='white',
                    bd=0, cursor='hand2', padx=18, pady=8,
                    activebackground='#1976D2', activeforeground='white'
                )
                reimpr_btn.pack(side='right')

            # --- Carte : Type & Client ---
            _parent_id = avoir[22] if len(avoir) > 22 else None
            _est_enfant = (bool(avoir[23]) if len(avoir) > 23 else False) or bool(_parent_id)
            c_client = _make_card("Type & client", self.colors['primary'])
            if _est_enfant:
                _row(c_client, "Type d'avoir", "Residu (avoir enfant)")
                _parent = self.avoir_manager.get_avoir_parent(avoir[0])
                if _parent:
                    _row(c_client, "Avoir parent", _parent[1], valeur_couleur=self.colors['info'])
                    _row(c_client, "Montant avoir parent", self.format_montant_xpf(_parent[8]))
                else:
                    _row(c_client, "Avoir parent", "introuvable")
            else:
                _row(c_client, "Type d'avoir", "Retour marchandise")
            _row(c_client, "Numero client", avoir[2] or "-")
            _row(c_client, "Nom", avoir[3] or "-")
            _row(c_client, "Email", avoir[4] or "-")

            # --- Carte : Montants ---
            c_montant = _make_card("Montants", self.colors['success'])
            _row(c_montant, "Montant initial", self.format_montant_xpf(avoir[8]), big=True)
            _row(c_montant, "Deja utilise", self.format_montant_xpf(avoir[19] or 0))
            _restant = avoir[20] if avoir[20] is not None else avoir[8]
            _restant_couleur = self.colors['success'] if (_restant and float(_restant) > 0) else self.colors['text_secondary']
            _row(c_montant, "Montant restant", self.format_montant_xpf(_restant),
                 valeur_couleur=_restant_couleur, bold=True)

            # --- Carte : Facture & dates ---
            c_dates = _make_card("Facture & dates", self.colors['info'])
            _row(c_dates, "Facture d'achat", avoir[5] or "-")
            _row(c_dates, "Date facture achat", _fdate(avoir[6]))
            if avoir[9]:
                _row(c_dates, "N facture avoir", avoir[9])
            _row(c_dates, "Cree le", _fdate(avoir[10]))
            _row(c_dates, "Valide jusqu'au", _fdate(avoir[11]))
            if avoir[13]:
                _row(c_dates, "Utilise le", _fdate(avoir[13]))
            if avoir[21]:
                _row(c_dates, "Facture d'utilisation", avoir[21])

            # --- Carte : Suivi ---
            c_suivi = _make_card("Suivi", self.colors['text_secondary'])
            _row(c_suivi, "Cree par", avoir[14] or "-")
            if avoir[15]:
                _row(c_suivi, "Valide par", avoir[15])
            if len(avoir) > 24 and avoir[24]:
                _row(c_suivi, "Forcage autorise par", avoir[24], valeur_couleur=self.colors['warning'])

            # --- Carte : Blocage (si l'avoir est bloque) ---
            if statut == AVOIR_STATUS['BLOQUE']:
                c_bloc = _make_card("Blocage", self.colors['error'])
                if len(avoir) > 26 and avoir[26]:
                    _row(c_bloc, "Bloque par", avoir[26])
                if len(avoir) > 27 and avoir[27]:
                    _row(c_bloc, "Date de blocage", _fdate(avoir[27]))
                if len(avoir) > 25 and avoir[25]:
                    _row(c_bloc, "Commentaire", avoir[25], valeur_couleur=self.colors['error'])

            # --- Carte : Suppression (si l'avoir est supprime) ---
            # Memes colonnes que le blocage : commentaire_blocage = motif,
            # bloque_par = qui a supprime, date_blocage = quand.
            if statut == AVOIR_STATUS['SUPPRIME']:
                c_supp = _make_card("Suppression", self.colors['error'])
                if len(avoir) > 26 and avoir[26]:
                    _row(c_supp, "Supprime par", avoir[26])
                if len(avoir) > 27 and avoir[27]:
                    _row(c_supp, "Date de suppression", _fdate(avoir[27]))
                if len(avoir) > 25 and avoir[25]:
                    _row(c_supp, "Motif", avoir[25], valeur_couleur=self.colors['error'])

            # ═══════════════════════════════════════════════════════════════
            # ONGLET HISTORIQUE (tableau)
            # ═══════════════════════════════════════════════════════════════
            if isinstance(details, dict) and details.get('historique'):
                hist_frame = tk.Frame(notebook, bg=self.colors['hover'])
                notebook.add(hist_frame, text='Historique')

                # En-tete
                hist_head = tk.Frame(hist_frame, bg=self.colors['secondary'])
                hist_head.pack(fill='x')
                tk.Label(
                    hist_head,
                    text=f"Historique d'utilisation  -  {len(details['historique'])} operation(s)",
                    font=('Segoe UI', 12, 'bold'),
                    bg=self.colors['secondary'], fg=self.colors['primary']
                ).pack(anchor='w', padx=16, pady=12)

                # Tableau des operations
                hist_cols = ('Date', 'Montant utilise', 'Facture', 'Utilisateur', 'Type')
                hist_tree = ttk.Treeview(
                    hist_frame, columns=hist_cols, show='headings', style='Modern.Treeview'
                )
                hist_widths = {
                    'Date': 130, 'Montant utilise': 130, 'Facture': 140,
                    'Utilisateur': 150, 'Type': 100
                }
                for c in hist_cols:
                    hist_tree.heading(c, text=c)
                    hist_tree.column(c, width=hist_widths[c], anchor='w')

                # entry: 0 id, 1 avoir_id, 2 numero_avoir, 3 date_utilisation,
                #        4 montant_utilise, 5 numero_facture, 6 utilisateur,
                #        7 type_utilisation, 8 avoir_enfant_id
                for entry in details['historique']:
                    try:
                        d_val = _fdate(entry[3]) if len(entry) > 3 else '-'
                        m_val = self.format_montant_xpf(entry[4]) if len(entry) > 4 else '-'
                        f_val = entry[5] if (len(entry) > 5 and entry[5]) else '-'
                        u_val = entry[6] if (len(entry) > 6 and entry[6]) else '-'
                        t_val = (str(entry[7]).capitalize() if (len(entry) > 7 and entry[7]) else '-')
                        hist_tree.insert('', 'end', values=(d_val, m_val, f_val, u_val, t_val))
                    except Exception as e:
                        print(f"(info) entree d'historique illisible: {e}")
                        hist_tree.insert('', 'end', values=(str(entry), '', '', '', ''))

                hist_y = ttk.Scrollbar(hist_frame, orient='vertical', command=hist_tree.yview)
                hist_tree.configure(yscrollcommand=hist_y.set)
                hist_tree.pack(side='left', fill='both', expand=True, padx=(12, 0), pady=12)
                hist_y.pack(side='right', fill='y', pady=12)

            # Onglet avoirs enfants si applicable
            if isinstance(details, dict) and details.get('avoirs_enfants'):
                enfants_frame = tk.Frame(notebook, bg='white')
                notebook.add(enfants_frame, text='Avoirs enfants')
                # Afficher les avoirs enfants
                enfants_text = tk.Text(enfants_frame, wrap='word', bg='white', fg=self.colors['text_primary'], font=('Segoe UI', 10))
                enfants_text.pack(fill='both', expand=True, padx=10, pady=10)
                enfants_text.insert('end', f"Avoirs enfants de l'avoir {numero_avoir}:\n\n")
                for enfant in details['avoirs_enfants']:
                    enfants_text.insert('end', f"- {enfant}\n")
            
            # Onglet Actions (super_user ET comptabilite : tous deux peuvent supprimer)
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['COMPTABILITE']]:
                actions_frame = tk.Frame(notebook, bg='white')
                notebook.add(actions_frame, text='Actions Admin')
                
                # Titre
                tk.Label(
                    actions_frame,
                    text="Actions administrateur",
                    font=('Segoe UI', 14, 'bold'),
                    bg='white',
                    fg=self.colors['text_primary']
                ).pack(pady=(20, 10))
                
                tk.Label(
                    actions_frame,
                    text="Ces actions sont irreversibles. Utilisez-les avec precaution.",
                    font=('Segoe UI', 10),
                    bg='white',
                    fg='#f44336'
                ).pack(pady=(0, 20))
                
                # Champ motif
                tk.Label(
                    actions_frame,
                    text="Motif (obligatoire):",
                    font=('Segoe UI', 10),
                    bg='white'
                ).pack(anchor='w', padx=50)
                
                motif_entry = tk.Entry(
                    actions_frame,
                    font=('Segoe UI', 11),
                    width=50,
                    bd=1,
                    relief='solid'
                )
                motif_entry.pack(pady=(5, 30), padx=50)
                
                # Boutons d'action
                buttons_frame = tk.Frame(actions_frame, bg='white')
                buttons_frame.pack(pady=20)
                
                def annuler_avoir():
                    motif = motif_entry.get().strip()
                    if not motif:
                        messagebox.showerror("Erreur", "Le motif est obligatoire")
                        return
                    
                    if messagebox.askyesno(
                        "Confirmation ANNULATION",
                        f"Voulez-vous vraiment ANNULER l'avoir {numero_avoir}?\n\n"
                        f"Le montant sera remis a 0 et l'avoir ne pourra plus etre utilise.\n"
                        f"Cette action est irreversible.",
                        icon='warning'
                    ):
                        success, message = self.avoir_manager.cancel_avoir(
                            numero_avoir,
                            self.user[1],
                            motif
                        )
                        if success:
                            messagebox.showinfo("Succes", message)
                            details_window.destroy()
                            self.refresh_avoirs_list()
                        else:
                            messagebox.showerror("Erreur", message)
                
                def supprimer_avoir():
                    motif = motif_entry.get().strip()
                    if not motif:
                        messagebox.showerror("Erreur", "Le motif est obligatoire")
                        return
                    
                    if messagebox.askyesno(
                        "Confirmation SUPPRESSION",
                        f"Voulez-vous vraiment SUPPRIMER l'avoir {numero_avoir}?\n\n"
                        f"L'avoir ne sera plus visible dans les listes.\n"
                        f"Cette action est irreversible.",
                        icon='warning'
                    ):
                        success, message = self.avoir_manager.delete_avoir(
                            numero_avoir, 
                            self.user[1], 
                            motif
                        )
                        if success:
                            messagebox.showinfo("Succes", message)
                            details_window.destroy()
                            self.refresh_avoirs_list()
                        else:
                            messagebox.showerror("Erreur", message)
                
                tk.Button(
                    buttons_frame,
                    text="Annuler l'avoir",
                    command=annuler_avoir,
                    font=('Segoe UI', 10, 'bold'),
                    bg=self.colors['warning'],
                    fg='white',
                    bd=0,
                    cursor='hand2',
                    padx=20,
                    pady=10
                ).pack(side='left', padx=10)
                
                tk.Button(
                    buttons_frame,
                    text="Supprimer l'avoir",
                    command=supprimer_avoir,
                    font=('Segoe UI', 10, 'bold'),
                    bg='#f44336',
                    fg='white',
                    bd=0,
                    cursor='hand2',
                    padx=20,
                    pady=10
                ).pack(side='left', padx=10)
            
            # Onglet Blocage / Deblocage (super_user, responsable, comptabilite)
            if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]:
                blocage_frame = tk.Frame(notebook, bg='white')
                notebook.add(blocage_frame, text='Blocage')
                
                avoir_tuple = details['avoir']
                statut_actuel = avoir_tuple[12]
                
                tk.Label(
                    blocage_frame,
                    text="Blocage / Deblocage de l'avoir",
                    font=('Segoe UI', 14, 'bold'),
                    bg='white',
                    fg=self.colors['text_primary']
                ).pack(pady=(20, 10))
                
                if statut_actuel == AVOIR_STATUS['BLOQUE']:
                    commentaire_blocage = avoir_tuple[25] if len(avoir_tuple) > 25 else ''
                    bloque_par = avoir_tuple[26] if len(avoir_tuple) > 26 else ''
                    
                    tk.Label(
                        blocage_frame,
                        text="Cet avoir est actuellement BLOQUE.",
                        font=('Segoe UI', 11, 'bold'),
                        bg='white', fg='#c62828'
                    ).pack(pady=(0, 5))
                    tk.Label(
                        blocage_frame,
                        text=f"Bloque par : {bloque_par or 'N/A'}",
                        font=('Segoe UI', 10), bg='white'
                    ).pack()
                    tk.Label(
                        blocage_frame,
                        text=f"Commentaire : {commentaire_blocage or 'N/A'}",
                        font=('Segoe UI', 10), bg='white',
                        wraplength=500, justify='left'
                    ).pack(pady=(0, 20))
                    
                    def debloquer_avoir():
                        if messagebox.askyesno(
                            "Confirmation",
                            f"Voulez-vous DEBLOQUER l'avoir {numero_avoir}?\n\n"
                            f"Le statut sera recalcule automatiquement (actif ou expire)."
                        ):
                            success, message = self.avoir_manager.unblock_avoir(
                                numero_avoir, self.user[1]
                            )
                            if success:
                                messagebox.showinfo("Succes", message)
                                details_window.destroy()
                                self.refresh_avoirs_list()
                            else:
                                messagebox.showerror("Erreur", message)
                    
                    tk.Button(
                        blocage_frame,
                        text="Debloquer l'avoir",
                        command=debloquer_avoir,
                        font=('Segoe UI', 10, 'bold'),
                        bg='#4CAF50', fg='white',
                        bd=0, cursor='hand2', padx=20, pady=10
                    ).pack(pady=10)
                else:
                    tk.Label(
                        blocage_frame,
                        text="Bloquer un avoir empeche son utilisation en caisse.\n"
                             "Le client devra alors passer a la comptabilite.",
                        font=('Segoe UI', 10), bg='white', fg='#555555',
                        justify='center'
                    ).pack(pady=(0, 15))
                    tk.Label(
                        blocage_frame,
                        text="Commentaire de blocage (obligatoire) :",
                        font=('Segoe UI', 10), bg='white'
                    ).pack(anchor='w', padx=50)
                    commentaire_blocage_entry = tk.Entry(
                        blocage_frame, font=('Segoe UI', 11), width=50, bd=1, relief='solid'
                    )
                    commentaire_blocage_entry.pack(pady=(5, 25), padx=50)
                    
                    def bloquer_avoir():
                        commentaire = commentaire_blocage_entry.get().strip()
                        if not commentaire:
                            messagebox.showerror("Erreur", "Le commentaire de blocage est obligatoire")
                            return
                        if messagebox.askyesno(
                            "Confirmation",
                            f"Voulez-vous BLOQUER l'avoir {numero_avoir}?\n\n"
                            f"Il ne pourra plus etre utilise tant qu'il n'est pas debloque."
                        ):
                            success, message = self.avoir_manager.block_avoir(
                                numero_avoir, self.user[1], commentaire
                            )
                            if success:
                                messagebox.showinfo("Succes", message)
                                details_window.destroy()
                                self.refresh_avoirs_list()
                            else:
                                messagebox.showerror("Erreur", message)
                    
                    tk.Button(
                        blocage_frame,
                        text="Bloquer l'avoir",
                        command=bloquer_avoir,
                        font=('Segoe UI', 10, 'bold'),
                        bg='#9C27B0', fg='white',
                        bd=0, cursor='hand2', padx=20, pady=10
                    ).pack(pady=10)
    
    # Toutes les autres methodes restent identiques
    def show_anomalies(self):
        """
        Onglet Anomalies (super_user + comptabilite) : fait ressortir les
        clients ayant recu beaucoup d'avoirs sur une PERIODE choisie (plage de
        dates), avec filtres par type et par client. Double-clic sur un client
        = ses avoirs correspondant aux memes filtres.
        """
        if self.user[4] not in [USER_ROLES['SUPER_USER'], USER_ROLES['COMPTABILITE']]:
            messagebox.showerror(
                "Acces refuse",
                "Acces reserve au super administrateur et a la comptabilite."
            )
            return

        self.clear_content_frame()
        self.update_content_title("Anomalies clients")
        self.update_status("Analyse des anomalies...")

        self.anomalies_seuil = getattr(self, 'anomalies_seuil', 5)
        today = datetime.now()
        default_from = (today - timedelta(days=30)).strftime('%d/%m/%Y')
        default_to = today.strftime('%d/%m/%Y')

        white = self.colors['white']

        # ----- Ligne 1 : periode + seuil -----
        bar1 = tk.Frame(self.content_frame, bg=white)
        bar1.pack(fill='x', padx=20, pady=(0, 0))
        tk.Label(bar1, text="Periode  du", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=(20, 5), pady=(12, 4))
        self.anomalies_from_entry = tk.Entry(bar1, width=11, font=('Segoe UI', 10),
                                             bd=1, relief='solid')
        self.anomalies_from_entry.insert(0, default_from)
        self.anomalies_from_entry.pack(side='left', pady=(12, 4))
        tk.Label(bar1, text="au", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=5, pady=(12, 4))
        self.anomalies_to_entry = tk.Entry(bar1, width=11, font=('Segoe UI', 10),
                                           bd=1, relief='solid')
        self.anomalies_to_entry.insert(0, default_to)
        self.anomalies_to_entry.pack(side='left', pady=(12, 4))
        tk.Label(bar1, text="(jj/mm/aaaa)", font=('Segoe UI', 8), bg=white,
                 fg=self.colors['text_secondary']).pack(side='left', padx=5, pady=(12, 4))
        tk.Label(bar1, text="    Seuil : au moins", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=(15, 5), pady=(12, 4))
        self.anomalies_seuil_entry = tk.Entry(bar1, width=4, font=('Segoe UI', 10),
                                              bd=1, relief='solid')
        self.anomalies_seuil_entry.insert(0, str(self.anomalies_seuil))
        self.anomalies_seuil_entry.pack(side='left', pady=(12, 4))
        tk.Label(bar1, text="avoirs", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=5, pady=(12, 4))

        # ----- Ligne 2 : type + client + boutons -----
        bar2 = tk.Frame(self.content_frame, bg=white)
        bar2.pack(fill='x', padx=20, pady=(0, 8))
        tk.Label(bar2, text="Type :", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=(20, 5), pady=(4, 12))
        self.anomalies_type = ttk.Combobox(
            bar2, values=['Tous', 'Hors residus', 'Residus uniquement'],
            width=18, state='readonly'
        )
        self.anomalies_type.set('Tous')
        self.anomalies_type.pack(side='left', pady=(4, 12))
        tk.Label(bar2, text="    N client :", font=('Segoe UI', 10), bg=white
                 ).pack(side='left', padx=(15, 5), pady=(4, 12))
        self.anomalies_client_entry = tk.Entry(bar2, width=12, font=('Segoe UI', 10),
                                               bd=1, relief='solid')
        self.anomalies_client_entry.pack(side='left', pady=(4, 12))
        tk.Button(bar2, text=" Analyser", command=self.refresh_anomalies, font=('Segoe UI', 10),
                  bg=self.colors['primary'], fg=self.colors['secondary'], bd=0,
                  cursor='hand2', padx=15).pack(side='left', padx=(15, 5), pady=(4, 12))
        tk.Button(bar2, text=" Reinitialiser", command=self.reset_anomalies_filters,
                  font=('Segoe UI', 10), bg=self.colors['hover'],
                  fg=self.colors['text_primary'], bd=0, cursor='hand2',
                  padx=15).pack(side='left', padx=5, pady=(4, 12))

        # Bandeau d'information (periode/type analyses) + aide
        self.anomalies_period_label = tk.Label(
            self.content_frame, text="", font=('Segoe UI', 9, 'bold'),
            bg=self.colors['bg_light'], fg=self.colors['text_primary']
        )
        self.anomalies_period_label.pack(anchor='w', padx=25, pady=(0, 2))
        tk.Label(
            self.content_frame,
            text="Double-cliquez sur un client pour voir ses avoirs correspondant aux filtres.",
            font=('Segoe UI', 9, 'italic'), bg=self.colors['bg_light'],
            fg=self.colors['text_secondary']
        ).pack(anchor='w', padx=25, pady=(0, 6))

        table_frame = tk.Frame(self.content_frame, bg=white)
        table_frame.pack(fill='both', expand=True, padx=20)

        columns = ('N Client', 'Nom', 'Nb avoirs', 'Montant total', 'Premier', 'Dernier')
        self.anomalies_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                           height=20, style='Modern.Treeview')
        widths = {'N Client': 110, 'Nom': 250, 'Nb avoirs': 90,
                  'Montant total': 140, 'Premier': 110, 'Dernier': 110}
        aligns = {'Nb avoirs': 'center', 'Montant total': 'e',
                  'Premier': 'center', 'Dernier': 'center'}
        for col in columns:
            self.anomalies_tree.heading(col, text=col)
            self.anomalies_tree.column(col, width=widths.get(col, 110),
                                       anchor=aligns.get(col, 'w'))

        ysb = ttk.Scrollbar(table_frame, orient='vertical', command=self.anomalies_tree.yview)
        self.anomalies_tree.configure(yscrollcommand=ysb.set)
        self.anomalies_tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')

        self.anomalies_tree.tag_configure('alerte', background='#ffcdd2')
        self.anomalies_tree.tag_configure('attention', background='#fff3e0')

        self.anomalies_tree.bind('<Double-Button-1>', self.show_client_avoirs_6mois)

        self.refresh_anomalies()
        self.update_status("Analyse des anomalies terminee")

    def _anomalies_to_iso(self, s, default_iso):
        """Convertit une date jj/mm/aaaa (ou aaaa-mm-jj) en 'YYYY-MM-DD'."""
        s = (s or '').strip()
        if not s:
            return default_iso
        for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
            try:
                return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
            except Exception:
                continue
        return default_iso

    def reset_anomalies_filters(self):
        """Remet les filtres d'anomalies par defaut (30 derniers jours)."""
        try:
            today = datetime.now()
            self.anomalies_from_entry.delete(0, 'end')
            self.anomalies_from_entry.insert(0, (today - timedelta(days=30)).strftime('%d/%m/%Y'))
            self.anomalies_to_entry.delete(0, 'end')
            self.anomalies_to_entry.insert(0, today.strftime('%d/%m/%Y'))
            self.anomalies_seuil_entry.delete(0, 'end')
            self.anomalies_seuil_entry.insert(0, '5')
            self.anomalies_type.set('Tous')
            self.anomalies_client_entry.delete(0, 'end')
        except Exception as e:
            print(f"Erreur reinitialisation anomalies: {e}")
        self.refresh_anomalies()

    def refresh_anomalies(self):
        """(Re)calcule et affiche la liste des clients en anomalie sur la periode."""
        if not hasattr(self, 'anomalies_tree'):
            return
        for item in self.anomalies_tree.get_children():
            self.anomalies_tree.delete(item)

        today = datetime.now()
        default_from = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        default_to = today.strftime('%Y-%m-%d')
        date_from = self._anomalies_to_iso(self.anomalies_from_entry.get(), default_from)
        date_to = self._anomalies_to_iso(self.anomalies_to_entry.get(), default_to)
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        self.anomalies_date_from = date_from
        self.anomalies_date_to = date_to

        try:
            seuil = int(self.anomalies_seuil_entry.get().strip())
        except Exception:
            seuil = 5
        self.anomalies_seuil = max(1, seuil)

        type_map = {'Tous': 'tous', 'Hors residus': 'hors_residus',
                    'Residus uniquement': 'residus'}
        type_avoir = 'tous'
        try:
            if getattr(self, 'anomalies_type', None) is not None:
                type_avoir = type_map.get(self.anomalies_type.get(), 'tous')
        except Exception:
            type_avoir = 'tous'
        self.anomalies_type_value = type_avoir

        numero_client_filtre = ''
        try:
            if getattr(self, 'anomalies_client_entry', None) is not None:
                numero_client_filtre = self.anomalies_client_entry.get().strip()
        except Exception:
            numero_client_filtre = ''

        clients = self.avoir_manager.get_clients_anomalies(
            date_from=date_from, date_to=date_to,
            seuil=self.anomalies_seuil, type_avoir=type_avoir,
            numero_client=(numero_client_filtre or None)
        )

        def _fdate(v):
            s = str(v)[:10] if v else ''
            if len(s) == 10 and s[4] == '-':
                return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
            return s

        for c in clients:
            numero_client, nom_client, nb, total, premiere, derniere = c
            tag = 'alerte' if nb >= self.anomalies_seuil * 2 else 'attention'
            self.anomalies_tree.insert('', 'end', values=(
                numero_client, nom_client or '', nb,
                self.format_montant_xpf(total or 0),
                _fdate(premiere), _fdate(derniere)
            ), tags=(tag,))

        # Bandeau d'information
        type_lib = self.anomalies_type.get() if getattr(self, 'anomalies_type', None) else 'Tous'
        if hasattr(self, 'anomalies_period_label'):
            info = (f"Periode : du {_fdate(date_from)} au {_fdate(date_to)}   |   "
                    f"Type : {type_lib}   |   {len(clients)} client(s) affiche(s)")
            if numero_client_filtre:
                info += f"   |   filtre client {numero_client_filtre} (seuil ignore)"
            self.anomalies_period_label.config(text=info)

        if numero_client_filtre:
            self.update_status(f"Client {numero_client_filtre} : {len(clients)} ligne(s)")
        else:
            self.update_status(f"{len(clients)} client(s) en anomalie sur la periode")

    def show_client_avoirs_6mois(self, event):
        """Double-clic sur un client : ses avoirs correspondant AUX FILTRES
        (plage de dates + type) de l'analyse. Le total affiche correspond donc
        exactement au « Nb avoirs » du tableau (memes criteres, supprimes exclus).
        """
        selection = self.anomalies_tree.selection()
        if not selection:
            return
        item = self.anomalies_tree.item(selection[0])
        numero_client = item['values'][0]
        nom_client = item['values'][1] if len(item['values']) > 1 else ''

        # Memes filtres que l'analyse en cours
        date_from = getattr(self, 'anomalies_date_from',
                            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        date_to = getattr(self, 'anomalies_date_to', datetime.now().strftime('%Y-%m-%d'))
        type_avoir = getattr(self, 'anomalies_type_value', 'tous')

        def _fdate(v):
            s = str(v)[:10] if v else ''
            if len(s) == 10 and s[4] == '-':
                return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
            return s

        win = tk.Toplevel(self.root)
        win.title(f"Avoirs du client {numero_client}")
        win.geometry("920x600")
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win, text=f"Client {numero_client} - {nom_client}",
            font=('Segoe UI', 14, 'bold'), bg='white', fg=self.colors['text_primary']
        ).pack(fill='x', pady=(10, 0))
        type_lib = {'tous': 'Tous', 'hors_residus': 'Hors residus',
                    'residus': 'Residus uniquement'}.get(type_avoir, 'Tous')
        tk.Label(
            win,
            text=(f"Avoirs correspondant aux filtres  —  periode du {_fdate(date_from)} "
                  f"au {_fdate(date_to)}, type : {type_lib} (supprimes exclus)"),
            font=('Segoe UI', 9, 'italic'), bg='white', fg=self.colors['text_secondary']
        ).pack(fill='x', pady=(0, 10))

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        columns = ('N Avoir', 'Type', 'Date', 'Montant', 'Restant', 'Statut', 'N Facture', 'Cree par')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=22, style='Modern.Treeview')
        widths = {'N Avoir': 100, 'Type': 80, 'Date': 100, 'Montant': 110, 'Restant': 110,
                  'Statut': 140, 'N Facture': 120, 'Cree par': 110}
        aligns = {'Montant': 'e', 'Restant': 'e', 'Type': 'center',
                  'Date': 'center', 'Statut': 'center'}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 100), anchor=aligns.get(col, 'w'))

        ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side='left', fill='both', expand=True)
        ysb.pack(side='right', fill='y')

        avoirs = self.avoir_manager.get_avoirs_client_filtre(
            numero_client, date_from, date_to, type_avoir
        )

        for a in avoirs:
            numero_avoir, date_creation, montant, restant, statut, num_facture, cree_par, est_enfant = a
            type_label = 'Residu' if est_enfant else 'Avoir'
            tree.insert('', 'end', values=(
                numero_avoir, type_label, _fdate(date_creation),
                self.format_montant_xpf(montant or 0),
                self.format_montant_xpf(restant or 0),
                (statut or '').upper(), num_facture or '', cree_par or ''
            ))

        tk.Label(
            win,
            text=f"Total : {len(avoirs)} avoir(s) sur la periode  (= Nb avoirs du tableau)",
            font=('Segoe UI', 10, 'bold'), bg='white', fg=self.colors['text_primary']
        ).pack(pady=(0, 10))

    def show_logs(self):
        """Affiche les logs systeme (uniquement pour super_user et responsable)"""
        # Verifier les permissions
        if self.user[4] == USER_ROLES['VENDEUR']:
            messagebox.showerror("Acces refuse", "Vous n'avez pas acces aux logs systeme")
            return
        
        self.clear_content_frame()
        self.update_content_title("Logs systeme")
        self.update_status("Chargement des logs...")
        
        # Container principal
        main_container = tk.Frame(self.content_frame, bg=self.colors['white'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Titre et options
        header_frame = tk.Frame(main_container, bg=self.colors['white'])
        header_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(
            header_frame,
            text=" Historique des logs systeme",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['text_primary']
        ).pack(side='left')
        
        # Bouton de rafraichissement
        refresh_btn = tk.Button(
            header_frame,
            text=" Rafraichir",
            command=lambda: self.refresh_logs(),
            font=('Segoe UI', 10),
            bg=self.colors['info'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15,
            pady=5
        )
        refresh_btn.pack(side='right', padx=5)
        
        # Bouton d'export
        export_btn = tk.Button(
            header_frame,
            text=" Exporter",
            command=self.export_logs,
            font=('Segoe UI', 10),
            bg=self.colors['success'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15,
            pady=5
        )
        export_btn.pack(side='right', padx=5)
        
        # Tableau des logs
        columns = ('ID', 'Date/Heure', 'Utilisateur', 'Action', 'Details')
        self.logs_tree = ttk.Treeview(
            main_container,
            columns=columns,
            show='headings',
            height=25,
            style='Modern.Treeview'
        )
        
        # Configuration des colonnes
        column_widths = {
            'ID': 50,
            'Date/Heure': 150,
            'Utilisateur': 120,
            'Action': 200,
            'Details': 400
        }
        
        for col in columns:
            self.logs_tree.heading(col, text=col)
            self.logs_tree.column(col, width=column_widths.get(col, 100))
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(main_container, orient='vertical', command=self.logs_tree.yview)
        x_scrollbar = ttk.Scrollbar(main_container, orient='horizontal', command=self.logs_tree.xview)
        self.logs_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack
        self.logs_tree.pack(side='left', fill='both', expand=True)
        y_scrollbar.pack(side='right', fill='y')
        x_scrollbar.pack(side='bottom', fill='x')
        
        # Tags pour coloration selon le type d'action
        self.logs_tree.tag_configure('login', background='#e8f5e9')
        self.logs_tree.tag_configure('creation', background='#e3f2fd')
        self.logs_tree.tag_configure('validation', background='#fff3e0')
        self.logs_tree.tag_configure('error', background='#ffebee')
        self.logs_tree.tag_configure('warning', background='#fff9c4')
        self.logs_tree.tag_configure('partiel', background='#e1f5fe')
        
        # Charger les logs
        self.refresh_logs()
        self.update_status("Logs systeme charges")
    
    def refresh_logs(self):
        """Rafraichit la liste des logs"""
        # Effacer le tableau
        if hasattr(self, 'logs_tree'):
            for item in self.logs_tree.get_children():
                self.logs_tree.delete(item)
            
            # Recuperer les logs depuis la base
            try:
                logs = self.db.cursor.execute(
                    "SELECT * FROM logs ORDER BY id DESC LIMIT 500"
                ).fetchall()
                
                for log in logs:
                    # Determiner le tag selon l'action
                    action = log[3].upper() if log[3] else ''
                    tag = ''
                    if 'LOGIN' in action or 'LOGOUT' in action:
                        tag = 'login'
                    elif 'CREATION' in action or 'ADD' in action:
                        tag = 'creation'
                    elif 'VALIDATION' in action or 'UTILISATION_TOTALE' in action:
                        tag = 'validation'
                    elif 'PARTIELLE' in action:
                        tag = 'partiel'
                    elif 'ERREUR' in action or 'INTROUVABLE' in action:
                        tag = 'error'
                    elif 'TENTATIVE' in action or 'EXPIRE' in action:
                        tag = 'warning'
                    
                    self.logs_tree.insert('', 'end', values=(
                        log[0],  # ID
                        log[1],  # Timestamp
                        log[2],  # User
                        log[3],  # Action
                        log[4]   # Details
                    ), tags=(tag,))
                
                self.update_status(f"{len(logs)} logs affiches")
                
            except Exception as e:
                print(f"Erreur lors du chargement des logs: {e}")
                self.update_status("Erreur lors du chargement des logs")
    
    def show_user_management(self):
        """Interface de gestion des utilisateurs moderne optimisee"""
        if self.user[4] != USER_ROLES['SUPER_USER']:
            messagebox.showerror("Erreur", "Acces non autorise")
            return
        
        self.clear_content_frame()
        self.update_content_title("Gestion des utilisateurs")
        self.update_status("Chargement de la gestion des utilisateurs...")
        
        # Container principal
        main_container = tk.Frame(self.content_frame, bg=self.colors['bg_light'])
        main_container.pack(fill='both', expand=True)
        
        # Carte d'ajout d'utilisateur
        add_card = tk.Frame(main_container, bg=self.colors['white'], relief='flat')
        add_card.pack(fill='x', padx=20, pady=10)
        
        # Titre de la carte
        tk.Label(
            add_card,
            text=" Ajouter un utilisateur",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['primary']
        ).pack(anchor='w', padx=20, pady=(15, 10))
        
        # Import en masse via CSV + telechargement du modele
        # (reserve au super_user : tout cet ecran l'est deja).
        csv_btn_row = tk.Frame(add_card, bg=self.colors['white'])
        csv_btn_row.pack(anchor='w', padx=20, pady=(0, 10))
        tk.Button(
            csv_btn_row,
            text=" Importer des utilisateurs (CSV)",
            command=self.import_users_csv,
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['info'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15,
            pady=6
        ).pack(side='left')
        tk.Button(
            csv_btn_row,
            text=" Telecharger le modele CSV",
            command=self.download_user_csv_template,
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['secondary'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15,
            pady=6
        ).pack(side='left', padx=(10, 0))
        
        # Formulaire d'ajout optimise en 2 lignes
        form_frame = tk.Frame(add_card, bg=self.colors['white'])
        form_frame.pack(padx=30, pady=(0, 20))
        
        # Ligne 1 : Username et Email cote a cote
        row1_frame = tk.Frame(form_frame, bg=self.colors['white'])
        row1_frame.pack(fill='x', pady=5)
        
        # Username
        username_frame = tk.Frame(row1_frame, bg=self.colors['white'])
        username_frame.pack(side='left', padx=(0, 15))
        tk.Label(username_frame, text="Nom d'utilisateur:", font=('Segoe UI', 10), bg=self.colors['white']).pack(anchor='w')
        self.new_username = tk.Entry(username_frame, font=('Segoe UI', 10), width=25)
        self.new_username.pack()
        
        # Email
        email_frame = tk.Frame(row1_frame, bg=self.colors['white'])
        email_frame.pack(side='left')
        tk.Label(email_frame, text="Email:", font=('Segoe UI', 10), bg=self.colors['white']).pack(anchor='w')
        self.new_email = tk.Entry(email_frame, font=('Segoe UI', 10), width=25)
        self.new_email.pack()
        
        # Ligne 2 : Password et Role cote a cote
        row2_frame = tk.Frame(form_frame, bg=self.colors['white'])
        row2_frame.pack(fill='x', pady=5)
        
        # Password
        password_frame = tk.Frame(row2_frame, bg=self.colors['white'])
        password_frame.pack(side='left', padx=(0, 15))
        tk.Label(password_frame, text="Mot de passe:", font=('Segoe UI', 10), bg=self.colors['white']).pack(anchor='w')
        self.new_password = tk.Entry(password_frame, font=('Segoe UI', 10), width=25, show='•')
        self.new_password.pack()
        
        # Role
        role_frame = tk.Frame(row2_frame, bg=self.colors['white'])
        role_frame.pack(side='left')
        tk.Label(role_frame, text="Role:", font=('Segoe UI', 10), bg=self.colors['white']).pack(anchor='w')
        self.new_role = ttk.Combobox(
            role_frame,
            values=['vendeur', 'responsable', 'comptabilite', 'super_user'],
            width=23,
            state='readonly'
        )
        self.new_role.set('vendeur')
        self.new_role.pack()
        
        # Checkbox email
        self.send_credentials_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            form_frame,
            text=" Envoyer les identifiants par email",
            variable=self.send_credentials_var,
            font=('Segoe UI', 10),
            bg=self.colors['white']
        ).pack(pady=10)
        
        # Bouton d'ajout
        add_btn = tk.Button(
            form_frame,
            text="Ajouter l'utilisateur",
            command=self.add_user,
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['success'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=20,
            pady=10
        )
        add_btn.pack()
        
        # Liste des utilisateurs
        list_card = tk.Frame(main_container, bg=self.colors['white'], relief='flat')
        list_card.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Header de la liste
        header_frame = tk.Frame(list_card, bg=self.colors['white'])
        header_frame.pack(fill='x', padx=20, pady=15)
        
        tk.Label(
            header_frame,
            text=" Utilisateurs existants",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['primary']
        ).pack(side='left')
        
        # Boutons d'action
        action_frame = tk.Frame(header_frame, bg=self.colors['white'])
        action_frame.pack(side='right')
        
        tk.Button(
            action_frame,
            text=" Modifier",
            command=self.modify_user,
            font=('Segoe UI', 10),
            bg=self.colors['info'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15
        ).pack(side='left', padx=2)
        
        tk.Button(
            action_frame,
            text=" Supprimer",
            command=self.delete_user,
            font=('Segoe UI', 10),
            bg=self.colors['error'],
            fg=self.colors['white'],
            bd=0,
            cursor='hand2',
            padx=15
        ).pack(side='left', padx=2)
        
        # Tableau des utilisateurs
        columns = ('ID', 'Username', 'Email', 'Role', 'Date creation', 'Actif')
        self.users_tree = ttk.Treeview(
            list_card,
            columns=columns,
            show='headings',
            height=15,
            style='Modern.Treeview'
        )
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_card, orient='vertical', command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side='left', fill='both', expand=True, padx=(20, 0))
        scrollbar.pack(side='right', fill='y', padx=(0, 20))
        
        # Double-clic pour modifier
        self.users_tree.bind('<Double-Button-1>', lambda e: self.modify_user())
        
        self.refresh_users_list()
        self.update_status("Gestion des utilisateurs chargee")
    
    def add_user(self):
        """Ajoute un nouvel utilisateur"""
        username = self.new_username.get().strip()
        email = self.new_email.get().strip()
        password = self.new_password.get()
        role = self.new_role.get()
        
        # Validation
        if not all([username, email, password, role]):
            messagebox.showerror("Erreur", "Tous les champs sont obligatoires")
            return
        
        # Validation email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messagebox.showerror("Erreur", "L'adresse email n'est pas valide")
            return
        
        # Ajout
        if self.user_manager.add_user(username, password, email, role):
            # Envoi email si demande
            if self.send_credentials_var.get():
                user_data = {
                    'username': username,
                    'email': email,
                    'password': password,
                    'role': role
                }
                success, error = self.email_service.send_user_credentials(user_data)
                if success:
                    messagebox.showinfo("Succes", 
                        f" Utilisateur {username} cree!\n Identifiants envoyes a {email}")
                else:
                    messagebox.showwarning("Attention",
                        f" Utilisateur cree\n Erreur email: {error}")
            else:
                messagebox.showinfo("Succes", f" Utilisateur {username} cree avec succes!")
            
            # Nettoyer et rafraichir
            self.new_username.delete(0, tk.END)
            self.new_email.delete(0, tk.END)
            self.new_password.delete(0, tk.END)
            self.refresh_users_list()
            self.db.add_log(self.user[1], "ADD_USER", f"Utilisateur {username} ajoute")
            self.update_status(f"Utilisateur {username} ajoute")
        else:
            messagebox.showerror("Erreur", "Cet utilisateur existe deja")
    
    def modify_user(self):
        """Modifie un utilisateur selectionne"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez selectionner un utilisateur")
            return
        
        # Code de modification existant...
    
    def delete_user(self):
        """Supprime un utilisateur"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez selectionner un utilisateur")
            return
        
        item = self.users_tree.item(selection[0])
        user_data = item['values']
        user_id = user_data[0]
        username = user_data[1]
        
        # Empecher la suppression de l'admin
        if username == 'admin':
            messagebox.showerror("Erreur", "Impossible de supprimer l'administrateur principal")
            return
        
        # Empecher l'auto-suppression
        if username == self.user[1]:
            messagebox.showerror("Erreur", "Vous ne pouvez pas supprimer votre propre compte")
            return
        
        # Confirmation
        if messagebox.askyesno("Confirmation", 
                               f"tes-vous sur de vouloir supprimer l'utilisateur {username} ?"):
            if self.user_manager.delete_user(user_id):
                messagebox.showinfo("Succes", f" Utilisateur {username} supprime")
                self.db.add_log(self.user[1], "DELETE_USER", f"Utilisateur {username} supprime")
                self.refresh_users_list()
                self.update_status(f"Utilisateur {username} supprime")
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression")
    
    def refresh_users_list(self):
        """Rafraichit la liste des utilisateurs"""
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        users = self.user_manager.get_all_users_with_email()
        for user in users:
            self.users_tree.insert('', 'end', values=(
                user[0],  # ID
                user[1],  # Username
                user[2] or '',  # Email
                user[3],  # Role
                user[4][:10] if user[4] else '',  # Date creation
                '' if user[5] else ''  # Actif
            ))
    
    def import_users_csv(self):
        """
        Importe des utilisateurs en masse depuis un fichier CSV.
        Reserve au super_user (tout l'ecran de gestion l'est deja).

        Colonnes attendues (avec une ligne d'en-tete) :
            username ; password ; email ; role
        - Separateur accepte : ';' ou ','
        - email est optionnel
        - role doit valoir : super_user, responsable, comptabilite ou vendeur
        """
        if self.user[4] != USER_ROLES['SUPER_USER']:
            messagebox.showerror("Acces refuse", "Import reserve au super administrateur.")
            return

        filepath = filedialog.askopenfilename(
            title="Choisir un fichier CSV d'utilisateurs",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        if not filepath:
            return

        roles_valides = {
            USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'],
            USER_ROLES['COMPTABILITE'], USER_ROLES['VENDEUR']
        }

        # Lecture du fichier (gestion encodage + separateur ';' ou ',')
        contenu = None
        for enc in ('utf-8-sig', 'latin-1'):
            try:
                with open(filepath, 'r', encoding=enc, newline='') as f:
                    contenu = f.read()
                break
            except Exception:
                continue
        if contenu is None:
            messagebox.showerror("Erreur", "Impossible de lire le fichier CSV.")
            return

        lignes = contenu.splitlines()
        if not lignes:
            messagebox.showerror("Erreur", "Le fichier CSV est vide.")
            return
        premiere_ligne = lignes[0]
        delimiteur = ';' if premiere_ligne.count(';') >= premiere_ligne.count(',') else ','

        import io
        reader = csv.DictReader(io.StringIO(contenu), delimiter=delimiteur)
        if not reader.fieldnames:
            messagebox.showerror("Erreur", "Le fichier CSV est vide ou illisible.")
            return

        # Normalisation des en-tetes : retire un eventuel BOM, espaces, casse.
        def _norm(s):
            return (s or '').replace('\ufeff', '').strip().lower()

        champs = {_norm(c) for c in reader.fieldnames}
        requis = {'username', 'password', 'role'}
        if not requis.issubset(champs):
            messagebox.showerror(
                "Format CSV invalide",
                "Le fichier doit contenir au minimum les colonnes :\n"
                "    username ; password ; role\n"
                "(la colonne email est optionnelle)\n\n"
                "Roles autorises : super_user, responsable, comptabilite, vendeur"
            )
            return

        crees = 0
        ignores_existants = []
        erreurs = []
        for i, row in enumerate(reader, start=2):  # ligne 2 = 1re ligne de donnees
            donnees = {_norm(k): (v or '').strip() for k, v in row.items()}
            username = donnees.get('username', '')
            password = donnees.get('password', '')
            email = donnees.get('email', '')
            role = donnees.get('role', '').lower()

            if not username or not password or not role:
                erreurs.append(f"Ligne {i} : username, password et role obligatoires")
                continue
            if role not in roles_valides:
                erreurs.append(f"Ligne {i} : role '{role}' invalide")
                continue

            if self.user_manager.add_user(username, password, email, role):
                crees += 1
            else:
                ignores_existants.append(f"Ligne {i} : '{username}' existe deja")

        self.refresh_users_list()
        self.db.add_log(self.user[1], "IMPORT_USERS_CSV", f"{crees} utilisateur(s) cree(s)")

        resume = f"Import termine.\n\n- Crees : {crees}"
        if ignores_existants:
            resume += f"\n- Ignores (deja existants) : {len(ignores_existants)}"
        if erreurs:
            resume += f"\n- Erreurs : {len(erreurs)}"
        details = ignores_existants + erreurs
        if details:
            apercu = "\n".join(details[:15])
            if len(details) > 15:
                apercu += f"\n... (+{len(details) - 15} autre(s))"
            resume += "\n\n" + apercu
        messagebox.showinfo("Import CSV", resume)
    
    def download_user_csv_template(self):
        """
        Permet de telecharger (enregistrer une copie de) le modele CSV
        d'import d'utilisateurs. Utilise le fichier 'modele_utilisateurs.csv'
        place a la racine du projet s'il existe, sinon un modele integre.
        """
        if self.user[4] != USER_ROLES['SUPER_USER']:
            messagebox.showerror("Acces refuse", "Reserve au super administrateur.")
            return

        # Modele integre (utilise si le fichier n'est pas trouve a la racine)
        modele_par_defaut = (
            "username;password;email;role\n"
            "jdupont;MotDePasse1;jdupont@exemple.fr;vendeur\n"
            "mmartin;MotDePasse2;mmartin@exemple.fr;responsable\n"
            "compta1;MotDePasse3;compta@exemple.fr;comptabilite\n"
        )

        # Chercher le fichier a la racine du projet (dossier de gui_main.py)
        contenu = None
        try:
            racine = os.path.dirname(os.path.abspath(__file__))
            chemin_modele = os.path.join(racine, 'modele_utilisateurs.csv')
            if os.path.exists(chemin_modele):
                for enc in ('utf-8-sig', 'latin-1'):
                    try:
                        with open(chemin_modele, 'r', encoding=enc) as f:
                            contenu = f.read()
                        break
                    except Exception:
                        continue
        except Exception:
            contenu = None
        if not contenu:
            contenu = modele_par_defaut

        # Demander ou enregistrer la copie
        destination = filedialog.asksaveasfilename(
            title="Enregistrer le modele CSV",
            defaultextension=".csv",
            initialfile="modele_utilisateurs.csv",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        if not destination:
            return
        try:
            with open(destination, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(contenu)
            self.db.add_log(self.user[1], "TELECHARGEMENT_MODELE_CSV", destination)
            messagebox.showinfo(
                "Modele enregistre",
                f"Le modele CSV a ete enregistre :\n{destination}\n\n"
                "Colonnes : username ; password ; email ; role\n"
                "Roles : super_user, responsable, comptabilite, vendeur"
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer le modele :\n{e}")
    
    # Methodes utilitaires restent identiques
    def create_form_section(self, parent, title):
        """Cree une section dans le formulaire"""
        section = tk.Frame(parent, bg=self.colors['white'])
        section.pack(fill='x', pady=(20, 10))
        
        tk.Label(
            section,
            text=title,
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['white'],
            fg=self.colors['primary']
        ).pack(anchor='w')
        
        tk.Frame(section, height=1, bg=self.colors['hover']).pack(fill='x', pady=(5, 10))
    
    def format_montant_xpf(self, montant):
        """Formate un montant en XPF"""
        try:
            if isinstance(montant, str):
                montant = float(montant.replace(',', '.').replace(' ', ''))
            elif montant is None:
                montant = 0.0
            else:
                montant = float(montant)
            
            return f"{montant:,.0f} XPF".replace(',', ' ')
        except (ValueError, TypeError):
            return "0 XPF"
    
    def validate_email(self, event, field):
        """Valide le format de l'email"""
        email = self.avoir_entries[field].get().strip()
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messagebox.showwarning("Format invalide", "L'adresse email n'est pas valide")
            self.avoir_entries[field].focus()
            return False
        return True
    
    def validate_montant(self, event, field):
        """Valide le format du montant"""
        montant = self.avoir_entries[field].get().strip()
        if montant:
            try:
                montant_clean = montant.replace(' ', '').replace(',', '.')
                float(montant_clean)
            except ValueError:
                messagebox.showwarning("Format invalide", "Le montant doit etre un nombre")
                self.avoir_entries[field].focus()
                return False
        return True
    
    def toggle_email_field(self):
        """Active/desactive le champ email selon la checkbox"""
        if self.send_email_var.get():
            self.avoir_entries['email_client'].config(state='normal')
            if not self.avoir_entries['email_client'].get():
                self.avoir_entries['email_client'].focus()
        else:
            self.avoir_entries['email_client'].config(state='readonly')
    
    def detect_format(self, event=None):
        """Detecte le format de l'entree"""
        value = self.avoir_input.get().strip()
        
        if not value:
            self.format_label.config(text="")
        elif '/' in value:
            self.format_label.config(text=" Format: Numero d'avoir", fg=self.colors['success'])
        elif value.isdigit() and len(value) >= 6:
            self.format_label.config(text=" Format: Code-barres", fg=self.colors['info'])
        else:
            self.format_label.config(text=" Saisie en cours...", fg=self.colors['text_secondary'])
    
    def reset_avoir_input(self):
        """Reinitialise le champ de saisie"""
        self.avoir_input.delete(0, tk.END)
        self.avoir_input.focus()
        self.format_label.config(text="")
    
    def play_sound(self, sound_type):
        """Joue un son de feedback"""
        try:
            import winsound
            if sound_type == 'success':
                winsound.Beep(1000, 200)  # Son aigu court
            else:
                winsound.Beep(500, 500)   # Son grave long
        except:
            pass
    
    def update_status(self, message):
        """Met a jour la barre de statut"""
        self.status_message.configure(text=message)
        self.root.update()
    
    def center_window(self):
        """Centre la fenetre sur l'ecran"""
        self.root.update_idletasks()
        width = 1400
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def fade_in(self):
        """Animation d'ouverture avec fondu"""
        alpha = 0.0
        self.root.attributes('-alpha', alpha)
        
        def increase_alpha():
            nonlocal alpha
            if alpha < 1.0:
                alpha += 0.1
                self.root.attributes('-alpha', alpha)
                self.root.after(30, increase_alpha)
        
        increase_alpha()
    """
    Methode validate_avoir corrigee pour gui_main.py
    Gere l'utilisation partielle avec generation PDF et envoi email automatique
    """

    def validate_avoir(self):
        """
        Valide l'utilisation d'un avoir avec dialogue pour montant et facture
        GENRE automatiquement PDF et ENVOIE email pour utilisation partielle
        """
        input_value = self.avoir_input.get().strip()
        if not input_value:
            messagebox.showerror(
                "Erreur de saisie", 
                "Veuillez saisir un numero d'avoir ou scanner le code-barres"
            )
            return
        
        # Determiner le format et traiter
        numero_avoir = input_value
        
        # Si c'est un code-barres (format sans slash)
        if '/' not in input_value and len(input_value) >= 6:
            if len(input_value) == 7:  # Format YYXXXXX
                numero_avoir = f"{input_value[:2]}/{input_value[2:]}"
                print(f" Code-barres detecte: {input_value}  N avoir: {numero_avoir}")
        
        # Recuperer les details de l'avoir
        avoir_details = self.avoir_manager.get_avoir_details(numero_avoir)
        if not avoir_details:
            messagebox.showerror(
                " AVOIR INTROUVABLE",
                f"L'avoir {numero_avoir} n'existe pas!\n\n"
                f"Verifiez le numero saisi ou le code-barres scanne."
            )
            self.reset_avoir_input()
            return
        
        avoir = avoir_details if not isinstance(avoir_details, dict) else avoir_details['avoir']
        
        # Verifier le statut
        statut = avoir[12]
        if statut == AVOIR_STATUS['UTILISE']:
            self.play_sound('error')
            messagebox.showerror(
                " AVOIR DEJA UTILISE",
                f"ERREUR : L'avoir {numero_avoir} a deja ete utilise!\n\n"
                f"Cet avoir ne peut pas etre valide une seconde fois."
            )
            self.reset_avoir_input()
            return
        
        # Avoir BLOQUE : utilisation impossible (le forcage ne leve PAS un blocage).
        if statut == AVOIR_STATUS['BLOQUE']:
            self.play_sound('error')
            messagebox.showwarning(
                " AVOIR BLOQUE",
                f"L'avoir {numero_avoir} est BLOQUE.\n\n"
                f"Demandez au client de passer a la COMPTABILITE."
            )
            self.reset_avoir_input()
            return
        
        # Avoir SUPPRIME : utilisation impossible. On affiche le MOTIF de
        # suppression (stocke dans commentaire_blocage, index 25) pour que le
        # vendeur puisse expliquer la raison au client.
        if statut == AVOIR_STATUS['SUPPRIME']:
            self.play_sound('error')
            motif_suppression = avoir[25] if (len(avoir) > 25 and avoir[25]) else ''
            message_suppr = (
                f"L'avoir {numero_avoir} a ete SUPPRIME.\n\n"
                f"Il ne peut plus etre utilise."
            )
            if motif_suppression:
                message_suppr += f"\n\nMotif : {motif_suppression}"
            messagebox.showwarning(" AVOIR SUPPRIME", message_suppr)
            self.reset_avoir_input()
            return
        
        # Avoir ANNULE : utilisation impossible. Meme principe que bloque/supprime :
        # on indique QUI l'a annule, la DATE et le MOTIF (memes colonnes :
        # commentaire_blocage index 25, bloque_par index 26, date_blocage index 27).
        if statut == AVOIR_STATUS['ANNULE']:
            self.play_sound('error')
            motif_annule = avoir[25] if (len(avoir) > 25 and avoir[25]) else ''
            annule_par = avoir[26] if (len(avoir) > 26 and avoir[26]) else ''
            date_annule = avoir[27] if (len(avoir) > 27 and avoir[27]) else ''
            message_annule = (
                f"L'avoir {numero_avoir} a ete ANNULE.\n\n"
                f"Il ne peut plus etre utilise."
            )
            if annule_par:
                message_annule += f"\n\nAnnule par : {annule_par}"
            if date_annule:
                d = str(date_annule)[:10]
                if len(d) == 10 and d[4] == '-':
                    d = f"{d[8:10]}/{d[5:7]}/{d[0:4]}"
                message_annule += f"\nDate : {d}"
            if motif_annule:
                message_annule += f"\nMotif : {motif_annule}"
            messagebox.showwarning(" AVOIR ANNULE", message_annule)
            self.reset_avoir_input()
            return
        
        # Determiner si l'avoir est expire : statut 'expire' OU cree il y a plus
        # de 90 jours (regle metier). On ne se base PAS sur date_validite, qui a
        # pu etre heritee/faussee pour d'anciens residus.
        is_expired = self.avoir_manager.is_avoir_expire(avoir)
        
        # Recuperer le montant restant
        montant_restant = avoir[20] if avoir[20] is not None else avoir[8]
        
        # Ouvrir le dialogue pour saisir le montant et la facture
        # (avec option de forcage si l'avoir est expire)
        # Liste deroulante des responsables autorises a valider un forcage :
        # uniquement les comptes ACTIFS de role 'responsable' ou 'comptabilite'.
        responsables_forcage = self.user_manager.get_active_usernames_by_roles(
            [USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]
        )
        dialog = UtilisationDialog(
            self.root, numero_avoir, montant_restant,
            is_expired=is_expired, responsables=responsables_forcage
        )
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            # Utiliser l'avoir avec les parametres saisis
            self.update_status(f"Validation de l'avoir {numero_avoir}...")
            
            result = self.avoir_manager.use_avoir(
                numero_avoir, 
                self.user[1],
                dialog.result['montant_facture'],
                dialog.result['numero_facture'],
                force=dialog.result.get('force', False),
                forcage_autorise_par=dialog.result.get('forcage_autorise_par')
            )
            
            # Securite : avoir bloque renvoye par le gestionnaire
            if result.get('status') == 'blocked':
                self.play_sound('error')
                messagebox.showwarning(" AVOIR BLOQUE", f"{result['message']}")
                self.reset_avoir_input()
                return
            
            # Securite : avoir expire non force
            if result.get('status') == 'expired':
                self.play_sound('error')
                messagebox.showerror(" AVOIR EXPIRE", f"{result['message']}")
                self.reset_avoir_input()
                return
            
            # Traiter le resultat selon le type d'utilisation
            if result['status'] == 'success':
                self.play_sound('success')
                
                if result.get('type_utilisation') == 'partielle':
                    print(f" Utilisation partielle detectee")
                    print(f"   N avoir enfant: {result.get('numero_avoir_enfant')}")
                    
                    # ========== GENERATION PDF AUTOMATIQUE ==========
                    pdf_generated = False
                    pdf_path = None
                    
                    try:
                        from services.pdf_creator import PDFCreator
                        
                        avoir_enfant = result.get('avoir_enfant')
                        date_validite = result.get('date_validite')
                        
                        print(f"   avoir_enfant present: {avoir_enfant is not None}")
                        print(f"   date_validite present: {date_validite is not None}")
                        
                        if avoir_enfant and date_validite:
                            # Normaliser la date de validite (toujours obtenir une chaine JJ/MM/AAAA)
                            if isinstance(date_validite, datetime):
                                date_validite_str = date_validite.strftime('%d/%m/%Y')
                            else:
                                # Chaine renvoyee par la base : on garde uniquement la partie date
                                date_validite_str = str(date_validite).split(' ')[0].split('T')[0]

                            # Preparer les donnees pour le PDF (aucune valeur None ne doit passer)
                            avoir_parent = result.get('avoir_parent')
                            pdf_data = {
                                'numero_client': avoir_enfant[2] or '',
                                'nom_client': avoir_enfant[3] or '',
                                'email_client': avoir_enfant[4] or '',
                                # "facture achat" = facture d'ORIGINE (achat), heritee
                                # de l'avoir parent.
                                'numero_facture': (avoir_enfant[5] or ''),
                                'date_facture': avoir_enfant[6] or '',
                                'montant': result.get('montant_restant', 0),
                                # "facture avoir" : pour un RESIDU, on y met la DERNIERE
                                # facture saisie par l'utilisateur lors de l'utilisation
                                # (celle qui a genere ce residu).
                                # result['numero_facture'] = numero_facture_utilisation.
                                'numero_facture_avoir': (result.get('numero_facture') or avoir_enfant[9] or ''),
                                'date_creation': datetime.now().strftime('%d/%m/%Y'),
                                'date_validite': date_validite_str,
                                # Avoir enfant => type "Résidu" + reference de l'avoir parent
                                'est_residu': True,
                                'avoir_parent_numero': (avoir_parent[1] if avoir_parent else ''),
                                'avoir_parent_montant': (avoir_parent[8] if avoir_parent else None)
                            }
                            
                            print(f"   Generation PDF avec montant: {pdf_data['montant']} XPF")
                            
                            pdf_creator = PDFCreator()
                            success_pdf, pdf_result = pdf_creator.generate(
                                result['numero_avoir_enfant'],
                                pdf_data,
                                self.user[1]
                            )
                            
                            if success_pdf:
                                print(f" PDF genere: {pdf_result}")
                                pdf_generated = True
                                pdf_path = pdf_result
                                
                                # Ouvrir le PDF automatiquement pour impression
                                try:
                                    if os.name == 'nt':  # Windows
                                        os.startfile(str(pdf_path))
                                    elif os.name == 'posix':  # Linux/Mac
                                        import subprocess
                                        subprocess.run(['xdg-open', str(pdf_path)], check=False)
                                    print(f" PDF ouvert pour impression")
                                except Exception as e:
                                    print(f" Impossible d'ouvrir le PDF: {e}")
                            else:
                                print(f" Erreur PDF: {pdf_result}")
                                messagebox.showwarning(
                                    "PDF non genere",
                                    "L'avoir enfant a bien ete cree, mais son PDF n'a pas pu "
                                    "etre genere.\n\nErreur exacte :\n"
                                    f"{pdf_result}"
                                )
                        else:
                            print(f" Donnees manquantes pour generer le PDF")
                            details = []
                            if not avoir_enfant:
                                print("   - avoir_enfant manquant")
                                details.append("- donnees de l'avoir enfant introuvables")
                            if not date_validite:
                                print("   - date_validite manquant")
                                details.append("- date de validite manquante")
                            messagebox.showwarning(
                                "PDF non genere",
                                "L'avoir enfant a bien ete cree, mais le PDF n'a pas pu "
                                "etre genere car des donnees sont manquantes :\n\n"
                                + "\n".join(details)
                            )
                    
                    except ImportError as e:
                        print(f" Module PDFCreator introuvable: {e}")
                        messagebox.showwarning(
                            "Module manquant",
                            "Le module reportlab n'est pas installe.\n"
                            "Le PDF ne peut pas etre genere.\n\n"
                            "Installez-le avec: pip install reportlab Pillow"
                        )
                    except Exception as e:
                        print(f" Erreur generation PDF: {e}")
                        import traceback
                        traceback.print_exc()
                        messagebox.showerror(
                            "Erreur PDF",
                            "Une erreur s'est produite pendant la generation du PDF "
                            "de l'avoir enfant.\n\nDetail technique :\n"
                            f"{type(e).__name__}: {e}"
                        )
                    
                    # ========== ENVOI EMAIL AUTOMATIQUE ==========
                    email_sent = False
                    
                    try:
                        avoir_parent = result.get('avoir_parent')
                        
                        print(f"   avoir_parent present: {avoir_parent is not None}")
                        
                        if avoir_parent and avoir_parent[4] and self.email_service:
                            email_data = {
                                'numero_avoir': numero_avoir,
                                'numero_avoir_enfant': result['numero_avoir_enfant'],
                                'nom_client': avoir_parent[3],
                                'email_client': avoir_parent[4],
                                'montant_initial': avoir_parent[8],
                                'montant_utilise': result.get('montant_utilise', result.get('montant_facture', 0)),
                                'montant_restant': result['montant_restant'],
                                'numero_facture': result['numero_facture'],
                                'date_utilisation': datetime.now(),
                                'date_validite': result['date_validite']
                            }
                            
                            print(f"   Envoi email a: {avoir_parent[4]}")
                            
                            success_email, error = self.email_service.send_utilisation_partielle_notification(email_data)
                            
                            if success_email:
                                print(f" Email envoye a {avoir_parent[4]}")
                                email_sent = True
                            else:
                                print(f" Erreur email: {error}")
                        else:
                            if not avoir_parent:
                                print("   - avoir_parent manquant")
                            elif not avoir_parent[4]:
                                print("   - email_client vide")
                            elif not self.email_service:
                                print("   - email_service non disponible")
                    
                    except AttributeError as e:
                        print(f" Methode send_utilisation_partielle_notification manquante: {e}")
                        print(" PROBLME: email_service.py n'a pas ete modifie")
                    except Exception as e:
                        print(f" Erreur envoi email: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # ========== MESSAGE DE CONFIRMATION ==========
                    message_parts = [
                        f"{result['message']}\n",
                        f" N AVOIR ENFANT: {result['numero_avoir_enfant']}",
                        f" MONTANT RESTANT: {self.format_montant_xpf(result['montant_restant'])}\n"
                    ]
                    
                    if pdf_generated:
                        message_parts.append(f" PDF genere et ouvert automatiquement")
                        message_parts.append(f" {pdf_path}\n")
                    else:
                        message_parts.append(f" Le PDF n'a pas pu etre genere\n")
                    
                    if email_sent:
                        message_parts.append(f" Email de notification envoye au client")
                    elif avoir_parent and avoir_parent[4]:
                        message_parts.append(f" Email non envoye (erreur)")
                    else:
                        message_parts.append(f" Pas d'email client renseigne")
                    
                    message_parts.extend([
                        "\n IMPORTANT :",
                        f" L'avoir N{numero_avoir} n'est PLUS utilisable",
                        f" Remettez le NOUVEAU bon d'avoir N{result['numero_avoir_enfant']} au client"
                    ])
                    
                    messagebox.showinfo(
                        " UTILISATION PARTIELLE REUSSIE",
                        "\n".join(message_parts)
                    )
                    
                elif result.get('type_utilisation') == 'insuffisant':
                    # CAS: Avoir insuffisant - afficher le restant a payer
                    restant_a_payer = result.get('restant_a_payer', 0)
                    messagebox.showwarning(
                        "⚠️ RESTANT À PAYER",
                        f"L'avoir a été utilisé en totalité.\n\n"
                        f"Montant de l'avoir: {self.format_montant_xpf(result['montant_avoir'])}\n"
                        f"Montant de la facture: {self.format_montant_xpf(result['montant_facture'])}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💰 RESTANT À PAYER: {self.format_montant_xpf(restant_a_payer)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"Le client doit régler ce montant."
                    )
                    
                else:
                    # Utilisation totale
                    messagebox.showinfo(
                        " VALIDATION REUSSIE",
                        f"{result['message']}\n\n"
                        f"L'avoir a ete marque comme UTILISE dans le systeme."
                    )
                
                # Enregistrer dans les logs
                self.db.add_log(
                    self.user[1], 
                    f"VALIDATION_AVOIR_{result.get('type_utilisation', 'TOTALE').upper()}", 
                    f"Avoir {numero_avoir} - Facture: {dialog.result['numero_facture']}"
                )
            else:
                self.play_sound('error')
                messagebox.showerror(" ERREUR", result['message'])
        
        # Reinitialiser le champ de saisie
        self.reset_avoir_input()
        
    # ══════════════════════════════════════════════════════════════════════
    # UTILISATION DE PLUSIEURS AVOIRS CUMULES SUR UNE MEME FACTURE
    # ══════════════════════════════════════════════════════════════════════

    def _generer_pdf_avoir_enfant(self, result):
        """
        Genere (et ouvre) le PDF de l'avoir residu cree lors d'une utilisation
        partielle. Utilise par l'utilisation multi-avoirs.

        Returns:
            tuple: (succes: bool, chemin_ou_message: str)
        """
        try:
            from services.pdf_creator import PDFCreator

            avoir_enfant = result.get('avoir_enfant')
            date_validite = result.get('date_validite')

            if not avoir_enfant or not date_validite:
                return False, "donnees de l'avoir enfant incompletes"

            # Normaliser la date de validite (toujours une chaine JJ/MM/AAAA)
            if isinstance(date_validite, datetime):
                date_validite_str = date_validite.strftime('%d/%m/%Y')
            else:
                date_validite_str = str(date_validite).split(' ')[0].split('T')[0]

            avoir_parent = result.get('avoir_parent')
            pdf_data = {
                'numero_client': avoir_enfant[2] or '',
                'nom_client': avoir_enfant[3] or '',
                'email_client': avoir_enfant[4] or '',
                # "facture achat" = facture d'ORIGINE, heritee de l'avoir parent
                'numero_facture': (avoir_enfant[5] or ''),
                'date_facture': avoir_enfant[6] or '',
                'montant': result.get('montant_restant', 0),
                # "facture avoir" : facture saisie lors de l'utilisation
                'numero_facture_avoir': (result.get('numero_facture') or avoir_enfant[9] or ''),
                'date_creation': datetime.now().strftime('%d/%m/%Y'),
                'date_validite': date_validite_str,
                'est_residu': True,
                'avoir_parent_numero': (avoir_parent[1] if avoir_parent else ''),
                'avoir_parent_montant': (avoir_parent[8] if avoir_parent else None)
            }

            pdf_creator = PDFCreator()
            success_pdf, pdf_result = pdf_creator.generate(
                result['numero_avoir_enfant'],
                pdf_data,
                self.user[1]
            )

            if not success_pdf:
                return False, str(pdf_result)

            # Ouvrir le PDF automatiquement pour impression
            try:
                if os.name == 'nt':
                    os.startfile(str(pdf_result))
                elif os.name == 'posix':
                    import subprocess
                    subprocess.run(['xdg-open', str(pdf_result)], check=False)
            except Exception as e:
                print(f" Impossible d'ouvrir le PDF: {e}")

            return True, str(pdf_result)

        except ImportError as e:
            print(f" Module PDFCreator introuvable: {e}")
            return False, "module reportlab non installe"
        except Exception as e:
            print(f" Erreur generation PDF: {e}")
            import traceback
            traceback.print_exc()
            return False, f"{type(e).__name__}: {e}"

    def _envoyer_email_avoir_enfant(self, result, numero_avoir):
        """
        Envoie au client l'email de notification d'utilisation partielle.
        Utilise par l'utilisation multi-avoirs.

        Returns:
            bool: True si l'email a bien ete envoye
        """
        try:
            avoir_parent = result.get('avoir_parent')
            if not avoir_parent or not avoir_parent[4] or not self.email_service:
                return False

            email_data = {
                'numero_avoir': numero_avoir,
                'numero_avoir_enfant': result['numero_avoir_enfant'],
                'nom_client': avoir_parent[3],
                'email_client': avoir_parent[4],
                'montant_initial': avoir_parent[8],
                'montant_utilise': result.get('montant_utilise', result.get('montant_facture', 0)),
                'montant_restant': result['montant_restant'],
                'numero_facture': result['numero_facture'],
                'date_utilisation': datetime.now(),
                'date_validite': result['date_validite']
            }

            success_email, error = self.email_service.send_utilisation_partielle_notification(email_data)
            if not success_email:
                print(f" Erreur email: {error}")
            return bool(success_email)

        except Exception as e:
            print(f" Erreur envoi email: {e}")
            return False

    def validate_multi_avoirs(self):
        """
        Utilisation CUMULEE de plusieurs avoirs sur une seule facture.

        Les avoirs sont consommes un par un, dans l'ordre de la liste, via
        AvoirManager.use_avoir() : chaque avoir est donc trace normalement
        (historique, logs, statut). Le dernier avoir partiellement consomme
        genere automatiquement son avoir residu (PDF + email).
        Les avoirs peuvent appartenir a des CLIENTS DIFFERENTS.
        """
        responsables_forcage = self.user_manager.get_active_usernames_by_roles(
            [USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']]
        )

        dialog = MultiAvoirDialog(
            self.root, self.avoir_manager, responsables=responsables_forcage
        )
        self.root.wait_window(dialog.dialog)

        if not dialog.result:
            return

        numero_facture = dialog.result['numero_facture']
        montant_facture = dialog.result['montant_facture']
        forcage_autorise_par = dialog.result.get('forcage_autorise_par')

        reste = montant_facture
        total_impute = 0
        lignes_recap = []
        residus = []
        erreurs = []
        non_utilises = []

        for item in dialog.result['avoirs']:
            numero = item['numero']

            # Facture deja entierement couverte : l'avoir reste intact
            if reste <= 0:
                non_utilises.append(numero)
                continue

            montant_impute = min(item['montant_restant'], reste)
            self.update_status(f"Utilisation de l'avoir {numero}...")

            result = self.avoir_manager.use_avoir(
                numero,
                self.user[1],
                montant_impute,
                numero_facture,
                force=bool(item['expire']),
                forcage_autorise_par=forcage_autorise_par if item['expire'] else None
            )

            if result.get('status') != 'success':
                erreurs.append(f"  - {numero} : {result.get('message', 'erreur inconnue')}")
                continue

            reste -= montant_impute
            total_impute += montant_impute

            ligne = f"  - {numero} : {format_montant_simple(montant_impute)}"
            if item['expire']:
                ligne += "  [FORCAGE]"

            # Utilisation partielle => avoir residu : PDF + email client
            if result.get('type_utilisation') == 'partielle':
                numero_enfant = result.get('numero_avoir_enfant')
                montant_residu = result.get('montant_restant', 0)

                pdf_ok, pdf_info = self._generer_pdf_avoir_enfant(result)
                email_ok = self._envoyer_email_avoir_enfant(result, numero)

                residus.append({
                    'numero': numero_enfant,
                    'montant': montant_residu,
                    'pdf_ok': pdf_ok,
                    'pdf_info': pdf_info,
                    'email_ok': email_ok
                })
                ligne += (f"  ->  residu N{numero_enfant} de "
                          f"{format_montant_simple(montant_residu)}")

            lignes_recap.append(ligne)

            self.db.add_log(
                self.user[1],
                "VALIDATION_AVOIR_MULTI",
                f"Avoir {numero} - Facture: {numero_facture} - "
                f"Impute: {format_montant_simple(montant_impute)}"
            )

        # ---------------- Aucun avoir n'a pu etre utilise ----------------
        if not lignes_recap:
            self.play_sound('error')
            messagebox.showerror(
                " ERREUR",
                "Aucun avoir n'a pu etre utilise.\n\n" + "\n".join(erreurs)
            )
            self.update_status("Utilisation multi-avoirs echouee")
            return

        # ---------------- Message de synthese ----------------
        self.play_sound('success')

        message_parts = [
            f"Facture {numero_facture} : {format_montant_simple(montant_facture)}",
            f"Total des avoirs imputes : {format_montant_simple(total_impute)}",
            "",
            "Detail :",
        ]
        message_parts.extend(lignes_recap)

        if reste > 0:
            message_parts.extend([
                "",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f" RESTANT A PAYER : {format_montant_simple(reste)}",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "Le client doit regler ce montant."
            ])
        else:
            message_parts.append("\nLa facture est entierement couverte par les avoirs.")

        for residu in residus:
            message_parts.extend([
                "",
                f" NOUVEL AVOIR (residu) N{residu['numero']} : "
                f"{format_montant_simple(residu['montant'])}",
                ("   PDF genere et ouvert : " + residu['pdf_info']) if residu['pdf_ok']
                else ("   PDF NON genere (" + residu['pdf_info'] + ")"),
                "   Email de notification envoye au client" if residu['email_ok']
                else "   Pas d'email envoye au client",
                f"   Remettez ce nouveau bon d'avoir au client."
            ])

        if non_utilises:
            message_parts.extend([
                "",
                "Avoirs NON utilises (facture deja couverte, toujours valables) : "
                + ", ".join(non_utilises)
            ])

        if erreurs:
            message_parts.extend(["", "Avoirs en erreur :"] + erreurs)

        titre = " UTILISATION MULTI-AVOIRS REUSSIE"
        if erreurs:
            messagebox.showwarning(titre + " (avec erreurs)", "\n".join(message_parts))
        else:
            messagebox.showinfo(titre, "\n".join(message_parts))

        self.db.add_log(
            self.user[1],
            "VALIDATION_MULTI_AVOIRS",
            f"Facture {numero_facture} - {len(lignes_recap)} avoir(s) cumule(s) - "
            f"Total impute: {format_montant_simple(total_impute)} - "
            f"Restant a payer: {format_montant_simple(reste)}"
        )

        self.update_status("Utilisation multi-avoirs terminee")

    def setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier"""
        self.root.bind('<Control-d>', lambda e: self.show_dashboard())
        self.root.bind('<Control-n>', lambda e: self.show_create_avoir() if self.user[4] in [USER_ROLES['SUPER_USER'], USER_ROLES['RESPONSABLE'], USER_ROLES['COMPTABILITE']] else None)
        self.root.bind('<Control-u>', lambda e: self.show_use_avoir())
        self.root.bind('<Control-l>', lambda e: self.logout())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<F5>', lambda e: self.refresh_current_view())
        self.root.bind('<F1>', lambda e: self.show_shortcuts())
    
    def refresh_current_view(self):
        """Rafraichit la vue actuelle"""
        self.update_status("Rafraichissement...")
        # Logique de rafraichissement selon la vue active
        self.update_status("Vue rafraichie")
    
    def show_search_avoir(self):
        """Interface de recherche d'avoir"""
        pass
    
    def show_configuration(self):
        """Interface de configuration de la base de donnees (reservee au super_user)."""
        # Seul un super utilisateur peut changer la base de l'application
        if self.user[4] != USER_ROLES['SUPER_USER']:
            messagebox.showerror(
                "Acces refuse",
                "Seul un super utilisateur peut modifier la configuration de la base de donnees."
            )
            return

        from config.paths import get_base_path, set_base_path, NETWORK_BASE
        from pathlib import Path

        prod_dir = NETWORK_BASE / "db_module_avoir_qc"
        test_dir = NETWORK_BASE / "db_module_avoir_qc_TEST"

        self.clear_content_frame()
        self.update_content_title("Configuration")
        self.update_status("Configuration de la base de donnees")

        card = tk.Frame(self.content_frame, bg=self.colors['white'], bd=0)
        card.pack(fill='x', padx=30, pady=20)
        tk.Frame(card, bg=self.colors['primary'], height=5).pack(fill='x')
        inner = tk.Frame(card, bg=self.colors['white'])
        inner.pack(fill='x', padx=30, pady=20)

        tk.Label(
            inner, text="Base de donnees", font=('Segoe UI', 16, 'bold'),
            bg=self.colors['white'], fg=self.colors['text_primary']
        ).pack(anchor='w', pady=(0, 10))

        info_var = tk.StringVar()

        def _refresh_state():
            base = get_base_path()
            dbf = Path(base) / "avoirs.db"
            try:
                existe = dbf.exists()
            except Exception:
                existe = False
            if str(base) == str(prod_dir):
                mode = "PRODUCTION"
            elif str(base) == str(test_dir):
                mode = "TEST (serveur)"
            else:
                mode = "Personnalisee"
            info_var.set(
                f"Mode actuel       : {mode}\n"
                f"Dossier           : {base}\n"
                f"Fichier de base   : {dbf}\n"
                f"La base existe    : {'OUI' if existe else 'NON'}"
            )

        _refresh_state()
        tk.Label(
            inner, textvariable=info_var, font=('Segoe UI', 10),
            bg=self.colors['white'], fg=self.colors['text_secondary'],
            justify='left'
        ).pack(anchor='w', pady=(0, 15))

        tk.Label(
            inner, text="Changer de base (effet au PROCHAIN demarrage)",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['white'], fg=self.colors['text_primary']
        ).pack(anchor='w', pady=(10, 8))

        def _switch(target, label):
            if not messagebox.askyesno(
                "Confirmation",
                f"Faire pointer l'application sur la base {label} ?\n\n"
                f"{Path(target) / 'avoirs.db'}\n\n"
                "Le changement sera effectif apres REDEMARRAGE de l'application "
                "(sur ce poste et sur les autres postes)."
            ):
                return
            try:
                set_base_path(str(target))
                _refresh_state()
                messagebox.showinfo(
                    "Configuration enregistree",
                    f"L'application utilisera la base {label} au prochain demarrage.\n\n"
                    "Veuillez FERMER puis RELANCER l'application pour appliquer le changement."
                )
            except Exception as e:
                messagebox.showerror(
                    "Erreur",
                    f"Impossible d'enregistrer la configuration :\n{e}\n\n"
                    "Verifiez l'acces au partage reseau."
                )

        btns = tk.Frame(inner, bg=self.colors['white'])
        btns.pack(anchor='w')
        tk.Button(
            btns, text=" Base de PRODUCTION",
            command=lambda: _switch(prod_dir, "de PRODUCTION"),
            font=('Segoe UI', 10, 'bold'), bg=self.colors['success'], fg='white',
            bd=0, cursor='hand2', padx=20, pady=10
        ).pack(side='left', padx=(0, 10))
        tk.Button(
            btns, text=" Base de TEST (serveur)",
            command=lambda: _switch(test_dir, "de TEST"),
            font=('Segoe UI', 10, 'bold'), bg=self.colors['info'], fg='white',
            bd=0, cursor='hand2', padx=20, pady=10
        ).pack(side='left')

        # ─── Reinitialisation de la base de TEST (jamais la production) ───
        tk.Frame(inner, bg='#e0e0e0', height=1).pack(fill='x', pady=(20, 12))
        tk.Label(
            inner, text="Reinitialiser la base de TEST",
            font=('Segoe UI', 11, 'bold'),
            bg=self.colors['white'], fg=self.colors['text_primary']
        ).pack(anchor='w', pady=(0, 4))
        tk.Label(
            inner,
            text="Vide toutes les donnees de la base de TEST (avoirs, historiques, logs). "
                 "Les comptes utilisateurs sont conserves. La PRODUCTION n'est jamais touchee.",
            font=('Segoe UI', 9), bg=self.colors['white'],
            fg=self.colors['text_secondary'], wraplength=600, justify='left'
        ).pack(anchor='w', pady=(0, 8))

        def _reset_test():
            test_db = str(test_dir / 'avoirs.db')
            current = str(getattr(self.db, 'db_path', ''))
            # Garde-fou : on ne reinitialise QUE la base de test reellement ouverte
            if current != test_db:
                messagebox.showerror(
                    "Reinitialisation refusee",
                    "La reinitialisation n'est possible QUE sur la base de TEST.\n\n"
                    f"Base actuellement ouverte :\n{current}\n\n"
                    "Basculez sur la base de TEST (bouton ci-dessus) puis REDEMARREZ "
                    "l'application avant de reinitialiser."
                )
                return
            if not messagebox.askyesno(
                "Reinitialiser la base de TEST",
                "Cette operation va SUPPRIMER DEFINITIVEMENT toutes les donnees de la "
                "base de TEST :\n"
                "   - tous les avoirs\n"
                "   - l'historique d'utilisation\n"
                "   - l'historique des emails\n"
                "   - les journaux (logs)\n\n"
                "Les comptes utilisateurs sont CONSERVES.\n"
                "La base de PRODUCTION n'est PAS affectee.\n\n"
                "Confirmer la reinitialisation de la base de TEST ?"
            ):
                return
            try:
                for table in ('avoirs', 'historique_utilisation', 'email_history', 'logs'):
                    try:
                        self.db.cursor.execute(f"DELETE FROM {table}")
                    except Exception:
                        pass
                self.db.conn.commit()
                try:
                    self.db.add_log(self.user[1], "RESET_BDD_TEST",
                                    "Reinitialisation de la base de TEST depuis l'interface")
                except Exception:
                    pass
                messagebox.showinfo(
                    "Base de TEST reinitialisee",
                    "La base de TEST a ete videe avec succes.\n\n"
                    "Pour la repeupler avec des donnees de test, lancez :\n"
                    "    python test_data.py"
                )
            except Exception as e:
                messagebox.showerror("Erreur", f"Echec de la reinitialisation :\n{e}")

        tk.Button(
            inner, text=" Reinitialiser la base de TEST", command=_reset_test,
            font=('Segoe UI', 10, 'bold'), bg=self.colors['error'], fg='white',
            bd=0, cursor='hand2', padx=20, pady=10
        ).pack(anchor='w')

        def _fill_test():
            test_db = str(test_dir / 'avoirs.db')
            current = str(getattr(self.db, 'db_path', ''))
            # Garde-fou : remplissage autorise UNIQUEMENT sur la base de test ouverte
            if current != test_db:
                messagebox.showerror(
                    "Action refusee",
                    "Le remplissage de donnees de test n'est possible QUE sur la base de TEST.\n\n"
                    f"Base actuellement ouverte :\n{current}\n\n"
                    "Basculez sur la base de TEST (bouton ci-dessus) puis REDEMARREZ "
                    "l'application avant de continuer."
                )
                return
            if not messagebox.askyesno(
                "Donnees de test",
                "Ajouter un jeu de donnees de test (clients TST, avoirs de tous statuts, "
                "comptes de test) a la base de TEST ?\n\n"
                "La base de PRODUCTION n'est PAS affectee."
            ):
                return
            try:
                from test_data import generate_test_data
                generate_test_data(self.db.db_path, reset=False)
                try:
                    self.db.add_log(self.user[1], "REMPLISSAGE_BDD_TEST",
                                    "Ajout de donnees de test depuis l'interface")
                except Exception:
                    pass
                messagebox.showinfo(
                    "Donnees de test ajoutees",
                    "Le jeu de donnees de test a ete ajoute a la base de TEST.\n\n"
                    "Ouvrez la liste des avoirs (ou le tableau de bord) pour les voir."
                )
            except Exception as e:
                messagebox.showerror("Erreur", f"Echec du remplissage :\n{e}")

        tk.Button(
            inner, text=" Remplir avec des donnees de test", command=_fill_test,
            font=('Segoe UI', 10, 'bold'), bg=self.colors['info'], fg='white',
            bd=0, cursor='hand2', padx=20, pady=10
        ).pack(anchor='w', pady=(10, 0))

        tk.Label(
            inner,
            text="Astuce : sur la base de TEST, utilisez \"Remplir avec des donnees de test\" "
                 "pour generer des avoirs d'exemple (equivalent de test_data.py).",
            font=('Segoe UI', 9), bg=self.colors['white'],
            fg=self.colors['text_secondary'], wraplength=600, justify='left'
        ).pack(anchor='w', pady=(15, 0))
    
    def send_reminders_manually(self):
        """Envoi manuel de rappels"""
        if messagebox.askyesno("Confirmation", "Voulez-vous envoyer les rappels maintenant?"):
            self.email_service.check_and_send_reminders()
            messagebox.showinfo("Succes", "Rappels envoyes")
    
    def export_logs(self):
        """Exporte les logs en CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(['ID', 'Date/Heure', 'Utilisateur', 'Action', 'Details'])
                    
                    logs = self.db.cursor.execute(
                        "SELECT * FROM logs ORDER BY id DESC"
                    ).fetchall()
                    
                    for log in logs:
                        writer.writerow([log[0], log[1], log[2], log[3], log[4]])
                
                messagebox.showinfo("Succes", f" Logs exportes: {filename}")
                self.db.add_log(self.user[1], "EXPORT_LOGS", filename)
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
    
    def print_report(self):
        """Impression de rapport"""
        messagebox.showinfo("Info", "Fonction d'impression en developpement")
    
    def test_email_connection(self):
        """Test de la connexion email"""
        success, message = self.email_service.test_smtp_connection()
        if success:
            messagebox.showinfo("Test Email", f" {message}")
        else:
            messagebox.showerror("Test Email", f" {message}")
    
    def verify_database(self):
        """Verification de la base de donnees"""
        self.avoir_manager.verify_database_structure()
        messagebox.showinfo("Base de donnees", "Verification terminee. Voir les logs.")
    
    def show_documentation(self):
        """Affiche la documentation"""
        messagebox.showinfo("Documentation", "Documentation disponible sur demande")
    
    def show_shortcuts(self):
        """Affiche les raccourcis clavier"""
        shortcuts = """
        RACCOURCIS CLAVIER
        
        Ctrl+D : Tableau de bord
        Ctrl+N : Creer un avoir
        Ctrl+U : Utiliser un avoir
        Ctrl+L : Deconnexion
        Ctrl+Q : Quitter
        F5 : Rafraichir
        F1 : Afficher cette aide
        """
        messagebox.showinfo("Raccourcis clavier", shortcuts)
    
    def show_about(self):
        """A propos"""
        about_text = """
        MODULE DE GESTION DES AVOIRS CLIENTS
        Version 3.1 - Avec gestion avoirs partiels
        
        Entreprise: STOYANN
        QUINCAILLERIE CALEDONIENNE
        
        Fonctionnalites:
         Interface moderne et intuitive
         Gestion complete des avoirs
         Utilisation partielle des avoirs
         Creation automatique d'avoirs enfants
         Type retour force pour creation manuelle
         Historique d'utilisation detaille
         Generation PDF avec code-barres
         Systeme de scan en caisse
         Messages popup detailles
         Logs systeme complets
         Multi-utilisateurs
         Export Excel/CSV
        
         2025 STOYANN - Tous droits reserves
        """
        messagebox.showinfo("A propos", about_text)
    
    def export_csv(self):
        """Export CSV des avoirs avec nouveaux champs"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"avoirs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow([
                        'N Avoir', 'N Client', 'Nom Client', 'Email', 
                        'Montant (XPF)', 'Montant Utilise', 'Montant Restant',
                        'Date Creation', 'Date Validite', 'Statut',
                        'N Facture Utilisation', 'Est Enfant'
                    ])
                    
                    avoirs = self.avoir_manager.get_avoirs_list('Tous')
                    for avoir in avoirs:
                        montant = float(avoir[8]) if avoir[8] else 0
                        montant_utilise = float(avoir[19]) if len(avoir) > 19 and avoir[19] else 0
                        montant_restant = float(avoir[20]) if len(avoir) > 20 and avoir[20] else montant
                        est_enfant = 'Oui' if (len(avoir) > 23 and avoir[23]) else 'Non'
                        
                        writer.writerow([
                            avoir[1], avoir[2], avoir[3], avoir[4] or '',
                            f"{montant:.0f}",
                            f"{montant_utilise:.0f}",
                            f"{montant_restant:.0f}",
                            avoir[10], avoir[11], avoir[12],
                            avoir[21] if len(avoir) > 21 else '',
                            est_enfant
                        ])
                
                messagebox.showinfo("Succes", f" Export reussi: {filename}")
                self.db.add_log(self.user[1], "EXPORT_CSV", filename)
                self.update_status(f"Export CSV: {filename}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
    
    def export_excel(self):
        """Export Excel avance"""
        pass
    
    def logout(self):
        """Deconnexion : revient a l'ecran de connexion sans fermer le programme."""
        if messagebox.askyesno("Deconnexion", "Voulez-vous vraiment vous deconnecter?"):
            self.db.add_log(self.user[1], "LOGOUT", "Deconnexion")
            self.relogin = True
            self.cleanup()
            self.root.quit()
    
    def quit_app(self):
        """Quitter l'application completement."""
        if messagebox.askyesno("Quitter", "Voulez-vous vraiment quitter l'application?"):
            self.db.add_log(self.user[1], "QUIT", "Fermeture application")
            self.relogin = False
            self.cleanup()
            self.root.quit()
    
    def cleanup(self):
        """Nettoyage avant fermeture"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def generate_pdf(self, numero_avoir, data):
        """Generation du bon d'avoir en PDF avec tampon entreprise"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
            from reportlab.graphics.barcode import code128
            from reportlab.graphics.shapes import Drawing, Rect
            from pathlib import Path
            
            # Chemin du PDF
            pdf_path = BASE_PATH / f"avoir_{numero_avoir.replace('/', '_')}.pdf"
            
            # Creation du document avec marges reduites
            doc = SimpleDocTemplate(
                str(pdf_path), 
                pagesize=A4,
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=8*mm,
                bottomMargin=8*mm
            )
            elements = []
            styles = getSampleStyleSheet()
            
            # Styles personnalises avec tailles reduites
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#000000'),
                alignment=TA_CENTER,
                spaceAfter=1*mm,
                fontName='Helvetica-Bold'
            )
            
            # EN-TTE AVEC LOGO ET CODE-BARRES CTE A CTE
            header_data = []
            header_row = []
            
            # Logo a gauche
            logo_path = Path(r"W:\STOYANN\assets\logo_carre_qc.jpg")
            if not logo_path.exists():
                logo_path = BASE_PATH / "logo.jpg"
            
            if logo_path.exists():
                try:
                    logo = Image(str(logo_path), width=25*mm, height=25*mm)
                    header_row.append(logo)
                except:
                    header_row.append('')
            else:
                header_row.append('')
            
            # Titre et infos au centre
            company_info = """<b>QUINCAILLERIE CALEDONIENNE</b><br/>
            <font size="8">13 Rue Ampere - Ducos, Nouvelle-Caledonie<br/>
             27 27 00 |  www.quincaillerie.nc |  info@quincaillerie.nc </font>"""
            
            company_style = ParagraphStyle(
                'Company',
                parent=styles['Normal'],
                fontSize=14,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#000000')
            )
            header_row.append(Paragraph(company_info, company_style))
            
            # Code-barres a droite
            barcode_value = numero_avoir.replace('/', '')
            barcode = code128.Code128(barcode_value, barWidth=0.4*mm, barHeight=12*mm)
            barcode_container = Table([[barcode], [Paragraph(f"<font size='7'><b>{barcode_value}</b></font>", styles['Normal'])]])
            barcode_container.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            header_row.append(barcode_container)
            
            header_data.append(header_row)
            
            # Creer le tableau d'en-tete
            header_table = Table(header_data, colWidths=[50*mm, 90*mm, 50*mm])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(header_table)
            
            # Horaires
            horaires_data = [['Horaires: Lun-Ven 7h-17h | Sam 7h30-16h | Dim Ferme']]
            horaires_table = Table(horaires_data, colWidths=[190*mm])
            horaires_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff001')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#000000')),
            ]))
            elements.append(Spacer(1, 2*mm))
            elements.append(horaires_table)
            elements.append(Spacer(1, 3*mm))
            
            # TITRE DU DOCUMENT
            doc_title = Paragraph("<b>BON D'AVOIR</b>", ParagraphStyle(
                'DocTitle',
                fontSize=18,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=3*mm
            ))
            elements.append(doc_title)
            
            # Note sur le type
            type_note = Paragraph(
                "<i>Type: RETOUR</i>",
                ParagraphStyle(
                    'TypeNote',
                    fontSize=10,
                    alignment=TA_CENTER,
                    textColor=colors.HexColor('#666666'),
                    spaceAfter=3*mm
                )
            )
            elements.append(type_note)
            
            # Informations de l'avoir
            info_data = [
                ['N Avoir:', numero_avoir],
                ['Date de creation:', data.get('date_creation', '')],
                ['Client:', data.get('nom_client', '')],
                ['Email:', data.get('email_client', '')],
                ['Montant total:', f"{float(data.get('montant', 0)):.0f} XPF"],
                ['Montant utilise:', f"{float(data.get('montant_utilise', 0)):.0f} XPF"],
                ['Montant restant:', f"{float(data.get('montant_restant', 0)):.0f} XPF"],
                ['Validite jusqu\'au:', data.get('date_validite', '')],
                ['Statut:', data.get('statut', '')]
            ]

            info_table = Table(info_data, colWidths=[50*mm, 140*mm])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 5*mm))
            # Remerciements
            thanks = Paragraph(
                "Merci de votre confiance et a bientot !",
                ParagraphStyle(
                    'Thanks',
                    fontSize=12,
                    alignment=TA_CENTER,
                    textColor=colors.HexColor('#000000'),
                    spaceAfter=5*mm,
                    fontName='Helvetica-Oblique'
                )
            )
            elements.append(thanks)
            elements.append(Spacer(1, 10*mm))
            
            
            # Generation du PDF
            doc.build(elements)
            
            # Ouvrir le PDF automatiquement
            if os.name == 'nt':
                os.startfile(str(pdf_path))
            elif os.name == 'posix':
                os.system(f'open "{pdf_path}"')
            
            print(f" PDF genere avec succes: {pdf_path}")
            self.update_status(f"PDF genere: {pdf_path}")
            
        except ImportError:
            messagebox.showwarning(
                "Module manquant",
                "Le module reportlab n'est pas installe.\n"
                "Installez-le avec: pip install reportlab Pillow"
            )
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la generation: {str(e)}")
            print(f" Erreur PDF: {e}")
            import traceback
            traceback.print_exc()