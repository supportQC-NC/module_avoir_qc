# -*- coding: utf-8 -*-
"""
=============================================================================
                    TEMPLATES D'EMAILS
=============================================================================
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne
Entreprise: STOYANN

Ce fichier contient tous les templates d'emails utilisés par l'application.
Les templates utilisent des placeholders {variable} pour l'injection de données.
=============================================================================
"""

# =============================================================================
# TEMPLATES D'EMAILS
# =============================================================================

EMAIL_TEMPLATES = {
    # -------------------------------------------------------------------------
    # Email de création d'avoir
    # -------------------------------------------------------------------------
    'CREATION_AVOIR': {
        'subject': 'Votre avoir Quincaillerie Calédonienne N°{numero_avoir}',
        'body': """
Bonjour {nom_client},

Nous vous confirmons la création de votre avoir N°{numero_avoir} d'un montant de {montant_formate} XPF.

Détails de l'avoir :
- Numéro de facture concernée : {numero_facture}
- Type d'avoir : {type_avoir}
- Date de création : {date_creation}
- Date de validité : {date_validite}

Cet avoir est valable jusqu'au {date_validite} et peut être utilisé dans notre magasin sur présentation du document original.

CONDITIONS D'UTILISATION :
- Avoir à utiliser en magasin avant le délai sous présentation de cet avoir (original fourni par le magasin)
- En cas de perte, l'avoir ne pourra pas être réémis
- L'avoir peut être utilisé partiellement, un nouvel avoir sera émis pour le solde restant


Cordialement,
L'équipe Quincaillerie Calédonienne
"""
    },
    
    # -------------------------------------------------------------------------
    # Email de rappel avant expiration
    # -------------------------------------------------------------------------
    'RAPPEL_EXPIRATION': {
        'subject': 'Rappel : Votre avoir Quincaillerie Calédonienne N°{numero_avoir} expire bientôt',
        'body': """
Bonjour {nom_client},

Nous vous rappelons que votre avoir N°{numero_avoir} d'un montant de {montant_formate} XPF expire le {date_validite}.

Il vous reste {jours_restants} jours pour l'utiliser dans notre magasin.

Montant restant à utiliser : {montant_restant} XPF

N'hésitez pas à venir nous voir pour utiliser votre avoir avant son expiration.

Cordialement,
L'équipe Quincaillerie Calédonienne
"""
    },
    
    # -------------------------------------------------------------------------
    # Email d'utilisation partielle
    # -------------------------------------------------------------------------
    'UTILISATION_PARTIELLE': {
        'subject': 'Utilisation partielle de votre avoir N°{numero_avoir}',
        'body': """
Bonjour {nom_client},

Votre avoir N°{numero_avoir} a été utilisé partiellement.

Détails de l'utilisation :
- Montant utilisé : {montant_utilise} XPF
- Numéro de facture : {numero_facture_utilisation}
- Date d'utilisation : {date_utilisation}

Un nouvel avoir N°{numero_avoir_enfant} a été créé pour le solde restant de {montant_restant} XPF.

Cordialement,
L'équipe Quincaillerie Calédonienne
"""
    },
    
    # -------------------------------------------------------------------------
    # Email d'utilisation totale
    # -------------------------------------------------------------------------
    'UTILISATION_TOTALE': {
        'subject': 'Utilisation de votre avoir N°{numero_avoir}',
        'body': """
Bonjour {nom_client},

Votre avoir N°{numero_avoir} a été utilisé en totalité.

Détails de l'utilisation :
- Montant utilisé : {montant_utilise} XPF
- Numéro de facture : {numero_facture_utilisation}
- Date d'utilisation : {date_utilisation}

Merci de votre confiance.

Cordialement,
L'équipe Quincaillerie Calédonienne
"""
    }
}


# =============================================================================
# FONCTION UTILITAIRE POUR FORMATER UN TEMPLATE
# =============================================================================

def format_email_template(template_name, data):
    """
    Formate un template d'email avec les données fournies.
    
    Args:
        template_name (str): Nom du template (clé dans EMAIL_TEMPLATES)
        data (dict): Dictionnaire avec les valeurs à injecter
        
    Returns:
        tuple: (subject, body) formatés ou (None, None) si erreur
        
    Example:
        subject, body = format_email_template('CREATION_AVOIR', {
            'numero_avoir': '2600001',
            'nom_client': 'Jean Dupont',
            'montant_formate': '15 000 F',
            ...
        })
    """
    if template_name not in EMAIL_TEMPLATES:
        return None, None
    
    template = EMAIL_TEMPLATES[template_name]
    
    try:
        subject = template['subject'].format(**data)
        body = template['body'].format(**data)
        return subject, body
    except KeyError as e:
        print(f"Erreur de template: clé manquante {e}")
        return None, None