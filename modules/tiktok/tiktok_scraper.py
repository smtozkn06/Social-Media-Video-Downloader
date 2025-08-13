import os
import time
import random
import requests
import yt_dlp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path

class TikTokScraper:
    def __init__(self, log_callback=None, bulk_downloader=None):
        self.base_url = "https://www.tiktok.com/search?q="
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.log_callback = log_callback
        self.bulk_downloader = bulk_downloader
        
    def log(self, message):
        """Log mesajı gönder"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
        
    def setup_driver(self):
        """Selenium WebDriver'ı ayarla - bulk_downloader'dan setup_selenium metodunu kullan"""
        try:
            # Eğer bulk_downloader referansı varsa onun setup_selenium metodunu kullan
            if self.bulk_downloader and hasattr(self.bulk_downloader, 'setup_selenium'):
                return self.bulk_downloader.setup_selenium(for_login=False)
            else:
                # Fallback: Basit WebDriver kurulumu
                chrome_options = Options()
                
                # Temel ayarlar
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-images')
                
                # Anti-bot tespiti
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # User-Agent ayarla
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # WebDriver oluştur
                driver = webdriver.Chrome(options=chrome_options)
                
                # WebDriver tespitini engelle
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                return driver
            
        except Exception as e:
            self.log(f"WebDriver kurulum hatası: {str(e)}")
            return None
            
    def search_videos(self, search_query, max_videos=5):
        """TikTok'ta video ara ve URL'leri topla"""
        self.log(f"TikTok'ta '{search_query}' aranıyor...")
        
        driver = self.setup_driver()
        if not driver:
            return []
            
        video_urls = []
        
        try:
            # TikTok arama sayfasına git
            search_url = f"{self.base_url}{search_query}"
            self.log(f"Arama URL'si: {search_url}")
            
            driver.get(search_url)
            time.sleep(3)
            
            # 15 saniye boyunca aşağı scroll yap (daha fazla video yüklemek için)
            self.log("15 saniye boyunca sayfa kaydırılıyor...")
            scroll_duration = 15
            scroll_interval = 0.3
            scroll_count = int(scroll_duration / scroll_interval)
            
            for i in range(scroll_count):
                # Daha fazla içerik yüklemek için farklı scroll miktarları
                if i % 3 == 0:
                    driver.execute_script("window.scrollBy(0, 800);")
                else:
                    driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(scroll_interval)
                
                # Her 10 scroll'da bir sayfanın sonuna git
                if i % 10 == 0:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                
            # Sayfanın yüklenmesini bekle
            time.sleep(2)
            
            # Video linklerini topla
            video_elements = self.find_video_elements(driver)
            
            self.log(f"{len(video_elements)} video elementi bulundu")
            
            # Her video için bilgileri topla
            for i, element in enumerate(video_elements[:max_videos]):
                try:
                    video_data = self.extract_video_data(driver, element)
                    if video_data and video_data['url']:
                        video_urls.append(video_data)
                        self.log(f"Video {i+1}: {video_data['url']} - İzlenme: {video_data['views']}")
                        
                except Exception as e:
                    self.log(f"Video {i+1} veri çıkarma hatası: {str(e)}")
                    continue
                    
            # İzlenme sayısına göre sırala (en çok izlenen önce)
            video_urls.sort(key=lambda x: self.parse_view_count(x['views']), reverse=True)
            
            self.log(f"Toplam {len(video_urls)} video URL'si toplandı")
            
        except Exception as e:
            self.log(f"Video arama hatası: {str(e)}")
            
        finally:
            driver.quit()
            
        return [video['url'] for video in video_urls]
        
    def find_video_elements(self, driver):
        """Sayfadaki video elementlerini bul"""
        video_elements = []
        
        # Farklı seçiciler dene (daha kapsamlı)
        selectors = [
            '[data-e2e="search_top-item"]',  # Yeni TikTok seçicisi
            '[data-e2e="search-card-item"]',
            '[data-e2e="search-card"]',
            '[data-e2e="video-card"]',
            'div[data-e2e*="search"]',
            'div[data-e2e*="video"]',
            'div[data-e2e*="item"]',
            'a[href*="/video/"]',
            'div[class*="DivContainer"]',  # TikTok'un yeni class yapısı
            'div[class*="video"]',
            'div[class*="item"]',
            'div[class*="Card"]',
            '[role="button"]',  # Video kartları genelde button rolü taşır
            'div[tabindex="0"]'  # Tıklanabilir video elementleri
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self.log(f"'{selector}' ile {len(elements)} element bulundu")
                    video_elements.extend(elements)
                    break
            except:
                continue
                
        # Eğer hiç element bulunamazsa, daha kapsamlı arama yap
        if not video_elements:
            self.log("Standart seçicilerle video bulunamadı, alternatif yöntemler deneniyor...")
            
            # Tüm linkleri kontrol et
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            video_links = []
            for link in all_links:
                href = link.get_attribute('href')
                if href and ('/video/' in href or ('/@' in href and '/video/' in href)):
                    video_links.append(link)
            
            # Tıklanabilir div elementlerini kontrol et
            clickable_divs = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"], div[tabindex="0"]')
            for div in clickable_divs:
                # İçinde video linki olan div'leri bul
                try:
                    inner_link = div.find_element(By.CSS_SELECTOR, 'a[href*="/video/"]')
                    if inner_link:
                        video_links.append(div)
                except:
                    continue
            
            video_elements = video_links[:max_videos*2]  # Daha fazla element al
            
        return video_elements
        
    def extract_video_data(self, driver, element):
        """Video elementinden veri çıkar"""
        try:
            # Video URL'sini bul
            video_url = None
            
            # Element'in kendisi link mi?
            if element.tag_name == 'a':
                video_url = element.get_attribute('href')
            else:
                # Element içinde link ara
                link_element = element.find_element(By.CSS_SELECTOR, 'a[href*="/video/"], a[href*="/@"]')
                if link_element:
                    video_url = link_element.get_attribute('href')
                    
            if not video_url:
                return None
                
            # Video URL'sini düzelt
            if '/video/' not in video_url and '/@' in video_url:
                # Profil linkinden video linkine çevir
                video_id = self.extract_video_id_from_profile_url(video_url)
                if video_id:
                    username = video_url.split('/@')[1].split('/')[0]
                    video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
                    
            # İzlenme sayısını bul
            views = self.extract_view_count(element)
            
            # Başlığı bul
            title = self.extract_title(element)
            
            return {
                'url': video_url,
                'views': views,
                'title': title
            }
            
        except Exception as e:
            self.log(f"Video veri çıkarma hatası: {str(e)}")
            return None
            
    def extract_view_count(self, element):
        """İzlenme sayısını çıkar"""
        try:
            # İzlenme sayısı için farklı seçiciler
            view_selectors = [
                '[data-e2e="browse-like-count"]',
                '[data-e2e="video-views"]',
                'strong[data-e2e*="count"]',
                'span[data-e2e*="count"]',
                'strong[class*="count"]',
                'span[class*="count"]'
            ]
            
            for selector in view_selectors:
                try:
                    view_element = element.find_element(By.CSS_SELECTOR, selector)
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
        """Video başlığını çıkar"""
        try:
            # Başlık için farklı seçiciler
            title_selectors = [
                '[data-e2e="browse-video-desc"]',
                '[data-e2e="video-desc"]',
                'div[class*="desc"]',
                'div[class*="caption"]',
                'span[class*="desc"]'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 5:
                        return title_text[:100]  # İlk 100 karakter
                except:
                    continue
                    
            return "TikTok Video"
            
        except:
            return "TikTok Video"
            
    def extract_video_id_from_profile_url(self, url):
        """Profil URL'sinden video ID'sini çıkar"""
        try:
            # URL'den uzun sayısal ID'yi ara
            match = re.search(r'/(\d{15,})', url)
            if match:
                return match.group(1)
            return None
        except:
            return None
            
    def parse_view_count(self, view_text):
        """İzlenme sayısını sayısal değere çevir"""
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
            
    def download_video(self, video_url, output_folder):
        """yt-dlp kullanarak video indir"""
        try:
            self.log(f"Video indiriliyor: {video_url}")
            
            # yt-dlp ayarları
            ydl_opts = {
                'outtmpl': os.path.join(output_folder, '%(title)s_%(id)s.%(ext)s'),
                'format': 'best[height<=1920]',  # En iyi kalite, max 1920p
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
                'no_warnings': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'subtitleslangs': ['tr', 'en'],
                'cookiefile': None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Video bilgilerini al
                info = ydl.extract_info(video_url, download=False)
                
                if info:
                    # Video indir
                    ydl.download([video_url])
                    
                    # İndirilen dosyayı bul
                    video_title = info.get('title', 'video')
                    video_id = info.get('id', 'unknown')
                    
                    # Dosya adını temizle
                    safe_title = self.sanitize_filename(video_title)
                    
                    # Olası dosya uzantıları
                    extensions = ['.mp4', '.webm', '.mkv', '.avi']
                    
                    for ext in extensions:
                        possible_path = os.path.join(output_folder, f"{safe_title}_{video_id}{ext}")
                        if os.path.exists(possible_path):
                            self.log(f"Video başarıyla indirildi: {possible_path}")
                            return possible_path
                            
                    # Eğer tam dosya adı bulunamazsa, klasördeki en son dosyayı kontrol et
                    files = os.listdir(output_folder)
                    video_files = [f for f in files if any(f.endswith(ext) for ext in extensions)]
                    
                    if video_files:
                        # En son oluşturulan dosyayı al
                        latest_file = max(video_files, key=lambda x: os.path.getctime(os.path.join(output_folder, x)))
                        latest_path = os.path.join(output_folder, latest_file)
                        self.log(f"Video dosyası bulundu: {latest_path}")
                        return latest_path
                        
            return None
            
        except Exception as e:
            self.log(f"Video indirme hatası: {str(e)}")
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
    
    def scrape_profile_videos_with_requests(self, profile_url, max_videos=20, cookies=None):
        """Request tabanlı profil video scraping - tarayıcı açmadan"""
        try:
            self.log(f"Request ile profil videoları alınıyor: {profile_url}")
            
            # Profil URL'sinden kullanıcı adını çıkar
            username = self.extract_username_from_url(profile_url)
            if not username:
                self.log("Geçersiz profil URL'si")
                return []
            
            # TikTok API endpoint'i (unofficial)
            api_url = f"https://www.tiktok.com/api/post/item_list/"
            
            # Request headers - gerçek tarayıcıyı taklit et
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': profile_url,
                'Origin': 'https://www.tiktok.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Cookie'leri ekle
            session = requests.Session()
            if cookies:
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', '.tiktok.com'))
            
            # API parametreleri
            params = {
                'secUid': '',  # Bu değer profil sayfasından alınmalı
                'userId': '',  # Bu değer profil sayfasından alınmalı
                'count': min(max_videos, 30),  # Maksimum 30 video per request
                'cursor': '0',
                'type': '1',
                'minCursor': '0',
                'maxCursor': '0',
                'shareUid': '',
                'lang': 'en'
            }
            
            # Önce profil sayfasını ziyaret ederek secUid ve userId'yi al
            profile_data = self.get_profile_data_with_requests(profile_url, session, headers)
            if not profile_data:
                self.log("Profil verileri alınamadı, Selenium yöntemine geçiliyor...")
                return self.scrape_profile_videos_selenium(profile_url, max_videos)
            
            params.update(profile_data)
            
            video_urls = []
            cursor = '0'
            
            # Sayfalama ile videoları al
            while len(video_urls) < max_videos:
                params['cursor'] = cursor
                
                try:
                    response = session.get(api_url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'itemList' in data and data['itemList']:
                            items = data['itemList']
                            
                            for item in items:
                                if len(video_urls) >= max_videos:
                                    break
                                    
                                video_id = item.get('id')
                                author_info = item.get('author', {})
                                author_username = author_info.get('uniqueId', username)
                                
                                if video_id:
                                    video_url = f"https://www.tiktok.com/@{author_username}/video/{video_id}"
                                    video_urls.append(video_url)
                                    self.log(f"Video bulundu: {video_url}")
                            
                            # Sonraki sayfa için cursor güncelle
                            if 'hasMore' in data and data['hasMore'] and 'cursor' in data:
                                cursor = str(data['cursor'])
                            else:
                                break
                        else:
                            self.log("API'den video verisi alınamadı")
                            break
                    else:
                        self.log(f"API isteği başarısız: {response.status_code}")
                        break
                        
                except requests.exceptions.RequestException as e:
                    self.log(f"Request hatası: {str(e)}")
                    break
                
                # Rate limiting
                time.sleep(random.uniform(1, 2))
            
            if video_urls:
                self.log(f"Request ile {len(video_urls)} video URL'si toplandı")
                return video_urls
            else:
                self.log("Request yöntemi başarısız, Selenium yöntemine geçiliyor...")
                return self.scrape_profile_videos_selenium(profile_url, max_videos)
                
        except Exception as e:
            self.log(f"Request tabanlı scraping hatası: {str(e)}")
            self.log("Selenium yöntemine geçiliyor...")
            return self.scrape_profile_videos_selenium(profile_url, max_videos)
    
    def get_profile_data_with_requests(self, profile_url, session, headers):
        """Profil sayfasından secUid ve userId'yi al"""
        try:
            response = session.get(profile_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html_content = response.text
                
                # JavaScript'ten profil verilerini çıkar
                # TikTok profil verilerini içeren script tag'ini bul
                patterns = [
                    r'"secUid":"([^"]+)"',
                    r'"userId":"([^"]+)"',
                    r'"id":"([^"]+)"',
                    r'"uniqueId":"([^"]+)"'
                ]
                
                profile_data = {}
                
                # secUid'yi bul
                sec_uid_match = re.search(r'"secUid":"([^"]+)"', html_content)
                if sec_uid_match:
                    profile_data['secUid'] = sec_uid_match.group(1)
                
                # userId'yi bul
                user_id_match = re.search(r'"userId":"([^"]+)"', html_content)
                if user_id_match:
                    profile_data['userId'] = user_id_match.group(1)
                
                # shareUid'yi bul
                share_uid_match = re.search(r'"shareUid":"([^"]+)"', html_content)
                if share_uid_match:
                    profile_data['shareUid'] = share_uid_match.group(1)
                
                if profile_data.get('secUid') and profile_data.get('userId'):
                    self.log(f"Profil verileri bulundu: secUid={profile_data['secUid'][:10]}..., userId={profile_data['userId']}")
                    return profile_data
                else:
                    self.log("Profil verilerinde secUid veya userId bulunamadı")
                    return None
            else:
                self.log(f"Profil sayfası yüklenemedi: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"Profil veri çıkarma hatası: {str(e)}")
            return None
    
    def extract_username_from_url(self, profile_url):
        """Profil URL'sinden kullanıcı adını çıkar"""
        try:
            # https://www.tiktok.com/@username formatından username'i çıkar
            match = re.search(r'/@([^/?]+)', profile_url)
            if match:
                return match.group(1)
            return None
        except:
            return None
    
    def scrape_profile_videos_selenium(self, profile_url, max_videos=20):
        """Selenium ile profil video scraping (fallback yöntem)"""
        self.log("Selenium ile profil videoları alınıyor...")
        
        driver = self.setup_driver()
        if not driver:
            return []
            
        video_urls = []
        
        try:
            # Profil sayfasına git
            driver.get(profile_url)
            time.sleep(3)
            
            # Sayfayı scroll yaparak daha fazla video yükle
            self.log("Profil sayfası kaydırılıyor...")
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
            video_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
            
            self.log(f"Profilde {len(video_elements)} video elementi bulundu")
            
            for element in video_elements[:max_videos]:
                try:
                    video_url = element.get_attribute('href')
                    if video_url and '/video/' in video_url:
                        video_urls.append(video_url)
                        self.log(f"Profil videosu: {video_url}")
                except:
                    continue
            
            self.log(f"Selenium ile {len(video_urls)} video URL'si toplandı")
            
        except Exception as e:
            self.log(f"Selenium profil scraping hatası: {str(e)}")
            
        finally:
            driver.quit()
            
        return video_urls
