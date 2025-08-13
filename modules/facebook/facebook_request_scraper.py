import requests
import re
import json
import time
import random
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import os

class FacebookRequestScraper:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        self.setup_session()
        
    def log(self, message):
        """Log mesajı gönderir"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def setup_session(self):
        """Request session'ını kurar"""
        # User-Agent ayarla
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        self.session.headers.update(headers)
        
        # Cookie'leri yükle
        self.load_cookies()
    
    def load_cookies(self):
        """Kaydedilmiş cookie'leri yükler"""
        try:
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "facebook_cookies.json")
            
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie['name'], 
                        cookie['value'], 
                        domain=cookie.get('domain', '.facebook.com')
                    )
                
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
            cookies = []
            
            for cookie in self.session.cookies:
                cookies.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path
                })
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            self.log(f"✅ {len(cookies)} adet cookie kaydedildi")
            return True
            
        except Exception as e:
            self.log(f"❌ Cookie kaydetme hatası: {str(e)}")
            return False
    
    def get_page_content(self, url, retries=3):
        """Sayfa içeriğini alır - geliştirilmiş hata yönetimi ile"""
        for attempt in range(retries):
            try:
                # Farklı header kombinasyonlarını dene
                header_sets = [
                    {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0'
                    },
                    {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive'
                    }
                ]
                
                # İlk denemede mevcut session header'larını kullan
                if attempt == 0:
                    response = self.session.get(url, timeout=30)
                else:
                    # Sonraki denemelerde farklı header'lar dene
                    headers = header_sets[min(attempt - 1, len(header_sets) - 1)]
                    temp_headers = self.session.headers.copy()
                    temp_headers.update(headers)
                    response = self.session.get(url, headers=temp_headers, timeout=30)
                
                if response.status_code == 200:
                    # İçerik kontrolü
                    content = response.text
                    if len(content) > 100:  # Minimum içerik kontrolü
                        return content
                    else:
                        self.log(f"⚠️ Çok kısa içerik alındı ({len(content)} karakter), tekrar deneniyor...")
                        continue
                        
                elif response.status_code == 429:
                    # Rate limit
                    wait_time = random.uniform(5, 15)
                    self.log(f"⚠️ Rate limit, {wait_time:.1f} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code == 403:
                    self.log(f"⚠️ HTTP 403 hatası (deneme {attempt + 1}/{retries}), farklı header deneniyor...")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(3, 7))
                    continue
                    
                elif response.status_code == 404:
                    self.log(f"❌ HTTP 404 hatası: Sayfa bulunamadı - {url}")
                    return None
                    
                else:
                    self.log(f"⚠️ HTTP {response.status_code} hatası (deneme {attempt + 1}/{retries}): {url}")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(2, 5))
                    continue
                    
            except requests.exceptions.Timeout as e:
                self.log(f"⚠️ Timeout hatası (deneme {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(3, 8))
                    
            except requests.exceptions.ConnectionError as e:
                self.log(f"⚠️ Bağlantı hatası (deneme {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
                    
            except requests.exceptions.RequestException as e:
                self.log(f"⚠️ İstek hatası (deneme {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(2, 5))
                    
            except Exception as e:
                self.log(f"⚠️ Beklenmeyen hata (deneme {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(2, 5))
                    
        self.log(f"❌ Tüm denemeler başarısız oldu: {url}")
        return None
    
    def get_page_content_with_search_headers(self, url, retries=3):
        """Arama için mevcut session header'ları ve cookie'leri kullanarak sayfa içeriğini alır"""
        for attempt in range(retries):
            try:
                # Mevcut session header'larını kopyala ve arama için özelleştir
                search_headers = self.session.headers.copy()
                
                # Arama için ek header'lar ekle
                search_headers.update({
                    'Referer': 'https://www.facebook.com/',
                    'Origin': 'https://www.facebook.com',
                    'Sec-Fetch-Site': 'same-origin',
                    'Cache-Control': 'max-age=0'
                })
                
                # Session'daki cookie'ler otomatik olarak kullanılacak
                response = self.session.get(url, headers=search_headers, timeout=30)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    # Rate limit
                    wait_time = random.uniform(5, 15)
                    self.log(f"⚠️ Rate limit, {wait_time:.1f} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.log(f"⚠️ HTTP {response.status_code} hatası: {url}")
                    
            except requests.exceptions.RequestException as e:
                self.log(f"⚠️ İstek hatası (deneme {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(2, 5))
                    
        return None
    
    def extract_video_urls_from_content(self, content, base_url=""):
        """HTML içeriğinden video URL'lerini çıkarır"""
        video_urls = set()
        
        try:
            # BeautifulSoup ile parse et
            soup = BeautifulSoup(content, 'html.parser')
            
            # Video link pattern'leri - daha kapsamlı
            video_patterns = [
                r'https?://(?:www\.)?facebook\.com/watch/\?v=\d+',
                r'https?://(?:www\.)?facebook\.com/watch/\?.*v=\d+',
                r'https?://(?:www\.)?facebook\.com/[^/]+/videos/\d+',
                r'https?://(?:www\.)?facebook\.com/video\.php\?v=\d+',
                r'https?://(?:www\.)?facebook\.com/photo\.php\?fbid=\d+',
                r'https?://(?:www\.)?facebook\.com/photo/\?fbid=\d+',
                r'https?://fb\.watch/[A-Za-z0-9_-]+',
                r'https?://(?:www\.)?facebook\.com/reel/\d+',
                r'https?://(?:www\.)?facebook\.com/[^/]+/posts/\d+',
                r'https?://(?:www\.)?facebook\.com/story\.php\?story_fbid=\d+',
                r'https?://(?:www\.)?facebook\.com/permalink\.php\?story_fbid=\d+',
                r'https?://(?:www\.)?facebook\.com/groups/[^/]+/posts/\d+',
                r'https?://(?:www\.)?facebook\.com/groups/[^/]+/permalink/\d+'
            ]
            
            # Tüm linkleri bul
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                if href:
                    # Relative URL'leri absolute yap
                    if href.startswith('/'):
                        href = urljoin('https://www.facebook.com', href)
                    
                    # Video pattern'lerini kontrol et
                    for pattern in video_patterns:
                        if re.search(pattern, href):
                            clean_url = self.clean_facebook_url(href)
                            if clean_url:
                                video_urls.add(clean_url)
                                break
            
            # JSON içindeki URL'leri de ara - daha kapsamlı pattern'ler
            json_patterns = [
                r'"[^"]*url[^"]*"\s*:\s*"([^"]*facebook[^"]*)',
                r'"permalink_url"\s*:\s*"([^"]*facebook[^"]*)',
                r'"link"\s*:\s*"([^"]*facebook[^"]*)',
                r'"href"\s*:\s*"([^"]*facebook[^"]*)',
                r'"story_permalink"\s*:\s*"([^"]*facebook[^"]*)',
                r'https?://(?:www\.)?facebook\.com/[^\s"\'>]*(?:watch|video|photo|reel|posts|story|permalink)[^\s"\'>]*'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, content, re.IGNORECASE)
                
                for match in json_matches:
                    if match:
                        # URL'yi decode et
                        decoded_url = match.replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
                        clean_url = self.clean_facebook_url(decoded_url)
                        if clean_url and self.is_valid_facebook_video_url(clean_url):
                            video_urls.add(clean_url)
            
            # Data attribute'larından da ara
            data_elements = soup.find_all(attrs={'data-href': True})
            for element in data_elements:
                data_href = element.get('data-href')
                if data_href and 'facebook.com' in data_href:
                    for pattern in video_patterns:
                        if re.search(pattern, data_href):
                            clean_url = self.clean_facebook_url(data_href)
                            if clean_url:
                                video_urls.add(clean_url)
                                break
            
            return list(video_urls)
            
        except Exception as e:
            self.log(f"❌ Video URL çıkarma hatası: {str(e)}")
            return []
    
    def clean_facebook_url(self, url):
        """Facebook URL'ini temizler ve standartlaştırır"""
        try:
            if not url or not isinstance(url, str):
                return None
            
            # URL'yi decode et
            url = url.replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
            
            # Facebook domain kontrolü
            if not any(domain in url.lower() for domain in ['facebook.com', 'fb.watch']):
                return None
            
            # Gereksiz parametreleri temizle
            parsed = urlparse(url)
            
            # Query parametrelerini filtrele
            query_params = parse_qs(parsed.query)
            
            # Önemli parametreleri koru
            important_params = {}
            
            if 'v' in query_params:
                important_params['v'] = query_params['v'][0]
            if 'fbid' in query_params:
                important_params['fbid'] = query_params['fbid'][0]
            if 'set' in query_params:
                important_params['set'] = query_params['set'][0]
            if 'story_fbid' in query_params:
                important_params['story_fbid'] = query_params['story_fbid'][0]
            if 'id' in query_params:
                important_params['id'] = query_params['id'][0]
            
            # Temiz URL oluştur
            clean_query = '&'.join([f"{k}={v}" for k, v in important_params.items()])
            
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_query:
                clean_url += f"?{clean_query}"
            
            return clean_url
            
        except Exception as e:
            self.log(f"⚠️ URL temizleme hatası: {str(e)}")
            return None
    
    def is_valid_facebook_video_url(self, url):
        """Facebook video URL'inin geçerli olup olmadığını kontrol eder"""
        if not url:
            return False
        
        video_patterns = [
            # Video URL'leri
            r'facebook\.com/watch/\?.*v=\d+',
            r'facebook\.com/watch\?v=\d+',
            r'facebook\.com/[^/]+/videos/\d+',
            r'facebook\.com/video\.php\?v=\d+',
            r'fb\.watch/[A-Za-z0-9_-]+',
            
            # Reel URL'leri
            r'facebook\.com/reel/\d+',
            r'facebook\.com/[^/]+/reel/\d+',
            
            # Photo URL'leri - Genişletilmiş
            r'facebook\.com/photo\.php\?fbid=\d+',
            r'facebook\.com/photo/\?fbid=\d+',
            r'facebook\.com/photo\?fbid=\d+',
            r'facebook\.com/[^/]+/photos/[^/]+/\d+',
            r'facebook\.com/photo/\?fbid=\d+&set=[^&]+',
            r'facebook\.com/photo\?fbid=\d+&set=[^&]+',
            
            # Post URL'leri
            r'facebook\.com/[^/]+/posts/\d+',
            r'facebook\.com/story\.php\?story_fbid=\d+',
            r'facebook\.com/permalink\.php\?story_fbid=\d+',
            
            # Group URL'leri
            r'facebook\.com/groups/[^/]+/posts/\d+',
            r'facebook\.com/groups/[^/]+/permalink/\d+'
        ]
        
        return any(re.search(pattern, url) for pattern in video_patterns)
    
    def is_valid_facebook_url(self, url):
        """Facebook URL'inin geçerli olup olmadığını kontrol eder (video URL'leri için alias)"""
        return self.is_valid_facebook_video_url(url)
    
    def search_videos_from_page(self, page_url, max_videos=50):
        """Belirli bir sayfadan video linklerini arar"""
        self.log(f"🔍 Sayfa taranıyor: {page_url}")
        
        content = self.get_page_content(page_url)
        if not content:
            self.log("❌ Sayfa içeriği alınamadı")
            return []
        
        video_urls = self.extract_video_urls_from_content(content, page_url)
        
        # Maksimum video sayısını sınırla
        if len(video_urls) > max_videos:
            video_urls = video_urls[:max_videos]
        
        self.log(f"✅ {len(video_urls)} adet video linki bulundu")
        return video_urls
    
    def search_posts_with_infinite_scroll(self, search_term, max_videos=50):
        """Facebook'ta arama yaparak infinite scroll ile post/video linklerini toplar"""
        self.log(f"🔍 Facebook'ta arama yapılıyor: {search_term}")
        
        # Farklı arama URL formatlarını dene
        search_urls = [
            f"https://www.facebook.com/search/top/?q={search_term}",
            f"https://www.facebook.com/search/videos/?q={search_term}",
            f"https://m.facebook.com/search/?q={search_term}",
            f"https://www.facebook.com/public/{search_term}"
        ]
        
        all_video_urls = set()
        
        for search_url in search_urls:
            self.log(f"🔍 Denenen arama URL'i: {search_url}")
            
            cursor = None
            page_count = 0
            max_pages = 5  # Her URL için maksimum sayfa sayısı
            
            while len(all_video_urls) < max_videos and page_count < max_pages:
                try:
                    # İlk sayfa veya cursor ile sonraki sayfa
                    if cursor:
                        url = f"{search_url}&cursor={cursor}"
                    else:
                        url = search_url
                    
                    self.log(f"📄 Sayfa {page_count + 1} yükleniyor...")
                    content = self.get_page_content_with_search_headers(url)
                    
                    if not content:
                        self.log("❌ Sayfa içeriği alınamadı")
                        break
                
                    # Video URL'lerini çıkar
                    page_video_urls = self.extract_video_urls_from_content(content, url)
                    
                    if not page_video_urls:
                        self.log("⚠️ Bu sayfada video bulunamadı")
                        # Cursor'u bulmaya çalış
                        cursor = self.extract_next_cursor(content)
                        if not cursor:
                            self.log("❌ Sonraki sayfa cursor'u bulunamadı")
                            break
                        page_count += 1
                        continue
                    
                    # Yeni URL'leri ekle
                    new_urls = 0
                    for video_url in page_video_urls:
                        if video_url not in all_video_urls:
                            all_video_urls.add(video_url)
                            new_urls += 1
                    
                    self.log(f"✅ Bu sayfada {new_urls} yeni video bulundu (Toplam: {len(all_video_urls)})")
                    
                    # Sonraki sayfa cursor'unu bul
                    cursor = self.extract_next_cursor(content)
                    if not cursor:
                        self.log("ℹ️ Sonraki sayfa bulunamadı, bu URL için arama tamamlandı")
                        break
                    
                    page_count += 1
                    
                    # Rate limiting için bekleme
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    self.log(f"❌ Sayfa {page_count + 1} işlenirken hata: {str(e)}")
                    break
            
            # Bu URL'den yeterli sonuç alındıysa diğer URL'lere geçme
            if len(all_video_urls) >= max_videos:
                break
                
            # URL'ler arası bekleme
            time.sleep(random.uniform(1, 3))
        
        # Sonuçları liste olarak döndür ve maksimum sayıyı sınırla
        result_urls = list(all_video_urls)[:max_videos]
        self.log(f"🎉 Toplam {len(result_urls)} video/post linki bulundu")
        
        return result_urls
    
    def extract_next_cursor(self, content):
        """Sayfa içeriğinden sonraki sayfa için cursor değerini çıkarır"""
        try:
            # Facebook'un infinite scroll için kullandığı cursor pattern'leri
            cursor_patterns = [
                r'"cursor"\s*:\s*"([^"]+)"',
                r'"end_cursor"\s*:\s*"([^"]+)"',
                r'"page_info"[^}]*"end_cursor"\s*:\s*"([^"]+)"',
                r'"after"\s*:\s*"([^"]+)"',
                r'data-cursor="([^"]+)"',
                r'cursor=([^&\s"]+)',
                r'"next"[^}]*"cursor"\s*:\s*"([^"]+)"'
            ]
            
            for pattern in cursor_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    cursor = matches[-1]  # Son cursor'u al
                    if cursor and cursor != "null" and len(cursor) > 5:
                        return cursor
            
            return None
            
        except Exception as e:
            self.log(f"⚠️ Cursor çıkarma hatası: {str(e)}")
            return None
    
    def search_videos_from_profile(self, profile_url, max_videos=50):
        """Profil sayfasından video linklerini arar"""
        self.log(f"👤 Profil taranıyor: {profile_url}")
        
        # Profil sayfasının video sekmesine git
        videos_url = f"{profile_url.rstrip('/')}/videos"
        
        return self.search_videos_from_page(videos_url, max_videos)
    
    def download_video_info(self, video_url):
        """Video bilgilerini indirir"""
        try:
            self.log(f"📹 Video bilgileri alınıyor: {video_url}")
            
            content = self.get_page_content(video_url)
            if not content:
                return None
            
            # Video başlığını bul
            title_patterns = [
                r'<title[^>]*>([^<]+)</title>',
                r'"title"\s*:\s*"([^"]+)"',
                r'"name"\s*:\s*"([^"]+)"'
            ]
            
            title = "Facebook Video"
            for pattern in title_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    break
            
            # Video açıklamasını bul
            description_patterns = [
                r'"description"\s*:\s*"([^"]+)"',
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\'>]+)["\']',
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\'>]+)["\']'
            ]
            
            description = ""
            for pattern in description_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    description = match.group(1).strip()
                    break
            
            return {
                'url': video_url,
                'title': title,
                'description': description,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.log(f"❌ Video bilgi alma hatası: {str(e)}")
            return None
    
    def extract_photo_url(self, photo_page_url):
        """Facebook fotoğraf sayfasından gerçek fotoğraf URL'ini çıkarır - geliştirilmiş"""
        try:
            self.log(f"📸 Fotoğraf URL'i çıkarılıyor: {photo_page_url}")
            
            # Profil fotoğrafı kontrolü - başlangıçta kontrol et
            if self._is_profile_photo(photo_page_url):
                self.log(f"⏭️ Profil/kapak fotoğrafı URL'i atlanıyor: {photo_page_url}")
                return None
            
            # Eğer URL zaten direkt fotoğraf URL'i ise
            if any(domain in photo_page_url for domain in ['scontent', 'fbcdn']) and any(ext in photo_page_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                self.log(f"✅ Direkt fotoğraf URL'i tespit edildi")
                cleaned_url = self._clean_photo_url(photo_page_url)
                # Direkt URL için de profil kontrolü yap
                if cleaned_url and self._is_profile_photo(cleaned_url):
                    self.log(f"⏭️ Direkt profil/kapak fotoğrafı URL'i atlanıyor: {cleaned_url}")
                    return None
                return cleaned_url
            
            # fbid parametresini çıkar
            fbid_match = re.search(r'fbid=([0-9]+)', photo_page_url)
            if fbid_match:
                fbid = fbid_match.group(1)
                self.log(f"📋 FBID bulundu: {fbid}")
                
                # Farklı URL formatlarını dene
                url_formats = [
                    f"https://www.facebook.com/photo.php?fbid={fbid}",
                    f"https://m.facebook.com/photo.php?fbid={fbid}",
                    f"https://www.facebook.com/photo/?fbid={fbid}",
                    f"https://m.facebook.com/photo/?fbid={fbid}",
                    photo_page_url,
                    photo_page_url.replace('www.facebook.com', 'm.facebook.com')
                ]
            else:
                # fbid bulunamazsa orijinal URL'leri kullan
                url_formats = [
                    photo_page_url,
                    photo_page_url.replace('www.facebook.com', 'm.facebook.com'),
                    photo_page_url.replace('m.facebook.com', 'www.facebook.com')
                ]
            
            for url in url_formats:
                self.log(f"🔍 Denenen URL: {url}")
                content = self.get_page_content(url)
                if not content:
                    continue
                
                photo_urls = set()
                
                # BeautifulSoup ile img tag'lerini bul
                soup = BeautifulSoup(content, 'html.parser')
                
                # Farklı img selector'ları dene
                img_selectors = [
                    'img[src*="scontent"]',
                    'img[src*="fbcdn"]',
                    'img[data-src*="scontent"]',
                    'img[data-src*="fbcdn"]',
                    'img[data-original*="scontent"]',
                    'img[data-original*="fbcdn"]',
                    'img'
                ]
                
                for selector in img_selectors:
                    imgs = soup.select(selector)
                    for img in imgs:
                        for attr in ['src', 'data-src', 'data-original', 'data-lazy-src']:
                            src = img.get(attr)
                            if src and self._is_valid_photo_url(src) and not self._is_profile_photo(src):
                                photo_urls.add(self._clean_photo_url(src))
                
                # JSON içindeki URL'leri ara - daha kapsamlı pattern'ler (boyut parametreleri dahil)
                json_patterns = [
                    r'"url"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"src"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"image"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"full_picture"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"picture"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"photo_image"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"hd_src"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    r'"image_src"\s*:\s*"([^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)",?',
                    # Boyut parametreli URL'ler için özel pattern'ler
                    r'"(https?://[^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*[?&]w=[0-9]+[^"]*)',
                    r'"(https?://[^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*[?&]h=[0-9]+[^"]*)',
                    r'https://[^\s"\'>]*(?:scontent|fbcdn)[^\s"\'>]*\.(?:jpg|jpeg|png|webp)[^\s"\'>]*'
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        
                        clean_url = self._clean_photo_url(match)
                        if clean_url and self._is_valid_photo_url(clean_url) and not self._is_profile_photo(clean_url):
                            photo_urls.add(clean_url)
                
                # Meta tag'lerden de ara
                meta_patterns = [
                    r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\'>]*(?:scontent|fbcdn)[^"\'>]*\.(?:jpg|jpeg|png|webp)[^"\'>]*)["\']',
                    r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\'>]*(?:scontent|fbcdn)[^"\'>]*\.(?:jpg|jpeg|png|webp)[^"\'>]*)["\']'
                ]
                
                for pattern in meta_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        clean_url = self._clean_photo_url(match)
                        if clean_url and self._is_valid_photo_url(clean_url) and not self._is_profile_photo(clean_url):
                            photo_urls.add(clean_url)
                
                if photo_urls:
                    # En yüksek kaliteli URL'yi seç
                    best_url = self._select_best_photo_url(photo_urls)
                    self.log(f"✅ Fotoğraf URL'i bulundu: {best_url[:100]}...")
                    return best_url
            
            self.log("❌ Fotoğraf URL'i bulunamadı")
            return None
                
        except Exception as e:
            self.log(f"❌ Fotoğraf URL çıkarma hatası: {str(e)}")
            return None
    
    def _is_valid_photo_url(self, url):
        """Fotoğraf URL'inin geçerli olup olmadığını kontrol eder (profil resimlerini filtreler)"""
        if not url or not isinstance(url, str):
            return False
        
        # Facebook CDN kontrolü
        if not any(domain in url for domain in ['scontent', 'fbcdn']):
            return False
        
        # Dosya uzantısı kontrolü
        if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return False
        
        # Profil resimlerini filtrele
        profile_indicators = [
            '/p50x50/',     # Küçük profil resmi
            '/p100x100/',   # Orta profil resmi
            '/p200x200/',   # Büyük profil resmi
            '/s50x50/',     # Square profil resmi
            '/s100x100/',   # Square profil resmi
            '/s200x200/',   # Square profil resmi
            '/c50.',        # Crop profil resmi
            '/c100.',       # Crop profil resmi
            '/c200.',       # Crop profil resmi
            'profile_pic',  # Profil resmi göstergesi
            '/safe_image',  # Safe image (genellikle profil)
            't39.30808-1',  # Facebook profil resmi type
            'cp0/e15/q65', # Profil resmi parametreleri
        ]
        
        # URL'de profil resmi göstergesi varsa reddet
        for indicator in profile_indicators:
            if indicator in url.lower():
                return False
        
        # Çok küçük boyutlu resimleri filtrele (genellikle profil resimleri)
        size_patterns = [
            r'[&?]w=([0-9]+)',
            r'[&?]h=([0-9]+)',
            r'/([0-9]+)x([0-9]+)/',
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, url)
            for match in matches:
                if isinstance(match, tuple):
                    # Tuple durumunda (width, height)
                    width, height = int(match[0]), int(match[1])
                    if width < 300 or height < 300:  # 300px'den küçük resimleri filtrele
                        return False
                else:
                    # Tek değer durumunda
                    size = int(match)
                    if size < 300:  # 300px'den küçük resimleri filtrele
                        return False
        
        return True
    
    def _clean_photo_url(self, url):
        """Fotoğraf URL'ini temizler"""
        if not url:
            return None
        
        # Escape karakterlerini temizle
        url = url.replace('\\/', '/').replace('\\u0026', '&').replace('&amp;', '&')
        
        # URL decode
        try:
            from urllib.parse import unquote
            url = unquote(url)
        except:
            pass
        
        return url
    
    def _select_best_photo_url(self, photo_urls):
        """En iyi kaliteli fotoğraf URL'ini seçer - hedef boyut: 1290x1720 px (3:4 aspect ratio)"""
        if not photo_urls:
            return None
        
        # Hedef boyutlar
        target_width = 1290
        target_height = 1720
        target_aspect_ratio = 3/4  # 0.75
        
        # URL'leri kalite kriterlerine göre sırala
        def quality_score(url):
            score = 0
            
            # Boyut parametrelerini URL'den çıkarmaya çalış
            width_match = re.search(r'[&?]w=([0-9]+)', url)
            height_match = re.search(r'[&?]h=([0-9]+)', url)
            
            if width_match and height_match:
                width = int(width_match.group(1))
                height = int(height_match.group(1))
                aspect_ratio = width / height
                
                # Hedef boyutlara yakınlık puanı
                width_diff = abs(width - target_width) / target_width
                height_diff = abs(height - target_height) / target_height
                aspect_diff = abs(aspect_ratio - target_aspect_ratio) / target_aspect_ratio
                
                # Boyut yakınlığı puanı (0-100)
                size_score = max(0, 100 - (width_diff + height_diff) * 50)
                aspect_score = max(0, 50 - aspect_diff * 50)
                
                score += size_score + aspect_score
                
                # Hedef boyuttan büyük görüntüleri tercih et
                if width >= target_width and height >= target_height:
                    score += 50
                
                self.log(f"📏 URL boyut analizi: {width}x{height} (AR: {aspect_ratio:.2f}) - Puan: {score:.1f}")
            else:
                # Boyut bilgisi yoksa, geleneksel kalite göstergelerini kullan
                if '_o.' in url or '_n.' in url:  # Orijinal veya büyük boyut
                    score += 100
                elif '_b.' in url:  # Büyük boyut
                    score += 80
                elif '_c.' in url:  # Orta boyut
                    score += 60
                elif '_s.' in url:  # Küçük boyut
                    score += 40
                
                # URL uzunluğu (genellikle daha uzun = daha fazla parametre = daha iyi kalite)
                score += len(url) / 10
            
            return score
        
        best_url = max(photo_urls, key=quality_score)
        self.log(f"🎯 En uygun fotoğraf URL'i seçildi: {best_url[:100]}...")
        return best_url
    
    def download_photo(self, photo_url, output_path):
        """Fotoğrafı indirir - geliştirilmiş hata yönetimi ile"""
        try:
            # Profil fotoğrafı kontrolü - profil fotoğraflarını indirme
            if self._is_profile_photo(photo_url):
                self.log(f"⏭️ Profil/kapak fotoğrafı atlanıyor: {photo_url}")
                return False
            
            self.log(f"📥 Fotoğraf indiriliyor: {photo_url}")
            
            # Fotoğraf URL'ini çıkar
            if 'photo' in photo_url and not any(domain in photo_url for domain in ['scontent', 'fbcdn']):
                actual_photo_url = self.extract_photo_url(photo_url)
                if not actual_photo_url:
                    self.log(f"❌ Fotoğraf URL'i çıkarılamadı: {photo_url}")
                    return False
            else:
                actual_photo_url = photo_url
                
            # URL geçerliliğini kontrol et
            if not self._is_valid_photo_url(actual_photo_url):
                self.log(f"❌ Geçersiz fotoğraf URL'i: {actual_photo_url}")
                return False
            
            # Farklı header kombinasyonlarını dene
            header_sets = [
                {
                    'Referer': 'https://www.facebook.com/',
                    'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Cache-Control': 'no-cache'
                },
                {
                    'Referer': photo_url if 'facebook.com' in photo_url else 'https://m.facebook.com/',
                    'Accept': 'image/*,*/*;q=0.8',
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                },
                {
                    'Accept': '*/*',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            ]
            
            for i, headers in enumerate(header_sets):
                try:
                    # Mevcut session header'larını koru ve yeni header'ları ekle
                    temp_headers = self.session.headers.copy()
                    temp_headers.update(headers)
                    
                    response = self.session.get(
                        actual_photo_url, 
                        headers=temp_headers, 
                        timeout=30,
                        stream=True
                    )
                    
                    if response.status_code == 200:
                        # Dosya uzantısını belirle
                        content_type = response.headers.get('content-type', '')
                        if 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'
                        elif 'png' in content_type:
                            ext = '.png'
                        elif 'webp' in content_type:
                            ext = '.webp'
                        else:
                            # URL'den uzantıyı çıkarmaya çalış
                            url_ext = re.search(r'\.(jpg|jpeg|png|webp)', actual_photo_url, re.IGNORECASE)
                            ext = url_ext.group(0) if url_ext else '.jpg'
                        
                        # Dosya adını oluştur
                        if not output_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            output_path += ext
                        
                        # Dosyayı kaydet
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        file_size = os.path.getsize(output_path)
                        
                        # Dosya boyutu kontrolü (çok küçükse hata olabilir)
                        if file_size < 1024:  # 1KB'den küçükse
                            self.log(f"⚠️ Dosya çok küçük ({file_size} bytes), başka yöntem deneniyor...")
                            os.remove(output_path)
                            continue
                        
                        self.log(f"✅ Fotoğraf indirildi: {output_path} ({file_size} bytes)")
                        return True
                        
                    elif response.status_code == 403:
                        self.log(f"⚠️ HTTP 403 hatası (deneme {i+1}/{len(header_sets)}), farklı header deneniyor...")
                        continue
                    else:
                        self.log(f"⚠️ HTTP {response.status_code} hatası (deneme {i+1}/{len(header_sets)})")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    self.log(f"⚠️ İstek hatası (deneme {i+1}/{len(header_sets)}): {str(e)}")
                    continue
            
            self.log("❌ Tüm indirme yöntemleri başarısız oldu")
            return False
                
        except Exception as e:
            self.log(f"❌ Fotoğraf indirme hatası: {str(e)}")
            return False
    
    def _is_profile_photo(self, url):
        """URL'nin profil fotoğrafı olup olmadığını kontrol eder - Geliştirilmiş versiyon"""
        if not url:
            return False
        
        # Profil fotoğrafı göstergeleri - Genişletilmiş liste
        profile_indicators = [
            'profile',
            'profilepic', 
            'profile_pic',
            'profile_picture',
            'avatar',
            'user_photo',
            'profile_image',
            'profile_img',
            '/pp/',
            'type=1',  # Facebook profil fotoğrafı type parametresi
            'type=3',  # Facebook kapak fotoğrafı type parametresi
            'profile.php',
            'picture.php',
            'picture?',
            'picture/',
            'profilepicture',
            'user_avatar',
            'user_pic',
            'user_image',
            'cover_photo',
            'cover_pic',
            'cover_image',
            'coverphoto',
            'timeline_cover',
            'banner_image',
            'header_image',
            'dp.',  # Display picture kısaltması
            'pfp.',  # Profile picture kısaltması
            '/profile/',
            '/avatar/',
            '/user/',
            'profile_photos',
            'timeline_photos',
            'mobile_photos',
            'profile_timeline',
            'set=a.profile',
            'set=a.timeline',
            'set=profile',
            'set=timeline',
            'set=cover',
            'album_id=profile',
            'album_id=timeline',
            'album_type=profile',
            'album_type=timeline'
        ]
        
        url_lower = url.lower()
        
        # Temel göstergeleri kontrol et
        for indicator in profile_indicators:
            if indicator in url_lower:
                self.log(f"⏭️ Profil/kapak fotoğrafı tespit edildi ('{indicator}'): {url[:100]}...")
                return True
        
        # URL pattern'leri ile daha detaylı kontrol
        profile_patterns = [
            r'/photos/[^/]+/profile',
            r'/photos/[^/]+/timeline',
            r'/photos/[^/]+/cover',
            r'/photo\.php\?fbid=\d+.*type=[13]',
            r'/photo/\?fbid=\d+.*type=[13]',
            r'/photos/profile/',
            r'/photos/timeline/',
            r'/photos/cover/',
            r'album_id=\d+.*type=[13]',
            r'set=a\.\d+.*type=[13]',
            r'profile.*picture',
            r'timeline.*picture',
            r'cover.*picture'
        ]
        
        for pattern in profile_patterns:
            if re.search(pattern, url_lower):
                self.log(f"⏭️ Profil/kapak fotoğrafı pattern tespit edildi: {url[:100]}...")
                return True
        
        # Boyut kontrolü - Profil fotoğrafları genellikle kare veya belirli boyutlarda olur
        size_patterns = [
            r'[&?]w=([0-9]+)',
            r'[&?]h=([0-9]+)',
            r'[&?]width=([0-9]+)',
            r'[&?]height=([0-9]+)'
        ]
        
        width = height = None
        for pattern in size_patterns:
            match = re.search(pattern, url_lower)
            if match:
                size = int(match.group(1))
                if 'w=' in pattern or 'width=' in pattern:
                    width = size
                elif 'h=' in pattern or 'height=' in pattern:
                    height = size
        
        # Profil fotoğrafı boyut kontrolü (genellikle 160x160, 320x320, 480x480 gibi)
        if width and height:
            # Kare fotoğraflar ve küçük boyutlar profil fotoğrafı olabilir
            if width == height and width <= 500:
                self.log(f"⏭️ Profil fotoğrafı boyut tespit edildi ({width}x{height}): {url[:100]}...")
                return True
            
            # Yaygın profil fotoğrafı boyutları
            common_profile_sizes = [(160, 160), (320, 320), (480, 480), (200, 200), (100, 100), (50, 50)]
            if (width, height) in common_profile_sizes:
                self.log(f"⏭️ Standart profil fotoğrafı boyutu tespit edildi ({width}x{height}): {url[:100]}...")
                return True
        
        return False
    
    def download_video_with_http_api(self, video_url, output_path):
        """HTTP/API kullanarak video indirir"""
        try:
            self.log(f"🌐 HTTP/API ile video indiriliyor: {video_url}")
            
            # Facebook Graph API kullanarak video bilgilerini al
            video_info = self._get_video_info_from_api(video_url)
            if video_info and 'video_url' in video_info:
                self.log(f"✅ API'den video URL alındı: {video_info['video_url'][:100]}...")
                return self._download_video_file(video_info['video_url'], output_path)
            
            # API başarısız olursa, HTTP scraping ile dene
            return self._download_video_with_http_scraping(video_url, output_path)
            
        except Exception as e:
            self.log(f"❌ HTTP/API video indirme hatası: {str(e)}")
            return False
    
    def _get_video_info_from_api(self, video_url):
        """Facebook Graph API kullanarak video bilgilerini alır"""
        try:
            # Video ID'sini URL'den çıkar
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None
            
            # Graph API endpoint'i
            api_url = f"https://graph.facebook.com/v18.0/{video_id}"
            
            # API parametreleri
            params = {
                'fields': 'source,title,description,length,created_time,picture',
                'access_token': self._get_public_access_token()
            }
            
            response = self.session.get(api_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'source' in data:
                    return {
                        'video_url': data['source'],
                        'title': data.get('title', ''),
                        'description': data.get('description', ''),
                        'duration': data.get('length', 0),
                        'thumbnail': data.get('picture', '')
                    }
            
            return None
            
        except Exception as e:
            self.log(f"⚠️ API video bilgisi alınamadı: {str(e)}")
            return None
    
    def _extract_video_id(self, video_url):
        """Video URL'sinden video ID'sini çıkarır"""
        try:
            # Farklı Facebook video URL formatları için regex pattern'leri
            patterns = [
                r'/videos/(?:vb\.\d+/)?([0-9]+)',
                r'/watch/\?v=([0-9]+)',
                r'/reel/([0-9]+)',
                r'video_id=([0-9]+)',
                r'/([0-9]{10,})/?',
                r'fbid=([0-9]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, video_url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def _get_public_access_token(self):
        """Genel erişim token'ı alır"""
        # Facebook'un genel API erişimi için app token formatı
        # Bu gerçek bir production uygulamasında güvenli bir şekilde saklanmalı
        return "your_app_id|your_app_secret"  # Placeholder
    
    def _download_video_with_http_scraping(self, video_url, output_path):
        """HTTP scraping ile video indirir"""
        try:
            self.log("🔍 HTTP scraping ile video URL'i aranıyor...")
            
            # Sayfa içeriğini al
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://www.facebook.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(video_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.log(f"❌ Sayfa yüklenemedi: HTTP {response.status_code}")
                return False
            
            content = response.text
            
            # Video URL pattern'leri (Facebook'un farklı formatları için)
            video_patterns = [
                r'"playable_url":"([^"]+)"',
                r'"playable_url_quality_hd":"([^"]+)"',
                r'"video_url":"([^"]+)"',
                r'"src":"([^"]+\.mp4[^"]*?)"',
                r'"url":"([^"]+\.mp4[^"]*?)"',
                r'hd_src:"([^"]+)"',
                r'sd_src:"([^"]+)"',
                r'"representation_url":"([^"]+)"',
                r'"browser_native_hd_url":"([^"]+)"',
                r'"browser_native_sd_url":"([^"]+)"'
            ]
            
            video_urls = []
            
            for pattern in video_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # URL'yi decode et
                    decoded_url = match.replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
                    decoded_url = decoded_url.replace('%3A', ':').replace('%2F', '/').replace('%3F', '?').replace('%3D', '=')
                    
                    if decoded_url.startswith('http') and any(ext in decoded_url.lower() for ext in ['.mp4', '.webm', '.avi']):
                        video_urls.append(decoded_url)
            
            if not video_urls:
                self.log("❌ Sayfa içeriğinde video URL'i bulunamadı")
                return False
            
            # En iyi kaliteli URL'i seç (genellikle HD olan)
            best_url = self._select_best_video_url(video_urls)
            self.log(f"✅ Video URL bulundu: {best_url[:100]}...")
            
            # Video dosyasını indir
            return self._download_video_file(best_url, output_path)
            
        except Exception as e:
            self.log(f"❌ HTTP scraping video indirme hatası: {str(e)}")
            return False
    
    def _select_best_video_url(self, video_urls):
        """En iyi kaliteli video URL'ini seçer"""
        if not video_urls:
            return None
        
        # HD kalite göstergeleri
        hd_indicators = ['hd', 'high', '720', '1080', 'quality_hd']
        
        # HD URL'leri öncelikle seç
        hd_urls = []
        for url in video_urls:
            url_lower = url.lower()
            if any(indicator in url_lower for indicator in hd_indicators):
                hd_urls.append(url)
        
        if hd_urls:
            # En uzun HD URL'i seç (genellikle daha fazla parametre = daha iyi kalite)
            return max(hd_urls, key=len)
        
        # HD bulunamazsa, en uzun URL'i seç
        return max(video_urls, key=len)
    
    def _download_video_file(self, video_url, output_path):
        """Video dosyasını indirir"""
        try:
            self.log(f"📥 Video dosyası indiriliyor: {video_url}")
            
            # Video header'ları
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Accept-Language': 'en-US,en;q=0.5',
                'Range': 'bytes=0-',
                'Referer': 'https://www.facebook.com/'
            }
            
            response = self.session.get(video_url, headers=headers, stream=True, timeout=60)
            
            if response.status_code in [200, 206]:  # 206 for partial content
                # Dosya uzantısını belirle
                content_type = response.headers.get('content-type', '')
                if 'mp4' in content_type:
                    ext = '.mp4'
                elif 'webm' in content_type:
                    ext = '.webm'
                elif 'avi' in content_type:
                    ext = '.avi'
                else:
                    ext = '.mp4'  # Varsayılan
                
                # Dosya adını oluştur
                if not output_path.endswith(('.mp4', '.webm', '.avi', '.mov')):
                    output_path += ext
                
                # Dosyayı kaydet
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # İlerleme göster
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                if downloaded_size % (1024 * 1024) == 0:  # Her MB'da log
                                    self.log(f"📥 İndiriliyor: {progress:.1f}% ({downloaded_size // (1024*1024)}MB/{total_size // (1024*1024)}MB)")
                
                file_size = os.path.getsize(output_path)
                
                # Dosya boyutu kontrolü
                if file_size < 10240:  # 10KB'den küçükse
                    self.log(f"⚠️ Video dosyası çok küçük ({file_size} bytes)")
                    os.remove(output_path)
                    return False
                
                self.log(f"✅ Video indirildi: {output_path} ({file_size // (1024*1024)}MB)")
                return True
            else:
                self.log(f"❌ Video indirme hatası: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Video dosyası indirme hatası: {str(e)}")
            return False
    
    def download_video_with_direct_http(self, video_url, output_path):
        """Doğrudan HTTP ile video indirir (FFmpeg alternatifi)"""
        try:
            self.log(f"🌐 Doğrudan HTTP ile video indiriliyor: {video_url}")
            
            # Facebook'un mobil versiyonunu dene (daha basit HTML)
            mobile_url = video_url.replace('www.facebook.com', 'm.facebook.com')
            
            # Mobil sayfa içeriğini al
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://m.facebook.com/',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(mobile_url, headers=mobile_headers, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                
                # Mobil sayfada video URL pattern'leri
                mobile_patterns = [
                    r'"videoUrl":"([^"]+)"',
                    r'"src":"([^"]+\.mp4[^"]*?)"',
                    r'data-sigil="inlineVideo"[^>]*src="([^"]+)"',
                    r'<video[^>]*src="([^"]+)"',
                    r'"playable_url":"([^"]+)"'
                ]
                
                for pattern in mobile_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        decoded_url = match.replace('\\/', '/').replace('\\u0026', '&')
                        if decoded_url.startswith('http') and '.mp4' in decoded_url:
                            self.log(f"✅ Mobil sayfadan video URL bulundu: {decoded_url[:100]}...")
                            return self._download_video_file(decoded_url, output_path)
            
            # Mobil başarısız olursa, embed URL'i dene
            return self._try_embed_video_download(video_url, output_path)
            
        except Exception as e:
            self.log(f"❌ Doğrudan HTTP video indirme hatası: {str(e)}")
            return False
    
    def _try_embed_video_download(self, video_url, output_path):
        """Embed video URL'i ile indirme dener"""
        try:
            self.log("🔗 Embed video URL'i deneniyor...")
            
            # Video ID'sini çıkar
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return False
            
            # Embed URL'i oluştur
            embed_url = f"https://www.facebook.com/plugins/video.php?href={video_url}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://www.facebook.com/'
            }
            
            response = self.session.get(embed_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                
                # Embed sayfasında video URL pattern'leri
                embed_patterns = [
                    r'"videoUrl":"([^"]+)"',
                    r'"src":"([^"]+\.mp4[^"]*?)"',
                    r'"playable_url":"([^"]+)"',
                    r'hd_src:"([^"]+)"',
                    r'sd_src:"([^"]+)"'
                ]
                
                for pattern in embed_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        decoded_url = match.replace('\\/', '/').replace('\\u0026', '&')
                        if decoded_url.startswith('http') and '.mp4' in decoded_url:
                            self.log(f"✅ Embed sayfasından video URL bulundu: {decoded_url[:100]}...")
                            return self._download_video_file(decoded_url, output_path)
            
            return False
            
        except Exception as e:
            self.log(f"❌ Embed video indirme hatası: {str(e)}")
            return False
    
    def download_video_alternative(self, video_url, output_path):
        """HTTP/API tabanlı video indirme yöntemleri"""
        self.log(f"🌐 HTTP/API tabanlı yöntemlerle video indiriliyor: {video_url}")
        
        # Yöntem 1: Facebook Graph API
        self.log("🔧 Yöntem 1: Facebook Graph API deneniyor...")
        if self.download_video_with_http_api(video_url, output_path):
            return True
        
        # Yöntem 2: Doğrudan HTTP scraping
        self.log("🔧 Yöntem 2: HTTP scraping deneniyor...")
        if self._download_video_with_http_scraping(video_url, output_path):
            return True
        
        # Yöntem 3: Mobil ve embed URL'leri
        self.log("🔧 Yöntem 3: Mobil/embed HTTP deneniyor...")
        if self.download_video_with_direct_http(video_url, output_path):
            return True
        
        # Yöntem 4: Doğrudan regex ile video URL çıkarma
        self.log("🔧 Yöntem 4: Doğrudan video URL çıkarma deneniyor...")
        if self._download_video_direct(video_url, output_path):
            return True
        
        self.log("❌ Tüm HTTP/API tabanlı video indirme yöntemleri başarısız oldu")
        return False
    
    def _download_video_direct(self, video_url, output_path):
        """Doğrudan video URL'i çıkararak indirir"""
        try:
            self.log("🔍 Sayfa içeriğinden video URL'i aranıyor...")
            
            content = self.get_page_content(video_url)
            if not content:
                return False
            
            # Video URL pattern'leri
            video_patterns = [
                r'"playable_url":"([^"]+)"',
                r'"playable_url_quality_hd":"([^"]+)"',
                r'"video_url":"([^"]+)"',
                r'"src":"([^"]+\.mp4[^"]*)"',
                r'"url":"([^"]+\.mp4[^"]*)"',
                r'hd_src:"([^"]+)"',
                r'sd_src:"([^"]+)"',
                r'"representation_url":"([^"]+)"'
            ]
            
            video_urls = []
            
            for pattern in video_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # URL'yi decode et
                    decoded_url = match.replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
                    if decoded_url.startswith('http') and any(ext in decoded_url for ext in ['.mp4', '.webm', '.avi']):
                        video_urls.append(decoded_url)
            
            if not video_urls:
                self.log("❌ Sayfa içeriğinde video URL'i bulunamadı")
                return False
            
            # En iyi kaliteli URL'i seç (genellikle en uzun olan)
            best_url = max(video_urls, key=len)
            self.log(f"✅ Video URL bulundu: {best_url[:100]}...")
            
            # Video dosyasını indir
            return self._download_video_file(best_url, output_path)
            
        except Exception as e:
            self.log(f"❌ Doğrudan video indirme hatası: {str(e)}")
            return False

    def close(self):
        """Scraper'ı kapatır ve cookie'leri kaydeder"""
        self.save_cookies()
        self.session.close()
        self.log("🔒 Facebook Request Scraper kapatıldı")