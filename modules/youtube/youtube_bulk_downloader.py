import flet as ft
import os
import sys
import threading
import time
import re

# Ana dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.youtube.youtube_scraper import YouTubeScraper
from modules.youtube.youtube_api_scraper import YouTubeAPIScraper
from video_processor import VideoProcessor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
# asyncio artık gerekli değil - scraper fonksiyonları normal fonksiyonlar
from pathlib import Path
import subprocess
import shutil

class YouTubeBulkDownloaderApp:
    def __init__(self):
        self.scraper = YouTubeScraper(log_callback=self.add_log)
        self.api_scraper = YouTubeAPIScraper()  # API tabanlı scraper
        self.video_processor = VideoProcessor()
        self.is_downloading = False
        self.page = None
        self.youtube_cookies = None  # YouTube hesap cookie'lerini saklamak için
        
        # Kaydedilmiş cookie'leri yükle
        self.load_saved_cookies()
    
    def load_saved_cookies(self):
        """Kaydedilmiş cookie'leri dosyadan yükler"""
        try:
            import json
            # Cookie klasörünü oluştur
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "youtube_cookies.json")
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    self.youtube_cookies = json.load(f)
                print(f"Kaydedilmiş {len(self.youtube_cookies)} adet cookie yüklendi")
            else:
                print("Kaydedilmiş cookie dosyası bulunamadı")
        except Exception as e:
            print(f"Cookie yükleme hatası: {str(e)}")
            self.youtube_cookies = None
        
    def main(self, page: ft.Page):
        page.title = "YouTube Toplu Video İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 800
        page.window_height = 900
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri - Arama alanı kaldırıldı
        
        self.profile_url_field = ft.TextField(
            label="Profil URL'si",
            hint_text="Örn: https://www.youtube.com/c/channelname",
            width=500,
            prefix_icon=ft.Icons.PERSON
        )
        
        # Video türü seçimi - profil modunda görünür
        self.video_type_selection = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="videos", label="Video İndir"),
                ft.Radio(value="shorts", label="Short İndir")
            ]),
            value="videos",
            visible=True
        )
        
        # Video türü container'ı
        self.video_type_container = ft.Container(
            content=ft.Column([
                ft.Text("Video Türü", size=16, weight=ft.FontWeight.BOLD),
                self.video_type_selection
            ]),
            visible=True,  # Başlangıçta görünür
            padding=ft.padding.only(left=10, top=5, bottom=5),
            bgcolor=ft.Colors.GREY_50,
            border_radius=5,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
        
        # İndirme modu seçimi
        self.download_mode = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="profile", label="Profil URL'si ile İndir"),
                ft.Radio(value="playlist", label="Oynatma Listesi İndir"),
                ft.Radio(value="txt_file", label="Youtube Txt Dosyasından Toplu İndir")
            ]),
            value="profile",
            on_change=self.on_download_mode_change
        )
        
        # TXT dosyası seçimi için UI bileşenleri
        self.txt_file_field = ft.TextField(
            label="TXT Dosyası (.txt)",
            hint_text="Her satırda bir video URL'si olan dosya seçin",
            width=500,
            read_only=True,
            visible=False,
            prefix_icon=ft.Icons.TEXT_SNIPPET
        )
        
        # Oynatma listesi URL'si için UI bileşeni
        self.playlist_url_field = ft.TextField(
            label="Oynatma Listesi URL'si",
            hint_text="Örn: https://www.youtube.com/playlist?list=PLxxxxxx",
            width=500,
            visible=False,
            prefix_icon=ft.Icons.PLAYLIST_PLAY
        )
        
        # Başlangıçta TXT dosyası alanını gizle
        self.profile_url_field.visible = True
        
        # Headless mod checkbox'ı - profil modunda görünür
        self.headless_mode_checkbox = ft.Checkbox(
            label="Headless Mod (Tarayıcıyı Gizle)",
            value=True,
            visible=True,
            tooltip="Tarayıcı penceresini gizleyerek daha hızlı çalışır"
        )
        
        # CAPTCHA açıklaması - profil modunda görünür
        self.captcha_warning = ft.Container(
            content=ft.Text(
                "⚠️ Not: CAPTCHA çıkarsa, tarayıcıda manuel olarak çözmeniz gerekmektedir.",
                size=12,
                color=ft.Colors.ORANGE_700,
                italic=True
            ),
            visible=True,
            padding=ft.padding.only(left=10, top=5),
            bgcolor=ft.Colors.ORANGE_50,
            border_radius=5,
            border=ft.border.all(1, ft.Colors.ORANGE_300)
        )
        
        self.use_logo_checkbox = ft.Checkbox(
            label="Logo Ekle",
            value=False,
            on_change=self.on_logo_checkbox_change
        )
        
        # MP3 olarak indirme checkbox'ı
        self.convert_to_mp3_checkbox = ft.Checkbox(
            label="MP3 Olarak İndir (Direkt MP3 formatında indirir)",
            value=False,
            tooltip="Videoları direkt MP3 formatında indirir, daha hızlı ve etkili"
        )
        
        self.logo_file_field = ft.TextField(
            label="Logo Dosyası (.png)",
            width=400,
            read_only=True,
            visible=False
        )
        
        self.output_folder_field = ft.TextField(
            label="Çıktı Klasörü",
            value="output",
            width=400,
            read_only=True
        )
        
        # Paralel indirme grup sayısı ayarı
        self.parallel_batch_size_field = ft.TextField(
            label="Paralel İndirme Grup Sayısı (1-50)",
            value="10",
            width=200,
            hint_text="Varsayılan: 10",
            prefix_icon=ft.Icons.SPEED,
            tooltip="Aynı anda kaç video indirileceğini belirler. Yüksek değerler daha hızlı ama daha fazla kaynak kullanır."
        )
        
        # Ses seviyesi kontrolleri kaldırıldı
        
        # Dosya seçici butonları
        logo_file_picker = ft.FilePicker(
            on_result=self.on_logo_file_selected
        )
        
        output_folder_picker = ft.FilePicker(
            on_result=self.on_output_folder_selected
        )
        
        txt_file_picker = ft.FilePicker(
            on_result=self.on_txt_file_selected
        )
        
        page.overlay.extend([logo_file_picker, output_folder_picker, txt_file_picker])
        
        # Logo butonunu sınıf değişkeni olarak sakla
        self.logo_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=False
        )
        
        # TXT dosyası seçici butonu
        self.txt_file_button = ft.ElevatedButton(
            "TXT Dosyası Seç",
            icon=ft.Icons.TEXT_SNIPPET,
            on_click=lambda _: txt_file_picker.pick_files(
                allowed_extensions=["txt"]
            ),
            visible=False
        )
        
        # TXT dosyası row'u
        self.txt_file_row = ft.Row([
            self.txt_file_field,
            self.txt_file_button
        ], visible=False)
        
        # Progress bar ve status
        self.progress_bar = ft.ProgressBar(width=600, visible=False)
        self.status_text = ft.Text("Hazır", size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=12, color=ft.Colors.BLACK87, selectable=True, 
                                font_family="Consolas")  # Monospace font ve daha büyük boyut
        
        # Butonlar
        start_button = ft.ElevatedButton(
            text="Toplu İndirmeyi Başlat",
            icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
            on_click=self.start_download,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600
            )
        )
        
        stop_button = ft.ElevatedButton(
            text="Durdur",
            icon=ft.Icons.STOP,
            on_click=self.stop_download,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600
            )
        )
        

        
        # YouTube hesap giriş bölümü için UI bileşenleri
        self.cookie_status_text = ft.Text(
            "YouTube hesabı bağlı değil", 
            size=14, 
            color=ft.Colors.RED_600
        )
        
        login_button = ft.ElevatedButton(
            text="YouTube Hesabına Giriş Yap",
            icon=ft.Icons.LOGIN,
            on_click=self.login_to_youtube,
            width=200,
            height=40,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600
            )
        )
        
        # Giriş işlemi için Tamam ve İptal butonları
        self.login_confirm_button = ft.ElevatedButton(
            text="Tamam",
            icon=ft.Icons.CHECK,
            on_click=lambda e: self.handle_login_action("tamam"),
            width=100,
            height=40,
            visible=False,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600
            )
        )
        
        self.login_cancel_button = ft.ElevatedButton(
            text="İptal",
            icon=ft.Icons.CLOSE,
            on_click=lambda e: self.handle_login_action("iptal"),
            width=100,
            height=40,
            visible=False,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600
            )
        )
        
        # Giriş butonları satırı
        self.login_buttons_row = ft.Row([
            self.login_confirm_button,
            self.login_cancel_button
        ], spacing=10, visible=False)
        
        # Layout
        content = ft.Column([
            ft.Text("YouTube Toplu Video İndirici", 
                   size=24, weight=ft.FontWeight.BOLD, 
                   color=ft.Colors.RED_600),
            ft.Divider(),
            
            # YouTube hesap giriş bölümü
            ft.Text("YouTube Hesap Ayarları", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        "CAPTCHA sorunlarını önlemek için YouTube hesabınıza giriş yapın.",
                        size=14,
                        color=ft.Colors.BLACK87
                    ),
                    ft.Row([
                        login_button,
                        self.cookie_status_text
                    ], spacing=20),
                    self.login_buttons_row
                ]),
                padding=10,
                border_radius=5,
                bgcolor=ft.Colors.BLUE_50,
                border=ft.border.all(1, ft.Colors.BLUE_300)
            ),
            
            ft.Divider(),
            
            # İndirme modu seçimi
            ft.Text("İndirme Modu", size=18, weight=ft.FontWeight.BOLD),
            self.download_mode,
            
            ft.Divider(),
            
            # Profil ve dosya ayarları
            ft.Text("İndirme Ayarları", size=18, weight=ft.FontWeight.BOLD),
            
            self.profile_url_field,
            
            # Oynatma listesi URL'si - sadece playlist modunda görünür
            self.playlist_url_field,
            
            # Video türü seçimi - sadece profil modunda görünür
            self.video_type_container,
            
            # TXT dosyası seçimi
            self.txt_file_row,
            
            # CAPTCHA açıklaması - sadece profil modunda görünür
            self.captcha_warning,
            
            # Headless mod ayarı - sadece profil modunda görünür
            self.headless_mode_checkbox,
            
            ft.Divider(),
            
            # Dosya ayarları
            ft.Text("Dosya Ayarları", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Row([
                self.use_logo_checkbox,
            ]),
            
            ft.Row([
                self.convert_to_mp3_checkbox,
            ]),
            
            ft.Row([
                self.logo_file_field,
                self.logo_button
            ]),
            
            ft.Row([
                self.output_folder_field,
                ft.ElevatedButton(
                    "Seç",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: output_folder_picker.get_directory_path()
                )
            ]),
            
            # Paralel indirme ayarları
            ft.Text("Paralel İndirme Ayarları", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.parallel_batch_size_field,
                ft.Text("(Önerilen: 5-15)", size=12, color=ft.Colors.GREY_600)
            ]),
            
            ft.Divider(),
            
            # Kontrol butonları
            ft.Row([
                start_button,
                stop_button
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Container(height=10),
            
            ft.Divider(),
            
            # Progress ve status
            self.status_text,
            self.progress_bar,
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Log:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton(
                                "Logları Kopyala",
                                icon=ft.Icons.COPY,
                                on_click=self.copy_logs,
                                height=30,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE_600
                                )
                            ),
                            ft.ElevatedButton(
                                "Logları Temizle",
                                icon=ft.Icons.CLEAR,
                                on_click=self.clear_logs,
                                height=30,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.RED_600
                                )
                            )
                        ], spacing=10)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📋 Detaylı Log Kayıtları", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                            ft.Container(
                                content=ft.ListView(
                                    controls=[self.log_text],
                                    auto_scroll=True,
                                    spacing=0,
                                    padding=ft.padding.all(0)
                                ),
                                height=300,  # Yükseklik artırıldı
                                width=800,   # Genişlik artırıldı
                                bgcolor=ft.Colors.GREY_50,
                                padding=15,
                                border_radius=5,
                                border=ft.border.all(2, ft.Colors.BLUE_300)
                            )
                        ], spacing=5),
                        bgcolor=ft.Colors.WHITE,
                        padding=10,
                        border_radius=8,
                        border=ft.border.all(1, ft.Colors.GREY_400)
                    )
                ]),
                height=400,  # Log container yüksekliği artırıldı
                bgcolor=ft.Colors.WHITE,
                padding=10,
                border_radius=5
            )
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        scrollable_content = ft.Container(
            content=content,
            expand=True,
            padding=20
        )
        
        page.add(scrollable_content)
        
        # Cookie durumunu güncelle
        self.update_cookie_status()
    
    def update_cookie_status(self):
        """Cookie durumunu UI'da günceller"""
        if self.youtube_cookies and len(self.youtube_cookies) > 0:
            self.cookie_status_text.value = "YouTube hesabı bağlı ✓"
            self.cookie_status_text.color = ft.Colors.GREEN_600
        else:
            self.cookie_status_text.value = "YouTube hesabı bağlı değil"
            self.cookie_status_text.color = ft.Colors.RED_600
        
        if self.page:
            self.page.update()
    
    def check_ffmpeg_installed(self):
        """FFmpeg'in kurulu olup olmadığını kontrol eder"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def convert_mp4_to_mp3(self, mp4_file_path):
        """MP4 dosyasını MP3'e çevirir ve orijinal MP4 dosyasını siler"""
        try:
            if not os.path.exists(mp4_file_path):
                self.add_log(f"MP4 dosyası bulunamadı: {mp4_file_path}")
                return None
            
            # FFmpeg kontrolü
            if not self.check_ffmpeg_installed():
                self.add_log("⚠️ FFmpeg bulunamadı! MP3 çevirme atlandı.")
                self.add_log("FFmpeg indirmek için: https://ffmpeg.org/download.html")
                return mp4_file_path  # Orijinal MP4 dosyasını döndür
            
            # MP3 dosya yolunu oluştur
            mp3_file_path = mp4_file_path.rsplit('.', 1)[0] + '.mp3'
            
            self.add_log(f"🎵 MP3'e çeviriliyor: {os.path.basename(mp4_file_path)}")
            
            # FFmpeg ile MP3'e çevir
            try:
                # FFmpeg komutunu hazırla
                cmd = [
                    'ffmpeg',
                    '-i', mp4_file_path,
                    '-vn',  # Video stream'ini devre dışı bırak
                    '-acodec', 'mp3',  # Audio codec olarak MP3 kullan
                    '-ab', '192k',  # Audio bitrate
                    '-ar', '44100',  # Audio sample rate
                    '-y',  # Dosya varsa üzerine yaz
                    mp3_file_path
                ]
                
                # FFmpeg'i çalıştır
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    # Başarılı çevirme
                    if os.path.exists(mp3_file_path):
                        # Orijinal MP4 dosyasını sil
                        try:
                            os.remove(mp4_file_path)
                            self.add_log(f"✅ MP3'e çevirme tamamlandı: {os.path.basename(mp3_file_path)}")
                            self.add_log(f"🗑️ Orijinal MP4 dosyası silindi: {os.path.basename(mp4_file_path)}")
                            return mp3_file_path
                        except Exception as delete_error:
                            self.add_log(f"⚠️ MP4 dosyası silinemedi: {str(delete_error)}")
                            return mp3_file_path
                    else:
                        self.add_log(f"❌ MP3 dosyası oluşturulamadı: {mp3_file_path}")
                        return mp4_file_path  # Orijinal dosyayı döndür
                else:
                    self.add_log(f"❌ FFmpeg hatası: {result.stderr}")
                    return mp4_file_path  # Orijinal dosyayı döndür
                    
            except Exception as ffmpeg_error:
                self.add_log(f"❌ FFmpeg çalıştırma hatası: {str(ffmpeg_error)}")
                return mp4_file_path  # Orijinal dosyayı döndür
                
        except Exception as e:
            self.add_log(f"❌ MP3 çevirme hatası: {str(e)}")
            return mp4_file_path  # Orijinal dosyayı döndür
        
    def on_logo_checkbox_change(self, e):
        # Logo alanı ve butonunun görünürlüğünü güncelle
        self.logo_file_field.visible = e.control.value
        self.logo_button.visible = e.control.value
        self.page.update()
        
    def on_download_mode_change(self, e):
        # İndirme moduna göre alanların görünürlüğünü güncelle
        if e.control.value == "profile":
            self.profile_url_field.visible = True
            self.playlist_url_field.visible = False
            self.video_type_container.visible = True
            self.txt_file_row.visible = False
            self.txt_file_field.visible = False
            self.txt_file_button.visible = False
            self.captcha_warning.visible = True
            self.headless_mode_checkbox.visible = True
        elif e.control.value == "playlist":
            self.profile_url_field.visible = False
            self.playlist_url_field.visible = True
            self.video_type_container.visible = False  # Oynatma listesinde video türü seçimi kapalı
            self.txt_file_row.visible = False
            self.txt_file_field.visible = False
            self.txt_file_button.visible = False
            self.captcha_warning.visible = True
            self.headless_mode_checkbox.visible = True
        elif e.control.value == "txt_file":
            self.profile_url_field.visible = False
            self.playlist_url_field.visible = False
            self.video_type_container.visible = False  # TXT dosyası modunda gizle
            self.txt_file_row.visible = True
            self.txt_file_field.visible = True
            self.txt_file_button.visible = True
            self.captcha_warning.visible = False
            self.headless_mode_checkbox.visible = False
        self.page.update()
        
    def setup_selenium(self, for_login=False):
        """Selenium WebDriver'ı ayarla - Anti-bot, CAPTCHA engelleme ve medya optimizasyonu ile"""
        try:
            chrome_options = Options()
            
            # Gelişmiş anti-bot argümanları
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            # CAPTCHA ve popup engelleme
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            # chrome_options.add_argument('--disable-images')  # Resimleri etkinleştir
            # chrome_options.add_argument('--disable-javascript')  # JavaScript'i etkinleştir
            chrome_options.add_argument('--disable-java')
            chrome_options.add_argument('--disable-flash')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer')
            
            # Anti-bot tespiti - Gelişmiş
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-automation')
            chrome_options.add_argument('--disable-extensions-except')
            chrome_options.add_argument('--disable-plugins-discovery')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            
            # Headless mod kontrolü
            if not for_login:
                # Profil modunda headless checkbox'ının değerini kontrol et
                if hasattr(self, 'headless_mode_checkbox') and self.headless_mode_checkbox.value:
                    chrome_options.add_argument('--headless=new')
                    self.add_log("Headless mod etkin - tarayıcı gizli çalışıyor")
                else:
                    self.add_log("Headless mod kapalı - tarayıcı görünür")
            else:
                # Giriş işlemi için headless her zaman kapalı
                pass
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            
            # User agent ayarla - Daha gerçekçi
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
            
            # Pencere boyutu
            chrome_options.add_argument('--window-size=1920,1080')
            
            # WebDriver tespitini engelle
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Gelişmiş prefs ayarları - CAPTCHA ve popup engelleme
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "media_stream": 2,
                    "geolocation": 2,
                    "camera": 2,
                    "microphone": 2,
                    "plugins": 2,
                    "popups": 2,
                    "automatic_downloads": 2,
                    "mixed_script": 2,
                    "media_stream_mic": 2,
                    "media_stream_camera": 2,
                    "protocol_handlers": 2,
                    "ppapi_broker": 2,
                    "midi_sysex": 2,
                    "push_messaging": 2,
                    "ssl_cert_decisions": 2,
                    "metro_switch_to_desktop": 2,
                    "protected_media_identifier": 2,
                    "app_banner": 2,
                    "site_engagement": 2,
                    "durable_storage": 2
                },
                "profile.managed_default_content_settings": {
                    "images": 1,  # Resimleri etkinleştir
                    "javascript": 1,  # JavaScript'i etkinleştir
                    "plugins": 2,
                    "popups": 2,
                    "geolocation": 2,
                    "notifications": 2,
                    "media_stream": 2
                }
                # JavaScript artık genel olarak etkin olduğu için özel ayar gerekmiyor
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # WebDriver oluştur
            driver = webdriver.Chrome(options=chrome_options)
            
            # WebDriver tespitini engelle - Gelişmiş
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            driver.execute_script("Object.defineProperty(navigator, 'permissions', {get: () => undefined})")
            
            # Pencere boyutunu ayarla
            driver.set_window_size(1920, 1080)
            
            # CAPTCHA popup'larını engellemek için ek JavaScript
            driver.execute_script("""
                // Popup'ları engelle
                window.alert = function() {};
                window.confirm = function() { return true; };
                window.prompt = function() { return null; };
                
                // CAPTCHA elementlerini gizle
                const style = document.createElement('style');
                style.textContent = `
                    [class*="captcha"], [id*="captcha"], [class*="recaptcha"], [id*="recaptcha"],
                    [class*="challenge"], [id*="challenge"], [class*="verification"], [id*="verification"],
                    .captcha, .recaptcha, .challenge, .verification {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                        height: 0 !important;
                        width: 0 !important;
                    }
                `;
                document.head.appendChild(style);
            """)
            
            # Eğer cookie'ler varsa ve giriş işlemi için değilse, cookie'leri ekle
            if self.youtube_cookies and not for_login:
                self.add_log("Kaydedilmiş YouTube cookie'leri ekleniyor...")
                # Önce YouTube ana sayfasına git
                driver.get("https://www.youtube.com/")
                time.sleep(2)
                
                # Cookie'leri ekle
                for cookie in self.youtube_cookies:
                    try:
                        # Bazı cookie'ler eklenemeyebilir, bu yüzden try-except içinde ekle
                        driver.add_cookie(cookie)
                    except Exception as cookie_error:
                        self.add_log(f"Cookie ekleme hatası: {str(cookie_error)}")
                
                # Sayfayı yenile
                driver.refresh()
                time.sleep(3)
                self.add_log("Cookie'ler eklendi ve sayfa yenilendi")
            
            return driver
            
        except Exception as e:
            self.add_log(f"Selenium kurulum hatası: {str(e)}")
            return None
    

        pass
            
    def get_profile_videos(self, profile_url):
        """Profil sayfasından tüm video linklerini topla - HTTP istekleri ile (Selenium fallback)"""
        self.add_log(f"Profil videoları HTTP istekleri ile alınıyor: {profile_url}")
        
        # Video türü seçimine göre URL'yi değiştir
        video_type = self.video_type_selection.value
        if video_type == "shorts":
            if not profile_url.endswith("/shorts"):
                profile_url = profile_url.rstrip('/') + "/shorts"
            self.add_log(f"Shorts modu seçildi, URL güncellendi: {profile_url}")
        elif video_type == "videos":
            if not profile_url.endswith("/videos"):
                profile_url = profile_url.rstrip('/') + "/videos"
            self.add_log(f"Videos modu seçildi, URL güncellendi: {profile_url}")
        
        # Önce HTTP istekleri ile dene
        try:
            videos = self.get_profile_videos_http(profile_url)
            if videos:
                self.add_log(f"HTTP istekleri ile {len(videos)} video bulundu")
                return videos, "unknown"  # Username'i HTTP'den çıkarmak zor, şimdilik unknown
            else:
                self.add_log("HTTP istekleri başarısız, Selenium'a geçiliyor...")
        except Exception as e:
            self.add_log(f"HTTP istekleri hatası: {str(e)}, Selenium'a geçiliyor...")
        
        # HTTP başarısız olursa Selenium'a geç
        return self.get_profile_videos_selenium_fallback(profile_url)
    
    def get_profile_videos_http(self, profile_url):
        """HTTP istekleri ile profil videolarını al"""
        try:
            # Kanal ID'sini URL'den çıkar
            channel_id = self.api_scraper.extract_channel_id_from_url(profile_url)
            if not channel_id:
                self.add_log("Kanal ID'si çıkarılamadı")
                return []
            
            self.add_log(f"Kanal ID'si: {channel_id}")
            
            # Video türüne göre farklı yaklaşımlar
            video_type = self.video_type_selection.value
            
            if video_type == "shorts":
                # Shorts için kanal API'si
                self.add_log("Shorts videoları HTTP ile alınıyor...")
                videos = self.api_scraper.get_channel_videos_api(channel_id, max_videos=50, video_type="shorts")
            else:
                # Normal videolar için kanal API'si
                self.add_log("Normal videolar HTTP ile alınıyor...")
                videos = self.api_scraper.get_channel_videos_api(channel_id, max_videos=50, video_type="videos")
            
            if videos:
                self.add_log(f"HTTP ile {len(videos)} video bulundu")
                return videos
            else:
                self.add_log("HTTP ile video bulunamadı")
                return []
                
        except Exception as e:
            self.add_log(f"HTTP profil scraping hatası: {str(e)}")
            return []
    
    def get_playlist_videos(self, playlist_url):
        """Oynatma listesinden tüm video linklerini topla - HTTP istekleri ile"""
        self.add_log(f"Playlist videoları HTTP istekleri ile alınıyor: {playlist_url}")
        
        try:
            # API scraper ile playlist videolarını al
            videos, playlist_title = self.api_scraper.get_playlist_videos_api(playlist_url, max_videos=100)
            
            if videos:
                self.add_log(f"HTTP ile {len(videos)} playlist videosu bulundu")
                return videos, playlist_title
            else:
                self.add_log("HTTP ile playlist videosu bulunamadı")
                return [], "unknown"
                
        except Exception as e:
            self.add_log(f"HTTP playlist scraping hatası: {str(e)}")
            return [], "unknown"
    
    def get_profile_videos_selenium_fallback(self, profile_url):
        """Selenium ile profil videolarını al (tiktok_scraper.py'den basit ve etkili versiyon)"""
        self.add_log(f"Selenium ile profil videoları alınıyor: {profile_url}")
        
        driver = self.setup_selenium(for_login=False)
        if not driver:
            return [], "unknown"
            
        video_urls = []
        username = 'unknown'
        
        try:
            # Video türü seçimine göre URL'yi değiştir
            video_type = self.video_type_selection.value
            if video_type == "shorts":
                if not profile_url.endswith("/shorts"):
                    profile_url = profile_url.rstrip('/') + "/shorts"
                self.add_log(f"Shorts modu seçildi, URL güncellendi: {profile_url}")
            elif video_type == "videos":
                if not profile_url.endswith("/videos"):
                    profile_url = profile_url.rstrip('/') + "/videos"
                self.add_log(f"Videos modu seçildi, URL güncellendi: {profile_url}")
            
            # Kullanıcı adını URL'den çıkar
            try:
                if profile_url and '/@' in profile_url:
                    username_parts = profile_url.split('/@')
                    if len(username_parts) > 1:
                        username = username_parts[1].split('/')[0].split('?')[0]
                        self.add_log(f"URL'den kullanıcı adı çıkarıldı: @{username}")
            except:
                username = 'unknown'
            
            # Profil sayfasına git
            driver.get(profile_url)
            time.sleep(3)
            
            # CAPTCHA kontrolü ve bekleme mekanizması
            self.check_and_handle_captcha(driver)
            
            # Sayfa yüklendikten sonra sayfa başlığından da username'i kontrol et
            try:
                page_title = driver.title
                self.add_log(f"Sayfa başlığı: {page_title}")
                
                # Eğer URL'den username alınamadıysa sayfa başlığından almaya çalış
                if username == 'unknown' and page_title:
                    # TikTok sayfa başlığı genellikle "@username | TikTok" formatında
                    if '@' in page_title:
                        title_parts = page_title.split('@')
                        if len(title_parts) > 1:
                            username_from_title = title_parts[1].split('|')[0].split('(')[0].strip()
                            if username_from_title and len(username_from_title) > 0:
                                username = username_from_title
                                self.add_log(f"Sayfa başlığından kullanıcı adı çıkarıldı: @{username}")
                
                # Son kontrol: username hala unknown ise URL'den tekrar dene
                if username == 'unknown' and profile_url and '/@' in profile_url:
                    try:
                        url_username = profile_url.split('/@')[1].split('/')[0].split('?')[0]
                        if url_username and len(url_username) > 0:
                            username = url_username
                            self.add_log(f"URL'den tekrar kullanıcı adı çıkarıldı: @{username}")
                    except:
                        pass
                        
            except Exception as e:
                self.add_log(f"Sayfa başlığı kontrolü hatası: {str(e)}")
            
            # Sayfayı scroll yaparak daha fazla video yükle
            self.add_log("Profil sayfası kaydırılıyor...")
            scroll_duration = 10
            scroll_interval = 0.5
            scroll_count = int(scroll_duration / scroll_interval)
            
            for i in range(scroll_count):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(scroll_interval)
                
                # Her 5 scroll'da bir sayfanın sonuna git
                if i % 5 == 0:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
            
            # Video elementlerini topla - başlık bilgisi ile birlikte
            video_elements = self.find_video_elements(driver)
            
            self.add_log(f"Profilde {len(video_elements)} video elementi bulundu")
            
            video_data_list = []
            for element in video_elements:
                try:
                    # Video verilerini çıkar (URL, başlık, vs.)
                    video_data = self.extract_video_data(driver, element)
                    if video_data and video_data.get('url'):
                        video_url = video_data['url']
                        if video_url not in [v['url'] for v in video_data_list]:  # Duplicate kontrolü
                            video_data_list.append(video_data)
                            title = video_data.get('title', 'TikTok Video')
                            self.add_log(f"Profil videosu: {title[:30]}... - {video_url}")
                except Exception as e:
                    self.add_log(f"Video veri çıkarma hatası: {str(e)}")
                    continue
            
            # Geriye dönük uyumluluk için video_urls listesi oluştur
            video_urls = [video_data['url'] for video_data in video_data_list]
            
            self.add_log(f"Selenium ile {len(video_urls)} video URL'si toplandı")
            
        except Exception as e:
            self.add_log(f"Selenium profil scraping hatası: {str(e)}")
            
        finally:
            driver.quit()
            
        # video_data_list varsa onu kullan, yoksa video_urls'den oluştur
        if 'video_data_list' in locals() and video_data_list:
            return video_data_list, username
        else:
            return video_urls, username
    
    def check_and_handle_captcha(self, driver):
        """CAPTCHA algılama ve kullanıcı müdahalesi bekleme mekanizması"""
        try:
            # CAPTCHA elementlerini kontrol et
            captcha_selectors = [
                '[data-testid="captcha"]',
                '.captcha',
                '#captcha',
                '[class*="captcha"]',
                '[id*="captcha"]',
                'iframe[src*="captcha"]',
                'div[class*="verify"]',
                'div[class*="challenge"]',
                'div[class*="security"]',
                '[data-e2e="captcha"]',
                '.secsdk-captcha-wrapper',
                '.captcha-verify-image',
                'div[class*="Captcha"]'
            ]
            
            captcha_found = False
            for selector in captcha_selectors:
                try:
                    captcha_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if captcha_element and captcha_element.is_displayed():
                        captcha_found = True
                        self.add_log(f"CAPTCHA algılandı: {selector}")
                        break
                except:
                    continue
            
            # Sayfa başlığında CAPTCHA kontrolü
            page_title = driver.title.lower()
            if 'captcha' in page_title or 'verify' in page_title or 'challenge' in page_title:
                captcha_found = True
                self.add_log(f"Sayfa başlığında CAPTCHA algılandı: {driver.title}")
            
            # URL'de CAPTCHA kontrolü
            current_url = driver.current_url.lower()
            if 'captcha' in current_url or 'verify' in current_url or 'challenge' in current_url:
                captcha_found = True
                self.add_log(f"URL'de CAPTCHA algılandı: {driver.current_url}")
            
            if captcha_found:
                self.add_log("⚠️ CAPTCHA tespit edildi! Kullanıcı müdahalesi gerekiyor.")
                self.update_status("CAPTCHA tespit edildi - Lütfen tarayıcıda CAPTCHA'yı çözün", ft.Colors.ORANGE)
                
                # Kullanıcıya bildirim dialog'u göster
                self.show_captcha_dialog(driver)
                
                # CAPTCHA çözülene kadar bekle
                self.wait_for_captcha_resolution(driver)
            else:
                self.add_log("✅ CAPTCHA tespit edilmedi, işleme devam ediliyor")
                
        except Exception as e:
            self.add_log(f"CAPTCHA kontrolü hatası: {str(e)}")
    
    def show_captcha_dialog(self, driver):
        """CAPTCHA tespit edildiğinde kullanıcıya bildirim dialog'u göster"""
        try:
            def close_captcha_dialog(e):
                self.page.dialog.open = False
                self.page.update()
            
            # CAPTCHA dialog'u oluştur
            captcha_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("CAPTCHA Tespit Edildi", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "TikTok tarafından CAPTCHA doğrulaması isteniyor.",
                            size=14
                        ),
                        ft.Text(
                            "Lütfen tarayıcıda CAPTCHA'yı çözün ve sayfanın yüklenmesini bekleyin.",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            "CAPTCHA çözüldükten sonra bu dialog otomatik olarak kapanacak.",
                            size=12,
                            color=ft.Colors.GREY_600
                        )
                    ], spacing=10),
                    padding=ft.padding.all(10),
                    width=400,
                    height=120
                ),
                actions=[
                    ft.TextButton(
                        "Anladım", 
                        on_click=close_captcha_dialog,
                        style=ft.ButtonStyle(color=ft.Colors.BLUE)
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Dialog'u göster
            self.page.dialog = captcha_dialog
            self.page.dialog.open = True
            self.page.update()
            
        except Exception as e:
            self.add_log(f"CAPTCHA dialog hatası: {str(e)}")
    
    def wait_for_captcha_resolution(self, driver):
        """CAPTCHA çözülene kadar bekle"""
        try:
            self.add_log("CAPTCHA çözülmesi bekleniyor...")
            max_wait_time = 300  # 5 dakika maksimum bekleme
            check_interval = 5   # 5 saniyede bir kontrol
            waited_time = 0
            
            while waited_time < max_wait_time:
                time.sleep(check_interval)
                waited_time += check_interval
                
                # CAPTCHA hala var mı kontrol et
                captcha_still_present = False
                
                # Sayfa başlığı kontrolü
                try:
                    page_title = driver.title.lower()
                    if 'captcha' in page_title or 'verify' in page_title or 'challenge' in page_title:
                        captcha_still_present = True
                except:
                    pass
                
                # URL kontrolü
                try:
                    current_url = driver.current_url.lower()
                    if 'captcha' in current_url or 'verify' in current_url or 'challenge' in current_url:
                        captcha_still_present = True
                except:
                    pass
                
                # CAPTCHA elementleri kontrolü
                if not captcha_still_present:
                    captcha_selectors = [
                        '[data-testid="captcha"]',
                        '.captcha',
                        '#captcha',
                        '[class*="captcha"]',
                        'iframe[src*="captcha"]',
                        'div[class*="verify"]',
                        'div[class*="challenge"]'
                    ]
                    
                    for selector in captcha_selectors:
                        try:
                            captcha_element = driver.find_element(By.CSS_SELECTOR, selector)
                            if captcha_element and captcha_element.is_displayed():
                                captcha_still_present = True
                                break
                        except:
                            continue
                
                if not captcha_still_present:
                    self.add_log("✅ CAPTCHA başarıyla çözüldü!")
                    self.update_status("CAPTCHA çözüldü - İşleme devam ediliyor", ft.Colors.GREEN)
                    
                    # Dialog'u kapat
                    try:
                        if hasattr(self.page, 'dialog') and self.page.dialog and self.page.dialog.open:
                            self.page.dialog.open = False
                            self.page.update()
                    except:
                        pass
                    
                    return True
                
                # İlerleme mesajı
                if waited_time % 30 == 0:  # Her 30 saniyede bir
                    remaining_time = max_wait_time - waited_time
                    self.add_log(f"CAPTCHA bekleniyor... (Kalan süre: {remaining_time} saniye)")
            
            # Zaman aşımı
            self.add_log("⚠️ CAPTCHA bekleme süresi doldu. İşleme devam ediliyor.")
            self.update_status("CAPTCHA bekleme süresi doldu", ft.Colors.ORANGE)
            return False
            
        except Exception as e:
            self.add_log(f"CAPTCHA bekleme hatası: {str(e)}")
            return False
    
    def on_logo_file_selected(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.logo_file_field.value = e.files[0].path
            self.page.update()
            
    def on_output_folder_selected(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.output_folder_field.value = e.path
            self.page.update()
            
    def on_txt_file_selected(self, e: ft.FilePickerResultEvent):
        """TXT dosyası seçildiğinde çağrılır"""
        if e.files:
            self.txt_file_field.value = e.files[0].path
            # Dosyayı okuyup URL sayısını göster
            try:
                with open(e.files[0].path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    url_count = len(lines)
                    self.add_log(f"TXT dosyası seçildi: {url_count} URL bulundu")
                    self.txt_file_field.hint_text = f"{url_count} URL bulundu"
            except Exception as ex:
                self.add_log(f"TXT dosyası okuma hatası: {str(ex)}")
                self.txt_file_field.hint_text = "Dosya okunamadı"
            self.page.update()
            
    def update_status(self, message, color=ft.Colors.BLUE):
        self.status_text.value = message
        self.status_text.color = color
        self.page.update()
        
    def update_log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Milisaniye dahil
        
        # Daha detaylı log formatı
        if "✓" in message or "başarı" in message.lower():
            formatted_message = f"[{timestamp}] ✅ {message}"
        elif "❌" in message or "hata" in message.lower() or "error" in message.lower():
            formatted_message = f"[{timestamp}] ❌ {message}"
        elif "scroll" in message.lower():
            formatted_message = f"[{timestamp}] 🔄 {message}"
        elif "video" in message.lower() and ("bulundu" in message.lower() or "found" in message.lower()):
            formatted_message = f"[{timestamp}] 🎬 {message}"
        elif "indiriliyor" in message.lower() or "downloading" in message.lower():
            formatted_message = f"[{timestamp}] ⬇️ {message}"
        elif "tamamlandı" in message.lower() or "completed" in message.lower():
            formatted_message = f"[{timestamp}] ✅ {message}"
        else:
            formatted_message = f"[{timestamp}] ℹ️ {message}"
        
        current_log = self.log_text.value
        new_log = f"{current_log}\n{formatted_message}" if current_log else formatted_message
        
        # Karakter sınırlandırmasını kaldır - tüm logları göster
        lines = new_log.split('\n')
        # Sadece çok fazla log varsa (1000+ satır) son 500 satırı göster
        if len(lines) > 1000:
            lines = ["... (eski loglar kısaltıldı) ..."] + lines[-500:]
        
        self.log_text.value = '\n'.join(lines)
        self.page.update()
        
    def add_log(self, message):
        """update_log ile aynı işlevi görür - geriye dönük uyumluluk için"""
        self.update_log(message)
        
    def find_video_elements(self, driver):
         """Gelişmiş video element bulma sistemi - tiktok_scraper.py'den entegre edildi ve genişletildi"""
         video_elements = []
         
         # tiktok_scraper.py'deki kapsamlı seçiciler - Genişletildi
         selectors = [
             # TikTok'un yeni seçicileri - Öncelikli
             '[data-e2e="user-post-item"]',
             '[data-e2e="user-post-item-list"] > div',
             '[data-e2e="user-post-item-video"]',
             '[data-e2e="search_top-item"]',
             '[data-e2e="search-card-item"]',
             '[data-e2e="search-card"]',
             '[data-e2e="video-card"]',
             '[data-e2e="user-post-item-desc"]',
             
             # Video linkleri - En önemli
             'a[href*="/video/"]',
             'a[href*="/@"][href*="/video/"]',
             'a[tabindex="-1"][href*="/video/"]',
             
             # Data attribute'ları ile arama - Genişletildi
             'div[data-e2e*="video"]',
             'div[data-e2e*="item"]',
             'div[data-e2e*="post"]',
             'div[data-e2e*="user"]',
             'div[data-e2e*="search"]',
             'div[data-testid*="video"]',
             'div[data-testid*="post"]',
             'div[data-testid*="item"]',
             'div[data-testid*="user"]',
             'div[data-video-id]',
             'div[data-item-id]',
             'div[data-post-id]',
             'div[data-user-id]',
             'div[data-aweme-id]',
             'div[data-unique-id]',
             
             # TikTok'un class yapısı - Genişletildi
             'div[class*="DivContainer"]',
             'div[class*="DivItemContainer"]',
             'div[class*="ItemContainer"]',
             'div[class*="VideoContainer"]',
             'div[class*="PostContainer"]',
             'div[class*="UserPost"]',
             'div[class*="FeedItem"]',
             'div[class*="VideoItem"]',
             'div[class*="ContentItem"]',
             'div[class*="MediaItem"]',
             'div[class*="GridItem"]',
             'div[class*="ListItem"]',
             'div[class*="video"]',
             'div[class*="item"]',
             'div[class*="Card"]',
             'div[class*="Tile"]',
             'div[class*="Post"]',
             'div[class*="Feed"]',
             
             # CSS sınıfları ile arama - Genişletildi
             'a[class*="AVideoContainer"]',
             'a[class*="css-"][class*="AVideoContainer"]',
             'a[href*="/video/"][class*="css-"]',
             'div[class*="css-"][class*="video"]',
             'div[class*="css-"][class*="item"]',
             'div[class*="css-"][class*="post"]',
             'div[class*="css-"][class*="container"]',
             'div[class*="css-"][class*="wrapper"]',
             'div[class*="css-"][class*="card"]',
             'div[class*="css-"][class*="tile"]',
             
             # Genel linkler
             'a[href*="tiktok.com"]',
             'a[href*="/@"]',
             'a[href*="/t/"]',
             'a[href*="/v/"]',
             'a[href*="/user/"]',
             
             # Role ve tabindex ile arama
             '[role="button"]',
             '[role="link"]',
             'div[tabindex="0"]',
             'div[tabindex="-1"]',
             'a[role="link"]',
             'button[role="button"]',
             
             # Canvas ve video player içindeki linkler
             'a:has(canvas)',
             'a:has(div[class*="DivPlayerContainer"])',
             'a:has(div[class*="DivContainer"])',
             
             # Genel yapılar
             'article',
             'section[class*="video"]',
             'section[class*="post"]',
             'section[class*="item"]',
             'section[class*="user"]',
             'li[class*="video"]',
             'li[class*="post"]',
             'li[class*="item"]',
             'li[class*="user"]',
             
             # TikTok spesifik seçiciler
             'div[class*="tiktok"]',
             'div[class*="aweme"]',
             'div[class*="feed"]',
             'div[class*="profile"]',
             'span[class*="video"]',
             'span[class*="item"]',
             
             # Yeni eklenen kapsamlı seçiciler
             'div[class*="grid"]',
             'div[class*="list"]',
             'div[class*="row"]',
             'div[class*="col"]',
             'div[class*="content"]',
             'div[class*="media"]',
             'div[class*="thumb"]',
             'div[class*="preview"]'
         ]
         
         # Tüm seçicileri dene ve en çok element bulan seçiciyi kullan
         best_selector = None
         max_elements = 0
         
         for selector in selectors:
             try:
                 elements = driver.find_elements(By.CSS_SELECTOR, selector)
                 if len(elements) > max_elements:
                     max_elements = len(elements)
                     best_selector = selector
                     video_elements = elements
                 if elements:
                     self.add_log(f"Seçici '{selector}' ile {len(elements)} element bulundu")
             except Exception as ex:
                 self.add_log(f"Seçici hatası ({selector}): {str(ex)}")
                 continue
         
         if best_selector:
             self.add_log(f"En iyi seçici: '{best_selector}' - {max_elements} element")
         
         # Eğer hiç element bulunamadıysa, tüm seçicileri birleştir
         if not video_elements:
             self.add_log("Tek seçici başarısız, tüm seçiciler birleştiriliyor...")
             all_elements = []
             for selector in selectors[:10]:  # İlk 10 seçiciyi dene
                 try:
                     elements = driver.find_elements(By.CSS_SELECTOR, selector)
                     all_elements.extend(elements)
                 except:
                     continue
             video_elements = all_elements
                 
         # Eğer hiç element bulunamazsa, daha kapsamlı arama yap
         if not video_elements:
             self.add_log("Standart seçicilerle video bulunamadı, alternatif yöntemler deneniyor...")
             
             try:
                 # Tüm linkleri kontrol et - Selenium ile
                 all_links = driver.find_elements(By.TAG_NAME, 'a')
                 video_links = []
                 for link in all_links:
                     href = link.get_attribute('href')
                     if href and ('/video/' in href or ('/@' in href and '/video/' in href)):
                         video_links.append(link)
                 
                 # Tıklanabilir div elementlerini kontrol et - Selenium ile
                 clickable_divs = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"], div[tabindex="0"]')
                 for div in clickable_divs:
                     try:
                         inner_link = div.find_element(By.CSS_SELECTOR, 'a[href*="/video/"]')
                         if inner_link:
                             video_links.append(div)
                     except:
                         continue
                 
                 # Tüm div'leri kontrol et (son çare) - Selenium ile
                 all_divs = driver.find_elements(By.TAG_NAME, 'div')
                 for div in all_divs[:100]:  # İlk 100 div'i kontrol et
                     class_name = div.get_attribute('class') or ''
                     if any(keyword in class_name.lower() for keyword in ['video', 'post', 'item', 'container', 'card']):
                         video_links.append(div)
                 
                 video_elements = video_links
                 self.add_log(f"Alternatif yöntemlerle {len(video_elements)} element bulundu")
                 
             except Exception as ex:
                 self.add_log(f"Alternatif arama hatası: {str(ex)}")
                 
         # Duplicate'ları temizle - Daha akıllı algoritma
         unique_elements = []
         seen_urls = set()
         seen_positions = set()
         
         for element in video_elements:
             try:
                 # Element pozisyonu ile unique kontrolü (daha güvenilir)
                 location = element.location
                 position_key = f"{location['x']}_{location['y']}"
                 
                 # Eğer aynı pozisyonda element varsa, atla
                 if position_key in seen_positions:
                     continue
                     
                 # Element içindeki video URL'ini kontrol et
                 has_video_url = False
                 try:
                     # Element kendisi link mi?
                     if element.tag_name == 'a':
                         href = element.get_attribute('href')
                         if href and '/video/' in href:
                             if href not in seen_urls:
                                 seen_urls.add(href)
                                 has_video_url = True
                     else:
                         # Element içindeki video linklerini kontrol et
                         video_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
                         for link in video_links:
                             href = link.get_attribute('href')
                             if href and href not in seen_urls:
                                 seen_urls.add(href)
                                 has_video_url = True
                                 break
                 except:
                     # Hata durumunda elementi dahil et
                     has_video_url = True
                 
                 # Video URL'si varsa ve pozisyon unique ise ekle
                 if has_video_url:
                     unique_elements.append(element)
                     seen_positions.add(position_key)
                     
             except Exception as e:
                 # Hata durumunda elementi dahil et
                 unique_elements.append(element)
                 
         self.add_log(f"Duplicate temizleme sonrası {len(unique_elements)} unique element (önceki: {len(video_elements)})")
         
         # Eğer çok az element kaldıysa, daha esnek temizleme yap
         if len(unique_elements) < len(video_elements) * 0.1:  # %10'dan az kaldıysa
             self.add_log("Çok agresif temizleme tespit edildi, daha esnek algoritma kullanılıyor...")
             unique_elements = []
             seen_html = set()
             
             for element in video_elements:
                 try:
                     # Sadece HTML'in ilk 50 karakterini kontrol et (daha esnek)
                     element_html = element.get_attribute('outerHTML')[:50]
                     if element_html not in seen_html:
                         unique_elements.append(element)
                         seen_html.add(element_html)
                 except:
                     unique_elements.append(element)
             
             self.add_log(f"Esnek temizleme sonrası {len(unique_elements)} unique element")
         
         return unique_elements
        
    def extract_video_data(self, driver, element):
         """Video elementinden veri çıkarma - tiktok_scraper.py'den entegre edildi"""
         try:
             # Element kontrolü - NoneType hatası önleme
             if element is None:
                 return None
                 
             video_data = {
                 'url': None,
                 'title': 'TikTok Video',
                 'views': '0',
                 'likes': '0',
                 'author': ''
             }
             
             # Video URL'sini bul - Geliştirilmiş mantık
             video_url = None
             
             # Eğer element kendisi bir link ise
             try:
                 tag_name = element.tag_name
             except:
                 tag_name = None
                 
             if tag_name == 'a':
                 video_url = element.get_attribute('href')
                 self.add_log(f"Element kendisi link: {video_url}")
             else:
                 # Element içindeki link'i ara - daha kapsamlı
                 link_selectors = [
                     'a[href*="/video/"]',
                     'a[href*="/@"][href*="/video/"]',
                     'a[href*="/@"]',
                     'a[tabindex="-1"]',
                     'a[class*="AVideoContainer"]',
                     'a[class*="css-"]',
                     'a'
                 ]
                 
                 for selector in link_selectors:
                     try:
                         link_elements = element.find_elements(By.CSS_SELECTOR, selector)
                         self.add_log(f"Seçici '{selector}' ile {len(link_elements)} link bulundu")
                         for link_element in link_elements:
                             href = link_element.get_attribute('href')
                             if href:
                                 self.add_log(f"Link bulundu: {href}")
                                 if '/video/' in href or ('/@' in href):
                                     video_url = href
                                     self.add_log(f"Video URL seçildi: {video_url}")
                                     break
                         if video_url:
                             break
                     except Exception as e:
                         self.add_log(f"Seçici '{selector}' hatası: {str(e)}")
                         continue
             
             # Eğer hala URL bulunamadıysa, element'in data attributelerini kontrol et
             if not video_url:
                 try:
                     # data-e2e attributelerini kontrol et
                     data_e2e = element.get_attribute('data-e2e')
                     if data_e2e and 'post-item' in data_e2e:
                         # Bu bir video post item'ı, içindeki tüm linkleri kontrol et
                         all_links = element.find_elements(By.TAG_NAME, 'a')
                         for link in all_links:
                             href = link.get_attribute('href')
                             if href and ('tiktok.com' in href):
                                 video_url = href
                                 break
                 except:
                     pass
             
             if not video_url:
                 self.add_log(f"Video URL bulunamadı - Element: {element.get_attribute('outerHTML')[:200]}...")
                 return None
                 
             # Video URL'sini düzelt (profil linkinden video linkine çevir)
             if '/video/' not in video_url and '/@' in video_url:
                 video_id = self.extract_video_id_from_profile_url(video_url)
                 if video_id:
                     try:
                         username = video_url.split('/@')[1].split('/')[0] if video_url and '/@' in video_url else 'unknown'
                     except Exception:
                         username = 'unknown'
                     video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                 else:
                     return None
             elif '/video/' not in video_url:
                 return None
                 
             video_data['url'] = video_url
             
             # Video başlığını bul - tiktok_scraper.py'deki gelişmiş yöntem
             video_data['title'] = self.extract_title(element)
             
             # İzlenme sayısını bul - tiktok_scraper.py'deki gelişmiş yöntem
             video_data['views'] = self.extract_view_count(element)
             
             # Yazar bilgisini bul
             try:
                 author_selectors = [
                     '[data-e2e="video-author"]',
                     'span[data-e2e="video-author"]',
                     'a[data-e2e="video-author"]',
                     'span[class*="SpanUserTitle"]',
                     'a[class*="LinkUserTitle"]'
                 ]
                 
                 for selector in author_selectors:
                     try:
                         author_element = element.find_element(By.CSS_SELECTOR, selector)
                         if author_element:
                             author = author_element.text
                             if author:
                                 video_data['author'] = author
                                 break
                     except:
                         continue
             except:
                 pass
                 
             return video_data
             
         except Exception as ex:
             self.add_log(f"Video veri çıkarma hatası: {str(ex)}")
             return None
             
    def extract_view_count(self, element):
        """İzlenme sayısını çıkar - tiktok_scraper.py'den entegre edildi"""
        try:
            # Element kontrolü - NoneType hatası önleme
            if element is None:
                return "0"
                
            # İzlenme sayısı için farklı seçiciler
            view_selectors = [
                '[data-e2e="browse-like-count"]',
                '[data-e2e="video-views"]',
                'strong[data-e2e*="count"]',
                'span[data-e2e*="count"]',
                'strong[class*="count"]',
                'span[class*="count"]',
                'div[class*="DivVideoInfoContainer"] strong',
                'strong[class*="StrongVideoCount"]'
            ]
            
            for selector in view_selectors:
                try:
                    view_element = element.find_element(By.CSS_SELECTOR, selector)
                    if view_element:
                        view_text = view_element.text.strip()
                        if view_text and any(char.isdigit() for char in view_text):
                            return view_text
                except:
                    continue
                    
            # Fallback: element içindeki tüm metinleri kontrol et
            all_text = element.text
            view_patterns = [r'(\d+(?:\.\d+)?[KMB]?)\s*(?:views?|izlenme)', r'(\d+(?:\.\d+)?[KMB]?)']
            
            for pattern in view_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    return matches[0]
                    
            return "0"
            
        except:
            return "0"
            
    def extract_title(self, element):
        """Video başlığını çıkar - tiktok_scraper.py'den entegre edildi"""
        try:
            # Element kontrolü - NoneType hatası önleme
            if element is None:
                return "TikTok Video"
                
            # Başlık için farklı seçiciler
            title_selectors = [
                '[data-e2e="browse-video-desc"]',
                '[data-e2e="video-desc"]',
                'div[class*="desc"]',
                'div[class*="caption"]',
                'span[class*="desc"]',
                'div[class*="DivVideoInfoContainer"] span',
                'span[class*="SpanText"]',
                'div[title]',
                'span[title]'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    if title_element:
                        title_text = title_element.get_attribute('title') or title_element.text.strip()
                        if title_text and len(title_text) > 5:
                            return title_text[:100]  # İlk 100 karakter
                except:
                    continue
                    
            return "TikTok Video"
            
        except:
            return "TikTok Video"
            
    def extract_video_id(self, url):
        """URL'den video ID'sini çıkar"""
        try:
            # URL'den uzun sayısal ID'yi ara
            match = re.search(r'/(\d{15,})', url)
            if match:
                return match.group(1)
            return 'unknown'
        except:
            return 'unknown'
            
    def extract_video_id_from_profile_url(self, url):
        """Profil URL'sinden video ID'sini çıkar - tiktok_scraper.py'den entegre edildi"""
        try:
            # URL'den uzun sayısal ID'yi ara
            match = re.search(r'/(\d{15,})', url)
            if match:
                return match.group(1)
            return None
        except:
            return None
            
    def parse_view_count(self, view_text):
        """İzlenme sayısını sayısal değere çevir - tiktok_scraper.py'den entegre edildi"""
        try:
            if not view_text:
                return 0
                
            # K, M, B gibi kısaltmaları işle
            view_text = view_text.upper().replace(',', '').replace('.', '')
            
            if 'K' in view_text:
                return int(float(view_text.replace('K', '')) * 1000)
            elif 'M' in view_text:
                return int(float(view_text.replace('M', '')) * 1000000)
            elif 'B' in view_text:
                return int(float(view_text.replace('B', '')) * 1000000000)
            else:
                # Sadece sayı
                numbers = re.findall(r'\d+', view_text)
                if numbers:
                    return int(numbers[0])
                    
            return 0
            
        except:
            return 0
            
    def parse_view_count(self, view_text):
        """İzlenme sayısını sayısal değere çevir - tiktok_scraper.py'den entegre edildi"""
        try:
            if not view_text:
                return 0
                
            # K, M, B gibi kısaltmaları işle
            view_text = view_text.upper().replace(',', '').replace('.', '')
            
            if 'K' in view_text:
                return int(float(view_text.replace('K', '')) * 1000)
            elif 'M' in view_text:
                return int(float(view_text.replace('M', '')) * 1000000)
            elif 'B' in view_text:
                return int(float(view_text.replace('B', '')) * 1000000000)
            else:
                # Sadece sayı
                numbers = re.findall(r'\d+', view_text)
                if numbers:
                    return int(numbers[0])
                    
            return 0
            
        except:
            return 0
        
    def copy_logs(self, e):
        if self.log_text.value:
            self.page.set_clipboard(self.log_text.value)
            self.update_status("Loglar panoya kopyalandı!", ft.Colors.GREEN)
        else:
            self.update_status("Kopyalanacak log bulunamadı!", ft.Colors.ORANGE)
             
    def clear_logs(self, e):
        self.log_text.value = ""
        self.page.update()
        self.update_status("Loglar temizlendi!", ft.Colors.BLUE)
        
    def start_download(self, e):
        if self.is_downloading:
            return
        
        # İndirme modu kontrolü
        download_mode = self.download_mode.value
        
        # Validasyon
        if download_mode == "txt_file":
            if not self.txt_file_field.value:
                self.update_status("TXT dosyası seçiniz!", ft.Colors.RED)
                return
            # TXT dosyasının varlığını kontrol et
            if not os.path.exists(self.txt_file_field.value):
                self.update_status("Seçilen TXT dosyası bulunamadı!", ft.Colors.RED)
                return
        elif download_mode == "playlist":
            if not self.playlist_url_field.value:
                self.update_status("Oynatma listesi URL'si giriniz!", ft.Colors.RED)
                return
            if 'youtube.com' not in self.playlist_url_field.value or 'list=' not in self.playlist_url_field.value:
                self.update_status("Geçerli bir YouTube oynatma listesi URL'si giriniz!", ft.Colors.RED)
                return
        else:
            if not self.profile_url_field.value:
                self.update_status("Profil URL'si giriniz!", ft.Colors.RED)
                return
            if 'youtube.com' not in self.profile_url_field.value:
                self.update_status("Geçerli bir YouTube profil URL'si giriniz!", ft.Colors.RED)
                return
        
        # Çıktı klasörü kontrolü
        if not self.output_folder_field.value:
            self.update_status("Çıktı klasörü seçiniz!", ft.Colors.RED)
            return
        
        # Logo ekleme seçeneği işaretliyse logo dosyasını kontrol et
        if self.use_logo_checkbox.value and not self.logo_file_field.value:
            self.update_status("Logo dosyası seçiniz!", ft.Colors.RED)
            return
        
        # MP3 çevirme seçeneği işaretliyse FFmpeg kontrolü yap
        if self.convert_to_mp3_checkbox.value:
            if not self.check_ffmpeg_installed():
                self.update_status("⚠️ FFmpeg bulunamadı! MP3 çevirme için FFmpeg gerekli.", ft.Colors.ORANGE)
                self.update_log("FFmpeg indirmek için: https://ffmpeg.org/download.html")
                self.update_log("MP3 çevirme özelliği devre dışı bırakılacak.")
                # MP3 çevirme özelliğini otomatik olarak kapat
                self.convert_to_mp3_checkbox.value = False
                self.page.update()
                return
        
        # Video sayısını sıfırla (profil ve txt modunda kullanılmaz)
        video_count = 0
        
        # İndirmeyi başlat
        self.is_downloading = True
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.update_status("Toplu indirme başlatılıyor...", ft.Colors.ORANGE)
        self.page.update()
        
        # Thread'de çalıştır
        threading.Thread(target=self.download_process, daemon=True).start()
        
    def stop_download(self, e):
        self.is_downloading = False
        self.progress_bar.visible = False
        self.update_status("İndirme durduruldu", ft.Colors.RED)
        self.page.update()
        
    def download_process(self):
        try:
            # Zaman sayacını başlat
            import datetime
            start_time = datetime.datetime.now()
            self.update_log(f"İndirme başlangıç zamanı: {start_time.strftime('%H:%M:%S')}")
            
            download_mode = self.download_mode.value
            # Logo ekleme seçeneği işaretliyse logo dosyasını kullan, değilse None olarak ayarla
            logo_file = self.logo_file_field.value if self.use_logo_checkbox.value else None
            output_folder = self.output_folder_field.value
            
            # Klasörleri oluştur
            os.makedirs(output_folder, exist_ok=True)
            
            # MP3 olarak indir seçeneği işaretliyse Music alt klasörü oluştur
            if self.convert_to_mp3_checkbox.value:
                music_folder = os.path.join(output_folder, "Music")
                os.makedirs(music_folder, exist_ok=True)
                output_folder = music_folder
                self.update_log("MP3 dosyaları Music klasörüne indirilecek")
            
            videos = []
            
            if download_mode == "txt_file":
                # TXT dosyası modu
                txt_file_path = self.txt_file_field.value
                self.update_log(f"TXT dosyasından toplu indirme başlatıldı: {txt_file_path}")
                
                # TXT dosyasını oku
                try:
                    with open(txt_file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                    
                    self.update_log(f"TXT dosyasından {len(lines)} URL okundu")
                    
                    # Youtube Txt Dosyasından Toplu İndir klasörü oluştur
                    txt_folder = os.path.join(output_folder, "Youtube Txt Dosyasından Toplu İndir")
                    os.makedirs(txt_folder, exist_ok=True)
                    
                    # URL'leri video formatına çevir
                    videos = []
                    for i, url in enumerate(lines):
                        if 'tiktok.com' in url:
                            video_id = url.split('/video/')[1].split('?')[0] if '/video/' in url else f"video_{i+1}"
                            videos.append({
                                'url': url,
                                'video_url': url,
                                'video_id': video_id,
                                'title': f'TikTok Video {i+1}'
                            })
                        else:
                            self.update_log(f"Geçersiz URL atlandı: {url}")
                    
                    # Çıktı klasörünü TXT klasörü olarak güncelle
                    output_folder = txt_folder
                    self.update_log(f"Videolar {txt_folder} klasörüne indirilecek")
                    
                except Exception as e:
                    self.update_status(f"TXT dosyası okuma hatası: {str(e)}", ft.Colors.RED)
                    self.is_downloading = False
                    return
                    
            elif download_mode == "playlist":
                # Playlist modu
                playlist_url = self.playlist_url_field.value.strip()
                self.update_log(f"Oynatma listesinden toplu indirme başlatıldı: {playlist_url}")
                
                # Playlist videolarını topla
                video_data_or_urls, playlist_title = self.get_playlist_videos(playlist_url)
                
                # Youtube Oynatma Listesi İndir klasörü oluştur
                if playlist_title == 'unknown':
                    playlist_folder = os.path.join(output_folder, "Youtube Oynatma Listesi İndir")
                    list_folder = os.path.join(playlist_folder, "Bilinmeyen Oynatma Listesi")
                else:
                    playlist_folder = os.path.join(output_folder, "Youtube Oynatma Listesi İndir")
                    list_folder = os.path.join(playlist_folder, playlist_title)
                
                os.makedirs(list_folder, exist_ok=True)
                
                self.update_log(f"{playlist_title} oynatma listesinden videolar toplanıyor...")
                    
                if not video_data_or_urls:
                    self.update_status("Oynatma listesinde video bulunamadı!", ft.Colors.RED)
                    self.is_downloading = False
                    return
                
                # Playlist modunda tüm videoları indir
                self.update_log(f"Toplam {len(video_data_or_urls)} video bulundu, hepsi indirilecek")
                
                # Video verilerini işle
                videos = []
                for i, item in enumerate(video_data_or_urls):
                    if isinstance(item, dict) and 'url' in item:
                        # Zaten video_data formatında
                        video_data = item.copy()
                        if 'video_id' not in video_data:
                            url = video_data['url']
                            video_data['video_id'] = url.split('v=')[1].split('&')[0] if 'v=' in url else f"video_{i+1}"
                        if 'video_url' not in video_data:
                            video_data['video_url'] = video_data['url']
                        videos.append(video_data)
                    else:
                        # URL formatında, video_data'ya çevir
                        url = item
                        video_id = url.split('v=')[1].split('&')[0] if 'v=' in url else f"video_{i+1}"
                        videos.append({
                            'url': url,
                            'video_url': url,
                            'video_id': video_id,
                            'title': 'YouTube Video'
                        })
                
                # Çıktı klasörünü playlist klasörü olarak güncelle
                output_folder = list_folder
                self.update_log(f"Videolar {list_folder} klasörüne indirilecek")
                
            else:
                # Profil modu
                profile_url = self.profile_url_field.value.strip()
                if not profile_url or '/@' not in profile_url:
                    self.update_status("Geçerli bir profil URL'si girin!", ft.Colors.RED)
                    self.is_downloading = False
                    return
                
                # Profil videolarını topla (kullanıcı adı sayfa başlığından çıkarılacak)
                video_data_or_urls, username = self.get_profile_videos(profile_url)
                
                # Youtube Profil Url Bölümü klasörü oluştur
                if username == 'unknown':
                    profile_folder = os.path.join(output_folder, "Youtube Profil Url Bölümü")
                    user_folder = os.path.join(profile_folder, "Bilinmeyen Kullanıcı")
                else:
                    profile_folder = os.path.join(output_folder, "Youtube Profil Url Bölümü")
                    user_folder = os.path.join(profile_folder, username)
                
                os.makedirs(user_folder, exist_ok=True)
                
                self.update_log(f"@{username} profilinden videolar toplanıyor...")
                    
                if not video_data_or_urls:
                    self.update_status("Profilde video bulunamadı!", ft.Colors.RED)
                    self.is_downloading = False
                    return
                
                # Profil modunda tüm videoları indir (video_count sınırlaması yok)
                self.update_log(f"Toplam {len(video_data_or_urls)} video bulundu, hepsi indirilecek")
                
                # Video verilerini işle
                videos = []
                for i, item in enumerate(video_data_or_urls):
                    if isinstance(item, dict) and 'url' in item:
                        # Zaten video_data formatında
                        video_data = item.copy()
                        if 'video_id' not in video_data:
                            url = video_data['url']
                            video_data['video_id'] = url.split('/video/')[1].split('?')[0] if '/video/' in url else f"video_{i+1}"
                        if 'video_url' not in video_data:
                            video_data['video_url'] = video_data['url']
                        videos.append(video_data)
                    else:
                        # URL formatında, video_data'ya çevir
                        url = item
                        video_id = url.split('/video/')[1].split('?')[0] if '/video/' in url else f"video_{i+1}"
                        videos.append({
                            'url': url,
                            'video_url': url,
                            'video_id': video_id,
                            'title': 'TikTok Video'
                        })
                
                # Çıktı klasörünü kullanıcı klasörü olarak güncelle
                output_folder = user_folder
                self.update_log(f"Videolar {user_folder} klasörüne indirilecek")
            
            if not videos:
                self.update_status("Video bulunamadı!", ft.Colors.RED)
                self.is_downloading = False
                return
                
            self.update_log(f"{len(videos)} video bulundu")
            
            # Müzik özelliği kaldırıldı
            
            # Paralel indirme sistemi - 10'arlı gruplar halinde
            processed_count = self.download_videos_parallel(videos, output_folder, logo_file)
                    
            # Tamamlandı - Zaman sayacını durdur ve toplam süreyi hesapla
            end_time = datetime.datetime.now()
            total_duration = end_time - start_time
            hours, remainder = divmod(total_duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            self.update_log(f"İndirme bitiş zamanı: {end_time.strftime('%H:%M:%S')}")
            self.update_log(f"{processed_count} video {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d} sürecinde indirildi")
            
            self.is_downloading = False
            self.progress_bar.visible = False
            self.update_status(f"Tamamlandı! {processed_count}/{len(videos)} video işlendi", ft.Colors.GREEN)
            self.page.update()
            
        except Exception as e:
            self.is_downloading = False
            self.progress_bar.visible = False
            self.update_status(f"Hata: {str(e)}", ft.Colors.RED)
            self.page.update()
    
    def download_single_video(self, video_data):
        """Tek bir videoyu indirir ve işler - thread-safe"""
        video, output_folder, logo_file, video_index, total_videos = video_data
        
        try:
            if not self.is_downloading:
                return None
                
            # Video indir
            video_path = self.download_video(video, output_folder)
            
            if not video_path:
                # Video indirilemedi - genel hata mesajı
                video_url = video.get('video_url') if isinstance(video, dict) else video
                return {'success': False, 'index': video_index, 'error': 'Video indirilemedi', 'skip': True}
            
            # MP3 olarak indirme kontrolü - artık direkt MP3 indiriliyor, çevirme gerekmiyor
            # video_path zaten doğru formatta (MP3 veya MP4)
                
            # Video işleme - sadece logo ekle (eğer seçilmişse ve MP4 dosyasıysa)
            # MP3 dosyalarına logo eklenemez
            if logo_file and video_path.lower().endswith('.mp4') and not self.convert_to_mp3_checkbox.value:
                try:
                    # Sadece logo ekleme işlemi
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    processed_path = os.path.join(output_folder, f"{base_name}_with_logo.mp4")
                    
                    success = self.video_processor.add_logo_with_ffmpeg(
                        video_path=video_path,
                        logo_path=logo_file,
                        output_path=processed_path
                    )
                    
                    if success:
                        # Orijinal videoyu sil
                        try:
                            os.remove(video_path)
                        except:
                            pass
                        return {'success': True, 'index': video_index, 'filename': os.path.basename(processed_path), 'logo_added': True}
                    else:
                        return {'success': True, 'index': video_index, 'filename': os.path.basename(video_path), 'logo_added': False}
                except Exception as logo_error:
                    return {'success': True, 'index': video_index, 'filename': os.path.basename(video_path), 'logo_error': str(logo_error)}
            else:
                # Logo yoksa veya MP3 dosyası ise dosya olduğu gibi kalır
                if self.convert_to_mp3_checkbox.value and logo_file:
                    self.add_log(f"⚠️ MP3 dosyalarına logo eklenemez: {os.path.basename(video_path)}")
                return {'success': True, 'index': video_index, 'filename': os.path.basename(video_path), 'logo_added': False}
                
        except Exception as e:
            return {'success': False, 'index': video_index, 'error': str(e)}
    
    def download_videos_parallel(self, videos, output_folder, logo_file):
        """Videoları paralel olarak kullanıcının belirlediği grup sayısında indirir"""
        total_videos = len(videos)
        processed_count = 0
        failed_videos = []  # Başarısız indirmeler için
        
        # Kullanıcının belirlediği grup sayısını al ve doğrula
        try:
            batch_size = int(self.parallel_batch_size_field.value)
            if batch_size < 1:
                batch_size = 1
            elif batch_size > 50:
                batch_size = 50
        except:
            batch_size = 10  # Varsayılan değer
            self.update_log("Geçersiz grup sayısı, varsayılan değer (10) kullanılıyor")
        
        self.update_log(f"Paralel indirme başlatılıyor - {batch_size}'arlı gruplar halinde")
        
        # Videoları gruplar halinde böl
        for batch_start in range(0, total_videos, batch_size):
            if not self.is_downloading:
                break
                
            batch_end = min(batch_start + batch_size, total_videos)
            current_batch = videos[batch_start:batch_end]
            
            self.update_log(f"Grup {batch_start//batch_size + 1}: Video {batch_start + 1}-{batch_end} indiriliyor...")
            
            # Mevcut grup için video verilerini hazırla
            video_data_list = []
            for i, video in enumerate(current_batch):
                video_data_list.append((video, output_folder, logo_file, batch_start + i + 1, total_videos))
            
            # ThreadPoolExecutor ile paralel indirme
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Tüm videoları submit et
                future_to_video = {executor.submit(self.download_single_video, video_data): video_data for video_data in video_data_list}
                
                # Sonuçları topla
                for future in as_completed(future_to_video):
                    if not self.is_downloading:
                        break
                        
                    try:
                        result = future.result()
                        if result:
                            if result['success']:
                                processed_count += 1
                                filename = result['filename']
                                video_num = result['index']
                                
                                if 'logo_added' in result and result['logo_added']:
                                    self.update_log(f"Video {video_num}/{total_videos} indirildi ve logo eklendi: {filename}")
                                elif 'logo_error' in result:
                                    self.update_log(f"Video {video_num}/{total_videos} indirildi (logo hatası): {filename}")
                                else:
                                    self.update_log(f"Video {video_num}/{total_videos} indirildi: {filename}")
                            else:
                                video_num = result['index']
                                error = result.get('error', 'Bilinmeyen hata')
                                
                                # Video indirilemedi - genel hata mesajı
                                if result.get('skip'):
                                    self.update_log(f"⏭️ Video {video_num}/{total_videos} atlandı: {error}")
                                else:
                                    self.update_log(f"Video {video_num}/{total_videos} hatası: {error}")
                                    # Başarısız videoyu listeye ekle
                                    failed_videos.append({
                                        'video': videos[video_num - 1],
                                        'index': video_num,
                                        'error': error
                                    })
                            
                            # Progress güncelle
                            progress = result['index'] / total_videos
                            self.progress_bar.value = progress
                            self.page.update()
                            
                    except Exception as e:
                        self.update_log(f"Thread hatası: {str(e)}")
            
            # Grup tamamlandı, kısa bir bekleme (son grup değilse)
            if batch_end < total_videos and self.is_downloading:
                self.update_log(f"Grup {batch_start//batch_size + 1} tamamlandı. 2 saniye bekleniyor...")
                time.sleep(2)
        
        # Başarısız videoları sürekli tekrar dene
        if failed_videos and self.is_downloading:
            self.update_log(f"\n{len(failed_videos)} başarısız video sürekli tekrar deneniyor...")
            retry_processed = self.retry_failed_videos_continuously(failed_videos, output_folder, logo_file, batch_size)
            processed_count += retry_processed
        
        return processed_count
    
    def retry_failed_videos(self, failed_videos, output_folder, logo_file, batch_size):
        """Başarısız videoları tekrar indir"""
        retry_processed = 0
        total_failed = len(failed_videos)
        
        self.update_log("Başarısız videolar için tekrar deneme başlatılıyor...")
        
        # Başarısız videoları gruplar halinde tekrar dene
        for batch_start in range(0, total_failed, batch_size):
            if not self.is_downloading:
                break
                
            batch_end = min(batch_start + batch_size, total_failed)
            current_batch = failed_videos[batch_start:batch_end]
            
            self.update_log(f"Tekrar deneme grubu: {batch_start + 1}-{batch_end}")
            
            # Mevcut grup için video verilerini hazırla
            video_data_list = []
            for i, failed_item in enumerate(current_batch):
                video_data_list.append((
                    failed_item['video'], 
                    output_folder, 
                    logo_file, 
                    failed_item['index'], 
                    total_failed
                ))
            
            # ThreadPoolExecutor ile paralel tekrar deneme
            with ThreadPoolExecutor(max_workers=min(batch_size, len(current_batch))) as executor:
                # Tüm videoları submit et
                future_to_video = {executor.submit(self.download_single_video, video_data): video_data for video_data in video_data_list}
                
                # Sonuçları topla
                for future in as_completed(future_to_video):
                    if not self.is_downloading:
                        break
                        
                    try:
                        result = future.result()
                        if result and result['success']:
                            retry_processed += 1
                            filename = result['filename']
                            video_num = result['index']
                            
                            if 'logo_added' in result and result['logo_added']:
                                self.update_log(f"✓ Tekrar deneme başarılı {video_num}: {filename} (logo eklendi)")
                            else:
                                self.update_log(f"✓ Tekrar deneme başarılı {video_num}: {filename}")
                        else:
                            video_num = result['index'] if result else 'Bilinmeyen'
                            self.update_log(f"✗ Tekrar deneme başarısız {video_num}")
                            
                    except Exception as e:
                        self.update_log(f"Tekrar deneme thread hatası: {str(e)}")
            
            # Grup tamamlandı, kısa bir bekleme (son grup değilse)
            if batch_end < total_failed and self.is_downloading:
                time.sleep(1)
        
        self.update_log(f"Tekrar deneme tamamlandı: {retry_processed}/{total_failed} video başarılı")
        return retry_processed
    
    def retry_failed_videos_continuously(self, failed_videos, output_folder, logo_file, batch_size):
        """Başarısız videoları sürekli tekrar indir (tüm videolar başarılı olana kadar)"""
        retry_processed = 0
        current_failed = failed_videos.copy()
        retry_attempt = 1
        max_attempts = 10  # Maksimum 10 kez deneme
        
        while current_failed and self.is_downloading and retry_attempt <= max_attempts:
            self.update_log(f"\n🔄 Tekrar deneme #{retry_attempt} - {len(current_failed)} video deneniyor...")
            
            # Bu turda başarısız olan videoları takip et
            still_failed = []
            
            # Başarısız videoları gruplar halinde tekrar dene
            for batch_start in range(0, len(current_failed), batch_size):
                if not self.is_downloading:
                    break
                    
                batch_end = min(batch_start + batch_size, len(current_failed))
                current_batch = current_failed[batch_start:batch_end]
                
                self.update_log(f"Grup {batch_start//batch_size + 1}: {batch_start + 1}-{batch_end} videoları deneniyor...")
                
                # Mevcut grup için video verilerini hazırla
                video_data_list = []
                for failed_item in current_batch:
                    video_data_list.append((
                        failed_item['video'], 
                        output_folder, 
                        logo_file, 
                        failed_item['index'], 
                        len(current_failed)
                    ))
                
                # ThreadPoolExecutor ile paralel tekrar deneme
                with ThreadPoolExecutor(max_workers=min(batch_size, len(current_batch))) as executor:
                    # Tüm videoları submit et
                    future_to_video = {executor.submit(self.download_single_video, video_data): (video_data, current_batch[i]) for i, video_data in enumerate(video_data_list)}
                    
                    # Sonuçları topla
                    for future in as_completed(future_to_video):
                        if not self.is_downloading:
                            break
                            
                        try:
                            result = future.result()
                            video_data, failed_item = future_to_video[future]
                            
                            if result and result['success']:
                                retry_processed += 1
                                filename = result['filename']
                                video_num = result['index']
                                
                                if 'logo_added' in result and result['logo_added']:
                                    self.update_log(f"✅ #{retry_attempt} Başarılı {video_num}: {filename} (logo eklendi)")
                                else:
                                    self.update_log(f"✅ #{retry_attempt} Başarılı {video_num}: {filename}")
                            else:
                                # Hala başarısız, tekrar deneme listesine ekle
                                still_failed.append(failed_item)
                                video_num = result['index'] if result else failed_item['index']
                                self.update_log(f"❌ #{retry_attempt} Başarısız {video_num} - tekrar denenecek")
                                
                        except Exception as e:
                            # Hata durumunda da tekrar deneme listesine ekle
                            video_data, failed_item = future_to_video[future]
                            still_failed.append(failed_item)
                            self.update_log(f"⚠️ #{retry_attempt} Thread hatası {failed_item['index']}: {str(e)}")
                
                # Grup tamamlandı, kısa bir bekleme
                if batch_end < len(current_failed) and self.is_downloading:
                    time.sleep(1)
            
            # Sonraki tur için başarısız videoları güncelle
            current_failed = still_failed
            
            if current_failed:
                self.update_log(f"🔄 Tekrar deneme #{retry_attempt} tamamlandı. {len(current_failed)} video hala başarısız.")
                if retry_attempt < max_attempts:
                    self.update_log(f"⏳ 3 saniye bekleyip tekrar denenecek...")
                    time.sleep(3)
            else:
                self.update_log(f"🎉 Tüm videolar başarıyla indirildi! (Toplam {retry_attempt} deneme)")
                break
                
            retry_attempt += 1
        
        if current_failed and retry_attempt > max_attempts:
            self.update_log(f"⚠️ Maksimum deneme sayısına ulaşıldı. {len(current_failed)} video indirilemedi.")
            for failed_item in current_failed:
                self.update_log(f"❌ İndirilemedi: Video {failed_item['index']} - {failed_item.get('error', 'Bilinmeyen hata')}")
        
        total_attempted = len(failed_videos)
        self.update_log(f"\n📊 Sürekli tekrar deneme özeti: {retry_processed}/{total_attempted} video başarılı")
        return retry_processed
             
    def login_to_youtube(self, e):
        """YouTube hesabına giriş yapmak için tarayıcı açar ve cookie'leri alır"""
        self.update_status("YouTube hesabına giriş yapılıyor...", ft.Colors.ORANGE)
        self.update_log("YouTube hesabına giriş işlemi başlatılıyor...")
        
        # Tarayıcıyı aç ve butonları göster
        self.start_login_process()
    
    def start_login_process(self):
        """YouTube giriş işlemini başlatır ve butonları gösterir"""
        try:
            # Tarayıcıyı thread'de aç
            def open_browser():
                try:
                    # Selenium WebDriver'ı ayarla - giriş işlemi için for_login=True
                    self.login_driver = self.setup_selenium(for_login=True)
                    if not self.login_driver:
                        self.update_status("Tarayıcı açılamadı!", ft.Colors.RED)
                        return
                    
                    # YouTube ana sayfasına git
                    self.update_log("YouTube ana sayfası açılıyor...")
                    self.login_driver.get("https://www.youtube.com/")
                    
                    # Sayfanın yüklenmesini bekle
                    time.sleep(5)
                    
                    # Kullanıcıya bilgi ver
                    self.update_log("YouTube sayfası açıldı. Lütfen hesabınıza giriş yapın.")
                    
                except Exception as e:
                    self.update_log(f"Tarayıcı açma hatası: {str(e)}")
                    self.update_status("Tarayıcı açılamadı!", ft.Colors.RED)
            
            # Tarayıcıyı thread'de başlat
            threading.Thread(target=open_browser, daemon=True).start()
            
            # Butonları göster
            self.login_buttons_row.visible = True
            self.login_confirm_button.visible = True
            self.login_cancel_button.visible = True
            
            self.page.update()
            self.update_log("Giriş yapın ve ardından 'Tamam' butonuna tıklayın.")
            
        except Exception as e:
            self.update_log(f"Giriş işlemi hatası: {str(e)}")
            self.update_status("Giriş işlemi başarısız!", ft.Colors.RED)
    
    def handle_login_action(self, action):
        """Giriş işlemi buton aksiyonlarını yönetir"""
        try:
            # Butonları gizle
            self.login_buttons_row.visible = False
            self.login_confirm_button.visible = False
            self.login_cancel_button.visible = False
            
            if action == "tamam":
                # Cookie'leri al
                if hasattr(self, 'login_driver') and self.login_driver:
                    self.get_cookies_from_browser(self.login_driver)
                else:
                    self.update_status("Tarayıcı bulunamadı!", ft.Colors.RED)
            else:
                # İptal edildi
                self.update_status("Giriş işlemi iptal edildi", ft.Colors.RED)
                if hasattr(self, 'login_driver') and self.login_driver:
                    try:
                        self.login_driver.quit()
                    except:
                        pass
            
            self.page.update()
            
        except Exception as e:
            self.update_log(f"Buton işlemi hatası: {str(e)}")
    
    def login_process(self):
        """YouTube hesabına giriş yapma işlemi"""
        try:
            # Tarayıcıyı thread'de aç
            def open_browser():
                try:
                    # Selenium WebDriver'ı ayarla - giriş işlemi için for_login=True
                    self.login_driver = self.setup_selenium(for_login=True)
                    if not self.login_driver:
                        self.update_status("Tarayıcı açılamadı!", ft.Colors.RED)
                        return
                    
                    # YouTube ana sayfasına git
                    self.update_log("YouTube ana sayfası açılıyor...")
                    self.login_driver.get("https://www.youtube.com/")
                    
                    # Sayfanın yüklenmesini bekle
                    time.sleep(5)
                    
                    # Kullanıcıya bilgi ver
                    self.update_log("YouTube sayfası açıldı. Lütfen hesabınıza giriş yapın.")
                    
                except Exception as e:
                    self.update_log(f"Tarayıcı açma hatası: {str(e)}")
                    self.update_status("Tarayıcı açılamadı!", ft.Colors.RED)
            
            # Tarayıcıyı thread'de başlat
            threading.Thread(target=open_browser, daemon=True).start()
            
            # Dialog'u ana thread'de göster
            def close_dialog(e, result="iptal"):
                # Dialog'u kapat
                self.page.dialog.open = False
                self.page.update()
                
                if result == "tamam":
                    # Cookie'leri al
                    if hasattr(self, 'login_driver') and self.login_driver:
                        self.get_cookies_from_browser(self.login_driver)
                    else:
                        self.update_status("Tarayıcı bulunamadı!", ft.Colors.RED)
                else:
                    # İptal edildi
                    self.update_status("Giriş işlemi iptal edildi", ft.Colors.RED)
                    if hasattr(self, 'login_driver') and self.login_driver:
                        try:
                            self.login_driver.quit()
                        except:
                            pass
            
            # Dialog oluştur ve göster
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("YouTube Hesap Girişi", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Text(
                        "Lütfen açılan tarayıcıda YouTube hesabınıza giriş yapın.\n\n"
                        "Giriş yaptıktan sonra 'Tamam' butonuna tıklayın.",
                        size=14
                    ),
                    padding=ft.padding.all(10),
                    width=400,
                    height=100
                ),
                actions=[
                    ft.TextButton(
                        "İptal", 
                        on_click=lambda e: close_dialog(e, "iptal"),
                        style=ft.ButtonStyle(color=ft.Colors.RED)
                    ),
                    ft.TextButton(
                        "Tamam", 
                        on_click=lambda e: close_dialog(e, "tamam"),
                        style=ft.ButtonStyle(color=ft.Colors.GREEN)
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Dialog'u göster
            self.page.dialog = dialog
            self.page.dialog.open = True
            self.page.update()
            
            # Dialog'un açıldığını logla
            self.update_log("Giriş dialog'u açıldı. Lütfen tarayıcıda giriş yapın.")
            
        except Exception as e:
            self.update_log(f"Giriş işlemi hatası: {str(e)}")
            self.update_status("Giriş işlemi başarısız!", ft.Colors.RED)
    
    def get_cookies_from_browser(self, driver):
        """Tarayıcıdan cookie'leri alır ve kaydeder"""
        try:
            # Cookie'leri al
            cookies = driver.get_cookies()
            
            if not cookies:
                self.update_log("Cookie'ler alınamadı!")
                self.update_status("Cookie'ler alınamadı!", ft.Colors.RED)
                driver.quit()
                return
            
            # Cookie'leri sakla
            self.youtube_cookies = cookies
            
            # Cookie'leri dosyaya kaydet (kalıcı saklama için)
            try:
                import json
                # Cookie klasörünü oluştur
                cookie_dir = "cookie"
                if not os.path.exists(cookie_dir):
                    os.makedirs(cookie_dir)
                
                cookie_file = os.path.join(cookie_dir, "youtube_cookies.json")
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                self.update_log(f"Cookie'ler {cookie_file} dosyasına kaydedildi")
            except Exception as save_error:
                self.update_log(f"Cookie kaydetme hatası: {str(save_error)}")
            
            # Cookie bilgilerini logla
            self.update_log(f"{len(cookies)} adet cookie alındı")
            
            # Cookie durumunu güncelle
            self.update_cookie_status()
            
            # Kullanıcıya bilgi ver
            self.update_status("YouTube hesabına başarıyla giriş yapıldı!", ft.Colors.GREEN)
            self.update_log("Cookie'ler kaydedildi. Artık tüm işlemler bu cookie'ler ile yapılacak.")
            
            # Tarayıcıyı kapat
            driver.quit()
            
            # UI güncelle
            self.page.update()
            
        except Exception as e:
            self.update_log(f"Cookie alma hatası: {str(e)}")
            self.update_status("Cookie'ler alınamadı!", ft.Colors.RED)
            try:
                driver.quit()
            except:
                pass
    
    def download_video(self, video_data, output_folder):
        """Tek bir videoyu indir - video başlığını dosya adı olarak kullan"""
        try:
            # video_data string (URL) veya dictionary olabilir
            if isinstance(video_data, str):
                video_url = video_data
            else:
                video_url = video_data.get('video_url') or video_data.get('url')
            
            if not video_url:
                return None
            
            # MP3 olarak indirme kontrolü
            if self.convert_to_mp3_checkbox.value:
                self.add_log(f"MP3 olarak indiriliyor: {video_url}")
                downloaded_path = self.scraper.download_video_as_mp3(video_url, output_folder)
            else:
                self.add_log(f"Video indiriliyor: {video_url}")
                downloaded_path = self.scraper.download_video(video_url, output_folder)
            
            # Canlı yayın kontrolü - eğer None döndüyse ve log'da canlı yayın mesajı varsa atla
            if downloaded_path is None:
                # Son log mesajlarını kontrol et (canlı yayın hatası için)
                return None
            
            if downloaded_path and os.path.exists(downloaded_path):
                filename = os.path.basename(downloaded_path)
                if self.convert_to_mp3_checkbox.value:
                    self.add_log(f"MP3 başarıyla indirildi: {filename}")
                else:
                    self.add_log(f"Video başarıyla indirildi: {filename}")
                return downloaded_path
            else:
                self.add_log(f"İndirme başarısız: {video_url}")
                return None
                
        except Exception as e:
            self.add_log(f"İndirme hatası: {str(e)}")
            return None
            
    # Müzik seçme fonksiyonu kaldırıldı

def main():
    app = YouTubeBulkDownloaderApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()