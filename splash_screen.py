import flet as ft
from math import pi
import time
import threading
from translations import Translations

def show_splash_screen(page, on_complete_callback=None, language="tr"):
    """Modern sosyal medya temalı splash screen göster"""
    # Çeviri sistemi
    translations = Translations()
    translations.set_language(language)
    
    def get_text(key):
        return translations.get_text(key)
    
    # Dil değiştirme fonksiyonu
    def change_language(new_language):
        translations.set_language(new_language)
        # Metinleri güncelle
        title_text.value = get_text("splash_title")
        subtitle_text.value = get_text("splash_subtitle")
        progress_text.value = get_text("splash_loading")
        page.update()
    page.title = "Social Media Video Downloader"
    page.window.width = 1920
    page.window.height = 1080
    page.window.resizable = True
    page.window.maximizable = True
    page.window.minimizable = True
    page.window.closable = True
    page.window.center()
    page.window.title_bar_hidden = False
    page.window.title_bar_buttons_hidden = False
    page.bgcolor = ft.Colors.WHITE
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Ana container - beyaz arka plan
    main_container = ft.Container(
        width=1920,
        height=1080,
        bgcolor=ft.Colors.WHITE,
        border_radius=0,
        padding=50,
        # Başlangıçta görünmez
        opacity=0,
        animate_opacity=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
    )
    
    # Modern logo container - beyaz tema
    logo_container = ft.Container(
        content=ft.Stack([
            # Glow efekti
            ft.Container(
                width=180,
                height=180,
                border_radius=90,
                bgcolor=ft.Colors.BLUE_50,
                border=ft.border.all(2, ft.Colors.BLUE_200),
            ),
            # Orta çember
            ft.Container(
                width=160,
                height=160,
                border_radius=80,
                bgcolor=ft.Colors.BLUE_100,
                border=ft.border.all(2, ft.Colors.BLUE_300),
                left=10,
                top=10,
            ),
            # Ana logo
            ft.Container(
                content=ft.Text(
                    "📱",
                    size=70,
                ),
                width=140,
                height=140,
                border_radius=70,
                bgcolor=ft.Colors.BLUE_600,
                alignment=ft.alignment.center,
                left=20,
                top=20,
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=15,
                    color=ft.Colors.BLUE_200,
                ),
            ),
        ]),
        width=180,
        height=180,
        # Başlangıçta küçük
        scale=ft.Scale(0.2),
        animate_scale=ft.Animation(1000, ft.AnimationCurve.BOUNCE_OUT),
        # Dönen animasyon
        rotate=ft.Rotate(0, alignment=ft.alignment.center),
        animate_rotation=ft.Animation(3000, ft.AnimationCurve.LINEAR),
    )
    
    # Modern başlık - mavi renk
    title_text = ft.Text(
        get_text("splash_title"),
        size=36,
        weight=ft.FontWeight.W_900,
        color=ft.Colors.BLUE_600,
        text_align=ft.TextAlign.CENTER,
        # Başlangıçta görünmez ve yukarıda
        opacity=0,
        offset=ft.Offset(0, -0.8),
        animate_opacity=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
    )
    
    # Alt başlık - gri renk
    subtitle_text = ft.Text(
        get_text("splash_subtitle"),
        size=16,
        weight=ft.FontWeight.W_500,
        color=ft.Colors.GREY_600,
        text_align=ft.TextAlign.CENTER,
        # Başlangıçta görünmez ve aşağıda
        opacity=0,
        offset=ft.Offset(0, 0.8),
        animate_opacity=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(1200, ft.AnimationCurve.EASE_OUT),
    )
    
    # Sosyal medya ikonları
    social_icons = ft.Row([
        ft.Container(
            content=ft.Text("📺", size=24),  # YouTube
            width=50,
            height=50,
            border_radius=25,
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(1, ft.Colors.GREY_300),
            alignment=ft.alignment.center,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(0.5),
            animate_scale=ft.Animation(800, ft.AnimationCurve.BOUNCE_OUT),
        ),
        ft.Container(
            content=ft.Text("🎵", size=24),  # TikTok
            width=50,
            height=50,
            border_radius=25,
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(1, ft.Colors.GREY_300),
            alignment=ft.alignment.center,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(0.5),
            animate_scale=ft.Animation(900, ft.AnimationCurve.BOUNCE_OUT),
        ),
        ft.Container(
            content=ft.Text("📷", size=24),  # Instagram
            width=50,
            height=50,
            border_radius=25,
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(1, ft.Colors.GREY_300),
            alignment=ft.alignment.center,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
            scale=ft.Scale(0.5),
            animate_scale=ft.Animation(1000, ft.AnimationCurve.BOUNCE_OUT),
        ),
        ft.Container(
             content=ft.Text("👥", size=24),  # Facebook
             width=50,
             height=50,
             border_radius=25,
             bgcolor=ft.Colors.GREY_100,
             border=ft.border.all(1, ft.Colors.GREY_300),
             alignment=ft.alignment.center,
             opacity=0,
             animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
             scale=ft.Scale(0.5),
             animate_scale=ft.Animation(1100, ft.AnimationCurve.BOUNCE_OUT),
         ),
         ft.Container(
             content=ft.Text("🐦", size=24),  # Twitter
             width=50,
             height=50,
             border_radius=25,
             bgcolor=ft.Colors.GREY_100,
             border=ft.border.all(1, ft.Colors.GREY_300),
             alignment=ft.alignment.center,
             opacity=0,
             animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
             scale=ft.Scale(0.5),
             animate_scale=ft.Animation(1200, ft.AnimationCurve.BOUNCE_OUT),
         ),
    ],
    alignment=ft.MainAxisAlignment.CENTER,
    spacing=15,
    )
    
    # Progress bar
    progress_bar = ft.ProgressBar(
        width=400,
        height=8,
        bgcolor=ft.Colors.GREY_200,
        color=ft.Colors.BLUE_600,
        border_radius=4,
        value=0,
    )
    
    # Progress text
    progress_text = ft.Text(
        get_text("splash_loading"),
        size=14,
        color=ft.Colors.GREY_600,
        text_align=ft.TextAlign.CENTER,
    )
    
    # Modern progress bar container
    progress_container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=progress_bar,
                border_radius=4,
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=15,
                    color=ft.Colors.GREY_300,
                ),
            ),
            ft.Container(height=15),
            progress_text,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0),
        margin=ft.margin.only(top=30),
        # Başlangıçta görünmez
        opacity=0,
        animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
    )
    
    # Dil seçim butonları
    language_buttons = ft.Row([
        ft.ElevatedButton(
            text="🇹🇷 Türkçe",
            on_click=lambda e: change_language("tr"),
            bgcolor=ft.Colors.BLUE_600 if language == "tr" else ft.Colors.GREY_300,
            color=ft.Colors.WHITE if language == "tr" else ft.Colors.BLACK,
            width=120,
            height=40,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
        ),
        ft.ElevatedButton(
            text="🇺🇸 English",
            on_click=lambda e: change_language("en"),
            bgcolor=ft.Colors.BLUE_600 if language == "en" else ft.Colors.GREY_300,
            color=ft.Colors.WHITE if language == "en" else ft.Colors.BLACK,
            width=120,
            height=40,
            opacity=0,
            animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
        ),
    ],
    alignment=ft.MainAxisAlignment.CENTER,
    spacing=10,
    )
    
    # Ana içerik
    splash_content = ft.Column([
        # Dil seçim butonları en üstte
        ft.Container(
            content=language_buttons,
            margin=ft.margin.only(bottom=30),
        ),
        logo_container,
        ft.Container(height=25),  # Spacer
        title_text,
        ft.Container(height=10),  # Spacer
        subtitle_text,
        ft.Container(height=20),  # Spacer
        social_icons,
        progress_container,
    ], 
    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    spacing=0)
    
    main_container.content = splash_content
    
    def start_animations():
        """Splash screen animasyonlarını başlat"""
        # 1. Ana container fade in
        main_container.opacity = 1
        
        # 2. Dil butonları animasyonu
        for button in language_buttons.controls:
            button.opacity = 1
        
        # 3. Logo animasyonları
        logo_container.scale = ft.Scale(1.0)
        logo_container.rotate.angle = pi * 2
        
        # 4. Text animasyonları
        title_text.opacity = 1
        title_text.offset = ft.Offset(0, 0)
        subtitle_text.opacity = 1
        subtitle_text.offset = ft.Offset(0, 0)
        
        # 5. Sosyal medya ikonları
        for i, icon in enumerate(social_icons.controls):
            icon.opacity = 1
            icon.scale = ft.Scale(1.0)
        
        # 6. Progress bar
        progress_container.opacity = 1
        
        page.update()
    
    # Animasyon tamamlandığında çağrılacak fonksiyon
    def on_animation_end(e):
        if on_complete_callback:
            on_complete_callback()
    
    # Modern progress bar animasyonu için
    def animate_progress():
        """Smooth progress bar animasyonu"""
        for i in range(101):
            progress_bar.value = i / 100
            progress_text.value = f"{get_text('splash_loading')} {i}%"
            page.update()
            time.sleep(0.05)  # Daha yavaş animasyon
        
        # Animasyon bitince callback çağır
        time.sleep(0.5)
        on_animation_end(None)
    
    # Progress animasyonunu başlat
    threading.Thread(target=animate_progress, daemon=True).start()
    
    # Ana container'ı sayfaya ekle
    page.add(main_container)
    page.update()
    
    # Animasyonları başlat
    start_animations()

if __name__ == "__main__":
    ft.app(target=show_splash_screen, view=ft.AppView.FLET_APP)