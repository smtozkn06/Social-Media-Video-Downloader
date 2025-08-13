import re
import json
from datetime import datetime
from gallery_dl.extractor import twitter

def get_metadata(username, auth_token, timeline_type="timeline", batch_size=0, page=0, media_type="all"):
    url = f"https://x.com/{username}/{timeline_type}"
    
    if timeline_type == "media":
        extractor_class = twitter.TwitterMediaExtractor
    elif timeline_type == "tweets":
        extractor_class = twitter.TwitterTweetsExtractor
    elif timeline_type == "with_replies":
        extractor_class = twitter.TwitterRepliesExtractor
    else:
        extractor_class = twitter.TwitterTimelineExtractor
    
    match = re.match(extractor_class.pattern, url)
    if not match:
        raise ValueError(f"Invalid URL for {timeline_type}: {url}")
    
    extractor = extractor_class(match)
    
    config_dict = {
        "cookies": {
            "auth_token": auth_token
        },
        "extractor": {
            "twitter": {
                "include": "media",
                "retweets": False,
                "replies": False,
                "quoted": False
            }
        }
    }
    
    # Büyük batch size ayarla - tüm medyaları çekmek için
    if batch_size and batch_size > 1000:
        # Çok büyük batch size için özel ayarlar
        config_dict["extractor"]["twitter"]["count"] = -1  # Sınırsız
    elif batch_size > 0:
        config_dict["extractor"]["twitter"]["count"] = batch_size
    
    def config_getter(key, default=None):
        if key == "extractor":
            return config_dict.get("extractor", {})
        return config_dict.get(key, default)
    
    extractor.config = config_getter
    
    try:
        extractor.initialize()
        
        api = twitter.TwitterAPI(extractor)
        try:
            if username.startswith("id:"):
                user = api.user_by_rest_id(username[3:])
            else:
                user = api.user_by_screen_name(username)
                
            if "legacy" in user and user["legacy"].get("withheld_scope"):
                raise ValueError("withheld")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "withheld" in error_msg or (hasattr(e, "response") and "withheld" in str(e.response.text).lower()):
                raise ValueError("withheld")
            raise
        
        structured_output = {
            'account_info': {},
            'total_urls': 0,
            'timeline': []
        }
        
        iterator = iter(extractor)
        
        # Cursor tabanlı sayfalama için page parametresini kullanma
        # Twitter API'si otomatik olarak cursor ile ilerleyecek
        
        new_timeline_entries = []
        
        items_to_fetch = batch_size if batch_size > 0 else float('inf')
        items_fetched = 0
        
        try:
            while items_fetched < items_to_fetch:
                item = next(iterator)
                items_fetched += 1
                
                if isinstance(item, tuple) and len(item) >= 3:
                    media_url = item[1]
                    tweet_data = item[2]
                    
                    if not structured_output['account_info'] and 'user' in tweet_data:
                        user = tweet_data['user']
                        user_date = user.get('date', '')
                        if isinstance(user_date, datetime):
                            user_date = user_date.strftime("%Y-%m-%d %H:%M:%S")
                        
                        structured_output['account_info'] = {
                            'name': user.get('name', ''),
                            'nick': user.get('nick', ''),
                            'date': user_date,
                            'followers_count': user.get('followers_count', 0),
                            'friends_count': user.get('friends_count', 0),
                            'profile_image': user.get('profile_image', ''),
                            'statuses_count': user.get('statuses_count', 0)
                        }
                    
                    if 'pbs.twimg.com' in media_url or 'video.twimg.com' in media_url:
                        tweet_date = tweet_data.get('date', datetime.now())
                        if isinstance(tweet_date, datetime):
                            tweet_date = tweet_date.strftime("%Y-%m-%d %H:%M:%S")
                        
                        timeline_entry = {
                            'url': media_url,
                            'date': tweet_date,
                            'tweet_id': tweet_data.get('tweet_id', 0),
                        }
                        
                        if 'type' in tweet_data:
                            timeline_entry['type'] = tweet_data['type']
                        
                        if media_type == 'all' or (
                            (media_type == 'image' and 'pbs.twimg.com' in media_url and tweet_data.get('type') == 'photo') or
                            (media_type == 'video' and 'video.twimg.com' in media_url and tweet_data.get('type') == 'video') or
                            (media_type == 'gif' and 'video.twimg.com' in media_url and tweet_data.get('type') == 'animated_gif')
                        ):
                            new_timeline_entries.append(timeline_entry)
                            structured_output['total_urls'] += 1
        except StopIteration:
            pass
        
        structured_output['timeline'].extend(new_timeline_entries)
        
        cursor_info = None
        if hasattr(extractor, '_cursor') and extractor._cursor:
            cursor_info = extractor._cursor
        
        # has_more kontrolü: eğer StopIteration ile çıktıysak, daha fazla veri yok
        # eğer batch_size kadar veri çektiyse ve StopIteration olmadıysa, daha fazla veri olabilir
        has_more_data = False
        if batch_size > 0:
            # Eğer tam batch_size kadar çektiyse ve StopIteration olmadıysa, daha fazla veri olabilir
            has_more_data = items_fetched == batch_size
            # Ek kontrol: iterator'da daha fazla veri var mı?
            try:
                # Bir sonraki item'ı kontrol et ama consume etme
                test_item = next(iterator)
                has_more_data = True
                # Bu item'ı geri koy (mümkün değil, ama en azından has_more=True olarak işaretle)
            except StopIteration:
                has_more_data = False
        
        structured_output['metadata'] = {
            "new_entries": len(new_timeline_entries),
            "page": page,
            "batch_size": batch_size,
            "has_more": has_more_data,
            "cursor": cursor_info,
            "items_fetched": items_fetched
        }
        
        if not structured_output['account_info']:
            raise ValueError("Failed to fetch account information. Please check the username and auth token.")
        
        return structured_output
    
    except Exception as e:
        error_msg = str(e).lower()
        if "withheld" in error_msg or e.__class__.__name__ == "ValueError" and str(e) == "withheld":
            return {"error": "To download withheld accounts, use this userscript version: https://www.patreon.com/exyezed"}
        elif "requested user could not be found" in error_msg or "user not found" in error_msg:
            return {"error": "Kullanıcı bulunamadı. Lütfen kullanıcı adının doğru olduğundan emin olun."}
        elif "unauthorized" in error_msg or "forbidden" in error_msg:
            return {"error": "Erişim reddedildi. Auth token'ınızın geçerli olduğundan emin olun."}
        else:
            error_str = str(e)
            if error_str == "None":
                return {"error": "Kimlik doğrulama başarısız. Auth token'ınızın geçerli ve süresi dolmamış olduğundan emin olun."}
            else:
                return {"error": error_str}

def main():
    username = ""
    auth_token = ""
    timeline_type = "media"
    batch_size = 100
    page = 0
    media_type = "all"
    
    try:
        data = get_metadata(
            username=username,
            auth_token=auth_token,
            timeline_type=timeline_type,
            batch_size=batch_size,
            page=page,
            media_type=media_type
        )
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        error_str = str(e)
        if error_str == "None":
            print(json.dumps({"error": "Failed to authenticate. Please verify your auth token is valid and not expired."}, ensure_ascii=False))
        else:
            print(json.dumps({"error": error_str}, ensure_ascii=False))

if __name__ == '__main__':
    main()