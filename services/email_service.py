"""
Service d'envoi d'emails - VERSION CORRIGE
Module de Gestion des Avoirs Clients - STOYANN
Version: 1.7 - Correction complte du formatage des emails
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta
import threading
import time
from config.settings import SMTP_CONFIG, AVOIR_CONFIG, format_montant
from config.email_templates import EMAIL_TEMPLATES
from database.connection import Database

class EmailService:
    def __init__(self, database=None):
        self.db = database if database else Database(thread_safe=True)
        self.smtp_config = SMTP_CONFIG
        self.reminder_thread = None
        self.start_reminder_service()
    
    def get_email_header(self):
        """Retourne le header HTML pour les emails"""
        return """
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif; 
                line-height: 1.6; 
                color: #000000; 
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .container { 
                max-width: 600px; 
                margin: 20px auto; 
                background-color: #ffffff;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .header { 
                background-color: #fff001; 
                color: #000000; 
                padding: 30px; 
                text-align: center;
                border-bottom: 5px solid #000000;
            }
            .header-urgent {
                background-color: #ff0000;
                color: #ffffff;
                padding: 30px;
                text-align: center;
                border-bottom: 5px solid #000000;
            }
            .header h1, .header-urgent h1 {
                margin: 0;
                font-size: 28px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .header p, .header-urgent p {
                margin: 5px 0 0 0;
                font-size: 14px;
                opacity: 0.9;
            }
            .content { 
                padding: 30px; 
                background-color: #ffffff;
                color: #000000;
            }
            .info-box {
                background-color: #f9f9f9;
                border-left: 4px solid #fff001;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .urgent-box {
                background-color: #ffebee;
                border: 2px solid #ff0000;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                text-align: center;
            }
            .urgent-box h2 {
                color: #ff0000;
                margin: 0 0 10px 0;
                font-size: 24px;
            }
            .info-box h3 {
                margin: 0 0 10px 0;
                color: #000000;
                font-size: 16px;
                text-transform: uppercase;
            }
            .info-line {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e0e0e0;
            }
            .info-line:last-child {
                border-bottom: none;
            }
            .label {
                font-weight: 600;
                color: #333333;
            }
            .value {
                color: #000000;
                text-align: right;
            }
            .montant-box {
                background: linear-gradient(135deg, #fff001 0%, #ffeb3b 100%);
                color: #000000;
                padding: 20px;
                text-align: center;
                border-radius: 10px;
                margin: 25px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .montant-label {
                font-size: 14px;
                text-transform: uppercase;
                margin-bottom: 5px;
                opacity: 0.8;
            }
            .montant-value {
                font-size: 32px;
                font-weight: bold;
                margin: 0;
            }
            .conditions {
                background-color: #fff8e1;
                border: 2px solid #fff001;
                border-radius: 8px;
                padding: 20px;
                margin: 25px 0;
            }
            .warning-box {
                background-color: #ffebee;
                border: 2px solid #d32f2f;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
            }
            .warning-box p {
                color: #d32f2f;
                font-weight: bold;
                margin: 0;
                font-size: 14px;
            }
            .conditions h4 {
                color: #000000;
                margin: 0 0 15px 0;
                font-size: 14px;
                text-transform: uppercase;
            }
            .conditions ul {
                margin: 0;
                padding-left: 20px;
            }
            .conditions li {
                color: #333333;
                margin: 8px 0;
                font-size: 13px;
            }
            .contact-box {
                background-color: #000000;
                color: #ffffff;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: center;
            }
            .contact-box h4 {
                color: #fff001;
                margin: 0 0 15px 0;
                font-size: 16px;
                text-transform: uppercase;
            }
            .contact-box p {
                margin: 5px 0;
                font-size: 14px;
            }
            .horaires {
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
            }
            .horaires h5 {
                color: #000;
                margin: 0 0 10px 0;
                font-size: 14px;
                text-transform: uppercase;
            }
            .horaires p {
                margin: 5px 0;
                font-size: 13px;
            }
            .footer { 
                padding: 20px; 
                text-align: center; 
                font-size: 11px; 
                color: #666666;
                background-color: #f5f5f5;
                border-top: 1px solid #e0e0e0;
            }
            .footer a {
                color: #666666;
            }
            .important { 
                color: #d32f2f; 
                font-weight: bold; 
            }
            .signature {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #f0f0f0;
            }
        </style>
        """
    
    def get_contact_info_html(self):
        """Retourne le HTML des informations de contact"""
        return """
        <div class="contact-box">
            <h4> NOUS TROUVER</h4>
            <p><strong>QUINCAILLERIE CALÉDONIENNE</strong></p>
            <p>13 Rue Ampère - Ducos</p>
            <p>Nouvelle-Calédonie</p>
            <p style="margin-top: 10px;"> Tél : 27 47 22</p>
        </div>
        
        <div class="horaires">
            <h5> Horaires d'ouverture</h5>
            <p><strong>Du lundi au vendredi :</strong> 7h00 - 17h00</p>
            <p><strong>Le samedi :</strong> 7h30 - 16h00</p>
            <p><strong>Dimanche :</strong> Ferm</p>
        </div>
        """
    
    def send_email(self, to_email, subject, body, is_html_ready=False):
        """
        Envoie un email via SMTP avec formatage correct de l'expditeur.
        
        CORRECTION COMPLTE du problme ">"@mx1.canl.local :
        - Utilisation de formataddr pour crer un expditeur correctement format
        - Utilisation de sendmail au lieu de send_message
        - Sparation claire entre l'adresse d'authentification et l'adresse d'affichage
        """
        try:
            print(f" Tentative d'envoi email  : {to_email}")
            
            # Création du message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["To"] = to_email
            
            # CORRECTION CRITIQUE : Utiliser formataddr pour formater correctement l'expditeur
            # formataddr gre correctement l'encodage et le formatage RFC 2822
            from_address = formataddr((
                self.smtp_config['FROM_NAME'],
                self.smtp_config['FROM_EMAIL']
            ))
            message["From"] = from_address
            
            # Ajouter des headers supplmentaires pour amliorer la dlivrabilit
            message["Reply-To"] = self.smtp_config['FROM_EMAIL']
            message["Return-Path"] = self.smtp_config['FROM_EMAIL']
            
            # Corps du message en texte brut
            text_part = MIMEText(body, "plain", "utf-8")
            
            # HTML amlior avec nouveau design
            if not is_html_ready:
                html_body = f"""
                <html>
                <head>
                    {self.get_email_header()}
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>QUINCAILLERIE CALÉDONIENNE</h1>
                            <p>13 Rue Ampère - Ducos | Tél : 27 47 22</p>
                        </div>
                        <div class="content">
                            {body.replace(chr(10), '<br>')}
                        </div>
                        <div class="footer">
                             {datetime.now().year} Quincaillerie Calédonienne - Nouvelle-Calédonie<br>
                            13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                            <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                        </div>
                    </div>
                </body>
                </html>
                """
            else:
                html_body = body
            
            html_part = MIMEText(html_body, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Connexion et envoi via SMTP avec SSL
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            print(f" Connexion  {self.smtp_config['SMTP_HOST']}:{self.smtp_config['SMTP_PORT']}")
            
            with smtplib.SMTP_SSL(
                self.smtp_config['SMTP_HOST'], 
                self.smtp_config['SMTP_PORT'], 
                context=context,
                timeout=30
            ) as server:
                print(" Authentification...")
                server.login(
                    self.smtp_config['SMTP_EMAIL'], 
                    self.smtp_config['SMTP_PASSWORD']
                )
                
                print(" Envoi du message...")
                
                # UTILISATION CORRECTE de sendmail :
                # - from_addr : adresse email PURE (sans nom, sans <>)
                # - to_addrs : liste d'adresses email PURES
                # - msg : le message complet avec tous les headers
                server.sendmail(
                    from_addr=self.smtp_config['FROM_EMAIL'],
                    to_addrs=[to_email],
                    msg=message.as_string()
                )
                
                print(f" Email envoyé avec succès  {to_email}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Erreur: {str(e)}"
            print(f" {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def send_avoir_confirmation(self, avoir_data):
        """Envoie l'email de confirmation avec nouveau design"""
        if not avoir_data.get('email_client'):
            print(" Pas d'email client fourni")
            return False, "Pas d'email client"
        
        print(f" Prparation email confirmation pour avoir {avoir_data['numero_avoir']}")
        
        # Formater le montant en XPF
        montant_formate = avoir_data.get('montant_formate')
        if not montant_formate:
            montant_formate = format_montant(avoir_data['montant'])
        
        # Préparer les données
        template_data = avoir_data.copy()
        template_data['montant_formate'] = montant_formate
        template_data['type_avoir'] = 'AVOIR RETOUR' if avoir_data['type_avoir'] == 'retour' else 'AVOIR DIFFRENCE'
        template_data['date_creation'] = datetime.now().strftime('%d/%m/%Y')
        
        if isinstance(avoir_data['date_validite'], datetime):
            template_data['date_validite'] = avoir_data['date_validite'].strftime('%d/%m/%Y')
        
        # Crer le HTML personnalis
        html_body = f"""
        <html>
        <head>
            {self.get_email_header()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>QUINCAILLERIE CALÉDONIENNE</h1>
                    <p>Confirmation de votre avoir</p>
                </div>
                <div class="content">
                    <h2 style="color: #000;">Bonjour {template_data['nom_client']},</h2>
                    
                    <p>Nous vous confirmons la création de votre avoir avec les détails suivants :</p>
                    
                    <div class="montant-box">
                        <div class="montant-label">Montant de l'avoir</div>
                        <div class="montant-value">{montant_formate} XPF</div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Détails de l'avoir</h3>
                        <div class="info-line">
                            <span class="label">N° Avoir :</span>
                            <span class="value">{template_data['numero_avoir']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Type :</span>
                            <span class="value">{template_data['type_avoir']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Facture concernée :</span>
                            <span class="value">{template_data['numero_facture']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Date de création :</span>
                            <span class="value">{template_data['date_creation']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Valable jusqu'au :</span>
                            <span class="value important">{template_data['date_validite']}</span>
                        </div>
                    </div>
                    
                    <div class="warning-box">
                        <p> ATTENTION : CET EMAIL N'EST PAS UN BON D'AVOIR</p>
                        <p>Seul le BON D'AVOIR ORIGINAL délivré en magasin permet d'utiliser votre avoir</p>
                    </div>
                    
                    <div class="conditions">
                        <h4> Conditions d'utilisation</h4>
                        <ul>
                            <li><strong>Présentation OBLIGATOIRE du bon d'avoir ORIGINAL en magasin</strong></li>
                            <li>Cet email est uniquement un rappel informatif</li>
                            <li>Avoir à utiliser avant la date d'expiration</li>
                            <li>En cas de perte du bon original, l'avoir ne pourra pas être réémis</li>
                            <li>Non remboursable</li>
                        </ul>
                    </div>
                    
                    {self.get_contact_info_html()}
                    
                    <div class="signature">
                        <p>Cordialement,<br>
                        <strong>L'équipe Quincaillerie Calédonienne</strong></p>
                    </div>
                </div>
                <div class="footer">
                     {datetime.now().year} Quincaillerie Calédonienne<br>
                    13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                    <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"Votre avoir N°{template_data['numero_avoir']} - Quincaillerie Calédonienne"
        
        # Envoyer l'email
        success, error = self.send_email(avoir_data['email_client'], subject, html_body, is_html_ready=True)
        
        # Enregistrer dans l'historique
        if hasattr(self.db, 'thread_safe') and self.db.thread_safe:
            self.db.add_email_log(
                avoir_data['numero_avoir'],
                avoir_data['email_client'],
                'CREATION',
                'SUCCESS' if success else 'ERROR',
                error
            )
            
            if success:
                self.db.mark_email_sent(avoir_data['numero_avoir'])
        
        return success, error

    def send_utilisation_partielle_notification(self, data):
        """Envoie l'email de notification pour utilisation partielle avec nouvel avoir"""
        if not data.get('email_client'):
            print(" Pas d'email client fourni")
            return False, "Pas d'email client"
        
        print(f" Prparation email utilisation partielle pour avoir {data['numero_avoir']}")
        
        # Formater les montants
        montant_initial = self.format_montant_xpf(data['montant_initial'])
        montant_utilise = self.format_montant_xpf(data['montant_utilise'])
        montant_restant = self.format_montant_xpf(data['montant_restant'])
        
        # Formater les dates
        date_utilisation = data['date_utilisation'].strftime('%d/%m/%Y') if isinstance(data['date_utilisation'], datetime) else str(data['date_utilisation'])
        date_validite = data['date_validite'].strftime('%d/%m/%Y') if isinstance(data['date_validite'], datetime) else str(data['date_validite'])
        
        # Crer le HTML personnalis
        html_body = f"""
        <html>
        <head>
            {self.get_email_header()}
        </head>
        <body>
            <div class="container">
                <div class="header" style="background-color: #2196F3;">
                    <h1>UTILISATION PARTIELLE D'AVOIR</h1>
                    <p>Nouvel avoir cr pour le solde</p>
                </div>
                <div class="content">
                    <h2 style="color: #000;">Bonjour {data['nom_client']},</h2>
                    
                    <p style="font-size: 14px; color: #000;">
                        Votre avoir <strong>N°{data['numero_avoir']}</strong> a été utilisé partiellement 
                        lors de votre achat du {date_utilisation}.
                    </p>
                    
                    <div class="info-box" style="border-left: 4px solid #2196F3;">
                        <h3>DTAILS DE L'UTILISATION</h3>
                        <div class="info-line">
                            <span class="label">Avoir utilisé :</span>
                            <span class="value">{data['numero_avoir']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Montant initial :</span>
                            <span class="value">{montant_initial}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Montant utilisé :</span>
                            <span class="value important">{montant_utilise}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">N Facture :</span>
                            <span class="value">{data['numero_facture']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Date utilisation :</span>
                            <span class="value">{date_utilisation}</span>
                        </div>
                    </div>
                    
                    <div style="background-color: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                        <p style="font-size: 16px; color: #000; margin: 0;">
                            <strong> UN NOUVEL AVOIR A T CR</strong>
                        </p>
                    </div>
                    
                    <div class="montant-box" style="background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);">
                        <div class="montant-label" style="color: #fff;">NOUVEAU N AVOIR</div>
                        <div class="montant-value" style="color: #fff; font-size: 28px;">{data['numero_avoir_enfant']}</div>
                        <div class="montant-label" style="color: #fff; margin-top: 10px;">MONTANT DISPONIBLE</div>
                        <div class="montant-value" style="color: #fff;">{montant_restant}</div>
                    </div>
                    
                    <div class="info-box" style="border-left: 4px solid #4CAF50;">
                        <h3>VOTRE NOUVEAU BON D'AVOIR</h3>
                        <div class="info-line">
                            <span class="label">N° Avoir :</span>
                            <span class="value" style="font-weight: bold; color: #4CAF50;">{data['numero_avoir_enfant']}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Montant :</span>
                            <span class="value important">{montant_restant}</span>
                        </div>
                        <div class="info-line">
                            <span class="label">Valable jusqu'au :</span>
                            <span class="value important">{date_validite}</span>
                        </div>
                    </div>
                    
                    <div class="warning-box">
                        <p> IMPORTANT : RCUPREZ LE NOUVEAU BON D'AVOIR EN MAGASIN</p>
                        <p>Le bon d'avoir original N°{data['numero_avoir']} n'est PLUS utilisable</p>
                        <p>Seul le NOUVEAU bon d'avoir N°{data['numero_avoir_enfant']} peut être utilisé</p>
                    </div>
                    
                    <div class="conditions">
                        <h4> CONDITIONS D'UTILISATION DU NOUVEAU BON</h4>
                        <ul>
                            <li><strong>Présentation OBLIGATOIRE du NOUVEAU bon d'avoir ORIGINAL en magasin</strong></li>
                            <li>Cet email est uniquement un rappel informatif</li>
                            <li>Avoir à utiliser avant la date d'expiration</li>
                            <li>En cas de perte du bon original, l'avoir ne pourra pas être réémis</li>
                            <li>Non remboursable</li>
                        </ul>
                    </div>
                    
                    {self.get_contact_info_html()}
                    
                    <div class="signature">
                        <p>Merci de votre confiance,<br>
                        <strong>L'équipe Quincaillerie Calédonienne</strong></p>
                    </div>
                </div>
                <div class="footer">
                     {datetime.now().year} Quincaillerie Calédonienne<br>
                    13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                    <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f" Nouvel avoir N°{data['numero_avoir_enfant']} - Solde de votre avoir N°{data['numero_avoir']}"
        
        # Envoyer l'email
        success, error = self.send_email(data['email_client'], subject, html_body, is_html_ready=True)
        
        # Enregistrer dans l'historique
        if hasattr(self.db, 'thread_safe') and self.db.thread_safe:
            self.db.add_email_log(
                data['numero_avoir'],
                data['email_client'],
                'UTILISATION_PARTIELLE',
                'SUCCESS' if success else 'ERROR',
                error
            )
            
            self.db.add_email_log(
                data['numero_avoir_enfant'],
                data['email_client'],
                'CREATION_AVOIR_ENFANT',
                'SUCCESS' if success else 'ERROR',
                error
            )
            
            if success:
                self.db.mark_email_sent(data['numero_avoir_enfant'])
        
        return success, error
    
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
    
    def send_user_credentials(self, user_data):
        """Envoie les identifiants de connexion  un nouvel utilisateur"""
        if not user_data.get('email'):
            return False, "Pas d'email fourni"
        
        print(f" Envoi des identifiants  {user_data['username']}")
        
        html_body = f"""
        <html>
        <head>
            {self.get_email_header()}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>QUINCAILLERIE CALÉDONIENNE</h1>
                    <p>Module de Gestion des Avoirs</p>
                </div>
                <div class="content">
                    <h2 style="color: #000;">Bienvenue {user_data['username']} !</h2>
                    
                    <p>Votre compte a été créé avec succès sur le Module de Gestion des Avoirs.</p>
                    
                    <div class="info-box">
                        <h3>Vos identifiants de connexion</h3>
                        <div class="info-line">
                            <span class="label">Nom d'utilisateur :</span>
                            <span class="value"><strong>{user_data['username']}</strong></span>
                        </div>
                        <div class="info-line">
                            <span class="label">Mot de passe :</span>
                            <span class="value"><strong>{user_data['password']}</strong></span>
                        </div>
                        <div class="info-line">
                            <span class="label">Rle :</span>
                            <span class="value">{user_data['role'].replace('_', ' ').title()}</span>
                        </div>
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <h3 style="color: #000;">Vos permissions</h3>
                        {self._get_role_permissions_html(user_data['role'])}
                    </div>
                    
                    <div class="signature">
                        <p>Cordialement,<br>
                        <strong>Stoyann - Support QC</strong></p>
                    </div>
                </div>
                <div class="footer">
                     {datetime.now().year} Quincaillerie Calédonienne<br>
                    Module de Gestion des Avoirs<br>
                    13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                    <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = "Vos identifiants de connexion - Module Avoirs"
        
        return self.send_email(user_data['email'], subject, html_body, is_html_ready=True)
    
    def _get_role_permissions_html(self, role):
        """Retourne le HTML des permissions selon le rle"""
        permissions = {
            'super_user': [
                " Crer et grer les avoirs",
                " Utiliser les avoirs en caisse",
                " Grer les utilisateurs",
                " Accs aux statistiques compltes",
                " Export des données",
                " Configuration du systme"
            ],
            'responsable': [
                " Crer et grer les avoirs",
                " Utiliser les avoirs en caisse",
                " Accs aux statistiques",
                " Export des données",
                " Gestion des utilisateurs"
            ],
            'comptabilite': [
                " Crer et grer les avoirs",
                " Utiliser les avoirs en caisse",
                " Bloquer / dbloquer les avoirs",
                " Accs aux statistiques",
                " Export des données"
            ],
            'vendeur': [
                " Utiliser les avoirs en caisse",
                " Consulter la liste des avoirs",
                " Crer des avoirs",
                " Accs aux statistiques",
                " Gestion des utilisateurs"
            ]
        }
        
        role_permissions = permissions.get(role, [])
        html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
        for perm in role_permissions:
            color = "#4CAF50" if perm.startswith("") else "#f44336"
            html += f"<li style='margin: 5px 0; color: {color};'>{perm}</li>"
        html += "</ul>"
        
        return html
    
    def send_expiration_reminder(self, avoir, is_final_reminder=False):
        """Envoie un rappel d'expiration"""
        numero_avoir = avoir[1]
        nom_client = avoir[3]
        email_client = avoir[4]
        montant = avoir[8]
        
        if isinstance(avoir[11], str):
            date_validite = datetime.fromisoformat(avoir[11])
        else:
            date_validite = avoir[11]
        
        if not email_client:
            return False, "Pas d'email client"
        
        print(f" Envoi rappel {'FINAL' if is_final_reminder else 'normal'} pour avoir {numero_avoir}")
        
        jours_restants = (date_validite - datetime.now()).days
        montant_formate = format_montant(montant)
        
        if is_final_reminder:
            html_body = f"""
            <html>
            <head>
                {self.get_email_header()}
            </head>
            <body>
                <div class="container">
                    <div class="header-urgent">
                        <h1> DERNIER JOUR </h1>
                        <p>Votre avoir expire DEMAIN !</p>
                    </div>
                    <div class="content">
                        <h2 style="color: #ff0000;">Bonjour {nom_client},</h2>
                        
                        <div class="urgent-box">
                            <h2> ATTENTION : DERNIRES 24 HEURES !</h2>
                            <p style="font-size: 18px; color: #000; margin: 10px 0;">
                                Votre avoir de <strong>{montant_formate} XPF</strong> expire <strong>DEMAIN</strong> !
                            </p>
                            <p style="font-size: 16px; color: #ff0000; font-weight: bold;">
                                Aprs demain, votre avoir sera DFINITIVEMENT PERDU
                            </p>
                        </div>
                        
                        <div class="montant-box" style="background: linear-gradient(135deg, #ff0000 0%, #ff9800 100%);">
                            <div class="montant-label" style="color: #fff;">VOUS ALLEZ PERDRE</div>
                            <div class="montant-value" style="color: #fff;">{montant_formate} XPF</div>
                        </div>
                        
                        <div class="info-box" style="border-left: 4px solid #ff0000;">
                            <h3>VOTRE AVOIR - DERNIRE CHANCE</h3>
                            <div class="info-line">
                                <span class="label">N° Avoir :</span>
                                <span class="value" style="font-weight: bold;">{numero_avoir}</span>
                            </div>
                            <div class="info-line">
                                <span class="label">Date d'expiration :</span>
                                <span class="value important" style="font-size: 18px;">DEMAIN - {date_validite.strftime('%d/%m/%Y')}</span>
                            </div>
                        </div>
                        
                        <div class="warning-box">
                            <p> RAPPEL IMPORTANT </p>
                            <p>Vous devez OBLIGATOIREMENT présenter le BON D'AVOIR ORIGINAL en magasin</p>
                            <p>Cet email n'est qu'un rappel et ne permet pas d'utiliser l'avoir</p>
                        </div>
                        
                        {self.get_contact_info_html()}
                        
                        <div class="signature">
                            <p>Ne perdez pas votre avoir !<br>
                            <strong>L'équipe Quincaillerie Calédonienne</strong></p>
                        </div>
                    </div>
                    <div class="footer">
                         {datetime.now().year} Quincaillerie Calédonienne<br>
                        13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                        <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = f" URGENT - DERNIER JOUR : Votre avoir N°{numero_avoir} expire DEMAIN !"
        else:
            html_body = f"""
            <html>
            <head>
                {self.get_email_header()}
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background-color: #ff9800;">
                        <h1> RAPPEL EXPIRATION</h1>
                        <p>Votre avoir expire bientôt</p>
                    </div>
                    <div class="content">
                        <h2 style="color: #000;">Bonjour {nom_client},</h2>
                        
                        <div style="background-color: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 5px solid #ff9800;">
                            <p style="margin: 0; font-size: 16px; color: #000;">
                                <strong>Votre avoir expire dans {jours_restants} jours !</strong>
                            </p>
                        </div>
                        
                        <div class="montant-box">
                            <div class="montant-label">Montant de l'avoir</div>
                            <div class="montant-value">{montant_formate} XPF</div>
                        </div>
                        
                        <div class="info-box">
                            <h3>Rappel des détails</h3>
                            <div class="info-line">
                                <span class="label">N° Avoir :</span>
                                <span class="value">{numero_avoir}</span>
                            </div>
                            <div class="info-line">
                                <span class="label">Date d'expiration :</span>
                                <span class="value important">{date_validite.strftime('%d/%m/%Y')}</span>
                            </div>
                            <div class="info-line">
                                <span class="label">Jours restants :</span>
                                <span class="value important">{jours_restants} jours</span>
                            </div>
                        </div>
                        
                        <div class="warning-box">
                            <p> IMPORTANT : CONSERVEZ VOTRE BON D'AVOIR ORIGINAL</p>
                            <p>Seul le bon papier délivré en magasin permet d'utiliser votre avoir</p>
                        </div>
                        
                        {self.get_contact_info_html()}
                        
                        <div class="signature">
                            <p>Cordialement,<br>
                            <strong>L'équipe Quincaillerie Calédonienne</strong></p>
                        </div>
                    </div>
                    <div class="footer">
                         {datetime.now().year} Quincaillerie Calédonienne<br>
                        13 Rue Ampère - Ducos | Tél : 27 47 22<br>
                        <a href="mailto:support@robot-nc.com">support@robot-nc.com</a>
                    </div>
                </div>
            </body>
            </html>
            """
            
            subject = f" Rappel : Votre avoir N°{numero_avoir} expire dans {jours_restants} jours"
        
        success, error = self.send_email(email_client, subject, html_body, is_html_ready=True)
        
        # Journalisation TOUJOURS effectuee (independamment de self.db), via une
        # connexion thread-safe dediee : c'est l'historique des emails qui sert
        # de reference anti-doublon. Le marquage (rappel_envoye / claim) est gere
        # par check_and_send_reminders AVANT l'envoi.
        try:
            reminder_type = 'RAPPEL_FINAL' if is_final_reminder else 'RAPPEL'
            log_db = Database(thread_safe=True)
            log_db.add_email_log(
                numero_avoir,
                email_client,
                reminder_type,
                'SUCCESS' if success else 'ERROR',
                error
            )
        except Exception as e:
            print(f" (avertissement) Journalisation du rappel impossible : {e}")
        
        return success, error
    
    def check_and_send_reminders(self):
        """Verifie et envoie les rappels d'expiration, SANS jamais de doublon.

        Pour chaque avoir :
        - on verifie d'abord dans l'historique qu'aucun rappel du meme type n'a
          deja ete envoye avec succes ;
        - on « reserve » l'envoi de facon atomique (claim_reminder) : si un autre
          poste l'a deja reserve, on passe ;
        - on envoie, puis en cas d'echec seulement on libere la reservation pour
          retenter au prochain cycle.
        """
        try:
            print("\n Verification des avoirs a rappeler...")
            
            db_thread = Database(thread_safe=True)
            
            # ----- RAPPELS NORMAUX -----
            avoirs_to_remind = db_thread.get_avoirs_to_remind(AVOIR_CONFIG['RAPPEL_JOURS'])
            envoyes_normaux = 0
            if avoirs_to_remind:
                print(f" {len(avoirs_to_remind)} avoir(s) candidat(s) au rappel normal")
                for avoir in avoirs_to_remind:
                    numero_avoir = avoir[1]
                    # Securite 1 : deja envoye avec succes ?
                    if db_thread.reminder_already_logged(numero_avoir, final=False):
                        continue
                    # Securite 2 : reservation atomique (anti-doublon multi-postes)
                    if not db_thread.claim_reminder(numero_avoir, final=False):
                        continue
                    success, error = self.send_expiration_reminder(avoir, is_final_reminder=False)
                    if not success:
                        # Echec : on libere pour retenter plus tard
                        db_thread.release_reminder(numero_avoir, final=False)
                        print(f" Echec rappel normal {numero_avoir} : {error}")
                    else:
                        envoyes_normaux += 1
                    time.sleep(2)
            
            # ----- RAPPELS FINAUX (expire dans 1 jour) -----
            avoirs_final = db_thread.get_avoirs_for_final_reminder(1)
            envoyes_finaux = 0
            for avoir in avoirs_final:
                numero_avoir = avoir[1]
                # Securite 1 : un rappel FINAL a-t-il deja ete envoye ?
                if db_thread.reminder_already_logged(numero_avoir, final=True):
                    continue
                # Securite 2 : reservation atomique du rappel final
                if not db_thread.claim_reminder(numero_avoir, final=True):
                    continue
                print(f" Envoi rappel FINAL pour avoir {numero_avoir}")
                success, error = self.send_expiration_reminder(avoir, is_final_reminder=True)
                if not success:
                    db_thread.release_reminder(numero_avoir, final=True)
                    print(f" Echec rappel final {numero_avoir} : {error}")
                else:
                    envoyes_finaux += 1
                time.sleep(2)
            
            if not envoyes_normaux and not envoyes_finaux:
                print(" Aucun nouveau rappel a envoyer")
            else:
                print(f" Rappels envoyes : {envoyes_normaux} normal(aux), "
                      f"{envoyes_finaux} final(aux)")
                
        except Exception as e:
            print(f" Erreur lors de l'envoi des rappels: {e}")
            import traceback
            traceback.print_exc()
    
    def reminder_service_worker(self):
        """Thread de service pour l'envoi automatique de rappels"""
        print(" Service de rappel email dmarr")
        while True:
            try:
                self.check_and_send_reminders()
                print(f" Prochaine vrification dans 1 heure...")
                time.sleep(3600)
            except Exception as e:
                print(f" Erreur dans le service de rappel: {e}")
                time.sleep(3600)
    
    def start_reminder_service(self):
        """Dmarre le service de rappel en arrire-plan"""
        if not self.reminder_thread or not self.reminder_thread.is_alive():
            self.reminder_thread = threading.Thread(
                target=self.reminder_service_worker,
                daemon=True,
                name="EmailReminderService"
            )
            self.reminder_thread.start()
            print(" Service de rappel email activ")
    
    def test_smtp_connection(self):
        """Test la connexion SMTP"""
        try:
            print(f" Test connexion SMTP {self.smtp_config['SMTP_HOST']}:{self.smtp_config['SMTP_PORT']}")
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with smtplib.SMTP_SSL(
                self.smtp_config['SMTP_HOST'], 
                self.smtp_config['SMTP_PORT'], 
                context=context,
                timeout=10
            ) as server:
                server.login(
                    self.smtp_config['SMTP_EMAIL'], 
                    self.smtp_config['SMTP_PASSWORD']
                )
            print(" Connexion SMTP réussie")
            return True, "Connexion SMTP réussie"
        except Exception as e:
            error_msg = f"Erreur de connexion SMTP: {str(e)}"
            print(f" {error_msg}")
            return False, error_msg