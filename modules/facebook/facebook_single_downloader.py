import flet as ft
import os
import threading
import time
import re
import subprocess
import shutil
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from video_processor import VideoProcessor

# Relative import için try-except kullan
try:
    from .facebook_request_scraper import FacebookRequestScraper
except ImportError:
    from facebook_request_scraper import FacebookRequestScraper

import random
from pathlib import Path

class FacebookSingleDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor()
        self.is_downloading = False
        self.page = None
        self.facebook_scraper = None
        
    def main(self, page: ft.Page):
        page.title = "Facebook Tekli Video İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 800
        page.window_height = 700
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.url_field = ft.TextField(
            label="Facebook Video URL'si",
            hint_text="Örn: https://www.facebook.com/watch/?v=...",
            width=500,
            prefix_icon=ft.Icons.LINK
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
        
        # Dosya seçici butonları
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
                            "Facebook Tekli Video İndirici",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700
                        ),
                        ft.Text(
                            "Facebook videolarını kolayca indirin",
                            size=14,
                            color=ft.Colors.GREY_600
                        )
                    ]),
                    padding=20,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # URL girişi
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
                
                # İndirme butonu
                ft.Container(
                    content=self.download_button,
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
            self.add_log("❌ Lütfen bir Facebook URL'si girin")
            return
        
        if not self.is_valid_facebook_url(url):
            self.add_log("❌ Geçerli bir Facebook URL'si girin")
            return
        
        # UI'yi güncelle
        self.is_downloading = True
        self.download_button.disabled = True
        self.progress_bar.visible = True
        self.page.update()
        
        # İndirme işlemini ayrı thread'de başlat
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()
    
    def is_valid_facebook_url(self, url):
        """Facebook URL'sinin geçerli olup olmadığını kontrol eder"""
        facebook_patterns = [
            r'https?://(www\.)?facebook\.com/watch/\?v=\d+',
            r'https?://(www\.)?facebook\.com/watch\?v=\d+',  # Facebook watch URL'leri
            r'https?://(www\.)?facebook\.com/[^/]+/videos/\d+',
            r'https?://(www\.)?facebook\.com/video\.php\?v=\d+',
            r'https?://(www\.)?facebook\.com/photo\.php\?fbid=\d+',
            r'https?://(www\.)?facebook\.com/photo/\?fbid=\d+',
            r'https?://(www\.)?facebook\.com/[^/]+/posts/\d+',
            r'https?://(www\.)?facebook\.com/reel/\d+',
            r'https?://fb\.watch/[A-Za-z0-9_-]+'
        ]
        
        for pattern in facebook_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def download_video(self, url):
        """Video indirme işlemini gerçekleştirir"""
        try:
            self.add_log(f"📥 Facebook video indiriliyor: {url}")
            self.update_status("Video indiriliyor...")
            self.update_progress(0.1)
            
            # Facebook scraper'ı başlat
            self.facebook_scraper = FacebookRequestScraper(log_callback=self.add_log)
            
            # Çıktı klasörünü oluştur
            output_dir = self.output_folder_field.value
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            self.update_progress(0.2)
            
            # URL'yi temizle ve doğrula
            clean_url = self.facebook_scraper.clean_facebook_url(url)
            if not clean_url:
                self.add_log("❌ Geçersiz Facebook URL'si")
                return
            
            self.add_log(f"🔗 Temizlenmiş URL: {clean_url}")
            self.update_progress(0.3)
            
            # yt-dlp kullanarak video indir
            video_filename = self.download_with_ytdlp(clean_url, output_dir)
            
            if not video_filename:
                self.add_log("❌ Video indirilemedi")
                return
            
            self.update_progress(0.7)
            
            # Logo ekleme
            if self.use_logo_checkbox.value and self.logo_file_field.value:
                self.add_log("🎨 Logo ekleniyor...")
                self.update_status("Logo ekleniyor...")
                
                logo_path = self.logo_file_field.value
                
                # Video dosyaları için logo ekleme
                if video_filename.endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
                    result_path = self.video_processor.add_logo_to_video(
                        video_filename, logo_path, output_dir
                    )
                    
                    if result_path and os.path.exists(result_path):
                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                        os.remove(video_filename)
                        os.rename(result_path, video_filename)
                        self.add_log("✅ Video'ya logo başarıyla eklendi")
                    else:
                        self.add_log("❌ Video logo ekleme başarısız")
                
                # Resim dosyaları için logo ekleme
                elif video_filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
                    result_path = self.video_processor.add_logo_to_image(
                        video_filename, logo_path, output_dir
                    )
                    
                    if result_path and os.path.exists(result_path):
                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                        os.remove(video_filename)
                        os.rename(result_path, video_filename)
                        self.add_log("✅ Resim'e logo başarıyla eklendi")
                    else:
                        self.add_log("❌ Resim logo ekleme başarısız")
                else:
                    self.add_log("⚠️ Desteklenmeyen dosya formatı için logo eklenemedi")
            
            self.update_progress(1.0)
            self.add_log("✅ İndirme tamamlandı!")
            self.update_status("İndirme tamamlandı")
            
        except Exception as e:
            self.add_log(f"❌ Hata: {str(e)}")
            self.update_status("Hata oluştu")
        
        finally:
            # Facebook scraper'ı kapat
            if self.facebook_scraper:
                self.facebook_scraper.close()
                self.facebook_scraper = None
            
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.disabled = False
            self.progress_bar.visible = False
            self.page.update()
    
    def download_with_ytdlp(self, url, output_dir):
        """yt-dlp kullanarak video indirir veya Facebook Request Scraper ile fotoğraf indirir"""
        try:
            # URL'nin fotoğraf olup olmadığını kontrol et
            is_photo = 'photo' in url.lower()
            
            if is_photo:
                # Fotoğraf için Facebook Request Scraper kullan
                self.add_log("📸 Fotoğraf indirme modu aktif")
                
                # Dosya adı oluştur
                import time
                timestamp = int(time.time())
                output_path = os.path.join(output_dir, f"facebook_photo_{timestamp}")
                
                # Facebook Request Scraper ile fotoğraf indir
                success = self.facebook_scraper.download_photo(url, output_path)
                
                if success:
                    # İndirilen dosyayı bul
                    for file in os.listdir(output_dir):
                        if file.startswith(f"facebook_photo_{timestamp}") and file.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            return os.path.join(output_dir, file)
                    return None
                else:
                    return None
            else:
                # Video için yt-dlp kullan
                self.add_log("🎥 Video indirme modu aktif")
                
                # Dosya adı formatı
                output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
                
                # yt-dlp komutu
                cmd = [
                    "python", "-m", "yt_dlp",
                    "-f", "best[ext=mp4]",
                    "-o", output_template,
                    "--no-playlist",
                    url
                ]
                
                # Komutu çalıştır
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                
                if result.returncode == 0:
                    # İndirilen dosyayı bul
                    for file in os.listdir(output_dir):
                        if file.endswith('.mp4'):
                            return os.path.join(output_dir, file)
                    return None
                else:
                    self.add_log(f"yt-dlp hatası: {result.stderr}")
                    return None
                
        except Exception as e:
            self.add_log(f"İndirme hatası: {str(e)}")
            return None

if __name__ == "__main__":
    app = FacebookSingleDownloaderApp()
    ft.app(target=app.main)