#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Profil HTTP İndirme Test Kodu
Cookie kullanarak HTTP ile profil gönderileri ve reels indirme testi
"""

import os
import json
import time
from .instagram_http_downloader import InstagramHttpDownloader
from .instagram_scraper import InstagramScraper

# Instagrapi kütüphanesini import et
try:
    from instagrapi import Client
    INSTAGRAPI_AVAILABLE = True
    print("✅ Instagrapi kütüphanesi yüklendi")
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    print("❌ Instagrapi kütüphanesi bulunamadı. 'pip install instagrapi' ile yükleyin.")

def load_cookies():
    """Kaydedilmiş cookie'leri yükler"""
    try:
        cookie_file = "cookie/instagram_cookies.json"
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            print(f"✅ {len(cookies)} adet cookie yüklendi")
            return cookies
        else:
            print("❌ Cookie dosyası bulunamadı")
            return None
    except Exception as e:
        print(f"❌ Cookie yükleme hatası: {str(e)}")
        return None

def test_instagrapi_login():
    """Instagrapi ile giriş testi"""
    if not INSTAGRAPI_AVAILABLE:
        print("❌ Instagrapi kütüphanesi mevcut değil")
        return None
    
    try:
        cl = Client()
        
        # Cookie'leri yükle ve session'a aktar
        cookies = load_cookies()
        if cookies:
            # Cookie'leri requests session formatına çevir
            session_cookies = {}
            for cookie in cookies:
                session_cookies[cookie['name']] = cookie['value']
            
            # Instagrapi client'ının session'ına cookie'leri ekle
            cl.private.cookies.update(session_cookies)
            
            # Önemli session bilgilerini ayarla
            settings = {
                'user_agent': 'Instagram 219.0.0.12.117 Android',
                'cookies': session_cookies
            }
            
            # Eğer sessionid varsa, login durumunu ayarla
            if 'sessionid' in session_cookies:
                settings['user_id'] = None  # Bu otomatik olarak tespit edilecek
                cl.set_settings(settings)
                
                # Login durumunu kontrol et
                try:
                    user_info = cl.account_info()
                    print(f"✅ Giriş başarılı: {user_info.username}")
                    return cl
                except Exception as e:
                    print(f"⚠️ Cookie ile giriş başarısız: {e}")
                    # Public API'yi dene
                    try:
                        print("🔄 Public API ile deneniyor...")
                        return cl
                    except Exception as e2:
                        print(f"❌ Public API de başarısız: {e2}")
                        return None
            else:
                print("❌ sessionid cookie'si bulunamadı")
                return None
        else:
            print("❌ Cookie bulunamadı")
            return None
            
    except Exception as e:
        print(f"❌ Instagrapi client oluşturma hatası: {e}")
        return None

def test_instagrapi_profile_posts(profile_url, max_posts=5):
    """Instagram API ile profil gönderileri test eder (Scrapfly yöntemi)"""
    print("\n" + "="*60)
    print("📝 İNSTAGRAM API PROFİL GÖNDERİLERİ TESTİ")
    print("="*60)
    
    try:
        import requests
        import json
        
        # Username çıkar
        username = profile_url.split('/')[-1] or profile_url.split('/')[-2]
        print(f"🔍 Test kullanıcı: {username}")
        print(f"📊 Maksimum gönderi: {max_posts}")
        
        # Instagram API headers (Scrapfly yöntemi)
        headers = {
            "x-ig-app-id": "936619743392459",  # Instagram backend app ID
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        
        # Instagram API endpoint kullan
        print("\n👤 Kullanıcı bilgisi alınıyor (Instagram API)...")
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                user_data = data.get('data', {}).get('user', {})
                
                if user_data:
                    print(f"✅ Kullanıcı bilgisi alındı")
                    print(f"📝 Tam ad: {user_data.get('full_name', 'N/A')}")
                    print(f"👥 Takipçi: {user_data.get('edge_followed_by', {}).get('count', 'N/A')}")
                    print(f"👤 Takip edilen: {user_data.get('edge_follow', {}).get('count', 'N/A')}")
                    print(f"📊 Gönderi sayısı: {user_data.get('edge_owner_to_timeline_media', {}).get('count', 'N/A')}")
                    print(f"🔒 Gizli hesap: {'Evet' if user_data.get('is_private', False) else 'Hayır'}")
                    print(f"✅ Doğrulanmış: {'Evet' if user_data.get('is_verified', False) else 'Hayır'}")
                    
                    # Profil fotoğrafı
                    if user_data.get('profile_pic_url_hd'):
                        print(f"🖼️ Profil fotoğrafı: {user_data['profile_pic_url_hd'][:60]}...")
                    
                    # Biyografi
                    if user_data.get('biography'):
                        bio = user_data['biography'][:100] + "..." if len(user_data['biography']) > 100 else user_data['biography']
                        print(f"📝 Biyografi: {bio}")
                    
                    # Son gönderileri al
                    timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                    edges = timeline_media.get('edges', [])
                    
                    if edges:
                        print(f"\n📱 {len(edges[:max_posts])} gönderi bulundu:")
                        
                        for i, edge in enumerate(edges[:max_posts], 1):
                            node = edge.get('node', {})
                            print(f"\n  {i}. Gönderi:")
                            print(f"     🔗 Shortcode: {node.get('shortcode', 'N/A')}")
                            print(f"     📅 Tarih: {node.get('taken_at_timestamp', 'N/A')}")
                            print(f"     👍 Beğeni: {node.get('edge_liked_by', {}).get('count', 'N/A')}")
                            print(f"     💬 Yorum: {node.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                            print(f"     📺 Video: {'Evet' if node.get('is_video', False) else 'Hayır'}")
                            
                            # Medya URL'si
                            if node.get('display_url'):
                                print(f"     🖼️ Medya: {node['display_url'][:60]}...")
                            
                            # Caption (kısaltılmış)
                            caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                            if caption_edges and caption_edges[0].get('node', {}).get('text'):
                                caption = caption_edges[0]['node']['text']
                                short_caption = caption[:80] + "..." if len(caption) > 80 else caption
                                print(f"     💬 Açıklama: {short_caption}")
                        
                        return True
                    else:
                        print("❌ Gönderi bulunamadı")
                        return False
                else:
                    print("❌ Kullanıcı verisi bulunamadı")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return False
        else:
            print(f"❌ API isteği başarısız: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

def test_instagrapi_profile_reels(profile_url, max_reels=5):
    """Instagram API ile profil reels test eder (Scrapfly yöntemi)"""
    print("\n" + "="*60)
    print("🎬 İNSTAGRAM API PROFİL REELS TESTİ")
    print("="*60)
    
    try:
        import requests
        import json
        
        # Username çıkar
        username = profile_url.split('/')[-1] or profile_url.split('/')[-2]
        print(f"🔍 Test kullanıcı: {username}")
        print(f"🎬 Maksimum reels: {max_reels}")
        
        # Instagram API headers (Scrapfly yöntemi)
        headers = {
            "x-ig-app-id": "936619743392459",  # Instagram backend app ID
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        
        # Instagram API endpoint kullan
        print("\n🎬 Reels bilgisi alınıyor (Instagram API)...")
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                user_data = data.get('data', {}).get('user', {})
                
                if user_data:
                    print(f"✅ Kullanıcı bilgisi alındı")
                    
                    # Timeline medyalarından video olanları filtrele
                    timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                    edges = timeline_media.get('edges', [])
                    
                    # Video olan gönderileri filtrele
                    video_posts = []
                    for edge in edges:
                        node = edge.get('node', {})
                        if node.get('is_video', False):
                            video_posts.append(node)
                    
                    if video_posts:
                        reels_found = video_posts[:max_reels]
                        print(f"\n🎬 {len(reels_found)} video/reels bulundu:")
                        
                        for i, video in enumerate(reels_found, 1):
                            print(f"\n  {i}. Video/Reels:")
                            print(f"     🔗 Shortcode: {video.get('shortcode', 'N/A')}")
                            print(f"     📅 Tarih: {video.get('taken_at_timestamp', 'N/A')}")
                            print(f"     👍 Beğeni: {video.get('edge_liked_by', {}).get('count', 'N/A')}")
                            print(f"     💬 Yorum: {video.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                            print(f"     ⏱️ Süre: {video.get('video_duration', 'N/A')} saniye")
                            print(f"     👁️ İzlenme: {video.get('video_view_count', 'N/A')}")
                            
                            # Thumbnail
                            if video.get('display_url'):
                                print(f"     🖼️ Thumbnail: {video['display_url'][:60]}...")
                            
                            # Video URL (eğer varsa)
                            if video.get('video_url'):
                                print(f"     🎬 Video URL: {video['video_url'][:60]}...")
                            
                            # Caption (kısaltılmış)
                            caption_edges = video.get('edge_media_to_caption', {}).get('edges', [])
                            if caption_edges and caption_edges[0].get('node', {}).get('text'):
                                caption = caption_edges[0]['node']['text']
                                short_caption = caption[:80] + "..." if len(caption) > 80 else caption
                                print(f"     💬 Açıklama: {short_caption}")
                        
                        return True
                    else:
                        print("❌ Video/Reels bulunamadı")
                        
                        # Alternatif: Tüm gönderileri göster (debug için)
                        if edges:
                            print(f"\n📊 Toplam {len(edges)} gönderi var, ancak hiçbiri video değil")
                            print("İlk 3 gönderinin türü:")
                            for i, edge in enumerate(edges[:3], 1):
                                node = edge.get('node', {})
                                print(f"  {i}. Video: {node.get('is_video', False)}, Shortcode: {node.get('shortcode', 'N/A')}")
                        
                        return False
                else:
                    print("❌ Kullanıcı verisi bulunamadı")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return False
        else:
            print(f"❌ API isteği başarısız: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

def test_profile_posts_http(profile_url, max_posts=5):
    """Instagram API ile profil gönderileri test eder"""
    print("\n" + "="*60)
    print("📝 İNSTAGRAM API PROFİL GÖNDERİLERİ TESTİ")
    print("="*60)
    
    try:
        import requests
        import json
        
        # Username çıkar
        username = profile_url.split('/')[-1] or profile_url.split('/')[-2]
        print(f"🔍 Test kullanıcı: {username}")
        print(f"📊 Maksimum gönderi: {max_posts}")
        
        # Instagram API headers
        headers = {
            "x-ig-app-id": "936619743392459",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        
        # Instagram API endpoint
        print("\n📱 Instagram API ile profil gönderileri alınıyor...")
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                user_data = data.get('data', {}).get('user', {})
                
                if user_data:
                    # Son gönderileri al
                    timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                    edges = timeline_media.get('edges', [])
                    
                    if edges:
                        posts_found = edges[:max_posts]
                        print(f"✅ {len(posts_found)} gönderi bulundu:")
                        
                        for i, edge in enumerate(posts_found, 1):
                            node = edge.get('node', {})
                            print(f"\n  {i}. Gönderi:")
                            print(f"     🔗 Shortcode: {node.get('shortcode', 'N/A')}")
                            print(f"     📅 Tarih: {node.get('taken_at_timestamp', 'N/A')}")
                            print(f"     👍 Beğeni: {node.get('edge_liked_by', {}).get('count', 'N/A')}")
                            print(f"     💬 Yorum: {node.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                            print(f"     📺 Video: {'Evet' if node.get('is_video', False) else 'Hayır'}")
                            
                            # Medya URL'si
                            if node.get('display_url'):
                                print(f"     🖼️ Medya: {node['display_url'][:60]}...")
                            
                            # Caption (kısaltılmış)
                            caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                            if caption_edges and caption_edges[0].get('node', {}).get('text'):
                                caption = caption_edges[0]['node']['text']
                                short_caption = caption[:80] + "..." if len(caption) > 80 else caption
                                print(f"     💬 Açıklama: {short_caption}")
                        
                        return True
                    else:
                        print("❌ Gönderi bulunamadı")
                        return False
                else:
                    print("❌ Kullanıcı verisi bulunamadı")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return False
        else:
            print(f"❌ API hatası: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

def test_profile_reels_http(profile_url, max_reels=5):
    """Instagram API ile profil reels test eder"""
    print("\n" + "="*60)
    print("🎬 İNSTAGRAM API PROFİL REELS TESTİ")
    print("="*60)
    
    try:
        import requests
        import json
        
        # Username çıkar
        username = profile_url.split('/')[-1] or profile_url.split('/')[-2]
        print(f"🔍 Test kullanıcı: {username}")
        print(f"🎬 Maksimum reels: {max_reels}")
        
        # Instagram API headers
        headers = {
            "x-ig-app-id": "936619743392459",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        
        # Instagram API endpoint
        print("\n🎬 Instagram API ile profil reels alınıyor...")
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                user_data = data.get('data', {}).get('user', {})
                
                if user_data:
                    # Timeline medyalarından video olanları filtrele
                    timeline_media = user_data.get('edge_owner_to_timeline_media', {})
                    edges = timeline_media.get('edges', [])
                    
                    # Video olan gönderileri filtrele
                    video_posts = []
                    for edge in edges:
                        node = edge.get('node', {})
                        if node.get('is_video', False):
                            video_posts.append(node)
                    
                    if video_posts:
                        reels_found = video_posts[:max_reels]
                        print(f"✅ {len(reels_found)} video/reels bulundu:")
                        
                        for i, video in enumerate(reels_found, 1):
                            print(f"\n  {i}. Video/Reels:")
                            print(f"     🔗 Shortcode: {video.get('shortcode', 'N/A')}")
                            print(f"     📅 Tarih: {video.get('taken_at_timestamp', 'N/A')}")
                            print(f"     👍 Beğeni: {video.get('edge_liked_by', {}).get('count', 'N/A')}")
                            print(f"     💬 Yorum: {video.get('edge_media_to_comment', {}).get('count', 'N/A')}")
                            print(f"     ⏱️ Süre: {video.get('video_duration', 'N/A')} saniye")
                            print(f"     👁️ İzlenme: {video.get('video_view_count', 'N/A')}")
                            
                            # Thumbnail
                            if video.get('display_url'):
                                print(f"     🖼️ Thumbnail: {video['display_url'][:60]}...")
                            
                            # Video URL (eğer varsa)
                            if video.get('video_url'):
                                print(f"     🎬 Video URL: {video['video_url'][:60]}...")
                            
                            # Caption (kısaltılmış)
                            caption_edges = video.get('edge_media_to_caption', {}).get('edges', [])
                            if caption_edges and caption_edges[0].get('node', {}).get('text'):
                                caption = caption_edges[0]['node']['text']
                                short_caption = caption[:80] + "..." if len(caption) > 80 else caption
                                print(f"     💬 Açıklama: {short_caption}")
                        
                        return True
                    else:
                        print("❌ Video/Reels bulunamadı")
                        
                        # Alternatif: Tüm gönderileri göster (debug için)
                        if edges:
                            print(f"\n📊 Toplam {len(edges)} gönderi var, ancak hiçbiri video değil")
                            print("İlk 3 gönderinin türü:")
                            for i, edge in enumerate(edges[:3], 1):
                                node = edge.get('node', {})
                                print(f"  {i}. Video: {node.get('is_video', False)}, Shortcode: {node.get('shortcode', 'N/A')}")
                        
                        return False
                else:
                    print("❌ Kullanıcı verisi bulunamadı")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return False
        else:
            print(f"❌ API hatası: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

def test_profile_info_http(profile_url):
    """Instagram API ile profil bilgilerini test eder"""
    print("\n" + "="*60)
    print("👤 İNSTAGRAM API PROFİL BİLGİ TESTİ")
    print("="*60)
    
    try:
        import requests
        import json
        
        # Username çıkar
        username = profile_url.split('/')[-1] or profile_url.split('/')[-2]
        print(f"🔍 Test kullanıcı: {username}")
        
        # Instagram API headers
        headers = {
            "x-ig-app-id": "936619743392459",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        
        # Instagram API endpoint
        print("\n🌐 Instagram API isteği gönderiliyor...")
        api_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        response = requests.get(api_url, headers=headers, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📏 Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                data = response.json()
                user_data = data.get('data', {}).get('user', {})
                
                if user_data:
                    print("✅ Instagram API isteği başarılı")
                    print(f"📝 Kullanıcı ID: {user_data.get('id', 'N/A')}")
                    print(f"📝 Tam ad: {user_data.get('full_name', 'N/A')}")
                    print(f"👥 Takipçi: {user_data.get('edge_followed_by', {}).get('count', 'N/A')}")
                    print(f"👤 Takip edilen: {user_data.get('edge_follow', {}).get('count', 'N/A')}")
                    print(f"📊 Gönderi sayısı: {user_data.get('edge_owner_to_timeline_media', {}).get('count', 'N/A')}")
                    print(f"🔒 Gizli hesap: {'Evet' if user_data.get('is_private', False) else 'Hayır'}")
                    print(f"✅ Doğrulanmış: {'Evet' if user_data.get('is_verified', False) else 'Hayır'}")
                    return True
                else:
                    print("❌ Kullanıcı verisi bulunamadı")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse hatası: {e}")
                return False
        else:
            print(f"❌ API hatası: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {str(e)}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🚀 INSTAGRAM PROFİL HTTP İNDİRME TEST BAŞLADI")
    print("="*80)
    
    # Test profil URL'si - buraya test etmek istediğiniz profil URL'sini girin
    test_profile_url = "https://www.instagram.com/smtozkn06/"  # Örnek profil
    
    print(f"🎯 Test Profili: {test_profile_url}")
    print(f"⏰ Test Zamanı: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test sonuçları
    results = {
        'profile_info_http': False,
        'profile_posts_http': False,
        'profile_reels_http': False,
        'profile_posts_instagrapi': False,
        'profile_reels_instagrapi': False
    }
    
    # HTTP Testleri
    print("\n🌐 HTTP TESTLERİ BAŞLADI")
    print("="*50)
    
    # 1. Profil bilgi testi (HTTP)
    results['profile_info_http'] = test_profile_info_http(test_profile_url)
    time.sleep(2)  # API rate limit için bekle
    
    # 2. Profil gönderileri testi (HTTP)
    results['profile_posts_http'] = test_profile_posts_http(test_profile_url, max_posts=3)
    time.sleep(2)  # API rate limit için bekle
    
    # 3. Profil reels testi (HTTP)
    results['profile_reels_http'] = test_profile_reels_http(test_profile_url, max_reels=3)
    time.sleep(3)  # API rate limit için bekle
    
    # Instagrapi Testleri
    print("\n📚 INSTAGRAPI TESTLERİ BAŞLADI")
    print("="*50)
    
    # 4. Profil gönderileri testi (Instagrapi)
    results['profile_posts_instagrapi'] = test_instagrapi_profile_posts(test_profile_url, max_posts=3)
    time.sleep(2)  # API rate limit için bekle
    
    # 5. Profil reels testi (Instagrapi)
    results['profile_reels_instagrapi'] = test_instagrapi_profile_reels(test_profile_url, max_reels=3)
    
    # Sonuçları özetle
    print("\n" + "="*80)
    print("📊 TEST SONUÇLARI")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"  {test_name.upper()}: {status}")
    
    success_count = sum(results.values())
    total_tests = len(results)
    
    print(f"\n🎯 Genel Başarı Oranı: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 Tüm testler başarılı! HTTP indirme sistemi çalışıyor.")
    elif success_count > 0:
        print("⚠️ Bazı testler başarılı. Sistem kısmen çalışıyor.")
    else:
        print("💥 Hiçbir test başarılı değil. Sistem çalışmıyor.")
    
    print("\n" + "="*80)
    print("🏁 TEST TAMAMLANDI")
    print("="*80)

if __name__ == "__main__":
    main()