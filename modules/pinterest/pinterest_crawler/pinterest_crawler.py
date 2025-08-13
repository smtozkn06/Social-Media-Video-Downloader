import os
import random
from itertools import combinations
from .scraper import Scraper
from .config import Config


class PinterestCrawler:
    def __init__(self, output_dir_path="./io/output"):
        self.output_dir_path = output_dir_path
        os.makedirs(self.output_dir_path, exist_ok=True)
        
    def __call__(self, keywords, number_of_words=2, max_images_per_keyword=100, max_keywords=5):
        keywords_list = self.create_keywords_list(keywords)
        print("Start crawling...")
        self.counter = 0
        keyword_count = 0
        
        if len(keywords_list) == 1:
            number_of_words = 1
            
        for item in combinations(keywords_list, number_of_words):
            if self.counter >= 4 or keyword_count >= max_keywords:
                print(f"Arama limiti aşıldı. Toplam {keyword_count} kelime işlendi.")
                break

            keyword = " ".join(item)
            print(f"Aranıyor: {keyword}")
            keyword_count += 1
            
            # Her kelime için maksimum sayfa sayısı
            page_count = 0
            max_pages = 3  # Her kelime için maksimum 3 sayfa
            
            while page_count < max_pages:
                configs = Config(
                    search_keywords=keyword,  # Search word
                    # Kelime başına indirme limiti
                    file_lengths=max_images_per_keyword,
                    # image quality (default = "orig")
                    image_quality="originals",
                    # next page data (default= "")
                    bookmarks="",
                    scroll=page_count * 1000)  # Her sayfa için farklı scroll değeri

                downloaded_count = self.download(configs, self.output_dir_path)
                page_count += 1
                
                if downloaded_count == 0:
                    print(f"'{keyword}' için daha fazla resim bulunamadı.")
                    break
                else:
                    print(f"'{keyword}' için {downloaded_count} resim indirildi (Sayfa {page_count})")
                    
                # Toplam indirilen resim sayısını kontrol et
                total_images = len(os.listdir(self.output_dir_path))
                if total_images >= 500:  # Maksimum toplam resim sayısı
                    print(f"Maksimum resim sayısına ulaşıldı: {total_images}")
                    return
        
        images = os.listdir(self.output_dir_path)
        print(f"{len(images)} images saved in directory: {self.output_dir_path}")

    def create_keywords_list(self, keywords):
        keywords_list = []
        for keyword in keywords:
            if os.path.isfile(keyword):
                file = open(keyword, "r", encoding="utf-8")
                keywords_list += [keyword.strip() for keyword in file.read().split('\n')]
            elif isinstance(keyword, str):
                keywords_list.append(keyword)
        random.shuffle(keywords_list)
        return keywords_list

    def download(self, configs, output_dir_path):
        number = Scraper(configs).download_images(output_dir_path)
        if number == 0:
            self.counter += 1
            return 0
        else:
            self.counter = 0
            return number
