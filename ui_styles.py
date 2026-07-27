"""
Module de configuration des styles et thmes
Module de Gestion des Avoirs Clients - STOYANN
Version: 2.0 - Styles centraliss pour interface moderne
"""

import tkinter as tk
from tkinter import ttk, font
import json
from pathlib import Path

class ThemeManager:
    """Gestionnaire de thmes pour l'application"""
    
    def __init__(self):
        self.themes = {
            'modern_light': ModernLightTheme(),
            'modern_dark': ModernDarkTheme(),
            'classic': ClassicTheme(),
            'high_contrast': HighContrastTheme()
        }
        self.current_theme = 'modern_light'
        self.load_user_preferences()
    
    def load_user_preferences(self):
        """Charge les prfrences utilisateur"""
        try:
            pref_file = Path.home() / '.qc_avoirs' / 'preferences.json'
            if pref_file.exists():
                with open(pref_file, 'r') as f:
                    prefs = json.load(f)
                    self.current_theme = prefs.get('theme', 'modern_light')
        except:
            pass
    
    def save_user_preferences(self):
        """Sauvegarde les prfrences utilisateur"""
        try:
            pref_dir = Path.home() / '.qc_avoirs'
            pref_dir.mkdir(exist_ok=True)
            pref_file = pref_dir / 'preferences.json'
            
            prefs = {
                'theme': self.current_theme,
                'version': '2.0'
            }
            
            with open(pref_file, 'w') as f:
                json.dump(prefs, f, indent=2)
        except:
            pass
    
    def get_theme(self):
        """Retourne le thme actuel"""
        return self.themes.get(self.current_theme, self.themes['modern_light'])
    
    def set_theme(self, theme_name):
        """Change le thme actuel"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.save_user_preferences()
            return True
        return False
    
    def apply_theme(self, root):
        """Applique le thme  une fentre"""
        theme = self.get_theme()
        theme.apply_to_window(root)

class BaseTheme:
    """Classe de base pour les thmes"""
    
    def __init__(self):
        self.name = "Base Theme"
        self.colors = {}
        self.fonts = {}
        self.styles = {}
        self.animations = {}
        self.icons = {}
        self.setup_theme()
    
    def setup_theme(self):
        """Configuration du thme -  surcharger"""
        pass
    
    def apply_to_window(self, window):
        """Applique le thme  une fentre"""
        window.configure(bg=self.colors['bg_primary'])
        self.configure_ttk_styles()
    
    def configure_ttk_styles(self):
        """Configure les styles ttk"""
        style = ttk.Style()
        
        # Style gnral
        style.configure(
            '.',
            background=self.colors['bg_primary'],
            foreground=self.colors['text_primary'],
            font=self.fonts['normal']
        )
        
        # Notebooks (onglets)
        style.configure(
            'Modern.TNotebook',
            background=self.colors['bg_primary'],
            borderwidth=0,
            relief='flat'
        )
        
        style.configure(
            'Modern.TNotebook.Tab',
            padding=self.styles['tab_padding'],
            background=self.colors['bg_secondary'],
            foreground=self.colors['text_primary'],
            font=self.fonts['tab']
        )
        
        style.map(
            'Modern.TNotebook.Tab',
            background=[
                ('selected', self.colors['primary']),
                ('active', self.colors['hover'])
            ],
            foreground=[
                ('selected', self.colors['text_on_primary']),
                ('active', self.colors['text_primary'])
            ]
        )
        
        # Boutons
        style.configure(
            'Modern.TButton',
            relief='flat',
            background=self.colors['primary'],
            foreground=self.colors['text_on_primary'],
            borderwidth=0,
            font=self.fonts['button'],
            padding=self.styles['button_padding']
        )
        
        style.map(
            'Modern.TButton',
            background=[
                ('pressed', self.colors['primary_dark']),
                ('active', self.colors['primary_light'])
            ]
        )
        
        # Treeview
        style.configure(
            'Modern.Treeview',
            background=self.colors['bg_white'],
            foreground=self.colors['text_primary'],
            rowheight=self.styles['treeview_rowheight'],
            fieldbackground=self.colors['bg_white'],
            borderwidth=0,
            font=self.fonts['table']
        )
        
        style.configure(
            'Modern.Treeview.Heading',
            background=self.colors['primary'],
            foreground=self.colors['text_on_primary'],
            relief='flat',
            font=self.fonts['table_header']
        )
        
        style.map(
            'Modern.Treeview',
            background=[
                ('selected', self.colors['selection'])
            ],
            foreground=[
                ('selected', self.colors['text_on_selection'])
            ]
        )
        
        # Combobox
        style.configure(
            'Modern.TCombobox',
            fieldbackground=self.colors['bg_white'],
            background=self.colors['bg_white'],
            foreground=self.colors['text_primary'],
            borderwidth=1,
            relief='solid',
            font=self.fonts['input']
        )
        
        # Entry
        style.configure(
            'Modern.TEntry',
            fieldbackground=self.colors['bg_white'],
            foreground=self.colors['text_primary'],
            borderwidth=1,
            relief='solid',
            font=self.fonts['input']
        )
        
        # Progressbar
        style.configure(
            'Modern.Horizontal.TProgressbar',
            background=self.colors['primary'],
            troughcolor=self.colors['bg_secondary'],
            borderwidth=0,
            relief='flat'
        )
        
        # Scale
        style.configure(
            'Modern.Horizontal.TScale',
            background=self.colors['bg_primary'],
            troughcolor=self.colors['bg_secondary'],
            borderwidth=0
        )
        
        # Scrollbar
        style.configure(
            'Modern.Vertical.TScrollbar',
            background=self.colors['bg_secondary'],
            troughcolor=self.colors['bg_primary'],
            borderwidth=0,
            relief='flat',
            arrowcolor=self.colors['text_secondary']
        )
    
    def get_button_style(self, button_type='default'):
        """Retourne le style pour un type de bouton"""
        button_styles = {
            'default': {
                'bg': self.colors['primary'],
                'fg': self.colors['text_on_primary'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'success': {
                'bg': self.colors['success'],
                'fg': self.colors['white'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'danger': {
                'bg': self.colors['error'],
                'fg': self.colors['white'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'warning': {
                'bg': self.colors['warning'],
                'fg': self.colors['white'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'info': {
                'bg': self.colors['info'],
                'fg': self.colors['white'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'outline': {
                'bg': self.colors['bg_white'],
                'fg': self.colors['primary'],
                'font': self.fonts['button'],
                'bd': 2,
                'relief': 'solid',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            },
            'ghost': {
                'bg': self.colors['transparent'],
                'fg': self.colors['primary'],
                'font': self.fonts['button'],
                'bd': 0,
                'relief': 'flat',
                'cursor': 'hand2',
                'padx': 20,
                'pady': 10
            }
        }
        return button_styles.get(button_type, button_styles['default'])
    
    def get_card_style(self):
        """Retourne le style pour une carte"""
        return {
            'bg': self.colors['bg_white'],
            'relief': 'flat',
            'bd': 0,
            'highlightbackground': self.colors['border'],
            'highlightthickness': 1
        }
    
    def get_input_style(self):
        """Retourne le style pour un champ de saisie"""
        return {
            'font': self.fonts['input'],
            'bg': self.colors['bg_white'],
            'fg': self.colors['text_primary'],
            'bd': 1,
            'relief': 'solid',
            'insertbackground': self.colors['primary']
        }

class ModernLightTheme(BaseTheme):
    """Thme moderne clair"""
    
    def setup_theme(self):
        self.name = "Modern Light"
        
        # Palette de couleurs
        self.colors = {
            # Couleurs principales
            'primary': '#fff001',           # Jaune signature
            'primary_light': '#fffa4d',     # Jaune clair
            'primary_dark': '#ccb800',      # Jaune fonc
            'secondary': '#000000',         # Noir
            'accent': '#ffd700',           # Or
            
            # Couleurs d'tat
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#f44336',
            'info': '#2196F3',
            
            # Couleurs de fond
            'bg_primary': '#fafafa',
            'bg_secondary': '#f5f5f5',
            'bg_white': '#ffffff',
            'bg_dark': '#212121',
            
            # Couleurs de texte
            'text_primary': '#212121',
            'text_secondary': '#757575',
            'text_disabled': '#bdbdbd',
            'text_on_primary': '#000000',
            'text_on_dark': '#ffffff',
            'text_on_selection': '#ffffff',
            
            # Autres
            'border': '#e0e0e0',
            'hover': '#f5f5f5',
            'selection': '#2196F3',
            'transparent': '#00000000',
            'shadow': '#00000020',
            'white': '#ffffff',
            'sidebar_bg': '#1a1a1a'
        }
        
        # Configuration des polices
        self.fonts = {
            'heading1': ('Segoe UI', 24, 'bold'),
            'heading2': ('Segoe UI', 20, 'bold'),
            'heading3': ('Segoe UI', 16, 'bold'),
            'heading4': ('Segoe UI', 14, 'bold'),
            'heading5': ('Segoe UI', 12, 'bold'),
            'normal': ('Segoe UI', 10),
            'small': ('Segoe UI', 9),
            'tiny': ('Segoe UI', 8),
            'button': ('Segoe UI', 10, 'bold'),
            'input': ('Segoe UI', 10),
            'tab': ('Segoe UI', 10),
            'table': ('Segoe UI', 9),
            'table_header': ('Segoe UI', 10, 'bold'),
            'code': ('Consolas', 10)
        }
        
        # Styles divers
        self.styles = {
            'border_radius': 5,
            'shadow_offset': 2,
            'tab_padding': [20, 12],
            'button_padding': [20, 10],
            'treeview_rowheight': 30,
            'sidebar_width': 250,
            'header_height': 70,
            'statusbar_height': 30
        }
        
        # Configuration des animations
        self.animations = {
            'fade_duration': 300,
            'slide_duration': 200,
            'hover_duration': 100,
            'enable_animations': True
        }
        
        # Icnes (emoji ou caractres unicode)
        self.icons = {
            'home': '',
            'add': '',
            'edit': '',
            'delete': '',
            'save': '',
            'search': '',
            'refresh': '',
            'settings': '',
            'user': '',
            'email': '',
            'calendar': '',
            'clock': '',
            'warning': '',
            'error': '',
            'success': '',
            'info': '',
            'document': '',
            'folder': '',
            'chart': '',
            'money': '',
            'logout': '',
            'print': '',
            'export': '',
            'import': ''
        }

class ModernDarkTheme(BaseTheme):
    """Thme moderne sombre"""
    
    def setup_theme(self):
        self.name = "Modern Dark"
        
        # Palette de couleurs sombres
        self.colors = {
            'primary': '#fff001',
            'primary_light': '#fffa4d',
            'primary_dark': '#ccb800',
            'secondary': '#ffffff',
            'accent': '#ffd700',
            
            'success': '#66BB6A',
            'warning': '#FFA726',
            'error': '#EF5350',
            'info': '#42A5F5',
            
            'bg_primary': '#121212',
            'bg_secondary': '#1e1e1e',
            'bg_white': '#2a2a2a',
            'bg_dark': '#000000',
            
            'text_primary': '#ffffff',
            'text_secondary': '#b0b0b0',
            'text_disabled': '#606060',
            'text_on_primary': '#000000',
            'text_on_dark': '#ffffff',
            'text_on_selection': '#000000',
            
            'border': '#404040',
            'hover': '#333333',
            'selection': '#fff001',
            'transparent': '#00000000',
            'shadow': '#00000080',
            'white': '#ffffff',
            'sidebar_bg': '#0a0a0a'
        }
        
        # Polices identiques mais adaptes au thme sombre
        self.fonts = {
            'heading1': ('Segoe UI', 24, 'bold'),
            'heading2': ('Segoe UI', 20, 'bold'),
            'heading3': ('Segoe UI', 16, 'bold'),
            'heading4': ('Segoe UI', 14, 'bold'),
            'heading5': ('Segoe UI', 12, 'bold'),
            'normal': ('Segoe UI', 10),
            'small': ('Segoe UI', 9),
            'tiny': ('Segoe UI', 8),
            'button': ('Segoe UI', 10, 'bold'),
            'input': ('Segoe UI', 10),
            'tab': ('Segoe UI', 10),
            'table': ('Segoe UI', 9),
            'table_header': ('Segoe UI', 10, 'bold'),
            'code': ('Consolas', 10)
        }
        
        self.styles = {
            'border_radius': 5,
            'shadow_offset': 3,
            'tab_padding': [20, 12],
            'button_padding': [20, 10],
            'treeview_rowheight': 30,
            'sidebar_width': 250,
            'header_height': 70,
            'statusbar_height': 30
        }
        
        self.animations = {
            'fade_duration': 300,
            'slide_duration': 200,
            'hover_duration': 100,
            'enable_animations': True
        }
        
        # Icnes identiques
        self.icons = ModernLightTheme().icons

class ClassicTheme(BaseTheme):
    """Thme classique"""
    
    def setup_theme(self):
        self.name = "Classic"
        
        self.colors = {
            'primary': '#003366',
            'primary_light': '#0066cc',
            'primary_dark': '#001a33',
            'secondary': '#666666',
            'accent': '#ff6600',
            
            'success': '#339933',
            'warning': '#ff9933',
            'error': '#cc3333',
            'info': '#3366cc',
            
            'bg_primary': '#f0f0f0',
            'bg_secondary': '#e0e0e0',
            'bg_white': '#ffffff',
            'bg_dark': '#333333',
            
            'text_primary': '#000000',
            'text_secondary': '#666666',
            'text_disabled': '#999999',
            'text_on_primary': '#ffffff',
            'text_on_dark': '#ffffff',
            'text_on_selection': '#ffffff',
            
            'border': '#cccccc',
            'hover': '#e8e8e8',
            'selection': '#0066cc',
            'transparent': '#00000000',
            'shadow': '#00000030',
            'white': '#ffffff',
            'sidebar_bg': '#003366'
        }
        
        self.fonts = {
            'heading1': ('Arial', 22, 'bold'),
            'heading2': ('Arial', 18, 'bold'),
            'heading3': ('Arial', 14, 'bold'),
            'heading4': ('Arial', 12, 'bold'),
            'heading5': ('Arial', 11, 'bold'),
            'normal': ('Arial', 10),
            'small': ('Arial', 9),
            'tiny': ('Arial', 8),
            'button': ('Arial', 10, 'bold'),
            'input': ('Arial', 10),
            'tab': ('Arial', 10),
            'table': ('Arial', 9),
            'table_header': ('Arial', 10, 'bold'),
            'code': ('Courier New', 10)
        }
        
        self.styles = {
            'border_radius': 0,
            'shadow_offset': 1,
            'tab_padding': [15, 8],
            'button_padding': [15, 8],
            'treeview_rowheight': 25,
            'sidebar_width': 200,
            'header_height': 60,
            'statusbar_height': 25
        }
        
        self.animations = {
            'fade_duration': 200,
            'slide_duration': 150,
            'hover_duration': 50,
            'enable_animations': False
        }
        
        self.icons = ModernLightTheme().icons

class HighContrastTheme(BaseTheme):
    """Thme haute contraste pour l'accessibilit"""
    
    def setup_theme(self):
        self.name = "High Contrast"
        
        self.colors = {
            'primary': '#ffff00',
            'primary_light': '#ffff66',
            'primary_dark': '#cccc00',
            'secondary': '#ffffff',
            'accent': '#00ffff',
            
            'success': '#00ff00',
            'warning': '#ff8800',
            'error': '#ff0000',
            'info': '#0088ff',
            
            'bg_primary': '#000000',
            'bg_secondary': '#1a1a1a',
            'bg_white': '#333333',
            'bg_dark': '#000000',
            
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'text_disabled': '#666666',
            'text_on_primary': '#000000',
            'text_on_dark': '#ffffff',
            'text_on_selection': '#000000',
            
            'border': '#ffffff',
            'hover': '#333333',
            'selection': '#ffff00',
            'transparent': '#00000000',
            'shadow': '#00000000',
            'white': '#ffffff',
            'sidebar_bg': '#000000'
        }
        
        self.fonts = {
            'heading1': ('Arial', 26, 'bold'),
            'heading2': ('Arial', 22, 'bold'),
            'heading3': ('Arial', 18, 'bold'),
            'heading4': ('Arial', 16, 'bold'),
            'heading5': ('Arial', 14, 'bold'),
            'normal': ('Arial', 12),
            'small': ('Arial', 11),
            'tiny': ('Arial', 10),
            'button': ('Arial', 12, 'bold'),
            'input': ('Arial', 12),
            'tab': ('Arial', 12),
            'table': ('Arial', 11),
            'table_header': ('Arial', 12, 'bold'),
            'code': ('Courier New', 12)
        }
        
        self.styles = {
            'border_radius': 0,
            'shadow_offset': 0,
            'tab_padding': [25, 15],
            'button_padding': [25, 15],
            'treeview_rowheight': 35,
            'sidebar_width': 280,
            'header_height': 80,
            'statusbar_height': 35
        }
        
        self.animations = {
            'fade_duration': 0,
            'slide_duration': 0,
            'hover_duration': 0,
            'enable_animations': False
        }
        
        self.icons = ModernLightTheme().icons

class StyleHelper:
    """Classe utilitaire pour appliquer les styles"""
    
    @staticmethod
    def apply_card_style(widget, theme):
        """Applique le style de carte  un widget"""
        card_style = theme.get_card_style()
        widget.configure(**card_style)
    
    @staticmethod
    def apply_button_style(button, theme, button_type='default'):
        """Applique le style de bouton"""
        button_style = theme.get_button_style(button_type)
        button.configure(**button_style)
        
        # Ajouter les effets hover si les animations sont actives
        if theme.animations['enable_animations']:
            original_bg = button_style['bg']
            hover_color = theme.colors.get('hover', original_bg)
            
            def on_enter(e):
                button.configure(bg=hover_color)
            
            def on_leave(e):
                button.configure(bg=original_bg)
            
            button.bind('<Enter>', on_enter)
            button.bind('<Leave>', on_leave)
    
    @staticmethod
    def apply_input_style(entry, theme):
        """Applique le style de champ de saisie"""
        input_style = theme.get_input_style()
        entry.configure(**input_style)
    
    @staticmethod
    def create_gradient(canvas, color1, color2, direction='vertical'):
        """Cre un dgrad sur un canvas"""
        width = canvas.winfo_reqwidth()
        height = canvas.winfo_reqheight()
        
        if direction == 'vertical':
            for i in range(height):
                ratio = i / height
                r1, g1, b1 = StyleHelper.hex_to_rgb(color1)
                r2, g2, b2 = StyleHelper.hex_to_rgb(color2)
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                color = StyleHelper.rgb_to_hex(r, g, b)
                canvas.create_line(0, i, width, i, fill=color, width=1)
        else:  # horizontal
            for i in range(width):
                ratio = i / width
                r1, g1, b1 = StyleHelper.hex_to_rgb(color1)
                r2, g2, b2 = StyleHelper.hex_to_rgb(color2)
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                color = StyleHelper.rgb_to_hex(r, g, b)
                canvas.create_line(i, 0, i, height, fill=color, width=1)
    
    @staticmethod
    def hex_to_rgb(hex_color):
        """Convertit une couleur hex en RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r, g, b):
        """Convertit RGB en hex"""
        return f'#{r:02x}{g:02x}{b:02x}'
    
    @staticmethod
    def animate_fade(widget, start_alpha=0, end_alpha=1, duration=300, callback=None):
        """Anime un fondu sur un widget"""
        steps = 30
        delay = duration // steps
        alpha_step = (end_alpha - start_alpha) / steps
        
        def fade_step(step):
            if step <= steps:
                alpha = start_alpha + (alpha_step * step)
                widget.attributes('-alpha', alpha)
                widget.after(delay, lambda: fade_step(step + 1))
            elif callback:
                callback()
        
        fade_step(0)
    
    @staticmethod
    def animate_slide(widget, start_x, end_x, start_y, end_y, duration=200, callback=None):
        """Anime un glissement sur un widget"""
        steps = 20
        delay = duration // steps
        x_step = (end_x - start_x) / steps
        y_step = (end_y - start_y) / steps
        
        def slide_step(step):
            if step <= steps:
                x = start_x + (x_step * step)
                y = start_y + (y_step * step)
                widget.geometry(f'+{int(x)}+{int(y)}')
                widget.after(delay, lambda: slide_step(step + 1))
            elif callback:
                callback()
        
        slide_step(0)

# Instance globale du gestionnaire de thmes
theme_manager = ThemeManager()

# Fonction helper pour obtenir le thme actuel
def get_current_theme():
    """Retourne le thme actuel"""
    return theme_manager.get_theme()

# Fonction helper pour changer de thme
def set_theme(theme_name):
    """Change le thme actuel"""
    return theme_manager.set_theme(theme_name)

# Fonction helper pour appliquer le thme  une fentre
def apply_theme_to_window(window):
    """Applique le thme actuel  une fentre"""
    theme_manager.apply_theme(window)