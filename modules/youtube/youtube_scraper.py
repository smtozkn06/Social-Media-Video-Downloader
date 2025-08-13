import os
import time
import random
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import yt_dlp
import subprocess
import json
from urllib.parse import urlparse, parse_qs

class YouTubeScraper:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.driver = None
        
    def log(self, message):
        """Log mesajı gönder"""
        if self.log_callback:
            self.log_callback(message)
        print(message)
    
    def setup_driver(self):
        """Selenium WebDriver'ı kur"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.log("Chrome WebDriver başarıyla kuruldu")
            return driver
            
        except Exception as e:
            self.log(f"WebDriver kurulum hatası: {str(e)}")
            return None
    

    

    

    

    

    

    

    

    
    def extract_video_id_from_profile_url(self, profile_url):
        """Profil URL'sinden video ID'sini çıkar"""
        try:
            # YouTube video URL formatı: https://www.youtube.com/watch?v=VIDEO_ID
            if '/watch?' in profile_url:
                parsed_url = urlparse(profile_url)
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [None])[0]
                return video_id
            return None
        except:
            return None
    

    
    def download_video_as_mp3(self, video_url, output_folder, progress_callback=None, status_callback=None):
        """YouTube videosunu direkt MP3 olarak indir"""
        try:
            self.log(f"YouTube video MP3 olarak indiriliyor: {video_url}")
            
            if status_callback:
                status_callback("MP3 indiriliyor...")
            
            # yt-dlp seçenekleri - MP3 için
            ydl_opts = {
                'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
                'format': 'bestaudio/best',  # En iyi ses kalitesi
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,  # Hataları yoksay ve devam et
            }
            
            # Progress hook ekle
            if progress_callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        try:
                            percent = d.get('_percent_str', '0%')
                            speed = d.get('_speed_str', 'N/A')
                            self.log(f"MP3 İndirme: {percent} - Hız: {speed}")
                            
                            # Yüzdeyi sayısal değere çevir
                            percent_num = float(percent.replace('%', '')) / 100.0
                            progress_callback(percent_num)
                        except:
                            pass
                    elif d['status'] == 'finished':
                        self.log(f"MP3 indirme tamamlandı: {d['filename']}")
                        if progress_callback:
                            progress_callback(1.0)
                
                ydl_opts['progress_hooks'] = [progress_hook]
            
            # Çıktı klasörünü oluştur
            os.makedirs(output_folder, exist_ok=True)
            
            # İndirme öncesi dosya sayısını al
            files_before = set(os.listdir(output_folder)) if os.path.exists(output_folder) else set()
            
            # yt-dlp ile MP3 olarak indir
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if status_callback:
                status_callback("MP3 Tamamlandı")
            
            # İndirilen dosyayı bul
            files_after = set(os.listdir(output_folder)) if os.path.exists(output_folder) else set()
            new_files = files_after - files_before
            
            if new_files:
                # En son oluşturulan MP3 dosyasını bul
                latest_file = None
                latest_time = 0
                
                for file in new_files:
                    if file.lower().endswith('.mp3'):
                        file_path = os.path.join(output_folder, file)
                        if os.path.isfile(file_path):
                            file_time = os.path.getctime(file_path)
                            if file_time > latest_time:
                                latest_time = file_time
                                latest_file = file
                
                if latest_file:
                    latest_path = os.path.join(output_folder, latest_file)
                    self.log(f"MP3 dosyası bulundu: {latest_path}")
                    return latest_path
                        
            return None
            
        except Exception as e:
            self.log(f"MP3 indirme hatası: {str(e)}")
            if status_callback:
                status_callback(f"MP3 Hatası: {str(e)}")
            return None
    
    def download_video(self, video_url, output_folder, progress_callback=None, status_callback=None):
        """YouTube videosunu indir"""
        try:
            self.log(f"YouTube video indiriliyor: {video_url}")
            
            if status_callback:
                status_callback("İndiriliyor...")
            
            # yt-dlp seçenekleri
            ydl_opts = {
                'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
                'format': 'best[height<=720]/best',  # 720p veya daha düşük kalite
                'noplaylist': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                # Canlı yayın kontrolü kaldırıldı - yt-dlp kendi kontrolünü yapacak
                'ignoreerrors': True,  # Hataları yoksay ve devam et
            }
            
            # Progress hook ekle
            if progress_callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        try:
                            percent = d.get('_percent_str', '0%')
                            speed = d.get('_speed_str', 'N/A')
                            self.log(f"İndirme: {percent} - Hız: {speed}")
                            
                            # Yüzdeyi sayısal değere çevir
                            percent_num = float(percent.replace('%', '')) / 100.0
                            progress_callback(percent_num)
                        except:
                            pass
                    elif d['status'] == 'finished':
                        self.log(f"İndirme tamamlandı: {d['filename']}")
                        if progress_callback:
                            progress_callback(1.0)
                
                ydl_opts['progress_hooks'] = [progress_hook]
            
            # Çıktı klasörünü oluştur
            os.makedirs(output_folder, exist_ok=True)
            
            # İndirme öncesi dosya sayısını al
            files_before = set(os.listdir(output_folder)) if os.path.exists(output_folder) else set()
            
            # yt-dlp ile indir
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if status_callback:
                status_callback("Tamamlandı")
            
            # İndirilen dosyayı bul
            files_after = set(os.listdir(output_folder)) if os.path.exists(output_folder) else set()
            new_files = files_after - files_before
            
            if new_files:
                # En son oluşturulan dosyayı bul
                latest_file = None
                latest_time = 0
                
                for file in new_files:
                    file_path = os.path.join(output_folder, file)
                    if os.path.isfile(file_path):
                        file_time = os.path.getctime(file_path)
                        if file_time > latest_time:
                            latest_time = file_time
                            latest_file = file
                
                if latest_file:
                    latest_path = os.path.join(output_folder, latest_file)
                    self.log(f"Video dosyası bulundu: {latest_path}")
                    return latest_path
                        
            return None
            
        except Exception as e:
            self.log(f"Video indirme hatası: {str(e)}")
            if status_callback:
                status_callback(f"Hata: {str(e)}")
            return None
            
    def sanitize_filename(self, filename):
        """Dosya adını temizle"""
        # Geçersiz karakterleri kaldır
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Uzunluğu sınırla
        if len(filename) > 100:
            filename = filename[:100]
            
        return filename.strip()
    
    def scrape_channel_videos(self, channel_url, max_videos=20):
        """YouTube kanalından video URL'lerini topla"""
        try:
            self.log(f"YouTube kanalından videolar alınıyor: {channel_url}")
            
            driver = self.setup_driver()
            if not driver:
                return []
            
            video_urls = []
            
            # Kanal videolar sayfasına git
            if '/videos' not in channel_url:
                if channel_url.endswith('/'):
                    channel_url = channel_url + 'videos'
                else:
                    channel_url = channel_url + '/videos'
            
            driver.get(channel_url)
            time.sleep(3)
            
            # Sayfayı scroll yaparak daha fazla video yükle
            self.log("Kanal sayfası kaydırılıyor...")
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
            
            # Video linklerini topla
            video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/watch?"]')
            
            self.log(f"Kanalda {len(video_elements)} video elementi bulundu")
            
            for element in video_elements[:max_videos]:
                try:
                    video_url = element.get_attribute('href')
                    if video_url and '/watch?' in video_url:
                        # URL'yi temizle
                        if '&' in video_url:
                            video_url = video_url.split('&')[0]
                        video_urls.append(video_url)
                        self.log(f"Kanal videosu: {video_url}")
                except:
                    continue
            
            self.log(f"Kanaldan {len(video_urls)} video URL'si toplandı")
            
            driver.quit()
            return video_urls
                
        except Exception as e:
            self.log(f"Kanal scraping hatası: {str(e)}")
            if 'driver' in locals():
                driver.quit()
            return []
    
    def extract_username_from_url(self, channel_url):
        """Kanal URL'sinden kullanıcı adını çıkar"""
        try:
            # https://www.youtube.com/c/username veya https://www.youtube.com/@username formatından username'i çıkar
            if '/c/' in channel_url:
                match = re.search(r'/c/([^/?]+)', channel_url)
            elif '/@' in channel_url:
                match = re.search(r'/@([^/?]+)', channel_url)
            elif '/channel/' in channel_url:
                match = re.search(r'/channel/([^/?]+)', channel_url)
            else:
                return None
                
            if match:
                return match.group(1)
            return None
        except:
            return None