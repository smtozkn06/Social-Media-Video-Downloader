# -*- coding: utf-8 -*-

class Translations:
    def __init__(self):
        self.current_language = "tr"
        self.translations = {
            "tr": {
                # Main Menu
                "app_title": "Social Media Video Downloader",
                "main_menu_title": "Video Downloader and Editor - Main Menu",
                "supported_platforms": "YouTube • TikTok • Instagram • Facebook • Pinterest • Twitter",
                "app_description": "Modern ve güçlü sosyal medya video indirme platformu",
                "supported_platforms_title": "Desteklenen Platformlar",
                
                # Navigation Menu
                "nav_home": "Ana Sayfa",
                "nav_tiktok_single": "TikTok Hızlı İndirme",
                "nav_youtube_single": "YouTube Video Çekici",
                "nav_instagram_single": "Instagram Medya İndirici",
                "nav_facebook_single": "Facebook Video Alıcı",
                "nav_pinterest_single": "Pinterest Pin Kaydetme",
                "nav_twitter_single": "Twitter Medya Çekici",
                "nav_tiktok_bulk": "TikTok Toplu Arşivleme",
                "nav_youtube_bulk": "YouTube Playlist İndirici",
                "nav_instagram_bulk": "Instagram Galeri Yedekleme",
                "nav_pinterest_bulk": "Pinterest Koleksiyon İndirici",
                "nav_twitter_bulk": "Twitter Medya Arşivleme",
                "nav_video_editor": "TikTok Video Editörü",
                "nav_settings": "Ayarlar",
                
                # Settings
                "settings_title": "Ayarlar",
                "general_settings": "Genel Ayarlar",
                "theme_light": "Açık Tema (Sabit)",
                "language": "Dil",
                "language_turkish": "Türkçe",
                "language_english": "English",
                "auto_start": "Otomatik Başlatma",
                "notifications": "Bildirimler",
                "back_to_main": "Back to Main Menu",
                "reset_settings": "Ayarları Sıfırla",
                "reset_confirm_title": "Ayarları Sıfırla",
                "reset_confirm_message": "Tüm ayarlar varsayılan değerlere sıfırlanacak. Emin misiniz?",
                "yes": "Evet",
                "no": "Hayır",
                
                # Common Buttons
                "download": "İndir",
                "start": "Başlat",
                "stop": "Durdur",
                "browse": "Gözat",
                "save": "Kaydet",
                "cancel": "İptal",
                "close": "Kapat",
                "open": "Aç",
                "clear": "Temizle",
                "refresh": "Yenile",
                
                # Status Messages
                "downloading": "İndiriliyor...",
                "completed": "Tamamlandı",
                "failed": "Başarısız",
                "processing": "İşleniyor...",
                "waiting": "Bekliyor...",
                "ready": "Hazır",
                
                # Error Messages
                "error_invalid_url": "Geçersiz URL",
                "error_network": "Ağ hatası",
                "error_file_not_found": "Dosya bulunamadı",
                "error_permission_denied": "İzin reddedildi",
                "error_unknown": "Bilinmeyen hata",
                
                # Platform Names
                "platform_youtube": "YouTube",
                "platform_tiktok": "TikTok",
                "platform_instagram": "Instagram",
                "platform_facebook": "Facebook",
                "platform_pinterest": "Pinterest",
                "platform_twitter": "Twitter",
                
                # File Operations
                "select_folder": "Klasör Seç",
                "output_folder": "Çıktı Klasörü",
                "file_saved": "Dosya kaydedildi",
                "file_exists": "Dosya zaten mevcut",
                
                # Video Quality
                "quality_high": "Yüksek Kalite",
                "quality_medium": "Orta Kalite",
                "quality_low": "Düşük Kalite",
                "quality_auto": "Otomatik",
                
                # Platform Descriptions
                "platform_youtube_desc": "Videolar, müzikler ve oynatma listeleri",
                "platform_tiktok_desc": "Viral videolar ve müzikler",
                "platform_instagram_desc": "Fotoğraflar, videolar ve hikayeler",
                "platform_facebook_desc": "Videolar ve sosyal içerikler",
                "platform_pinterest_desc": "Pinler ve görsel içerikler",
                "platform_twitter_desc": "Videolar ve medya içerikleri",
                "platform_more_desc": "Sürekli güncellenen platform desteği",
                "platform_more": "Daha Fazlası",
                
                # Quick Actions
                "quick_start": "Hızlı Başlangıç",
                "download_video": "🎬 Video İndir",
                "exit_app": "🚪 Çıkış",
                
                # Content Titles and Descriptions
                "tiktok_single_content_title": "TikTok Hızlı İndirme",
                "tiktok_single_content_desc": "Tek bir TikTok videosunu indirmek için bu modülü kullanın.",
                "tiktok_single_content_button": "TikTok Hızlı İndirmeyi Başlat",
                
                "youtube_single_content_title": "YouTube Video Çekici",
                "youtube_single_content_desc": "Tek bir YouTube videosunu indirmek için bu modülü kullanın.",
                "youtube_single_content_button": "YouTube Video Çekiciyi Başlat",
                
                "tiktok_bulk_content_title": "TikTok Toplu Arşivleme",
                "tiktok_bulk_content_desc": "Birden fazla TikTok videosunu toplu olarak indirmek için bu modülü kullanın.",
                "tiktok_bulk_content_button": "TikTok Toplu Arşivlemeyi Başlat",
                
                "youtube_bulk_content_title": "YouTube Playlist İndirici",
                "youtube_bulk_content_desc": "Birden fazla YouTube short videosunu toplu olarak indirmek için bu modülü kullanın.",
                "youtube_bulk_content_button": "YouTube Playlist İndiriciyi Başlat",
                
                "instagram_single_content_title": "Instagram Medya İndirici",
                "instagram_single_content_desc": "Tek bir Instagram videosunu indirmek için bu modülü kullanın.",
                "instagram_single_content_button": "Instagram Medya İndiriciyi Başlat",
                
                "instagram_bulk_content_title": "Instagram Galeri Yedekleme",
                "instagram_bulk_content_desc": "Birden fazla Instagram videosunu toplu olarak indirmek için bu modülü kullanın.",
                "instagram_bulk_content_button": "Instagram Galeri Yedeklemeyi Başlat",
                
                "facebook_single_content_title": "Facebook Video Alıcı",
                "facebook_single_content_desc": "Tek bir Facebook videosunu indirmek için bu modülü kullanın.",
                "facebook_single_content_button": "Facebook Video Alıcıyı Başlat",
                
                "twitter_single_content_title": "Twitter Medya Çekici",
                "twitter_single_content_desc": "Twitter/X'den video, resim ve GIF'leri indirin.",
                "twitter_single_content_button": "Twitter Medya İndirici Başlat",
                
                "twitter_bulk_content_title": "Twitter Medya Arşivleme",
                "twitter_bulk_content_desc": "Twitter/X hesaplarından toplu medya indirin ve arşivleyin.",
                "twitter_bulk_content_button": "Twitter Toplu İndirici Başlat",
                
                "video_editor_content_title": "TikTok Video Editörü",
                "video_editor_content_desc": "TikTok videolarını indirin ve düzenleyin.",
                "video_editor_content_button": "Video Editörü Başlat",
                
                "settings_content_title": "Ayarlar",
            "settings_content_desc": "Uygulama ayarlarını buradan yapılandırabilirsiniz.",
            "settings_content_button1": "Ayarları Aç",
            "settings_content_button2": "Tema Değiştir",
            
            # Splash Screen
            "splash_title": "Social Media Downloader",
            "splash_subtitle": "YouTube • TikTok • Instagram • Facebook • Twitter",
            "splash_loading": "Sosyal medya platformları yükleniyor...",
                
                # TikTok Module
                "tiktok_single_title": "TikTok Tekli Video İndirici ve Düzenleyici",
                "video_url_input": "Video URL Girişi",
                "tiktok_url_label": "TikTok Video URL'si",
                "tiktok_url_hint": "Örnek: https://www.tiktok.com/@kullaniciadi/video/1234567890123456789",
                "file_settings": "Dosya Ayarları",
                "add_logo": "Logo Ekle",
                "logo_file": "Logo Dosyası (.png)",
                "output_folder": "Çıktı Klasörü",
                "select": "Seç",
                "start_download": "İndirmeyi Başlat",
                "stop": "Durdur",
                "ready": "Hazır",
                "log": "Log:",
                "copy_logs": "Logları Kopyala",
                "clear_logs": "Logları Temizle",
                
                # YouTube Module
                "youtube_single_title": "YouTube Tekli Video İndirici ve Düzenleyici",
                "youtube_url_label": "YouTube Video URL'si",
                "youtube_url_hint": "Örnek: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "convert_to_mp3": "MP3'e Dönüştür",
                "audio_level": "Ses Seviyesi",
                "original": "Orijinal",
                "low": "Düşük",
                "medium": "Orta",
                 "high": "Yüksek",
                 
                 # Instagram Module
                 "instagram_single_title": "Instagram Tekli İndirici",
                 "instagram_url_label": "Instagram URL'si",
                 "instagram_url_hint": "Örn: https://www.instagram.com/p/... (Post/Reel/Hikaye)",
                 "download_type": "İndirme Türü",
                 "auto_detect": "Otomatik Algıla",
                 "post": "Post",
                 "reel": "Reel",
                 "story": "Hikaye",
                 "post_info": "Post Bilgileri",
                 "author": "Yazar",
                 "caption": "Açıklama",
                 "likes": "Beğeni",
                 "comments": "Yorum",
                 "date": "Tarih",
                
                # TikTok Module
                "tiktok_single_title": "TikTok Single Video Downloader and Editor",
                "video_url_input": "Video URL Input",
                "tiktok_url_label": "TikTok Video URL",
                "tiktok_url_hint": "Example: https://www.tiktok.com/@username/video/1234567890123456789",
                "file_settings": "File Settings",
                "add_logo": "Add Logo",
                "logo_file": "Logo File (.png)",
                "output_folder": "Output Folder",
                "select": "Select",
                "start_download": "Start Download",
                "stop": "Stop",
                "ready": "Ready",
                "log": "Log:",
                "copy_logs": "Copy Logs",
                 "clear_logs": "Clear Logs",
                 
                 # YouTube Module
                 "youtube_single_title": "YouTube Single Video Downloader and Editor",
                 "youtube_url_label": "YouTube Video URL",
                 "youtube_url_hint": "Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                 "convert_to_mp3": "Convert to MP3",
                 "audio_level": "Audio Level",
                 "original": "Original",
                 "low": "Low",
                 "medium": "Medium",
                 "high": "High",
             },
            
            "en": {
                # Main Menu
                "app_title": "Social Media Video Downloader",
                "main_menu_title": "Video Downloader and Editor - Main Menu",
                "supported_platforms": "YouTube • TikTok • Instagram • Facebook • Pinterest • Twitter",
                "app_description": "Modern and powerful social media video download platform",
                "supported_platforms_title": "Supported Platforms",
                
                # Navigation Menu
                "nav_home": "Home",
                "nav_tiktok_single": "TikTok Quick Download",
                "nav_youtube_single": "YouTube Video Downloader",
                "nav_instagram_single": "Instagram Media Downloader",
                "nav_facebook_single": "Facebook Video Downloader",
                "nav_pinterest_single": "Pinterest Pin Saver",
                "nav_twitter_single": "Twitter Media Downloader",
                "nav_tiktok_bulk": "TikTok Bulk Archive",
                "nav_youtube_bulk": "YouTube Playlist Downloader",
                "nav_instagram_bulk": "Instagram Gallery Backup",
                "nav_pinterest_bulk": "Pinterest Collection Downloader",
                "nav_twitter_bulk": "Twitter Media Archive",
                "nav_video_editor": "TikTok Video Editor",
                "nav_settings": "Settings",
                
                # Settings
                "settings_title": "Settings",
                "general_settings": "General Settings",
                "theme_light": "Light Theme (Fixed)",
                "language": "Language",
                "language_turkish": "Türkçe",
                "language_english": "English",
                "auto_start": "Auto Start",
                "notifications": "Notifications",
                "back_to_main": "Back to Main Menu",
                "reset_settings": "Reset Settings",
                "reset_confirm_title": "Reset Settings",
                "reset_confirm_message": "All settings will be reset to default values. Are you sure?",
                "yes": "Yes",
                "no": "No",
                
                # Common Buttons
                "download": "Download",
                "start": "Start",
                "stop": "Stop",
                "browse": "Browse",
                "save": "Save",
                "cancel": "Cancel",
                "close": "Close",
                "open": "Open",
                "clear": "Clear",
                "refresh": "Refresh",
                
                # Status Messages
                "downloading": "Downloading...",
                "completed": "Completed",
                "failed": "Failed",
                "processing": "Processing...",
                "waiting": "Waiting...",
                "ready": "Ready",
                
                # Error Messages
                "error_invalid_url": "Invalid URL",
                "error_network": "Network error",
                "error_file_not_found": "File not found",
                "error_permission_denied": "Permission denied",
                "error_unknown": "Unknown error",
                
                # Platform Names
                "platform_youtube": "YouTube",
                "platform_tiktok": "TikTok",
                "platform_instagram": "Instagram",
                "platform_facebook": "Facebook",
                "platform_pinterest": "Pinterest",
                "platform_twitter": "Twitter",
                
                # File Operations
                "select_folder": "Select Folder",
                "output_folder": "Output Folder",
                "file_saved": "File saved",
                "file_exists": "File already exists",
                
                # Video Quality
                "quality_high": "High Quality",
                "quality_medium": "Medium Quality",
                "quality_low": "Low Quality",
                "quality_auto": "Auto",
                
                # Platform Descriptions
                "platform_youtube_desc": "Videos, music and playlists",
                "platform_tiktok_desc": "Viral videos and music",
                "platform_instagram_desc": "Photos, videos and stories",
                "platform_facebook_desc": "Videos and social content",
                "platform_pinterest_desc": "Pins and visual content",
                "platform_twitter_desc": "Videos and media content",
                "platform_more_desc": "Continuously updated platform support",
                "platform_more": "More",
                
                # Quick Actions
                "quick_start": "Quick Start",
                "download_video": "🎬 Download Video",
                "exit_app": "🚪 Exit",
                
                # Content Titles and Descriptions
                "tiktok_single_content_title": "TikTok Quick Download",
                "tiktok_single_content_desc": "Use this module to download a single TikTok video.",
                "tiktok_single_content_button": "Start TikTok Quick Download",
                
                "youtube_single_content_title": "YouTube Video Downloader",
                "youtube_single_content_desc": "Use this module to download a single YouTube video.",
                "youtube_single_content_button": "Start YouTube Video Downloader",
                
                "tiktok_bulk_content_title": "TikTok Bulk Archive",
                "tiktok_bulk_content_desc": "Use this module to download multiple TikTok videos in bulk.",
                "tiktok_bulk_content_button": "Start TikTok Bulk Archive",
                
                "youtube_bulk_content_title": "YouTube Playlist Downloader",
                "youtube_bulk_content_desc": "Use this module to download multiple YouTube short videos in bulk.",
                "youtube_bulk_content_button": "Start YouTube Playlist Downloader",
                
                "instagram_single_content_title": "Instagram Media Downloader",
                "instagram_single_content_desc": "Use this module to download a single Instagram video.",
                "instagram_single_content_button": "Start Instagram Media Downloader",
                
                "instagram_bulk_content_title": "Instagram Gallery Backup",
                "instagram_bulk_content_desc": "Use this module to download multiple Instagram videos in bulk.",
                "instagram_bulk_content_button": "Start Instagram Gallery Backup",
                
                "facebook_single_content_title": "Facebook Video Downloader",
                "facebook_single_content_desc": "Use this module to download a single Facebook video.",
                "facebook_single_content_button": "Start Facebook Video Downloader",
                
                "twitter_single_content_title": "Twitter Media Downloader",
                "twitter_single_content_desc": "Download videos, images and GIFs from Twitter/X.",
                "twitter_single_content_button": "Start Twitter Media Downloader",
                
                "twitter_bulk_content_title": "Twitter Media Archive",
                "twitter_bulk_content_desc": "Download and archive bulk media from Twitter/X accounts.",
                "twitter_bulk_content_button": "Start Twitter Bulk Downloader",
                
                "video_editor_content_title": "TikTok Video Editor",
                "video_editor_content_desc": "Download and edit TikTok videos.",
                "video_editor_content_button": "Start Video Editor",
                
                "settings_content_title": "Settings",
            "settings_content_desc": "You can configure application settings from here.",
            "settings_content_button1": "Open Settings",
            "settings_content_button2": "Change Theme",
            
            # Splash Screen
            "splash_title": "Social Media Downloader",
            "splash_subtitle": "YouTube • TikTok • Instagram • Facebook • Twitter",
            "splash_loading": "Loading social media platforms...",
                
                # Instagram Module
                "instagram_single_title": "Instagram Single Downloader",
                "instagram_url_label": "Instagram URL",
                "instagram_url_hint": "Example: https://www.instagram.com/p/... (Post/Reel/Story)",
                "download_type": "Download Type",
                "auto_detect": "Auto Detect",
                "post": "Post",
                "reel": "Reel",
                "story": "Story",
                "post_info": "Post Information",
                "author": "Author",
                "caption": "Caption",
                "likes": "Likes",
                "comments": "Comments",
                "date": "Date",
                "exit_app": "🚪 Exit",
            }
        }
    
    def set_language(self, language):
        """Mevcut dili ayarla"""
        if language in self.translations:
            self.current_language = language
    
    def get_text(self, key, language=None):
        """Belirtilen anahtar için çeviriyi döndür"""
        if language is None:
            language = self.current_language
        
        if language in self.translations and key in self.translations[language]:
            return self.translations[language][key]
        elif key in self.translations["tr"]:
            return self.translations["tr"][key]
        else:
            return key
    
    def get_all_keys(self):
        """Tüm çeviri anahtarlarını döndür"""
        return list(self.translations["tr"].keys())