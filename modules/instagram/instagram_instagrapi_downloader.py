import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, FeedNotModified, MediaNotFound
import random

class InstagramInstagrapiDownloader:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.client = Client()
        self.is_logged_in = False
        
        # Dosya sayaçları - sıralı isimlendirme için
        self.photo_counter = 0
        self.video_counter = 0
        
        # Session ayarları
        self.setup_client()
    
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
    
    def setup_client(self):
        """Instagrapi client'ını ayarlar"""
        try:
            # Client ayarları
            self.client.delay_range = [1, 3]  # İstekler arası bekleme süresi
            self.client.request_timeout = 30
            
            # User agent ayarla
            self.client.set_user_agent("Instagram 219.0.0.12.117 Android")
            
            self.log("📱 Instagrapi client ayarlandı")
            
        except Exception as e:
            self.log(f"⚠️ Client ayarlama hatası: {str(e)}")
    
    def login_with_credentials(self, username: str, password: str) -> bool:
        """Kullanıcı adı ve şifre ile giriş yapar"""
        try:
            self.log(f"🔐 Instagram'a giriş yapılıyor: {username}")
            
            # Giriş yap
            self.client.login(username, password)
            self.is_logged_in = True
            
            self.log("✅ Instagram'a başarıyla giriş yapıldı")
            return True
            
        except LoginRequired as e:
            self.log(f"❌ Giriş gerekli: {str(e)}")
            return False
        except ChallengeRequired as e:
            self.log(f"❌ Challenge gerekli: {str(e)}")
            return False
        except Exception as e:
            self.log(f"❌ Giriş hatası: {str(e)}")
            return False
    
    def load_session(self, session_file: str) -> bool:
        """Kaydedilmiş session'ı yükler"""
        try:
            if os.path.exists(session_file):
                self.client.load_settings(session_file)
                self.client.login(self.client.username, self.client.password)
                self.is_logged_in = True
                self.log("✅ Kaydedilmiş session yüklendi")
                return True
            else:
                self.log("⚠️ Session dosyası bulunamadı")
                return False
        except Exception as e:
            self.log(f"⚠️ Session yükleme hatası: {str(e)}")
            return False
    
    def save_session(self, session_file: str):
        """Mevcut session'ı kaydeder"""
        try:
            if self.is_logged_in:
                self.client.dump_settings(session_file)
                self.log("💾 Session kaydedildi")
        except Exception as e:
            self.log(f"⚠️ Session kaydetme hatası: {str(e)}")
    
    def get_hashtag_medias(self, hashtag: str, amount: int = 50) -> List[Dict]:
        """Hashtag'den medyaları alır"""
        try:
            self.log(f"🔍 Hashtag medyaları alınıyor: #{hashtag}")
            
            # Hashtag bilgisini al
            hashtag_info = self.client.hashtag_info(hashtag)
            self.log(f"📊 Hashtag bilgisi: {hashtag_info.name} - {hashtag_info.media_count} medya")
            
            # Son medyaları al
            medias = self.client.hashtag_medias_recent(hashtag, amount=amount)
            
            if not medias:
                self.log(f"⚠️ #{hashtag} hashtag'inde medya bulunamadı")
                return []
            
            self.log(f"✅ {len(medias)} adet medya bulundu")
            
            # Medya bilgilerini düzenle
            media_list = []
            for media in medias:
                media_info = {
                    'id': media.id,
                    'pk': media.pk,
                    'code': media.code,
                    'media_type': media.media_type,  # 1: photo, 2: video, 8: album
                    'caption': media.caption_text if media.caption_text else '',
                    'like_count': media.like_count,
                    'comment_count': media.comment_count,
                    'taken_at': media.taken_at,
                    'user': {
                        'username': media.user.username,
                        'full_name': media.user.full_name,
                        'pk': media.user.pk
                    },
                    'thumbnail_url': media.thumbnail_url,
                    'video_url': media.video_url if hasattr(media, 'video_url') else None,
                    'resources': []
                }
                
                # Album ise tüm medyaları ekle
                if media.media_type == 8 and hasattr(media, 'resources'):
                    for resource in media.resources:
                        media_info['resources'].append({
                            'pk': resource.pk,
                            'media_type': resource.media_type,
                            'thumbnail_url': resource.thumbnail_url,
                            'video_url': resource.video_url if hasattr(resource, 'video_url') else None
                        })
                
                media_list.append(media_info)
            
            return media_list
            
        except Exception as e:
            self.log(f"❌ Hashtag medya alma hatası: {str(e)}")
            return []
    
    def get_hashtag_medias_top(self, hashtag: str, amount: int = 20) -> List[Dict]:
        """Hashtag'den en popüler medyaları alır"""
        try:
            self.log(f"🔥 Hashtag top medyaları alınıyor: #{hashtag}")
            
            # En popüler medyaları al
            medias = self.client.hashtag_medias_top(hashtag, amount=amount)
            
            if not medias:
                self.log(f"⚠️ #{hashtag} hashtag'inde top medya bulunamadı")
                return []
            
            self.log(f"✅ {len(medias)} adet top medya bulundu")
            
            # Medya bilgilerini düzenle (get_hashtag_medias ile aynı format)
            media_list = []
            for media in medias:
                media_info = {
                    'id': media.id,
                    'pk': media.pk,
                    'code': media.code,
                    'media_type': media.media_type,
                    'caption': media.caption_text if media.caption_text else '',
                    'like_count': media.like_count,
                    'comment_count': media.comment_count,
                    'taken_at': media.taken_at,
                    'user': {
                        'username': media.user.username,
                        'full_name': media.user.full_name,
                        'pk': media.user.pk
                    },
                    'thumbnail_url': media.thumbnail_url,
                    'video_url': media.video_url if hasattr(media, 'video_url') else None,
                    'resources': []
                }
                
                # Album ise tüm medyaları ekle
                if media.media_type == 8 and hasattr(media, 'resources'):
                    for resource in media.resources:
                        media_info['resources'].append({
                            'pk': resource.pk,
                            'media_type': resource.media_type,
                            'thumbnail_url': resource.thumbnail_url,
                            'video_url': resource.video_url if hasattr(resource, 'video_url') else None
                        })
                
                media_list.append(media_info)
            
            return media_list
            
        except Exception as e:
            self.log(f"❌ Hashtag top medya alma hatası: {str(e)}")
            return []
    
    def download_media_by_pk(self, media_pk: str, output_folder: str = "output") -> List[str]:
        """Media PK ile medyayı indirir"""
        try:
            self.log(f"⬇️ Medya indiriliyor: {media_pk}")
            
            # Output klasörünü oluştur
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            
            downloaded_files = []
            
            # Media bilgisini al
            media = self.client.media_info(media_pk)
            
            if media.media_type == 1:  # Fotoğraf
                file_path = self.client.photo_download(media_pk, folder=output_folder)
                downloaded_files.append(str(file_path))
                self.log(f"📸 Fotoğraf indirildi: {file_path.name}")
                
            elif media.media_type == 2:  # Video
                file_path = self.client.video_download(media_pk, folder=output_folder)
                downloaded_files.append(str(file_path))
                self.log(f"🎥 Video indirildi: {file_path.name}")
                
            elif media.media_type == 8:  # Album
                file_paths = self.client.album_download(media_pk, folder=output_folder)
                for file_path in file_paths:
                    downloaded_files.append(str(file_path))
                self.log(f"📁 Album indirildi: {len(file_paths)} dosya")
            
            return downloaded_files
            
        except MediaNotFound:
            self.log(f"❌ Medya bulunamadı: {media_pk}")
            return []
        except Exception as e:
            self.log(f"❌ Medya indirme hatası: {str(e)}")
            return []
    
    def download_hashtag_medias(self, hashtag: str, amount: int = 50, output_folder: str = "output") -> List[str]:
        """Hashtag medyalarını toplu olarak indirir"""
        try:
            self.log(f"📥 Hashtag medyaları toplu indiriliyor: #{hashtag}")
            
            # Hashtag medyalarını al
            medias = self.get_hashtag_medias(hashtag, amount)
            
            if not medias:
                return []
            
            downloaded_files = []
            
            # Her medyayı indir
            for i, media in enumerate(medias, 1):
                self.log(f"📥 İndiriliyor ({i}/{len(medias)}): {media['user']['username']}")
                
                try:
                    files = self.download_media_by_pk(media['pk'], output_folder)
                    downloaded_files.extend(files)
                    
                    # İstekler arası bekleme
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    self.log(f"⚠️ Medya indirme hatası: {str(e)}")
                    continue
            
            self.log(f"✅ Toplam {len(downloaded_files)} dosya indirildi")
            return downloaded_files
            
        except Exception as e:
            self.log(f"❌ Toplu indirme hatası: {str(e)}")
            return []
    
    def get_user_medias(self, username: str, amount: int = 50) -> List[Dict]:
        """Kullanıcının medyalarını alır"""
        try:
            self.log(f"👤 Kullanıcı medyaları alınıyor: @{username}")
            
            # Kullanıcı ID'sini al
            user_id = self.client.user_id_from_username(username)
            
            # Kullanıcı medyalarını al
            medias = self.client.user_medias(user_id, amount=amount)
            
            if not medias:
                self.log(f"⚠️ @{username} kullanıcısında medya bulunamadı")
                return []
            
            self.log(f"✅ {len(medias)} adet medya bulundu")
            
            # Medya bilgilerini düzenle
            media_list = []
            for media in medias:
                media_info = {
                    'id': media.id,
                    'pk': media.pk,
                    'code': media.code,
                    'media_type': media.media_type,
                    'caption': media.caption_text if media.caption_text else '',
                    'like_count': media.like_count,
                    'comment_count': media.comment_count,
                    'taken_at': media.taken_at,
                    'user': {
                        'username': media.user.username,
                        'full_name': media.user.full_name,
                        'pk': media.user.pk
                    },
                    'thumbnail_url': media.thumbnail_url,
                    'video_url': media.video_url if hasattr(media, 'video_url') else None,
                    'resources': []
                }
                
                # Album ise tüm medyaları ekle
                if media.media_type == 8 and hasattr(media, 'resources'):
                    for resource in media.resources:
                        media_info['resources'].append({
                            'pk': resource.pk,
                            'media_type': resource.media_type,
                            'thumbnail_url': resource.thumbnail_url,
                            'video_url': resource.video_url if hasattr(resource, 'video_url') else None
                        })
                
                media_list.append(media_info)
            
            return media_list
            
        except Exception as e:
            self.log(f"❌ Kullanıcı medya alma hatası: {str(e)}")
            return []
    
    def get_media_info_by_shortcode(self, shortcode: str) -> Optional[Dict]:
        """Shortcode ile medya bilgisini alır"""
        try:
            self.log(f"🔍 Medya bilgisi alınıyor: {shortcode}")
            
            # Shortcode'dan media PK'sını al
            media_pk = self.client.media_pk_from_code(shortcode)
            
            # Media bilgisini al
            media = self.client.media_info(media_pk)
            
            media_info = {
                'id': media.id,
                'pk': media.pk,
                'code': media.code,
                'media_type': media.media_type,
                'caption': media.caption_text if media.caption_text else '',
                'like_count': media.like_count,
                'comment_count': media.comment_count,
                'taken_at': media.taken_at,
                'user': {
                    'username': media.user.username,
                    'full_name': media.user.full_name,
                    'pk': media.user.pk
                },
                'thumbnail_url': media.thumbnail_url,
                'video_url': media.video_url if hasattr(media, 'video_url') else None,
                'resources': []
            }
            
            # Album ise tüm medyaları ekle
            if media.media_type == 8 and hasattr(media, 'resources'):
                for resource in media.resources:
                    media_info['resources'].append({
                        'pk': resource.pk,
                        'media_type': resource.media_type,
                        'thumbnail_url': resource.thumbnail_url,
                        'video_url': resource.video_url if hasattr(resource, 'video_url') else None
                    })
            
            return media_info
            
        except Exception as e:
            self.log(f"❌ Medya bilgisi alma hatası: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Bağlantıyı test eder"""
        try:
            if self.is_logged_in:
                # Kendi profil bilgisini al
                account_info = self.client.account_info()
                self.log(f"✅ Bağlantı başarılı: @{account_info.username}")
                return True
            else:
                self.log("⚠️ Giriş yapılmamış")
                return False
        except Exception as e:
            self.log(f"❌ Bağlantı testi hatası: {str(e)}")
            return False