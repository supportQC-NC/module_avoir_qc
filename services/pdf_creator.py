"""
Module de cration de PDF pour les avoirs
Gre la gnration des bons d'avoir au format PDF
Version: 1.0 - Correction exclusive des formats de date
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing, Rect
from pathlib import Path
from datetime import datetime, timedelta
import os
from config.settings import AVOIR_CONFIG
from config.paths import get_base_path

# Pour compatibilité avec l'ancien code
BASE_PATH = get_base_path()

class PDFCreator:
    """Classe pour la cration de PDF d'avoirs"""

    def __init__(self):
        """Initialisation du crateur de PDF"""
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Configure les styles personnaliss pour le PDF"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            alignment=TA_CENTER,
            spaceAfter=1*mm,
            fontName='Helvetica-Bold'
        )

        self.company_style = ParagraphStyle(
            'Company',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#000000')
        )

        self.conditions_style = ParagraphStyle(
            'Conditions',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#000000'),
            leading=10,
        )

        self.conditions_title_style = ParagraphStyle(
            'ConditionsTitle',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#000000'),
            spaceAfter=2*mm,
        )

        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        )

    def format_date_fr(self, date_input):
        """
        Formate UNIQUEMENT les dates en JJ/MM/AAAA sans heure
        Version ultra-robuste qui gre tous les cas
        """
        if not date_input:
            return ""

        try:
            # Cas 1: Dj au format JJ/MM/AAAA
            if isinstance(date_input, str) and '/' in date_input:
                parts = date_input.split('/')
                if len(parts) == 3 and len(parts[0]) == 2:
                    return date_input.split(' ')[0]  # On enlve l'heure si prsente

            # Cas 2: Format ISO AAAA-MM-JJ
            if isinstance(date_input, str) and '-' in date_input:
                date_obj = datetime.strptime(date_input.split(' ')[0], "%Y-%m-%d")
                return date_obj.strftime("%d/%m/%Y")

            # Cas 3: Objet datetime
            if isinstance(date_input, datetime):
                return date_input.strftime("%d/%m/%Y")

            # Cas 4: Timestamp ou autre format numrique
            if isinstance(date_input, (int, float)):
                date_obj = datetime.fromtimestamp(date_input)
                return date_obj.strftime("%d/%m/%Y")

        except:
            # En cas d'erreur, retourne la valeur originale sans l'heure
            if isinstance(date_input, str) and ' ' in date_input:
                return date_input.split(' ')[0]
            return str(date_input)

    def format_montant_xpf(self, montant):
        """Formate un montant en XPF - INCHANG"""
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

    def create_header(self, numero_avoir):
        """Cre l'en-tte du PDF avec logo et code-barres - INCHANG"""
        header_data = []
        header_row = []

        # Logo  gauche
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
        company_info = """<b>QUINCAILLERIE CALÉDONIENNE</b><br/>
        <font size="8">13 Rue Ampère - Ducos, Nouvelle-Calédonie<br/>
         Tél. 27 27 00 | Web www.quincaillerie.nc | Email info@quincaillerie.nc</font>"""

        header_row.append(Paragraph(company_info, self.company_style))

        # Code-barres  droite
        barcode_value = numero_avoir.replace('/', '')
        barcode = code128.Code128(barcode_value, barWidth=0.4*mm, barHeight=12*mm)
        barcode_container = Table(
            [[barcode], [Paragraph(f"<font size='7'><b>{barcode_value}</b></font>", self.styles['Normal'])]],
            colWidths=[50*mm]
        )
        barcode_container.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        header_row.append(barcode_container)

        header_data.append(header_row)

        # Crer le tableau d'en-tte
        header_table = Table(header_data, colWidths=[50*mm, 90*mm, 50*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        return header_table

    def create_horaires_section(self):
        """Cre la section des horaires - INCHANG"""
        horaires_data = [['Horaires: Lun-Ven 7h-17h | Sam 7h30-16h | Dim Fermé']]
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
        return horaires_table

    def create_info_montant_section(self, numero_avoir, data):
        """Cre la section informations et montant - MODIFI POUR LES DATES"""
        info_montant_data = []

        # Informations  gauche - DATES CORRIGES
        # On utilise les dates REELLES de l'avoir si elles sont fournies dans
        # `data` (indispensable pour une REIMPRESSION : on ne doit pas reediter
        # une validite calculee a la date du jour). A defaut (creation d'un
        # nouvel avoir), on retombe sur la date du jour / date du jour + duree.
        date_emission = data.get('date_creation') or datetime.now()
        date_validite_aff = data.get('date_validite') or (
            datetime.now() + timedelta(days=AVOIR_CONFIG['VALIDITE_JOURS'])
        )
        info_data = [
            ['N° AVOIR', numero_avoir],
            ['Date émission', self.format_date_fr(date_emission)],
            ['Validité', self.format_date_fr(date_validite_aff)],
            ['Durée validité', f"{AVOIR_CONFIG['VALIDITE_JOURS']} jours"],
        ]

        info_table = Table(info_data, colWidths=[35*mm, 55*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        # Montant centr - INCHANG
        montant_formate = self.format_montant_xpf(data["montant"])
        montant_data = [
            ['MONTANT TTC'],
            [Paragraph(f"<para align='center' spaceb='4'><font size='16'><b>{montant_formate}</b></font></para>",
                    self.styles['Normal'])]
        ]

        montant_table = Table(montant_data, colWidths=[90*mm])
        montant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff001')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 22),
        ]))

        info_montant_data.append([info_table, montant_table])
        info_montant_main = Table(info_montant_data, colWidths=[95*mm, 95*mm])
        info_montant_main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return info_montant_main

    def create_client_details_section(self, data):
        """Cre la section client et dtails - MODIFI POUR LES DATES"""
        client_details_data = []

        # Client  gauche - INCHANG
        client_data = [
            ['CLIENT', ''],
            ['N° Client:', data['numero_client']],
            ['Nom:', data['nom_client']],
            ['Email:', data.get('email_client', 'Non renseigné') or 'Non renseigné'],
        ]

        client_table = Table(client_data, colWidths=[25*mm, 65*mm])
        client_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#000000')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#000000')),
        ]))

        # Type d'avoir : "Résidu" (avoir enfant) ou "Retour marchandise" (par défaut)
        est_residu = bool(data.get('est_residu'))
        type_label = "Résidu" if est_residu else "Retour marchandise"

        # Dtails  droite - DATES CORRIGES
        details_data = [
            ['DÉTAILS', ''],
            ['Type:', type_label],
            ['facture initial:', data['numero_facture']],
        ]

        # Date facture - TOUJOURS CORRIGE
        date_facture = data.get('date_facture', '')
        if date_facture:
            details_data.append(['Date facture :', self.format_date_fr(date_facture)])

        # "facture utilisation avoir" :
        # - avoir NORMAL : a sa place habituelle (juste apres la facture initiale)
        # - RESIDU : on la place TOUT EN BAS (apres les infos de l'avoir parent)
        if not est_residu:
            details_data.append(['facture utilisation avoir:', data['numero_facture_avoir']])
            # Date avoir - CORRIGE SI PRSENTE
            if 'date_facture_avoir' in data and data['date_facture_avoir']:
                details_data.append(['Date avoir :', self.format_date_fr(data['date_facture_avoir'])])

        # Si l'avoir est un résidu (avoir enfant) : reference et montant du parent
        if est_residu:
            parent_num = data.get('avoir_parent_numero')
            if parent_num:
                details_data.append(['Avoir parent:', parent_num])
            parent_montant = data.get('avoir_parent_montant')
            if parent_montant is not None:
                details_data.append(['Montant parent:', self.format_montant_xpf(parent_montant)])
            # En dernier, tout en bas : la facture d'utilisation qui a genere ce residu.
            details_data.append(['facture utilisation avoir:', data['numero_facture_avoir']])

        # Largeurs ajustees : la colonne libelle est elargie pour que le plus
        # long libelle ("facture utilisation avoir:") tienne dans le cadre, et
        # les valeurs sont calees a droite pour gagner de la place.
        # Le cadre total reste inchange (50 + 40 = 90 mm).
        details_table = Table(details_data, colWidths=[50*mm, 40*mm])
        details_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#000000')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#000000')),
        ]))

        client_details_data.append([client_table, details_table])
        client_details_main = Table(client_details_data, colWidths=[95*mm, 95*mm])
        client_details_main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return client_details_main

    def create_conditions_section(self):
        """Cre la section des conditions d'utilisation - INCHANG"""
        conditions_title = "<b>CONDITIONS D'UTILISATION</b>"
        conditions_text = """Valable {0} jours | Présenter l'original en caisse au moment du paiement
         Non remis en cas de perte | Non remboursable""".format(AVOIR_CONFIG['VALIDITE_JOURS'])

        conditions_title_para = Paragraph(conditions_title, self.conditions_title_style)
        conditions_text_para = Paragraph(conditions_text, self.conditions_style)

        conditions_table = Table([[conditions_title_para], [conditions_text_para]], colWidths=[190*mm])
        conditions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff9c4')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#f9a825')),
            ('TOPPADDING', (0, 0), (0, 0), 5),
            ('BOTTOMPADDING', (0, 0), (0, 0), 2),
            ('TOPPADDING', (0, 1), (0, 1), 2),
            ('BOTTOMPADDING', (0, 1), (0, 1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        return conditions_table

    def create_validation_section(self, user_name, date_creation=None):
        """Cre la section de validation et tampon - MODIFI POUR LA DATE

        `date_creation` : date reelle de creation de l'avoir (pour une
        reimpression). Si None, on utilise la date du jour (creation initiale).
        """
        # VALIDATION - cadre du haut  gauche - DATE CORRIGE
        validation_info = [
            ['VALIDATION', ''],
            ['Créé par:', user_name],
            ['Date:', self.format_date_fr(date_creation or datetime.now())],
        ]

        validation_table = Table(validation_info, colWidths=[30*mm, 60*mm], rowHeights=[8*mm, 7*mm, 7*mm])
        validation_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#e0e0e0')),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#999999')),
        ]))

        # SIGNATURE - INCHANG
        signature_data = [
            ['SIGNATURE'],
            [''],
            [''],
            ['']
        ]

        signature_table = Table(signature_data, colWidths=[90*mm], rowHeights=[7*mm, 10*mm, 10*mm, 10*mm])
        signature_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e0e0e0')),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
        ]))

        # CACHET - INCHANG
        tampon_data = [
            ['CACHET'],
            [''],
            [''],
            [''],
            ['']
        ]

        tampon_table = Table(tampon_data, colWidths=[90*mm], rowHeights=[8*mm, 15*mm, 15*mm, 15*mm, 8*mm])
        tampon_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e0e0e0')),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
        ]))

        # Crer une table avec les deux lments  gauche
        left_column_data = [
            [validation_table],
            [Spacer(1, 1*mm)],
            [signature_table]
        ]

        left_column = Table(left_column_data, colWidths=[90*mm])
        left_column.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Assembler les deux colonnes
        validation_main_data = [[left_column, tampon_table]]
        validation_main = Table(validation_main_data, colWidths=[95*mm, 95*mm])
        validation_main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return validation_main

    def create_footer(self):
        """Cre le pied de page - MODIFI POUR LA DATE"""
        footer_text = f"""<b>QUINCAILLERIE CALÉDONIENNE</b> | 13 Rue Ampère - Ducos, NC | Tél. 27 27 00
        | Document généré le {self.format_date_fr(datetime.now())}
         © {datetime.now().year} Module de Gestion des Avoirs QC"""

        return Paragraph(footer_text, self.footer_style)

    def generate(self, numero_avoir, data, user_name, output_path=None):
        """
        Gnre le PDF de l'avoir.

        Args:
            numero_avoir: Numero de l'avoir.
            data: Donnees de l'avoir (client, montant, dates, etc.).
            user_name: Nom a afficher comme createur.
            output_path: Emplacement de sortie du PDF. Si fourni (ex.
                reimpression enregistree sur le poste), le PDF est ecrit la ;
                sinon il est ecrit dans le dossier de base par defaut.
        """
        try:
            # Chemin du PDF : emplacement demande (reimpression sur le poste) ou
            # dossier de base par defaut.
            if output_path:
                pdf_path = Path(output_path)
            else:
                pdf_path = BASE_PATH / f"avoir_{numero_avoir.replace('/', '_')}.pdf"

            # Cration du document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=10*mm,
                leftMargin=10*mm,
                topMargin=8*mm,
                bottomMargin=8*mm
            )

            elements = []

            # Construction du document
            elements.append(self.create_header(numero_avoir))
            elements.append(Spacer(1, 2*mm))
            elements.append(self.create_horaires_section())
            elements.append(Spacer(1, 3*mm))

            # Titre du document
            doc_title = Paragraph("<b>BON D'AVOIR</b>", ParagraphStyle(
                'DocTitle',
                fontSize=18,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=3*mm
            ))
            elements.append(doc_title)

            # Sections principales
            elements.append(self.create_info_montant_section(numero_avoir, data))
            elements.append(Spacer(1, 4*mm))

            elements.append(self.create_client_details_section(data))
            elements.append(Spacer(1, 4*mm))

            elements.append(self.create_conditions_section())
            elements.append(Spacer(1, 4*mm))

            elements.append(self.create_validation_section(user_name, data.get('date_creation')))
            elements.append(Spacer(1, 3*mm))

            elements.append(self.create_footer())

            # Gnration du PDF
            doc.build(elements)

            # Ouvrir le PDF automatiquement
            if os.name == 'nt':
                os.startfile(str(pdf_path))
            elif os.name == 'posix':
                os.system(f'open "{pdf_path}"')

            return True, str(pdf_path)

        except Exception as e:
            return False, str(e)