import flet as ft
import os
import sys
import threading
import time
import re
import subprocess
import random
import json
from datetime import datetime
from urllib.parse import urlparse

# Ana dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from video_processor import VideoProcessor
from modules.tiktok.tiktok_scraper import TikTokScraper
from translations import Translations

class TikTokSingleDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor(log_callback=self.update_log)
        self.tiktok_scraper = TikTokScraper(log_callback=self.update_log)
        self.is_downloading = False
        self.page = None
        
        # Çeviri sistemi
        self.translations = Translations()
        self.current_language = "tr"  # Varsayılan dil
        
    def get_text(self, key):
        """Çeviri anahtarına göre metni döndür"""
        return self.translations.get_text(key, self.current_language)
        
    def set_language(self, language):
        """Dili değiştir ve UI'yi güncelle"""
        self.current_language = language
        if self.page:
            self.page.update()
            
    def on_language_change(self, e):
        """Dil değişikliği olayını işle"""
        self.set_language(e.control.value)
        # Sayfayı yeniden yükle
        self.page.clean()
        self.main(self.page)
        
    def main(self, page: ft.Page):
        page.title = self.get_text("tiktok_single_title")
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 800
        page.window_height = 900
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.video_url_field = ft.TextField(
            label=self.get_text("tiktok_url_label"),
            hint_text=self.get_text("tiktok_url_hint"),
            width=600,
            prefix_icon=ft.Icons.LINK
        )
        
        # Müzik klasör yolu kaldırıldı
        
        self.use_logo_checkbox = ft.Checkbox(
            label=self.get_text("add_logo"),
            value=False,
            on_change=self.on_logo_checkbox_change
        )
        

        
        self.logo_file_field = ft.TextField(
            label=self.get_text("logo_file"),
            width=400,
            read_only=True,
            visible=False
        )
        
        self.output_folder_field = ft.TextField(
            label=self.get_text("output_folder"),
            value="output",
            width=400,
            read_only=True
        )
        
        # Ses seviyesi kontrolleri kaldırıldı
        
        # Dosya seçici butonları
        logo_file_picker = ft.FilePicker(
            on_result=self.on_logo_file_selected
        )
        
        output_folder_picker = ft.FilePicker(
            on_result=self.on_output_folder_selected
        )
        
        page.overlay.extend([logo_file_picker, output_folder_picker])
        
        # Logo butonunu sınıf değişkeni olarak sakla
        self.logo_button = ft.ElevatedButton(
            self.get_text("select"),
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=False
        )
        
        # Progress bar ve status
        self.progress_bar = ft.ProgressBar(width=600, visible=False)
        self.status_text = ft.Text(self.get_text("ready"), size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=11, color=ft.Colors.BLACK, selectable=True)
        
        # Butonlar
        start_button = ft.ElevatedButton(
            text=self.get_text("start_download"),
            icon=ft.Icons.DOWNLOAD,
            on_click=self.start_download,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600
            )
        )
        
        stop_button = ft.ElevatedButton(
            text=self.get_text("stop"),
            icon=ft.Icons.STOP,
            on_click=self.stop_download,
            width=200,
            height=50,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_600
            )
        )
        

        
        # Dil seçimi dropdown
        language_dropdown = ft.Dropdown(
            label="Language / Dil",
            options=[
                ft.dropdown.Option("tr", "Türkçe"),
                ft.dropdown.Option("en", "English")
            ],
            value=self.current_language,
            on_change=self.on_language_change,
            width=150
        )
        
        # Back to main menu button
        back_button = ft.ElevatedButton(
            text="← Main Menu",
            on_click=lambda _: page.window_close(),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREY_600
            )
        )
        
        # Layout
        content = ft.Column([
            # Üst bar - dil seçimi ve geri butonu
            ft.Row([
                back_button,
                language_dropdown
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Text(self.get_text("tiktok_single_title"), 
                   size=24, weight=ft.FontWeight.BOLD, 
                   color=ft.Colors.PINK_600),
            ft.Divider(),
            
            # Video URL Girişi
            ft.Text(self.get_text("video_url_input"), size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.video_url_field
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Divider(),
            
            # Dosya ayarları
            ft.Text(self.get_text("file_settings"), size=18, weight=ft.FontWeight.BOLD),
            
            # Müzik klasör seçimi kaldırıldı
            
            ft.Row([
                self.use_logo_checkbox,
            ]),
            
            ft.Row([
                self.logo_file_field,
                self.logo_button
            ]),
            
            ft.Row([
                self.output_folder_field,
                ft.ElevatedButton(
                    self.get_text("select"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: output_folder_picker.get_directory_path()
                )
            ]),
            
            ft.Divider(),
            
            # Ses Ayarları kaldırıldı
            
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
                        ft.Text(self.get_text("log"), size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton(
                                self.get_text("copy_logs"),
                                icon=ft.Icons.COPY,
                                on_click=self.copy_logs,
                                height=30,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE_600
                                )
                            ),
                            ft.ElevatedButton(
                                self.get_text("clear_logs"),
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
                        content=self.log_text,
                        height=120,
                        width=750,
                        bgcolor=ft.Colors.WHITE,
                        padding=10,
                        border_radius=3,
                        border=ft.border.all(1, ft.Colors.GREY_600)
                    )
                ]),
                height=200,
                bgcolor=ft.Colors.WHITE,
                padding=10,
                border_radius=5
            )
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        # Scroll container ile sarmalayalım
        scrollable_content = ft.Container(
            content=content,
            expand=True,
            padding=20
        )
        
        page.add(scrollable_content)
        
    # Müzik klasörü seçme fonksiyonu kaldırıldı
            
    def on_logo_checkbox_change(self, e):
        # Logo alanı ve butonunun görünürlüğünü güncelle
        self.logo_file_field.visible = e.control.value
        self.logo_button.visible = e.control.value
        self.page.update()
    
    def on_logo_file_selected(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.logo_file_field.value = e.files[0].path
            self.page.update()
            
    def on_output_folder_selected(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.output_folder_field.value = e.path
            self.page.update()
            
    # Ses seviyesi değişiklik fonksiyonları kaldırıldı
            
    def update_status(self, message, color=ft.Colors.BLUE):
        self.status_text.value = message
        self.status_text.color = color
        self.page.update()
        
    def update_log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        current_log = self.log_text.value
        new_log = f"{current_log}\n{formatted_message}" if current_log else formatted_message
        
        lines = new_log.split('\n')
        if len(lines) > 20:
            lines = lines[-20:]
        
        self.log_text.value = '\n'.join(lines)
        self.page.update()
        

    
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
        
        # Validasyon
        if not self.video_url_field.value:
            self.update_status("TikTok video URL'si giriniz!", ft.Colors.RED)
            return
        
        # URL formatını kontrol et
        video_url = self.video_url_field.value.strip()
        if not self.is_valid_tiktok_url(video_url):
            self.update_status("Geçerli bir TikTok video URL'si giriniz!", ft.Colors.RED)
            return
        
        # Logo ekleme seçeneği işaretliyse logo dosyasını kontrol et
        if self.use_logo_checkbox.value and not self.logo_file_field.value:
            self.update_status("Logo dosyası seçiniz!", ft.Colors.RED)
            return
        
        # İndirmeyi başlat
        self.is_downloading = True
        self.downloaded_count = 0
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.update_status("İndirme başlatılıyor...", ft.Colors.ORANGE)
        self.page.update()
        
        # Thread'de çalıştır
        threading.Thread(target=self.download_process, daemon=True).start()
        
    def is_valid_tiktok_url(self, url):
        """TikTok video URL'sinin geçerli olup olmadığını kontrol et"""
        # TikTok video URL formatı: https://www.tiktok.com/@username/video/1234567890123456789
        pattern = r'https?://(?:www\.)?tiktok\.com/@[\w\.]+/video/\d+'
        return bool(re.match(pattern, url))
        
    def stop_download(self, e):
        self.is_downloading = False
        self.progress_bar.visible = False
        self.update_status("İndirme durduruldu", ft.Colors.RED)
        self.page.update()
        
    def download_process(self):
        try:
            video_url = self.video_url_field.value.strip()
            # Logo ekleme seçeneği işaretliyse logo dosyasını kullan, değilse None olarak ayarla
            logo_file = self.logo_file_field.value if self.use_logo_checkbox.value else None
            output_folder = self.output_folder_field.value
            
            # Klasörleri oluştur
            os.makedirs(output_folder, exist_ok=True)
            
            self.update_log(f"TikTok videosu indiriliyor: {video_url}")
            
            # İlerleme çubuğunu güncelle
            self.progress_bar.value = 0.1
            self.page.update()
            
            # Video indir
            video_path = self.tiktok_scraper.download_video(video_url, output_folder)
            
            if not video_path:
                self.update_status("Video indirilemedi!", ft.Colors.RED)
                self.is_downloading = False
                self.progress_bar.visible = False
                return
                
            self.update_log(f"Video indirildi: {os.path.basename(video_path)}")
            self.progress_bar.value = 0.4
            self.page.update()
            

            
            # Müzik seçimi kaldırıldı
            
            # Müzik özelliği kaldırıldı
            music_file = None
            
            # Video işleme kaldırıldı - sadece logo ekle (eğer seçilmişse ve MP4 dosyasıysa)
            if logo_file and video_path.lower().endswith('.mp4'):
                try:
                    # Sadece logo ekleme işlemi
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    processed_path = os.path.join(output_folder, f"{base_name}_with_logo.mp4")
                    
                    self.update_log("Videoya logo ekleniyor...")
                    self.progress_bar.value = 0.8
                    self.page.update()
                    
                    success = self.video_processor.add_logo_with_ffmpeg(
                        video_path=video_path,
                        logo_path=logo_file,
                        output_path=processed_path
                    )
                    
                    if success:
                        # Orijinal videoyu sil
                        try:
                            os.remove(video_path)
                            self.update_log(f"Orijinal video silindi: {os.path.basename(video_path)}")
                        except Exception as e:
                            self.update_log(f"Orijinal video silinemedi: {str(e)}")
                            
                        self.downloaded_count = 1
                        self.update_log(f"Video başarıyla işlendi (logo eklendi): {os.path.basename(processed_path)}")
                        
                        # Dosya yolunu göster
                        self.update_log(f"Dosya konumu: {processed_path}")
                        
                        # Tamamlandı
                        self.progress_bar.value = 1.0
                        self.update_status("Video başarıyla indirildi ve logo eklendi!", ft.Colors.GREEN)
                    else:
                        self.update_log("Logo eklenemedi")
                        self.update_status("Logo eklenemedi!", ft.Colors.RED)
                except Exception as logo_error:
                    self.update_log(f"Logo ekleme hatası: {str(logo_error)}")
                    self.update_status(f"Logo ekleme hatası: {str(logo_error)}", ft.Colors.RED)
            else:
                # Logo yoksa video olduğu gibi kalır
                self.downloaded_count = 1
                self.update_log(f"Video orijinal haliyle kaydedildi: {os.path.basename(video_path)}")
                
                # Dosya yolunu göster
                self.update_log(f"Dosya konumu: {video_path}")
                
                # Tamamlandı
                self.progress_bar.value = 1.0
                self.update_status("Video başarıyla indirildi!", ft.Colors.GREEN)
            
            # İşlem tamamlandı
            self.is_downloading = False
            self.page.update()
            
            # 3 saniye sonra progress bar'ı gizle
            time.sleep(3)
            self.progress_bar.visible = False
            self.page.update()
            
        except Exception as e:
            self.is_downloading = False
            self.progress_bar.visible = False
            self.update_status(f"Hata: {str(e)}", ft.Colors.RED)
            self.update_log(f"İşlem hatası: {str(e)}")
            self.page.update()
            
    # Müzik seçme fonksiyonu kaldırıldı

def main():
    app = TikTokSingleDownloaderApp()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()