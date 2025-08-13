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
from modules.pinterest.pinterest_request_downloader import PinterestRequestDownloader

class PinterestSingleDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor(log_callback=self.update_log)
        self.pinterest_downloader = PinterestRequestDownloader(log_callback=self.update_log)
        self.is_downloading = False
        self.page = None
        self.back_callback = None
        
    def main(self, page: ft.Page):
        page.clean()  # Sayfayı temizle
        page.title = "Pinterest Tekli Pin İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 800
        page.window_height = 900
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.pin_url_field = ft.TextField(
            label="Pinterest Pin URL'si",
            hint_text="Örnek: https://www.pinterest.com/pin/123456789/ veya https://pin.it/abc123",
            width=600,
            prefix_icon=ft.Icons.LINK,
            on_change=self.on_url_change,
            helper_text="Pinterest pin URL'sini buraya yapıştırın"
        )
        
        self.use_logo_checkbox = ft.Checkbox(
            label="Logo Ekle",
            value=False,
            on_change=self.on_logo_checkbox_change
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
            "Seç",
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=False
        )
        
        # Progress bar ve status
        self.progress_bar = ft.ProgressBar(width=600, visible=False)
        self.status_text = ft.Text("🟢 Hazır - Pinterest pin indirmeye hazır", size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=11, color=ft.Colors.BLACK, selectable=True)
        
        # İlk log mesajı
        self.update_log("🎯 Pinterest Tekli Pin İndirici başlatıldı")
        self.update_log("💡 Bir Pinterest pin URL'si girin ve indirmeyi başlatın")
        
        # Butonlar
        start_button = ft.ElevatedButton(
            text="İndirmeyi Başlat",
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
        

        
        # Layout
        content = ft.Column([
            ft.Text("Pinterest Tekli Pin İndirici", 
                   size=24, weight=ft.FontWeight.BOLD, 
                   color=ft.Colors.RED_600),
            ft.Divider(),
            
            # Pin URL Girişi
            ft.Text("Pin URL Girişi", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                self.pin_url_field
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Divider(),
            
            # Dosya ayarları
            ft.Text("Dosya Ayarları", size=18, weight=ft.FontWeight.BOLD),
            
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
                    "Seç",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: output_folder_picker.get_directory_path()
                )
            ]),
            
            ft.Divider(),
            
            # Kontrol butonları
            ft.Row([
                start_button,
                stop_button
            ], alignment=ft.MainAxisAlignment.CENTER),
            

            
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
                                    bgcolor=ft.Colors.ORANGE_600
                                )
                            )
                        ], spacing=10)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        content=self.log_text,
                        bgcolor=ft.Colors.GREY_100,
                        padding=10,
                        border_radius=5,
                        width=600,
                        height=200,
                        border=ft.border.all(1, ft.Colors.GREY_300)
                    )
                ]),
                margin=ft.margin.only(top=20)
            )
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO)
        
        page.add(content)
        page.update()
    
    def on_url_change(self, e):
        """URL field değiştiğinde gerçek zamanlı validation"""
        url = e.control.value.strip()
        if url:
            if 'pinterest.com' in url or 'pin.it' in url:
                e.control.error_text = None
                e.control.border_color = ft.Colors.GREEN
            else:
                e.control.error_text = "Geçersiz Pinterest URL"
                e.control.border_color = ft.Colors.RED
        else:
            e.control.error_text = None
            e.control.border_color = None
        self.page.update()
    
    def on_logo_checkbox_change(self, e):
        """Logo checkbox değiştiğinde"""
        self.logo_file_field.visible = e.control.value
        self.logo_button.visible = e.control.value
        self.page.update()
    
    def on_logo_file_selected(self, e: ft.FilePickerResultEvent):
        """Logo dosyası seçildiğinde"""
        if e.files:
            self.logo_file_field.value = e.files[0].path
            self.page.update()
    
    def on_output_folder_selected(self, e: ft.FilePickerResultEvent):
        """Çıktı klasörü seçildiğinde"""
        if e.path:
            self.output_folder_field.value = e.path
            self.page.update()
    
    def update_log(self, message):
        """Log mesajını güncelle"""
        if hasattr(self, 'log_text') and self.log_text:
            current_time = datetime.now().strftime("%H:%M:%S")
            self.log_text.value += f"[{current_time}] {message}\n"
            if self.page:
                self.page.update()
    
    def copy_logs(self, e):
        """Logları panoya kopyala"""
        if self.log_text.value:
            self.page.set_clipboard(self.log_text.value)
            self.update_log("📋 Loglar panoya kopyalandı")
    
    def clear_logs(self, e):
        """Logları temizle"""
        self.log_text.value = ""
        self.page.update()
    
    def start_download(self, e):
        """İndirmeyi başlat"""
        if self.is_downloading:
            self.update_log("⚠️ Zaten bir indirme işlemi devam ediyor")
            return
        
        # URL kontrolü
        pin_url = self.pin_url_field.value.strip()
        if not pin_url:
            self.update_log("❌ Lütfen Pinterest pin URL'si girin")
            self.update_log("💡 Örnek: https://www.pinterest.com/pin/123456789/")
            return
        
        # Pinterest URL kontrolü
        if not ('pinterest.com' in pin_url or 'pin.it' in pin_url):
            self.update_log("❌ Geçersiz Pinterest URL")
            self.update_log("💡 Desteklenen formatlar:")
            self.update_log("   • https://www.pinterest.com/pin/123456789/")
            self.update_log("   • https://pin.it/abc123")
            return
        
        # Çıktı klasörü kontrolü
        output_dir = self.output_folder_field.value or "output"
        try:
            os.makedirs(output_dir, exist_ok=True)
            self.update_log(f"📁 Çıktı klasörü hazırlandı: {output_dir}")
        except Exception as e:
            self.update_log(f"❌ Çıktı klasörü oluşturulamadı: {str(e)}")
            return
        
        # Logo dosyası kontrolü (eğer seçilmişse)
        if self.use_logo_checkbox.value:
            logo_path = self.logo_file_field.value
            if not logo_path or not os.path.exists(logo_path):
                self.update_log("❌ Logo dosyası seçilmedi veya bulunamadı")
                self.update_log("💡 Logo eklemek istemiyorsanız 'Logo Ekle' seçeneğini kapatın")
                return
            else:
                self.update_log(f"🎨 Logo dosyası: {os.path.basename(logo_path)}")
        
        # İndirme başlat
        self.is_downloading = True
        self.progress_bar.visible = True
        self.status_text.value = "İndirme başlatılıyor..."
        self.status_text.color = ft.Colors.ORANGE
        self.page.update()
        
        self.update_log("🚀 İndirme işlemi başlatılıyor...")
        self.update_log("="*50)
        
        # Thread'de indirme işlemini başlat
        download_thread = threading.Thread(target=self.download_pin, args=(pin_url,))
        download_thread.daemon = True
        download_thread.start()
    
    def download_pin(self, pin_url):
        """Pin'i indir"""
        try:
            # Arayüzden çıktı klasörünü al
            output_dir = self.output_folder_field.value or "output"
            
            self.update_log(f"🎯 İndirme başlatılıyor...")
            self.update_log(f"📌 Pin URL: {pin_url}")
            self.update_log(f"📁 Çıktı klasörü: {output_dir}")
            
            # Pinterest request downloader ile pin'i indir
            # use_logo parametresi pinterest_request_downloader.py'de kullanılmıyor
            # Logo ekleme işlemi ayrı olarak yapılacak
            downloaded_files = self.pinterest_downloader.download_pin(
                pin_url, 
                output_dir
            )
            
            if downloaded_files:
                self.update_log(f"📥 {len(downloaded_files)} dosya başarıyla indirildi")
                
                # Logo ekleme (video ve resim dosyaları için ve checkbox işaretliyse)
                if self.use_logo_checkbox.value and self.logo_file_field.value:
                    logo_path = self.logo_file_field.value
                    if os.path.exists(logo_path):
                        self.update_log(f"🎨 Logo ekleme işlemi başlatılıyor...")
                        processed_count = 0
                        video_count = 0
                        image_count = 0
                        
                        for file_path in downloaded_files:
                            try:
                                # Video dosyaları için logo ekleme
                                if file_path.endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
                                    video_count += 1
                                    processed_count += 1
                                    self.update_log(f"🎬 Video'ya logo ekleniyor: {os.path.basename(file_path)}")
                                    
                                    # Orijinal dosyayı yedekle
                                    original_path = file_path
                                    temp_path = file_path + ".temp"
                                    
                                    # Logo ekle
                                    result_path = self.video_processor.add_logo_to_video(file_path, logo_path, output_dir)
                                    
                                    if result_path and os.path.exists(result_path):
                                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                        os.remove(file_path)
                                        os.rename(result_path, file_path)
                                        self.update_log(f"✅ Video'ya logo başarıyla eklendi: {os.path.basename(file_path)}")
                                    else:
                                        self.update_log(f"❌ Video logo ekleme başarısız: {os.path.basename(file_path)}")
                                
                                # Resim dosyaları için logo ekleme
                                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
                                    image_count += 1
                                    processed_count += 1
                                    self.update_log(f"🖼️ Resim'e logo ekleniyor: {os.path.basename(file_path)}")
                                    
                                    # Logo ekle
                                    result_path = self.video_processor.add_logo_to_image(file_path, logo_path, output_dir)
                                    
                                    if result_path and os.path.exists(result_path):
                                        # Orijinal dosyayı sil ve işlenmiş dosyayı yeniden adlandır
                                        os.remove(file_path)
                                        os.rename(result_path, file_path)
                                        self.update_log(f"✅ Resim'e logo başarıyla eklendi: {os.path.basename(file_path)}")
                                    else:
                                        self.update_log(f"❌ Resim logo ekleme başarısız: {os.path.basename(file_path)}")
                                    
                            except Exception as logo_error:
                                self.update_log(f"❌ Logo ekleme hatası ({os.path.basename(file_path)}): {str(logo_error)}")
                        
                        if processed_count == 0:
                            self.update_log(f"ℹ️ Logo eklenebilecek dosya bulunamadı (video/resim)")
                        else:
                            self.update_log(f"🎨 Logo ekleme tamamlandı:")
                            if video_count > 0:
                                self.update_log(f"   📹 {video_count} video dosyasına logo eklendi")
                            if image_count > 0:
                                self.update_log(f"   🖼️ {image_count} resim dosyasına logo eklendi")
                    else:
                        self.update_log(f"❌ Logo dosyası bulunamadı: {logo_path}")
                
                # İndirilen dosyaları listele
                self.update_log(f"📋 İndirilen dosyalar:")
                for i, file_path in enumerate(downloaded_files, 1):
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    self.update_log(f"  {i}. {file_name} ({file_size:.2f} MB)")
                
                self.update_log(f"✅ İndirme tamamlandı! Toplam {len(downloaded_files)} dosya")
                self.update_log(f"📁 Dosya konumu: {output_dir}")
                self.download_finished(True)
            else:
                self.update_log("❌ Hiçbir dosya indirilemedi")
                self.update_log("💡 Olası nedenler:")
                self.update_log("   • Pin URL'si geçersiz veya erişilemiyor")
                self.update_log("   • Pin silinmiş olabilir")
                self.update_log("   • Pinterest erişim kısıtlaması")
                self.update_log("   • İnternet bağlantısı sorunu")
                self.download_finished(False)
            
        except Exception as e:
            self.update_log(f"❌ İndirme hatası: {str(e)}")
            self.update_log(f"🔧 Hata detayı: {type(e).__name__}")
            self.download_finished(False)
    
    def stop_download(self, e):
        """İndirmeyi durdur"""
        if self.is_downloading:
            self.is_downloading = False
            self.update_log("⏹️ İndirme kullanıcı tarafından durduruldu")
            self.update_log("🔄 İşlem iptal ediliyor...")
            self.status_text.value = "İndirme durduruluyor..."
            self.status_text.color = ft.Colors.ORANGE
            if self.page:
                self.page.update()
            self.download_finished(False)
        else:
            self.update_log("ℹ️ Şu anda aktif bir indirme işlemi yok")
    
    def download_finished(self, success):
        """İndirme tamamlandığında"""
        self.is_downloading = False
        self.progress_bar.visible = False
        
        if success:
            self.status_text.value = "✅ İndirme başarıyla tamamlandı"
            self.status_text.color = ft.Colors.GREEN
            self.update_log("="*50)
            self.update_log("🎉 İşlem başarıyla tamamlandı!")
        else:
            self.status_text.value = "❌ İndirme başarısız oldu"
            self.status_text.color = ft.Colors.RED
            self.update_log("="*50)
            self.update_log("💔 İşlem başarısız oldu")
        
        if self.page:
            self.page.update()
    

    
    def close_window(self, page):
        """Pencereyi kapat"""
        try:
            if self.pinterest_downloader:
                self.pinterest_downloader.close()
            page.window_destroy()
        except:
            pass

if __name__ == "__main__":
    app = PinterestSingleDownloaderApp()
    ft.app(target=app.main)