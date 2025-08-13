import requests
import json
import re
import os
import time
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import random
from typing import Dict, List, Optional, Tuple

class InstagramHttpDownloader:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        self.setup_session()
        
        # Dosya sayaçları - sıralı isimlendirme için
        self.photo_counter = 0
        self.video_counter = 0
    
    def reset_counters(self):
        """Dosya sayaçlarını sıfırlar - yeni indirme işlemi başlangıcında kullanılır"""
        self.photo_counter = 0
        self.video_counter = 0
        self.log("🔄 Dosya sayaçları sıfırlandı")
        
    def log(self, message: str):
        """Log mesajı yazdırır"""
        # Tüm emoji ve özel karakterleri kaldır (Windows terminal uyumluluğu için)
        import re
        # Emoji ve özel karakterleri kaldır
        clean_message = re.sub(r'[\U0001F000-\U0001F9FF]', '', message)  # Emojiler
        clean_message = re.sub(r'[\u2600-\u26FF]', '', clean_message)      # Çeşitli semboller
        clean_message = re.sub(r'[\u2700-\u27BF]', '', clean_message)      # Dingbats
        clean_message = re.sub(r'[\uFE0F]', '', clean_message)             # Variation selector
        clean_message = re.sub(r'[\u200D]', '', clean_message)             # Zero width joiner
        
        # Sadece ASCII karakterleri bırak
        clean_message = ''.join(char for char in clean_message if ord(char) < 128)
        
        if self.log_callback:
            self.log_callback(clean_message)
        else:
            print(clean_message)
    
    def setup_session(self):
        """HTTP oturumunu ayarlar"""
        # Güncel Chrome desktop tarayıcı başlıkları (daha az şüpheli)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
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
        
        # Gerçek tarayıcı cookie'leri ekle
        self._add_browser_cookies()
        
        # Instagram ana sayfasını ziyaret ederek CSRF token ve cookie'leri al
        self._initialize_session()
        
    def detect_content_type(self, url: str) -> str:
        """URL'den içerik tipini tespit eder"""
        if '/p/' in url and url.endswith('/p/'):
            return 'profile_posts'  # Profil gönderileri sayfası
        elif '/p/' in url:
            return 'post'  # Fotoğraf veya video post
        elif '/reel/' in url:
            return 'reel'  # Reels video
        elif '/stories/' in url:
            return 'story'  # Story
        elif '/explore/tags/' in url:
            return 'hashtag'  # Hashtag sayfası
        elif '/reels/' in url:
            return 'profile_reels'  # Profil reels sayfası
        elif re.match(r'https?://(www\.)?instagram\.com/[A-Za-z0-9_.]+/?$', url):
            return 'profile'  # Profil
        else:
            return 'unknown'
    
    def extract_shortcode(self, url: str) -> Optional[str]:
        """URL'den shortcode'u çıkarır"""
        patterns = [
            r'/p/([A-Za-z0-9_-]+)',
            r'/reel/([A-Za-z0-9_-]+)',
            r'/tv/([A-Za-z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    

    
    def _add_browser_cookies(self):
        """Gerçek tarayıcı cookie'lerini ekler"""
        try:
            # Instagram için gerekli temel cookie'ler
            cookies = {
                'ig_did': 'A1B2C3D4-E5F6-7890-ABCD-EF1234567890',
                'ig_nrcb': '1',
                'mid': 'ZqJ' + str(random.randint(100000, 999999)) + 'AAE',
                'datr': 'ZqJ' + str(random.randint(100000, 999999)),
                'dpr': '1',
                'wd': '1920x969'
            }
            
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain='.instagram.com')
                
            self.log("🍪 Tarayıcı cookie'leri eklendi")
            
        except Exception as e:
            self.log(f"⚠️ Cookie ekleme hatası: {str(e)}")
    
    def set_cookies(self, cookies_dict):
        """Dış kaynaklardan gelen cookie'leri ayarlar"""
        try:
            if not cookies_dict:
                return
            
            # Mevcut cookie'leri temizle
            self.session.cookies.clear()
            
            # Yeni cookie'leri ekle
            if isinstance(cookies_dict, dict):
                # Dictionary formatı
                for name, value in cookies_dict.items():
                    self.session.cookies.set(name, value, domain='.instagram.com')
                self.log(f"🍪 {len(cookies_dict)} adet cookie ayarlandı")
            elif isinstance(cookies_dict, list):
                # Liste formatı (Selenium'dan gelen)
                for cookie in cookies_dict:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        self.session.cookies.set(cookie['name'], cookie['value'], domain='.instagram.com')
                self.log(f"🍪 {len(cookies_dict)} adet cookie ayarlandı")
            else:
                self.log(f"⚠️ Desteklenmeyen cookie formatı: {type(cookies_dict)}")
            
            # Cookie'leri ayarladıktan sonra geçerliliğini test et
            self._test_session_validity()
            
        except Exception as e:
            self.log(f"⚠️ Cookie ayarlama hatası: {str(e)}")
    
    def _test_session_validity(self):
        """Mevcut session'ın geçerliliğini test eder"""
        try:
            # Instagram ana sayfasını test et
            response = self.session.get('https://www.instagram.com/', timeout=15, allow_redirects=False)
            
            # Redirect kontrolü
            if response.status_code in [301, 302, 303, 307, 308]:
                redirect_url = response.headers.get('Location', '')
                if 'login' in redirect_url or 'accounts/login' in redirect_url:
                    self.log("⚠️ Session geçersiz - giriş yapılmamış, hashtag erişimi sınırlı olabilir")
                    return False
                else:
                    # Redirect'i takip et
                    response = self.session.get('https://www.instagram.com/', timeout=15)
            
            # Response içeriğini kontrol et
            if response.status_code == 200:
                content = response.text.lower()
                
                # Login sayfası kontrolü
                if 'login' in content and ('password' in content or 'şifre' in content):
                    self.log("⚠️ Session geçersiz - login sayfasına yönlendirildi")
                    return False
                
                # Başarılı giriş kontrolü
                if 'sessionid' in [cookie.name for cookie in self.session.cookies]:
                    sessionid = None
                    for cookie in self.session.cookies:
                        if cookie.name == 'sessionid':
                            sessionid = cookie.value
                            break
                    
                    if sessionid and len(sessionid) > 10:  # Geçerli sessionid uzunluğu kontrolü
                        self.log("✅ Session geçerli - giriş yapılmış")
                        return True
                
                self.log("⚠️ Session durumu belirsiz - sınırlı erişim")
                return False
            else:
                self.log(f"⚠️ Session test hatası: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Session geçerlilik testi hatası: {str(e)}")
            return False
    
    def _initialize_session(self):
        """Instagram session'ını başlatır ve gerekli token'ları alır"""
        try:
            self.log("🔄 Instagram session başlatılıyor...")
            
            # Ana sayfayı ziyaret et
            response = self.session.get('https://www.instagram.com/', timeout=30)
            if response.status_code != 200:
                self.log(f"⚠️ Ana sayfa erişim hatası: {response.status_code}")
                return
            
            # CSRF token'ı çıkar
            csrf_token = None
            for cookie in self.session.cookies:
                if cookie.name == 'csrftoken':
                    csrf_token = cookie.value
                    break
            
            if not csrf_token:
                # HTML'den CSRF token çıkarmayı dene
                csrf_match = re.search(r'"csrf_token":"([^"]+)"', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            if csrf_token:
                self.csrf_token = csrf_token  # Instance variable olarak kaydet
                self.session.headers.update({
                    'X-CSRFToken': csrf_token,
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-IG-App-ID': '936619743392459',
                    'X-IG-WWW-Claim': '0',
                    'X-Instagram-AJAX': '1',
                    'Referer': 'https://www.instagram.com/',
                    'Origin': 'https://www.instagram.com'
                })
                self.log("✅ CSRF token alındı")
            else:
                self.csrf_token = None  # Token alınamazsa None olarak ayarla
            
            # Kısa bir bekleme
            time.sleep(2)
            
        except Exception as e:
            self.log(f"⚠️ Session başlatma hatası: {str(e)}")
            self.csrf_token = None  # Hata durumunda None olarak ayarla
    
    def get_post_data(self, shortcode: str) -> Optional[Dict]:
        """Instagram post verilerini alır"""
        try:
            # Web sayfasından veri çıkarmayı dene
            url = f"https://www.instagram.com/p/{shortcode}/"
            self.log(f"🔍 Web sayfasından post verileri alınıyor: {url}")
            
            # İlk olarak ana sayfayı ziyaret et (cookie almak için)
            self.session.get('https://www.instagram.com/')
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                self.log(f"❌ HTTP hatası: {response.status_code}")
                return None
            
            # HTML içeriğinden JSON verilerini çıkar
            html_content = response.text
            
            # Instagram'dan veri çıkarmak için gelişmiş pattern'ler
            patterns = [
                # En yeni Instagram formatları (2024)
                r'"xdt_shortcode_media":\s*({[^}]*(?:{[^}]*}[^}]*)*})',
                r'window\.__additionalDataLoaded\([^,]+,\s*({.*?"xdt_shortcode_media".*?})\);',
                r'"data":\s*({.*?"xdt_shortcode_media".*?}),"extensions"',
                # Eski formatlar
                r'window\._sharedData\s*=\s*({.*?});',
                r'"props":\s*({.*?"shortcode_media".*?})',
                r'"graphql":\s*({.*?"shortcode_media".*?})',
                # Alternatif formatlar
                r'"shortcode_media":\s*({.*?}),"logging_page_id"',
                r'"media":\s*({.*?"__typename".*?})',
            ]
            
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, html_content, re.DOTALL)
                
                for match in matches:
                    try:
                        # JSON parse et
                        if isinstance(match, tuple):
                            match = match[0] if match else '{}'
                        
                        data = json.loads(match)
                        
                        # Yeni formatlar için özel işlem
                        if i < 3 and 'xdt_shortcode_media' in match:
                            if not isinstance(data, dict) or 'data' not in data:
                                # Direkt xdt_shortcode_media objesi ise wrap et
                                if 'id' in data or '__typename' in data:
                                    data = {'data': {'xdt_shortcode_media': data}}
                        
                        if self._validate_post_data(data):
                            self.log("✅ Post verileri başarıyla alındı")
                            return data
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
            
            # Son çare: Basit medya URL'lerini direkt ara
            simple_data = self._extract_simple_media_urls(html_content)
            if simple_data:
                return simple_data
            
            self.log("❌ Post verileri çıkarılamadı")
            return None
            
        except Exception as e:
            self.log(f"❌ Post veri alma hatası: {str(e)}")
            return None
    
    def _get_hashtag_data_graphql(self, hashtag_name: str) -> Optional[Dict]:
        """GraphQL API ile hashtag verilerini alır"""
        try:
            self.log(f"🔍 GraphQL API ile hashtag verileri alınıyor: #{hashtag_name}")
            
            # GraphQL query parametreleri
            variables = {
                "tag_name": hashtag_name,
                "first": 12,
                "after": ""
            }
            
            # GraphQL endpoint
            graphql_url = "https://www.instagram.com/graphql/query/"
            
            # Query hash (Instagram'ın hashtag query'si için)
            query_hash = "9b498c08113f1e09617a1703c22b2f32"
            
            params = {
                "query_hash": query_hash,
                "variables": json.dumps(variables)
            }
            
            # GraphQL isteği gönder
            response = self.session.get(graphql_url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log(f"❌ GraphQL API hatası: {response.status_code}")
                return None
            
            try:
                data = response.json()
                if 'data' in data and 'hashtag' in data['data']:
                    hashtag_data = data['data']['hashtag']
                    if 'edge_hashtag_to_media' in hashtag_data:
                        media_edges = hashtag_data['edge_hashtag_to_media']['edges']
                        self.log(f"✅ GraphQL API'den {len(media_edges)} medya bulundu")
                        
                        # Medya verilerini işle
                        media_list = []
                        for edge in media_edges:
                            node = edge['node']
                            media_info = {
                                'shortcode': node.get('shortcode', ''),
                                'display_url': node.get('display_url', ''),
                                'is_video': node.get('is_video', False),
                                'video_url': node.get('video_url', '') if node.get('is_video') else '',
                                'typename': node.get('__typename', '')
                            }
                            media_list.append(media_info)
                        
                        return {
                            'media_list': media_list,
                            'count': len(media_list)
                        }
                    else:
                        self.log("❌ GraphQL yanıtında medya verisi bulunamadı")
                else:
                    self.log("❌ GraphQL yanıtında hashtag verisi bulunamadı")
            except json.JSONDecodeError:
                self.log("❌ GraphQL yanıtı JSON formatında değil")
            
            return None
            
        except Exception as e:
            self.log(f"❌ GraphQL API hatası: {str(e)}")
            return None
    

    

    

    
    def _validate_post_data(self, data: Dict) -> bool:
        """Post verilerinin geçerliliğini kontrol eder"""
        try:
            # Basit medya formatı
            if 'simple_media' in data:
                media_list = data['simple_media']
                if isinstance(media_list, list) and len(media_list) > 0:
                    # İlk medya öğesini kontrol et
                    first_media = media_list[0]
                    if isinstance(first_media, dict) and 'url' in first_media:
                        return True
            
            # Yeni Instagram formatı
            if 'data' in data and 'xdt_shortcode_media' in data['data']:
                media = data['data']['xdt_shortcode_media']
                # Temel alanları kontrol et
                if media and ('id' in media or '__typename' in media):
                    return True
            
            # Direkt xdt_shortcode_media
            if 'xdt_shortcode_media' in data:
                media = data['xdt_shortcode_media']
                if media and ('id' in media or '__typename' in media):
                    return True
            
            # GraphQL yapısını kontrol et
            if 'graphql' in data and 'shortcode_media' in data['graphql']:
                return True
            
            # Entry data yapısını kontrol et
            if ('entry_data' in data and 
                'PostPage' in data['entry_data'] and 
                len(data['entry_data']['PostPage']) > 0):
                return True
            
            # Direkt shortcode_media
            if 'shortcode_media' in data:
                return True
            
            # Tek medya objesi
            if '__typename' in data and data['__typename'] in ['GraphImage', 'GraphVideo', 'GraphSidecar']:
                return True
            
            return False
            
        except Exception:
            return False
    
    def _extract_simple_media_urls(self, html_content: str) -> Optional[Dict]:
        """HTML'den basit medya URL'lerini çıkarır"""
        try:
            import re
            
            # Video URL'leri ara
            video_patterns = [
                r'"video_url":"([^"]+)"',
                r'"src":"([^"]+\.mp4[^"]*?)"',
                r'"url":"([^"]+\.mp4[^"]*?)"'
            ]
            
            # Fotoğraf URL'leri ara
            image_patterns = [
                r'"display_url":"([^"]+)"',
                r'"src":"([^"]+\.jpg[^"]*?)"',
                r'"url":"([^"]+\.jpg[^"]*?)"'
            ]
            
            media_urls = []
            
            # Video URL'lerini bul
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if 'instagram' in match and ('.mp4' in match or 'video' in match):
                        # URL'yi temizle
                        clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                        media_urls.append({
                            'id': f'video_{len(media_urls)}',
                            'typename': 'GraphVideo',
                            'is_video': True,
                            'url': clean_url,
                            'thumbnail_url': None,
                            'caption': ''
                        })
                        break
            
            # Fotoğraf URL'lerini bul
            if not media_urls:  # Sadece video bulunamazsa fotoğraf ara
                for pattern in image_patterns:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if 'instagram' in match and ('.jpg' in match or '.jpeg' in match):
                            # URL'yi temizle
                            clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                            media_urls.append({
                                'id': f'image_{len(media_urls)}',
                                'typename': 'GraphImage',
                                'is_video': False,
                                'url': clean_url,
                                'thumbnail_url': None,
                                'caption': ''
                            })
                            break
            
            if media_urls:
                # Basit format oluştur
                return {
                    'simple_media': media_urls
                }
            
            return None
            
        except Exception as e:
            self.log(f"❌ Basit URL çıkarma hatası: {str(e)}")
            return None
    
    def extract_media_urls(self, post_data: Dict) -> List[Dict]:
        """Post verilerinden medya URL'lerini çıkarır"""
        media_list = []
        
        try:
            # Basit medya formatı kontrolü
            if 'simple_media' in post_data:
                return post_data['simple_media']
            
            shortcode_media = None
            
            # Yeni Instagram formatı
            if 'data' in post_data and 'xdt_shortcode_media' in post_data['data']:
                shortcode_media = post_data['data']['xdt_shortcode_media']
            # Eski GraphQL formatı
            elif 'graphql' in post_data:
                shortcode_media = post_data['graphql']['shortcode_media']
            elif 'entry_data' in post_data and 'PostPage' in post_data['entry_data']:
                shortcode_media = post_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
            # Direkt shortcode_media
            elif 'shortcode_media' in post_data:
                shortcode_media = post_data['shortcode_media']
            # Tek medya objesi
            elif '__typename' in post_data:
                shortcode_media = post_data
            else:
                self.log("❌ Medya verisi bulunamadı")
                return media_list
            
            if not shortcode_media:
                self.log("❌ Shortcode media verisi boş")
                return media_list
            
            # Tek medya mı yoksa carousel mı?
            carousel_edges = None
            
            # Yeni format için carousel kontrolü
            if 'carousel_media' in shortcode_media:
                carousel_edges = shortcode_media['carousel_media']
            # Eski format için carousel kontrolü
            elif shortcode_media.get('edge_sidecar_to_children'):
                carousel_edges = shortcode_media['edge_sidecar_to_children']['edges']
            
            if carousel_edges:
                # Carousel (birden fazla medya)
                self.log(f"📱 Carousel medya bulundu: {len(carousel_edges)} öğe")
                for item in carousel_edges:
                    # Yeni format
                    if isinstance(item, dict) and 'node' not in item:
                        media_info = self.extract_single_media(item)
                    # Eski format
                    else:
                        node = item.get('node', item)
                        media_info = self.extract_single_media(node)
                    
                    if media_info:
                        media_list.append(media_info)
            else:
                # Tek medya
                self.log("📱 Tek medya bulundu")
                media_info = self.extract_single_media(shortcode_media)
                if media_info:
                    media_list.append(media_info)
            
        except Exception as e:
            self.log(f"❌ Medya URL çıkarma hatası: {str(e)}")
        
        return media_list
    
    def extract_single_media(self, node: Dict) -> Optional[Dict]:
        """Tek bir medya öğesinin bilgilerini çıkarır"""
        try:
            media_info = {
                'id': node.get('id', ''),
                'typename': node.get('__typename', ''),
                'is_video': False,
                'url': None,
                'thumbnail_url': None,
                'caption': ''
            }
            
            # Video kontrolü - farklı formatlar
            is_video = (
                node.get('is_video', False) or 
                node.get('media_type') == 2 or  # Instagram media type 2 = video
                'video_url' in node or
                'video_versions' in node
            )
            
            media_info['is_video'] = is_video
            
            # Video mu fotoğraf mı?
            if is_video:
                # Video URL'sini al
                video_url = (
                    node.get('video_url') or
                    (node.get('video_versions', [{}])[0].get('url') if node.get('video_versions') else None)
                )
                media_info['url'] = video_url
                
                # Thumbnail URL
                thumbnail_url = (
                    node.get('display_url') or
                    node.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
                )
                media_info['thumbnail_url'] = thumbnail_url
            else:
                # Fotoğraf URL'sini al
                image_url = (
                    node.get('display_url') or
                    (node.get('image_versions2', {}).get('candidates', [{}])[0].get('url') if node.get('image_versions2') else None)
                )
                media_info['url'] = image_url
            
            # Caption (açıklama) al - farklı formatlar
            caption = ''
            
            # Yeni format
            if 'caption' in node and node['caption']:
                if isinstance(node['caption'], dict):
                    caption = node['caption'].get('text', '')
                else:
                    caption = str(node['caption'])
            
            # Eski format
            elif 'edge_media_to_caption' in node:
                edges = node['edge_media_to_caption']['edges']
                if edges:
                    caption = edges[0]['node']['text']
            
            media_info['caption'] = caption
            
            # URL kontrolü
            if not media_info['url']:
                self.log(f"⚠️ Medya URL'si bulunamadı: {media_info['typename']}")
                return None
            
            return media_info
            
        except Exception as e:
            self.log(f"❌ Tek medya çıkarma hatası: {str(e)}")
            return None
    
    def download_media(self, media_info: Dict, output_dir: str, filename_prefix: str = "", force_mp4: bool = False) -> Optional[str]:
        """Medya dosyasını indirir"""
        try:
            if not media_info['url']:
                self.log("❌ Medya URL'si bulunamadı")
                return None
            
            # Dosya uzantısını belirle
            if media_info['is_video']:
                extension = '.mp4'
                media_type = 'video'
            elif force_mp4:
                # Ses eklenmiş hikayeler için MP4
                extension = '.mp4'
                media_type = 'video'
            else:
                # Fotoğraflar için JPEG
                extension = '.jpeg'
                media_type = 'photo'
            
            # Dosya adını oluştur - sıralı isimlendirme ile
            if media_info['is_video'] or force_mp4:
                filename = f"{filename_prefix}{self.video_counter}{extension}"
                self.video_counter += 1
            else:
                filename = f"{filename_prefix}{self.photo_counter}{extension}"
                self.photo_counter += 1
            
            filepath = os.path.join(output_dir, filename)
            
            # Dosyayı indir
            self.log(f"{media_type.capitalize()} indiriliyor: {filename}")
            
            # Farklı User-Agent'lar ile retry mekanizması
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Android 14; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0'
            ]
            
            for attempt, user_agent in enumerate(user_agents, 1):
                try:
                    # Instagram medya indirme için özel header'lar
                    download_headers = {
                        'User-Agent': user_agent,
                        'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': 'https://www.instagram.com/',
                        'Origin': 'https://www.instagram.com',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Sec-Fetch-Dest': 'image',
                        'Sec-Fetch-Mode': 'no-cors',
                        'Sec-Fetch-Site': 'cross-site',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                    
                    # CSRF token varsa ekle
                    if hasattr(self, 'csrf_token') and self.csrf_token:
                        download_headers['X-CSRFToken'] = self.csrf_token
                    
                    # Yeni session oluştur (cookie'leri koruyarak)
                    temp_session = requests.Session()
                    temp_session.cookies.update(self.session.cookies)
                    
                    # Çerezleri de gönder
                    response = temp_session.get(media_info['url'], headers=download_headers, stream=True, timeout=30)
                    
                    if response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        self.log(f"İndirildi: {filename}")
                        return filepath
                    elif response.status_code == 403:
                        if attempt < len(user_agents):
                            time.sleep(random.uniform(2, 4))  # Rastgele bekleme
                            continue
                        else:
                            self.log(f"❌ Tüm denemeler başarısız (403). Instagram erişimi kısıtlamış olabilir.")
                            self.log(f"💡 İpucu: VPN kullanmayı veya farklı bir zamanda denemeyi düşünün.")
                            return None
                    else:
                        if attempt < len(user_agents):
                            time.sleep(random.uniform(1, 2))
                            continue
                        else:
                            self.log(f"❌ Tüm denemeler başarısız: HTTP {response.status_code}")
                            return None
                            
                except Exception as retry_error:
                    if attempt < len(user_agents):
                        time.sleep(random.uniform(1, 3))
                        continue
                    else:
                        raise retry_error
            
            return None
                
        except Exception as e:
            self.log(f"❌ Medya indirme hatası: {str(e)}")
            return None
    
    def download_post(self, post_url: str, output_dir: str) -> List[str]:
        """Instagram post'unu indirir"""
        try:
            self.log(f"📥 Post indiriliyor: {post_url}")
            
            # Shortcode'u çıkar
            shortcode = self.extract_shortcode(post_url)
            if not shortcode:
                self.log("❌ Shortcode çıkarılamadı")
                return []
            
            # Post verilerini al
            post_data = self.get_post_data(shortcode)
            if not post_data:
                self.log("❌ Post verileri alınamadı")
                return []
            
            # Medya URL'lerini çıkar
            media_list = self.extract_media_urls(post_data)
            if not media_list:
                self.log("❌ Medya bulunamadı")
                return []
            
            # Çıktı klasörünü oluştur
            os.makedirs(output_dir, exist_ok=True)
            
            downloaded_files = []
            
            # Her medyayı indir
            for i, media_info in enumerate(media_list):
                if len(media_list) > 1:
                    prefix = f"{i+1:02d}_"
                else:
                    prefix = ""
                
                filepath = self.download_media(media_info, output_dir, prefix)
                if filepath:
                    downloaded_files.append(filepath)
                
                # Rate limiting
                time.sleep(random.uniform(0.5, 1.5))
            
            return downloaded_files
            
        except Exception as e:
            self.log(f"❌ Post indirme hatası: {str(e)}")
            return []
    
    def download_from_url(self, url: str, output_dir: str) -> List[str]:
        """URL'den içeriği indirir"""
        downloaded_files = []
        
        try:
            # Çıktı klasörünü oluştur
            os.makedirs(output_dir, exist_ok=True)
            
            # İçerik tipini tespit et
            content_type = self.detect_content_type(url)
            self.log(f"🔍 İçerik tipi: {content_type}")
            
            if content_type in ['post', 'reel']:
                # Shortcode'u çıkar
                shortcode = self.extract_shortcode(url)
                if not shortcode:
                    self.log("❌ Shortcode çıkarılamadı")
                    return downloaded_files
                
                self.log(f"📋 Shortcode: {shortcode}")
                
                # Post verilerini al
                post_data = self.get_post_data(shortcode)
                if not post_data:
                    self.log("❌ Post verileri alınamadı")
                    return downloaded_files
                
                # Medya URL'lerini çıkar
                media_list = self.extract_media_urls(post_data)
                if not media_list:
                    self.log("❌ Medya bulunamadı")
                    return downloaded_files
                
                self.log(f"📱 {len(media_list)} medya bulundu")
                
                # Her medyayı indir
                for i, media_info in enumerate(media_list):
                    if len(media_list) > 1:
                        prefix = f"{i+1:02d}_"
                    else:
                        prefix = ""
                    
                    filepath = self.download_media(media_info, output_dir, prefix)
                    if filepath:
                        downloaded_files.append(filepath)
                    
                    # Rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
            
            elif content_type == 'story':
                # Hikaye indirme
                username = self.extract_story_username(url)
                if not username:
                    self.log("❌ Kullanıcı adı çıkarılamadı")
                    return downloaded_files
                
                self.log(f"👤 Kullanıcı: {username}")
                
                # Bireysel hikaye URL'si mi kontrol et
                if self.is_individual_story_url(url):
                    story_id = self.extract_story_id(url)
                    self.log(f"🎯 Bireysel hikaye ID: {story_id}")
                    
                    # Bireysel hikaye için özel işlem
                    individual_story = self.get_individual_story_data(username, story_id)
                    if individual_story:
                        filepath = self.download_media(individual_story, output_dir, f"story_{story_id}_")
                        if filepath:
                            downloaded_files.append(filepath)
                            file_ext = os.path.splitext(filepath)[1]
                            if file_ext == '.mp4':
                                self.log(f"🎬 Video hikaye indirildi: {os.path.basename(filepath)}")
                            else:
                                self.log(f"📷 Fotoğraf hikaye indirildi: {os.path.basename(filepath)}")
                    else:
                        self.log("❌ Bireysel hikaye verisi alınamadı")
                else:
                    # Tüm hikayeleri al (ana hikaye URL'si)
                    story_data = self.get_story_data(username)
                    if not story_data or not story_data.get('stories'):
                        self.log("❌ Hikaye verileri alınamadı veya hikaye bulunamadı")
                        self.log("💡 Not: Hikayeler gizli olabilir, süresi dolmuş olabilir veya giriş yapmanız gerekebilir")
                        return downloaded_files
                    
                    stories = story_data['stories']
                    self.log(f"📱 {len(stories)} hikaye medyası bulundu")
                    
                    # Her hikayeyi indir
                    for i, story_info in enumerate(stories):
                        prefix = f"story_{i+1:02d}_"
                        # Hikayeleri gerçek formatında indir
                        filepath = self.download_media(story_info, output_dir, prefix)
                        if filepath:
                            downloaded_files.append(filepath)
                            file_ext = os.path.splitext(filepath)[1]
                            if file_ext == '.mp4':
                                self.log(f"🎬 Video hikaye indirildi: {os.path.basename(filepath)}")
                            else:
                                self.log(f"📷 Fotoğraf hikaye indirildi: {os.path.basename(filepath)}")
                        
                        # Rate limiting
                        time.sleep(random.uniform(0.5, 1.5))
            
            elif content_type == 'hashtag':
                # Hashtag sayfasından içerik çıkarma
                hashtag_name = self.extract_hashtag_from_url(url)
                if not hashtag_name:
                    self.log("❌ Hashtag adı çıkarılamadı")
                    return downloaded_files
                
                self.log(f"🏷️ Hashtag: #{hashtag_name}")
                
                # Hashtag sayfasını ziyaret et ve içerik ara
                hashtag_data = self.get_hashtag_data(hashtag_name)
                if not hashtag_data:
                    self.log("❌ Hashtag içeriği bulunamadı")
                    self.log("💡 İpucu: Selenium modunu deneyebilirsiniz")
                    return downloaded_files
                
                # Bulunan medyaları indir
                media_list = hashtag_data.get('media', [])
                if not media_list:
                    self.log("❌ Hashtag'de medya bulunamadı")
                    return downloaded_files
                
                self.log(f"📱 {len(media_list)} medya bulundu")
                
                # Her medyayı indir
                for i, media_info in enumerate(media_list):
                    prefix = f"hashtag_{hashtag_name}_{i+1:02d}_"
                    filepath = self.download_media(media_info, output_dir, prefix)
                    if filepath:
                        downloaded_files.append(filepath)
                    
                    # Rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
            
            elif content_type == 'profile_posts':
                # Profil gönderileri sayfasından içerik çıkarma
                self.log("📝 Profil gönderileri sayfası tespit edildi")
                
                # Gönderiler sayfasını ziyaret et ve içerik ara
                posts_data = self.get_profile_posts_data(url)
                if not posts_data:
                    self.log("❌ Profil gönderileri içeriği bulunamadı")
                    self.log("💡 İpucu: Selenium modunu deneyebilirsiniz")
                    return downloaded_files
                
                # Bulunan medyaları indir
                media_list = posts_data.get('media', [])
                if not media_list:
                    self.log("❌ Profil gönderilerinde medya bulunamadı")
                    return downloaded_files
                
                self.log(f"📱 {len(media_list)} gönderi medyası bulundu")
                
                # Her medyayı indir
                for i, media_info in enumerate(media_list):
                    prefix = f"gönderi_{i}_"
                    filepath = self.download_media(media_info, output_dir, prefix)
                    if filepath:
                        downloaded_files.append(filepath)
                    
                    # Rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
            
            elif content_type == 'profile_reels':
                # Profil reels sayfasından içerik çıkarma
                self.log("🎬 Profil reels sayfası tespit edildi")
                
                # Reels sayfasını ziyaret et ve içerik ara
                reels_data = self.get_profile_reels_data(url)
                if not reels_data:
                    self.log("❌ Profil reels içeriği bulunamadı")
                    self.log("💡 İpucu: Selenium modunu deneyebilirsiniz")
                    return downloaded_files
                
                # Bulunan medyaları indir
                media_list = reels_data.get('media', [])
                if not media_list:
                    self.log("❌ Profil reels'lerinde medya bulunamadı")
                    return downloaded_files
                
                self.log(f"📱 {len(media_list)} reels medyası bulundu")
                
                # Her medyayı indir
                for i, media_info in enumerate(media_list):
                    prefix = f"reels_{i}_"
                    filepath = self.download_media(media_info, output_dir, prefix)
                    if filepath:
                        downloaded_files.append(filepath)
                    
                    # Rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
            
            elif content_type == 'profile':
                self.log("❌ Profil indirme henüz desteklenmiyor. Lütfen toplu indirici kullanın.")
            
            else:
                self.log("❌ Desteklenmeyen URL tipi")
            
        except Exception as e:
            self.log(f"❌ İndirme hatası: {str(e)}")
        
        return downloaded_files
    
    def get_profile_reels_data(self, url: str) -> Optional[Dict]:
        """Profil reels sayfasından medya verilerini alır"""
        try:
            self.log(f"🔍 Profil reels sayfası ziyaret ediliyor: {url}")
            
            # Profil reels sayfasını ziyaret et
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                self.log(f"❌ Profil reels sayfası erişim hatası: {response.status_code}")
                return None
            
            html_content = response.text
            self.log(f"📄 HTML içerik boyutu: {len(html_content)} karakter")
            
            # HTML içeriğinde temel kontroller
            if 'instagram' not in html_content.lower():
                self.log("⚠️ HTML içeriğinde Instagram verisi bulunamadı")
            if 'img' in html_content.lower():
                img_count = html_content.lower().count('<img')
                self.log(f"🖼️ HTML'de {img_count} adet img etiketi bulundu")
            
            # Profil reels sayfasından medya verilerini çıkar
            media_list = []
            
            # HTML img src URL'lerini ara
            img_patterns = [
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpg[^"]*?)"',
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpeg[^"]*?)"',
                r'<img[^>]+src="([^"]*fbcdn[^"]*\.jpg[^"]*?)"',
                r'srcset="[^"]*?(https://[^\s,"]*instagram[^\s,"]*\.jpg[^\s,"]*)',
            ]
            
            for pattern in img_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if match and 'profile' not in match.lower() and 'avatar' not in match.lower():
                        # URL'yi temizle
                        clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                        if clean_url.startswith('http'):
                            media_list.append({
                                'url': clean_url,
                                'is_video': False,
                                'width': 640,
                                'height': 640
                            })
            
            # Tekrarlanan URL'leri kaldır
            unique_media = []
            seen_urls = set()
            for media in media_list:
                if media['url'] not in seen_urls:
                    unique_media.append(media)
                    seen_urls.add(media['url'])
            
            self.log(f"📱 {len(unique_media)} benzersiz medya URL'si bulundu")
            
            # URL'leri çıkar
            media_urls = [media['url'] for media in unique_media[:20]]
            
            return {
                'media_urls': media_urls,
                'media': unique_media[:20]  # İlk 20 medyayı al
            }
            
        except Exception as e:
            self.log(f"❌ Profil reels veri çıkarma hatası: {str(e)}")
            return None
    
    def extract_hashtag_from_url(self, url: str) -> Optional[str]:
        """Hashtag URL'sinden hashtag adını çıkarır"""
        # https://www.instagram.com/explore/tags/komedi/ formatından 'komedi' çıkar
        pattern = r'/explore/tags/([A-Za-z0-9_]+)/?'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
    
    def get_hashtag_data(self, hashtag_name: str) -> Optional[Dict]:
        """Hashtag sayfasından medya verilerini alır"""
        try:
            # Önce session geçerliliğini test et
            test_response = self.session.get('https://www.instagram.com/accounts/edit/', timeout=30)
            if test_response.status_code == 200 and 'accounts/edit' in test_response.url:
                self.log("✅ Session geçerli - giriş yapılmış")
            else:
                self.log("⚠️ Session geçersiz - giriş yapılmamış, hashtag erişimi sınırlı olabilir")
            
            # İlk olarak normal hashtag sayfasını dene
            url = f"https://www.instagram.com/explore/tags/{hashtag_name}/"
            self.log(f"🔍 Hashtag sayfası ziyaret ediliyor: {url}")
            
            # Hashtag sayfasını ziyaret et
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                self.log(f"❌ Hashtag sayfası erişim hatası: {response.status_code}")
                return None
            
            # Eğer ana sayfaya yönlendirildiyse GraphQL API'yi dene
            if 'instagram.com/' == response.url or response.url.endswith('instagram.com/') or 'login' in response.url.lower():
                self.log("⚠️ Ana sayfaya yönlendirildi - GraphQL API deneniyor")
                graphql_result = self._get_hashtag_data_graphql(hashtag_name)
                if graphql_result:
                    return graphql_result
            
            # URL kontrolü - hashtag sayfasında olup olmadığını kontrol et
            if f'/explore/tags/{hashtag_name}' not in response.url:
                self.log(f"⚠️ Beklenmeyen URL: {response.url} - GraphQL API deneniyor")
                graphql_result = self._get_hashtag_data_graphql(hashtag_name)
                if graphql_result:
                    return graphql_result
            
            html_content = response.text
            self.log(f"📄 HTML içerik boyutu: {len(html_content)} karakter")
            
            # HTML içeriğinde temel kontroller
            if 'instagram' not in html_content.lower():
                self.log("⚠️ HTML içeriğinde Instagram verisi bulunamadı")
            if 'img' in html_content.lower():
                img_count = html_content.lower().count('<img')
                self.log(f"🖼️ HTML'de {img_count} adet img etiketi bulundu")
            if 'edge_hashtag_to_media' in html_content:
                self.log("✅ edge_hashtag_to_media verisi bulundu")
            if '_sharedData' in html_content:
                self.log("✅ _sharedData verisi bulundu")
            
            # Hashtag sayfasından medya verilerini çıkar
            patterns = [
                # Yeni Instagram formatları
                r'"edge_hashtag_to_media":\s*{"edges":\s*(\[.*?\])},',
                r'"hashtag":\s*{.*?"edge_hashtag_to_media":\s*{"edges":\s*(\[.*?\])},',
                r'window\._sharedData\s*=\s*({.*?});',
                # HTML img src URL'leri
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpg[^"]*?)"',
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpeg[^"]*?)"',
                r'<img[^>]+src="([^"]*instagram[^"]*\.png[^"]*?)"',
                r'<img[^>]+src="([^"]*fbcdn[^"]*\.jpg[^"]*?)"',
                # JSON içindeki medya URL'leri
                r'"display_url":\s*"([^"]+)"',
                r'"video_url":\s*"([^"]+)"',
                # Srcset URL'leri
                r'srcset="[^"]*?(https://[^\s,"]*instagram[^\s,"]*\.jpg[^\s,"]*)',
                # Href bağlantıları (/p/ formatında)
                r'href="(/p/[^"]+)"',
                # Shortcode'ları direkt ara
                r'/p/([A-Za-z0-9_-]{11})/',
                r'"shortcode":"([A-Za-z0-9_-]{11})"'
            ]
            
            media_list = []
            
            for i, pattern in enumerate(patterns):
                try:
                    self.log(f"🔍 Pattern {i+1} deneniyor...")
                    if i < 2:  # Edge patterns
                        matches = re.findall(pattern, html_content, re.DOTALL)
                        self.log(f"📊 Pattern {i+1} - {len(matches)} eşleşme bulundu")
                        for match in matches:
                            try:
                                edges_data = json.loads(match)
                                for edge in edges_data:
                                    if 'node' in edge:
                                        node = edge['node']
                                        media_info = self._extract_hashtag_media_info(node)
                                        if media_info:
                                            media_list.append(media_info)
                                            if len(media_list) >= 10:  # Maksimum 10 medya
                                                break
                                if media_list:
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                    
                    elif i == 2:  # _sharedData pattern
                        matches = re.findall(pattern, html_content, re.DOTALL)
                        self.log(f"📊 Pattern {i+1} (_sharedData) - {len(matches)} eşleşme bulundu")
                        for match in matches:
                            try:
                                data = json.loads(match)
                                if 'entry_data' in data and 'TagPage' in data['entry_data']:
                                    tag_page = data['entry_data']['TagPage'][0]
                                    if 'graphql' in tag_page and 'hashtag' in tag_page['graphql']:
                                        hashtag_data = tag_page['graphql']['hashtag']
                                        if 'edge_hashtag_to_media' in hashtag_data:
                                            edges = hashtag_data['edge_hashtag_to_media']['edges']
                                            for edge in edges:
                                                if 'node' in edge:
                                                    node = edge['node']
                                                    media_info = self._extract_hashtag_media_info(node)
                                                    if media_info:
                                                        media_list.append(media_info)
                                                        if len(media_list) >= 10:
                                                            break
                                if media_list:
                                    break
                            except (json.JSONDecodeError, KeyError):
                                continue
                    
                    elif i >= 3 and i <= 6:  # HTML img src patterns
                        matches = re.findall(pattern, html_content)
                        self.log(f"📊 Pattern {i+1} (HTML img) - {len(matches)} eşleşme bulundu")
                        for match in matches:
                            if isinstance(match, str) and ('instagram' in match or 'fbcdn' in match):
                                # URL'yi temizle
                                clean_url = match.replace('\\/', '/').replace('&amp;', '&')
                                media_info = {
                                    'id': f'img_{len(media_list)}',
                                    'shortcode': f"hashtag_{len(media_list)+1}",
                                    'typename': 'GraphImage',
                                    'is_video': False,
                                    'url': clean_url,
                                    'thumbnail_url': clean_url,
                                    'caption': ''
                                }
                                media_list.append(media_info)
                                self.log(f"📷 HTML'den medya bulundu: {clean_url[:50]}...")
                                if len(media_list) >= 10:
                                    break
                    
                    elif i == len(patterns) - 1:  # Href pattern (son pattern)
                        matches = re.findall(pattern, html_content)
                        self.log(f"📊 Pattern {i+1} (href) - {len(matches)} eşleşme bulundu")
                        for match in matches:
                            if isinstance(match, str) and match.startswith('/p/'):
                                # Href'i tam URL'ye dönüştür
                                full_url = f"https://www.instagram.com{match}"
                                media_info = {
                                    'url': full_url,
                                    'type': 'post',
                                    'shortcode': match.split('/')[-2] if len(match.split('/')) > 2 else f"hashtag_{len(media_list)+1}"
                                }
                                media_list.append(media_info)
                                self.log(f"🔗 Href bulundu: {full_url}")
                                if len(media_list) >= 10:
                                    break
                    
                    elif i in [len(patterns) - 3, len(patterns) - 2]:  # Shortcode patterns
                        matches = re.findall(pattern, html_content)
                        self.log(f"📊 Pattern {i+1} (shortcode) - {len(matches)} eşleşme bulundu")
                        for shortcode in matches:
                            if isinstance(shortcode, str) and len(shortcode) == 11:
                                # Shortcode'dan post verilerini al
                                try:
                                    post_data = self.get_post_data(shortcode)
                                    if post_data:
                                        media_urls = self.extract_media_urls(post_data)
                                        if media_urls:
                                            for media in media_urls:
                                                media_info = {
                                                    'id': media.get('id', shortcode),
                                                    'shortcode': shortcode,
                                                    'typename': media.get('typename', 'GraphImage'),
                                                    'is_video': media.get('is_video', False),
                                                    'url': media.get('url'),
                                                    'thumbnail_url': media.get('thumbnail_url'),
                                                    'caption': media.get('caption', '')
                                                }
                                                media_list.append(media_info)
                                                self.log(f"📷 Shortcode'dan medya bulundu: {shortcode}")
                                                if len(media_list) >= 10:
                                                    break
                                            if len(media_list) >= 10:
                                                break
                                except Exception as e:
                                    self.log(f"⚠️ Shortcode işleme hatası {shortcode}: {str(e)[:30]}...")
                                    continue
                    
                    else:  # JSON ve srcset URL patterns
                        matches = re.findall(pattern, html_content)
                        self.log(f"📊 Pattern {i+1} (JSON/srcset) - {len(matches)} eşleşme bulundu")
                        for match in matches:
                            if isinstance(match, str) and ('instagram' in match or 'cdninstagram' in match or 'fbcdn' in match):
                                clean_url = match.replace('\\/', '/').replace('&amp;', '&')
                                media_info = {
                                    'id': f'json_{len(media_list)}',
                                    'shortcode': f"hashtag_{len(media_list)+1}",
                                    'typename': 'GraphImage' if any(ext in match for ext in ['.jpg', '.jpeg', '.png']) else 'GraphVideo',
                                    'is_video': not any(ext in match for ext in ['.jpg', '.jpeg', '.png']),
                                    'url': clean_url,
                                    'thumbnail_url': clean_url,
                                    'caption': ''
                                }
                                media_list.append(media_info)
                                if len(media_list) >= 10:
                                    break
                    
                    if media_list:
                        break
                        
                except Exception as e:
                    self.log(f"⚠️ Pattern {i+1} işleme hatası: {str(e)[:50]}...")
                    continue
            
            if media_list:
                self.log(f"✅ {len(media_list)} hashtag medyası bulundu")
                return {'media': media_list}
            else:
                self.log("❌ Normal yöntemlerle hashtag medyası bulunamadı - GraphQL API deneniyor")
                graphql_result = self._get_hashtag_data_graphql(hashtag_name)
                if graphql_result:
                    return graphql_result
                else:
                    self.log("❌ GraphQL API ile de hashtag medyası bulunamadı")
                    return None
                
        except Exception as e:
            self.log(f"❌ Hashtag veri alma hatası: {str(e)}")
            return None
    
    def _extract_hashtag_media_info(self, node: Dict) -> Optional[Dict]:
        """Hashtag node'undan medya bilgilerini çıkarır"""
        try:
            # Shortcode'u al - bu önemli çünkü post URL'si oluşturmak için gerekli
            shortcode = node.get('shortcode', '')
            if not shortcode:
                self.log("⚠️ Shortcode bulunamadı, node atlanıyor")
                return None
            
            media_info = {
                'id': node.get('id', shortcode),
                'shortcode': shortcode,
                'typename': node.get('__typename', 'GraphImage'),
                'is_video': node.get('is_video', False),
                'url': None,
                'thumbnail_url': None,
                'caption': ''
            }
            
            # Medya URL'sini al - farklı formatları dene
            if node.get('is_video', False):
                # Video için URL
                video_url = (
                    node.get('video_url') or
                    node.get('video_versions', [{}])[0].get('url') if node.get('video_versions') else None
                )
                media_info['url'] = video_url
                media_info['typename'] = 'GraphVideo'
            else:
                # Fotoğraf için URL
                image_url = (
                    node.get('display_url') or
                    node.get('image_versions2', {}).get('candidates', [{}])[0].get('url') if node.get('image_versions2') else None
                )
                media_info['url'] = image_url
                media_info['typename'] = 'GraphImage'
            
            # Thumbnail URL
            media_info['thumbnail_url'] = (
                node.get('thumbnail_src') or
                node.get('display_url') or
                node.get('image_versions2', {}).get('candidates', [{}])[0].get('url') if node.get('image_versions2') else None
            )
            
            # Caption (açıklama) al
            caption = ''
            if 'caption' in node and node['caption']:
                if isinstance(node['caption'], dict):
                    caption = node['caption'].get('text', '')
                else:
                    caption = str(node['caption'])
            elif 'edge_media_to_caption' in node:
                edges = node['edge_media_to_caption']['edges']
                if edges:
                    caption = edges[0]['node']['text']
            
            media_info['caption'] = caption
            
            # URL kontrolü - eğer URL yoksa shortcode'dan post URL'si oluştur
            if not media_info['url']:
                self.log(f"⚠️ Direkt medya URL'si bulunamadı, post URL'si oluşturuluyor: {shortcode}")
                # Post URL'sini oluştur ve post verilerini al
                post_url = f"https://www.instagram.com/p/{shortcode}/"
                post_data = self.get_post_data(shortcode)
                if post_data:
                    # Post verilerinden medya URL'lerini çıkar
                    media_urls = self.extract_media_urls(post_data)
                    if media_urls:
                        # İlk medyayı al
                        first_media = media_urls[0]
                        media_info['url'] = first_media.get('url')
                        media_info['is_video'] = first_media.get('is_video', False)
                        media_info['typename'] = first_media.get('typename', 'GraphImage')
                        if not media_info['caption']:
                            media_info['caption'] = first_media.get('caption', '')
                        self.log(f"✅ Post verilerinden URL alındı: {shortcode}")
            
            # Son kontrol
            if not media_info['url']:
                self.log(f"❌ Medya URL'si bulunamadı: {shortcode}")
                return None
            
            return media_info
            
        except Exception as e:
            self.log(f"⚠️ Hashtag medya bilgisi çıkarma hatası: {str(e)}")
            return None
    
    def get_profile_posts_data(self, url: str) -> Optional[Dict]:
        """Profil gönderileri sayfasından medya verilerini alır"""
        try:
            self.log(f"🔍 Profil gönderileri sayfası ziyaret ediliyor: {url}")
            
            # Profil gönderileri sayfasını ziyaret et
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                self.log(f"❌ Profil gönderileri sayfası erişim hatası: {response.status_code}")
                return None
            
            html_content = response.text
            self.log(f"📄 HTML içerik boyutu: {len(html_content)} karakter")
            
            # HTML içeriğinde temel kontroller
            if 'instagram' not in html_content.lower():
                self.log("⚠️ HTML içeriğinde Instagram verisi bulunamadı")
            if 'img' in html_content.lower():
                img_count = html_content.lower().count('<img')
                self.log(f"🖼️ HTML'de {img_count} adet img etiketi bulundu")
            
            # Profil gönderileri sayfasından medya verilerini çıkar
            media_list = []
            
            # HTML img src URL'lerini ara
            img_patterns = [
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpg[^"]*?)"',
                r'<img[^>]+src="([^"]*instagram[^"]*\.jpeg[^"]*?)"',
                r'<img[^>]+src="([^"]*fbcdn[^"]*\.jpg[^"]*?)"',
                r'srcset="[^"]*?(https://[^\s,"]*instagram[^\s,"]*\.jpg[^\s,"]*)',
            ]
            
            for pattern in img_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if match and 'profile' not in match.lower() and 'avatar' not in match.lower():
                        # URL'yi temizle
                        clean_url = match.replace('\\u0026', '&').replace('\\/', '/')
                        if clean_url.startswith('http'):
                            media_list.append({
                                'url': clean_url,
                                'is_video': False,
                                'width': 640,
                                'height': 640
                            })
            
            # Tekrarlanan URL'leri kaldır
            unique_media = []
            seen_urls = set()
            for media in media_list:
                if media['url'] not in seen_urls:
                    unique_media.append(media)
                    seen_urls.add(media['url'])
            
            self.log(f"📱 {len(unique_media)} benzersiz medya URL'si bulundu")
            
            # URL'leri çıkar
            media_urls = [media['url'] for media in unique_media[:20]]
            
            return {
                'media_urls': media_urls,
                'media': unique_media[:20]  # İlk 20 medyayı al
            }
            
        except Exception as e:
            self.log(f"❌ Profil gönderileri veri çıkarma hatası: {str(e)}")
            return None
    
    def get_profile_info(self, username: str) -> Optional[Dict]:
        """Profil bilgilerini alır"""
        try:
            url = f"https://www.instagram.com/{username}/"
            
            # Daha detaylı headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.log(f"❌ Profil erişim hatası: {response.status_code}")
                return None
            
            html_content = response.text
            
            # Farklı JSON pattern'lerini dene
            patterns = [
                r'window\._sharedData = ({.*?});',
                r'"ProfilePage":\[({.*?})\]',
                r'"user":({.*?"username":"' + re.escape(username) + r'".*?})',
                r'"props":{"pageProps":{"user":({.*?})'
            ]
            
            profile_data = None
            
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, html_content, re.DOTALL)
                    for match in matches:
                        try:
                            if isinstance(match, str):
                                data = json.loads(match)
                            else:
                                data = match
                            
                            # Farklı veri yapılarını kontrol et
                            user_data = None
                            
                            # _sharedData yapısı
                            if 'entry_data' in data and 'ProfilePage' in data['entry_data']:
                                if data['entry_data']['ProfilePage']:
                                    page_data = data['entry_data']['ProfilePage'][0]
                                    if 'graphql' in page_data and 'user' in page_data['graphql']:
                                        user_data = page_data['graphql']['user']
                            
                            # Direkt user verisi
                            elif 'username' in data:
                                user_data = data
                            
                            # Nested user verisi
                            elif 'user' in data:
                                user_data = data['user']
                            
                            if user_data and user_data.get('username') == username:
                                profile_data = {
                                    'id': user_data.get('id', ''),
                                    'username': user_data.get('username', ''),
                                    'full_name': user_data.get('full_name', ''),
                                    'biography': user_data.get('biography', ''),
                                    'followers_count': user_data.get('edge_followed_by', {}).get('count', 0),
                                    'following_count': user_data.get('edge_follow', {}).get('count', 0),
                                    'posts_count': user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                                    'is_private': user_data.get('is_private', False),
                                    'profile_pic_url': user_data.get('profile_pic_url_hd', user_data.get('profile_pic_url', ''))
                                }
                                break
                        except (json.JSONDecodeError, KeyError, TypeError):
                            continue
                    
                    if profile_data:
                        break
                        
                except Exception:
                    continue
            
            if profile_data:
                self.log(f"✅ {username} profil bilgileri alındı")
                return profile_data
            
            # Basit HTML parsing ile temel bilgileri al
            self.log("⚠️ JSON parsing başarısız, HTML parsing deneniyor...")
            
            # Basit profil bilgileri
            basic_profile = {
                'id': '',
                'username': username,
                'full_name': '',
                'biography': '',
                'followers_count': 0,
                'following_count': 0,
                'posts_count': 0,
                'is_private': False,  # Varsayılan olarak açık kabul et
                'profile_pic_url': ''
            }
            
            # Gizlilik kontrolü - daha spesifik pattern'ler
            private_indicators = [
                'This account is private',
                'Bu hesap gizli',
                '"is_private":true',
                'private":true',
                'Follow to see their photos and videos',
                'Fotoğraf ve videolarını görmek için takip et'
            ]
            
            for indicator in private_indicators:
                if indicator in html_content:
                    basic_profile['is_private'] = True
                    break
            
            # Meta tag'lerden bilgi çıkar
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            if title_match:
                title = title_match.group(1)
                if '@' in title:
                    basic_profile['full_name'] = title.split('@')[0].strip()
            
            # Profil fotoğrafı URL'si
            pic_match = re.search(r'"profile_pic_url":"([^"]+)"', html_content)
            if pic_match:
                basic_profile['profile_pic_url'] = pic_match.group(1).replace('\\/', '/')
            
            self.log(f"✅ {username} temel profil bilgileri alındı (HTML parsing)")
            return basic_profile
            
        except Exception as e:
            self.log(f"❌ Profil bilgi alma hatası: {str(e)}")
            return None

if __name__ == "__main__":
    # Test için
    downloader = InstagramHttpDownloader()
    
    # Test URL'leri
    test_urls = [
        "https://www.instagram.com/p/DKU61axo7tx/",  # Fotoğraf
        "https://www.instagram.com/reel/DKRXbXhI6la/",  # Reels
        "https://www.instagram.com/stories/aslihanaltay24/"  # Hikaye
    ]
    
    for url in test_urls:
        print(f"\nTest URL: {url}")
        files = downloader.download_from_url(url, "test_output")
        print(f"İndirilen dosyalar: {files}")