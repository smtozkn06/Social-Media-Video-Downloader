import requests
import json
import time
import random
from urllib.parse import quote

class YouTubeAPIScraper:
    """YouTube API kullanarak video arama ve kanal tarama - Selenium'a alternatif"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        
        # Güncellenmiş ve daha gerçekçi header'lar
        self.base_headers = {
            'authority': 'www.youtube.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,tr;q=0.8',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.youtube.com/',
            'origin': 'https://www.youtube.com',
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
            'VISITOR_INFO1_LIVE': self.generate_device_id()[:32],
            'YSC': self.generate_device_id()[:16],
            'PREF': 'f4=4000000&tz=Europe.Istanbul',
            'CONSENT': 'YES+cb.20210328-17-p0.en+FX+667',
            'GPS': '1'
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
    
    def check_if_live_video_from_html(self, html_content, video_url):
        """HTML içeriğinden video URL'sinin canlı yayın olup olmadığını kontrol et"""
        try:
            # Video ID'sini çıkar
            video_id = video_url.split('v=')[1].split('&')[0] if 'v=' in video_url else None
            if not video_id:
                return False
            
            import re
            
            # Daha kesin canlı yayın göstergeleri ara - sadece gerçekten canlı olan videoları yakala
            live_indicators = [
                rf'"videoId":"{video_id}"[^}}]*"isLiveContent":true[^}}]*"liveBroadcastContent":"live"',
                rf'"videoId":"{video_id}"[^}}]*"liveBroadcastContent":"live"[^}}]*"isLiveContent":true',
                rf'{video_id}[^}}]*"badges":[^]]*"LIVE"[^}}]*"style":"BADGE_STYLE_TYPE_LIVE_NOW"',
                rf'"videoId":"{video_id}"[^}}]*"isLive":true[^}}]*"liveBroadcastContent":"live"'
            ]
            
            # Sadece çok kesin göstergeleri kontrol et
            for pattern in live_indicators:
                if re.search(pattern, html_content, re.IGNORECASE):
                    self.log(f"Gerçek canlı yayın tespit edildi: {video_url}")
                    return True
            
            return False
            
        except Exception as e:
            self.log(f"Canlı yayın HTML kontrolü hatası: {str(e)}")
            return False
        
    def search_videos_api(self, search_query, max_videos=10, video_type="normal"):
        """YouTube arama sayfasından video ara (HTML parsing ile)"""
        self.log(f"'{search_query}' için video aranıyor... (Tür: {video_type})")
        
        try:
            # Arama sayfasına git (encode işlemi kaldırıldı)
            search_url = f"https://www.youtube.com/results?search_query={search_query}"
            
            # Video türüne göre filtre ekle
            if video_type == "shorts":
                search_url += "&sp=EgIYAQ%253D%253D"  # Shorts filtresi
            
            self.log(f"Arama sayfası yükleniyor: {search_url}")
            
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                video_pattern = r'https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+'
                videos = re.findall(video_pattern, response.text)
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # Canlı yayın videoları filtrele
                filtered_videos = []
                for video_url in videos:
                    if not self.check_if_live_video_from_html(response.text, video_url):
                        filtered_videos.append(video_url)
                        self.log(f"Video eklendi: {video_url}")
                    else:
                        self.log(f"Canlı yayın tespit edildi, atlanıyor: {video_url}")
                
                # İstenen sayıya sınırla
                filtered_videos = filtered_videos[:max_videos]
                
                self.log(f"Arama sonucu: {len(filtered_videos)} video bulundu (canlı yayınlar filtrelendi)")
                return filtered_videos
            else:
                self.log(f"Arama sayfası HTTP hatası: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Arama hatası: {str(e)}")
            return []
            
    def get_trending_videos_api(self, count=16):
        """Trending sayfasından video listesi al (HTML parsing ile)"""
        self.log("Trending sayfasından videolar alınıyor...")
        
        try:
            # Direkt trending sayfasını al
            trending_url = "https://www.youtube.com/feed/trending"
            
            self.log("Trending sayfası yükleniyor...")
            
            response = self.session.get(trending_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                video_pattern = r'https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+'
                videos = re.findall(video_pattern, response.text)
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # İstenen sayıya sınırla
                videos = videos[:count]
                
                self.log(f"Trending sayfasından {len(videos)} video bulundu")
                return videos
            else:
                self.log(f"Trending sayfası HTTP hatası: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Trending sayfası hatası: {str(e)}")
            return []
            
    def get_channel_videos_api(self, channel_id, max_videos=20, video_type="videos"):
        """Kanalın videolarını HTML parsing ile al"""
        self.log(f"{channel_id} kanalının videoları alınıyor... (Tür: {video_type})")
        
        try:
            # Kanal URL'sini oluştur - farklı formatları dene
            channel_urls = []
            
            # Eğer channel_id zaten tam URL ise
            if channel_id.startswith('http'):
                base_url = channel_id.rstrip('/')
                if video_type == "shorts":
                    channel_urls.append(f"{base_url}/shorts")
                else:
                    channel_urls.append(f"{base_url}/videos")
            else:
                # Farklı kanal formatlarını dene
                if video_type == "shorts":
                    channel_urls = [
                        f"https://www.youtube.com/channel/{channel_id}/shorts",
                        f"https://www.youtube.com/c/{channel_id}/shorts",
                        f"https://www.youtube.com/@{channel_id}/shorts"
                    ]
                else:
                    channel_urls = [
                        f"https://www.youtube.com/channel/{channel_id}/videos",
                        f"https://www.youtube.com/c/{channel_id}/videos",
                        f"https://www.youtube.com/@{channel_id}/videos"
                    ]
            
            videos = []
            
            # Her URL formatını dene
            for channel_url in channel_urls:
                self.log(f"Kanal sayfası deneniyor: {channel_url}")
                
                try:
                    response = self.session.get(channel_url, timeout=15)
                    
                    if response.status_code == 200:
                        # HTML'den video linklerini çıkar
                        import re
                        
                        # Daha kapsamlı video pattern'i
                        video_patterns = [
                            r'"url":"/watch\?v=([a-zA-Z0-9_-]+)"',
                            r'"videoId":"([a-zA-Z0-9_-]+)"',
                            r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                            r'/watch\?v=([a-zA-Z0-9_-]+)'
                        ]
                        
                        video_ids = set()
                        for pattern in video_patterns:
                            matches = re.findall(pattern, response.text)
                            video_ids.update(matches)
                        
                        # Video ID'lerini tam URL'lere çevir
                        videos = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]
                        
                        # Tekrarları kaldır
                        videos = list(set(videos))
                        
                        if videos:
                            self.log(f"{channel_url} adresinden {len(videos)} video bulundu")
                            break
                        else:
                            self.log(f"{channel_url} adresinde video bulunamadı")
                    else:
                        self.log(f"Kanal sayfası HTTP hatası: {response.status_code} - {channel_url}")
                        
                except Exception as url_error:
                    self.log(f"URL deneme hatası ({channel_url}): {str(url_error)}")
                    continue
            
            # İstenen sayıya sınırla
            videos = videos[:max_videos]
            
            self.log(f"{channel_id} kanalından toplam {len(videos)} video bulundu")
            return videos
                
        except Exception as e:
            self.log(f"Kanal sayfası hatası: {str(e)}")
            return []
            
    def get_playlist_videos_api(self, playlist_url, max_videos=50):
        """Oynatma listesinden video listesi al (HTML parsing ile)"""
        self.log(f"Oynatma listesinden videolar alınıyor: {playlist_url}")
        
        try:
            # Playlist ID'sini çıkar
            playlist_id = self.extract_playlist_id_from_url(playlist_url)
            if not playlist_id:
                self.log("Playlist ID'si çıkarılamadı")
                return [], "unknown"
            
            self.log(f"Playlist ID'si: {playlist_id}")
            
            response = self.session.get(playlist_url, timeout=15)
            
            if response.status_code == 200:
                # HTML'den video linklerini çıkar
                import re
                
                # Playlist başlığını çıkar
                title_pattern = r'<title>([^<]+)</title>'
                title_match = re.search(title_pattern, response.text)
                playlist_title = "unknown"
                if title_match:
                    playlist_title = title_match.group(1).replace(' - YouTube', '').strip()
                    # Dosya adı için güvenli hale getir
                    import string
                    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
                    playlist_title = ''.join(c for c in playlist_title if c in valid_chars)
                
                # Video ID'lerini çıkar
                video_patterns = [
                    r'"videoId":"([a-zA-Z0-9_-]+)"',
                    r'"url":"/watch\?v=([a-zA-Z0-9_-]+)',
                    r'/watch\?v=([a-zA-Z0-9_-]+)&list=' + playlist_id
                ]
                
                video_ids = set()
                for pattern in video_patterns:
                    matches = re.findall(pattern, response.text)
                    video_ids.update(matches)
                
                # Video ID'lerini tam URL'lere çevir
                videos = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]
                
                # Tekrarları kaldır
                videos = list(set(videos))
                
                # Canlı yayın videoları filtrele
                filtered_videos = []
                for video_url in videos:
                    if not self.check_if_live_video_from_html(response.text, video_url):
                        filtered_videos.append(video_url)
                        self.log(f"Video eklendi: {video_url}")
                    else:
                        self.log(f"Canlı yayın tespit edildi, atlanıyor: {video_url}")
                
                # İstenen sayıya sınırla
                filtered_videos = filtered_videos[:max_videos]
                
                self.log(f"Playlist'ten {len(filtered_videos)} video bulundu (canlı yayınlar filtrelendi)")
                return filtered_videos, playlist_title
            else:
                self.log(f"Playlist sayfası HTTP hatası: {response.status_code}")
                return [], "unknown"
                
        except Exception as e:
            self.log(f"Playlist hatası: {str(e)}")
            return [], "unknown"
    
    def extract_playlist_id_from_url(self, playlist_url):
        """Playlist URL'sinden playlist ID'sini çıkar"""
        try:
            # https://www.youtube.com/playlist?list=PLAYLIST_ID formatından playlist_id'yi çıkar
            if 'list=' in playlist_url:
                playlist_id = playlist_url.split('list=')[1].split('&')[0]
                return playlist_id
            return None
        except:
            return None
    
    def extract_channel_id_from_url(self, channel_url):
        """Kanal URL'sinden kanal ID'sini çıkar"""
        try:
            # https://www.youtube.com/channel/CHANNEL_ID formatından channel_id'yi çıkar
            if '/channel/' in channel_url:
                channel_id = channel_url.split('/channel/')[1].split('/')[0].split('?')[0]
                return channel_id
            # https://www.youtube.com/c/CHANNEL_NAME formatı için
            elif '/c/' in channel_url:
                channel_name = channel_url.split('/c/')[1].split('/')[0].split('?')[0]
                return channel_name
            # https://www.youtube.com/@CHANNEL_NAME formatı için
            elif '/@' in channel_url:
                channel_name = channel_url.split('/@')[1].split('/')[0].split('?')[0]
                return channel_name
            return None
        except:
            return None
            
    def test_api_connection(self):
        """API bağlantısını test et"""
        self.log("YouTube API bağlantısı test ediliyor...")
        
        try:
            # Basit bir trending isteği gönder
            videos = self.get_trending_videos_api(count=1)
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
    scraper = YouTubeAPIScraper()
    
    print("YouTube API Scraper Test")
    print("=" * 30)
    
    # API bağlantısını test et
    if scraper.test_api_connection():
        print("\n1. Trending videoları test ediliyor...")
        trending_videos = scraper.get_trending_videos_api(count=3)
        print(f"Trending'den {len(trending_videos)} video alındı")
        
        print("\n2. Arama testi yapılıyor...")
        search_videos = scraper.search_videos_api("funny", max_videos=3)
        print(f"Aramadan {len(search_videos)} video alındı")
        
        print("\n3. Kanal videoları testi yapılıyor...")
        channel_videos = scraper.get_channel_videos_api("UC_x5XG1OV2P6uZZ5FSM9Ttw", max_videos=3)
        print(f"Kanaldan {len(channel_videos)} video alındı")
    else:
        print("API bağlantısı kurulamadı!")