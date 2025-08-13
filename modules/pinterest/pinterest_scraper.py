import requests
import json
import re
import os
import sys
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random

# Ana dizini sys.path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class PinterestScraper:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.session = requests.Session()
        self.driver = None
        self.pinterest_cookies = None
        
        # User-Agent ayarla
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Cookie'leri yükle
        self.load_cookies()
    
    def log(self, message):
        """Log mesajı yazdır"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def load_cookies(self):
        """Kaydedilmiş cookie'leri yükle"""
        try:
            cookie_file = os.path.join("cookie", "pinterest_cookies.json")
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self.pinterest_cookies = json.loads(content)
                        self.log(f"Kaydedilmiş {len(self.pinterest_cookies)} adet cookie yüklendi")
                        
                        # Cookie'leri session'a ekle
                        for cookie in self.pinterest_cookies:
                            self.session.cookies.set(cookie['name'], cookie['value'])
                    else:
                        self.log("Cookie dosyası boş")
            else:
                self.log("Kaydedilmiş cookie dosyası bulunamadı")
        except Exception as e:
            self.log(f"Cookie yükleme hatası: {str(e)}")
    
    def save_cookies(self, cookies):
        """Cookie'leri kaydet"""
        try:
            # Cookie klasörünü oluştur
            cookie_dir = "cookie"
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
            
            cookie_file = os.path.join(cookie_dir, "pinterest_cookies.json")
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            self.pinterest_cookies = cookies
            self.log(f"{len(cookies)} adet cookie kaydedildi")
        except Exception as e:
            self.log(f"Cookie kaydetme hatası: {str(e)}")
    
    def extract_pin_id(self, url):
        """Pinterest URL'sinden pin ID'sini çıkar"""
        try:
            # Pinterest pin URL formatları:
            # https://www.pinterest.com/pin/123456789/
            # https://pin.it/abc123
            
            if 'pin.it' in url:
                # Kısa URL'yi genişlet
                response = self.session.head(url, allow_redirects=True)
                url = response.url
            
            # Pin ID'sini çıkar
            pin_match = re.search(r'/pin/([0-9]+)/', url)
            if pin_match:
                return pin_match.group(1)
            
            return None
        except Exception as e:
            self.log(f"Pin ID çıkarma hatası: {str(e)}")
            return None
    
    def get_pin_data(self, pin_url):
        """Pinterest pin verilerini al"""
        try:
            pin_id = self.extract_pin_id(pin_url)
            if not pin_id:
                self.log("❌ Geçersiz Pinterest URL")
                return None
            
            self.log(f"📌 Pin ID: {pin_id}")
            
            # Pinterest API endpoint'i
            api_url = f"https://www.pinterest.com/resource/PinResource/get/?source_url=%2Fpin%2F{pin_id}%2F&data=%7B%22options%22%3A%7B%22field_set_key%22%3A%22detailed%22%2C%22id%22%3A%22{pin_id}%22%7D%2C%22context%22%3A%7B%7D%7D"
            
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'resource_response' in data and 'data' in data['resource_response']:
                    pin_data = data['resource_response']['data']
                    
                    # Pin bilgilerini çıkar
                    result = {
                        'id': pin_data.get('id'),
                        'title': pin_data.get('title', ''),
                        'description': pin_data.get('description', ''),
                        'images': [],
                        'videos': [],
                        'board_name': pin_data.get('board', {}).get('name', ''),
                        'pinner_name': pin_data.get('pinner', {}).get('username', ''),
                        'created_at': pin_data.get('created_at', '')
                    }
                    
                    # Görsel/video URL'lerini çıkar
                    if 'images' in pin_data:
                        images = pin_data['images']
                        if 'orig' in images:
                            result['images'].append(images['orig']['url'])
                        elif '736x' in images:
                            result['images'].append(images['736x']['url'])
                    
                    # Video varsa
                    if 'videos' in pin_data and pin_data['videos']:
                        video_list = pin_data['videos'].get('video_list', {})
                        if 'V_720P' in video_list:
                            result['videos'].append(video_list['V_720P']['url'])
                        elif 'V_HLSV4' in video_list:
                            result['videos'].append(video_list['V_HLSV4']['url'])
                    
                    return result
                else:
                    self.log("❌ Pin verisi bulunamadı")
                    return None
            else:
                self.log(f"❌ API isteği başarısız: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ Pin verisi alma hatası: {str(e)}")
            return None
    
    def download_media(self, url, filename, output_dir="output"):
        """Medya dosyasını indir"""
        try:
            # Çıktı klasörünü oluştur
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            filepath = os.path.join(output_dir, filename)
            
            self.log(f"📥 İndiriliyor: {filename}")
            
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.log(f"✅ İndirildi: {filename}")
            return filepath
            
        except Exception as e:
            self.log(f"❌ İndirme hatası: {str(e)}")
            return None
    
    def close(self):
        """Kaynakları temizle"""
        if self.driver:
            self.driver.quit()
        self.session.close()