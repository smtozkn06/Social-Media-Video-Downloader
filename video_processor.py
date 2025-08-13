import os
import subprocess
from pathlib import Path
import tempfile
import shutil
import json

class VideoProcessor:
    def __init__(self, log_callback=None):
        self.target_width = 2160  # 4K genişlik
        self.target_height = 3840  # 4K yükseklik
        self.target_fps = 30
        self.music_volume = 0.5  # %50 ses seviyesi (varsayılan)
        self.original_audio_volume = 0.3  # %30 ses seviyesi (varsayılan)
        self.log_callback = log_callback
        
    def log(self, message):
        """Log mesajı gönder"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
        
    def get_video_info_ffmpeg(self, video_path):
        """
        FFmpeg ile video bilgilerini al
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                video_stream = None
                audio_stream = None
                
                for stream in data['streams']:
                    if stream['codec_type'] == 'video' and video_stream is None:
                        video_stream = stream
                    elif stream['codec_type'] == 'audio' and audio_stream is None:
                        audio_stream = stream
                
                info = {
                    'duration': float(data['format']['duration']),
                    'width': int(video_stream['width']) if video_stream else 0,
                    'height': int(video_stream['height']) if video_stream else 0,
                    'fps': eval(video_stream['r_frame_rate']) if video_stream and 'r_frame_rate' in video_stream else 30,
                    'has_audio': audio_stream is not None
                }
                return info
            else:
                self.log(f"FFprobe hatası: {result.stderr}")
                return None
                
        except Exception as e:
            self.log(f"Video bilgisi alma hatası: {str(e)}")
            return None
        
    def process_video(self, input_path, output_path, logo_path=None, music_path=None, music_volume=0.5, original_volume=0.3):
        """
        Videoyu işle: boyutlandır, logo ekle, müzik ekle (tamamen FFmpeg ile)
        """
        try:
            import time
            self.log(f"Video işleme başlıyor (FFmpeg): {input_path}")
            
            # Video bilgilerini al
            video_info = self.get_video_info_ffmpeg(input_path)
            if not video_info:
                self.log("Video bilgileri alınamadı")
                return False
            
            self.log(f"Video bilgileri: {video_info}")
            
            # Geçici dosya yolları
            temp_dir = os.path.dirname(output_path)
            temp_resized = os.path.join(temp_dir, f"temp_resized_{int(time.time())}.mp4")
            temp_with_logo = os.path.join(temp_dir, f"temp_logo_{int(time.time())}.mp4")
            
            try:
                # 1. Video boyutlandırma
                self.log("Video boyutlandırılıyor...")
                success = self.resize_video_with_ffmpeg(input_path, temp_resized)
                if not success:
                    self.log("Video boyutlandırma başarısız")
                    return False
                
                current_video_path = temp_resized
                
                # 2. Logo ekleme (varsa)
                if logo_path and os.path.exists(logo_path):
                    self.log("Logo ekleniyor...")
                    success = self.add_logo_with_ffmpeg(current_video_path, logo_path, temp_with_logo)
                    if success:
                        current_video_path = temp_with_logo
                    else:
                        self.log("Logo ekleme başarısız, logo olmadan devam ediliyor")
                
                # 3. Müzik ekleme (varsa)
                if music_path and os.path.exists(music_path):
                    self.log(f"Müzik ekleniyor... (Müzik: %{int(music_volume*100)}, Orijinal: %{int(original_volume*100)})")
                    success = self.add_music_with_ffmpeg(current_video_path, music_path, output_path, music_volume, original_volume)
                    if not success:
                        self.log("Müzik ekleme başarısız, müzik olmadan kopyalanıyor")
                        shutil.copy2(current_video_path, output_path)
                else:
                    self.log("Müzik yok, video kopyalanıyor...")
                    shutil.copy2(current_video_path, output_path)
                
                self.log(f"Video başarıyla işlendi (FFmpeg): {output_path}")
                return True
                
            finally:
                # Geçici dosyaları temizle
                for temp_file in [temp_resized, temp_with_logo]:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            self.log(f"Geçici dosya silindi: {temp_file}")
                        except:
                            pass
            
        except Exception as e:
            self.log(f"Video işleme hatası: {str(e)}")
            return False
    
    def resize_video_with_ffmpeg(self, input_path, output_path):
        """
        FFmpeg kullanarak videoyu 2160x3840 boyutuna ayarla (4K TikTok formatı)
        """
        try:
            self.log(f"FFmpeg ile video boyutlandırılıyor: {self.target_width}x{self.target_height}")
            
            # FFmpeg komutu oluştur - scale ve crop ile
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase,crop={self.target_width}:{self.target_height}',
                '-c:a', 'copy',    # Ses akışını kopyala
                '-c:v', 'libx264', # Video codec
                '-preset', 'fast', # Hızlı encoding
                '-crf', '23',      # Kalite
                '-y',              # Üzerine yaz
                output_path
            ]
            
            self.log(f"FFmpeg komutu çalıştırılıyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.log("FFmpeg ile video boyutlandırma başarılı")
                return True
            else:
                self.log(f"FFmpeg hatası: {result.stderr}")
                # Hata durumunda orijinal videoyu kopyala
                shutil.copy2(input_path, output_path)
                return False
                
        except Exception as e:
            self.log(f"FFmpeg video boyutlandırma hatası: {str(e)}")
            # Hata durumunda orijinal videoyu kopyala
            try:
                shutil.copy2(input_path, output_path)
            except:
                pass
            return False
    
    def add_logo_with_ffmpeg(self, video_path, logo_path, output_path):
        """
        FFmpeg kullanarak videoya logo ekle (sağ üst köşe)
        """
        try:
            if not logo_path or not os.path.exists(logo_path):
                self.log(f"Logo dosyası bulunamadı: {logo_path}")
                self.log("Video logo olmadan kopyalanacak")
                shutil.copy2(video_path, output_path)
                return True
                
            self.log(f"FFmpeg ile logo ekleniyor: {logo_path}")
            
            # Logo boyutunu hesapla (video genişliğinin %15'u - daha küçük)
            logo_width = int(self.target_width * 0.15)
            margin = 20
            
            # FFmpeg komutu oluştur - sağ üst köşe konumlandırması
            cmd = [
                'ffmpeg',
                '-i', video_path,  # Video girişi
                '-i', logo_path,   # Logo girişi
                '-filter_complex',
                f'[1:v]scale={logo_width}:-1[logo];'
                f'[0:v][logo]overlay=main_w-overlay_w-{margin}:{margin}',
                '-c:a', 'copy',    # Ses akışını kopyala
                '-c:v', 'libx264', # Video codec
                '-preset', 'fast', # Hızlı encoding
                '-crf', '23',      # Kalite
                '-y',              # Üzerine yaz
                output_path
            ]
            
            self.log(f"FFmpeg komutu çalıştırılıyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.log("FFmpeg ile logo başarıyla eklendi")
                return True
            else:
                self.log(f"FFmpeg hatası: {result.stderr}")
                # Hata durumunda orijinal videoyu kopyala
                shutil.copy2(video_path, output_path)
                return False
                
        except Exception as e:
            self.log(f"FFmpeg logo ekleme hatası: {str(e)}")
            # Hata durumunda orijinal videoyu kopyala
            try:
                shutil.copy2(video_path, output_path)
            except:
                pass
            return False
    
    def add_logo_to_video(self, video_path, logo_path, output_dir):
        """
        Videoya logo ekle ve işlenmiş dosya yolunu döndür
        """
        try:
            if not logo_path or not os.path.exists(logo_path):
                self.log(f"Logo dosyası bulunamadı: {logo_path}")
                return None
                
            # Çıktı dosya adını oluştur
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_with_logo.mp4")
            
            # Logo ekleme işlemi
            success = self.add_logo_with_ffmpeg(video_path, logo_path, output_path)
            
            if success and os.path.exists(output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            self.log(f"Logo ekleme hatası: {str(e)}")
            return None
    
    def add_logo_to_image(self, image_path, logo_path, output_dir):
        """
        Resme logo ekle ve işlenmiş dosya yolunu döndür
        """
        try:
            if not logo_path or not os.path.exists(logo_path):
                self.log(f"Logo dosyası bulunamadı: {logo_path}")
                return None
                
            # Çıktı dosya adını oluştur
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = os.path.splitext(image_path)[1]
            output_path = os.path.join(output_dir, f"{base_name}_with_logo{ext}")
            
            # FFmpeg ile resme logo ekleme
            success = self.add_logo_to_image_with_ffmpeg(image_path, logo_path, output_path)
            
            if success and os.path.exists(output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            self.log(f"Resim logo ekleme hatası: {str(e)}")
            return None
    
    def add_logo_to_image_with_ffmpeg(self, image_path, logo_path, output_path):
        """
        FFmpeg kullanarak resme logo ekle (sağ üst köşe)
        """
        try:
            if not logo_path or not os.path.exists(logo_path):
                self.log(f"Logo dosyası bulunamadı: {logo_path}")
                shutil.copy2(image_path, output_path)
                return True
                
            self.log(f"FFmpeg ile resme logo ekleniyor: {logo_path}")
            
            # Logo boyutunu hesapla (resim genişliğinin %15'u - daha küçük)
            margin = 20
            
            # FFmpeg komutu oluştur - sağ üst köşe konumlandırması
            cmd = [
                'ffmpeg',
                '-i', image_path,  # Resim girişi
                '-i', logo_path,   # Logo girişi
                '-filter_complex',
                f'[1:v]scale=iw*0.15:-1[logo];[0:v][logo]overlay=main_w-overlay_w-{margin}:{margin}',
                '-y',              # Üzerine yaz
                output_path
            ]
            
            self.log(f"FFmpeg komutu çalıştırılıyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.log("FFmpeg ile resme logo başarıyla eklendi")
                return True
            else:
                self.log(f"FFmpeg hatası: {result.stderr}")
                # Hata durumunda orijinal resmi kopyala
                shutil.copy2(image_path, output_path)
                return False
                
        except Exception as e:
            self.log(f"FFmpeg resim logo ekleme hatası: {str(e)}")
            # Hata durumunda orijinal resmi kopyala
            try:
                shutil.copy2(image_path, output_path)
            except:
                pass
            return False
            
    def add_music_with_ffmpeg(self, video_path, music_path, output_path, music_volume=0.5, original_volume=0.3):
        """
        FFmpeg kullanarak videoya müzik ekle (%30 ses seviyesinde)
        """
        try:
            if not music_path or not os.path.exists(music_path):
                self.log(f"Müzik dosyası bulunamadı veya belirtilmedi: {music_path}")
                self.log("Video müzik olmadan kopyalanacak")
                shutil.copy2(video_path, output_path)
                return True
                
            self.log(f"FFmpeg ile müzik ekleniyor: {music_path}")
            
            # Video bilgilerini al
            video_info = self.get_video_info_ffmpeg(video_path)
            if not video_info:
                self.log("Video bilgileri alınamadı, müzik ekleme atlanıyor")
                shutil.copy2(video_path, output_path)
                return True
            
            # FFmpeg komutu oluştur
            if video_info['has_audio']:
                # Orijinal ses varsa karıştır
                cmd = [
                    'ffmpeg',
                    '-i', video_path,  # Video girişi
                    '-i', music_path,  # Müzik girişi
                    '-filter_complex',
                    f'[0:a]volume={original_volume}[original_audio];'
                    f'[1:a]volume={music_volume},aloop=loop=-1:size=2e+09[music];'
                    f'[original_audio][music]amix=inputs=2:duration=first:dropout_transition=2[audio]',
                    '-map', '0:v',     # Video akışını kopyala
                    '-map', '[audio]', # Karışık ses akışını kullan
                    '-c:v', 'copy',    # Video codec'ini kopyala
                    '-c:a', 'aac',     # Ses codec'i
                    '-b:a', '128k',    # Ses bitrate
                    '-y',              # Üzerine yaz
                    output_path
                ]
            else:
                # Orijinal ses yoksa sadece müzik ekle
                cmd = [
                    'ffmpeg',
                    '-i', video_path,  # Video girişi
                    '-i', music_path,  # Müzik girişi
                    '-filter_complex',
                    f'[1:a]volume={music_volume},aloop=loop=-1:size=2e+09[audio]',
                    '-map', '0:v',     # Video akışını kopyala
                    '-map', '[audio]', # Müzik ses akışını kullan
                    '-c:v', 'copy',    # Video codec'ini kopyala
                    '-c:a', 'aac',     # Ses codec'i
                    '-b:a', '128k',    # Ses bitrate
                    '-shortest',       # En kısa akışa göre kes
                    '-y',              # Üzerine yaz
                    output_path
                ]
            
            self.log(f"FFmpeg komutu çalıştırılıyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.log("FFmpeg ile müzik başarıyla eklendi")
                return True
            else:
                self.log(f"FFmpeg hatası: {result.stderr}")
                # Hata durumunda orijinal videoyu kopyala
                shutil.copy2(video_path, output_path)
                return False
                
        except Exception as e:
            self.log(f"FFmpeg müzik ekleme hatası: {str(e)}")
            # Hata durumunda orijinal videoyu kopyala
            try:
                shutil.copy2(video_path, output_path)
            except:
                pass
            return False
    

            

            


# Import işlemleri yukarıda tamamlandı
