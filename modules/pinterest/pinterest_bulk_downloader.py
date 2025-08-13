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
from modules.pinterest.pinterest_crawler.pinterest_crawler import PinterestCrawler

class PinterestBulkDownloaderApp:
    def __init__(self):
        self.video_processor = VideoProcessor(log_callback=self.update_log)
        self.pinterest_downloader = PinterestRequestDownloader(log_callback=self.update_log)
        self.pinterest_crawler = PinterestCrawler()
        self.is_downloading = False
        self.page = None
        self.back_callback = None
        self.download_count = 0
        self.total_count = 0
        
    def main(self, page: ft.Page):
        page.clean()  # Sayfayı temizle
        page.title = "Pinterest Toplu Pin İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 900
        page.window_height = 1000
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.download_type = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="search", label="Kelime ile Arama"),
                ft.Radio(value="txt", label="TXT Dosyasından İndir")
            ]),
            value="search",
            on_change=self.on_download_type_change
        )
        
        
        self.txt_file_field = ft.TextField(
            label="TXT Dosyası (.txt)",
            width=400,
            read_only=True,
            visible=False
        )
        
        self.search_keyword_field = ft.TextField(
            label="Arama Kelimesi",
            hint_text="Örnek: kedi, doğa, yemek",
            width=600,
            prefix_icon=ft.Icons.SEARCH,
            visible=True
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
        
        self.max_pins_field = ft.TextField(
            label="Maksimum Pin Sayısı (0 = Sınırsız)",
            value="50",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.parallel_downloads_field = ft.TextField(
            label="Paralel İndirme Sayısı",
            value="3",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Dosya seçici butonları
        txt_file_picker = ft.FilePicker(
            on_result=self.on_txt_file_selected
        )
        
        logo_file_picker = ft.FilePicker(
            on_result=self.on_logo_file_selected
        )
        
        output_folder_picker = ft.FilePicker(
            on_result=self.on_output_folder_selected
        )
        
        page.overlay.extend([txt_file_picker, logo_file_picker, output_folder_picker])
        
        # Butonları sınıf değişkeni olarak sakla
        self.txt_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.TEXT_SNIPPET,
            on_click=lambda _: txt_file_picker.pick_files(
                allowed_extensions=["txt"]
            ),
            visible=False
        )
        
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
        self.progress_text = ft.Text("", size=14, color=ft.Colors.BLUE)
        self.status_text = ft.Text("Hazır", size=16, color=ft.Colors.GREEN)
        self.log_text = ft.Text("", size=11, color=ft.Colors.BLACK, selectable=True)
        
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
            ft.Text("Pinterest Toplu Pin İndirici", 
                   size=24, weight=ft.FontWeight.BOLD, 
                   color=ft.Colors.RED_600),
            ft.Divider(),
            
            # İndirme türü seçimi
            ft.Text("İndirme Türü", size=18, weight=ft.FontWeight.BOLD),
            self.download_type,
            
            ft.Divider(),
            
            # URL/Dosya Girişi
            ft.Text("URL/Dosya Girişi", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Row([
                self.txt_file_field,
                self.txt_button
            ]),
            
            ft.Row([
                self.search_keyword_field
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Divider(),
            
            # İndirme ayarları
            ft.Text("İndirme Ayarları", size=18, weight=ft.FontWeight.BOLD),
            
            ft.Row([
                self.max_pins_field,
                self.parallel_downloads_field
            ], spacing=20),
            
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
            self.progress_text,
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
    
    def on_download_type_change(self, e):
        """İndirme türü değiştiğinde"""
        download_type = e.control.value
        
        if download_type == "txt":
            self.txt_file_field.visible = True
            self.txt_button.visible = True
            self.search_keyword_field.visible = False
        elif download_type == "search":
            self.txt_file_field.visible = False
            self.txt_button.visible = False
            self.search_keyword_field.visible = True
        
        self.page.update()
    
    def on_txt_file_selected(self, e: ft.FilePickerResultEvent):
        """TXT dosyası seçildiğinde"""
        if e.files:
            self.txt_file_field.value = e.files[0].path
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
        
        download_type = self.download_type.value
        
        # Girdi kontrolü
        if download_type == "txt":
            if not self.txt_file_field.value:
                self.update_log("❌ Lütfen TXT dosyası seçin")
                return
            if not os.path.exists(self.txt_file_field.value):
                self.update_log("❌ TXT dosyası bulunamadı")
                return
        elif download_type == "search":
            keyword = self.search_keyword_field.value.strip()
            if not keyword:
                self.update_log("❌ Lütfen arama kelimesi girin")
                return
        
        # Sayısal değer kontrolü
        try:
            max_pins = int(self.max_pins_field.value) if self.max_pins_field.value else 0
            parallel_downloads = int(self.parallel_downloads_field.value) if self.parallel_downloads_field.value else 3
            
            if parallel_downloads < 1:
                parallel_downloads = 1
            elif parallel_downloads > 10:
                parallel_downloads = 10
                
        except ValueError:
            self.update_log("❌ Geçersiz sayısal değer")
            return
        
        self.is_downloading = True
        self.download_count = 0
        self.total_count = 0
        self.progress_bar.visible = True
        self.status_text.value = "İndiriliyor..."
        self.status_text.color = ft.Colors.ORANGE
        self.page.update()
        
        # Thread'de indirme işlemini başlat
        if download_type == "txt":
            download_thread = threading.Thread(
                target=self.download_from_txt, 
                args=(self.txt_file_field.value, max_pins, parallel_downloads)
            )
        elif download_type == "search":
            download_thread = threading.Thread(
                target=self.download_from_search, 
                args=(self.search_keyword_field.value, max_pins, parallel_downloads)
            )
        
        download_thread.daemon = True
        download_thread.start()
    

    
    def download_from_txt(self, txt_file, max_pins, parallel_downloads):
        """TXT dosyasından indirme"""
        try:
            self.update_log(f"📄 TXT dosyası okunuyor: {txt_file}")
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            pin_urls = []
            for line in lines:
                line = line.strip()
                if line and ('pinterest.com' in line or 'pin.it' in line):
                    pin_urls.append(line)
            
            if not pin_urls:
                self.update_log("❌ TXT dosyasında geçerli Pinterest URL'si bulunamadı")
                self.download_finished(False)
                return
            
            # Maksimum pin sayısını uygula
            if max_pins > 0 and len(pin_urls) > max_pins:
                pin_urls = pin_urls[:max_pins]
            
            self.total_count = len(pin_urls)
            self.update_log(f"📌 {self.total_count} pin URL'si bulundu")
            
            # Paralel indirme
            self.download_pins_parallel(pin_urls, parallel_downloads)
            
        except Exception as e:
            self.update_log(f"❌ TXT dosyası okuma hatası: {str(e)}")
            self.download_finished(False)
    
    def download_from_search(self, keyword, max_pins, parallel_downloads):
        """Arama kelimesi ile indirme"""
        try:
            self.update_log(f"🔍 '{keyword}' kelimesi ile arama yapılıyor...")
            
            # Çıktı klasörü oluştur
            output_dir = os.path.join(self.output_folder_field.value or "output", keyword.replace(" ", "_"))
            os.makedirs(output_dir, exist_ok=True)
            
            # Pinterest crawler'ı başlat
            crawler = PinterestCrawler(output_dir)
            
            # Pinterest crawler parametreleri:
            # keywords: arama kelimeleri listesi
            # number_of_words: her aramada kullanılacak kelime sayısı (varsayılan: 2)
            # max_images_per_keyword: kelime başına maksimum resim sayısı
            # max_keywords: işlenecek maksimum kelime kombinasyonu sayısı
            
            keywords = [keyword]  # Tek kelime listesi
            number_of_words = 1   # Tek kelime kullan
            max_images_per_keyword = max_pins or 50
            max_keywords = 1      # Tek kelime kombinasyonu
            
            self.update_log(f"📋 Arama parametreleri:")
            self.update_log(f"   - Kelime: {keyword}")
            self.update_log(f"   - Maksimum resim: {max_images_per_keyword}")
            self.update_log(f"   - Çıktı klasörü: {output_dir}")
            
            # Crawler'ı çalıştır
            crawler(keywords, number_of_words, max_images_per_keyword, max_keywords)
            
            # İndirilen dosyaları say
            downloaded_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
            downloaded_count = len(downloaded_files)
            
            if downloaded_count > 0:
                self.update_log(f"✅ {downloaded_count} resim başarıyla indirildi!")
                
                # Logo ekleme işlemi (arama ile indirilen dosyalar için)
                if self.use_logo_checkbox.value and self.logo_file_field.value:
                    logo_path = self.logo_file_field.value
                    if os.path.exists(logo_path):
                        self.update_log(f"🎨 İndirilen dosyalara logo ekleniyor...")
                        
                        for filename in downloaded_files:
                            file_path = os.path.join(output_dir, filename)
                            try:
                                self.update_log(f"🎨 Logo ekleniyor: {filename}")
                                
                                processed_file = None
                                
                                # Video dosyaları için
                                if file_path.endswith(('.mp4', '.avi', '.mov', '.webm')):
                                    processed_file = self.video_processor.add_logo_to_video(
                                        file_path, logo_path, output_dir
                                    )
                                # Resim dosyaları için
                                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                    processed_file = self.video_processor.add_logo_to_image(
                                        file_path, logo_path, output_dir
                                    )
                                
                                if processed_file and os.path.exists(processed_file):
                                    # Orijinal dosyayı sil ve yeni dosyayı eski adla yeniden adlandır
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    os.rename(processed_file, file_path)
                                    
                                    self.update_log(f"✅ Logo eklendi: {filename}")
                                else:
                                    self.update_log(f"⚠️ Logo eklenemedi: {filename}")
                            except Exception as e:
                                self.update_log(f"❌ Logo ekleme hatası ({filename}): {str(e)}")
                
                self.update_log(f"📁 İndirilen dosyalar: {output_dir}")
                self.download_finished(True)
            else:
                self.update_log(f"❌ '{keyword}' için resim bulunamadı")
                self.download_finished(False)
            
        except Exception as e:
            self.update_log(f"❌ Arama hatası: {str(e)}")
            import traceback
            self.update_log(f"Detaylı hata: {traceback.format_exc()}")
            self.download_finished(False)
    
    def download_pins_parallel(self, pin_urls, parallel_downloads):
        """Pinleri paralel olarak indir"""
        import concurrent.futures
        
        output_dir = self.output_folder_field.value or "output"
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
            futures = []
            
            for pin_url in pin_urls:
                if not self.is_downloading:
                    break
                
                future = executor.submit(self.download_single_pin, pin_url, output_dir)
                futures.append(future)
            
            # Sonuçları bekle
            for future in concurrent.futures.as_completed(futures):
                if not self.is_downloading:
                    break
                
                try:
                    success = future.result()
                    self.download_count += 1
                    
                    # Progress güncelle
                    progress = self.download_count / self.total_count
                    self.progress_bar.value = progress
                    self.progress_text.value = f"{self.download_count}/{self.total_count} pin indirildi"
                    
                    if self.page:
                        self.page.update()
                        
                except Exception as e:
                    self.update_log(f"❌ Pin indirme hatası: {str(e)}")
        
        if self.is_downloading:
            self.update_log(f"✅ Toplu indirme tamamlandı! {self.download_count}/{self.total_count} pin indirildi")
            self.download_finished(True)
        else:
            self.update_log("⏹️ İndirme durduruldu")
            self.download_finished(False)
    

    

    
    def download_finished(self, success):
        """İndirme işlemi tamamlandığında çağrılır"""
        self.is_downloading = False
        self.progress_bar.visible = False
        
        if success:
            self.status_text.value = "İndirme Tamamlandı!"
            self.status_text.color = ft.Colors.GREEN
        else:
            self.status_text.value = "İndirme Başarısız!"
            self.status_text.color = ft.Colors.RED
        
        if self.page:
            self.page.update()
    
    def download_single_pin(self, pin_url, output_dir):
        """Tek bir pin'i indir"""
        try:
            # Yeni request downloader ile pin'i indir
            downloaded_files = self.pinterest_downloader.download_pin(
                pin_url, 
                output_dir
            )
            
            if downloaded_files:
                # Logo ekleme (video ve resim dosyaları için)
                if self.use_logo_checkbox.value and self.logo_file_field.value:
                    logo_path = self.logo_file_field.value
                    if os.path.exists(logo_path):
                        for file_path in downloaded_files:
                            try:
                                if self.update_log:
                                    self.update_log(f"🎨 Logo ekleniyor: {os.path.basename(file_path)}")
                                
                                output_dir = os.path.dirname(file_path)
                                processed_file = None
                                
                                # Video dosyaları için
                                if file_path.endswith(('.mp4', '.avi', '.mov', '.webm')):
                                    processed_file = self.video_processor.add_logo_to_video(
                                        file_path, logo_path, output_dir
                                    )
                                # Resim dosyaları için
                                elif file_path.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                    processed_file = self.video_processor.add_logo_to_image(
                                        file_path, logo_path, output_dir
                                    )
                                
                                if processed_file and os.path.exists(processed_file):
                                    # Orijinal dosyayı sil ve yeni dosyayı eski adla yeniden adlandır
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    os.rename(processed_file, file_path)
                                    
                                    if self.update_log:
                                        self.update_log(f"✅ Logo eklendi: {os.path.basename(file_path)}")
                                else:
                                    if self.update_log:
                                        self.update_log(f"⚠️ Logo eklenemedi: {os.path.basename(file_path)}")
                            except Exception as e:
                                if self.update_log:
                                    self.update_log(f"❌ Logo ekleme hatası: {str(e)}")
                
                self.update_log(f"✅ Pin indirildi: {len(downloaded_files)} dosya")
                return True
            else:
                self.update_log(f"❌ Pin indirilemedi: {pin_url}")
                return False
            
        except Exception as e:
            self.update_log(f"❌ Pin indirme hatası: {str(e)}")
            return False
    
    def stop_download(self, e):
        """İndirmeyi durdur"""
        if self.is_downloading:
            self.is_downloading = False
            self.update_log("⏹️ İndirme durduruldu")
            self.download_finished(False)
    

    

    
    def close_window(self, page):
        """Pencereyi kapat"""
        try:
            if self.pinterest_downloader:
                self.pinterest_downloader.close()
            page.window_destroy()
        except:
            pass

if __name__ == "__main__":
    app = PinterestBulkDownloaderApp()
    ft.app(target=app.main)