import flet as ft
import os
import subprocess
import sys
import time
import threading
import json
from translations import Translations
from modules.tiktok.tiktok_scraper import TikTokScraper
from video_processor import VideoProcessor
from modules.tiktok.tiktok_single_downloader import TikTokSingleDownloaderApp
from modules.tiktok.tiktok_bulk_downloader import TikTokBulkDownloaderApp
from modules.youtube.youtube_single_downloader import YouTubeSingleDownloaderApp
from modules.youtube.youtube_bulk_downloader import YouTubeBulkDownloaderApp
from modules.instagram.instagram_single_downloader import InstagramSingleDownloaderApp
from modules.instagram.instagram_bulk_downloader import InstagramBulkDownloaderApp
from modules.instagram.instagram_scraper import InstagramScraper
from modules.facebook.facebook_single_downloader import FacebookSingleDownloaderApp
from modules.facebook.facebook_scraper import FacebookScraper
from modules.pinterest.pinterest_single_downloader import PinterestSingleDownloaderApp
from modules.pinterest.pinterest_bulk_downloader import PinterestBulkDownloaderApp
from modules.pinterest.pinterest_scraper import PinterestScraper
from modules.twitter.twitter_single_downloader import TwitterSingleDownloaderApp
from modules.twitter.twitter_bulk_downloader import TwitterBulkDownloaderApp
from modules.twitter.twitter_scraper import TwitterScraper
from splash_screen import show_splash_screen

class MainMenuApp:
    def __init__(self):
        self.page = None
        self.splash_screen_visible = True
        self.settings_visible = False
        self.settings = self.load_settings()
        self.splash_progress = 0.0
        
        # Translation system
        self.translations = Translations()
        self.current_language = self.settings.get("language", "tr")
        
        # Theme always light mode
        self.settings["theme"] = "light"  # Theme fixed to light
        self.current_theme = ft.ThemeMode.LIGHT
    
    def get_text(self, key):
        """Get translation text for current language"""
        return self.translations.get_text(key, self.current_language)
        
    def launch_module(self, module_name):
        """Launch selected module in the same window"""
        try:
            # Import and run module file
            if module_name == "tiktok_single_downloader.py":
                self.show_tiktok_single_downloader()
            elif module_name == "youtube_single_downloader.py":
                self.show_youtube_single_downloader()
            elif module_name == "tiktok_bulk_downloader.py":
                self.show_tiktok_bulk_downloader()
            elif module_name == "youtube_bulk_downloader.py":
                self.show_youtube_bulk_downloader()
            elif module_name == "instagram_single_downloader.py":
                self.show_instagram_single_downloader()
            elif module_name == "instagram_bulk_downloader.py":
                self.show_instagram_bulk_downloader()
            elif module_name == "facebook_single_downloader.py":
                self.show_facebook_single_downloader()
            elif module_name == "pinterest_single_downloader.py":
                self.show_pinterest_single_downloader()
            elif module_name == "pinterest_bulk_downloader.py":
                self.show_pinterest_bulk_downloader()
            elif module_name == "twitter_single_downloader.py":
                self.show_twitter_single_downloader()
            elif module_name == "twitter_bulk_downloader.py":
                self.show_twitter_bulk_downloader()
            elif module_name == "tiktok_video_editor":
                self.show_tiktok_video_editor()
            elif module_name == "settings":
                self.show_settings()
        except Exception as e:
            print(f"Module could not be started: {e}")
    
    def load_settings(self):
        """Load settings"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "theme": "light",
                "language": "tr",
                "auto_start": False,
                "notifications": True
            }
    
    def save_settings(self):
        """Save settings"""
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Settings could not be saved: {e}")
    
    def show_settings(self, e):
        """Ayarlar sayfasını göster"""
        self.settings_visible = True
        self.page.clean()
        self.page.padding = 20
        
        # Ayarlar başlığı - tema durumuna göre renk
        title_color = ft.Colors.BLUE_600 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLUE_300
        
        title = ft.Text(
            self.get_text("settings_title"),
            size=28,
            weight=ft.FontWeight.BOLD,
            color=title_color,
            text_align=ft.TextAlign.CENTER
        )
        
        # Tema durumuna göre renk ayarları
        text_color = ft.Colors.BLACK87 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.WHITE
        
        # Tema bilgisi (sadece açık tema)
        theme_info = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.LIGHT_MODE, color=ft.Colors.ORANGE_400),
                ft.Text(self.get_text("theme_light"), size=16, color=text_color)
            ], spacing=10),
            padding=10,
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            width=300
        )
        
        # Dil ayarı
        self.language_dropdown = ft.Dropdown(
            label=self.get_text("language"),
            value=self.settings.get("language", "tr"),
            options=[
                ft.dropdown.Option("tr", self.get_text("language_turkish")),
                ft.dropdown.Option("en", self.get_text("language_english"))
            ],
            width=300,
            on_change=self.on_language_change,
            color=text_color,
            label_style=ft.TextStyle(color=text_color)
        )
        
        # Otomatik başlatma
        self.auto_start_switch = ft.Switch(
            label=self.get_text("auto_start"),
            value=self.settings.get("auto_start", False),
            on_change=self.on_auto_start_change,
            label_style=ft.TextStyle(color=text_color)
        )
        
        # Bildirimler
        self.notifications_switch = ft.Switch(
            label=self.get_text("notifications"),
            value=self.settings.get("notifications", True),
            on_change=self.on_notifications_change,
            label_style=ft.TextStyle(color=text_color)
        )
        
        # Geri butonu
        back_button = ft.ElevatedButton(
            text=self.get_text("back_to_main"),
            icon=ft.Icons.ARROW_BACK,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600
            ),
            on_click=self.back_to_main_menu
        )
        
        # Ayarları sıfırla butonu
        reset_button = ft.ElevatedButton(
            text=self.get_text("reset_settings"),
            icon=ft.Icons.REFRESH,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600
            ),
            on_click=self.reset_settings
        )
        
        # Layout
        content = ft.Column([
            ft.Container(height=30),
            title,
            ft.Container(height=40),
            
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        self.get_text("general_settings"), 
                        size=18, 
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLACK87 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.WHITE70
                    ),
                    ft.Container(height=20),
                    theme_info,
                    ft.Container(height=15),
                    self.language_dropdown,
                    ft.Container(height=20),
                    self.auto_start_switch,
                    ft.Container(height=15),
                    self.notifications_switch
                ]),
                padding=20,
                bgcolor=ft.Colors.GREY_100 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
                border_radius=10
            ),
            
            ft.Container(height=40),
            
            ft.Row([
                back_button,
                reset_button
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            
            ft.Container(height=30)
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO)
        
        self.page.add(content)
        self.page.update()
    
    # Tema değiştirme özelliği kaldırıldı - sadece açık tema
        
    def on_language_change(self, e):
        """Dil değiştirildiğinde"""
        new_language = e.control.value
        self.current_language = new_language
        self.settings["language"] = new_language
        self.save_settings()
        # UI'yi yeniden yükle
        self.show_settings(e)
        
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
            if e.control.text == self.get_text("yes"):
                # Ayarları sıfırla
                self.settings = {
                    "theme": "light",
                    "language": "tr",
                    "auto_start": False,
                    "notifications": True
                }
                self.current_language = "tr"
                self.save_settings()
                
                # UI'yi güncelle
                self.language_dropdown.value = "tr"
                self.auto_start_switch.value = False
                self.notifications_switch.value = True
                
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.current_theme = ft.ThemeMode.LIGHT
                
                # Ayarlar sayfasını yeniden yükle
                self.show_settings(e)
                return
                
            # Dialogu kapat
            dialog.open = False
            self.page.update()
            
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self.get_text("reset_confirm_title")),
            content=ft.Text(self.get_text("reset_confirm_message")),
            actions=[
                ft.TextButton(self.get_text("no"), on_click=confirm_reset),
                ft.TextButton(self.get_text("yes"), on_click=confirm_reset)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def back_to_main_menu(self, e):
        """Go back to main menu"""
        self.settings_visible = False
        self.show_main_menu()
    
    def toggle_theme(self, e):
        """Tema her zaman açık modda kalır"""
        self.current_theme = ft.ThemeMode.LIGHT
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.settings["theme"] = "light"
        self.save_settings()
        self.page.update()
    

        
    def main(self, page: ft.Page):
        page.title = "Social Media Video Downloader"
        page.theme_mode = self.current_theme
        page.window_width = 1920
        page.window_height = 1080
        page.window_resizable = True
        page.window_maximizable = True
        page.window_minimizable = True
        page.window_closable = True
        page.window_title_bar_hidden = False
        page.window_title_bar_buttons_hidden = False
        page.padding = 0
        page.bgcolor = ft.Colors.WHITE
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        
        self.page = page
        
        # Modern splash screen'i göster
        show_splash_screen(page, on_complete_callback=self.transition_to_main_menu, language=self.current_language)
    

    
    def transition_to_main_menu(self):
        """Transition to main menu"""
        # Set window size for main menu
        self.page.window_width = 1920
        self.page.window_height = 1080
        self.page.window_resizable = True
        self.page.window_maximizable = True
        self.page.window_minimizable = True
        self.page.window_closable = True
        self.page.window_title_bar_hidden = False
        self.page.window_title_bar_buttons_hidden = False
        self.page.bgcolor = ft.Colors.WHITE
        self.page.title = self.get_text("main_menu_title")
        
        # Show main menu
        self.show_main_menu()
        

        
    def show_main_menu(self):
        """Show main menu with modern sidebar layout"""
        # Splash screen'i temizle
        self.page.clean()
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.WHITE
        
        # Pencere boyutunu büyüt
        self.page.window_width = 1920
        self.page.window_height = 1080
        
        # Seçili menü indeksi
        self.selected_menu_index = 0
        
        # Navigation Rail oluştur
        self.nav_rail = ft.Container(
            content=ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=150,
                min_extended_width=300,
                extended=True,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=ft.Icons.HOME,
                        selected_icon=ft.Icons.HOME,
                        label=self.get_text("nav_home")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.VIDEO_LIBRARY,
                        selected_icon=ft.Icons.VIDEO_LIBRARY,
                        label=self.get_text("nav_tiktok_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.PLAY_CIRCLE,
                        selected_icon=ft.Icons.PLAY_CIRCLE,
                        label=self.get_text("nav_youtube_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.CAMERA_ALT,
                        selected_icon=ft.Icons.CAMERA_ALT,
                        label=self.get_text("nav_instagram_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.FACEBOOK,
                        selected_icon=ft.Icons.FACEBOOK,
                        label=self.get_text("nav_facebook_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.PUSH_PIN,
                        selected_icon=ft.Icons.PUSH_PIN,
                        label=self.get_text("nav_pinterest_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.ALTERNATE_EMAIL,
                        selected_icon=ft.Icons.ALTERNATE_EMAIL,
                        label=self.get_text("nav_twitter_single")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                        selected_icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                        label=self.get_text("nav_tiktok_bulk")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.PLAYLIST_PLAY,
                        selected_icon=ft.Icons.PLAYLIST_PLAY,
                        label=self.get_text("nav_youtube_bulk")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.PHOTO_LIBRARY,
                        selected_icon=ft.Icons.PHOTO_LIBRARY,
                        label=self.get_text("nav_instagram_bulk")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.COLLECTIONS,
                        selected_icon=ft.Icons.COLLECTIONS,
                        label=self.get_text("nav_pinterest_bulk")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                        selected_icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                        label=self.get_text("nav_twitter_bulk")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.VIDEO_SETTINGS,
                        selected_icon=ft.Icons.VIDEO_SETTINGS,
                        label=self.get_text("nav_video_editor")
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.Icons.SETTINGS,
                        selected_icon=ft.Icons.SETTINGS,
                        label=self.get_text("nav_settings")
                    ),
                ],
                on_change=self.nav_rail_change,
                bgcolor=ft.Colors.WHITE,
            ),
            bgcolor=ft.Colors.WHITE,
            height=self.page.window_height - 40,
            width=300
        )
        
        # Ana içerik alanı
        self.main_content = ft.Container(
            content=self.get_home_content(),
            expand=True,
            padding=30,
            bgcolor=ft.Colors.WHITE,
        )
        
        # Ana layout - Row ile sidebar ve content
        main_layout = ft.Container(
            content=ft.Row(
                [
                    self.nav_rail,
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                    self.main_content
                ],
                expand=True,
                spacing=0
            ),
            bgcolor=ft.Colors.WHITE,
            expand=True
        )
        
        self.page.add(main_layout)
        self.page.update()
    
    def change_tab(self, tab_index):
        """Sekme değiştir - hızlı başlangıç için"""
        self.selected_menu_index = tab_index
        # NavigationRail'in selected_index'ini güncelle
        self.nav_rail.content.selected_index = tab_index
        
        # İçeriği güncelle
        if self.selected_menu_index == 0:
            self.main_content.content = self.get_home_content()
        elif self.selected_menu_index == 1:
            self.main_content.content = self.get_tiktok_single_content()
        elif self.selected_menu_index == 2:
            self.main_content.content = self.get_youtube_single_content()
        elif self.selected_menu_index == 3:
            self.main_content.content = self.get_instagram_single_content()
        elif self.selected_menu_index == 4:
            self.main_content.content = self.get_facebook_single_content()
        elif self.selected_menu_index == 5:
            self.main_content.content = self.get_pinterest_single_content()
        elif self.selected_menu_index == 6:
            self.main_content.content = self.get_twitter_single_content()
        elif self.selected_menu_index == 7:
            self.main_content.content = self.get_tiktok_bulk_content()
        elif self.selected_menu_index == 8:
            self.main_content.content = self.get_youtube_bulk_content()
        elif self.selected_menu_index == 9:
            self.main_content.content = self.get_instagram_bulk_content()
        elif self.selected_menu_index == 10:
            self.main_content.content = self.get_pinterest_bulk_content()
        elif self.selected_menu_index == 11:
            self.main_content.content = self.get_twitter_bulk_content()
        elif self.selected_menu_index == 12:
            self.main_content.content = self.get_video_editor_content()
        elif self.selected_menu_index == 13:
            self.main_content.content = self.get_settings_content()
        
        self.page.update()
    
    def nav_rail_change(self, e):
        """Navigation rail seçimi değiştiğinde çağrılır"""
        self.selected_menu_index = e.control.selected_index
        # NavigationRail'in selected_index'ini güncelle
        self.nav_rail.content.selected_index = e.control.selected_index
        
        # İçeriği güncelle
        if self.selected_menu_index == 0:
            self.main_content.content = self.get_home_content()
        elif self.selected_menu_index == 1:
            self.main_content.content = self.get_tiktok_single_content()
        elif self.selected_menu_index == 2:
            self.main_content.content = self.get_youtube_single_content()
        elif self.selected_menu_index == 3:
            self.main_content.content = self.get_instagram_single_content()
        elif self.selected_menu_index == 4:
            self.main_content.content = self.get_facebook_single_content()
        elif self.selected_menu_index == 5:
            self.main_content.content = self.get_pinterest_single_content()
        elif self.selected_menu_index == 6:
            self.main_content.content = self.get_twitter_single_content()
        elif self.selected_menu_index == 7:
            self.main_content.content = self.get_tiktok_bulk_content()
        elif self.selected_menu_index == 8:
            self.main_content.content = self.get_youtube_bulk_content()
        elif self.selected_menu_index == 9:
            self.main_content.content = self.get_instagram_bulk_content()
        elif self.selected_menu_index == 10:
            self.main_content.content = self.get_pinterest_bulk_content()
        elif self.selected_menu_index == 11:
            self.main_content.content = self.get_twitter_bulk_content()
        elif self.selected_menu_index == 12:
            self.main_content.content = self.get_video_editor_content()
        elif self.selected_menu_index == 13:
            self.main_content.content = self.get_settings_content()
        
        self.page.update()
    
    def get_home_content(self):
        """Ana sayfa içeriğini döndür - Social Media Video Downloader teması"""
        # Ana başlık - tema durumuna göre renk (splash screen ile uyumlu)
        title_color = ft.Colors.BLUE_600 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLUE_300
        subtitle_color = ft.Colors.GREY_600 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_300
        
        return ft.Column(
            [
                # Ana başlık bölümü - splash screen temasına uygun
                ft.Container(
                    content=ft.Column([
                        # Logo ve başlık kombinasyonu
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📱", size=40),
                                ft.Container(width=15),
                                ft.Text(
                                    self.get_text("app_title"),
                                    size=36,
                                    weight=ft.FontWeight.W_900,
                                    color=title_color,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            padding=ft.padding.only(bottom=10)
                        ),
                        ft.Text(
                            self.get_text("supported_platforms"),
                            size=16,
                            weight=ft.FontWeight.W_500,
                            color=subtitle_color,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            self.get_text("app_description"),
                            size=18,
                            color=subtitle_color,
                            text_align=ft.TextAlign.CENTER
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.only(bottom=40)
                ),
                
                # Sosyal medya platformları - splash screen temasına uygun
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            self.get_text("supported_platforms_title"),
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=title_color,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=10),
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "YouTube",
                                        self.get_text("platform_youtube_desc"),
                                        "📺",
                                        ft.Colors.RED_600
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "TikTok",
                                        self.get_text("platform_tiktok_desc"),
                                        "🎵",
                                        ft.Colors.PINK_600
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "Instagram",
                                        self.get_text("platform_instagram_desc"),
                                        "📷",
                                        ft.Colors.PURPLE_600
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "Facebook",
                                        self.get_text("platform_facebook_desc"),
                                        "👥",
                                        ft.Colors.BLUE_700
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "Pinterest",
                                        self.get_text("platform_pinterest_desc"),
                                        "📌",
                                        ft.Colors.RED_500
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        "Twitter",
                                        self.get_text("platform_twitter_desc"),
                                        "🐦",
                                        ft.Colors.LIGHT_BLUE_600
                                    ),
                                    col={"sm": 12, "md": 6, "lg": 4}
                                ),
                                ft.Container(
                                    content=self.create_social_media_card(
                                        self.get_text("platform_more"),
                                        self.get_text("platform_more_desc"),
                                        "🌐",
                                        ft.Colors.TEAL_600
                                    ),
                                    col={"sm": 12, "md": 12, "lg": 4}
                                ),
                            ],
                            spacing=10,
                            run_spacing=10
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=25)
                ),
                
                ft.Container(height=50),
                
                # Hızlı eylemler - modern tasarım
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            self.get_text("quick_start"),
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=title_color,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=20),
                        ft.Row([
                            ft.Container(
                                content=ft.ElevatedButton(
                                    text=self.get_text("download_video"),
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.BLUE_600,
                                        color=ft.Colors.WHITE,
                                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                                        padding=ft.padding.symmetric(horizontal=30, vertical=15)
                                    ),
                                    on_click=lambda _: self.change_tab(1)
                                ),
                                expand=True
                            ),
                            ft.Container(width=15),
                            ft.Container(
                                content=ft.ElevatedButton(
                                    text=self.get_text("exit_app"),
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.RED_600,
                                        color=ft.Colors.WHITE,
                                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                                        padding=ft.padding.symmetric(horizontal=30, vertical=15)
                                    ),
                                    on_click=self.exit_app
                                ),
                                expand=True
                            ),
                        ], spacing=0)
                    ]),
                    padding=30,
                    border_radius=15,
                    bgcolor=ft.Colors.BLUE_50 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLUE_900,
                    border=ft.border.all(2, ft.Colors.BLUE_200 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLUE_700),
                    shadow=ft.BoxShadow(
                        spread_radius=2,
                        blur_radius=15,
                        color=ft.Colors.BLUE_200 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLUE_800,
                    ),
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def create_social_media_card(self, title, description, emoji, color):
        """Sosyal medya platform kartı oluştur - splash screen temasına uygun"""
        return ft.Container(
            content=ft.Column([
                # Platform ikonu - splash screen stilinde
                ft.Container(
                    content=ft.Text(emoji, size=50),
                    width=80,
                    height=80,
                    border_radius=40,
                    bgcolor=ft.Colors.GREY_100 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_800,
                    border=ft.border.all(2, ft.Colors.GREY_300 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_600),
                    alignment=ft.alignment.center,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=8,
                        color=ft.Colors.GREY_300 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_700,
                    ),
                ),
                ft.Container(height=20),
                ft.Text(
                    title,
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    color=color
                ),
                ft.Container(height=15),
                ft.Text(
                    description,
                    size=16,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_600 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_400,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            height=280,
            padding=20,
            border_radius=15,
            bgcolor=ft.Colors.WHITE if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_900,
            border=ft.border.all(1, ft.Colors.GREY_200 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.GREY_700),
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=10,
                color=ft.Colors.GREY_200 if self.current_theme == ft.ThemeMode.LIGHT else ft.Colors.BLACK26,
            ),
            expand=True
        )
    
    def create_feature_card(self, title, description, icon, color):
        """Özellik kartı oluştur - eski versiyon uyumluluğu için"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=70, color=color),
                ft.Container(height=10),
                ft.Text(
                    title,
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                ft.Text(
                    description,
                    size=18,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_600
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            height=250,
            padding=30,
            border_radius=15,
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(1, ft.Colors.GREY_300),
            expand=True
        )
    
    def get_tiktok_single_content(self):
        """TikTok hızlı indirme içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("tiktok_single_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PINK_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("tiktok_single_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("tiktok_single_content_button"),
                    icon=ft.Icons.VIDEO_LIBRARY,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PINK_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("tiktok_single_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_youtube_single_content(self):
        """YouTube video çekici içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("youtube_single_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("youtube_single_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("youtube_single_content_button"),
                    icon=ft.Icons.PLAY_CIRCLE,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("youtube_single_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_tiktok_bulk_content(self):
        """TikTok toplu arşivleme içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("tiktok_bulk_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PURPLE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("tiktok_bulk_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("tiktok_bulk_content_button"),
                    icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PURPLE_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("tiktok_bulk_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_youtube_bulk_content(self):
        """YouTube playlist indirici içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("youtube_bulk_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ORANGE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("youtube_bulk_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("youtube_bulk_content_button"),
                    icon=ft.Icons.PLAYLIST_PLAY,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.ORANGE_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("youtube_bulk_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_instagram_single_content(self):
        """Instagram medya indirici içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("instagram_single_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PURPLE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("instagram_single_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("instagram_single_content_button"),
                    icon=ft.Icons.CAMERA_ALT,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PURPLE_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("instagram_single_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_instagram_bulk_content(self):
        """Instagram galeri yedekleme içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("instagram_bulk_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PINK_400
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("instagram_bulk_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("instagram_bulk_content_button"),
                    icon=ft.Icons.PHOTO_LIBRARY,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PINK_400,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("instagram_bulk_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_facebook_single_content(self):
        """Facebook video alıcı içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("facebook_single_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("facebook_single_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("facebook_single_content_button"),
                    icon=ft.Icons.FACEBOOK,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("facebook_single_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    

    
    def get_twitter_single_content(self):
        """Twitter medya çekici içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("twitter_single_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.LIGHT_BLUE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("twitter_single_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("twitter_single_content_button"),
                    icon=ft.Icons.ALTERNATE_EMAIL,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.LIGHT_BLUE_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("twitter_single_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_twitter_bulk_content(self):
        """Twitter medya arşivleme içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("twitter_bulk_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.CYAN_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("twitter_bulk_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("twitter_bulk_content_button"),
                    icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.CYAN_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("twitter_bulk_downloader.py")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_video_editor_content(self):
        """Video editör içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("video_editor_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.TEAL_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("video_editor_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text=self.get_text("video_editor_content_button"),
                    icon=ft.Icons.VIDEO_SETTINGS,
                    width=300,
                    height=60,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.TEAL_600,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                    ),
                    on_click=lambda _: self.launch_module("tiktok_video_editor")
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def get_settings_content(self):
        """Ayarlar içeriği"""
        return ft.Column(
            [
                ft.Text(
                    self.get_text("settings_content_title"),
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_600
                ),
                ft.Container(height=20),
                ft.Text(
                    self.get_text("settings_content_desc"),
                    size=16,
                    color=ft.Colors.GREY_600
                ),
                ft.Container(height=30),
                ft.Row([
                    ft.ElevatedButton(
                        text=self.get_text("settings_content_button1"),
                        icon=ft.Icons.SETTINGS,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE
                        ),
                        on_click=self.show_settings
                    ),
                    ft.ElevatedButton(
                        text=self.get_text("settings_content_button2"),
                        icon=ft.Icons.PALETTE,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_600,
                            color=ft.Colors.WHITE
                        ),
                        on_click=self.toggle_theme
                    ),
                ], spacing=20)
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    def exit_app(self, e):
        """Uygulamadan çık"""
        import threading
        import time
        
        def delayed_exit():
            time.sleep(0.1)  # Kısa bir gecikme
            try:
                self.page.window.close()
            except:
                import os
                os._exit(0)
        
        # Arka planda hızlı çıkış
        threading.Thread(target=delayed_exit, daemon=True).start()
    
    def show_back_button(self):
        """Show back to main menu button"""
        back_button = ft.ElevatedButton(
            text="Back to Main Menu",
            icon=ft.Icons.ARROW_BACK,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600
            ),
            on_click=self.back_to_main_menu
        )
        return back_button
    
    def show_tiktok_single_downloader(self):
        """Show TikTok single video downloader page - using TikTokSingleDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start TikTokSingleDownloaderApp class
            tiktok_single_app = TikTokSingleDownloaderApp()
            tiktok_single_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"TikTok tekli indirici başlatılamadı: {e}")
            
            # Hata durumunda basit bir hata mesajı göster
            self.page.clean()
            self.page.padding = 20
            
            error_message = ft.Text(
                f"TikTok tekli indirici başlatılamadı: {e}",
                size=16,
                color=ft.Colors.RED_600,
                text_align=ft.TextAlign.CENTER
            )
            
            content = ft.Column([
                ft.Container(height=30),
                error_message,
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(content)
            self.page.update()
    
    def show_youtube_single_downloader(self):
        """Show YouTube single video downloader page - using YouTubeSingleDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start YouTubeSingleDownloaderApp class
            youtube_single_app = YouTubeSingleDownloaderApp()
            youtube_single_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"YouTube single downloader could not be started: {e}")
            
            # Show simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "YouTube Single Video Downloader",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_tiktok_bulk_downloader(self):
        """Show TikTok bulk video downloader page - using TikTokBulkDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start TikTokBulkDownloaderApp class
            tiktok_bulk_app = TikTokBulkDownloaderApp()
            tiktok_bulk_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"TikTok bulk downloader could not be started: {e}")
            
            # Show simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "TikTok Bulk Video Downloader",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_youtube_bulk_downloader(self):
        """Show YouTube bulk video downloader page - using YouTubeBulkDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start YouTubeBulkDownloaderApp class
            youtube_bulk_app = YouTubeBulkDownloaderApp()
            youtube_bulk_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"YouTube bulk downloader could not be started: {e}")
            
            # Show simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "YouTube Bulk Video Downloader",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ORANGE_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_instagram_single_downloader(self):
        """Show Instagram single video downloader page - using InstagramSingleDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start InstagramSingleDownloaderApp class
            instagram_single_app = InstagramSingleDownloaderApp()
            instagram_single_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Instagram single downloader could not be started: {e}")
            
            # Show simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Instagram Single Video Downloader",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PINK_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_instagram_bulk_downloader(self):
        """Show Instagram bulk video downloader page - using InstagramBulkDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Start InstagramBulkDownloaderApp class
            instagram_bulk_app = InstagramBulkDownloaderApp()
            instagram_bulk_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Instagram bulk downloader could not be started: {e}")
            
            # Show a simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Instagram Toplu Video İndirici",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PINK_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_facebook_single_downloader(self):
        """Show Facebook single video downloader page - using FacebookSingleDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Initialize FacebookSingleDownloaderApp class
            facebook_single_app = FacebookSingleDownloaderApp()
            facebook_single_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Facebook single downloader could not be started: {e}")
            
            # Show a simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Facebook Tekli Video İndirici",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_facebook_bulk_downloader(self):
        """Show Facebook bulk video downloader page - using FacebookBulkDownloaderApp class"""
        try:
            # Clear current page
            self.page.clean()
            
            # Initialize FacebookBulkDownloaderApp class
            facebook_bulk_app = FacebookBulkDownloaderApp()
            facebook_bulk_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Facebook bulk downloader could not be started: {e}")
            
            # Show a simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Facebook Toplu Video İndirici",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_twitter_single_downloader(self):
        """Show Twitter single video downloader page"""
        try:
            # Clear current page
            self.page.clean()
            self.page.padding = 0
            
            # Start Twitter Single Downloader application
            twitter_app = TwitterSingleDownloaderApp()
            twitter_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Twitter Single Downloader could not be started: {e}")
            # Return to main menu in case of error
            self.show_main_menu()
    
    def show_twitter_bulk_downloader(self):
        """Show Twitter bulk video downloader page"""
        try:
            # Clear current page
            self.page.clean()
            self.page.padding = 0
            
            # Start Twitter Bulk Downloader application
            twitter_app = TwitterBulkDownloaderApp()
            twitter_app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Twitter Bulk Downloader could not be started: {e}")
            # Return to main menu in case of error
            self.show_main_menu()
    
    def download_tiktok_video(self, url):
        """Download TikTok video"""
        if not url:
            self.show_message("Please enter a valid URL!")
            return
        
        # Real download process will be done here
        self.show_message(f"TikTok video downloading: {url}")
    
    def download_youtube_video(self, url):
        """Download YouTube video"""
        if not url:
            self.show_message("Please enter a valid URL!")
            return
        
        # Real download process will be done here
        self.show_message(f"YouTube video downloading: {url}")
    
    def download_tiktok_bulk(self, urls):
        """Download TikTok bulk videos"""
        if not urls:
            self.show_message("Please enter valid URLs!")
            return
        
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        if not url_list:
            self.show_message("Please enter valid URLs!")
            return
        
        # Real download process will be done here
        self.show_message(f"{len(url_list)} TikTok videos downloading...")
    
    def download_youtube_bulk(self, urls):
        """Download YouTube bulk shorts"""
        if not urls:
            self.show_message("Please enter valid URLs!")
            return
        
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        if not url_list:
            self.show_message("Please enter valid URLs!")
            return
        
        # Real download process will be done here
        self.show_message(f"{len(url_list)} YouTube Shorts downloading...")
    
    def show_message(self, message):
        """Show message"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Information"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda _: self.close_dialog())
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def add_log(self, message):
        """Add log message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'log_text'):
            self.log_text.value = (self.log_text.value or "") + log_message
            self.log_text.visible = True
            self.log_text.update()
            self.page.update()
    
    def get_random_music(self, music_folder):
        """Select random music from music folder"""
        import random
        import glob
        
        if not music_folder or not os.path.exists(music_folder):
            return None
        
        # Supported music formats
        music_extensions = ['*.mp3', '*.wav', '*.aac', '*.m4a', '*.ogg', '*.flac']
        music_files = []
        
        for ext in music_extensions:
            music_files.extend(glob.glob(os.path.join(music_folder, ext)))
            music_files.extend(glob.glob(os.path.join(music_folder, ext.upper())))
        
        if music_files:
            selected_music = random.choice(music_files)
            self.add_log(f"Random music selected: {os.path.basename(selected_music)}")
            return selected_music
        else:
            self.add_log(f"No supported files found in music folder: {music_folder}")
            return None
    
    def close_dialog(self):
        """Close dialog"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def show_tiktok_video_editor(self):
        """Show TikTok Video Downloader and Editor page"""
        self.page.clean()
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        
        title = ft.Text(
            "TikTok Video Downloader and Editor",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.TEAL_600,
            text_align=ft.TextAlign.CENTER
        )
        
        # Arama kelimesi girişi
        self.search_field = ft.TextField(
            label="Arama Kelimesi",
            hint_text="Örnek: funny cats, dance, music",
            width=400,
            multiline=False
        )
        
        # Video sayısı girişi
        self.video_count_field = ft.TextField(
            label="İndirilecek Video Sayısı",
            value="5",
            hint_text="1-50 arası bir sayı girin",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Logo dosyası seçimi
        self.logo_path_field = ft.TextField(
            label="Logo Dosya Yolu (İsteğe Bağlı)",
            hint_text="C:\\path\\to\\logo.png",
            width=400,
            multiline=False
        )
        
        logo_browse_btn = ft.ElevatedButton(
            text="Logo Seç",
            icon=ft.Icons.FOLDER_OPEN,
            width=120,
            height=40,
            on_click=self.pick_logo_file
        )
        
        # Müzik ekleme özelliği açma/kapama
        self.music_enabled_switch = ft.Switch(
            label="Müzik Ekleme Özelliği",
            value=False,
            on_change=self.toggle_music_options
        )
        
        # Müzik dosyası seçimi
        self.music_path_field = ft.TextField(
            label="Müzik Dosya Yolu (İsteğe Bağlı)",
            hint_text="C:\\path\\to\\music.mp3",
            width=400,
            multiline=False,
            visible=False
        )
        
        music_browse_btn = ft.ElevatedButton(
            text="Müzik Seç",
            icon=ft.Icons.FOLDER_OPEN,
            width=120,
            height=40,
            on_click=self.pick_music_file,
            visible=False
        )
        
        self.music_browse_btn = music_browse_btn  # Referansı sakla
        
        # Müzik dosya yolu row'u için referans
        self.music_path_row = ft.Row([
            self.music_path_field,
            self.music_browse_btn
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10, visible=False)
        
        # Output klasörü seçimi
        self.output_path_field = ft.TextField(
            label="Çıktı Klasörü",
            value="output/processed",
            hint_text="C:\\path\\to\\output",
            width=400,
            multiline=False
        )
        
        output_browse_btn = ft.ElevatedButton(
            text="Klasör Seç",
            icon=ft.Icons.FOLDER_OPEN,
            width=120,
            height=40,
            on_click=self.pick_output_folder
        )
        
        # Müzik klasörü seçimi
        self.music_folder_field = ft.TextField(
            label="Müzik Klasörü (Rastgele Seçim İçin)",
            hint_text="C:\\path\\to\\music\\folder",
            width=400,
            multiline=False,
            visible=False
        )
        
        music_folder_btn = ft.ElevatedButton(
            text="Müzik Klasörü Seç",
            icon=ft.Icons.FOLDER_OPEN,
            width=150,
            height=40,
            on_click=self.pick_music_folder,
            visible=False
        )
        
        self.music_folder_btn = music_folder_btn  # Referansı sakla
        
        # Müzik klasörü row'u için referans
        self.music_folder_row = ft.Row([
            self.music_folder_field,
            self.music_folder_btn
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10, visible=False)
        
        # Ses seviyesi ayarları
        self.music_volume_text = ft.Text(
            f"Müzik Ses Seviyesi: 50%",
            size=14,
            color=ft.Colors.BLACK,
            visible=False
        )
        
        self.music_volume_slider = ft.Slider(
            min=0,
            max=100,
            value=50,
            width=300,
            visible=False,
            on_change=self.update_music_volume_text
        )
        
        self.original_volume_text = ft.Text(
            f"Video Ses Seviyesi: 30%",
            size=14,
            color=ft.Colors.BLACK,
            visible=False
        )
        
        self.original_volume_slider = ft.Slider(
            min=0,
            max=100,
            value=30,
            width=300,
            visible=False,
            on_change=self.update_original_volume_text
        )
        
        # Müzik ayarları başlığı
        self.music_settings_title = ft.Text(
            "Müzik Ayarları", 
            size=16, 
            weight=ft.FontWeight.BOLD,
            visible=False
        )
        
        # Müzik ayarları için Container'lar
        self.music_container_1 = ft.Container(height=10, visible=False)
        self.music_container_2 = ft.Container(height=10, visible=False)
        self.music_container_3 = ft.Container(height=10, visible=False)
        self.music_container_4 = ft.Container(height=5, visible=False)
        
        # İşlem butonları
        search_download_btn = ft.ElevatedButton(
            text="Ara ve İndir",
            icon=ft.Icons.SEARCH,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600
            ),
            on_click=self.search_and_download_videos
        )
        
        # Videoları Düzenle butonu kaldırıldı
        
        # İlerleme göstergesi
        self.progress_bar = ft.ProgressBar(
            width=400,
            visible=False
        )
        
        self.progress_text = ft.Text(
            "",
            size=14,
            text_align=ft.TextAlign.CENTER,
            visible=False
        )
        
        # Sonuç listesi
        self.result_list = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            height=200,
            visible=False
        )
        
        # Loglar bölümü
        self.log_text = ft.TextField(
            label="İşlem Logları",
            multiline=True,
            read_only=True,
            width=600,
            height=150,
            visible=False
        )
        
        content = ft.Column([
            ft.Container(height=20),
            title,
            ft.Container(height=30),
            
            # Arama bölümü
            ft.Text("1. Video Arama", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            self.search_field,
            ft.Container(height=10),
            self.video_count_field,
            ft.Container(height=20),
            
            # Dosya seçimi bölümü
            ft.Text("2. Düzenleme Ayarları (İsteğe Bağlı)", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Row([
                self.logo_path_field,
                logo_browse_btn
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Container(height=10),
            ft.Row([
                self.output_path_field,
                output_browse_btn
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Container(height=20),
            
            # Müzik ekleme özelliği switch
            self.music_enabled_switch,
            ft.Container(height=10),
            
            # Müzik ayarları (başlangıçta gizli)
            self.music_settings_title,
            self.music_container_1,
            self.music_path_row,
            self.music_container_2,
            self.music_folder_row,
            self.music_container_3,
            self.music_volume_text,
            self.music_volume_slider,
            self.music_container_4,
            self.original_volume_text,
            self.original_volume_slider,
            ft.Container(height=20),
            
            # İşlem butonu
            ft.Text("3. İşlem", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            search_download_btn,
            
            ft.Container(height=20),
            
            # İlerleme göstergesi
            self.progress_bar,
            self.progress_text,
            
            ft.Container(height=10),
            
            # Sonuç listesi
            self.result_list,
            
            ft.Container(height=10),
            
            # Loglar bölümü
            self.log_text,
            
            ft.Container(height=30),
            self.show_back_button()
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        
        self.page.add(content)
        self.page.update()
    
    def pick_logo_file(self, e):
        """Logo dosyası seç"""
        def pick_files_result(e: ft.FilePickerResultEvent):
            if e.files:
                self.logo_path_field.value = e.files[0].path
                self.logo_path_field.update()
        
        file_picker = ft.FilePicker(on_result=pick_files_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.pick_files(
            dialog_title="Logo Dosyası Seçin",
            allowed_extensions=["png", "jpg", "jpeg", "gif", "bmp"]
        )
    
    def pick_music_file(self, e):
        """Müzik dosyası seç"""
        def pick_files_result(e: ft.FilePickerResultEvent):
            if e.files:
                self.music_path_field.value = e.files[0].path
                self.music_path_field.update()
        
        file_picker = ft.FilePicker(on_result=pick_files_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.pick_files(
            dialog_title="Müzik Dosyası Seçin",
            allowed_extensions=["mp3", "wav", "aac", "m4a", "ogg"]
        )
    
    def pick_output_folder(self, e):
        """Çıktı klasörü seç"""
        def pick_directory_result(e: ft.FilePickerResultEvent):
            if e.path:
                self.output_path_field.value = e.path
                self.output_path_field.update()
        
        file_picker = ft.FilePicker(on_result=pick_directory_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.get_directory_path(
            dialog_title="Çıktı Klasörü Seçin"
        )
    
    def pick_music_folder(self, e):
        """Müzik klasörü seç"""
        def pick_directory_result(e: ft.FilePickerResultEvent):
            if e.path:
                self.music_folder_field.value = e.path
                self.music_folder_field.update()
        
        file_picker = ft.FilePicker(on_result=pick_directory_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.get_directory_path(
            dialog_title="Müzik Klasörü Seçin"
        )
    
    def update_music_volume_text(self, e):
        """Müzik ses seviyesi text'ini güncelle"""
        self.music_volume_text.value = f"Müzik Ses Seviyesi: {int(e.control.value)}%"
        self.music_volume_text.update()
    
    def update_original_volume_text(self, e):
        """Video ses seviyesi text'ini güncelle"""
        self.original_volume_text.value = f"Video Ses Seviyesi: {int(e.control.value)}%"
        self.original_volume_text.update()
    
    def toggle_music_options(self, e):
        """Müzik ekleme özelliklerini açıp kapat"""
        is_enabled = e.control.value
        print(f"DEBUG: Müzik toggle çağrıldı, is_enabled: {is_enabled}")
        
        # Müzik ile ilgili tüm alanları göster/gizle
        self.music_settings_title.visible = is_enabled
        self.music_container_1.visible = is_enabled
        self.music_path_row.visible = is_enabled
        self.music_container_2.visible = is_enabled
        self.music_folder_row.visible = is_enabled
        self.music_container_3.visible = is_enabled
        self.music_volume_text.visible = is_enabled
        self.music_volume_slider.visible = is_enabled
        self.music_container_4.visible = is_enabled
        self.original_volume_text.visible = is_enabled
        self.original_volume_slider.visible = is_enabled
        
        # Row içindeki bileşenlerin de visible özelliklerini güncelle
        self.music_path_field.visible = is_enabled
        self.music_browse_btn.visible = is_enabled
        self.music_folder_field.visible = is_enabled
        self.music_folder_btn.visible = is_enabled
        
        print(f"DEBUG: music_path_row.visible = {self.music_path_row.visible}")
        print(f"DEBUG: music_folder_row.visible = {self.music_folder_row.visible}")
        print(f"DEBUG: music_path_field.visible = {self.music_path_field.visible}")
        print(f"DEBUG: music_folder_field.visible = {self.music_folder_field.visible}")
        
        # Sayfayı güncelle
        self.page.update()
    
    def get_random_music(self, music_folder):
        """Müzik klasöründen rastgele bir müzik dosyası seç"""
        import random
        
        if not music_folder or not os.path.exists(music_folder):
            return None
        
        # Desteklenen müzik formatları
        music_extensions = ['.mp3', '.wav', '.aac', '.m4a', '.ogg', '.flac']
        
        try:
            # Klasördeki tüm müzik dosyalarını bul
            music_files = []
            for file in os.listdir(music_folder):
                if any(file.lower().endswith(ext) for ext in music_extensions):
                    music_files.append(os.path.join(music_folder, file))
            
            if music_files:
                selected_music = random.choice(music_files)
                self.add_log(f"Rastgele seçilen müzik: {os.path.basename(selected_music)}")
                return selected_music
            else:
                self.add_log("Müzik klasöründe desteklenen müzik dosyası bulunamadı")
                return None
                
        except Exception as e:
            self.add_log(f"Müzik seçimi hatası: {str(e)}")
            return None
    
    def show_file_dialog(self, title, target_field):
        """Dosya yolu girişi için dialog göster"""
        def on_file_path_submit(e):
            if file_path_input.value:
                target_field.value = file_path_input.value
                target_field.update()
            dialog.open = False
            self.page.update()
        
        file_path_input = ft.TextField(
            label="Dosya Yolu",
            width=400,
            autofocus=True
        )
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Column([
                file_path_input,
                ft.Text("Örnek: C:\\Users\\Username\\Desktop\\file.png", size=12, color=ft.Colors.GREY_600)
            ], height=100),
            actions=[
                ft.TextButton("İptal", on_click=lambda _: self.close_dialog()),
                ft.TextButton("Tamam", on_click=on_file_path_submit)
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def search_and_download_videos(self, e):
        """TikTok'ta video ara ve indir"""
        search_query = self.search_field.value
        if not search_query:
            self.show_message("Lütfen arama kelimesi girin!")
            return
        
        try:
            video_count = int(self.video_count_field.value)
            if video_count < 1 or video_count > 50:
                self.show_message("Video sayısı 1-50 arasında olmalıdır!")
                return
        except ValueError:
            self.show_message("Geçerli bir video sayısı girin!")
            return
        
        # İlerleme göstergelerini göster
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_text.value = "TikTok'ta videolar aranıyor..."
        self.page.update()
        
        # Arka planda arama ve indirme işlemini başlat
        threading.Thread(target=self._search_and_download_worker, args=(search_query, video_count)).start()
    
    def _search_and_download_worker(self, search_query, video_count):
        """Arka planda video arama ve indirme işlemi"""
        try:
            self.add_log(f"Video arama başlatıldı: '{search_query}' - {video_count} video")
            
            # TikTok scraper'ı başlat
            scraper = TikTokScraper(log_callback=self.add_log)
            
            # Output klasörünü oluştur
            output_folder = "output"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            
            # Videoları ara
            self.progress_text.value = f"'{search_query}' için videolar aranıyor..."
            self.add_log(f"TikTok'ta video arama yapılıyor...")
            self.page.update()
            
            video_urls = scraper.search_videos(search_query, video_count)
            
            if not video_urls:
                self.progress_text.value = "Video bulunamadı!"
                self.add_log("Arama sonucunda video bulunamadı")
                self.progress_bar.visible = False
                self.page.update()
                return
            
            self.add_log(f"{len(video_urls)} video bulundu, indirme başlıyor...")
            
            # Videoları indir
            downloaded_files = []
            for i, url in enumerate(video_urls):
                self.progress_text.value = f"Video {i+1}/{len(video_urls)} indiriliyor..."
                self.progress_bar.value = (i + 1) / len(video_urls)
                self.page.update()
                
                downloaded_file = scraper.download_video(url, output_folder)
                if downloaded_file:
                    downloaded_files.append(downloaded_file)
                    
                    # Video indirildikten sonra hemen düzenle
                    logo_path = self.logo_path_field.value if self.logo_path_field.value else None
                    
                    # Müzik seçimi (sadece switch açıksa)
                    music_path = None
                    if self.music_enabled_switch.value:
                        if self.music_path_field.value:
                            music_path = self.music_path_field.value
                            self.add_log(f"Belirtilen müzik dosyası kullanılacak: {os.path.basename(music_path)}")
                        elif self.music_folder_field.value:
                            music_path = self.get_random_music(self.music_folder_field.value)
                    else:
                        self.add_log("Müzik ekleme devre dışı")
                    
                    music_volume = self.music_volume_slider.value / 100.0
                    original_volume = self.original_volume_slider.value / 100.0
                    
                    # Processed klasörünü oluştur
                    processed_folder = "output/processed"
                    if not os.path.exists(processed_folder):
                        os.makedirs(processed_folder)
                    
                    filename = os.path.basename(downloaded_file)
                    output_file = os.path.join(processed_folder, f"processed_{filename}")
                    
                    # Video işleme
                    processor = VideoProcessor(log_callback=self.add_log)
                    success = processor.process_video(
                        downloaded_file, 
                        output_file, 
                        logo_path, 
                        music_path,
                        music_volume,
                        original_volume
                    )
                    
                    if success:
                        # Orijinal dosyayı sil, işlenmiş dosyayı sakla
                        try:
                            os.remove(downloaded_file)
                            downloaded_files[-1] = output_file  # Listeyi güncelle
                        except:
                            pass
            
            # Sonuçları göster
            self.progress_bar.visible = False
            self.progress_text.value = f"{len(downloaded_files)} video başarıyla indirildi!"
            
            # Sonuç listesini güncelle
            self.result_list.controls.clear()
            self.result_list.controls.append(ft.Text("İndirilen Videolar:", weight=ft.FontWeight.BOLD))
            
            for file_path in downloaded_files:
                filename = os.path.basename(file_path)
                self.result_list.controls.append(
                    ft.Text(f"✓ {filename}", size=12, color=ft.Colors.GREEN_600)
                )
            
            self.result_list.visible = True
            self.page.update()
            
        except Exception as e:
            error_msg = f"Video işleme hatası: {str(e)}"
            self.progress_text.value = error_msg
            self.add_log(f"❌ {error_msg}")
            self.progress_bar.visible = False
            self.page.update()
    
    def process_downloaded_videos(self, e):
        """İndirilen videoları düzenle"""
        output_folder = "output"
        if not os.path.exists(output_folder):
            self.show_message("Önce video indirmeniz gerekiyor!")
            return
        
        # Video dosyalarını bul
        video_files = []
        for file in os.listdir(output_folder):
            if file.lower().endswith(('.mp4', '.webm', '.mkv', '.avi')):
                video_files.append(os.path.join(output_folder, file))
        
        if not video_files:
            self.show_message("İşlenecek video dosyası bulunamadı!")
            return
        
        logo_path = self.logo_path_field.value if self.logo_path_field.value else None
        
        # Müzik seçimi (sadece switch açıksa)
        music_path = None
        if self.music_enabled_switch.value:
            if self.music_path_field.value:
                music_path = self.music_path_field.value
            elif self.music_folder_field.value:
                music_path = self.get_random_music(self.music_folder_field.value)
        
        # İlerleme göstergelerini göster
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_text.value = "Videolar düzenleniyor..."
        self.page.update()
        
        # Arka planda düzenleme işlemini başlat
        threading.Thread(target=self._process_videos_worker, args=(video_files, logo_path, music_path)).start()
    
    def _process_videos_worker(self, video_files, logo_path, music_path):
        """Arka planda video düzenleme işlemi"""
        try:
            self.add_log(f"Video işleme başlatıldı: {len(video_files)} dosya")
            processor = VideoProcessor(log_callback=self.add_log)
            
            # Seçilen output klasörünü kullan
            processed_folder = self.output_path_field.value if self.output_path_field.value else "output/processed"
            if not os.path.exists(processed_folder):
                os.makedirs(processed_folder)
            
            self.add_log(f"Çıktı klasörü: {processed_folder}")
            if logo_path:
                self.add_log(f"Logo eklenecek: {os.path.basename(logo_path)}")
            if music_path:
                self.add_log(f"Müzik eklenecek: {os.path.basename(music_path)}")
            
            processed_files = []
            
            for i, video_file in enumerate(video_files):
                filename = os.path.basename(video_file)
                output_file = os.path.join(processed_folder, f"processed_{filename}")
                
                self.progress_text.value = f"Video {i+1}/{len(video_files)} düzenleniyor: {filename}"
                self.progress_bar.value = (i + 1) / len(video_files)
                self.page.update()
                
                # Ses seviyesi ayarlarını al
                music_volume = self.music_volume_slider.value / 100.0  # 0-1 arası değere çevir
                original_volume = self.original_volume_slider.value / 100.0  # 0-1 arası değere çevir
                
                self.add_log(f"İşleniyor: {filename}")
                success = processor.process_video(video_file, output_file, logo_path, music_path, music_volume, original_volume)
                if success:
                    processed_files.append(output_file)
                    self.add_log(f"✓ Başarıyla işlendi: {filename}")
                    # Orijinal dosyayı sil
                    try:
                        os.remove(video_file)
                        self.add_log(f"Orijinal dosya silindi: {filename}")
                    except:
                        self.add_log(f"Orijinal dosya silinemedi: {filename}")
                else:
                    self.add_log(f"✗ İşleme başarısız: {filename}")
            
            # Sonuçları göster
            if processed_files:
                self.progress_text.value = f"✅ {len(processed_files)} video başarıyla işlendi!"
                self.add_log(f"🎉 İşlem tamamlandı! {len(processed_files)} video başarıyla işlendi")
            else:
                self.progress_text.value = "❌ Hiçbir video işlenemedi!"
                self.add_log("❌ İşlem tamamlandı ancak hiçbir video işlenemedi")
            
            self.progress_bar.visible = False
            
            # Sonuç listesini güncelle
            self.result_list.controls.clear()
            self.result_list.controls.append(ft.Text("Düzenlenen Videolar:", weight=ft.FontWeight.BOLD))
            
            for file_path in processed_files:
                filename = os.path.basename(file_path)
                self.result_list.controls.append(
                    ft.Text(f"✓ {filename}", size=12, color=ft.Colors.BLUE_600)
                )
            
            self.result_list.visible = True
            self.page.update()
            
        except Exception as e:
            error_msg = f"Arama/indirme hatası: {str(e)}"
            self.progress_text.value = error_msg
            self.add_log(f"❌ {error_msg}")
            self.progress_bar.visible = False
            self.page.update()
    
    def get_pinterest_single_content(self):
        """Pinterest pin kaydetme içeriği"""
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    "Pinterest Pin Kaydetme",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.ElevatedButton(
                    text="Pinterest Pin Kaydetmeyi Başlat",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_500,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15)
                    ),
                    on_click=lambda _: self.launch_module("pinterest_single_downloader.py")
                ),
                ft.Container(height=20),
                ft.Text(
                    "Pinterest'ten pin kaydetmek için bu modülü kullanın.",
                    size=16,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_600
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30
        )
    
    def get_pinterest_bulk_content(self):
        """Pinterest koleksiyon indirici içeriği"""
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    "Pinterest Koleksiyon İndirici",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.ElevatedButton(
                    text="Pinterest Koleksiyon İndiriciyi Başlat",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_500,
                        color=ft.Colors.WHITE,
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15)
                    ),
                    on_click=lambda _: self.launch_module("pinterest_bulk_downloader.py")
                ),
                ft.Container(height=20),
                ft.Text(
                    "Pinterest'ten koleksiyon indirmek için bu modülü kullanın.",
                    size=16,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_600
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30
        )
    
    def show_pinterest_single_downloader(self):
        """Show Pinterest single pin downloader"""
        try:
            # Clear current page
            self.page.clean()
            
            # Initialize PinterestSingleDownloaderApp class
            app = PinterestSingleDownloaderApp()
            app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Pinterest single downloader could not be started: {e}")
            
            # Show a simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Pinterest Tekli Pin İndirici",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()
    
    def show_pinterest_bulk_downloader(self):
        """Show Pinterest bulk pin downloader"""
        try:
            # Clear current page
            self.page.clean()
            
            # Initialize PinterestBulkDownloaderApp class
            app = PinterestBulkDownloaderApp()
            app.main(self.page)
            
            # Add back to main menu button
            back_button = ft.ElevatedButton(
                text="Back to Main Menu",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda _: self.show_main_menu()
            )
            
            # Add button to the top of the page
            self.page.controls.insert(0, back_button)
            self.page.update()
            
        except Exception as e:
            print(f"Pinterest bulk downloader could not be started: {e}")
            
            # Show a simple error message in case of error
            self.page.clean()
            self.page.padding = 20
            
            error_content = ft.Column([
                ft.Text(
                    "Pinterest Toplu Pin İndirici",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                ft.Text(
                    f"Error: {str(e)}",
                    size=16,
                    color=ft.Colors.RED_400,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=40),
                self.show_back_button()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.add(error_content)
            self.page.update()


def main(page: ft.Page):
    """Ana uygulama fonksiyonu"""
    app = MainMenuApp()
    app.main(page)

if __name__ == "__main__":
    import asyncio
    import sys
    
    # Windows'ta asyncio subprocess sorununu çöz
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        ft.app(target=main, view=ft.AppView.FLET_APP)
    except NotImplementedError:
        # If there are still issues, run in web mode
        print("Windows desktop mode failed, switching to web mode...")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)
