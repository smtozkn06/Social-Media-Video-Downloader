import requests
import re
import os
import json
from urllib.parse import urlparse
from pathlib import Path

class TwitterScraper:
    def __init__(self, output_dir="output", debug=False, log_callback=None, bulk_downloader=None):
        self.output_dir = output_dir
        self.debug = debug
        self.log_callback = log_callback
        self.bulk_downloader = bulk_downloader
        self.session = requests.Session()
        
        # User-Agent header'ı ekle
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_with_requests(self, url):
        """Twitter URL'sinden medya dosyalarını indirir"""
        try:
            # URL'yi temizle ve tweet ID'sini çıkar
            tweet_id = self.extract_tweet_id(url)
            if not tweet_id:
                return {'success': False, 'error': 'Geçersiz Twitter URL'}
            
            # Çıktı klasörünü oluştur
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Twitter'ın guest token API'sini kullanarak medya bilgilerini al
            media_urls = self.get_media_urls(tweet_id)
            
            if not media_urls:
                return {'success': False, 'error': 'Medya bulunamadı'}
            
            downloaded_files = []
            
            for i, media_url in enumerate(media_urls):
                try:
                    # Dosya uzantısını belirle
                    parsed_url = urlparse(media_url)
                    file_extension = self.get_file_extension(media_url)
                    
                    # Dosya adını oluştur
                    filename = f"tweet_{tweet_id}_{i+1}{file_extension}"
                    file_path = os.path.join(self.output_dir, filename)
                    
                    # Medya dosyasını indir
                    response = self.session.get(media_url, stream=True)
                    response.raise_for_status()
                    
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    downloaded_files.append(file_path)
                    
                except Exception as e:
                    if self.debug:
                        print(f"Medya indirme hatası: {e}")
                    continue
            
            if downloaded_files:
                return {
                    'success': True,
                    'downloaded_files': downloaded_files,
                    'tweet_id': tweet_id
                }
            else:
                return {'success': False, 'error': 'Hiçbir medya dosyası indirilemedi'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extract_tweet_id(self, url):
        """Twitter URL'sinden tweet ID'sini çıkarır"""
        patterns = [
            r'https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/[^/]+/status/(\d+)',
            r'https?://t\.co/([A-Za-z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_media_urls(self, tweet_id):
        """Tweet ID'sinden medya URL'lerini alır"""
        try:
            # Twitter'ın guest token API'sini kullanarak tweet bilgilerini al
            guest_token = self.get_guest_token()
            if not guest_token:
                return []
            
            # Tweet detaylarını al
            tweet_url = f"https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}&include_entities=true&tweet_mode=extended"
            
            headers = {
                'Authorization': f'Bearer {guest_token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(tweet_url, headers=headers)
            
            if response.status_code == 200:
                tweet_data = response.json()
                media_urls = []
                
                # Extended entities'den medya URL'lerini çıkar
                if 'extended_entities' in tweet_data and 'media' in tweet_data['extended_entities']:
                    for media in tweet_data['extended_entities']['media']:
                        if media['type'] == 'video' or media['type'] == 'animated_gif':
                            # Video için en yüksek kaliteli variant'ı al
                            if 'video_info' in media and 'variants' in media['video_info']:
                                best_variant = None
                                best_bitrate = 0
                                
                                for variant in media['video_info']['variants']:
                                    if variant.get('content_type') == 'video/mp4':
                                        bitrate = variant.get('bitrate', 0)
                                        if bitrate > best_bitrate:
                                            best_bitrate = bitrate
                                            best_variant = variant
                                
                                if best_variant:
                                    media_urls.append(best_variant['url'])
                        
                        elif media['type'] == 'photo':
                            # Fotoğraf için orijinal boyutu al
                            photo_url = media['media_url_https'] + ':orig'
                            media_urls.append(photo_url)
                
                return media_urls
            
            # API başarısız olursa alternatif yöntem dene
            return self.get_media_urls_fallback(tweet_id)
            
        except Exception as e:
            if self.debug:
                print(f"Medya URL alma hatası: {e}")
            # Hata durumunda alternatif yöntem dene
            return self.get_media_urls_fallback(tweet_id)
    
    def get_guest_token(self):
        """Twitter guest token alır"""
        try:
            # Twitter'ın guest token endpoint'i
            token_url = "https://api.twitter.com/1.1/guest/activate.json"
            
            headers = {
                'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.post(token_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('guest_token')
            
            return None
            
        except Exception as e:
            if self.debug:
                print(f"Guest token alma hatası: {e}")
            return None
    
    def get_media_urls_fallback(self, tweet_id):
        """Alternatif medya URL alma yöntemi"""
        try:
            # Basit HTML scraping yöntemi
            tweet_url = f"https://twitter.com/i/status/{tweet_id}"
            
            response = self.session.get(tweet_url)
            
            if response.status_code == 200:
                html_content = response.text
                media_urls = []
                
                # Video URL'lerini regex ile bul
                video_patterns = [
                    r'"(https://video\.twimg\.com/[^"]+\.mp4[^"]*?)"',
                    r'"(https://pbs\.twimg\.com/[^"]+\.(jpg|jpeg|png|gif)[^"]*?)"'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if isinstance(match, tuple):
                            url = match[0]
                        else:
                            url = match
                        
                        if url not in media_urls:
                            media_urls.append(url)
                
                return media_urls
            
            return []
            
        except Exception as e:
            if self.debug:
                print(f"Fallback medya URL alma hatası: {e}")
            return []
    
    def get_file_extension(self, url):
        """URL'den dosya uzantısını belirler"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        if '.mp4' in path:
            return '.mp4'
        elif '.jpg' in path or '.jpeg' in path:
            return '.jpg'
        elif '.png' in path:
            return '.png'
        elif '.gif' in path:
            return '.gif'
        elif '.webm' in path:
            return '.webm'
        else:
            # Video için varsayılan
            if 'video' in url:
                return '.mp4'
            else:
                return '.jpg'
    
    def save_debug_info(self, tweet_id, data):
        """Debug bilgilerini dosyaya kaydeder"""
        if not self.debug:
            return
            
        try:
            debug_file = os.path.join(self.output_dir, f"debug_{tweet_id}.json")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Debug bilgisi kaydetme hatası: {e}")

# Test fonksiyonu
if __name__ == "__main__":
    scraper = TwitterScraper(output_dir="test_output", debug=True)
    
    # Test URL'si
    test_url = "https://twitter.com/example/status/1234567890"
    result = scraper.download_with_requests(test_url)
    
    print("Sonuç:", result)