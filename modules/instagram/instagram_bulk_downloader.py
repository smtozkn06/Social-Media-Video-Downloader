import flet as ft
import os
import sys
import threading
import time
import re
import shutil

# Ana dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.instagram.instagram_scraper import InstagramScraper
from modules.instagram.instagram_http_downloader import InstagramHttpDownloader
from video_processor import VideoProcessor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from pathlib import Path

class InstagramBulkDownloaderApp:
    def __init__(self):
        # UI bileşenlerini başlat
        self.log_text = None
        self.page = None
        
        self.scraper = InstagramScraper(log_callback=self.add_log, bulk_downloader=self, use_http=False)
        self.video_processor = VideoProcessor()
        self.http_downloader = InstagramHttpDownloader(log_callback=self.add_log)
        self.is_downloading = False
        self.instagram_cookies = None
        
        # Kaydedilmiş cookie'leri yükle
        self.load_saved_cookies()
        
        # HTTP downloader'a cookie'leri aktar
        self._sync_cookies_to_http_downloader()
    
    def _sync_cookies_to_http_downloader(self):
        """Cookie'leri tüm HTTP downloader'lara senkronize eder"""
        try:
            if self.instagram_cookies:
                # Ana HTTP downloader'a cookie'leri aktar
                if self.http_downloader:
                    self.http_downloader.set_cookies(self.instagram_cookies)
                
                # Scraper'daki HTTP downloader'a da cookie'leri aktar
                if hasattr(self.scraper, 'http_downloader') and self.scraper.http_downloader:
                    self.scraper.http_downloader.set_cookies(self.instagram_cookies)
                    
                print(f"🔄 Cookie'ler HTTP downloader'lara senkronize edildi")
            else:
                print("⚠️ Senkronize edilecek cookie bulunamadı")
        except Exception as e:
            print(f"⚠️ Cookie senkronizasyon hatası: {str(e)}")
    

    
    def load_saved_cookies(self):
        """Kaydedilmiş cookie'leri dosyadan yükler"""
        try:
            import json
            # Cookie klasörünü oluştur
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            self.cookie_file = os.path.join(cookie_dir, "instagram_cookies.json")
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Dosya boş değilse
                        self.instagram_cookies = json.loads(content)
                        if self.instagram_cookies and len(self.instagram_cookies) > 0:
                            print(f"Kaydedilmiş {len(self.instagram_cookies)} adet cookie yüklendi")
                            # HTTP downloader'lara cookie'leri senkronize et
                            self._sync_cookies_to_http_downloader()
                        else:
                            print("Cookie dosyası boş")
                            self.instagram_cookies = {}
                    else:
                        print("Cookie dosyası boş")
                        self.instagram_cookies = {}
                
                self.update_cookie_status()
            else:
                print("Kaydedilmiş cookie dosyası bulunamadı")
                self.instagram_cookies = {}
                self.update_cookie_status()
        except Exception as e:
            print(f"Cookie yükleme hatası: {str(e)}")
            self.instagram_cookies = {}
            self.update_cookie_status()
    
    def update_cookie_status(self):
        """Cookie durumunu güncelle"""
        try:
            if hasattr(self, 'cookie_status_text'):
                # Önce memory'deki cookie'leri kontrol et
                if self.instagram_cookies and len(self.instagram_cookies) > 0:
                    # Önemli cookie'lerin varlığını kontrol et
                    important_cookies = ['sessionid', 'csrftoken']
                    has_important_cookies = any(cookie in self.instagram_cookies for cookie in important_cookies)
                    
                    if has_important_cookies:
                        self.cookie_status_text.value = "Instagram hesabı bağlı ✅"
                        self.cookie_status_text.color = ft.Colors.GREEN_600
                    else:
                        self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                        self.cookie_status_text.color = ft.Colors.RED_600
                else:
                    # Memory'de cookie yoksa dosyayı kontrol et
                    cookie_file = getattr(self, 'cookie_file', os.path.join("cookie", "instagram_cookies.json"))
                    
                    if os.path.exists(cookie_file):
                        try:
                            import json
                            with open(cookie_file, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content:
                                    cookies = json.loads(content)
                                    if cookies and len(cookies) > 0:
                                        # Önemli cookie'lerin varlığını kontrol et
                                        important_cookies = ['sessionid', 'csrftoken']
                                        has_important_cookies = any(cookie in cookies for cookie in important_cookies)
                                        
                                        if has_important_cookies:
                                            self.cookie_status_text.value = "Instagram hesabı bağlı ✅"
                                            self.cookie_status_text.color = ft.Colors.GREEN_600
                                            # Memory'ye de yükle
                                            self.instagram_cookies = cookies
                                        else:
                                            self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                                            self.cookie_status_text.color = ft.Colors.RED_600
                                    else:
                                        self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                                        self.cookie_status_text.color = ft.Colors.RED_600
                                else:
                                    self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                                    self.cookie_status_text.color = ft.Colors.RED_600
                        except:
                            self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                            self.cookie_status_text.color = ft.Colors.RED_600
                    else:
                        self.cookie_status_text.value = "Instagram hesabı bağlı değil ❌"
                        self.cookie_status_text.color = ft.Colors.RED_600
                
                if hasattr(self, 'page') and self.page:
                    self.page.update()
        except Exception as e:
            print(f"Cookie durumu güncelleme hatası: {e}")
    
    def login_to_instagram(self, e):
        """Instagram hesabına giriş yap"""
        try:
            # Giriş butonlarını göster
            self.login_buttons_row.visible = True
            self.page.update()
            
            # Yeni thread'de tarayıcıyı aç
            import threading
            login_thread = threading.Thread(target=self.start_login_process)
            login_thread.daemon = True
            login_thread.start()
            
        except Exception as e:
            print(f"Instagram giriş hatası: {e}")
            self.add_log(f"❌ Instagram giriş hatası: {e}")
    
    def start_login_process(self):
        """Giriş sürecini başlat - Selenium tarayıcısı ile"""
        try:
            self.add_log("🔐 Instagram giriş tarayıcısı açılıyor...")
            self.add_log("💡 Açılan tarayıcıda Instagram'a giriş yapın ve ardından 'Tamam' butonuna tıklayın.")
            
            # Selenium WebDriver'ı başlat
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            import time
            
            # Chrome seçenekleri
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Headless modu kontrol et
            if hasattr(self, 'headless_mode_checkbox') and self.headless_mode_checkbox.value:
                chrome_options.add_argument("--headless")
            
            # WebDriver'ı başlat
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Instagram ana sayfasına git (cookie'leri yüklemek için)
            self.driver.get("https://www.instagram.com/")
            
            # Mevcut cookie'leri tarayıcıya entegre et
            self.add_log(f"🔍 Cookie durumu kontrol ediliyor...")
            self.add_log(f"📊 hasattr(self, 'instagram_cookies'): {hasattr(self, 'instagram_cookies')}")
            if hasattr(self, 'instagram_cookies'):
                self.add_log(f"📊 self.instagram_cookies: {bool(self.instagram_cookies)}")
                if self.instagram_cookies:
                    self.add_log(f"📊 Cookie sayısı: {len(self.instagram_cookies)}")
            
            if hasattr(self, 'instagram_cookies') and self.instagram_cookies:
                self.add_log(f"🍪 Mevcut {len(self.instagram_cookies)} adet cookie tarayıcıya entegre ediliyor...")
                
                successful_cookies = 0
                # Cookie'leri tarayıcıya ekle
                for cookie_name, cookie_value in self.instagram_cookies.items():
                    try:
                        self.driver.add_cookie({
                            'name': cookie_name,
                            'value': cookie_value,
                            'domain': '.instagram.com'
                        })
                        successful_cookies += 1
                        self.add_log(f"✅ Cookie eklendi: {cookie_name}")
                    except Exception as e:
                        self.add_log(f"⚠️ Cookie entegrasyon hatası ({cookie_name}): {e}")
                
                self.add_log(f"📊 Toplam {successful_cookies}/{len(self.instagram_cookies)} cookie başarıyla eklendi")
                
                # Sayfayı yenile
                self.add_log("🔄 Sayfa yenileniyor...")
                self.driver.refresh()
                time.sleep(2)
            else:
                self.add_log("⚠️ Entegre edilecek cookie bulunamadı!")
                if not hasattr(self, 'instagram_cookies'):
                    self.add_log("❌ instagram_cookies attribute'u bulunamadı")
                elif not self.instagram_cookies:
                    self.add_log("❌ instagram_cookies boş veya None")
                
            
            # Giriş durumunu kontrol et
            current_url = self.driver.current_url
            if "login" not in current_url:
                self.add_log("✅ Cookie'ler başarıyla entegre edildi - Zaten giriş yapılmış!")
            else:
                self.add_log("⚠️ Giriş gerekli - Giriş sayfasına yönlendiriliyor")
                # Giriş sayfasına yönlendir
                self.driver.get("https://www.instagram.com/accounts/login/")
            
            self.add_log("✅ Tarayıcı açıldı. Lütfen Instagram'a giriş yapın.")
            
        except Exception as e:
            print(f"Tarayıcı açma hatası: {e}")
            self.add_log(f"❌ Tarayıcı açma hatası: {e}")
            self.add_log("💡 Chrome tarayıcısının yüklü olduğundan emin olun.")
    
    def handle_login_action(self, action):
        """Giriş işlemi buton aksiyonlarını yönet - Selenium ile"""
        try:
            import json
            if action == "tamam":
                # Tarayıcıdan cookie'leri al
                if hasattr(self, 'driver') and self.driver:
                    try:
                        # Önce mevcut URL'yi kontrol et
                        current_url = self.driver.current_url
                        self.add_log(f"🔍 Mevcut sayfa: {current_url}")
                        
                        # Instagram sayfasında olup olmadığını kontrol et
                        if "instagram.com" not in current_url:
                            self.add_log("⚠️ Instagram sayfasında değilsiniz. Instagram'a yönlendiriliyor...")
                            self.driver.get("https://www.instagram.com/")
                            import time
                            time.sleep(3)
                        
                        # Tarayıcıdan tüm cookie'leri al
                        cookies = self.driver.get_cookies()
                        self.add_log(f"🍪 Tarayıcıdan {len(cookies)} adet cookie alındı")
                        
                        # Cookie'leri Instagram formatına çevir
                        instagram_cookies = {}
                        for cookie in cookies:
                            instagram_cookies[cookie['name']] = cookie['value']
                        
                        # Önemli cookie'lerin varlığını kontrol et
                        important_cookies = ['sessionid', 'csrftoken', 'ds_user_id']
                        missing_cookies = [c for c in important_cookies if c not in instagram_cookies]
                        
                        if missing_cookies:
                            self.add_log(f"⚠️ Eksik önemli cookie'ler: {', '.join(missing_cookies)}")
                            self.add_log("💡 Lütfen tarayıcıda Instagram'a giriş yaptığınızdan emin olun.")
                        
                        # Cookie dosyasını kaydet
                        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
                        with open(self.cookie_file, 'w', encoding='utf-8') as f:
                            json.dump(instagram_cookies, f, indent=2, ensure_ascii=False)
                        
                        # Cookie'leri yükle
                        self.instagram_cookies = instagram_cookies
                        self.add_log(f"✅ {len(instagram_cookies)} adet cookie başarıyla kaydedildi!")
                        self.add_log("📝 Cookie dosyası güncellendi: cookie/instagram_cookies.json")
                        
                        # Önemli cookie'leri logla
                        if 'sessionid' in instagram_cookies:
                            sessionid_preview = instagram_cookies['sessionid'][:20] + "..."
                            self.add_log(f"🔑 SessionID: {sessionid_preview}")
                        
                        # Tarayıcıyı kapat
                        self.driver.quit()
                        self.driver = None
                        
                        # Cookie durumunu güncelle
                        self.update_cookie_status()
                        
                    except Exception as e:
                        self.add_log(f"❌ Cookie alma hatası: {e}")
                        self.add_log("💡 Lütfen tarayıcıda Instagram'a giriş yaptığınızdan emin olun.")
                        # Hata durumunda da tarayıcıyı kapat
                        try:
                            if hasattr(self, 'driver') and self.driver:
                                self.driver.quit()
                                self.driver = None
                        except:
                            pass
                else:
                    self.add_log("❌ Tarayıcı bulunamadı. Lütfen önce giriş butonuna tıklayın.")
            
            elif action == "iptal":
                # Tarayıcıyı kapat
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                        self.driver = None
                    except:
                        pass
                self.add_log("Instagram giriş işlemi iptal edildi.")
            
            # Giriş butonlarını gizle
            self.login_buttons_row.visible = False
            self.page.update()
            
        except Exception as e:
            print(f"Giriş işlemi hatası: {e}")
            self.add_log(f"❌ Giriş işlemi hatası: {e}")
            
            # Hata durumunda da butonları gizle
            self.login_buttons_row.visible = False
            self.page.update()
    
    # Otomatik çerez alma fonksiyonu kaldırıldı
        
    def main(self, page: ft.Page):
        page.title = "Instagram Toplu Video İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 800
        page.window_height = 900
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.search_field = ft.TextField(
            label="Hashtag Arama",
            hint_text="Örn: komedi, travel, food (sadece kelime girin, # işareti gereksiz)",
            width=500,
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.profile_url_field = ft.TextField(
            label="Profil URL'si",
            hint_text="Örn: https://www.instagram.com/username",
            width=500,
            prefix_icon=ft.Icons.PERSON
        )
        

        
        # Video sayısı alanı
        self.video_count_field = ft.TextField(
            label="İndirilecek Gönderi Sayısı",
            hint_text="1-50 arası bir sayı girin",
            value="10",
            width=200,
            prefix_icon=ft.Icons.NUMBERS,
            visible=True
        )
        
        # İndirme modu seçimi
        self.download_mode = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="hashtag", label="Hashtag ile İndir"),
                ft.Radio(value="profile", label="Profil URL'si ile İndir"),
                ft.Radio(value="txt_file", label="TXT Dosyasından Toplu İndir")
            ]),
            value="hashtag",
            on_change=self.on_download_mode_change
        )
        
        # İndirme yöntemi seçimi
        self.download_method = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="http", label="HTTP API ile indir (Hızlı ve güvenilir)")
            ]),
            value="http",
            on_change=self.on_download_method_change
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
        
        # Profil içerik türü seçimi
        self.profile_content_type = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="posts", label="Gönderi İndir"),
                ft.Radio(value="reels", label="Reels İndir")
            ]),
            value="posts",
            visible=False
        )
        
        # Başlangıçta profil URL ve TXT dosyası alanlarını gizle
        self.profile_url_field.visible = True
        
        # Headless mod checkbox'ı
        self.headless_mode_checkbox = ft.Checkbox(
            label="Headless Mod (Tarayıcıyı Gizle)",
            value=True,
            visible=True,
            tooltip="Tarayıcı penceresini gizleyerek daha hızlı çalışır"
        )
        
        # CAPTCHA açıklaması
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
            value=True,
            on_change=self.on_logo_checkbox_change
        )
        

        
        self.logo_file_field = ft.TextField(
            label="Logo Dosyası (.png)",
            width=400,
            read_only=True,
            visible=True
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
        
        self.logo_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=True
        )
        
        self.txt_file_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.TEXT_SNIPPET,
            on_click=lambda _: txt_file_picker.pick_files(
                allowed_extensions=["txt"]
            ),
            visible=False
        )
        
        # TXT dosyası container'ı
        self.txt_file_container = ft.Container(
            content=ft.Column([
                ft.Text("TXT Dosyası", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.txt_file_field,
                    self.txt_file_button
                ])
            ]),
            padding=10,
            margin=ft.margin.only(bottom=10),
            visible=False
        )
        
        # İndirme butonu
        self.download_button = ft.ElevatedButton(
            "Toplu İndirmeyi Başlat",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.start_bulk_download,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE
            )
        )
        
        # Durdurma butonu
        self.stop_button = ft.ElevatedButton(
            "Durdur",
            icon=ft.Icons.STOP,
            on_click=self.stop_download,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED,
                color=ft.Colors.WHITE
            )
        )
        
        # İlerleme çubuğu
        self.progress_bar = ft.ProgressBar(
            width=500,
            visible=False
        )
        
        # Durum metni
        self.status_text = ft.Text(
            "",
            size=14,
            color=ft.Colors.BLUE_700
        )
        
        # İstatistik metni
        self.stats_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREEN_700
        )
        
        # Log metni
        self.log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_700,
            selectable=True
        )
        
        # Instagram hesap giriş bölümü için UI bileşenleri
        self.cookie_status_text = ft.Text(
            "Instagram hesabı bağlı değil", 
            size=14, 
            color=ft.Colors.RED_600
        )
        
        # UI oluşturulduktan sonra cookie durumunu güncelle
        self.update_cookie_status()
        
        login_button = ft.ElevatedButton(
            text="Instagram Hesabına Giriş Yap",
            icon=ft.Icons.LOGIN,
            on_click=self.login_to_instagram,
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
            visible=True,
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
            visible=True,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600
            )
        )
        
        # Giriş butonları satırı
        self.login_buttons_row = ft.Row([
            self.login_confirm_button,
            self.login_cancel_button
        ], spacing=10, visible=True)
        
        # Otomatik çerez alma butonu kaldırıldı

        # Ana layout
        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Instagram Toplu Video İndirici",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700
                        ),
                        ft.Text(
                            "Instagram videolarını toplu olarak indirin",
                            size=14,
                            color=ft.Colors.GREY_600
                        )
                    ]),
                    padding=20,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # Instagram hesap giriş bölümü
                ft.Container(
                    content=ft.Column([
                        ft.Text("Instagram Hesap Ayarları", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "CAPTCHA sorunlarını önlemek için Instagram hesabınıza giriş yapın.",
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
                    border=ft.border.all(1, ft.Colors.BLUE_300),
                    margin=ft.margin.only(bottom=20)
                ),
                
                # İndirme modu seçimi
                ft.Container(
                    content=ft.Column([
                        ft.Text("İndirme Modu", size=16, weight=ft.FontWeight.BOLD),
                        self.download_mode
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # İndirme yöntemi seçimi
                ft.Container(
                    content=ft.Column([
                        ft.Text("İndirme Yöntemi", size=16, weight=ft.FontWeight.BOLD),
                        self.download_method
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Hashtag arama
                ft.Container(
                    content=ft.Column([
                        ft.Text("Hashtag Arama", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(
                                "⚠️ Not: Hashtag ile indirme modunda sadece fotoğraflar indirilir, reels ve videolar dahil değildir.",
                                size=12,
                                color=ft.Colors.ORANGE_700,
                                italic=True
                            ),
                            padding=ft.padding.only(bottom=10),
                            bgcolor=ft.Colors.ORANGE_50,
                            border_radius=5,
                            border=ft.border.all(1, ft.Colors.ORANGE_300)
                        ),
                        self.search_field
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Profil URL
                ft.Container(
                    content=ft.Column([
                        ft.Text("Profil URL'si", size=16, weight=ft.FontWeight.BOLD),
                        self.profile_url_field,
                        ft.Container(
                            content=ft.Column([
                                ft.Text("İçerik Türü", size=14, weight=ft.FontWeight.BOLD),
                                self.profile_content_type
                            ]),
                            padding=ft.padding.only(top=10)
                        )
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                

                
                # TXT dosyası
                self.txt_file_container,
                
                # Video sayısı ve paralel indirme
                ft.Container(
                    content=ft.Row([
                        self.video_count_field,
                        ft.Container(width=20),
                        self.parallel_batch_size_field
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Seçenekler
                ft.Container(
                    content=ft.Column([
                        ft.Text("Seçenekler", size=16, weight=ft.FontWeight.BOLD),
                        self.headless_mode_checkbox,
                        self.captcha_warning,
                        self.use_logo_checkbox,
                        ft.Row([
                            self.logo_file_field,
                            self.logo_button
                        ], visible=True)
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Çıktı klasörü
                ft.Container(
                    content=ft.Column([
                        ft.Text("Çıktı Klasörü", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.output_folder_field,
                            ft.ElevatedButton(
                                "Seç",
                                icon=ft.Icons.FOLDER,
                                on_click=lambda _: output_folder_picker.get_directory_path()
                            )
                        ])
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # İndirme butonları
                ft.Container(
                    content=ft.Row([
                        self.download_button,
                        self.stop_button
                    ]),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # İlerleme ve durum
                ft.Container(
                    content=ft.Column([
                        self.progress_bar,
                        self.status_text,
                        self.stats_text,
                        ft.Container(
                            content=self.log_text,
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5,
                            margin=ft.margin.only(top=10)
                        )
                    ]),
                    margin=ft.margin.only(bottom=20)
                )
            ],
            scroll=ft.ScrollMode.AUTO
            )
        )
        
        # Sayfa yüklendikten sonra cookie durumunu güncelle
        self.update_cookie_status()
    
    def on_download_mode_change(self, e):
        """İndirme modu değiştiğinde çağrılır"""
        mode = e.control.value
        
        # Tüm alanları gizle
        self.search_field.visible = False
        self.profile_url_field.visible = False
        self.video_count_field.visible = False
        self.headless_mode_checkbox.visible = False
        self.captcha_warning.visible = False
        self.profile_content_type.visible = False
        
        # TXT dosyası container'ını ve bileşenlerini gizle
        self.txt_file_container.visible = False
        self.txt_file_field.visible = False
        self.txt_file_button.visible = False
        
        # Seçilen moda göre alanları göster
        if mode == "hashtag":
            self.search_field.visible = True
            self.video_count_field.visible = True
            self.headless_mode_checkbox.visible = True
            self.captcha_warning.visible = True
        elif mode == "profile":
            self.profile_url_field.visible = True
            self.profile_content_type.visible = True
            self.video_count_field.visible = True
            self.headless_mode_checkbox.visible = True
            self.captcha_warning.visible = True
        elif mode == "txt_file":
            self.txt_file_container.visible = True
            self.txt_file_field.visible = True
            self.txt_file_button.visible = True
        
        self.page.update()
    
    def on_download_method_change(self, e):
        """İndirme yöntemi değiştiğinde çağrılır"""
        # Artık sadece Selenium modu var, özel bir işlem gerekmiyor
        pass
    
    def on_logo_checkbox_change(self, e):
        """Logo checkbox değiştiğinde çağrılır"""
        is_checked = e.control.value
        self.logo_file_field.visible = is_checked
        self.logo_button.visible = is_checked
        
        # Logo row'unu görünür/gizli yap
        logo_row = None
        try:
            # Güvenli bir şekilde kontrolleri dolaş
            for control in self.page.controls:
                if hasattr(control, 'controls'):
                    for sub_control in control.controls:
                        if hasattr(sub_control, 'content') and hasattr(sub_control.content, 'controls'):
                            for inner_control in sub_control.content.controls:
                                if hasattr(inner_control, 'controls'):
                                    for row in inner_control.controls:
                                        if hasattr(row, 'controls') and len(row.controls) >= 2:
                                            if (hasattr(row.controls[0], 'label') and 
                                                row.controls[0].label == "Logo Dosyası (.png)"):
                                                logo_row = row
                                                break
        except Exception as ex:
            print(f"Logo row arama hatası: {ex}")
        
        if logo_row:
            logo_row.visible = is_checked
        
        self.page.update()
    
    def on_logo_file_selected(self, e: ft.FilePickerResultEvent):
        """Logo dosyası seçildiğinde çağrılır"""
        if e.files:
            self.logo_file_field.value = e.files[0].path
            self.page.update()
    
    def on_output_folder_selected(self, e: ft.FilePickerResultEvent):
        """Çıktı klasörü seçildiğinde çağrılır"""
        if e.path:
            self.output_folder_field.value = e.path
            self.page.update()
    
    def on_txt_file_selected(self, e: ft.FilePickerResultEvent):
        """TXT dosyası seçildiğinde çağrılır"""
        if e.files:
            self.txt_file_field.value = e.files[0].path
            self.page.update()
    
    def add_log(self, message):
        """Log mesajı ekler"""
        current_time = time.strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"
        
        # log_text henüz tanımlanmamışsa sadece print yap
        if self.log_text is None:
            print(log_message)
            return
        
        if self.log_text.value:
            self.log_text.value += "\n" + log_message
        else:
            self.log_text.value = log_message
        
        if self.page:
            self.page.update()
    
    def update_status(self, message):
        """Durum metnini günceller"""
        self.status_text.value = message
        self.page.update()
    
    def update_stats(self, message):
        """İstatistik metnini günceller"""
        self.stats_text.value = message
        self.page.update()
    
    def update_progress(self, value):
        """İlerleme çubuğunu günceller"""
        self.progress_bar.value = value
        self.page.update()
    
    def start_bulk_download(self, e):
        """Toplu indirme işlemini başlatır"""
        if self.is_downloading:
            return
        
        mode = self.download_mode.value
        
        if mode == "hashtag":
            search_term = self.search_field.value.strip()
            if not search_term:
                self.add_log("❌ Lütfen bir hashtag girin")
                return
        elif mode == "profile":
            profile_url = self.profile_url_field.value.strip()
            if not profile_url:
                self.add_log("❌ Lütfen bir profil URL'si girin")
                return
            if not self.is_valid_instagram_url(profile_url):
                self.add_log("❌ Geçerli bir Instagram profil URL'si girin")
                return
        elif mode == "story":
            story_username = self.story_username_field.value.strip()
            if not story_username:
                self.add_log("❌ Lütfen bir kullanıcı adı girin")
                return
            # Kullanıcı adı doğrulaması
            if not re.match(r'^[a-zA-Z0-9._]+$', story_username):
                self.add_log("❌ Geçerli bir Instagram kullanıcı adı girin")
                return
        elif mode == "txt_file":
            txt_file = self.txt_file_field.value.strip()
            if not txt_file:
                self.add_log("❌ Lütfen bir TXT dosyası seçin")
                return
            if not os.path.exists(txt_file):
                self.add_log("❌ Seçilen TXT dosyası bulunamadı")
                return
        
        # Video sayısını kontrol et (hikaye modu hariç)
        if mode != "story":
            try:
                video_count = int(self.video_count_field.value)
                if video_count < 1 or video_count > 50:
                    self.add_log("❌ Video sayısı 1-50 arasında olmalıdır")
                    return
            except ValueError:
                self.add_log("❌ Geçerli bir video sayısı girin")
                return
        
        # UI'yi güncelle
        self.is_downloading = True
        self.download_button.visible = False
        self.stop_button.visible = True
        self.progress_bar.visible = True
        self.page.update()
        
        # İndirme işlemini ayrı thread'de başlat
        threading.Thread(target=self.bulk_download_worker, daemon=True).start()
    
    def stop_download(self, e):
        """İndirme işlemini durdurur"""
        self.is_downloading = False
        self.scraper.stop_scraping = True
        self.add_log("🛑 İndirme durduruldu")
        self.update_status("İndirme durduruldu")
        
        # UI'yi sıfırla
        self.download_button.visible = True
        self.stop_button.visible = False
        self.progress_bar.visible = False
        self.page.update()
    
    def is_valid_instagram_url(self, url):
        """Instagram URL'sinin geçerli olup olmadığını kontrol eder"""
        instagram_pattern = r'https?://(www\.)?instagram\.com/[A-Za-z0-9_.]+/?'
        return re.match(instagram_pattern, url) is not None
    
    def bulk_download_worker(self):
        """Toplu indirme işlemini gerçekleştirir - Tamamen HTTP API tabanlı"""
        try:
            # HTTP downloader için sayaçları sıfırla (sadece bir kez)
            self.http_downloader.reset_counters()
            
            mode = self.download_mode.value
            
            if mode == "hashtag":
                video_count = int(self.video_count_field.value)
                search_term = self.search_field.value.strip()
                self.add_log(f"🔍 Instagrapi ile hashtag araması başlatılıyor: {search_term}")
                # Instagrapi ile hashtag arama
                self.download_hashtag_http(search_term, video_count)
                return
                    
            elif mode == "profile":
                video_count = int(self.video_count_field.value)
                profile_url = self.profile_url_field.value.strip()
                content_type = self.profile_content_type.value
                
                if content_type == "posts":
                    self.add_log(f"📝 HTTP API ile profil gönderileri alınıyor: {profile_url}")
                    # HTTP API ile profil gönderileri indirme
                    self.download_profile_posts_http(profile_url, video_count)
                    return
                elif content_type == "reels":
                    self.add_log(f"🎬 HTTP API ile profil reels'leri alınıyor: {profile_url}")
                    # HTTP API ile profil reels indirme
                    self.download_profile_reels_http(profile_url, video_count)
                    return
                else:
                    # Varsayılan olarak tüm profil içeriği
                    self.add_log(f"👤 HTTP API ile profil videoları alınıyor: {profile_url}")
                    self.download_profile_http(profile_url, video_count)
                    return
                    
            elif mode == "txt_file":
                txt_file = self.txt_file_field.value.strip()
                self.add_log(f"📄 TXT dosyasından URL'ler okunuyor: {txt_file}")
                video_urls = self.read_urls_from_txt(txt_file)
                
                if not video_urls:
                    self.add_log("❌ Video bulunamadı")
                    return
                
                self.add_log(f"✅ {len(video_urls)} video bulundu")
                self.update_status(f"{len(video_urls)} video indiriliyor...")
                
                # HTTP API ile paralel indirme
                output_dir = self.output_folder_field.value or "output"
                self.download_videos_parallel_http(video_urls, output_dir)
                return
            
        except Exception as e:
            self.add_log(f"❌ Hata: {str(e)}")
            self.update_status("Hata oluştu")
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.visible = True
            self.stop_button.visible = False
            self.progress_bar.visible = False
            self.page.update()
    
    def read_urls_from_txt(self, txt_file):
        """TXT dosyasından URL'leri okur"""
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f.readlines() if line.strip()]
            return [url for url in urls if self.is_valid_instagram_url(url)]
        except Exception as e:
            self.add_log(f"TXT dosyası okuma hatası: {str(e)}")
            return []
    
    def download_videos_parallel(self, video_urls):
        """Videoları paralel olarak indirir"""
        try:
            batch_size = int(self.parallel_batch_size_field.value)
            if batch_size < 1 or batch_size > 50:
                batch_size = 10
        except:
            batch_size = 10
        
        total_videos = len(video_urls)
        downloaded_count = 0
        failed_count = 0
        
        # Çıktı klasörünü oluştur
        output_dir = self.output_folder_field.value
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Future'ları submit et
            future_to_url = {executor.submit(self.download_single_video, url, output_dir): url 
                           for url in video_urls}
            
            # Sonuçları işle
            for future in as_completed(future_to_url):
                if not self.is_downloading:
                    break
                
                url = future_to_url[future]
                try:
                    success = future.result()
                    if success:
                        downloaded_count += 1
                        self.add_log(f"✅ İndirildi: {url}")
                    else:
                        failed_count += 1
                        self.add_log(f"❌ İndirilemedi: {url}")
                except Exception as e:
                    failed_count += 1
                    self.add_log(f"❌ Hata ({url}): {str(e)}")
                
                # İlerleme güncelle
                progress = (downloaded_count + failed_count) / total_videos
                self.update_progress(progress)
                self.update_stats(f"İndirilen: {downloaded_count}, Başarısız: {failed_count}, Toplam: {total_videos}")
        
        self.add_log(f"🎉 Toplu indirme tamamlandı! İndirilen: {downloaded_count}, Başarısız: {failed_count}")
        self.update_status("Toplu indirme tamamlandı")
    
    def download_hashtag_http(self, hashtag, count):
        """Tarayıcı ile hashtag arama ve HTTP ile indirme"""
        try:
            import os
            import time
            
            output_dir = self.output_folder_field.value or "downloads"
            
            self.add_log(f"🌐 Tarayıcı ile hashtag araması başlatılıyor: {hashtag}")
            
            # Tarayıcı ile hashtag arama
            post_urls = self.scraper.search_videos(hashtag, count)
            
            if not post_urls:
                self.add_log(f"❌ #{hashtag} hashtag'inde gönderi bulunamadı")
                return
            
            self.add_log(f"✅ #{hashtag} hashtag'inde {len(post_urls)} gönderi bulundu")
            
            # Çıktı klasörünü oluştur
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # HTTP downloader için sayaçları sıfırla
            self.http_downloader.reset_counters()
            
            # Gönderileri HTTP ile indir
            downloaded_count = 0
            for i, post_url in enumerate(post_urls):
                try:
                    if not self.is_downloading:
                        break
                        
                    self.update_progress((i + 1) / len(post_urls))
                    
                    self.add_log(f"📥 Gönderi {i+1}/{len(post_urls)} indiriliyor: {post_url}")
                    
                    # HTTP ile gönderiyi indir
                    success = self.http_downloader.download_post(post_url, output_dir)
                    
                    if success:
                        downloaded_count += 1
                        self.add_log(f"✅ Gönderi {i+1} başarıyla indirildi")
                    else:
                        self.add_log(f"❌ Gönderi {i+1} indirilemedi")
                    
                    # Kısa bekleme
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.add_log(f"❌ Gönderi {i+1} indirme hatası: {str(e)}")
                    continue
            
            # İndirme işlemini tamamla
            if downloaded_count > 0:
                self.add_log(f"✅ #{hashtag} hashtag'inden {downloaded_count} gönderi başarıyla indirildi")
            else:
                self.add_log(f"❌ #{hashtag} hashtag'inden hiç gönderi indirilemedi")
            
            self.update_progress(1.0)
            self.add_log(f"🎯 #{hashtag} hashtag indirme işlemi tamamlandı")
                
        except Exception as e:
            self.add_log(f"❌ Hashtag indirme hatası: {str(e)}")
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.visible = True
            self.stop_button.visible = False
            self.progress_bar.visible = False
            self.page.update()
    
    def download_profile_http(self, profile_url, count):
        """Instagram Private API ile profil arama ve indirme"""
        try:
            from instagrapi import Client
            import re
            import os
            import time
            
            output_dir = self.output_folder_field.value or "downloads"
            
            # Profil URL'sinden kullanıcı adını çıkar
            username_match = re.search(r'instagram\.com/([^/?]+)', profile_url)
            if not username_match:
                self.add_log("❌ Geçersiz profil URL'si")
                return
            
            username = username_match.group(1)
            self.add_log(f"👤 Instagram Private API ile profil araması: {username}")
            self.add_log("🔄 Instagram Private API kullanılıyor...")
            
            # Instagram Private API client oluştur
            cl = Client()
            
            # Çerezleri yükle
            if self.instagram_cookies:
                try:
                    # Çerezleri dictionary'e dönüştür
                    cookie_dict = {}
                    
                    # Çerez formatını kontrol et
                    if isinstance(self.instagram_cookies, str):
                        # String formatında ise JSON olarak parse et
                        import json
                        cookies_data = json.loads(self.instagram_cookies)
                    else:
                        cookies_data = self.instagram_cookies
                    
                    # Liste formatında çerezleri işle
                    if isinstance(cookies_data, list):
                        for cookie in cookies_data:
                            if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                                cookie_dict[cookie['name']] = cookie['value']
                    elif isinstance(cookies_data, dict):
                        # Eğer zaten dictionary formatındaysa direkt kullan
                        cookie_dict = cookies_data
                    
                    self.add_log(f"🍪 {len(cookie_dict)} adet çerez yüklendi")
                    
                    # Session ID'yi al ve decode et
                    sessionid = cookie_dict.get('sessionid')
                    if not sessionid:
                        self.add_log("❌ Session ID bulunamadı - giriş yapmanız gerekiyor")
                        return
                    
                    import urllib.parse
                    sessionid_decoded = urllib.parse.unquote(sessionid)
                    
                    # İnstagrapi settings formatında çerezleri hazırla
                    settings = {
                        "cookies": {
                            "sessionid": sessionid_decoded,
                            "csrftoken": cookie_dict.get('csrftoken', ''),
                            "ds_user_id": cookie_dict.get('ds_user_id', ''),
                            "mid": cookie_dict.get('mid', ''),
                            "ig_did": cookie_dict.get('ig_did', ''),
                            "ig_nrcb": cookie_dict.get('ig_nrcb', ''),
                            "rur": cookie_dict.get('rur', ''),
                            "datr": cookie_dict.get('datr', ''),
                            "shbid": cookie_dict.get('shbid', ''),
                            "shbts": cookie_dict.get('shbts', '')
                        }
                    }
                    
                    # Settings'i client'a yükle
                    cl.set_settings(settings)
                    
                    # Giriş durumunu kontrol et
                    try:
                        # Timeline feed'i alarak giriş durumunu test et
                        cl.get_timeline_feed()
                        self.add_log("✅ Çerezler ile giriş başarılı")
                    except Exception as e:
                        self.add_log(f"⚠️ Çerez girişi başarısız: {str(e)}")
                        # Sessionid ile doğrudan giriş dene
                        try:
                            cl = Client()  # Yeni client oluştur
                            cl.login_by_sessionid(sessionid_decoded)
                            self.add_log("✅ Session ID ile giriş başarılı")
                        except Exception as e2:
                            self.add_log(f"❌ Giriş başarısız: {str(e2)}")
                            self.add_log("💡 İpucu: Tarayıcıdan Instagram'a giriş yapıp çerezleri yenileyin")
                            return
                        
                except Exception as e:
                    self.add_log(f"❌ Çerez yükleme hatası: {str(e)}")
                    return
            else:
                self.add_log("❌ Çerez bulunamadı - önce giriş yapmanız gerekiyor")
                return
            
            # Kullanıcı bilgilerini al
            try:
                self.add_log(f"🔍 @{username} profili aranıyor...")
                
                # Kullanıcı ID'sini al
                user_id = cl.user_id_from_username(username)
                
                # Kullanıcı bilgilerini al
                user_info = cl.user_info(user_id)
                
                if user_info:
                    # Profil bilgilerini göster
                    full_name = user_info.full_name or ''
                    followers = user_info.follower_count or 0
                    posts_count = user_info.media_count or 0
                    is_private = user_info.is_private
                    
                    self.add_log(f"✅ Profil bulundu: {full_name} (@{username})")
                    self.add_log(f"📊 Takipçi: {followers:,} | Gönderi: {posts_count:,}")
                    
                    if is_private:
                        self.add_log("🔒 Bu profil gizli - gönderiler görüntülenemez")
                        return
                    
                    # Kullanıcının medyalarını al
                    self.add_log(f"📥 {count} gönderi indiriliyor...")
                    
                    # Kullanıcının medyalarını al (sayfa sayfa)
                    medias = cl.user_medias(user_id, amount=count)
                    
                    if medias:
                        self.add_log(f"📊 {len(medias)} gönderi bulundu")
                        
                        downloaded_files = []
                        
                        for i, media in enumerate(medias):
                            if not self.is_downloading:
                                break
                            
                            try:
                                # Medya tipini kontrol et
                                media_type = media.media_type
                                pk = media.pk
                                
                                if media_type == 1:  # Fotoğraf
                                    # Fotoğraf indir
                                    file_path = cl.photo_download(pk, output_dir)
                                    if file_path:
                                        downloaded_files.append(file_path)
                                        self.add_log(f"📸 Fotoğraf indirildi: {os.path.basename(file_path)}")
                                        
                                elif media_type == 2:  # Video
                                    # Video indir
                                    file_path = cl.video_download(pk, output_dir)
                                    if file_path:
                                        downloaded_files.append(file_path)
                                        self.add_log(f"🎥 Video indirildi: {os.path.basename(file_path)}")
                                        
                                elif media_type == 8:  # Carousel (Çoklu medya)
                                    # Carousel medyalarını indir
                                    files = cl.album_download(pk, output_dir)
                                    if files:
                                        downloaded_files.extend(files)
                                        for file in files:
                                            self.add_log(f"📁 Album medyası indirildi: {os.path.basename(file)}")
                                
                                # İlerleme güncelle
                                progress = (i + 1) / len(medias)
                                self.update_progress(progress)
                                
                                # Rate limiting
                                time.sleep(2)  # Instagram API rate limit için
                                
                            except Exception as e:
                                self.add_log(f"❌ Medya indirme hatası: {str(e)}")
                                continue
                        
                        if downloaded_files:
                            self.add_log(f"🎉 Toplam {len(downloaded_files)} dosya indirildi")
                            self.add_log(f"📂 Dosyalar: {output_dir} klasörüne kaydedildi")
                        else:
                            self.add_log("❌ Hiçbir dosya indirilemedi")
                    else:
                        self.add_log(f"❌ @{username} profilinde gönderi bulunamadı")
                else:
                    self.add_log(f"❌ @{username} profili bulunamadı")
                    
            except Exception as e:
                self.add_log(f"❌ Profil arama hatası: {str(e)}")
                if "login_required" in str(e).lower():
                    self.add_log("💡 İpucu: Giriş yapmanız gerekiyor")
                elif "challenge_required" in str(e).lower():
                    self.add_log("💡 İpucu: Instagram güvenlik kontrolü - tarayıcıdan giriş yapın")
                elif "rate limit" in str(e).lower():
                    self.add_log("💡 İpucu: Çok fazla istek - birkaç dakika bekleyin")
                elif "user not found" in str(e).lower():
                    self.add_log("💡 İpucu: Kullanıcı adını kontrol edin")
                
        except ImportError:
            self.add_log("❌ instagrapi kütüphanesi bulunamadı")
            self.add_log("💡 İpucu: pip install instagrapi komutuyla yükleyin")
        except Exception as e:
            self.add_log(f"❌ Profil indirme hatası: {str(e)}")
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.visible = True
            self.stop_button.visible = False
            self.progress_bar.visible = False
            self.page.update()
    

    
    def download_single_video(self, url, output_dir):
        """Tek bir videoyu HTTP ile indirir"""
        try:
            self.add_log(f"📥 HTTP ile indiriliyor: {url}")
            
            # Cookie'leri HTTP downloader'a aktar
            if self.instagram_cookies:
                self.http_downloader.set_cookies(self.instagram_cookies)
            
            downloaded_files = self.http_downloader.download_from_url(url, output_dir)
            
            if downloaded_files:
                self.add_log(f"✅ {len(downloaded_files)} dosya indirildi")
                
                # İndirilen dosyaları işle
                for file_path in downloaded_files:
                    self.add_log(f"📁 İndirilen: {os.path.basename(file_path)}")
                    
                    # Logo ekleme işlemi
                    if self.use_logo_checkbox.value and self.logo_file_field.value and self.video_processor:
                        try:
                            self.add_log("🎨 Logo ekleniyor...")
                            logo_path = self.logo_file_field.value
                            
                            # Video dosyaları için logo ekleme
                            if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.webm', '.mkv')):
                                processed_file = self.video_processor.add_logo_to_video(
                                    file_path, logo_path, output_dir
                                )
                                
                                if processed_file and os.path.exists(processed_file):
                                    # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    
                                    # İşlenmiş dosyayı orijinal isimle yeniden adlandır
                                    final_file = file_path
                                    if processed_file != final_file:
                                        os.rename(processed_file, final_file)
                                    file_path = final_file
                                    self.add_log("✅ Video'ya logo başarıyla eklendi")
                                else:
                                    self.add_log("⚠️ Video logo ekleme başarısız, orijinal dosya korundu")
                            
                            # Resim dosyaları için logo ekleme
                            elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
                                processed_file = self.video_processor.add_logo_to_image(
                                    file_path, logo_path, output_dir
                                )
                                
                                if processed_file and os.path.exists(processed_file):
                                    # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    
                                    # İşlenmiş dosyayı orijinal isimle yeniden adlandır
                                    final_file = file_path
                                    if processed_file != final_file:
                                        os.rename(processed_file, final_file)
                                    file_path = final_file
                                    self.add_log("✅ Resim'e logo başarıyla eklendi")
                                else:
                                    self.add_log("⚠️ Resim logo ekleme başarısız, orijinal dosya korundu")
                            
                            else:
                                self.add_log("⚠️ Desteklenmeyen dosya formatı için logo eklenemedi")
                                
                        except Exception as logo_error:
                            self.add_log(f"❌ Logo ekleme hatası: {str(logo_error)}")
                            self.add_log("⚠️ Orijinal dosya korundu")
                
                return True
            else:
                self.add_log(f"❌ İçerik indirilemedi: {url}")
                return False
            
        except Exception as e:
            self.add_log(f"❌ İndirme hatası: {str(e)}")
            return False
    
    def download_profile_posts_http(self, profile_url, count):
        """HTTP ile profil gönderilerini indirir - Test dosyasındaki başarılı API yaklaşımı"""
        try:
            import requests
            import json
            import re
            
            output_dir = self.output_folder_field.value or "downloads"
            
            # Profil URL'sinden kullanıcı adını çıkar
            username_match = re.search(r'instagram\.com/([^/?]+)', profile_url)
            if not username_match:
                self.add_log("❌ Geçersiz profil URL'si")
                return
            
            username = username_match.group(1)
            self.add_log(f"📸 HTTP API ile profil gönderileri: {username}")
            self.add_log(f"📊 Maksimum gönderi: {count}")
            
            # Instagram API headers (test dosyasından)
            headers = {
                "x-ig-app-id": "936619743392459",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "*/*",
            }
            
            # Instagram API endpoint
            self.add_log("📱 Instagram API ile profil gönderileri alınıyor...")
            api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    user_data = data.get('data', {}).get('user', {})
                    
                    if user_data:
                        # Profil bilgilerini göster (test dosyasındaki gibi)
                        self.add_log(f"✅ Kullanıcı bilgisi alındı")
                        self.add_log(f"📝 Tam ad: {user_data.get('full_name', 'N/A')}")
                        self.add_log(f"👥 Takipçi: {user_data.get('edge_followed_by', {}).get('count', 'N/A')}")
                        self.add_log(f"👤 Takip edilen: {user_data.get('edge_follow', {}).get('count', 'N/A')}")
                        self.add_log(f"📊 Gönderi sayısı: {user_data.get('edge_owner_to_timeline_media', {}).get('count', 'N/A')}")
                        self.add_log(f"🔒 Gizli hesap: {'Evet' if user_data.get('is_private', False) else 'Hayır'}")
                        self.add_log(f"✅ Doğrulanmış: {'Evet' if user_data.get('is_verified', False) else 'Hayır'}")
                        
                        # Gizli hesap kontrolü
                        if user_data.get('is_private', False):
                            self.add_log("🔒 Bu hesap gizli, gönderiler görüntülenemez")
                            return
                        
                        # Son gönderileri al
                        timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                        edges = timeline_media.get('edges', [])
                        
                        if edges:
                            posts_found = edges[:count]
                            self.add_log(f"✅ {len(posts_found)} gönderi bulundu:")
                            
                            for i, edge in enumerate(posts_found, 1):
                                if not self.is_downloading:
                                    break
                                    
                                node = edge.get('node', {})
                                self.add_log(f"\n  {i}. Gönderi:")
                                self.add_log(f"     🔗 Shortcode: {node.get('shortcode', 'N/A')}")
                                self.add_log(f"     📅 Tarih: {node.get('taken_at_timestamp', 'N/A')}")
                                self.add_log(f"     👍 Beğeni: {node.get('edge_liked_by', {}).get('count', 'N/A')}")
                                self.add_log(f"     💬 Yorum: {node.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                                self.add_log(f"     📺 Video: {'Evet' if node.get('is_video', False) else 'Hayır'}")
                                
                                # İndirme işlemi
                                shortcode = node.get('shortcode')
                                if shortcode:
                                    post_url = f"https://www.instagram.com/p/{shortcode}/"
                                    self.add_log(f"📥 İndiriliyor: {shortcode}")
                                    
                                    try:
                                        downloaded_files = self.http_downloader.download_from_url(post_url, output_dir)
                                        if downloaded_files:
                                            self.add_log(f"✅ İndirildi: {len(downloaded_files)} dosya")
                                        else:
                                            self.add_log(f"⚠️ İndirilemedi: {shortcode}")
                                    except Exception as download_error:
                                        self.add_log(f"❌ İndirme hatası: {str(download_error)}")
                                    
                                    # İlerleme güncelle
                                    progress = i / len(posts_found)
                                    self.update_progress(progress)
                                    
                                    # Rate limiting
                                    import time
                                    time.sleep(1)
                            
                            self.add_log(f"\n🎉 Profil gönderileri indirme tamamlandı!")
                        else:
                            self.add_log("❌ Gönderi bulunamadı")
                    else:
                        self.add_log("❌ Kullanıcı verisi bulunamadı")
                        
                except json.JSONDecodeError as e:
                    self.add_log(f"❌ JSON parse hatası: {e}")
            else:
                self.add_log(f"❌ API hatası: {response.status_code}")
                self.add_log(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            self.add_log(f"❌ Profil gönderileri indirme hatası: {str(e)}")
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.visible = True
            self.stop_button.visible = False
            self.progress_bar.visible = False
            self.page.update()
    
    def download_videos_parallel_http(self, video_urls, output_dir):
        """HTTP ile paralel video indirme"""
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import os
            
            if not video_urls:
                self.add_log("❌ İndirilecek video URL'si bulunamadı")
                return
            
            total_videos = len(video_urls)
            self.add_log(f"📥 {total_videos} video paralel olarak indiriliyor...")
            
            downloaded_count = 0
            failed_count = 0
            
            # Paralel indirme için ThreadPoolExecutor kullan
            max_workers = min(3, total_videos)  # Maksimum 3 paralel indirme
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Her URL için indirme görevini başlat
                future_to_url = {}
                for url in video_urls:
                    if not self.is_downloading:
                        break
                    future = executor.submit(self.download_single_video_http, url, output_dir)
                    future_to_url[future] = url
                
                # Sonuçları işle
                for future in as_completed(future_to_url):
                    if not self.is_downloading:
                        break
                    
                    url = future_to_url[future]
                    try:
                        success = future.result()
                        if success:
                            downloaded_count += 1
                            self.add_log(f"✅ İndirildi: {url}")
                        else:
                            failed_count += 1
                            self.add_log(f"❌ İndirilemedi: {url}")
                    except Exception as e:
                        failed_count += 1
                        self.add_log(f"❌ Hata ({url}): {str(e)}")
                    
                    # İlerleme güncelle
                    progress = (downloaded_count + failed_count) / total_videos
                    self.update_progress(progress)
                    self.update_stats(f"İndirilen: {downloaded_count}, Başarısız: {failed_count}, Toplam: {total_videos}")
            
            self.add_log(f"🎉 Paralel indirme tamamlandı! İndirilen: {downloaded_count}, Başarısız: {failed_count}")
            self.update_status("Paralel indirme tamamlandı")
            
        except Exception as e:
            self.add_log(f"❌ Paralel indirme hatası: {str(e)}")
    
    def download_single_video_http(self, video_url, output_dir):
        """HTTP ile tek video indirme"""
        try:
            downloaded_files = self.http_downloader.download_from_url(video_url, output_dir)
            return len(downloaded_files) > 0 if downloaded_files else False
        except Exception as e:
            self.add_log(f"❌ Video indirme hatası: {str(e)}")
            return False
    
    def download_profile_reels_http(self, profile_url, count):
        """HTTP ile profil reels'lerini indirir - Test dosyasındaki başarılı API yaklaşımı"""
        try:
            import requests
            import json
            import re
            
            output_dir = self.output_folder_field.value or "downloads"
            
            # Profil URL'sinden kullanıcı adını çıkar
            username_match = re.search(r'instagram\.com/([^/?]+)', profile_url)
            if not username_match:
                self.add_log("❌ Geçersiz profil URL'si")
                return
            
            username = username_match.group(1)
            self.add_log(f"🎬 HTTP API ile profil reels: {username}")
            self.add_log(f"📊 Maksimum reels: {count}")
            
            # Instagram API headers (test dosyasından)
            headers = {
                "x-ig-app-id": "936619743392459",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "*/*",
            }
            
            # Instagram API endpoint
            self.add_log("📱 Instagram API ile profil reels alınıyor...")
            api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    user_data = data.get('data', {}).get('user', {})
                    
                    if user_data:
                        # Profil bilgilerini göster (test dosyasındaki gibi)
                        self.add_log(f"✅ Kullanıcı bilgisi alındı")
                        self.add_log(f"📝 Tam ad: {user_data.get('full_name', 'N/A')}")
                        self.add_log(f"👥 Takipçi: {user_data.get('edge_followed_by', {}).get('count', 'N/A')}")
                        self.add_log(f"👤 Takip edilen: {user_data.get('edge_follow', {}).get('count', 'N/A')}")
                        self.add_log(f"🔒 Gizli hesap: {'Evet' if user_data.get('is_private', False) else 'Hayır'}")
                        self.add_log(f"✅ Doğrulanmış: {'Evet' if user_data.get('is_verified', False) else 'Hayır'}")
                        
                        # Gizli hesap kontrolü
                        if user_data.get('is_private', False):
                            self.add_log("🔒 Bu hesap gizli, reels görüntülenemez")
                            return
                        
                        # Video olan gönderileri filtrele (reels için)
                        timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                        all_edges = timeline_media.get('edges', [])
                        
                        # Sadece video olan gönderileri al
                        video_edges = [edge for edge in all_edges if edge.get('node', {}).get('is_video', False)]
                        
                        if video_edges:
                            reels_found = video_edges[:count]
                            self.add_log(f"✅ {len(reels_found)} video/reels bulundu:")
                            
                            for i, edge in enumerate(reels_found, 1):
                                if not self.is_downloading:
                                    break
                                    
                                node = edge.get('node', {})
                                self.add_log(f"\n  {i}. Video/Reels:")
                                self.add_log(f"     🔗 Shortcode: {node.get('shortcode', 'N/A')}")
                                self.add_log(f"     📅 Tarih: {node.get('taken_at_timestamp', 'N/A')}")
                                self.add_log(f"     👍 Beğeni: {node.get('edge_liked_by', {}).get('count', 'N/A')}")
                                self.add_log(f"     💬 Yorum: {node.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                                self.add_log(f"     ⏱️ Süre: {node.get('video_duration', 'N/A')} saniye")
                                self.add_log(f"     👀 İzlenme: {node.get('video_view_count', 'N/A')}")
                                
                                # İndirme işlemi
                                shortcode = node.get('shortcode')
                                if shortcode:
                                    # Reels URL'si oluştur
                                    reel_url = f"https://www.instagram.com/reel/{shortcode}/"
                                    self.add_log(f"📥 İndiriliyor: {shortcode}")
                                    
                                    try:
                                        downloaded_files = self.http_downloader.download_from_url(reel_url, output_dir)
                                        if downloaded_files:
                                            self.add_log(f"✅ İndirildi: {len(downloaded_files)} dosya")
                                        else:
                                            self.add_log(f"⚠️ İndirilemedi: {shortcode}")
                                    except Exception as download_error:
                                        self.add_log(f"❌ İndirme hatası: {str(download_error)}")
                                    
                                    # İlerleme güncelle
                                    progress = i / len(reels_found)
                                    self.update_progress(progress)
                                    
                                    # Rate limiting
                                    import time
                                    time.sleep(1)
                            
                            self.add_log(f"\n🎉 Profil reels indirme tamamlandı!")
                        else:
                            self.add_log("❌ Video/reels bulunamadı")
                    else:
                        self.add_log("❌ Kullanıcı verisi bulunamadı")
                        
                except json.JSONDecodeError as e:
                    self.add_log(f"❌ JSON parse hatası: {e}")
            else:
                self.add_log(f"❌ API hatası: {response.status_code}")
                self.add_log(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            self.add_log(f"❌ Profil reels'leri indirme hatası: {str(e)}")
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.visible = True
            self.stop_button.visible = False
            self.progress_bar.visible = False
            self.page.update()


if __name__ == "__main__":
    app = InstagramBulkDownloaderApp()
    ft.app(target=app.main, view=ft.AppView.FLET_APP)