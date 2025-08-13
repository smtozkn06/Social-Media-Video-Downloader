import requests
import json
import time
import random
from urllib.parse import quote

class TikTokAPIScraper:
    """TikTok API kullanarak video arama ve profil tarama - Selenium'a alternatif"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        
        # Güncellenmiş ve daha gerçekçi header'lar
        self.base_headers = {
            'authority': 'www.tiktok.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,tr;q=0.8',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.tiktok.com/',
            'origin': 'https://www.tiktok.com',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Güncellenmiş cookie'ler
        device_id = self.generate_device_id()
        self.base_cookies = {
            '_ttp': '2Lq3QGYaz7SeDZd8hZGq8pe4m1K',
            'tt_chain_token': 'JHjD/FLxEafq5143Wydg2w==',
            'tt_webid': device_id,
            'tt_webid_v2': device_id,
            'ttwid': self.generate_device_id(),
            'msToken': self.generate_device_id()[:32],
            'odin_tt': self.generate_device_id()[:32],
            'tiktok_webapp_theme': 'light',
            'tiktok_webapp_lang': 'en',
            'cookie-consent': '{"ga":true,"af":true,"fbp":true,"lip":true,"bing":true,"ttads":true,"reddit":true,"hubspot":true,"version":"v10"}'
        }
        
        # Session'a cookie'leri ekle
        for name, value in self.base_cookies.items():
            self.session.cookies.set(name, value)
            
        # Session'a headers'ları ekle
        self.session.headers.update(self.base_headers)
        
        # Timeout ayarları
        self.session.timeout = 30
        
    def log(self, message):
        """Log mesajı gönder"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
            
    def generate_device_id(self):
        """Rastgele device ID oluştur"""
        return str(random.randint(7000000000000000000, 7999999999999999999))
        
    def search_videos_api(self, search_query, max_videos=10):
        """TikTok arama sayfasından video ara (HTML parsing ile)"""
        self.log(f"'{search_query}' için video aranıyor...")
        
        try:
            # Arama sayfasına git (encode işlemi kaldırıldı)
            search_url = f"https://www.tiktok.com/search/video?q={search_query}"
            
            self.log(f"Arama sayfası yükleniyor: {search_url}")
            
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                video_pattern = r'https://www\.tiktok\.com/@[^/]+/video/\d+'
                videos = re.findall(video_pattern, response.text)
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # İstenen sayıya sınırla
                videos = videos[:max_videos]
                
                self.log(f"Arama sonucu: {len(videos)} video bulundu")
                return videos
            else:
                self.log(f"Arama sayfası HTTP hatası: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Arama hatası: {str(e)}")
            return []
            
    def get_explore_videos_api(self, count=16):
        """Explore sayfasından video listesi al (HTML parsing ile)"""
        self.log("Explore sayfasından videolar alınıyor...")
        
        try:
            # Direkt explore sayfasını al
            explore_url = "https://www.tiktok.com/foryou"
            
            self.log("Explore sayfası yükleniyor...")
            
            response = self.session.get(explore_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                video_pattern = r'https://www\.tiktok\.com/@[^/]+/video/\d+'
                videos = re.findall(video_pattern, response.text)
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # İstenen sayıya sınırla
                videos = videos[:count]
                
                self.log(f"Explore sayfasından {len(videos)} video bulundu")
                return videos
            else:
                self.log(f"Explore sayfası HTTP hatası: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Explore sayfası hatası: {str(e)}")
            return []
            
    def get_user_videos_api(self, username, max_videos=20):
        """Kullanıcının videolarını HTML parsing ile al"""
        self.log(f"@{username} kullanıcısının videoları alınıyor...")
        
        try:
            # Kullanıcı profiline git
            profile_url = f"https://www.tiktok.com/@{username}"
            
            self.log(f"Profil sayfası yükleniyor: {profile_url}")
            
            response = self.session.get(profile_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                video_pattern = rf'https://www\.tiktok\.com/@{re.escape(username)}/video/\d+'
                videos = re.findall(video_pattern, response.text)
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # İstenen sayıya sınırla
                videos = videos[:max_videos]
                
                self.log(f"@{username} kullanıcısından {len(videos)} video bulundu")
                return videos
            else:
                self.log(f"Profil sayfası HTTP hatası: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Profil sayfası hatası: {str(e)}")
            return []
            
    def extract_username_from_url(self, profile_url):
        """Profil URL'sinden kullanıcı adını çıkar"""
        try:
            # https://www.tiktok.com/@username formatından username'i çıkar
            if '/@' in profile_url:
                username = profile_url.split('/@')[1].split('/')[0].split('?')[0]
                return username
            return None
        except:
            return None
            
    def test_api_connection(self):
        """API bağlantısını test et"""
        self.log("TikTok API bağlantısı test ediliyor...")
        
        try:
            # Basit bir explore isteği gönder
            videos = self.get_explore_videos_api(count=1)
            if videos:
                self.log("✅ API bağlantısı başarılı!")
                return True
            else:
                self.log("❌ API bağlantısı başarısız - video alınamadı")
                return False
        except Exception as e:
            self.log(f"❌ API bağlantı testi hatası: {str(e)}")
            return False

# Test fonksiyonu
if __name__ == "__main__":
    scraper = TikTokAPIScraper()
    
    print("TikTok API Scraper Test")
    print("=" * 30)
    
    # API bağlantısını test et
    if scraper.test_api_connection():
        print("\n1. Explore videoları test ediliyor...")
        explore_videos = scraper.get_explore_videos_api(count=3)
        print(f"Explore'dan {len(explore_videos)} video alındı")
        
        print("\n2. Arama testi yapılıyor...")
        search_videos = scraper.search_videos_api("funny", max_videos=3)
        print(f"Aramadan {len(search_videos)} video alındı")
        
        print("\n3. Kullanıcı videoları testi yapılıyor...")
        user_videos = scraper.get_user_videos_api("tiktok", max_videos=3)
        print(f"Kullanıcıdan {len(user_videos)} video alındı")
    else:
        print("API bağlantısı kurulamadı!")