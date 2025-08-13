import flet as ft
import json
import os

class SettingsApp:
    def __init__(self):
        self.page = None
        self.settings_file = "settings.json"
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Ayarları dosyadan yükle"""
        default_settings = {
            "theme": "light",
            "language": "tr",
            "auto_start": False,
            "notifications": True
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Varsayılan ayarları güncelle
                    default_settings.update(loaded_settings)
            return default_settings
        except Exception:
            return default_settings
            
    def save_settings(self):
        """Ayarları dosyaya kaydet"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ayarlar kaydedilemedi: {e}")
        
    def main(self, page: ft.Page):
        page.title = "Ayarlar"
        page.theme_mode = ft.ThemeMode.LIGHT if self.settings.get("theme", "light") == "light" else ft.ThemeMode.DARK
        page.window_width = 700
        page.window_height = 800
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # Tema seçici
        self.theme_dropdown = ft.Dropdown(
            label="Tema",
            width=200,
            value=self.settings.get("theme", "light"),
            options=[
                ft.dropdown.Option("light", "Açık Tema"),
                ft.dropdown.Option("dark", "Koyu Tema")
            ],
            on_change=self.on_theme_change
        )
        
        # Dil seçici
        self.language_dropdown = ft.Dropdown(
            label="Dil",
            width=200,
            value=self.settings.get("language", "tr"),
            options=[
                ft.dropdown.Option("tr", "Türkçe"),
                ft.dropdown.Option("en", "English")
            ],
            on_change=self.on_language_change
        )
        
        # Otomatik başlatma
        self.auto_start_switch = ft.Switch(
            label="Otomatik Başlatma",
            value=self.settings.get("auto_start", False),
            on_change=self.on_auto_start_change
        )
        
        # Bildirimler
        self.notifications_switch = ft.Switch(
            label="Bildirimler",
            value=self.settings.get("notifications", True),
            on_change=self.on_notifications_change
        )
        
        # Back button
        back_button = ft.ElevatedButton(
            text="Back to Main Menu",
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda _: page.window_close(),
            width=200,
            height=40,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600
            )
        )
        
        # Ayarları sıfırla butonu
        reset_button = ft.ElevatedButton(
            text="Ayarları Sıfırla",
            icon=ft.Icons.RESTORE,
            on_click=self.reset_settings,
            width=200,
            height=40,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.ORANGE_600
            )
        )
        
        # Layout
        content = ft.Column([
            ft.Text("Ayarlar", 
                   size=24, weight=ft.FontWeight.BOLD, 
                   color=ft.Colors.BLUE_600),
            ft.Divider(),
            
            # Genel Ayarlar
            ft.Text("Genel Ayarlar", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PALETTE, color=ft.Colors.BLUE),
                        self.theme_dropdown
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.LANGUAGE, color=ft.Colors.GREEN),
                        self.language_dropdown
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.ORANGE),
                        self.auto_start_switch
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.NOTIFICATIONS, color=ft.Colors.PURPLE),
                        self.notifications_switch
                    ])
                ], spacing=15),
                padding=20,
                bgcolor=ft.Colors.GREY_100,
                border_radius=10
            ),
            
            ft.Divider(),
            
            # Yapımcı Bilgileri
            ft.Text("Yapımcı Bilgileri", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE, size=30),
                        ft.Column([
                            ft.Text("Geliştirici", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("Samet Kaya", size=16, color=ft.Colors.BLUE_600)
                        ], spacing=2)
                    ]),
                    
                    ft.Divider(height=1),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CODE, color=ft.Colors.GREEN, size=30),
                        ft.Column([
                            ft.Text("Proje Adı", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("TikTok & YouTube Video İndirici", size=16, color=ft.Colors.GREEN_600)
                        ], spacing=2)
                    ]),
                    
                    ft.Divider(height=1),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, color=ft.Colors.ORANGE, size=30),
                        ft.Column([
                            ft.Text("Versiyon", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("v2.0.0 - 2024", size=16, color=ft.Colors.ORANGE_600)
                        ], spacing=2)
                    ]),
                    
                    ft.Divider(height=1),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.EMAIL, color=ft.Colors.RED, size=30),
                        ft.Column([
                            ft.Text("İletişim", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("sametkaya@example.com", size=16, color=ft.Colors.RED_600)
                        ], spacing=2)
                    ]),
                    
                    ft.Divider(height=1),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.WEB, color=ft.Colors.PURPLE, size=30),
                        ft.Column([
                            ft.Text("GitHub", size=14, weight=ft.FontWeight.BOLD),
                            ft.Text("github.com/sametkaya", size=16, color=ft.Colors.PURPLE_600)
                        ], spacing=2)
                    ])
                ], spacing=15),
                padding=20,
                bgcolor=ft.Colors.GREY_100,
                border_radius=10
            ),
            
            ft.Divider(),
            
            # Özellikler
            ft.Text("Uygulama Özellikleri", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("TikTok tekli video indirme ve düzenleme", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("YouTube tekli video indirme ve düzenleme", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("TikTok toplu video indirme", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("YouTube toplu short video indirme", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("Logo ekleme ve boyutlandırma", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("Müzik ekleme ve ses seviyesi ayarlama", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("FFmpeg tabanlı video işleme", size=14)
                    ]),
                    
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("Modern ve kullanıcı dostu arayüz", size=14)
                    ])
                ], spacing=10),
                padding=20,
                bgcolor=ft.Colors.GREY_100,
                border_radius=10
            ),
            
            ft.Divider(),
            
            # Butonlar
            ft.Row([
                back_button,
                reset_button
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            
            ft.Container(height=20),
            
            # Telif hakkı
            ft.Text(
                "© 2024 Samet Kaya. Tüm hakları saklıdır.",
                size=12,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER
            )
        ], spacing=15, scroll=ft.ScrollMode.AUTO)
        
        scrollable_content = ft.Container(
            content=content,
            expand=True,
            padding=20
        )
        
        page.add(scrollable_content)
        
    def on_theme_change(self, e):
        """Tema değiştirildiğinde"""
        new_theme = e.control.value
        self.settings["theme"] = new_theme
        self.save_settings()
        
        # Temayı uygula
        if new_theme == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            
        self.page.update()
        
    def on_language_change(self, e):
        """Dil değiştirildiğinde"""
        new_language = e.control.value
        self.settings["language"] = new_language
        self.save_settings()
        
    def on_auto_start_change(self, e):
        """Otomatik başlatma değiştirildiğinde"""
        self.settings["auto_start"] = e.control.value
        self.save_settings()
        
    def on_notifications_change(self, e):
        """Bildirimler değiştirildiğinde"""
        self.settings["notifications"] = e.control.value
        self.save_settings()
        
    def reset_settings(self, e):
        """Ayarları sıfırla"""
        # Onay dialogu göster
        def confirm_reset(e):
            if e.control.text == "Evet":
                # Ayarları sıfırla
                self.settings = {
                    "theme": "light",
                    "language": "tr",
                    "auto_start": False,
                    "notifications": True
                }
                self.save_settings()
                
                # UI'yi güncelle
                self.theme_dropdown.value = "light"
                self.language_dropdown.value = "tr"
                self.auto_start_switch.value = False
                self.notifications_switch.value = True
                
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.page.update()
                
            # Dialogu kapat
            dialog.open = False
            self.page.update()
            
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ayarları Sıfırla"),
            content=ft.Text("Tüm ayarlar varsayılan değerlere sıfırlanacak. Emin misiniz?"),
            actions=[
                ft.TextButton("Hayır", on_click=confirm_reset),
                ft.TextButton("Evet", on_click=confirm_reset)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

def main():
    app = SettingsApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()