import os
import json
import urllib
import requests


class Scraper:
    def __init__(self, config, image_urls=None):
        self.config = config
        self.image_urls = image_urls if image_urls else []

    def setConfig(self, config):
        # Set config for bookmarks (next page)
        self.config = config

    def download_images(self, output_path) -> int:
        # prev get links
        results = self.get_urls()
        try:
            os.makedirs(output_path)
            print(f"Directory {output_path} Created")
        except FileExistsError:
            pass

        number = 0
        listdir = os.listdir(output_path)
        if results != None:
            for i in results:
                file_name = i.split("/")[-1]
                if file_name not in listdir:
                    try:
                        number += 1
                        print("Downloading", i)
                        urllib.request.urlretrieve(
                            i, os.path.join(output_path, file_name))
                    except Exception as e:
                        print("Error:", e)

        return number

    def get_urls(self) -> list:
        SOURCE_URL = self.config.source_url,
        DATA = self.config.image_data,
        URL_CONSTANT = self.config.search_url

        headers = {
            "x-pinterest-pws-handler": "www/search/[scope].js",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            r = requests.get(URL_CONSTANT, params={
                             "source_url": SOURCE_URL, "data": DATA}, headers=headers)
            print(f"API Yanıt Kodu: {r.status_code}")
            
            if r.status_code != 200:
                print(f"API Hatası: {r.status_code} - {r.text[:200]}")
                return []
                
            jsonData = json.loads(r.content)
            
            if "resource_response" not in jsonData:
                print("API yanıtında 'resource_response' bulunamadı")
                print(f"Yanıt anahtarları: {list(jsonData.keys())}")
                return []
                
            resource_response = jsonData["resource_response"]
            
            if "data" not in resource_response:
                print("API yanıtında 'data' bulunamadı")
                return []
                
            data = resource_response["data"]
            
            if "results" not in data:
                print("API yanıtında 'results' bulunamadı")
                return []
                
            results = data["results"]
            print(f"Bulunan sonuç sayısı: {len(results)}")

            for i in results:
                try:
                    self.image_urls.append(
                        i["objects"][0]["cover_images"][0]["originals"]["url"])
                except Exception as e:
                    self.URL = None
                    self.search(i)
                    if self.URL != None:
                        self.image_urls.append(self.URL)

            print(f"{len(self.image_urls)} resim URL'si bulundu")
            
            if len(self.image_urls) > 0:
                return self.image_urls[0:min(len(self.image_urls), int(self.config.file_length))]
            else:
                return []
                
        except Exception as e:
            print(f"API isteği hatası: {e}")
            return []

    def search(self, d):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict):
                    if k == "orig":
                        self.URL = v["url"]
                    else:
                        self.search(v)
                elif isinstance(v, list):
                    for item in v:
                        self.search(item)
