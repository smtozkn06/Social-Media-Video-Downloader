import time
import json
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import re
from urllib.parse import urljoin, urlparse

class FacebookScraper:
    def __init__(self, log_callback=None, bulk_downloader=None):
        self.driver = None
        self.log_callback = log_callback
        self.bulk_downloader = bulk_downloader
        self.stop_scraping = False
        self.cookies_loaded = False
        
    def log(self, message):
        """Log mesajı gönderir"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def setup_driver(self, headless=True):
        """WebDriver'ı kurar"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Dil ayarları
            prefs = {
                "intl.accept_languages": "tr-TR,tr;q=0.9,en;q=0.8",
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.log("✅ WebDriver başarıyla kuruldu")
            return True
            
        except Exception as e:
            self.log(f"❌ WebDriver kurulum hatası: {str(e)}")
            return False
    
    def load_cookies(self):
        """Kaydedilmiş cookie'leri yükler"""
        try:
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "facebook_cookies.json")
            
            if os.path.exists(cookie_file):
                # Önce Facebook ana sayfasına git
                self.driver.get("https://www.facebook.com")
                time.sleep(2)
                
                # Cookie'leri yükle
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        continue
                
                # Sayfayı yenile
                self.driver.refresh()
                time.sleep(3)
                
                self.cookies_loaded = True
                self.log(f"✅ {len(cookies)} adet cookie yüklendi")
                return True
            else:
                self.log("ℹ️ Kaydedilmiş cookie bulunamadı")
                return False
                
        except Exception as e:
            self.log(f"❌ Cookie yükleme hatası: {str(e)}")
            return False
    
    def save_cookies(self):
        """Mevcut cookie'leri kaydeder"""
        try:
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "facebook_cookies.json")
            cookies = self.driver.get_cookies()
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            self.log(f"✅ {len(cookies)} adet cookie kaydedildi")
            return True
            
        except Exception as e:
            self.log(f"❌ Cookie kaydetme hatası: {str(e)}")
            return False
    
    def check_for_captcha(self):
        """CAPTCHA kontrolü yapar"""
        try:
            # CAPTCHA elementlerini kontrol et
            captcha_selectors = [
                "[data-testid='captcha']",
                ".captcha",
                "#captcha",
                "[aria-label*='captcha']",
                "[aria-label*='Captcha']",
                "[aria-label*='CAPTCHA']"
            ]
            
            for selector in captcha_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        self.log("⚠️ CAPTCHA tespit edildi! Lütfen manuel olarak çözün...")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            return False
    
    def wait_for_page_load(self, timeout=10):
        """Sayfanın yüklenmesini bekler"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False
    
    def scroll_page(self, scroll_count=3):
        """Sayfayı aşağı kaydırır"""
        try:
            for i in range(scroll_count):
                if self.stop_scraping:
                    break
                
                # Sayfanın sonuna kaydır
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 4))
                
                # CAPTCHA kontrolü
                if self.check_for_captcha():
                    self.log("⚠️ CAPTCHA nedeniyle kaydırma durduruldu")
                    break
            
            return True
            
        except Exception as e:
            self.log(f"❌ Sayfa kaydırma hatası: {str(e)}")
            return False
    
    def search_videos(self, search_term, max_videos=10):
        """Facebook'ta video arar"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Cookie'leri yükle
            self.load_cookies()
            
            # Facebook ana sayfasına git
            self.driver.get("https://www.facebook.com")
            self.wait_for_page_load()
            
            # Arama kutusunu bul ve arama yap
            search_box = None
            search_selectors = [
                "[placeholder*='Search']",
                "[placeholder*='Ara']",
                "[aria-label*='Search']",
                "[aria-label*='Ara']",
                "input[type='search']"
            ]
            
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                self.log("❌ Arama kutusu bulunamadı")
                return []
            
            # Arama terimini gir
            search_box.clear()
            search_box.send_keys(search_term)
            search_box.send_keys(Keys.RETURN)
            
            self.wait_for_page_load()
            time.sleep(3)
            
            # Video filtresi uygula
            try:
                video_filter = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Videos') or contains(text(), 'Videolar')]"))
                )
                video_filter.click()
                self.wait_for_page_load()
                time.sleep(3)
            except:
                self.log("⚠️ Video filtresi uygulanamadı, genel aramaya devam ediliyor")
            
            # Video URL'lerini topla
            video_urls = self.find_video_elements(max_videos)
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return video_urls
            
        except Exception as e:
            self.log(f"❌ Arama hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def get_page_videos(self, page_url, max_videos=10):
        """Belirli bir Facebook sayfasından video URL'lerini alır"""
        try:
            if not self.setup_driver(headless=self.bulk_downloader.headless_mode_checkbox.value if self.bulk_downloader else True):
                return []
            
            # Cookie'leri yükle
            self.load_cookies()
            
            # Sayfa URL'sine git
            self.driver.get(page_url)
            self.wait_for_page_load()
            time.sleep(3)
            
            # Videolar sekmesine git
            try:
                videos_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Videos') or contains(text(), 'Videolar')]"))
                )
                videos_tab.click()
                self.wait_for_page_load()
                time.sleep(3)
            except:
                self.log("⚠️ Videolar sekmesi bulunamadı, ana sayfadan devam ediliyor")
            
            # Video URL'lerini topla
            video_urls = self.find_video_elements(max_videos)
            
            # Cookie'leri kaydet
            self.save_cookies()
            
            return video_urls
            
        except Exception as e:
            self.log(f"❌ Sayfa video alma hatası: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def find_video_elements(self, max_videos=10):
        """Sayfadaki video elementlerini bulur"""
        video_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        try:
            while len(video_urls) < max_videos and scroll_attempts < max_scroll_attempts and not self.stop_scraping:
                # CAPTCHA kontrolü
                if self.check_for_captcha():
                    self.log("⚠️ CAPTCHA tespit edildi, işlem durduruldu")
                    break
                
                # Video linklerini bul
                video_selectors = [
                    "a[href*='/watch/']",
                    "a[href*='/videos/']",
                    "a[href*='fb.watch']",
                    "a[href*='/video.php']",
                    "a[href*='/posts/'][href*='video']"
                ]
                
                for selector in video_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if len(video_urls) >= max_videos:
                                break
                            
                            try:
                                href = element.get_attribute('href')
                                if href and self.is_valid_facebook_video_url(href):
                                    # URL'yi temizle
                                    clean_url = self.clean_facebook_url(href)
                                    if clean_url:
                                        video_urls.add(clean_url)
                                        self.log(f"📹 Video bulundu: {clean_url}")
                            except:
                                continue
                    except:
                        continue
                
                # Daha fazla video yüklemek için sayfayı kaydır
                if len(video_urls) < max_videos:
                    self.scroll_page(1)
                    scroll_attempts += 1
                    time.sleep(random.uniform(2, 4))
                
                self.log(f"📊 Bulunan video sayısı: {len(video_urls)}/{max_videos}")
            
            return list(video_urls)[:max_videos]
            
        except Exception as e:
            self.log(f"❌ Video bulma hatası: {str(e)}")
            return list(video_urls)
    
    def is_valid_facebook_video_url(self, url):
        """Facebook video URL'sinin geçerli olup olmadığını kontrol eder"""
        if not url:
            return False
        
        facebook_patterns = [
            r'facebook\.com/watch/\?v=\d+',
            r'facebook\.com/[^/]+/videos/\d+',
            r'facebook\.com/video\.php\?v=\d+',
            r'facebook\.com/[^/]+/posts/\d+',
            r'fb\.watch/[A-Za-z0-9_-]+'
        ]
        
        for pattern in facebook_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def clean_facebook_url(self, url):
        """Facebook URL'sini temizler"""
        try:
            # URL'deki gereksiz parametreleri temizle
            if '?' in url:
                base_url, params = url.split('?', 1)
                # Sadece gerekli parametreleri koru
                if 'v=' in params:
                    video_id = re.search(r'v=(\d+)', params)
                    if video_id:
                        return f"{base_url}?v={video_id.group(1)}"
            
            return url
            
        except Exception as e:
            return url
    
    def __del__(self):
        """Destructor - WebDriver'ı kapat"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass