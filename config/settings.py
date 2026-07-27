


# -*- coding: utf-8 -*-
"""
=============================================================================
                    CONFIGURATION GENERALE - SETTINGS
=============================================================================
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne
Entreprise: STOYANN
Version: 1.4 - XPF (Franc Pacifique)

Ce fichier contient toutes les constantes et paramètres de configuration
de l'application. Aucune logique métier, uniquement des valeurs.
=============================================================================
"""

from datetime import datetime

# =============================================================================
# CONFIGURATION SMTP POUR L'ENVOI D'EMAILS
# =============================================================================
SMTP_CONFIG = {
    'SMTP_HOST': 'smtp.hostinger.com',
    'SMTP_PORT': 465,
    'SMTP_EMAIL': 'support@robot-nc.com',
    'SMTP_PASSWORD': 'Stoyann_19031985',
    'FROM_NAME': 'Quincaillerie Caledonienne',
    'FROM_EMAIL': 'support@robot-nc.com'
}

# =============================================================================
# ROLES UTILISATEURS
# =============================================================================
USER_ROLES = {
    'SUPER_USER': 'super_user',
    'RESPONSABLE': 'responsable',
    'COMPTABILITE': 'comptabilite',
    'VENDEUR': 'vendeur'
}

# =============================================================================
# STATUTS DES AVOIRS
# =============================================================================
AVOIR_STATUS = {
    'ACTIF': 'actif',
    'UTILISE': 'utilise',
    'UTILISE_PARTIELLEMENT': 'utilise_partiellement',
    'EXPIRE': 'expire',
    'ANNULE': 'annule',
    'SUPPRIME': 'supprime',
    'BLOQUE': 'bloque'
}

# =============================================================================
# TYPES D'AVOIRS
# =============================================================================
AVOIR_TYPES = {
    'RETOUR': 'Retour marchandise',
    'ERREUR': 'Erreur de facturation',
    'GESTE': 'Geste commercial',
    'AUTRE': 'Autre'
}

# =============================================================================
# TYPES D'UTILISATION
# =============================================================================
UTILISATION_TYPES = {
    'TOTALE': 'total',
    'PARTIELLE': 'partiel'
}

# =============================================================================
# CONFIGURATION DE L'INTERFACE UTILISATEUR
# =============================================================================
UI_CONFIG = {
    'LOGIN_WIDTH': 450,
    'LOGIN_HEIGHT': 550,
    'MAIN_WIDTH': 1400,
    'MAIN_HEIGHT': 900,
    'WINDOW_TITLE': 'Module de Gestion des Avoirs - Quincaillerie Caledonienne',
    'DATE_FORMAT': '%d/%m/%Y',
    'DATETIME_FORMAT': '%d/%m/%Y %H:%M',
    'CURRENCY': 'XPF',
    'CURRENCY_SYMBOL': 'F',
    'THOUSANDS_SEPARATOR': ' '
}

# =============================================================================
# CONFIGURATION DES AVOIRS
# =============================================================================
AVOIR_CONFIG = {
    'VALIDITY_DAYS': 90,
    'VALIDITE_JOURS': 90,
    'BARCODE_PREFIX': 'AV',
    'YEAR_FORMAT': '%y',
    'NUMBER_LENGTH': 5,
    'REMINDER_DAYS_BEFORE_EXPIRY': 15,
    'RAPPEL_JOURS': 15,
    'TYPE_DEFAUT': 'Retour marchandise'
}

# =============================================================================
# CONFIGURATION DES RAPPORTS ET ENTREPRISE
# =============================================================================
REPORT_CONFIG = {
    'COMPANY_NAME': 'Quincaillerie Caledonienne',
    'COMPANY_FULL_NAME': 'QUINCAILLERIE CALEDONIENNE SARL',
    'COMPANY_ADDRESS': '13 rue Ampere - Ducos',
    'COMPANY_CITY': '98800 Noumea',
    'COMPANY_PHONE': '27 47 22',
    'COMPANY_EMAIL': 'quincaillerie.caledonienne@gmail.com',
    'COMPANY_RIDET': '123456789',
    'REPORT_FOOTER': 'Quincaillerie Caledonienne - Module Gestion des Avoirs'
}

# =============================================================================
# COULEURS DE L'INTERFACE (THEME QUINCAILLERIE)
# =============================================================================
COLORS = {
    'primary': '#fff001',       # Jaune QC
    'secondary': '#000000',     # Noir
    'success': '#4CAF50',       # Vert
    'warning': '#FF9800',       # Orange
    'danger': '#f44336',        # Rouge
    'info': '#2196F3',          # Bleu
    'light': '#f5f5f5',         # Gris clair
    'dark': '#212121',          # Gris foncé
    'white': '#ffffff',         # Blanc
    'text_primary': '#333333',  # Texte principal
    'text_secondary': '#666666', # Texte secondaire
    'border': '#e0e0e0',        # Bordures
    'hover': '#f0f0f0',         # Survol
    'active': '#fff001'         # Actif
}

# =============================================================================
# MESSAGES D'ERREUR
# =============================================================================
ERROR_MESSAGES = {
    'AVOIR_NOT_FOUND': "L'avoir n'existe pas ou n'est pas valide",
    'AVOIR_EXPIRED': "Cet avoir a expire",
    'AVOIR_ALREADY_USED': "Cet avoir a deja ete utilise totalement",
    'AVOIR_BLOQUE': "Cet avoir est BLOQUE. Demandez au client de passer a la comptabilite.",
    'FORCAGE_RESPONSABLE_REQUIS': "Le nom du responsable ayant autorise le forcage est obligatoire",
    'BLOCAGE_COMMENTAIRE_REQUIS': "Un commentaire est obligatoire pour bloquer un avoir",
    'MONTANT_SUPERIEUR': "Le montant de la facture ({montant_facture} F) est superieur au montant de l'avoir ({montant_avoir} F)",
    'MONTANT_INVALID': "Montant invalide: {montant}",
    'MONTANT_NEGATIF': "Le montant doit etre positif",
    'FACTURE_REQUIRED': "Le numero de facture est obligatoire",
    'INVALID_AMOUNT': "Montant invalide",
    'ACCESS_DENIED': "Acces refuse",
    'USER_NOT_FOUND': "Utilisateur non trouve",
    'INVALID_CREDENTIALS': "Identifiants incorrects",
    'DUPLICATE_ENTRY': "Cette entree existe deja",
    'DATABASE_ERROR': "Erreur de base de donnees"
}

# =============================================================================
# MESSAGES DE SUCCES
# =============================================================================
SUCCESS_MESSAGES = {
    'AVOIR_CREATED': "Avoir {numero} cree avec succes",
    'AVOIR_USED': "Avoir {numero} utilise avec succes sur la facture {facture}",
    'AVOIR_USED_TOTAL': "Avoir {numero_avoir} utilise en totalite ({montant} F).",
    'AVOIR_USED_PARTIAL': "Avoir {numero_avoir} utilise partiellement ({montant_facture} F sur {montant_avoir} F).",
    'AVOIR_CHILD_CREATED': "Nouvel avoir {numero_avoir} cree pour le solde restant de {montant_restant}.",
    'AVOIR_CANCELLED': "Avoir {numero_avoir} annule avec succes.",
    'AVOIR_BLOCKED': "Avoir {numero_avoir} bloque avec succes. Le client doit passer a la comptabilite.",
    'AVOIR_UNBLOCKED': "Avoir {numero_avoir} debloque avec succes (statut: {statut}).",
    'AVOIR_FORCED': "Avoir expire {numero_avoir} force avec succes (autorise par: {responsable}).",
    'EMAIL_SENT': "Email envoye avec succes a {email}",
    'USER_CREATED': "Utilisateur {username} cree avec succes",
    'USER_UPDATED': "Utilisateur {username} mis a jour",
    'PDF_GENERATED': "PDF genere avec succes: {filename}"
}

# =============================================================================
# CONFIGURATION DES EXPORTS
# =============================================================================
EXPORT_CONFIG = {
    'CSV_DELIMITER': ';',
    'CSV_ENCODING': 'utf-8-sig',
    'DATE_FORMAT_EXPORT': '%Y-%m-%d',
    'EXPORT_PATH': None  # Sera défini par init_paths()
}

# =============================================================================
# CONFIGURATION DES PDF
# =============================================================================
PDF_CONFIG = {
    'PAGE_SIZE': 'A4',
    'MARGIN_TOP': 30,
    'MARGIN_BOTTOM': 30,
    'MARGIN_LEFT': 20,
    'MARGIN_RIGHT': 20,
    'FONT_FAMILY': 'Helvetica',
    'FONT_SIZE_TITLE': 16,
    'FONT_SIZE_NORMAL': 10,
    'FONT_SIZE_SMALL': 8,
    'LOGO_PATH': None,   # Sera défini par init_paths()
    'OUTPUT_PATH': None  # Sera défini par init_paths()
}

# =============================================================================
# CONFIGURATION DES LOGS
# =============================================================================
LOG_CONFIG = {
    'MAX_LOG_FILES': 30,
    'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(message)s',
    'LOG_DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
    'LOG_FILE_PREFIX': 'avoirs_log_'
}

# =============================================================================
# PERMISSIONS PAR ROLE
# =============================================================================
PERMISSIONS = {
    'super_user': [
        'create_avoir', 'use_avoir', 'view_avoir', 'delete_avoir', 'cancel_avoir',
        'export_data', 'manage_users', 'view_logs', 'send_email',
        'generate_reports', 'modify_settings', 'backup_db', 'view_deleted',
        'force_avoir', 'block_avoir', 'unblock_avoir'
    ],
    'responsable': [
        'create_avoir', 'use_avoir', 'view_avoir',
        'export_data', 'view_logs', 'send_email', 'generate_reports',
        'force_avoir', 'block_avoir', 'unblock_avoir'
    ],
    # La comptabilité a, pour le moment, exactement les mêmes droits que le responsable.
    'comptabilite': [
        'create_avoir', 'use_avoir', 'view_avoir',
        'export_data', 'view_logs', 'send_email', 'generate_reports',
        'force_avoir', 'block_avoir', 'unblock_avoir'
    ],
    'vendeur': [
        'use_avoir', 'view_avoir', 'force_avoir'
    ]
}

# =============================================================================
# VALIDATION DES DONNEES
# =============================================================================
VALIDATION = {
    'CLIENT_NUMBER_MIN_LENGTH': 1,
    'CLIENT_NUMBER_MAX_LENGTH': 20,
    'INVOICE_NUMBER_MIN_LENGTH': 1,
    'INVOICE_NUMBER_MAX_LENGTH': 50,
    'MIN_AMOUNT': 1,
    'MAX_AMOUNT': 100000000,
    'EMAIL_REGEX': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
}


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_current_year():
    """
    Retourne l'année en cours au format court (2 chiffres).
    
    Returns:
        str: L'année au format YY (ex: "26" pour 2026)
    """
    return datetime.now().strftime(AVOIR_CONFIG['YEAR_FORMAT'])


def format_currency(amount):
    """
    Formate un montant en XPF avec séparateur de milliers.
    
    Args:
        amount: Le montant à formater (int, float, str ou None)
        
    Returns:
        str: Le montant formaté (ex: "150 000 F")
    """
    if amount is None:
        return "0 F"
    try:
        amount = float(amount)
        # Formatage avec séparateur de milliers (espace)
        formatted = "{:,.0f}".format(amount).replace(",", " ")
        return f"{formatted} F"
    except (ValueError, TypeError):
        return "0 F"


def parse_currency(value):
    """
    Parse une valeur monétaire et retourne un float.
    
    Args:
        value: La valeur à parser (peut contenir espaces, "F", virgules)
        
    Returns:
        float: La valeur numérique
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    # Nettoyer la valeur
    clean = str(value).replace(" ", "").replace("F", "").replace(",", ".").strip()
    try:
        return float(clean)
    except ValueError:
        return 0


# Alias pour compatibilité avec l'ancien code
format_montant = format_currency