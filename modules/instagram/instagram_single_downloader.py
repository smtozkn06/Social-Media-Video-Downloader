import flet as ft
import os
import sys
import threading
import time
import re
import subprocess
import shutil
import instaloader
import requests
from datetime import datetime
from urllib.parse import urlparse
from translations import Translations

# Ana dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from video_processor import VideoProcessor
except ImportError:
    VideoProcessor = None

try:
    from modules.instagram.instagram_http_downloader import InstagramHttpDownloader
except ImportError:
    InstagramHttpDownloader = None

class InstagramSingleDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor() if VideoProcessor else None
        self.is_downloading = False
        self.page = None
        self.loader = instaloader.Instaloader()
        self.translations = Translations()
        self.current_language = "tr"  # Default language
        
    def get_text(self, key):
        """Get translated text for the given key"""
        return self.translations.get_text(key, self.current_language)
        
    def set_language(self, language):
        """Set the current language and update UI"""
        self.current_language = language
        if self.page:
            self.page.update()
            
    def on_language_change(self, e):
        """Handle language change event"""
        self.set_language(e.control.value)
        # Reload the page to apply new language
        self.page.clean()
        self.main(self.page)
    
    def main(self, page: ft.Page):
        self.page = page
        page.title = self.get_text("instagram_single_title")
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 600
        page.window_height = 800
        page.window_resizable = True
        page.padding = 20
        
        # Language selection and back button
        language_dropdown = ft.Dropdown(
            label=self.get_text("language"),
            options=[
                ft.dropdown.Option("tr", self.get_text("language_turkish")),
                ft.dropdown.Option("en", self.get_text("language_english"))
            ],
            value=self.current_language,
            on_change=self.on_language_change,
            width=150
        )
        
        back_button = ft.ElevatedButton(
            text=self.get_text("back_to_main"),
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda _: page.go("/")
        )
        
        # UI Bileşenleri
        self.url_field = ft.TextField(
            label=self.get_text("instagram_url_label"),
            hint_text=self.get_text("instagram_url_hint"),
            width=500,
            prefix_icon=ft.Icons.LINK
        )
        
        self.use_logo_checkbox = ft.Checkbox(
            label=self.get_text("add_logo"),
            value=True,
            on_change=self.on_logo_checkbox_change
        )
        
        self.logo_file_field = ft.TextField(
            label=self.get_text("logo_file"),
            width=400,
            read_only=True,
            visible=True
        )
        
        self.output_folder_field = ft.TextField(
            label=self.get_text("output_folder"),
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
        
        self.page.overlay.extend([logo_file_picker, output_folder_picker])
        
        self.logo_button = ft.ElevatedButton(
            self.get_text("select"),
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=True
        )
        
        # İndirme butonu
        self.download_button = ft.ElevatedButton(
            self.get_text("download"),
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
        
        # Post bilgileri metni
        self.post_info_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLUE_700,
            selectable=True
        )
        
        # Post bilgileri container'ı oluştur
        self.post_info_container = ft.Container(
            content=ft.Column([
                ft.Text(self.get_text("post_info"), size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                self.post_info_text
            ]),
            padding=10,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=5,
            margin=ft.margin.only(top=10),
            visible=False
        )
        
        # Log metni
        self.log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_700,
            selectable=True
        )
        
        # Ana layout
        self.page.add(
            ft.Column([
                # Language and navigation row
                ft.Row([
                    language_dropdown,
                    back_button
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            self.get_text("instagram_single_title"),
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700
                        ),
                        ft.Text(
                            self.get_text("platform_instagram_desc"),
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
                        # Post bilgileri bölümü
                        self.post_info_container,
                        # Log bölümü
                        ft.Container(
                            content=ft.Column([
                                ft.Text("İşlem Logları", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                                self.log_text
                            ]),
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
        try:
            # Logo alanlarının görünürlüğünü güncelle
            self.logo_file_field.visible = e.control.value
            self.logo_button.visible = e.control.value
            
            # Sadece ilgili kontrolleri güncelle
            self.logo_file_field.update()
            self.logo_button.update()
            
        except Exception as ex:
            self.add_log(f"❌ Logo checkbox hatası: {str(ex)}")
    
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
    
    def show_post_info(self, post_info):
        """Post bilgilerini gösterir"""
        if post_info:
            info_text = f"👤 Kullanıcı: @{post_info.get('username', 'Bilinmiyor')}\n"
            info_text += f"📅 Tarih: {post_info.get('date', 'Bilinmiyor')}\n"
            info_text += f"📝 Açıklama: {post_info.get('caption', 'Açıklama yok')[:100]}{'...' if len(post_info.get('caption', '')) > 100 else ''}\n"
            info_text += f"❤️ Beğeni: {post_info.get('likes', 'Bilinmiyor')}\n"
            info_text += f"💬 Yorum: {post_info.get('comments', 'Bilinmiyor')}\n"
            info_text += f"🎥 Video: {'Evet' if post_info.get('is_video', False) else 'Hayır'}\n"
            
            if post_info.get('is_video', False):
                info_text += f"⏱️ Süre: {post_info.get('duration', 'Bilinmiyor')} saniye\n"
            
            self.post_info_text.value = info_text
            self.post_info_container.visible = True
            self.page.update()
        else:
            self.post_info_container.visible = False
            self.page.update()
    
    def start_download(self, e):
        """İndirme işlemini başlatır"""
        if self.is_downloading:
            return
        
        url = self.url_field.value.strip()
        if not url:
            self.add_log("❌ Lütfen bir Instagram URL'si girin")
            return
        
        if not self.is_valid_instagram_url(url):
            self.add_log("❌ Geçerli bir Instagram URL'si girin")
            return
        
        # UI'yi güncelle
        self.is_downloading = True
        self.download_button.disabled = True
        self.progress_bar.visible = True
        self.page.update()
        
        # İndirme işlemini ayrı thread'de başlat (sadece Instaloader kullan)
        threading.Thread(target=self.download_with_instaloader, args=(url,), daemon=True).start()
    
    def is_valid_instagram_url(self, url):
        """Instagram URL'sinin geçerli olup olmadığını kontrol eder"""
        # Post, Reel ve Hikaye URL'lerini destekle
        patterns = [
            r'https?://(www\.)?instagram\.com/(p|reel)/[A-Za-z0-9_-]+/?',  # Post ve Reel
            r'https?://(www\.)?instagram\.com/stories/[A-Za-z0-9_.]+/?'  # Hikaye
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def extract_shortcode(self, url):
        """Instagram URL'sinden shortcode çıkarır"""
        if "instagram.com/p/" in url or "instagram.com/reel/" in url:
            return url.strip().split("/")[-2]
        return None
    
    def get_post_info(self, shortcode):
        """Post bilgilerini getirir"""
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Video süresi hesaplama
            duration = None
            if post.is_video and hasattr(post, 'video_duration'):
                duration = post.video_duration
            
            return {
                'post': post,
                'is_video': post.is_video,
                'media_url': post.video_url if post.is_video else post.url,
                'caption': post.caption or "Açıklama mevcut değil.",
                'username': post.owner_username,
                'date': post.date,
                'likes': post.likes,
                'comments': post.comments,
                'duration': duration,
                'shortcode': shortcode,
                'owner_id': post.owner_id if hasattr(post, 'owner_id') else None
            }
        except Exception as e:
            return None
    
    def download_media_with_instaloader(self, post_info, progress_callback=None):
        """Instaloader ile medyayı indirir"""
        try:
            post = post_info['post']
            media_url = post_info['media_url']
            file_ext = ".mp4" if post_info['is_video'] else ".jpg"
            filename = f"insta_{post_info['username']}_{post.date.strftime('%Y%m%d_%H%M%S')}{file_ext}"
            local_filename = os.path.join(self.output_folder_field.value, filename)
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(media_url, stream=True, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            # İndirme geçmişini kaydet
            self.save_download_history(post_info, filename)
            return local_filename
            
        except Exception as e:
            raise Exception(f"İndirme hatası: {str(e)}")
    
    def save_download_history(self, post_info, filename):
        """İndirme geçmişini kaydeder"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        media_type = "Video" if post_info['is_video'] else "Resim"
        with open("download_history.txt", "a", encoding="utf-8") as log_file:
             log_file.write(f"{now} — @{post_info['username']} — {media_type} — {filename}\n")
    
    def download_with_instaloader(self, url):
        """Instaloader ile indirme işlemi - Hata durumunda HTTP'ye fallback"""
        try:
            self.add_log(f"📥 Instaloader ile Instagram içeriği indiriliyor: {url}")
            self.update_status("Instaloader ile indiriliyor...")
            self.update_progress(0.1)
            
            # Shortcode çıkar
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                self.add_log("❌ Geçersiz Instagram linki!")
                return
            
            self.update_progress(0.3)
            
            # Post bilgilerini al
            try:
                post_info = self.get_post_info(shortcode)
                if not post_info:
                    raise Exception("Post bilgileri alınamadı")
                
                # Post bilgilerini göster
                self.show_post_info(post_info)
                self.add_log(f"📋 Post bilgileri alındı: @{post_info.get('username', 'Bilinmiyor')}")
                
            except Exception as e:
                self.add_log(f"❌ Instaloader hatası: {str(e)}")
                return
            
            self.update_progress(0.5)
            
            # Medyayı indir
            try:
                downloaded_file = self.download_media_with_instaloader(
                    post_info, 
                    lambda progress: self.update_progress(0.5 + (progress * 0.3 / 100))
                )
            except Exception as e:
                self.add_log(f"❌ Instaloader medya indirme hatası: {str(e)}")
                return
            
            if downloaded_file:
                self.add_log(f"✅ Dosya başarıyla indirildi: {os.path.basename(downloaded_file)}")
                
                # Logo ekleme işlemi
                if self.use_logo_checkbox.value and self.logo_file_field.value and self.video_processor:
                    try:
                        self.add_log("🎨 Logo ekleniyor...")
                        self.update_status("Logo ekleniyor...")
                        
                        logo_path = self.logo_file_field.value
                        output_dir = self.output_folder_field.value
                        
                        # Video dosyaları için logo ekleme
                        if downloaded_file.lower().endswith(('.mp4', '.mov', '.avi', '.webm', '.mkv')):
                            processed_file = self.video_processor.add_logo_to_video(
                                downloaded_file, logo_path, output_dir
                            )
                            
                            if processed_file and os.path.exists(processed_file):
                                # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                if os.path.exists(downloaded_file):
                                    os.remove(downloaded_file)
                                # İşlenmiş dosyayı orijinal isimle yeniden adlandır
                                final_file = downloaded_file
                                if processed_file != final_file:
                                    os.rename(processed_file, final_file)
                                downloaded_file = final_file
                                self.add_log("✅ Video'ya logo başarıyla eklendi")
                            else:
                                self.add_log("⚠️ Video logo ekleme başarısız, orijinal dosya korundu")
                        
                        # Resim dosyaları için logo ekleme
                        elif downloaded_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
                            processed_file = self.video_processor.add_logo_to_image(
                                downloaded_file, logo_path, output_dir
                            )
                            
                            if processed_file and os.path.exists(processed_file):
                                # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                if os.path.exists(downloaded_file):
                                    os.remove(downloaded_file)
                                # İşlenmiş dosyayı orijinal isimle yeniden adlandır
                                final_file = downloaded_file
                                if processed_file != final_file:
                                    os.rename(processed_file, final_file)
                                downloaded_file = final_file
                                self.add_log("✅ Resim'e logo başarıyla eklendi")
                            else:
                                self.add_log("⚠️ Resim logo ekleme başarısız, orijinal dosya korundu")
                        
                        else:
                            self.add_log("⚠️ Desteklenmeyen dosya formatı için logo eklenemedi")
                            
                    except Exception as logo_error:
                        self.add_log(f"❌ Logo ekleme hatası: {str(logo_error)}")
                        self.add_log("⚠️ Orijinal dosya korundu")
                
                self.update_progress(1.0)
                self.update_status("İndirme tamamlandı")
            else:
                self.add_log("❌ Dosya indirilemedi")
                return
                
        except Exception as e:
            self.add_log(f"❌ Instaloader genel hatası: {str(e)}")
            return
        
        finally:
            # UI'yi sıfırla
            self.is_downloading = False
            self.download_button.disabled = False
            self.progress_bar.visible = False
            self.page.update()
     

    


if __name__ == "__main__":
    app = InstagramSingleDownloaderApp()
    ft.app(target=app.main)