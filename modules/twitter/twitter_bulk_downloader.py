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
import tempfile
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import imageio_ffmpeg
from .twitter_scraper import TwitterScraper
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from video_processor import VideoProcessor
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from .getMetadata import get_metadata

# HTTP/API tabanlı kütüphaneler için koşullu importlar
try:
    import twikit
    TWIKIT_AVAILABLE = True
except ImportError:
    TWIKIT_AVAILABLE = False

try:
    import snscrape.modules.twitter as sntwitter
    SNSCRAPE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    SNSCRAPE_AVAILABLE = False
    print(f"Snscrape bulunamadı veya uyumsuz: {e}")

@dataclass
class Account:
    username: str
    nick: str
    followers: int
    following: int
    posts: int
    media_type: str
    profile_image: str = None
    media_list: list = None
    selected: bool = True

class TwitterMediaDownloadWorker:
    def __init__(self, accounts, outpath, auth_token, filename_format='username_date',
                 download_batch_size=25, convert_gif=False, gif_resolution='original',
                 progress_callback=None, log_callback=None, logo_file=None, use_logo=False):
        self.accounts = accounts
        self.outpath = outpath
        self.auth_token = auth_token
        self.filename_format = filename_format
        self.download_batch_size = download_batch_size
        self.convert_gif = convert_gif
        self.gif_resolution = gif_resolution
        self.is_paused = False
        self.is_stopped = False
        self.filepath_map = []
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.logo_file = logo_file
        self.use_logo = use_logo
        self.video_processor = VideoProcessor()

    async def download_file(self, session, url, filepath):
        try:
            if os.path.exists(filepath):
                return True, True
            if self.is_stopped:
                return False, False
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    return True, False
                return False, False
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Dosya indirme hatası: {str(e)}")
            return False, False

    async def download_account_media(self, account):
        if not account.media_list:
            return 0, 0, 0
            
        account_output_dir = os.path.join(self.outpath, account.username)
        os.makedirs(account_output_dir, exist_ok=True)        
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=self.download_batch_size)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:            
            total = len(account.media_list)
            completed = 0
            skipped = 0
            failed = 0
            
            used_filenames = set()
            
            for i in range(0, total, self.download_batch_size):
                if self.is_stopped:
                    break
                    
                while self.is_paused:
                    if self.is_stopped:
                        return completed, skipped, failed
                    await asyncio.sleep(0.1)
                
                batch = account.media_list[i:i + self.download_batch_size]
                tasks = []
                
                for item in batch:
                    url = item['url']
                    date = datetime.strptime(item['date'], "%Y-%m-%d %H:%M:%S")
                    formatted_date = date.strftime("%Y%m%d_%H%M%S")
                    tweet_id = str(item.get('tweet_id', ''))
                    
                    item_type = item.get('type', '')
                    if item_type == 'animated_gif':
                        media_type_folder = 'gif'
                        extension = 'mp4'
                    elif item_type == 'video' or 'video.twimg.com' in url:
                        media_type_folder = 'video'
                        extension = 'mp4'
                    else:
                        media_type_folder = 'image'
                        extension = 'jpg'
                    media_output_dir = os.path.join(account_output_dir, media_type_folder)
                    
                    if self.filename_format == "username_date":
                        base_filename = f"{account.username}_{formatted_date}_{tweet_id}"
                    else:
                        base_filename = f"{formatted_date}_{account.username}_{tweet_id}"
                    
                    filename = f"{base_filename}.{extension}"
                    counter = 1
                    while filename in used_filenames:
                        filename = f"{base_filename}_{counter:02d}.{extension}"
                        counter += 1
                    
                    used_filenames.add(filename)
                    filepath = os.path.join(media_output_dir, filename)
                    self.filepath_map.append((item, filepath))
                    task = asyncio.create_task(self.download_file(session, url, filepath))
                    tasks.append(task)
                    
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, tuple):
                        success, was_skipped = result
                        if success:
                            completed += 1
                            if was_skipped:
                                skipped += 1
                            else:
                                # Logo ekleme işlemi (video ve resim dosyaları için)
                                if self.use_logo and self.logo_file and i < len(batch):
                                    item = batch[i]
                                    item_type = item.get('type', '')
                                    
                                    # İlgili dosya yolunu bul
                                    for file_item, filepath in self.filepath_map:
                                        if file_item == item:
                                            try:
                                                if self.log_callback:
                                                    self.log_callback(f"🎨 Logo ekleniyor: {os.path.basename(filepath)}")
                                                
                                                output_dir = os.path.dirname(filepath)
                                                processed_file = None
                                                
                                                # Video dosyaları için
                                                if (item_type == 'video' or item_type == 'animated_gif' or 'video.twimg.com' in item['url']) and filepath.endswith('.mp4'):
                                                    processed_file = self.video_processor.add_logo_to_video(
                                                        filepath, self.logo_file, output_dir
                                                    )
                                                # Resim dosyaları için
                                                elif filepath.endswith(('.jpg', '.jpeg', '.png')):
                                                    processed_file = self.video_processor.add_logo_to_image(
                                                        filepath, self.logo_file, output_dir
                                                    )
                                                
                                                if processed_file and os.path.exists(processed_file):
                                                    # Orijinal dosyayı sil ve yeni dosyayı eski adla yeniden adlandır
                                                    if os.path.exists(filepath):
                                                        os.remove(filepath)
                                                    os.rename(processed_file, filepath)
                                                    
                                                    if self.log_callback:
                                                        self.log_callback(f"✅ Logo eklendi: {os.path.basename(filepath)}")
                                                else:
                                                    if self.log_callback:
                                                        self.log_callback(f"⚠️ Logo eklenemedi: {os.path.basename(filepath)}")
                                            except Exception as e:
                                                if self.log_callback:
                                                    self.log_callback(f"❌ Logo ekleme hatası: {str(e)}")
                                            break
                        else:
                            failed += 1
                    else:
                        failed += 1
                    
                    progress_percent = (completed + failed) / total
                    media_type_display = account.media_type if account.media_type != 'all' else 'medya'
                    if self.progress_callback:
                        self.progress_callback(completed + failed, total, f"{account.username} {media_type_display}")
                
                await asyncio.sleep(0.1)
            
            return completed, skipped, failed

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self): 
        self.is_stopped = True
        self.is_paused = False
    
    async def start_download(self):
        """İndirme işlemini başlat"""
        if self.log_callback:
            self.log_callback("📥 İndirme başlatılıyor...")
        
        total_completed = 0
        total_skipped = 0
        total_failed = 0
        
        for account in self.accounts:
            if self.is_stopped:
                break
                
            if self.log_callback:
                self.log_callback(f"📂 {account.username} hesabı indiriliyor...")
            
            completed, skipped, failed = await self.download_account_media(account)
            total_completed += completed
            total_skipped += skipped
            total_failed += failed
            
            if self.log_callback:
                self.log_callback(f"✅ {account.username}: {completed} başarılı, {skipped} atlandı, {failed} başarısız")
        
        if self.log_callback:
            self.log_callback(f"🎉 İndirme tamamlandı! Toplam: {total_completed} başarılı, {total_skipped} atlandı, {total_failed} başarısız")
        
        return total_completed, total_skipped, total_failed

class TwitterBulkDownloaderApp:
    def __init__(self):
        self.scraper = TwitterScraper(log_callback=self.add_log, bulk_downloader=self)
        self.video_processor = VideoProcessor()
        self.is_downloading = False
        self.page = None
        self.accounts = []
        self.download_worker = None
        self.auth_token = "d3e0291592fa280c0e9c6cb8111a42680aeea534"
        self.current_page = 0
        self.is_fetching = False
        # HTTP/API yöntemi varsayılan olarak kullanılıyor
    

    
    async def fetch_account_data(self, e):
        """Hesap verilerini çek - tüm medyaları cursor tabanlı sayfalama ile çek"""
        if self.is_fetching:
            return
            
        username = self.username_field.value.strip()
        
        if not username:
            self.add_log("❌ Kullanıcı adı gerekli")
            return
            
        self.is_fetching = True
        self.fetch_button.disabled = True
        self.status_text.value = "Hesap bilgileri çekiliyor..."
        self.status_text.color = ft.Colors.ORANGE
        self.page.update()
        
        try:
            # URL'den kullanıcı adını çıkar
            if username.startswith('http'):
                username = username.split('/')[-1]
            username = username.replace('@', '')
            
            # Tüm medyaları tek seferde çek - büyük batch size ile
            self.add_log(f"📥 @{username} hesabının tüm medyaları çekiliyor...")
            
            # Büyük batch size ile tek seferde çekmeye çalış
            result = await asyncio.to_thread(
                get_metadata,
                username=username,
                auth_token=self.auth_token,
                timeline_type="media",
                batch_size=50000,  # Çok büyük batch size - tüm medyaları çekmek için
                page=0,
                media_type=self.media_type_dropdown.value
            )
            
            if result and 'error' in result:
                self.add_log(f"❌ {result['error']}")
                self.status_text.value = "Hesap bulunamadı veya erişim reddedildi"
                self.status_text.color = ft.Colors.RED
                return
                
            if not result or 'account_info' not in result:
                self.add_log("❌ Hesap bulunamadı veya erişim reddedildi")
                self.status_text.value = "Hesap bulunamadı"
                self.status_text.color = ft.Colors.RED
                return
            
            account_info = result['account_info']
            total_posts = account_info.get('statuses_count', 0)
            self.add_log(f"📊 Hesap toplam gönderi sayısı: {total_posts}")
            
            all_media = result.get('timeline', [])
            total_fetched = len(all_media)
            
            metadata = result.get('metadata', {})
            items_fetched = metadata.get('items_fetched', 0)
            
            self.add_log(f"📄 {items_fetched} gönderi tarandı, {total_fetched} medya bulundu")
            self.add_log(f"✅ Tüm medyalar çekildi! Toplam: {total_fetched} medya")
            
            if account_info and all_media:
                account = Account(
                    username=account_info.get('nick', username),
                    nick=account_info.get('name', username),
                    followers=account_info.get('followers_count', 0),
                    following=account_info.get('friends_count', 0),
                    posts=len(all_media),
                    media_type=self.media_type_dropdown.value,
                    media_list=all_media
                )
                
                self.accounts.append(account)
                self.update_account_list()
                
                self.add_log(f"✅ Hesap bulundu: @{account.username} ({account.posts} medya)")
                self.status_text.value = "Hesap başarıyla eklendi"
                self.status_text.color = ft.Colors.GREEN
                self.download_button.disabled = False
            elif account_info:
                # Hesap var ama medya yok
                account = Account(
                    username=account_info.get('nick', username),
                    nick=account_info.get('name', username),
                    followers=account_info.get('followers_count', 0),
                    following=account_info.get('friends_count', 0),
                    posts=0,
                    media_type=self.media_type_dropdown.value,
                    media_list=[]
                )
                
                self.accounts.append(account)
                self.update_account_list()
                
                self.add_log(f"✅ Hesap bulundu: @{account.username} (0 medya)")
                self.status_text.value = "Hesap eklendi (medya yok)"
                self.status_text.color = ft.Colors.ORANGE
                
        except Exception as ex:
            self.add_log(f"❌ Hata: {str(ex)}")
            self.status_text.value = "Hata oluştu"
            self.status_text.color = ft.Colors.RED
        finally:
            self.is_fetching = False
            self.fetch_button.disabled = False
            self.page.update()
    
    def update_account_list(self):
        """Hesap listesini güncelle"""
        self.account_list.controls.clear()
        
        for i, account in enumerate(self.accounts):
            account_card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"@{account.username}", weight=ft.FontWeight.BOLD),
                            ft.Text(f"{account.nick}", size=12, color=ft.Colors.GREY_600),
                            ft.Text(f"Takipçi: {account.followers:,} | Takip: {account.following:,}", size=10),
                            ft.Text(f"Medya: {account.posts} ({account.media_type})", size=10, color=ft.Colors.BLUE)
                        ], expand=True),
                        ft.Column([
                            ft.Checkbox(
                                value=True,
                                on_change=lambda e, idx=i: self.toggle_account_selection(idx, e.control.value)
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                on_click=lambda e, idx=i: self.remove_account(idx),
                                icon_color=ft.Colors.RED
                            )
                        ])
                    ]),
                    padding=10
                )
            )
            self.account_list.controls.append(account_card)
        
        self.page.update()
    
    def toggle_account_selection(self, index, selected):
        """Hesap seçimini değiştir"""
        if 0 <= index < len(self.accounts):
            self.accounts[index].selected = selected
    
    def remove_account(self, index):
        """Hesabı listeden kaldır"""
        if 0 <= index < len(self.accounts):
            removed_account = self.accounts.pop(index)
            self.add_log(f"🗑️ Hesap kaldırıldı: @{removed_account.username}")
            self.update_account_list()
            
            if not self.accounts:
                self.download_button.disabled = True
                self.page.update()
        
    def main(self, page: ft.Page):
        page.title = "Twitter/X Medya Toplu İndirici"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 900
        page.window_height = 1000
        page.window_resizable = True
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        
        self.page = page
        
        # UI Bileşenleri
        self.username_field = ft.TextField(
            label="Kullanıcı Adı/URL",
            hint_text="Örn: username veya https://x.com/username",
            width=500,
            prefix_icon=ft.Icons.PERSON
        )
        
        # Sabit auth token kullan
        self.auth_token = "d3e0291592fa280c0e9c6cb8111a42680aeea534"
        
        self.auth_token_field = ft.TextField(
            label="Auth Token (Otomatik)",
            hint_text="Auth token otomatik olarak ayarlandı",
            width=500,
            password=True,
            prefix_icon=ft.Icons.KEY,
            value=self.auth_token,
            read_only=True,
            disabled=True
        )
        
        # Medya türü seçimi
        self.media_type_dropdown = ft.Dropdown(
            label="Medya Türü",
            width=200,
            options=[
                ft.dropdown.Option("all", "Tümü"),
                ft.dropdown.Option("image", "Resimler"),
                ft.dropdown.Option("video", "Videolar"),
                ft.dropdown.Option("gif", "GIF'ler")
            ],
            value="all"
        )
        
        # Batch boyutu kaldırıldı - artık sınırsız
        
        # İndirme modu seçimi
        self.download_mode = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="search", label="Arama ile İndir"),
                ft.Radio(value="user", label="Kullanıcı Adı ile İndir")
            ]),
            value="search",
            on_change=self.on_download_mode_change
        )
        
        # Username alanı her zaman görünür
        self.username_field.visible = True
        

        
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
        
        # Fetch butonu
        self.fetch_button = ft.ElevatedButton(
            "Hesap Bilgilerini Çek",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.fetch_account_data_wrapper,
            disabled=False
        )
        
        # Hesap listesi
        self.account_list = ft.ListView(
            height=200,
            spacing=5,
            padding=ft.padding.all(10)
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
        
        page.overlay.extend([logo_file_picker, output_folder_picker])
        
        self.logo_button = ft.ElevatedButton(
            "Seç",
            icon=ft.Icons.IMAGE,
            on_click=lambda _: logo_file_picker.pick_files(
                allowed_extensions=["png"]
            ),
            visible=True
        )
        
        # İndirme butonları
        self.download_button = ft.ElevatedButton(
            "Seçili Hesapları İndir",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.start_download_wrapper,
            disabled=True
        )
        
        self.pause_button = ft.ElevatedButton(
            "Duraklat",
            icon=ft.Icons.PAUSE,
            on_click=self.pause_download,
            disabled=True,
            color=ft.Colors.ORANGE
        )
        
        self.resume_button = ft.ElevatedButton(
            "Devam Et",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.resume_download,
            disabled=True,
            color=ft.Colors.GREEN
        )
        
        self.stop_button = ft.ElevatedButton(
            "Durdur",
            icon=ft.Icons.STOP,
            on_click=self.stop_download,
            disabled=True,
            color=ft.Colors.RED
        )
        
        # İlerleme çubuğu
        self.progress_bar = ft.ProgressBar(
            width=600,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.GREY_300,
            visible=False
        )
        
        # Durum metinleri
        self.status_text = ft.Text(
            "Hazır",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN
        )
        
        self.download_status_text = ft.Text(
            "",
            size=14,
            color=ft.Colors.BLUE
        )
        
        self.time_label = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_700
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
        
        # Ana layout
        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Twitter/X Medya Toplu İndirici",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700
                        ),
                        ft.Text(
                            "Twitter/X hesaplarından medya dosyalarını toplu olarak indirin",
                            size=14,
                            color=ft.Colors.GREY_600
                        )
                    ]),
                    padding=20,
                    margin=ft.margin.only(bottom=20)
                ),
                
                # Hesap bilgileri girişi
                ft.Container(
                    content=ft.Column([
                        ft.Text("Hesap Bilgileri", size=16, weight=ft.FontWeight.BOLD),
                        self.username_field,
                        self.auth_token_field,
                        ft.Row([
                            self.media_type_dropdown,
                            self.fetch_button
                        ])
                    ]),
                    padding=10,
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Hesap listesi
                ft.Container(
                    content=ft.Column([
                        ft.Text("Bulunan Hesaplar", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=self.account_list,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=5
                        )
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
                    margin=ft.margin.only(bottom=10)
                ),
                
                # Paralel indirme ayarları
                ft.Container(
                    content=ft.Row([
                        self.parallel_batch_size_field
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
                
                # İndirme butonları
                ft.Container(
                    content=ft.Row([
                        self.download_button,
                        self.pause_button,
                        self.resume_button,
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
                        self.download_status_text,
                        self.time_label,
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
    
    def on_download_mode_change(self, e):
        """İndirme modu değiştiğinde çağrılır"""
        mode = e.control.value
        
        # Tüm alanları gizle (username alanı hariç)
        self.search_field.visible = False
        self.username_field.visible = True  # Username alanı her zaman görünür
        self.video_count_field.visible = False
        
        # Seçilen moda göre alanları göster
        if mode == "search":
            self.search_field.visible = True
            self.video_count_field.visible = True
        elif mode == "user":
            self.username_field.visible = True
            self.video_count_field.visible = True
        
        self.page.update()
    
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
    
    def update_stats(self, message):
        """İstatistik metnini günceller"""
        self.stats_text.value = message
        self.page.update()
    
    def update_progress(self, value):
        """İlerleme çubuğunu günceller"""
        self.progress_bar.value = value
        self.page.update()
    
    async def start_download(self, e):
        """Seçili hesapları indir"""
        if self.is_downloading:
            return
            
        selected_accounts = [acc for acc in self.accounts if getattr(acc, 'selected', True)]
        if not selected_accounts:
            self.add_log("❌ İndirilecek hesap seçilmedi")
            return
            
        self.is_downloading = True
        self.download_button.disabled = True
        self.pause_button.disabled = False
        self.stop_button.disabled = False
        
        self.progress_bar.visible = True
        self.status_text.value = "İndirme başlatılıyor..."
        self.status_text.color = ft.Colors.BLUE
        self.page.update()
        
        try:
            output_dir = self.output_folder_field.value
            os.makedirs(output_dir, exist_ok=True)
            
            # Download worker'ı başlat
            self.download_worker = TwitterMediaDownloadWorker(
                accounts=selected_accounts,
                outpath=output_dir,
                auth_token=self.auth_token,
                download_batch_size=int(self.parallel_batch_size_field.value or 10),
                progress_callback=self.update_download_progress,
                log_callback=self.add_log,
                logo_file=self.logo_file_field.value if self.use_logo_checkbox.value else None,
                use_logo=self.use_logo_checkbox.value
            )
            
            # İndirme işlemini başlat
            await self.start_download_worker()
            
        except Exception as ex:
            self.add_log(f"❌ İndirme hatası: {str(ex)}")
            self.status_text.value = "İndirme hatası"
            self.status_text.color = ft.Colors.RED
        finally:
            self.is_downloading = False
            self.download_button.disabled = False
            self.pause_button.disabled = True
            self.resume_button.disabled = True
            self.stop_button.disabled = True
            self.progress_bar.visible = False
            self.page.update()
    
    def pause_download(self, e):
        """İndirmeyi duraklat"""
        if self.download_worker:
            self.download_worker.pause()
            self.pause_button.disabled = True
            self.resume_button.disabled = False
            self.status_text.value = "İndirme duraklatıldı"
            self.status_text.color = ft.Colors.ORANGE
            self.page.update()
            self.add_log("⏸️ İndirme duraklatıldı")
    
    def resume_download(self, e):
        """İndirmeyi devam ettir"""
        if self.download_worker:
            self.download_worker.resume()
            self.pause_button.disabled = False
            self.resume_button.disabled = True
            self.status_text.value = "İndirme devam ediyor"
            self.status_text.color = ft.Colors.BLUE
            self.page.update()
            self.add_log("▶️ İndirme devam ediyor")
    
    def stop_download(self, e):
        """İndirme işlemini durdur"""
        if self.download_worker:
            self.download_worker.stop()
            
        self.is_downloading = False
        self.download_button.disabled = False
        self.pause_button.disabled = True
        self.resume_button.disabled = True
        self.stop_button.disabled = True
        self.progress_bar.visible = False
        self.status_text.value = "İndirme durduruldu"
        self.status_text.color = ft.Colors.RED
        self.page.update()
        self.add_log("🛑 İndirme işlemi durduruldu")
    
    def update_download_progress(self, current, total, filename=""):
        """İndirme ilerlemesini güncelle"""
        if total > 0:
            progress = current / total
            self.progress_bar.value = progress
            
            if filename:
                self.download_status_text.value = f"İndiriliyor: {filename}"
            else:
                self.download_status_text.value = f"İlerleme: {current}/{total}"
                
            self.page.update()
    
    def update_download_status(self, status, color=None):
        """İndirme durumunu güncelle"""
        self.status_text.value = status
        if color:
            self.status_text.color = color
        
        # Zaman etiketi güncelle
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.value = f"Son güncelleme: {current_time}"
        
        self.page.update()
    
    async def start_download_worker(self):
        """Download worker'ı başlat"""
        if self.download_worker:
            await self.download_worker.start_download()
     
    def fetch_account_data_wrapper(self, e):
        """Fetch account data wrapper for threading"""
        import threading
        thread = threading.Thread(target=lambda: asyncio.run(self.fetch_account_data(e)))
        thread.daemon = True
        thread.start()
    
    def start_download_wrapper(self, e):
        """Start download wrapper for threading"""
        import threading
        thread = threading.Thread(target=lambda: asyncio.run(self.start_download(e)))
        thread.daemon = True
        thread.start()
    


if __name__ == "__main__":
    import asyncio
    import sys
    
    # Windows'ta asyncio subprocess sorununu çöz
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    app = TwitterBulkDownloaderApp()
    ft.app(target=app.main, view=ft.AppView.FLET_APP)