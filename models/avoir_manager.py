# -*- coding: utf-8 -*-
"""
Gestionnaire des avoirs
Module de Gestion des Avoirs Clients - Quincaillerie Calédonienne

Ce module gère toutes les opérations liées aux avoirs:
- Création d'avoirs (avec numérotation automatique YYXXXXX)
- Utilisation partielle ou totale
- Génération d'avoirs enfants pour le reste
- Statistiques et rapports
"""

from datetime import datetime, timedelta

from config.settings import (
    AVOIR_CONFIG, AVOIR_STATUS, UTILISATION_TYPES,
    format_montant, ERROR_MESSAGES, SUCCESS_MESSAGES
)


class AvoirManager:
    """
    Gestionnaire des avoirs.
    
    Gère le cycle de vie complet des avoirs:
    - Création avec numérotation automatique
    - Utilisation (partielle ou totale)
    - Génération d'avoirs enfants
    - Annulation et suppression
    - Statistiques
    
    Attributes:
        db: Instance de Database pour les opérations SQL
        email_service: Service d'envoi d'emails (optionnel)
    """
    
    def __init__(self, db, email_service=None):
        """
        Initialise le gestionnaire.
        
        Args:
            db: Instance de Database
            email_service: Instance de EmailService (optionnel)
        """
        self.db = db
        self.email_service = email_service
    
    # ══════════════════════════════════════════════════════════════════════════════
    # GÉNÉRATION DE NUMÉRO
    # ══════════════════════════════════════════════════════════════════════════════
    
    def generate_numero_avoir(self):
        """
        Génère un nouveau numéro d'avoir au format YYXXXXX (sans slash).
        
        Format: 2 chiffres année + 5 chiffres séquentiels
        Exemple: 2600001 pour le 1er avoir de 2026
        
        Returns:
            str: Numéro d'avoir généré
        """
        year = datetime.now().strftime("%y")
        
        # Récupérer TOUS les numéros de l'année (ancien format YY/XXXXX ET nouveau YYXXXXX).
        # On ne se base PAS sur la seule "dernière ligne" : quand les deux formats
        # coexistent, la dernière ligne par id n'a pas forcément le plus grand numéro
        # de séquence, ce qui regénérait un numéro déjà pris -> IntegrityError UNIQUE.
        rows = self.db.cursor.execute(
            """SELECT numero_avoir FROM avoirs 
               WHERE numero_avoir LIKE ? OR numero_avoir LIKE ?""",
            (f"{year}%", f"{year}/%")
        ).fetchall()
        
        max_num = 0
        existants = set()
        for row in rows:
            numero = str(row[0])
            existants.add(numero.replace('/', ''))  # numéro normalisé sans slash
            try:
                seq = int(numero.split('/')[1]) if '/' in numero else int(numero[2:])
                if seq > max_num:
                    max_num = seq
            except (ValueError, IndexError):
                continue
        
        # Incrémenter jusqu'à trouver un numéro réellement libre (garantie anti-collision)
        new_num = max_num + 1
        nouveau = f"{year}{new_num:05d}"
        while nouveau in existants:
            new_num += 1
            nouveau = f"{year}{new_num:05d}"
        
        # Nouveau format sans slash: YYXXXXX (ex: 2600001)
        return nouveau
    
    def normalize_numero_avoir(self, numero_avoir):
        """
        Normalise un numéro d'avoir (gère les anciens formats avec /).
        
        Args:
            numero_avoir: Numéro à normaliser
            
        Returns:
            str: Numéro normalisé sans slash
        """
        numero_avoir = str(numero_avoir)
        if '/' in numero_avoir:
            # Ancien format: convertir XX/XXXXX en XXXXXXX
            parts = numero_avoir.split('/')
            return f"{parts[0]}{parts[1]}"
        return numero_avoir
    
    # ══════════════════════════════════════════════════════════════════════════════
    # CRÉATION D'AVOIRS
    # ══════════════════════════════════════════════════════════════════════════════
    
    def create_avoir(self, data):
        """
        Crée un nouvel avoir.
        
        Args:
            data (dict): Données de l'avoir avec les clés:
                - numero_client: Numéro client
                - nom_client: Nom du client
                - email_client: Email (optionnel)
                - numero_facture: Numéro facture origine
                - date_facture: Date facture (format JJ/MM/AAAA)
                - montant: Montant de l'avoir
                - numero_facture_avoir: Numéro facture avoir (optionnel)
                - utilisateur: Utilisateur créateur
                - signature: Signature (optionnel)
                - send_email: Envoyer email de confirmation (bool)
                
        Returns:
            str: Numéro de l'avoir créé
        """
        numero_avoir = self.generate_numero_avoir()
        date_validite = datetime.now() + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
        
        type_avoir = AVOIR_CONFIG['TYPE_DEFAUT']
        
        # Parser la date de facture
        date_facture_str = data.get('date_facture', '')
        date_facture = None
        if date_facture_str:
            try:
                parts = date_facture_str.split('/')
                if len(parts) == 3:
                    jour, mois, annee = parts
                    date_facture = datetime(int(annee), int(mois), int(jour))
            except (ValueError, IndexError):
                pass
        
        # Nettoyer le montant
        montant = float(str(data['montant']).replace(' ', '').replace(',', '.'))
        
        # Insertion en base
        self.db.cursor.execute('''
            INSERT INTO avoirs (
                numero_avoir, numero_client, nom_client, email_client,
                numero_facture, date_facture, type_avoir, montant, 
                montant_restant, montant_utilise,
                numero_facture_avoir, date_validite, utilisateur_creation, 
                signature, est_avoir_enfant, avoir_parent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero_avoir, 
            data['numero_client'], 
            data['nom_client'],
            data.get('email_client', ''),
            data['numero_facture'], 
            date_facture,
            type_avoir,
            montant,
            montant,
            0,
            data.get('numero_facture_avoir', ''),
            date_validite, 
            data['utilisateur'], 
            data.get('signature', ''),
            data.get('est_avoir_enfant', 0),
            data.get('avoir_parent_id', None)
        ))
        
        self.db.conn.commit()
        self.db.add_log(data['utilisateur'], "CREATION_AVOIR", f"Avoir {numero_avoir} (type: {type_avoir})")
        
        # Envoi email si demandé
        if data.get('send_email') and data.get('email_client') and self.email_service:
            avoir_data = {
                'numero_avoir': numero_avoir,
                'nom_client': data['nom_client'],
                'email_client': data['email_client'],
                'montant': montant,
                'montant_formate': format_montant(montant),
                'numero_facture': data['numero_facture'],
                'type_avoir': type_avoir,
                'date_validite': date_validite,
                'date_creation': datetime.now().strftime('%d/%m/%Y')
            }
            self.email_service.send_avoir_confirmation(avoir_data)
        
        return numero_avoir
    
    def create_avoir_enfant(self, avoir_parent, montant_restant, utilisateur):
        """
        Crée un avoir enfant pour le montant restant après utilisation partielle.
        
        L'avoir enfant hérite des propriétés du parent (client, facture, etc.)
        mais reçoit SA PROPRE validité de 90 jours à partir de sa création.
        
        Args:
            avoir_parent: Tuple des données de l'avoir parent
            montant_restant: Montant à reporter sur l'avoir enfant
            utilisateur: Utilisateur effectuant l'opération
            
        Returns:
            tuple: (numero_avoir, avoir_enfant_complet, date_validite)
        """
        numero_avoir = self.generate_numero_avoir()

        # L'avoir enfant (résidu) reçoit SA PROPRE validité de 90 jours à partir
        # de sa date de création, et N'HÉRITE PAS de la validité du parent.
        # Ainsi un résidu fraîchement édité n'est jamais considéré comme expiré :
        # le forçage n'est requis que si le résidu lui-même a été édité il y a
        # plus de 90 jours (3 mois).
        date_validite = datetime.now() + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
        
        # Insertion de l'avoir enfant
        self.db.cursor.execute('''
            INSERT INTO avoirs (
                numero_avoir, numero_client, nom_client, email_client,
                numero_facture, date_facture, type_avoir, montant,
                montant_restant, montant_utilise,
                numero_facture_avoir, date_validite, utilisateur_creation,
                signature, est_avoir_enfant, avoir_parent_id, statut
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero_avoir,
            avoir_parent[2],   # numero_client
            avoir_parent[3],   # nom_client
            avoir_parent[4],   # email_client
            avoir_parent[5],   # numero_facture
            avoir_parent[6],   # date_facture
            avoir_parent[7],   # type_avoir
            montant_restant,
            montant_restant,
            0,
            avoir_parent[9],   # numero_facture_avoir
            date_validite,
            utilisateur,
            avoir_parent[16],  # signature
            1,                 # est_avoir_enfant
            avoir_parent[0],   # avoir_parent_id
            AVOIR_STATUS['ACTIF']
        ))
        
        self.db.conn.commit()
        self.db.add_log(utilisateur, "CREATION_AVOIR_ENFANT", 
                       f"Avoir enfant {numero_avoir} créé (parent: {avoir_parent[1]}, montant: {montant_restant} XPF)")
        
        # Récupérer l'avoir enfant complet
        avoir_enfant_complet = self.db.cursor.execute(
            """SELECT id, numero_avoir, numero_client, nom_client, email_client,
                      numero_facture, date_facture, type_avoir, montant,
                      numero_facture_avoir, date_creation, date_validite, statut,
                      date_utilisation, utilisateur_creation, utilisateur_validation,
                      signature, email_envoye, rappel_envoye, montant_utilise,
                      montant_restant, numero_facture_utilisation, avoir_parent_id,
                      est_avoir_enfant
               FROM avoirs WHERE numero_avoir = ?""",
            (numero_avoir,)
        ).fetchone()
        
        print(f" Avoir enfant créé: {numero_avoir}")
        print(f"   Données complètes récupérées: {avoir_enfant_complet is not None}")
        
        return numero_avoir, avoir_enfant_complet, date_validite
    
    # ══════════════════════════════════════════════════════════════════════════════
    # UTILISATION D'AVOIRS
    # ══════════════════════════════════════════════════════════════════════════════
    
    def _parse_date(self, value):
        """
        Convertit une date stockée (str ou datetime) en objet datetime.
        Retourne None si la valeur est vide ou illisible.
        Gère les formats : datetime, ISO 'AAAA-MM-JJ[ T]...', et 'JJ/MM/AAAA'.
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        s = str(value).strip()
        if not s:
            return None
        try:
            if 'T' in s:
                return datetime.fromisoformat(s.split('T')[0])
            if '/' in s:
                p = s.split('/')
                return datetime(int(p[2]), int(p[1]), int(p[0]))
            return datetime.fromisoformat(s.split(' ')[0])
        except (ValueError, IndexError):
            return None

    def is_avoir_expire(self, avoir_row):
        """
        Indique si un avoir est expiré.

        Règle métier : un avoir expire 90 jours (VALIDITE_JOURS) APRÈS sa date
        de CRÉATION (= date d'édition). On NE se base PAS sur date_validite, qui
        a pu être héritée/faussée pour d'anciens résidus. Ainsi le forçage n'est
        requis QUE si l'avoir a été édité il y a plus de 90 jours (≈ 3 mois).

        avoir_row : tuple issu d'un SELECT (index 10 = date_creation, 12 = statut).
        En cas de doute (date illisible), on considère l'avoir NON expiré pour
        ne pas imposer de forçage abusif.
        """
        try:
            if avoir_row[12] == AVOIR_STATUS['EXPIRE']:
                return True
            date_creation = self._parse_date(avoir_row[10])
            if date_creation is None:
                return False
            date_expiration = date_creation + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
            return datetime.now() > date_expiration
        except Exception:
            return False

    def use_avoir(self, numero_avoir, utilisateur, montant_facture, numero_facture_utilisation,
                  force=False, forcage_autorise_par=None):
        """
        Utilise un avoir avec le montant de la facture.
        
        - Si montant_facture < montant_avoir => génère automatiquement un avoir pour la différence
        - Si montant_facture >= montant_avoir => utilisation totale
        
        Args:
            numero_avoir: Numéro de l'avoir à utiliser
            utilisateur: Utilisateur effectuant l'opération
            montant_facture: Montant de la facture
            numero_facture_utilisation: Numéro de la facture d'utilisation
            force: Si True, autorise l'utilisation d'un avoir EXPIRÉ (forçage).
                   Ne lève PAS un blocage.
            forcage_autorise_par: Nom du responsable ayant autorisé le forçage.
                   Obligatoire lorsque force=True sur un avoir expiré.
            
        Returns:
            dict: Résultat avec les clés:
                - status: 'success' ou 'error'
                - message: Message descriptif
                - type_utilisation: 'partielle' ou 'totale' (si success)
                - montant_facture, montant_avoir, montant_restant (si success)
                - numero_avoir_enfant, avoir_enfant (si partielle)
        """
        if not numero_facture_utilisation:
            return {
                "status": "error", 
                "message": ERROR_MESSAGES['FACTURE_REQUIRED']
            }
        
        # Normaliser le numéro d'avoir (gérer ancien format avec /)
        numero_avoir_original = numero_avoir
        numero_avoir_normalized = self.normalize_numero_avoir(numero_avoir)
        
        # Chercher l'avoir avec les deux formats possibles
        avoir_query = """
            SELECT id, numero_avoir, numero_client, nom_client, email_client,
                   numero_facture, date_facture, type_avoir, montant,
                   numero_facture_avoir, date_creation, date_validite, statut,
                   date_utilisation, utilisateur_creation, utilisateur_validation,
                   signature, email_envoye, rappel_envoye, montant_utilise,
                   montant_restant, numero_facture_utilisation, avoir_parent_id,
                   est_avoir_enfant
            FROM avoirs WHERE numero_avoir = ? OR numero_avoir = ?
        """
        avoir = self.db.cursor.execute(avoir_query, (numero_avoir, numero_avoir_normalized)).fetchone()
        
        # Si pas trouvé, essayer avec l'ancien format (avec /)
        if not avoir and '/' not in numero_avoir and len(numero_avoir) == 7:
            ancien_format = f"{numero_avoir[:2]}/{numero_avoir[2:]}"
            avoir = self.db.cursor.execute(
                """SELECT id, numero_avoir, numero_client, nom_client, email_client,
                          numero_facture, date_facture, type_avoir, montant,
                          numero_facture_avoir, date_creation, date_validite, statut,
                          date_utilisation, utilisateur_creation, utilisateur_validation,
                          signature, email_envoye, rappel_envoye, montant_utilise,
                          montant_restant, numero_facture_utilisation, avoir_parent_id,
                          est_avoir_enfant
                   FROM avoirs WHERE numero_avoir = ?""",
                (ancien_format,)
            ).fetchone()
        
        if not avoir:
            return {
                "status": "error", 
                "message": ERROR_MESSAGES['AVOIR_NOT_FOUND'].format(numero_avoir=numero_avoir)
            }
        
        avoir_id = avoir[0]
        numero_avoir = avoir[1]  # Utiliser le numéro tel qu'en base
        statut = avoir[12]
        montant_avoir = avoir[8]
        montant_restant_actuel = avoir[20] if avoir[20] is not None else montant_avoir
        date_validite_str = avoir[11]
        
        # Vérifier le statut
        if statut == AVOIR_STATUS['UTILISE']:
            return {
                "status": "error", 
                "message": ERROR_MESSAGES['AVOIR_ALREADY_USED'].format(numero_avoir=numero_avoir)
            }
        
        # AVOIR BLOQUÉ : impossible à utiliser, même via forçage.
        # Le client doit passer à la comptabilité.
        if statut == AVOIR_STATUS['BLOQUE']:
            return {
                "status": "blocked",
                "message": ERROR_MESSAGES['AVOIR_BLOQUE']
            }
        
        if statut == AVOIR_STATUS['EXPIRE']:
            # Sans forçage : refus classique.
            if not force:
                return {
                    "status": "expired",
                    "message": ERROR_MESSAGES['AVOIR_EXPIRED'].format(numero_avoir=numero_avoir)
                }
            # Avec forçage : le nom du responsable est obligatoire.
            if not forcage_autorise_par or not str(forcage_autorise_par).strip():
                return {
                    "status": "error",
                    "message": ERROR_MESSAGES['FORCAGE_RESPONSABLE_REQUIS']
                }
            # Forçage autorisé : on poursuit l'utilisation.
        
        # Vérifier l'expiration : un avoir expire 90 jours APRÈS sa CRÉATION
        # (date d'édition), et non selon une date_validite qui a pu être héritée
        # ou faussée. Le forçage n'est donc requis que si l'avoir a été édité il
        # y a plus de 90 jours (≈ 3 mois).
        try:
            date_creation_ref = self._parse_date(avoir[10])  # date_creation
            if date_creation_ref is not None:
                date_expiration = date_creation_ref + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
                if datetime.now() > date_expiration:
                    # Validité réellement dépassée. Sans forçage : on marque expiré et on refuse.
                    if not force:
                        self.db.cursor.execute(
                            "UPDATE avoirs SET statut = ? WHERE numero_avoir = ?",
                            (AVOIR_STATUS['EXPIRE'], numero_avoir)
                        )
                        self.db.conn.commit()
                        return {
                            "status": "expired",
                            "message": ERROR_MESSAGES['AVOIR_EXPIRED'].format(numero_avoir=numero_avoir)
                        }
                    # Avec forçage : le nom du responsable est obligatoire.
                    if not forcage_autorise_par or not str(forcage_autorise_par).strip():
                        return {
                            "status": "error",
                            "message": ERROR_MESSAGES['FORCAGE_RESPONSABLE_REQUIS']
                        }
                    # Forçage autorisé : on poursuit l'utilisation.
        except Exception as e:
            print(f"Erreur lors du calcul d'expiration: {e}")
            # En cas de doute, on n'empêche pas l'utilisation (pas de forçage abusif).
        
        # Convertir le montant de la facture
        try:
            montant_facture = float(str(montant_facture).replace(' ', '').replace(',', '.'))
        except:
            return {
                "status": "error",
                "message": ERROR_MESSAGES['MONTANT_INVALID'].format(montant=montant_facture)
            }
        
        if montant_facture <= 0:
            return {
                "status": "error",
                "message": ERROR_MESSAGES['MONTANT_NEGATIF']
            }
        
        # Si l'utilisation se fait par forçage d'un avoir expiré, on trace
        # le nom du responsable ayant autorisé l'opération sur l'avoir lui-même.
        if force and forcage_autorise_par and str(forcage_autorise_par).strip():
            self.db.cursor.execute(
                "UPDATE avoirs SET forcage_autorise_par = ? WHERE numero_avoir = ?",
                (str(forcage_autorise_par).strip(), numero_avoir)
            )
            self.db.conn.commit()
            self.db.add_log(
                utilisateur, "FORCAGE_AVOIR",
                f"Avoir expiré {numero_avoir} forcé - autorisé par : {str(forcage_autorise_par).strip()}"
            )
        
        # ══════════════════════════════════════════════════════════════════════════
        # CAS 1: Montant facture > Montant avoir (AVOIR INSUFFISANT)
        # L'avoir est utilisé en totalité, le client doit payer la différence
        # ══════════════════════════════════════════════════════════════════════════
        if montant_facture > montant_restant_actuel:
            restant_a_payer = montant_facture - montant_restant_actuel
            
            print(f"→ Utilisation de l'avoir {numero_avoir} (INSUFFISANT)")
            print(f"   Montant avoir: {montant_restant_actuel} XPF")
            print(f"   Montant facture: {montant_facture} XPF")
            print(f"   Restant à payer: {restant_a_payer} XPF")
            
            # Marquer l'avoir comme utilisé (utilisation totale)
            self.db.cursor.execute(
                """UPDATE avoirs 
                   SET statut = ?, 
                       date_utilisation = ?, 
                       utilisateur_validation = ?,
                       montant_utilise = ?,
                       montant_restant = ?,
                       numero_facture_utilisation = ?
                   WHERE numero_avoir = ?""",
                (AVOIR_STATUS['UTILISE'],
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                 utilisateur, 
                 montant_restant_actuel,  # On utilise tout l'avoir
                 0,
                 numero_facture_utilisation,
                 numero_avoir)
            )
            self.db.conn.commit()
            
            # Enregistrer l'historique
            self.db.add_utilisation_history(
                avoir_id, numero_avoir, montant_restant_actuel,
                numero_facture_utilisation, utilisateur, 'insuffisant'
            )
            
            self.db.add_log(utilisateur, "UTILISATION_AVOIR_INSUFFISANT", 
                          f"Avoir {numero_avoir} utilisé: {format_montant(montant_restant_actuel)} XPF sur facture de {format_montant(montant_facture)} XPF - Restant à payer: {format_montant(restant_a_payer)} XPF")
            
            return {
                "status": "success",
                "message": f"Avoir {numero_avoir} utilisé avec succès.\n"
                          f"Montant de l'avoir: {format_montant(montant_restant_actuel)}\n"
                          f"Montant de la facture: {format_montant(montant_facture)}",
                "type_utilisation": "insuffisant",
                "montant_facture": montant_facture,
                "montant_avoir": montant_restant_actuel,
                "restant_a_payer": restant_a_payer,
                "numero_facture": numero_facture_utilisation
            }
        
        # ══════════════════════════════════════════════════════════════════════════
        # CAS 2: Montant facture < Montant avoir (UTILISATION PARTIELLE)
        # ══════════════════════════════════════════════════════════════════════════
        # Déterminer le type d'utilisation
        montant_restant_apres = montant_restant_actuel - montant_facture
        
        if montant_restant_apres > 0:
            # ══════════════════════════════════════════════════════════════════
            # UTILISATION PARTIELLE
            # ══════════════════════════════════════════════════════════════════
            type_utilisation = UTILISATION_TYPES['PARTIELLE']
            
            print(f" Utilisation de l'avoir {numero_avoir}")
            print(f"   Montant avoir: {montant_restant_actuel} XPF")
            print(f"   Montant facture: {montant_facture} XPF")
            print(f"   Reste: {montant_restant_apres} XPF")
            
            # Créer l'avoir enfant pour le reste
            numero_avoir_enfant, avoir_enfant_complet, date_validite_enfant = self.create_avoir_enfant(
                avoir, montant_restant_apres, utilisateur
            )
            
            # Marquer l'avoir parent comme utilisé
            self.db.cursor.execute(
                """UPDATE avoirs 
                   SET statut = ?, 
                       date_utilisation = ?, 
                       utilisateur_validation = ?,
                       montant_utilise = ?,
                       montant_restant = ?,
                       numero_facture_utilisation = ?
                   WHERE numero_avoir = ?""",
                (AVOIR_STATUS['UTILISE'],
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                 utilisateur, 
                 montant_facture,
                 0,
                 numero_facture_utilisation,
                 numero_avoir)
            )
            self.db.conn.commit()
            
            # Enregistrer l'historique
            self.db.add_utilisation_history(
                avoir_id, numero_avoir, montant_facture,
                numero_facture_utilisation, utilisateur, 'partielle',
                avoir_enfant_complet[0] if avoir_enfant_complet else None
            )
            
            self.db.add_log(utilisateur, "UTILISATION_AVOIR", 
                          f"Avoir {numero_avoir} utilisé: facture {format_montant(montant_facture)} XPF, reste {format_montant(montant_restant_apres)} XPF")
            
            message = SUCCESS_MESSAGES['AVOIR_USED_PARTIAL'].format(
                numero_avoir=numero_avoir,
                montant_facture=format_montant(montant_facture),
                montant_avoir=format_montant(montant_restant_actuel)
            )
            message += f"\nFacture: {numero_facture_utilisation}"
            message += f"\n" + SUCCESS_MESSAGES['AVOIR_CHILD_CREATED'].format(
                numero_avoir=numero_avoir_enfant,
                montant_restant=format_montant(montant_restant_apres)
            )
            
            result = {
                "status": "success",
                "message": message,
                "type_utilisation": "partielle",
                "montant_facture": montant_facture,
                "montant_avoir": montant_restant_actuel,
                # Montant réellement consommé sur l'avoir parent (= montant de la facture).
                # Cette clé était absente : l'interface y accédait pour l'email de
                # notification, ce qui provoquait un KeyError silencieux.
                "montant_utilise": montant_facture,
                "montant_restant": montant_restant_apres,
                "numero_facture": numero_facture_utilisation,
                "numero_avoir_enfant": numero_avoir_enfant,
                "avoir_enfant": avoir_enfant_complet,
                "avoir_parent": avoir,
                "date_validite": date_validite_enfant
            }
            
            print(f" Résultat use_avoir:")
            print(f"   - avoir_enfant présent: {result.get('avoir_enfant') is not None}")
            print(f"   - avoir_parent présent: {result.get('avoir_parent') is not None}")
            print(f"   - date_validite présent: {result.get('date_validite') is not None}")
            
            return result
            
        else:
            # ══════════════════════════════════════════════════════════════════
            # UTILISATION TOTALE
            # ══════════════════════════════════════════════════════════════════
            type_utilisation = UTILISATION_TYPES['TOTALE']
            
            self.db.cursor.execute(
                """UPDATE avoirs 
                   SET statut = ?, 
                       date_utilisation = ?, 
                       utilisateur_validation = ?,
                       montant_utilise = ?,
                       montant_restant = ?,
                       numero_facture_utilisation = ?
                   WHERE numero_avoir = ?""",
                (AVOIR_STATUS['UTILISE'], 
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                 utilisateur, 
                 montant_facture,
                 0,
                 numero_facture_utilisation,
                 numero_avoir)
            )
            self.db.conn.commit()
            
            self.db.add_utilisation_history(
                avoir_id, numero_avoir, montant_facture,
                numero_facture_utilisation, utilisateur, 'totale'
            )
            
            self.db.add_log(utilisateur, "UTILISATION_TOTALE_AVOIR", 
                          f"Avoir {numero_avoir} utilisé totalement: {format_montant(montant_facture)} XPF")
            
            message = SUCCESS_MESSAGES['AVOIR_USED_TOTAL'].format(
                numero_avoir=numero_avoir,
                montant=format_montant(montant_facture)
            )
            message += f"\nFacture: {numero_facture_utilisation}"
            
            return {
                "status": "success",
                "message": message,
                "type_utilisation": "totale",
                "montant_facture": montant_facture,
                "montant_avoir": montant_restant_actuel,
                "numero_facture": numero_facture_utilisation
            }
    
    # ══════════════════════════════════════════════════════════════════════════════
    # STATISTIQUES
    # ══════════════════════════════════════════════════════════════════════════════
    
    def get_statistics(self):
        """
        Récupère les statistiques des avoirs.
        
        Returns:
            dict: Statistiques avec les clés:
                - avoirs_actifs_count: Nombre d'avoirs actifs
                - avoirs_actifs_montant: Montant total des avoirs actifs
                - avoirs_peremption: Liste des avoirs bientôt expirés (7j)
                - top_clients: Top 10 des clients
                - utilises_totalement: Nombre d'utilisations totales
                - montant_total_utilise: Montant total utilisé
                - montant_total_restant: Montant total restant
                - emails_envoyes, rappels_envoyes: Stats email
                - avoirs_enfants: Nombre d'avoirs enfants
        """
        stats = {}
        
        try:
            # Avoirs actifs
            avoirs_actifs = self.db.cursor.execute(
                """SELECT COUNT(*), SUM(montant_restant) 
                   FROM avoirs 
                   WHERE statut = ?""",
                (AVOIR_STATUS['ACTIF'],)
            ).fetchone()
            stats['avoirs_actifs_count'] = avoirs_actifs[0] or 0
            stats['avoirs_actifs_montant'] = avoirs_actifs[1] or 0
            
            # Avoirs bientôt périmés (7 jours)
            date_limite = datetime.now() + timedelta(days=7)
            avoirs_peremption = self.db.cursor.execute(
                """SELECT id, numero_avoir, numero_client, nom_client, email_client,
                          numero_facture, CAST(date_facture AS TEXT), type_avoir, montant,
                          numero_facture_avoir, CAST(date_creation AS TEXT), 
                          CAST(date_validite AS TEXT), statut, montant_restant
                   FROM avoirs 
                   WHERE statut = ? AND date_validite <= ?""",
                (AVOIR_STATUS['ACTIF'], date_limite)
            ).fetchall()
            stats['avoirs_peremption'] = avoirs_peremption
            
            # Top clients
            top_clients = self.db.cursor.execute('''
                SELECT numero_client, nom_client, COUNT(*) as nb_avoirs, SUM(montant) as total
                FROM avoirs
                GROUP BY numero_client
                ORDER BY nb_avoirs DESC
                LIMIT 10
            ''').fetchall()
            stats['top_clients'] = top_clients
            
            # Stats d'utilisation
            utilisation_stats = self.db.cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN statut = ? THEN 1 END) as utilises_totalement,
                    SUM(montant_utilise) as montant_total_utilise,
                    SUM(montant_restant) as montant_total_restant
                FROM avoirs
                WHERE statut IN (?, ?)
            ''', (
                AVOIR_STATUS['UTILISE'],
                AVOIR_STATUS['UTILISE'],
                AVOIR_STATUS['ACTIF']
            )).fetchone()
            
            stats['utilises_totalement'] = utilisation_stats[0] or 0
            stats['utilises_partiellement'] = 0
            stats['montant_total_utilise'] = utilisation_stats[1] or 0
            stats['montant_total_restant'] = utilisation_stats[2] or 0
            
            # Stats email
            emails_stats = self.db.cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN email_envoye = 1 THEN 1 END) as emails_envoyes,
                    COUNT(CASE WHEN rappel_envoye = 1 THEN 1 END) as rappels_envoyes
                FROM avoirs
            ''').fetchone()
            stats['emails_envoyes'] = emails_stats[0] or 0
            stats['rappels_envoyes'] = emails_stats[1] or 0
            
            # Stats parent/enfant
            parent_enfant_stats = self.db.cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN est_avoir_enfant = 1 THEN 1 END) as avoirs_enfants,
                    COUNT(CASE WHEN avoir_parent_id IS NOT NULL THEN 1 END) as avoirs_avec_parent
                FROM avoirs
            ''').fetchone()
            stats['avoirs_enfants'] = parent_enfant_stats[0] or 0
            stats['avoirs_avec_parent'] = parent_enfant_stats[1] or 0
            
        except Exception as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            stats = {
                'avoirs_actifs_count': 0,
                'avoirs_actifs_montant': 0,
                'avoirs_peremption': [],
                'top_clients': [],
                'emails_envoyes': 0,
                'rappels_envoyes': 0,
                'utilises_totalement': 0,
                'utilises_partiellement': 0,
                'montant_total_utilise': 0,
                'montant_total_restant': 0,
                'avoirs_enfants': 0,
                'avoirs_avec_parent': 0,
                'avoirs_valides_count': 0,
                'avoirs_expires_count': 0,
                'avoirs_bloques_count': 0,
                'avoirs_annules_count': 0,
                'avoirs_utilises_count': 0,
                'total_avoirs': 0
            }
        
        # ══════════════════════════════════════════════════════════════════════
        # VUE D'ENSEMBLE PAR STATUT - bloc INDEPENDANT et robuste
        # Calculee separement (hors du try precedent) afin que les compteurs
        # restent corrects meme si une requete du bloc precedent a echoue.
        # Aucun parametre de date n'est passe a SQLite : on lit les statuts via
        # un simple GROUP BY, puis on affine en Python (tolerant aux formats).
        # ══════════════════════════════════════════════════════════════════════
        try:
            rows = self.db.cursor.execute(
                "SELECT statut, COUNT(*) FROM avoirs GROUP BY statut"
            ).fetchall()
            counts = {row[0]: (row[1] or 0) for row in rows}

            actifs_bruts = counts.get(AVOIR_STATUS['ACTIF'], 0)
            expires_bruts = counts.get(AVOIR_STATUS['EXPIRE'], 0)

            stats['avoirs_bloques_count'] = counts.get(AVOIR_STATUS['BLOQUE'], 0)
            stats['avoirs_annules_count'] = counts.get(AVOIR_STATUS['ANNULE'], 0)
            stats['avoirs_utilises_count'] = counts.get(AVOIR_STATUS['UTILISE'], 0)
            stats['total_avoirs'] = sum(
                v for k, v in counts.items() if k != AVOIR_STATUS['SUPPRIME']
            )

            # Valeurs par defaut : comptes bruts par statut (toujours corrects)
            stats['avoirs_valides_count'] = actifs_bruts
            stats['avoirs_expires_count'] = expires_bruts

            # Affinage : un avoir 'actif' est compté comme expiré uniquement si
            # sa CRÉATION remonte à plus de VALIDITE_JOURS (90 jours), comme la
            # règle d'utilisation. Le calcul se fait en Python (tolérant aux formats).
            try:
                maintenant = datetime.now()
                limite = timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
                actifs_dates = self.db.cursor.execute(
                    "SELECT CAST(date_creation AS TEXT) FROM avoirs WHERE statut = ?",
                    (AVOIR_STATUS['ACTIF'],)
                ).fetchall()
                perimes = 0
                for (dc,) in actifs_dates:
                    dcreation = self._parse_date(dc)
                    if dcreation is not None and maintenant > (dcreation + limite):
                        perimes += 1
                stats['avoirs_valides_count'] = max(0, actifs_bruts - perimes)
                stats['avoirs_expires_count'] = expires_bruts + perimes
            except Exception as e:
                print(f"Affinage dates (non bloquant): {e}")

        except Exception as e:
            print(f"Erreur vue d'ensemble (statistiques): {e}")
            stats.setdefault('avoirs_bloques_count', 0)
            stats.setdefault('avoirs_annules_count', 0)
            stats.setdefault('avoirs_utilises_count', 0)
            stats.setdefault('total_avoirs', 0)
            stats.setdefault('avoirs_valides_count', 0)
            stats.setdefault('avoirs_expires_count', 0)

        return stats
    
    # ══════════════════════════════════════════════════════════════════════════════
    # LECTURE
    # ══════════════════════════════════════════════════════════════════════════════
    
    def get_avoirs_list(self, status_filter='Tous', date_from=None, date_to=None,
                        autorise_par=None, utilise_par=None):
        """
        Récupère la liste des avoirs (exclut les supprimés par défaut).
        
        Args:
            status_filter: Filtre de statut ('Tous', 'actif', 'utilise', 
                          'Supprimés', 'Annulés', etc.)
            date_from: Date de création MINIMALE incluse, au format 'YYYY-MM-DD'.
                       None = pas de borne basse.
            date_to: Date de création MAXIMALE incluse, au format 'YYYY-MM-DD'.
                     None = pas de borne haute.
            autorise_par: Filtre sur le responsable ayant AUTORISÉ le forçage
                          (colonne forcage_autorise_par). None = pas de filtre.
            utilise_par: Filtre sur l'utilisateur ayant UTILISÉ l'avoir
                         (colonne utilisateur_validation, tous rôles confondus).
                         None = pas de filtre.
                          
        Returns:
            list: Liste des avoirs. Ordre des colonnes de chaque ligne :
                  0 id, 1 numero_avoir, 2 numero_client, 3 nom_client,
                  4 email_client, 5 numero_facture, 6 date_facture,
                  7 type_avoir, 8 montant, 9 numero_facture_avoir,
                  10 date_creation, 11 date_validite, 12 statut,
                  13 date_utilisation, 14 utilisateur_creation,
                  15 utilisateur_validation, 16 signature, 17 email_envoye,
                  18 rappel_envoye, 19 montant_utilise, 20 montant_restant,
                  21 numero_facture_utilisation, 22 avoir_parent_id,
                  23 est_avoir_enfant, 24 forcage_autorise_par,
                  25 commentaire_blocage
        """
        try:
            # Colonnes renvoyées : l'ORDRE est important car il est utilisé tel
            # quel par l'interface. La colonne forcage_autorise_par est ajoutée
            # en DERNIÈRE position (index 24) afin de NE PAS décaler les index
            # déjà utilisés ailleurs dans le programme.
            select_cols = """
                id, numero_avoir, numero_client, nom_client, email_client,
                numero_facture, CAST(date_facture AS TEXT) as date_facture,
                type_avoir, CAST(montant AS REAL) as montant,
                numero_facture_avoir,
                CAST(date_creation AS TEXT) as date_creation,
                CAST(date_validite AS TEXT) as date_validite,
                statut, CAST(date_utilisation AS TEXT) as date_utilisation,
                utilisateur_creation, utilisateur_validation, signature,
                email_envoye, rappel_envoye,
                CAST(montant_utilise AS REAL) as montant_utilise,
                CAST(montant_restant AS REAL) as montant_restant,
                numero_facture_utilisation, avoir_parent_id, est_avoir_enfant,
                forcage_autorise_par, commentaire_blocage
            """

            conditions = []
            params = []

            # --- Filtre de statut (robuste aux accents et aux valeurs brutes) ---
            sf = status_filter or 'Tous'
            if sf == 'Tous':
                conditions.append("statut != 'supprime'")
            elif sf in ('Supprimés', 'Supprimes', 'supprime'):
                conditions.append("statut = 'supprime'")
            elif sf in ('Annulés', 'Annules', 'annule'):
                conditions.append("statut = 'annule'")
            else:
                conditions.append("statut = ?")
                conditions.append("statut != 'supprime'")
                params.append(sf.lower())

            # --- Filtre plage de dates sur la DATE DE CRÉATION ---
            if date_from:
                conditions.append("date(date_creation) >= date(?)")
                params.append(date_from)
            if date_to:
                conditions.append("date(date_creation) <= date(?)")
                params.append(date_to)

            # --- Filtre : responsable ayant AUTORISÉ le forçage ---
            if autorise_par:
                conditions.append("forcage_autorise_par = ?")
                params.append(autorise_par)

            # --- Filtre : utilisateur ayant UTILISÉ l'avoir ---
            if utilise_par:
                conditions.append("utilisateur_validation = ?")
                params.append(utilise_par)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = (
                f"SELECT {select_cols} FROM avoirs "
                f"WHERE {where_clause} ORDER BY id DESC"
            )

            avoirs = self.db.cursor.execute(query, tuple(params)).fetchall()
            return avoirs
            
        except Exception as e:
            print(f"Erreur lors de la récupération des avoirs: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_distinct_autorise_par(self):
        """
        Récupère la liste DISTINCTE des responsables ayant autorisé au moins
        un forçage (valeurs non vides de forcage_autorise_par).
        
        Sert à alimenter le filtre « Autorisé par » de la liste des avoirs.
        
        Returns:
            list: Noms (str), triés par ordre alphabétique.
        """
        try:
            rows = self.db.cursor.execute(
                """SELECT DISTINCT forcage_autorise_par
                   FROM avoirs
                   WHERE forcage_autorise_par IS NOT NULL
                     AND TRIM(forcage_autorise_par) != ''
                   ORDER BY forcage_autorise_par COLLATE NOCASE ASC"""
            ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception as e:
            print(f"Erreur lors de la récupération des autorisations: {e}")
            return []
    
    def get_distinct_utilise_par(self):
        """
        Récupère la liste DISTINCTE des utilisateurs ayant utilisé au moins
        un avoir (valeurs non vides de utilisateur_validation), tous rôles
        confondus.
        
        Sert à alimenter le filtre « Utilisé par » de la liste des avoirs.
        
        Returns:
            list: Noms (str), triés par ordre alphabétique.
        """
        try:
            rows = self.db.cursor.execute(
                """SELECT DISTINCT utilisateur_validation
                   FROM avoirs
                   WHERE utilisateur_validation IS NOT NULL
                     AND TRIM(utilisateur_validation) != ''
                   ORDER BY utilisateur_validation COLLATE NOCASE ASC"""
            ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception as e:
            print(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []
    
    def get_clients_anomalies(self, date_from, date_to, seuil=5, type_avoir='tous',
                              numero_client=None):
        """
        Détecte les clients « en anomalie » sur une PLAGE DE DATES choisie :
        ceux qui ont reçu au moins `seuil` avoirs entre `date_from` et
        `date_to` (inclus), avoirs supprimés exclus.

        Args:
            date_from: Date de début incluse, au format 'YYYY-MM-DD'.
            date_to: Date de fin incluse, au format 'YYYY-MM-DD'.
            seuil: Nombre minimal d'avoirs sur la période pour être signalé.
            type_avoir: 'tous', 'hors_residus' ou 'residus'.
            numero_client: Si fourni, restreint à CE client et IGNORE le seuil.

        Returns:
            list of tuples:
                (numero_client, nom_client, nb_avoirs, montant_total,
                 premiere_date, derniere_date)
        """
        try:
            conditions = ["statut != 'supprime'",
                          "date(date_creation) >= date(?)",
                          "date(date_creation) <= date(?)"]
            params = [date_from, date_to]
            if type_avoir == 'hors_residus':
                conditions.append("(est_avoir_enfant = 0 OR est_avoir_enfant IS NULL)")
            elif type_avoir == 'residus':
                conditions.append("est_avoir_enfant = 1")
            client_filtre = str(numero_client).strip() if numero_client else ''
            if client_filtre:
                conditions.append("numero_client = ?")
                params.append(client_filtre)
            where = " AND ".join(conditions)
            having = "" if client_filtre else " HAVING COUNT(*) >= ?"
            if not client_filtre:
                params.append(int(seuil))
            query = (
                "SELECT numero_client, MAX(nom_client) as nom_client, "
                "COUNT(*) as nb_avoirs, SUM(montant) as montant_total, "
                "MIN(date_creation) as premiere, MAX(date_creation) as derniere "
                "FROM avoirs WHERE " + where +
                " GROUP BY numero_client" + having +
                " ORDER BY nb_avoirs DESC, montant_total DESC"
            )
            rows = self.db.cursor.execute(query, tuple(params)).fetchall()
            return rows
        except Exception as e:
            print(f"Erreur lors de la détection des anomalies: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_avoirs_client_filtre(self, numero_client, date_from, date_to,
                                 type_avoir='tous'):
        """
        Récupère les avoirs d'un client correspondant aux MÊMES filtres que
        l'analyse d'anomalies (plage de dates + type), avoirs supprimés exclus.
        Ainsi le total affiché correspond exactement au « Nb avoirs » du tableau.

        Returns:
            list of tuples:
                (numero_avoir, date_creation, montant, montant_restant,
                 statut, numero_facture, utilisateur_creation, est_avoir_enfant)
        """
        try:
            conditions = ["numero_client = ?",
                          "statut != 'supprime'",
                          "date(date_creation) >= date(?)",
                          "date(date_creation) <= date(?)"]
            params = [numero_client, date_from, date_to]
            if type_avoir == 'hors_residus':
                conditions.append("(est_avoir_enfant = 0 OR est_avoir_enfant IS NULL)")
            elif type_avoir == 'residus':
                conditions.append("est_avoir_enfant = 1")
            where = " AND ".join(conditions)
            rows = self.db.cursor.execute(
                "SELECT numero_avoir, CAST(date_creation AS TEXT) as date_creation, "
                "CAST(montant AS REAL) as montant, "
                "CAST(montant_restant AS REAL) as montant_restant, statut, "
                "numero_facture, utilisateur_creation, est_avoir_enfant "
                "FROM avoirs WHERE " + where + " ORDER BY date_creation DESC",
                tuple(params)
            ).fetchall()
            return rows
        except Exception as e:
            print(f"Erreur lors de la récupération des avoirs filtrés: {e}")
            return []
    
    def get_avoirs_client_periode(self, numero_client, mois=6):
        """
        Récupère tous les avoirs d'un client sur les `mois` derniers mois
        (avoirs supprimés inclus, pour la traçabilité), les plus récents
        en premier.

        Args:
            numero_client: Numéro du client.
            mois: Profondeur d'historique en mois.

        Returns:
            list of tuples:
                (numero_avoir, date_creation, montant, montant_restant,
                 statut, numero_facture, utilisateur_creation, est_avoir_enfant)
        """
        try:
            fenetre = f"-{int(mois)} months"
            rows = self.db.cursor.execute(
                """SELECT numero_avoir,
                          CAST(date_creation AS TEXT) as date_creation,
                          CAST(montant AS REAL) as montant,
                          CAST(montant_restant AS REAL) as montant_restant,
                          statut,
                          numero_facture,
                          utilisateur_creation,
                          est_avoir_enfant
                   FROM avoirs
                   WHERE numero_client = ?
                     AND date(date_creation) >= date('now', ?)
                   ORDER BY date_creation DESC""",
                (numero_client, fenetre)
            ).fetchall()
            return rows
        except Exception as e:
            print(f"Erreur lors de la récupération des avoirs du client: {e}")
            return []
    
    def get_avoir_details(self, numero_avoir):
        """
        Récupère les détails d'un avoir avec historique.
        
        Args:
            numero_avoir: Numéro de l'avoir
            
        Returns:
            dict: Dictionnaire avec 'avoir', 'historique', 'avoirs_enfants'
                  ou None si non trouvé
        """
        # Normaliser le numéro et chercher avec les deux formats
        numero_normalized = self.normalize_numero_avoir(numero_avoir)
        
        avoir = self.db.cursor.execute(
            "SELECT * FROM avoirs WHERE numero_avoir = ? OR numero_avoir = ?",
            (numero_avoir, numero_normalized)
        ).fetchone()
        
        # Essayer aussi avec l'ancien format
        if not avoir and '/' not in numero_avoir and len(numero_avoir) == 7:
            ancien_format = f"{numero_avoir[:2]}/{numero_avoir[2:]}"
            avoir = self.db.cursor.execute(
                "SELECT * FROM avoirs WHERE numero_avoir = ?",
                (ancien_format,)
            ).fetchone()
        
        if avoir:
            try:
                historique = self.db.get_historique_utilisation(avoir[0])
            except Exception as e:
                print(f"(info) historique indisponible pour {numero_avoir}: {e}")
                historique = []
            try:
                avoirs_enfants = self.db.get_avoir_enfants(avoir[0])
            except Exception as e:
                print(f"(info) avoirs enfants indisponibles pour {numero_avoir}: {e}")
                avoirs_enfants = []
            
            return {
                'avoir': avoir,
                'historique': historique,
                'avoirs_enfants': avoirs_enfants
            }
        
        return None
    
    def get_avoir_parent(self, avoir_id):
        """
        Récupère l'avoir parent d'un avoir enfant.
        
        Args:
            avoir_id: ID de l'avoir enfant
            
        Returns:
            tuple: Données de l'avoir parent ou None
        """
        result = self.db.cursor.execute(
            "SELECT avoir_parent_id FROM avoirs WHERE id = ?",
            (avoir_id,)
        ).fetchone()
        
        if result and result[0]:
            return self.db.cursor.execute(
                "SELECT * FROM avoirs WHERE id = ?",
                (result[0],)
            ).fetchone()
        
        return None
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MODIFICATION
    # ══════════════════════════════════════════════════════════════════════════════
    
    def update_avoir_email(self, numero_avoir, email):
        """
        Met à jour l'email d'un avoir.
        
        Args:
            numero_avoir: Numéro de l'avoir
            email: Nouvel email
            
        Returns:
            bool: True si mis à jour
        """
        self.db.cursor.execute(
            "UPDATE avoirs SET email_client = ? WHERE numero_avoir = ?",
            (email, numero_avoir)
        )
        self.db.conn.commit()
        return True
    
    def cancel_avoir(self, numero_avoir, utilisateur, motif=""):
        """
        Annule un avoir (remet le montant à 0 et marque comme annulé).
        Réservé aux super_user uniquement.
        
        Args:
            numero_avoir: Numéro de l'avoir
            utilisateur: Utilisateur effectuant l'annulation
            motif: Motif d'annulation (optionnel)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            avoir = self.db.cursor.execute(
                "SELECT * FROM avoirs WHERE numero_avoir = ?",
                (numero_avoir,)
            ).fetchone()
            
            if not avoir:
                return False, "Avoir introuvable"
            
            self.db.cursor.execute(
                """UPDATE avoirs 
                   SET montant = 0,
                       montant_restant = 0,
                       montant_utilise = 0,
                       statut = 'annule',
                       date_utilisation = ?,
                       utilisateur_validation = ?,
                       commentaire_blocage = ?,
                       bloque_par = ?,
                       date_blocage = ?
                   WHERE numero_avoir = ?""",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), utilisateur,
                 motif, utilisateur, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 numero_avoir)
            )
            self.db.conn.commit()
            
            self.db.add_log(
                utilisateur, 
                "ANNULATION_AVOIR", 
                f"Avoir {numero_avoir} annulé. Motif: {motif if motif else 'Non spécifié'}"
            )
            
            return True, f"Avoir {numero_avoir} annulé avec succès"
            
        except Exception as e:
            print(f"Erreur lors de l'annulation de l'avoir: {e}")
            return False, f"Erreur: {str(e)}"
    
    def block_avoir(self, numero_avoir, utilisateur, commentaire=""):
        """
        Bloque un avoir (statut 'bloque'), indépendamment de sa validité.

        Réservé (côté interface) aux rôles super_user / responsable / comptabilite.
        Un avoir bloqué ne peut plus être utilisé en caisse, ni débloqué par le
        forçage : le client doit passer à la comptabilité.

        Args:
            numero_avoir: Numéro de l'avoir
            utilisateur: Utilisateur effectuant le blocage
            commentaire: Commentaire obligatoire expliquant le blocage

        Returns:
            tuple: (success: bool, message: str)
        """
        if not commentaire or not str(commentaire).strip():
            return False, ERROR_MESSAGES['BLOCAGE_COMMENTAIRE_REQUIS']

        try:
            avoir = self.db.cursor.execute(
                "SELECT statut FROM avoirs WHERE numero_avoir = ?",
                (numero_avoir,)
            ).fetchone()

            if not avoir:
                return False, "Avoir introuvable"

            statut = avoir[0]
            if statut == AVOIR_STATUS['BLOQUE']:
                return False, f"L'avoir {numero_avoir} est déjà bloqué"
            if statut in (AVOIR_STATUS['UTILISE'], AVOIR_STATUS['ANNULE'], AVOIR_STATUS['SUPPRIME']):
                return False, f"Impossible de bloquer un avoir au statut '{statut}'"

            self.db.cursor.execute(
                """UPDATE avoirs
                   SET statut = ?,
                       commentaire_blocage = ?,
                       bloque_par = ?,
                       date_blocage = ?
                   WHERE numero_avoir = ?""",
                (AVOIR_STATUS['BLOQUE'],
                 str(commentaire).strip(),
                 utilisateur,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 numero_avoir)
            )
            self.db.conn.commit()

            self.db.add_log(
                utilisateur, "BLOCAGE_AVOIR",
                f"Avoir {numero_avoir} bloqué. Commentaire : {str(commentaire).strip()}"
            )

            return True, SUCCESS_MESSAGES['AVOIR_BLOCKED'].format(numero_avoir=numero_avoir)

        except Exception as e:
            print(f"Erreur lors du blocage de l'avoir: {e}")
            return False, f"Erreur: {str(e)}"

    def unblock_avoir(self, numero_avoir, utilisateur):
        """
        Débloque un avoir précédemment bloqué.

        Réservé (côté interface) aux rôles super_user / responsable / comptabilite.
        Le statut est recalculé automatiquement : 'actif' si la validité n'est pas
        dépassée, 'expire' sinon.

        Args:
            numero_avoir: Numéro de l'avoir
            utilisateur: Utilisateur effectuant le déblocage

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            avoir = self.db.cursor.execute(
                "SELECT statut, CAST(date_validite AS TEXT) FROM avoirs WHERE numero_avoir = ?",
                (numero_avoir,)
            ).fetchone()

            if not avoir:
                return False, "Avoir introuvable"

            if avoir[0] != AVOIR_STATUS['BLOQUE']:
                return False, f"L'avoir {numero_avoir} n'est pas bloqué"

            # Recalcul automatique du statut à partir de la validité
            nouveau_statut = AVOIR_STATUS['ACTIF']
            date_validite_str = avoir[1]
            try:
                if date_validite_str:
                    s = str(date_validite_str)
                    if 'T' in s:
                        date_validite = datetime.fromisoformat(s.split('T')[0])
                    elif '/' in s:
                        parts = s.split('/')
                        date_validite = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    else:
                        date_validite = datetime.fromisoformat(s.split(' ')[0])
                    if datetime.now() > date_validite:
                        nouveau_statut = AVOIR_STATUS['EXPIRE']
            except (ValueError, IndexError):
                nouveau_statut = AVOIR_STATUS['ACTIF']

            self.db.cursor.execute(
                "UPDATE avoirs SET statut = ? WHERE numero_avoir = ?",
                (nouveau_statut, numero_avoir)
            )
            self.db.conn.commit()

            self.db.add_log(
                utilisateur, "DEBLOCAGE_AVOIR",
                f"Avoir {numero_avoir} débloqué (nouveau statut : {nouveau_statut})"
            )

            return True, SUCCESS_MESSAGES['AVOIR_UNBLOCKED'].format(
                numero_avoir=numero_avoir, statut=nouveau_statut
            )

        except Exception as e:
            print(f"Erreur lors du déblocage de l'avoir: {e}")
            return False, f"Erreur: {str(e)}"

    def delete_avoir(self, numero_avoir, utilisateur, motif=""):
        """
        Supprime un avoir (le rend invisible en le marquant comme supprimé).
        Réservé (côté interface) aux super_user et à la comptabilité.
        
        Note: L'avoir n'est pas vraiment supprimé de la BDD pour traçabilité.
        Le motif est conservé dans commentaire_blocage (et bloque_par = qui a
        supprimé, date_blocage = quand), pour pouvoir l'afficher au vendeur si
        l'avoir est rescanné, et dans le récap des détails.
        
        Args:
            numero_avoir: Numéro de l'avoir
            utilisateur: Utilisateur effectuant la suppression
            motif: Motif de suppression (optionnel)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            avoir = self.db.cursor.execute(
                "SELECT * FROM avoirs WHERE numero_avoir = ?",
                (numero_avoir,)
            ).fetchone()
            
            if not avoir:
                return False, "Avoir introuvable"
            
            self.db.cursor.execute(
                """UPDATE avoirs 
                   SET statut = 'supprime',
                       date_utilisation = ?,
                       utilisateur_validation = ?,
                       commentaire_blocage = ?,
                       bloque_par = ?,
                       date_blocage = ?
                   WHERE numero_avoir = ?""",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 utilisateur,
                 (str(motif).strip() if motif else ''),
                 utilisateur,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 numero_avoir)
            )
            self.db.conn.commit()
            
            self.db.add_log(
                utilisateur, 
                "SUPPRESSION_AVOIR", 
                f"Avoir {numero_avoir} supprimé. Motif: {motif if motif else 'Non spécifié'}"
            )
            
            return True, f"Avoir {numero_avoir} supprimé avec succès"
            
        except Exception as e:
            print(f"Erreur lors de la suppression de l'avoir: {e}")
            return False, f"Erreur: {str(e)}"
    
    # ══════════════════════════════════════════════════════════════════════════════
    # DIAGNOSTIC
    # ══════════════════════════════════════════════════════════════════════════════
    
    def verify_database_structure(self):
        """
        Vérifie la structure de la base de données.
        Affiche les colonnes des tables et les statistiques.
        """
        try:
            cursor = self.db.cursor
            cursor.execute("PRAGMA table_info(avoirs)")
            columns = cursor.fetchall()
            print("Structure de la table avoirs:")
            for i, col in enumerate(columns):
                print(f"   Index {i}: {col[1]} ({col[2]})")
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='historique_utilisation'
            """)
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(historique_utilisation)")
                hist_columns = cursor.fetchall()
                print("Structure de la table historique_utilisation:")
                for i, col in enumerate(hist_columns):
                    print(f"   Index {i}: {col[1]} ({col[2]})")
            
            count = cursor.execute("SELECT COUNT(*) FROM avoirs").fetchone()[0]
            count_actifs = cursor.execute(
                "SELECT COUNT(*) FROM avoirs WHERE statut = ?",
                (AVOIR_STATUS['ACTIF'],)
            ).fetchone()[0]
            count_enfants = cursor.execute(
                "SELECT COUNT(*) FROM avoirs WHERE est_avoir_enfant = 1"
            ).fetchone()[0]
            
            print(f"Nombre total d'avoirs: {count}")
            print(f"   - Actifs: {count_actifs}")
            print(f"   - Avoirs enfants: {count_enfants}")
            
        except Exception as e:
            print(f"Erreur lors de la vérification de la base: {e}")