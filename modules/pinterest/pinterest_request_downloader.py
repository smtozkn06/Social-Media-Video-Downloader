'''
Pinterest Medya İndirici - Video, Resim ve GIF Destekli
Geliştirici: Samet - Tüm medya türleri için optimize edilmiş
'''
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
import re
from datetime import datetime

class PinterestRequestDownloader:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        
        # User-Agent ayarla
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def log(self, message):
        """Log mesajı gönder"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def download_file(self, media_url, file_path):
        """Verilen URL'den dosyayı indirir"""
        try:
            response = self.session.get(media_url, stream=True)
            response.raise_for_status()
            
            file_size = int(response.headers.get('Content-Length', 0))
            
            # Dosya boyutunu log'a yazdır
            if file_size > 0:
                size_mb = file_size / (1024 * 1024)
                self.log(f"📦 Dosya boyutu: {size_mb:.2f} MB")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as file:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # İlerleme durumunu log'a yazdır (her 1MB'da bir)
                        if file_size > 0 and downloaded % (1024 * 1024) == 0:
                            progress = (downloaded / file_size) * 100
                            self.log(f"📥 İndirme ilerlemesi: {progress:.1f}%")
            
            self.log(f"✅ Dosya başarıyla indirildi: {os.path.basename(file_path)}")
            return file_path
            
        except Exception as e:
            self.log(f"❌ Dosya indirme hatası: {str(e)}")
            return None

    def validate_url(self, url):
        """URL'nin geçerliliğini kontrol et"""
        if not url:
            return False
        return "pinterest.com/pin/" in url or "https://pin.it/" in url
    
    def expand_short_url(self, url):
        """Kısa pin.it URL'sini genişlet"""
        try:
            if "https://pin.it/" in url:
                self.log("🔄 Kısa link genişletiliyor...")
                response = self.session.get(url)
                if response.status_code != 200:
                    self.log("❌ URL geçersiz veya erişilemiyor.")
                    return None
                
                soup = BeautifulSoup(response.content, "html.parser")
                alternate_link = soup.find("link", rel="alternate")
                if alternate_link and alternate_link.get("href"):
                    url_match = re.search('url=(.*?)&', alternate_link["href"])
                    if url_match:
                        expanded_url = url_match.group(1)
                        self.log(f"✅ URL genişletildi: {expanded_url}")
                        return expanded_url
                
                self.log("❌ URL genişletme başarısız")
                return None
            
            return url
        except Exception as e:
            self.log(f"❌ URL genişletme hatası: {str(e)}")
            return None
    
    def get_page_content(self, url):
        """Sayfa içeriğini al"""
        try:
            self.log("📡 Sayfa içeriği alınıyor...")
            response = self.session.get(url)
            if response.status_code != 200:
                self.log(f"❌ Sayfa erişim hatası: HTTP {response.status_code}")
                return None
            
            self.log("✅ Sayfa içeriği başarıyla alındı")
            return BeautifulSoup(response.content, "html.parser")
            
        except Exception as e:
            self.log(f"❌ Sayfa içeriği alma hatası: {str(e)}")
            return None

    def find_video_url(self, soup):
        """Sayfada video URL'si bul"""
        self.log("🔍 Video içeriği aranıyor...")
        video_url = None
        
        # Yöntem 1: Orijinal seçiciyi dene
        video_element = soup.find("video", class_="hwa kVc MIw L4E")
        if video_element and video_element.get('src'):
            video_url = video_element['src']
            self.log("✅ Yöntem 1: Orijinal seçici ile video bulundu")
            return video_url
        
        # Yöntem 2: Herhangi bir video elementi bul
        video_element = soup.find("video")
        if video_element and video_element.get('src'):
            video_url = video_element['src']
            self.log("✅ Yöntem 2: Video elementi bulundu")
            return video_url
        
        # Yöntem 3: Farklı sınıf desenlerini dene
        video_selectors = [
            "video[class*='hwa']",
            "video[class*='kVc']", 
            "video[class*='MIw']",
            "video[class*='L4E']"
        ]
        
        for selector in video_selectors:
            video_element = soup.select_one(selector)
            if video_element and video_element.get('src'):
                video_url = video_element['src']
                self.log(f"✅ Yöntem 3: {selector} seçici ile video bulundu")
                return video_url
        
        # Yöntem 4: Script etiketlerinde video URL'leri ara
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                # .m3u8 veya .mp4 URL'lerini ara
                video_matches = re.findall(r'https?://[^"\s]+\.(?:m3u8|mp4)', script.string)
                if video_matches:
                    video_url = video_matches[0]
                    self.log("✅ Yöntem 4: Script etiketinde video URL'si bulundu")
                    return video_url
        
        # Yöntem 5: Veri özniteliklerini ara
        video_element = soup.find(attrs={"data-src": True})
        if video_element:
            video_url = video_element['data-src']
            self.log("✅ Yöntem 5: Data-src özniteliğinde video bulundu")
            return video_url
        
        # Hata ayıklama bilgisi
        video_count = len(soup.find_all("video"))
        self.log(f"🔧 Hata ayıklama: Toplam {video_count} video elementi bulundu")
        
        return None

    def find_image_url(self, soup):
        """Sayfada resim/GIF URL'si bul"""
        self.log("🔍 Resim ve GIF içeriği aranıyor...")
        
        # Resim elementlerini ara
        img_elements = soup.find_all('img')
        image_url = None
        media_type = "resim"
        
        # Ana pin resmi/GIF'ini bulmaya çalış
        for img in img_elements:
            src = img.get('src') or img.get('data-src')
            if src and ('pinimg.com' in src or 'pinterest' in src):
                # Küçük resimleri atla (küçük resimler, simgeler)
                if any(size in src for size in ['75x75', '170x', '236x', '345x']):
                    continue
                # Büyük resimleri veya orijinalleri ara
                if any(size in src for size in ['564x', '736x', '1200x', 'originals']) or '.gif' in src:
                    image_url = src
                    if '.gif' in src:
                        media_type = "GIF"
                    break
        
        # Hala resim bulunamadıysa, mevcut en büyüğünü dene
        if not image_url and img_elements:
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                if src and 'pinimg.com' in src:
                    image_url = src
                    if '.gif' in src:
                        media_type = "GIF"
                    break
        
        # Script etiketlerinde GIF URL'leri de kontrol et
        if not image_url:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    # .gif URL'lerini ara
                    gif_urls = re.findall(r'https://[^"\s]*\.gif', script.string)
                    if gif_urls:
                        image_url = gif_urls[0]
                        media_type = "GIF"
                        break
        
        if image_url:
            self.log(f"✅ {media_type} bulundu! URL: {image_url}")
            return image_url, media_type
        
        return None, None
    
    def get_file_extension(self, url, media_type):
        """URL'den dosya uzantısını belirle"""
        if '.jpg' in url or '.jpeg' in url:
            return '.jpg'
        elif '.png' in url:
            return '.png'
        elif '.gif' in url:
            return '.gif'
        elif '.webp' in url:
            return '.webp'
        elif '.mp4' in url:
            return '.mp4'
        else:
            return '.jpg'  # varsayılan
    
    def download_pin(self, pin_url, output_dir="output"):
        """Pinterest pin'ini indir"""
        try:
            # URL doğrulama
            if not self.validate_url(pin_url):
                self.log("❌ Geçersiz Pinterest URL")
                return []
            
            # Kısa URL'yi genişlet
            expanded_url = self.expand_short_url(pin_url)
            if not expanded_url:
                return []
            
            # Sayfa içeriğini al
            soup = self.get_page_content(expanded_url)
            if not soup:
                return []
            
            downloaded_files = []
            
            # Video arama
            video_url = self.find_video_url(soup)
            if video_url:
                self.log(f"✅ Video bulundu! URL: {video_url}")
                
                # m3u8 dosyası ise 720p URL'sine dönüştür
                if '.m3u8' in video_url:
                    converted_url = video_url.replace("hls", "720p").replace("m3u8", "mp4")
                    file_extension = ".mp4"
                else:
                    converted_url = video_url
                    file_extension = ".mp4"
                
                # Dosya adı oluştur
                timestamp = datetime.now().strftime("%d_%m_%H_%M_%S_")
                filename = f"{timestamp}video{file_extension}"
                file_path = os.path.join(output_dir, filename)
                
                self.log("📥 Video indiriliyor...")
                downloaded_file = self.download_file(converted_url, file_path)
                if downloaded_file:
                    downloaded_files.append(downloaded_file)
            
            else:
                # Video bulunamadıysa resim/GIF ara
                image_url, media_type = self.find_image_url(soup)
                if image_url:
                    file_extension = self.get_file_extension(image_url, media_type)
                    
                    # Dosya adı oluştur
                    timestamp = datetime.now().strftime("%d_%m_%H_%M_%S_")
                    filename = f"{timestamp}{media_type.lower()}{file_extension}"
                    file_path = os.path.join(output_dir, filename)
                    
                    self.log(f"📥 {media_type} indiriliyor...")
                    downloaded_file = self.download_file(image_url, file_path)
                    if downloaded_file:
                        downloaded_files.append(downloaded_file)
                
                else:
                    self.log("❌ Bu sayfada herhangi bir medya (video, resim veya GIF) bulunamadı.")
                    self.log("\n💡 Olası nedenler:")
                    self.log("• Pinterest HTML yapısını değiştirmiş")
                    self.log("• Sayfa içeriği yüklemek için JavaScript gerektiriyor")
                    self.log("• URL geçersiz veya pin silinmiş")
                    self.log("• Pin sadece metin içeriyor olabilir")
                    
                    # Hata ayıklama bilgisi
                    video_count = len(soup.find_all('video'))
                    img_count = len(soup.find_all('img'))
                    title = soup.title.string if soup.title else 'Başlık bulunamadı'
                    
                    self.log(f"🔧 Hata ayıklama:")
                    self.log(f"   • Bulunan videolar: {video_count}")
                    self.log(f"   • Bulunan resimler: {img_count}")
                    self.log(f"   • Sayfa başlığı: {title}")
            
            return downloaded_files
            
        except Exception as e:
            self.log(f"❌ Pin indirme hatası: {str(e)}")
            return []
    
    def search_pins(self, keyword, max_pins=50):
        """Pinterest'te kelime ile arama yap ve pin URL'lerini döndür"""
        try:
            self.log(f"🔍 '{keyword}' kelimesi ile Pinterest'te arama yapılıyor...")
            
            # Pinterest arama URL'si oluştur
            search_url = f"https://www.pinterest.com/search/pins/?q={keyword.replace(' ', '%20')}"
            
            # Arama sayfasını al
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Pin URL'lerini bul
            pin_urls = []
            
            # Pinterest pin linklerini ara
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '/pin/' in href and href.startswith('/'):
                    # Tam URL'ye dönüştür
                    full_url = f"https://www.pinterest.com{href}"
                    if full_url not in pin_urls:
                        pin_urls.append(full_url)
                        if len(pin_urls) >= max_pins:
                            break
            
            # Script etiketlerinde de pin URL'leri ara
            if len(pin_urls) < max_pins:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        # Pin URL pattern'lerini ara
                        import re
                        pin_matches = re.findall(r'https://www\.pinterest\.com/pin/[0-9]+', script.string)
                        for match in pin_matches:
                            if match not in pin_urls:
                                pin_urls.append(match)
                                if len(pin_urls) >= max_pins:
                                    break
                    if len(pin_urls) >= max_pins:
                        break
            
            self.log(f"✅ {len(pin_urls)} pin URL'si bulundu")
            return pin_urls[:max_pins]
            
        except Exception as e:
            self.log(f"❌ Arama hatası: {str(e)}")
            return []
    
    def close(self):
        """Kaynakları temizle"""
        if hasattr(self, 'session'):
            self.session.close()


# Eski script formatı için uyumluluk (eğer doğrudan çalıştırılırsa)
if __name__ == "__main__":
    print("🎯 Pinterest Medya İndirici - Video, Resim ve GIF Desteği")
    print("📌 Pinterest sayfa URL'sini girin: ", end="")
    pin_url = input()
    
    downloader = PinterestRequestDownloader()
    downloaded_files = downloader.download_pin(pin_url, "output")
    
    if downloaded_files:
        print(f"\n✅ {len(downloaded_files)} dosya başarıyla indirildi:")
        for file_path in downloaded_files:
            print(f"  • {os.path.basename(file_path)}")
    else:
        print("\n❌ Hiçbir dosya indirilemedi")
