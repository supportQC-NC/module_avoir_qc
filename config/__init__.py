# -*- coding: utf-8 -*-
"""
=============================================================================
                    MODULE CONFIG - EXPORTS
=============================================================================
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce fichier centralise tous les exports du module config pour permettre
des imports simples:
    from config import SMTP_CONFIG, COLORS, format_montant
    
au lieu de:
    from config.settings import SMTP_CONFIG, COLORS
    from config.settings import format_montant
=============================================================================
"""

# -----------------------------------------------------------------------------
# Imports depuis settings.py
# -----------------------------------------------------------------------------
from config.settings import (
    # Configuration SMTP
    SMTP_CONFIG,
    
    # Rôles et permissions
    USER_ROLES,
    PERMISSIONS,
    
    # Statuts et types d'avoirs
    AVOIR_STATUS,
    AVOIR_TYPES,
    UTILISATION_TYPES,
    
    # Configuration UI
    UI_CONFIG,
    COLORS,
    
    # Configuration des avoirs
    AVOIR_CONFIG,
    
    # Configuration rapports et entreprise
    REPORT_CONFIG,
    
    # Messages
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    
    # Configuration exports/PDF/logs
    EXPORT_CONFIG,
    PDF_CONFIG,
    LOG_CONFIG,
    
    # Validation
    VALIDATION,
    
    # Fonctions utilitaires
    get_current_year,
    format_currency,
    format_montant,  # Alias pour compatibilité
    parse_currency
)

# -----------------------------------------------------------------------------
# Imports depuis paths.py
# -----------------------------------------------------------------------------
from config.paths import (
    # Fichier de config
    CONFIG_FILE,
    
    # Variables globales de chemins
    BASE_PATH,
    DB_PATH,
    LOG_PATH,
    
    # Fonctions de configuration persistante
    load_persistent_config,
    save_persistent_config,
    
    # Gestion du chemin de base
    get_base_path,
    set_base_path,
    
    # Gestion première exécution
    is_first_run,
    mark_as_initialized,
    
    # Configuration admin
    get_admin_config,
    save_admin_config,
    
    # Chemins
    get_paths,
    init_paths,
    get_file_path
)

# -----------------------------------------------------------------------------
# Imports depuis email_templates.py
# -----------------------------------------------------------------------------
from config.email_templates import (
    EMAIL_TEMPLATES,
    format_email_template
)

# -----------------------------------------------------------------------------
# Liste des exports publics
# -----------------------------------------------------------------------------
__all__ = [
    # Settings
    'SMTP_CONFIG',
    'USER_ROLES',
    'PERMISSIONS',
    'AVOIR_STATUS',
    'AVOIR_TYPES',
    'UTILISATION_TYPES',
    'UI_CONFIG',
    'COLORS',
    'AVOIR_CONFIG',
    'REPORT_CONFIG',
    'ERROR_MESSAGES',
    'SUCCESS_MESSAGES',
    'EXPORT_CONFIG',
    'PDF_CONFIG',
    'LOG_CONFIG',
    'VALIDATION',
    'get_current_year',
    'format_currency',
    'format_montant',
    'parse_currency',
    
    # Paths
    'CONFIG_FILE',
    'BASE_PATH',
    'DB_PATH',
    'LOG_PATH',
    'load_persistent_config',
    'save_persistent_config',
    'get_base_path',
    'set_base_path',
    'is_first_run',
    'mark_as_initialized',
    'get_admin_config',
    'save_admin_config',
    'get_paths',
    'init_paths',
    'get_file_path',
    
    # Email templates
    'EMAIL_TEMPLATES',
    'format_email_template'
]
