import flet as ft
import os
import threading
import time
import re
import subprocess
import shutil
import sys
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from video_processor import VideoProcessor
from .getMetadata import get_metadata
try:
    from .twitter_scraper import TwitterScraper
    TWITTER_SCRAPER_AVAILABLE = True
except ImportError:
    TWITTER_SCRAPER_AVAILABLE = False
    print("Twitter scraper bulunamadı")

# Twikit ve snscrape import'ları
try:
    from twikit import Client as TwitterClient
    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False

try:
    import snscrape.modules.twitter as sntwitter
    SNSCRAPE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    SNSCRAPE_AVAILABLE = False
    print(f"Snscrape bulunamadı veya uyumsuz: {e}")

class TwitterSingleDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor()
        if TWITTER_SCRAPER_AVAILABLE:
            self.twitter_scraper = TwitterScraper(output_dir="output", debug=False)
        else:
            self.twitter_scraper = None
        self.is_downloading = False
        self.page = None
        # Auth token - bulk downloader'dan alındı
        self.auth_token = "d3e0291592fa280c0e9c6cb8111a42680aeea534"
        # HTTP/API yöntemi varsayılan olarak kullanılıyor
        
    def main(self, page: ft.Page):
        page.title = "Twitter Tekli Video İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 700
        page.window_height = 800
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.url_field = ft.TextField(
            label="Twitter Video URL'si",
            hint_text="Örn: https://twitter.com/username/status/1234567890",
            width=500,
            prefix_icon=ft.Icons.LINK
        )
        
        self.use_logo_checkbox = ft.Checkbox(
            label="Logo Ekle",
            value=True,
            on_change=self.on_logo_checkbox_change
        )
        

        
        # API bilgi metni
        self.api_info_text = ft.Text(
            "📡 Auth Token API yöntemi kullanılıyor (önerilen)",
            color=ft.Colors.GREEN,
            size=14
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
        
        # Dosya seçici
        logo_file_picker = ft.FilePicker(
            on_result=self.on_logo_file_selected
        )
        
        output_folder_picker = ft.FilePicker(
            on_result=self.on_output_folder_selected
        )
        
        page.overlay.extend([logo_file_picker, output_folder_picker])
        
        self.logo_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=True
        )
        
        # İndirme butonu
        self.download_button = ft.ElevatedButton(
            "İndir",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.start_download,
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
        
        # Log metni
        self.log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_700,
            selectable=True
        )
        
        # Ana layout
        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Twitter Tekli Video İndirici",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700
                        ),
                        ft.Text(
                            "Twitter videolarını kolayca indirin",
                            size=14,
                            color=ft.Colors.GREY_600
                        )
                    ]),
                    padding=20,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # URL alanı
                ft.Container(
                    content=ft.Column([
                        ft.Text("Video URL'si", size=16, weight=ft.FontWeight.BOLD),
                        self.url_field
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Seçenekler
                ft.Container(
                    content=ft.Column([
                        ft.Text("Seçenekler", size=16, weight=ft.FontWeight.BOLD),
                        self.api_info_text,
                        self.use_logo_checkbox,
                        ft.Row([
                            self.logo_file_field,
                            self.logo_button
                        ], visible=True),

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
    
    def on_logo_checkbox_change(self, e):
        """Logo checkbox değiştiğinde çağrılır"""
        is_checked = e.control.value
        self.logo_file_field.visible = is_checked
        self.logo_button.visible = is_checked
        
        # Logo row'unu görünür/gizli yap
        logo_row = None
        for control in self.page.controls[0].controls:
            if hasattr(control, 'content') and hasattr(control.content, 'controls'):
                for sub_control in control.content.controls:
                    if hasattr(sub_control, 'controls'):
                        for row in sub_control.controls:
                            if hasattr(row, 'controls') and len(row.controls) >= 2:
                                if (hasattr(row.controls[0], 'label') and 
                                    row.controls[0].label == "Logo Dosyası (.png)"):
                                    logo_row = row
                                    break
        
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
    
    def add_log(self, message):
        """Log mesajı ekler"""
        current_time = time.strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"
        
        if self.log_text.value:
            self.log_text.value += "\n" + log_message
        else:
            self.log_text.value = log_message
        
        self.page.update()
    
    def update_status(self, message):
        """Durum metnini günceller"""
        self.status_text.value = message
        self.page.update()
    
    def update_progress(self, value):
        """İlerleme çubuğunu günceller"""
        self.progress_bar.value = value
        self.page.update()
    
    def start_download(self, e):
        """İndirme işlemini başlatır"""
        if self.is_downloading:
            return
        
        url = self.url_field.value.strip()
        if not url:
            self.add_log("❌ Lütfen bir Twitter video URL'si girin")
            return
        
        if not self.is_valid_twitter_url(url):
            self.add_log("❌ Geçerli bir Twitter video URL'si girin")
            return
        
        # UI'yi güncelle
        self.is_downloading = True
        self.download_button.visible = False
        self.stop_button.visible = True
        self.progress_bar.visible = True
        self.page.update()
        
        # İndirme işlemini ayrı thread'de başlat
        threading.Thread(target=self.download_worker, daemon=True).start()
    
    def stop_download(self, e):
        """İndirme işlemini durdurur"""
        self.is_downloading = False
        self.add_log("🛑 İndirme durduruldu")
        self.update_status("İndirme durduruldu")
        
        # UI'yi sıfırla
        self.download_button.visible = True
        self.stop_button.visible = False
        self.progress_bar.visible = False
        self.page.update()
    
    def is_valid_twitter_url(self, url):
        """Twitter URL'sinin geçerli olup olmadığını kontrol eder"""
        twitter_patterns = [
            r'https?://(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/\d+',
            r'https?://t\.co/[A-Za-z0-9]+'
        ]
        
        for pattern in twitter_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def download_worker(self):
        """İndirme işlemini gerçekleştirir"""
        try:
            url = self.url_field.value.strip()
            output_dir = self.output_folder_field.value
            
            # Çıktı klasörünü oluştur
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            self.add_log(f"🔄 İndirme başlatılıyor: {url}")
            self.add_log(f"📡 Yöntem: Auth Token API")
            self.update_status("Medya indiriliyor...")
            self.update_progress(0.1)
            
            # HTTP/API yöntemi ile indir
            video_filename = self.download_with_api(url, output_dir)
            
            if not video_filename:
                self.add_log("❌ Video indirilemedi")
                self.update_status("İndirme başarısız")
                return
            
            self.update_progress(0.6)
            self.add_log(f"✅ Video indirildi: {os.path.basename(video_filename)}")
            
            # Logo ekleme - hem video hem görsel için
            if self.use_logo_checkbox.value and self.logo_file_field.value:
                self.update_status("Logo ekleniyor...")
                self.update_progress(0.7)
                
                logo_path = self.logo_file_field.value
                file_extension = os.path.splitext(video_filename)[1].lower()
                
                # Video dosyaları için
                if file_extension in ['.mp4', '.mov', '.avi', '.webm', '.mkv']:
                    processed_file = self.video_processor.add_logo_to_video(
                        video_filename, logo_path, output_dir
                    )
                    if processed_file:
                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                        try:
                            os.remove(video_filename)
                            video_filename = processed_file
                            self.add_log("✅ Video'ya logo eklendi")
                        except Exception as e:
                            self.add_log(f"⚠️ Dosya işleme hatası: {str(e)}")
                    else:
                        self.add_log("⚠️ Video'ya logo eklenemedi")
                
                # Görsel dosyaları için
                elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']:
                    processed_file = self.video_processor.add_logo_to_image(
                        video_filename, logo_path, output_dir
                    )
                    if processed_file:
                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                        try:
                            os.remove(video_filename)
                            video_filename = processed_file
                            self.add_log("✅ Görsele logo eklendi")
                        except Exception as e:
                            self.add_log(f"⚠️ Dosya işleme hatası: {str(e)}")
                    else:
                        self.add_log("⚠️ Görsele logo eklenemedi")
                
                else:
                    self.add_log(f"⚠️ Desteklenmeyen dosya formatı: {file_extension}")
            
            self.update_progress(0.8)
            

            
            self.update_progress(1.0)
            self.add_log("🎉 İndirme tamamlandı!")
            self.update_status("İndirme tamamlandı")
            
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
    
    def extract_tweet_id_from_url(self, url):
        """Twitter URL'sinden tweet ID'sini çıkarır"""
        patterns = [
            r'https?://(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/(\d+)',
            r'https?://t\.co/[A-Za-z0-9]+.*status/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(3) if len(match.groups()) >= 3 else match.group(1)
        return None
    
    def extract_username_from_url(self, url):
        """Twitter URL'sinden kullanıcı adını çıkarır"""
        patterns = [
            r'https?://(www\.)?(twitter|x)\.com/([A-Za-z0-9_]+)/status/\d+'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(3)
        return None
    
    async def download_file_async(self, session, url, filepath):
        """Async dosya indirme"""
        try:
            if os.path.exists(filepath):
                return True, True
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return True, False
                return False, False
        except Exception as e:
            self.add_log(f"Dosya indirme hatası: {str(e)}")
            return False, False
    
    def download_with_api(self, url, output_dir):
        """Auth token ve getMetadata kullanarak video indirir"""
        try:
            self.add_log("🔄 Auth token ile medya indiriliyor...")
            
            # URL'den kullanıcı adını çıkar
            username = self.extract_username_from_url(url)
            tweet_id = self.extract_tweet_id_from_url(url)
            
            if not username or not tweet_id:
                self.add_log("❌ URL'den kullanıcı adı veya tweet ID çıkarılamadı")
                return None
            
            self.add_log(f"📡 Kullanıcı: @{username}, Tweet ID: {tweet_id}")
            
            # getMetadata ile kullanıcının medyalarını çek
            result = get_metadata(
                username=username,
                auth_token=self.auth_token,
                timeline_type="media",
                batch_size=100,  # İlk 100 medyayı çek
                page=0,
                media_type="all"
            )
            
            if result and 'error' in result:
                self.add_log(f"❌ {result['error']}")
                return None
            
            if not result or 'timeline' not in result:
                self.add_log("❌ Medya bulunamadı")
                return None
            
            # Tweet ID'sine göre medyayı bul
            target_media = None
            for media_item in result['timeline']:
                if str(media_item.get('tweet_id', '')) == str(tweet_id):
                    target_media = media_item
                    break
            
            if not target_media:
                self.add_log(f"❌ Tweet ID {tweet_id} için medya bulunamadı")
                return None
            
            # Medya dosyasını indir
            media_url = target_media['url']
            media_date = datetime.strptime(target_media['date'], "%Y-%m-%d %H:%M:%S")
            formatted_date = media_date.strftime("%Y%m%d_%H%M%S")
            
            # Dosya uzantısını belirle
            if 'video.twimg.com' in media_url:
                extension = 'mp4'
                media_type_folder = 'video'
            elif target_media.get('type') == 'animated_gif':
                extension = 'mp4'
                media_type_folder = 'gif'
            else:
                extension = 'jpg'
                media_type_folder = 'image'
            
            # Dosya adını oluştur
            filename = f"{username}_{formatted_date}_{tweet_id}.{extension}"
            
            # Tweet ID'sine göre klasör oluştur
            tweet_output_dir = os.path.join(output_dir, f"tweet_{tweet_id}")
            os.makedirs(tweet_output_dir, exist_ok=True)
            
            filepath = os.path.join(tweet_output_dir, filename)
            
            self.add_log(f"📥 İndiriliyor: {filename}")
            
            # Async indirme işlemi
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def download_task():
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    success, was_skipped = await self.download_file_async(session, media_url, filepath)
                    return success, was_skipped, filepath
            
            success, was_skipped, final_filepath = loop.run_until_complete(download_task())
            loop.close()
            
            if success:
                if was_skipped:
                    self.add_log(f"✅ Dosya zaten mevcut: {os.path.basename(final_filepath)}")
                else:
                    self.add_log(f"✅ Medya başarıyla indirildi: {os.path.basename(final_filepath)}")
                return final_filepath
            else:
                self.add_log("❌ Medya indirilemedi")
                return None
            
        except Exception as e:
            self.add_log(f"❌ İndirme hatası: {str(e)}")
            return None
    


if __name__ == "__main__":
    app = TwitterSingleDownloaderApp()
    try:
        ft.app(target=app.main)
    except NotImplementedError:
        # Windows'ta asyncio subprocess sorunu için alternatif
        import asyncio
        if hasattr(asyncio, 'set_event_loop_policy'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        ft.app(target=app.main)