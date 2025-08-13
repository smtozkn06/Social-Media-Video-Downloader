import time
import random
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from .instagram_http_downloader import InstagramHttpDownloader
import json
import os
import requests

class InstagramScraper:
    def __init__(self, log_callback=None, bulk_downloader=None, use_http=True):
        self.driver = None
        self.log_callback = log_callback
        self.bulk_downloader = bulk_downloader
        self.stop_scraping = False
        self.use_http = use_http
        self.http_downloader = None
        
        if self.use_http:
            self.http_downloader = InstagramHttpDownloader(log_callback=log_callback)
        
    def log(self, message):
        """Log mesajı gönderir"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def setup_driver(self, headless=True):
        """Selenium WebDriver'ı ayarla - bulk_downloader'dan setup_selenium metodunu kullan"""
        try:
            # Eğer bulk_downloader referansı varsa onun setup_selenium metodunu kullan
            if self.bulk_downloader and hasattr(self.bulk_downloader, 'setup_selenium'):
                self.driver = self.bulk_downloader.setup_selenium(for_login=False)
                if self.driver:
                    self.log("✅ Chrome WebDriver başarıyla kuruldu (bulk_downloader'dan)")
                    return True
                else:
                    self.log("❌ bulk_downloader'dan WebDriver alınamadı, fallback kullanılıyor")
            
            # Fallback: Basit WebDriver kurulumu
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # Temel ayarlar
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Anti-bot tespiti
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User-Agent ayarla
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Bildirim, konum izinleri ve medya yüklemeyi devre dışı bırak (resimler hariç)
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.media_stream": 2,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "profile.default_content_setting_values.geolocation": 2,
                "profile.default_content_setting_values.desktop_notification": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # WebDriver oluştur
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # WebDriver tespitini engelle
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.implicitly_wait(10)
            
            self.log("✅ Chrome WebDriver başarıyla kuruldu (fallback)")
            return True
            
        except Exception as e:
            self.log(f"❌ WebDriver kurulum hatası: {str(e)}")
            return False
    
    def load_cookies(self):
        """Kaydedilmiş cookie'leri yükler"""
        try:
            if self.bulk_downloader and self.bulk_downloader.instagram_cookies:
                # Cookie'ler dictionary formatında ise Selenium formatına çevir
                if isinstance(self.bulk_downloader.instagram_cookies, dict):
                    for name, value in self.bulk_downloader.instagram_cookies.items():
                        cookie_dict = {
                            'name': name,
                            'value': value,
                            'domain': '.instagram.com',
                            'path': '/'
                        }
                        self.driver.add_cookie(cookie_dict)
                    self.log(f"🍪 {len(self.bulk_downloader.instagram_cookies)} adet cookie yüklendi (dict formatından)")
                # Cookie'ler zaten Selenium formatında ise direkt yükle
                elif isinstance(self.bulk_downloader.instagram_cookies, list):
                    for cookie in self.bulk_downloader.instagram_cookies:
                        self.driver.add_cookie(cookie)
                    self.log(f"🍪 {len(self.bulk_downloader.instagram_cookies)} adet cookie yüklendi (list formatından)")
                return True
        except Exception as e:
            self.log(f"Cookie yükleme hatası: {str(e)}")
        return False
    
    def save_cookies(self):
        """Mevcut cookie'leri kaydeder"""
        try:
            cookies = self.driver.get_cookies()
            
            # Cookie klasörünü oluştur
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "instagram_cookies.json")
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            if self.bulk_downloader:
                self.bulk_downloader.instagram_cookies = cookies
            
            self.log(f"🍪 {len(cookies)} adet cookie kaydedildi")
            
        except Exception as e:
            self.log(f"Cookie kaydetme hatası: {str(e)}")
    
    def search_videos(self, hashtag, max_videos=10):
        """Hashtag ile video arar - Tarayıcı tabanlı işlem"""
        try:
            self.log(f"🌐 Tarayıcı ile hashtag arama başlatılıyor: #{hashtag}")
            return self._search_videos_selenium(hashtag, max_videos)
                
        except Exception as e:
            self.log(f"❌ Hashtag arama hatası: {str(e)}")
            return []
    
    def _search_videos_selenium(self, hashtag, max_videos=10):
        """Selenium ile hashtag arama"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Instagram ana sayfasına git
            self.driver.get("https://www.instagram.com")
            time.sleep(3)
            
            # Cookie'leri yükle
            self.load_cookies()
            self.driver.refresh()
            time.sleep(3)
            
            # Hashtag sayfasına git - kullanıcının girdiği kelimeyi doğrudan kullan
            hashtag_clean = hashtag.replace('#', '').strip()
            hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag_clean}/"
            self.log(f"🔍 Selenium ile hashtag sayfasına gidiliyor: {hashtag_url}")
            self.log(f"📷 Not: Sadece fotoğraflar indirilecek, videolar filtrelenecek")
            
            self.driver.get(hashtag_url)
            time.sleep(5)
            
            # Video linklerini topla
            video_urls = []
            scroll_count = 0
            max_scrolls = 10
            
            while len(video_urls) < max_videos and scroll_count < max_scrolls and not self.stop_scraping:
                # Video elementlerini bul
                video_elements = self.find_video_elements()
                
                for element in video_elements:
                    if len(video_urls) >= max_videos or self.stop_scraping:
                        break
                    
                    try:
                        # Element zaten <a> tag'i ise direkt href al, değilse içindeki <a> tag'ini bul
                        if element.tag_name == 'a':
                            link = element.get_attribute("href")
                        else:
                            link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        if link and "/p/" in link:
                            # Eğer link sadece /p/ ile başlıyorsa tam URL yap
                            if link.startswith("/p/"):
                                full_url = f"https://www.instagram.com{link}"
                            else:
                                full_url = link
                            
                            if full_url not in video_urls:
                                # Video elementlerini filtrele - sadece fotoğrafları al
                                try:
                                    # Video ikonu veya play butonu var mı kontrol et
                                    video_indicators = element.find_elements(By.CSS_SELECTOR, 
                                        "svg[aria-label*='Video'], svg[aria-label*='video'], "
                                        "svg[aria-label*='Reel'], svg[aria-label*='reel'], "
                                        "[data-testid*='video'], [aria-label*='Video'], "
                                        "[aria-label*='Reel'], .video-icon")
                                    
                                    # Video göstergesi yoksa fotoğraf olarak kabul et
                                    if not video_indicators:
                                        video_urls.append(full_url)
                                        self.log(f"📷 Fotoğraf bulundu: {full_url}")
                                    else:
                                        self.log(f"🎬 Video atlandı (sadece fotoğraflar): {full_url}")
                                except:
                                    # Hata durumunda fotoğraf olarak kabul et
                                    video_urls.append(full_url)
                                    self.log(f"📷 Fotoğraf bulundu (varsayılan): {full_url}")
                    except:
                        continue
                
                # Sayfayı hızlı aşağı kaydır - daha agresif scroll
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);");
                time.sleep(random.uniform(0.5, 1.0))  # Çok daha hızlı scroll
                
                # Ek scroll işlemi - daha fazla içerik yüklemek için
                self.driver.execute_script("window.scrollBy(0, 1000);");
                time.sleep(0.3)
                scroll_count += 1
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return video_urls[:max_videos]
            
        except Exception as e:
            self.log(f"❌ Selenium hashtag arama hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def get_profile_videos(self, profile_url, max_videos=10):
        """Profil URL'sinden videoları alır - Tarayıcı tabanlı işlem"""
        try:
            self.log(f"🌐 Tarayıcı ile profil analiz ediliyor: {profile_url}")
            return self._get_profile_videos_selenium(profile_url, max_videos)
                
        except Exception as e:
            self.log(f"❌ Profil video alma hatası: {str(e)}")
            return []
    
    def get_profile_posts(self, profile_url, max_posts=10):
        """Profil URL'sinden gönderileri alır - Tarayıcı tabanlı işlem"""
        try:
            # URL'nin sonuna /p/ ekle
            if not profile_url.endswith('/'):
                profile_url += '/'
            profile_posts_url = profile_url + 'p/'
            
            self.log(f"🌐 Tarayıcı ile profil gönderileri alınıyor: {profile_posts_url}")
            return self._get_profile_posts_selenium(profile_posts_url, max_posts)
                
        except Exception as e:
            self.log(f"❌ Profil gönderileri alma hatası: {str(e)}")
            return []
    
    def get_profile_reels(self, profile_url, max_reels=10):
        """Profil URL'sinden reels alır - Tarayıcı tabanlı işlem"""
        try:
            # URL'nin sonuna /reels/ ekle
            if not profile_url.endswith('/'):
                profile_url += '/'
            profile_reels_url = profile_url + 'reels/'
            
            self.log(f"🌐 Tarayıcı ile profil reels alınıyor: {profile_reels_url}")
            return self._get_profile_reels_selenium(profile_reels_url, max_reels)
                
        except Exception as e:
            self.log(f"❌ Profil reels alma hatası: {str(e)}")
            return []
    
    def get_stories(self, username):
        """Kullanıcının hikayelerini alır - Tarayıcı tabanlı işlem"""
        try:
            self.log(f"⚠️ Tarayıcı ile hikaye alma henüz desteklenmiyor: {username}")
            self.log("💡 Hikaye indirme özelliği gelecek güncellemelerde eklenecek")
            return []
                
        except Exception as e:
            self.log(f"❌ Hikaye alma hatası: {str(e)}")
            return []
    
    def _get_profile_videos_selenium(self, profile_url, max_videos=10):
        """Selenium ile profil sayfasından video linklerini toplar"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Instagram ana sayfasına git
            self.driver.get("https://www.instagram.com")
            time.sleep(3)
            
            # Cookie'leri yükle
            self.load_cookies()
            self.driver.refresh()
            time.sleep(3)
            
            # Profil sayfasına git
            self.log(f"👤 Selenium ile profil sayfasına gidiliyor: {profile_url}")
            self.driver.get(profile_url)
            time.sleep(5)
            
            # Video linklerini topla
            video_urls = []
            scroll_count = 0
            max_scrolls = 10
            
            while len(video_urls) < max_videos and scroll_count < max_scrolls and not self.stop_scraping:
                # Video elementlerini bul
                video_elements = self.find_video_elements()
                
                for element in video_elements:
                    if len(video_urls) >= max_videos or self.stop_scraping:
                        break
                    
                    try:
                        # Element zaten <a> tag'i ise direkt href al, değilse içindeki <a> tag'ini bul
                        if element.tag_name == 'a':
                            link = element.get_attribute("href")
                        else:
                            link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        if link and "/p/" in link:
                            # Eğer link sadece /p/ ile başlıyorsa tam URL yap
                            if link.startswith("/p/"):
                                full_url = f"https://www.instagram.com{link}"
                            else:
                                full_url = link
                            
                            if full_url not in video_urls:
                                video_urls.append(full_url)
                                self.log(f"📹 Post bulundu: {full_url}")
                    except:
                        continue
                
                # Sayfayı hızlı aşağı kaydır - daha agresif scroll
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);");
                time.sleep(random.uniform(0.5, 1.0))  # Çok daha hızlı scroll
                
                # Ek scroll işlemi - daha fazla içerik yüklemek için
                self.driver.execute_script("window.scrollBy(0, 1000);");
                time.sleep(0.3)
                scroll_count += 1
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return video_urls[:max_videos]
            
        except Exception as e:
            self.log(f"❌ Selenium profil video alma hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def _get_profile_posts_selenium(self, profile_posts_url, max_posts=10):
        """Selenium ile profil gönderileri sayfasından post linklerini toplar"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Instagram ana sayfasına git
            self.driver.get("https://www.instagram.com")
            time.sleep(3)
            
            # Cookie'leri yükle
            self.load_cookies()
            self.driver.refresh()
            time.sleep(3)
            
            # Profil gönderileri sayfasına git
            self.log(f"📝 Selenium ile profil gönderileri sayfasına gidiliyor: {profile_posts_url}")
            self.driver.get(profile_posts_url)
            time.sleep(5)
            
            # Gönderi sayısını tespit etmeye çalış
            try:
                post_count_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.x1ji0vk5.x18bv5gf.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x1i0vuye.xl565be.xo1l8bm.x1roi4f4.x2b8uid.x10wh9bi.xpm28yp.x8viiok.x1o7cslx")
                
                for element in post_count_elements:
                    text = element.text.strip()
                    if 'gönderi' in text.lower():
                        # Sayıyı çıkar
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            total_posts = int(numbers[0])
                            self.log(f"📊 Toplam gönderi sayısı: {total_posts}")
                            break
            except:
                self.log("📊 Gönderi sayısı tespit edilemedi")
            
            # Post linklerini topla
            post_urls = []
            scroll_count = 0
            max_scrolls = 15  # Daha fazla scroll
            
            while len(post_urls) < max_posts and scroll_count < max_scrolls and not self.stop_scraping:
                # Post elementlerini bul
                post_elements = self.find_video_elements()
                
                for element in post_elements:
                    if len(post_urls) >= max_posts or self.stop_scraping:
                        break
                    
                    try:
                        # Element zaten <a> tag'i ise direkt href al, değilse içindeki <a> tag'ini bul
                        if element.tag_name == 'a':
                            link = element.get_attribute("href")
                        else:
                            link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        if link and "/p/" in link:
                            # Eğer link sadece /p/ ile başlıyorsa tam URL yap
                            if link.startswith("/p/"):
                                full_url = f"https://www.instagram.com{link}"
                            else:
                                full_url = link
                            
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                                self.log(f"📝 Gönderi bulundu: {full_url}")
                    except:
                        continue
                
                # Sayfayı aşağı kaydır
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);");
                time.sleep(random.uniform(0.5, 1.0))
                
                # Ek scroll işlemi
                self.driver.execute_script("window.scrollBy(0, 1000);");
                time.sleep(0.3)
                scroll_count += 1
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return post_urls[:max_posts]
            
        except Exception as e:
            self.log(f"❌ Selenium profil gönderileri alma hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def _get_profile_reels_selenium(self, profile_reels_url, max_reels=10):
        """Selenium ile profil reels sayfasından reel linklerini toplar"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Instagram ana sayfasına git
            self.driver.get("https://www.instagram.com")
            time.sleep(3)
            
            # Cookie'leri yükle
            self.load_cookies()
            self.driver.refresh()
            time.sleep(3)
            
            # Profil reels sayfasına git
            self.log(f"🎬 Selenium ile profil reels sayfasına gidiliyor: {profile_reels_url}")
            self.driver.get(profile_reels_url)
            time.sleep(5)
            
            # Reel linklerini topla
            reel_urls = []
            scroll_count = 0
            max_scrolls = 15  # Daha fazla scroll
            
            while len(reel_urls) < max_reels and scroll_count < max_scrolls and not self.stop_scraping:
                # Reel elementlerini bul (reels sayfasında da /p/ linkleri var)
                reel_elements = self.find_video_elements()
                
                for element in reel_elements:
                    if len(reel_urls) >= max_reels or self.stop_scraping:
                        break
                    
                    try:
                        # Element zaten <a> tag'i ise direkt href al, değilse içindeki <a> tag'ini bul
                        if element.tag_name == 'a':
                            link = element.get_attribute("href")
                        else:
                            link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        if link and "/p/" in link:
                            # Eğer link sadece /p/ ile başlıyorsa tam URL yap
                            if link.startswith("/p/"):
                                full_url = f"https://www.instagram.com{link}"
                            else:
                                full_url = link
                            
                            if full_url not in reel_urls:
                                reel_urls.append(full_url)
                                self.log(f"🎬 Reel bulundu: {full_url}")
                    except:
                        continue
                
                # Sayfayı aşağı kaydır
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);");
                time.sleep(random.uniform(0.5, 1.0))
                
                # Ek scroll işlemi
                self.driver.execute_script("window.scrollBy(0, 1000);");
                time.sleep(0.3)
                scroll_count += 1
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return reel_urls[:max_reels]
            
        except Exception as e:
            self.log(f"❌ Selenium profil reels alma hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def find_video_elements(self):
        """Sayfadaki video elementlerini bulur"""
        try:
            # Instagram'da video/post elementleri için güncel CSS selector'lar
            selectors = [
                # Kullanıcının belirttiği spesifik class ile
                "a.x1i10hfl.xjbqb8w.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.x972fbf.x10w94by.x1qhh985.x14e42zd.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x4gyw5p._a6hd",
                # Genel post linkleri
                "a[href*='/p/']",
                # Article içindeki linkler
                "article a[href*='/p/']",
                # Div container içindeki linkler
                "div._aagu a",
                "div._aagv a",
                # Fallback selector'lar
                "article div div div div a",
                "article a",
                "div[role='button'] a"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Sadece /p/ içeren linkleri filtrele
                        valid_elements = []
                        for element in elements:
                            try:
                                href = element.get_attribute("href")
                                if href and "/p/" in href:
                                    valid_elements.append(element)
                            except:
                                continue
                        
                        if valid_elements:
                            self.log(f"✅ {len(valid_elements)} post elementi bulundu (selector: {selector[:50]}...)")
                            return valid_elements
                except Exception as e:
                    self.log(f"Selector hatası ({selector[:30]}...): {str(e)}")
                    continue
            
            self.log("❌ Hiç post elementi bulunamadı")
            return []
            
        except Exception as e:
            self.log(f"Element bulma hatası: {str(e)}")
            return []
    
    def handle_captcha(self):
        """CAPTCHA durumunu kontrol eder ve kullanıcıyı uyarır"""
        try:
            # CAPTCHA elementlerini kontrol et
            captcha_selectors = [
                "[data-testid='captcha']",
                ".captcha",
                "#captcha",
                "[aria-label*='captcha']",
                "[aria-label*='Captcha']"
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if captcha_element.is_displayed():
                        self.log("🤖 CAPTCHA tespit edildi! Lütfen tarayıcıda manuel olarak çözün.")
                        
                        # Headless modda değilse kullanıcının CAPTCHA çözmesini bekle
                        if not self.bulk_downloader.headless_mode_checkbox.value:
                            self.log("⏳ CAPTCHA çözülmesi bekleniyor...")
                            
                            # CAPTCHA çözülene kadar bekle (maksimum 5 dakika)
                            wait_time = 0
                            max_wait = 300  # 5 dakika
                            
                            while wait_time < max_wait:
                                time.sleep(5)
                                wait_time += 5
                                
                                # CAPTCHA hala var mı kontrol et
                                try:
                                    captcha_still_there = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if not captcha_still_there.is_displayed():
                                        self.log("✅ CAPTCHA çözüldü!")
                                        return True
                                except:
                                    self.log("✅ CAPTCHA çözüldü!")
                                    return True
                            
                            self.log("⏰ CAPTCHA çözme süresi doldu")
                            return False
                        else:
                            self.log("❌ Headless modda CAPTCHA çözülemez. Lütfen headless modu kapatın.")
                            return False
                except:
                    continue
            
            return True  # CAPTCHA bulunamadı
            
        except Exception as e:
            self.log(f"CAPTCHA kontrol hatası: {str(e)}")
            return True
    
    def wait_for_page_load(self, timeout=10):
        """Sayfanın yüklenmesini bekler"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            self.log("⏰ Sayfa yükleme zaman aşımı")
            return False
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """Rastgele bekleme süresi"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def scroll_page(self, scroll_count=3):
        """Sayfayı hızlı aşağı kaydırır"""
        for i in range(scroll_count):
            if self.stop_scraping:
                break
            
            # Hızlı scroll işlemi
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(0.5, 1.0))  # Çok daha hızlı
            
            # Ek scroll - daha fazla içerik yüklemek için
            self.driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(0.3)
    
    def close_popups(self):
        """Açılır pencereleri kapatır"""
        try:
            # Yaygın popup kapatma butonları
            close_selectors = [
                "[aria-label='Close']",
                "[aria-label='Kapat']",
                "button[aria-label='Close']",
                ".close",
                ".close-button",
                "[data-testid='modal-close-button']"
            ]
            
            for selector in close_selectors:
                try:
                    close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if close_button.is_displayed():
                        close_button.click()
                        time.sleep(1)
                        self.log("❌ Popup kapatıldı")
                except:
                    continue
                    
        except Exception as e:
            pass  # Popup yoksa devam et

if __name__ == "__main__":
    # Test için
    scraper = InstagramScraper()
    videos = scraper.search_videos("travel", 5)
    print(f"Bulunan videolar: {videos}")