import random
import os
import re
import wikipediaapi
import requests
import json
from mastodon import Mastodon
from unidecode import unidecode
import csv
from time import sleep
import urllib.request

IMG_REQUEST = {
    'cs': 'http://cs.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles=',
    'en': 'http://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles='
}

mastodon_secrets = {
    'cs': os.environ['TOKEN_CS'],
    'en': os.environ['TOKEN_EN']
}

def get_categories(file_path,lang):
    categories = {}
    with open(file_path, 'r') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            categories[row['cat_'+lang]] = row['icon']
    del categories['']
    return categories

def get_page(category,lang):
    wiki = wikipediaapi.Wikipedia(
        "planetary-ecologist/0.1.0 (+https://github.com/kalab-oto/planetary-ecologist)",
        lang)
    cat_page = wiki.page(f"Category:{category}")
    articles = list(cat_page.categorymembers.values())
    random_article = random.choice(articles)

    return random_article

def get_text(page,maxchar):
    text = page.summary
    text = re.sub(r"[\(\[].*?[\)\]]", "", text)
    text = re.sub(r"\s+([,.])", r"\1", text.strip())
    text = re.sub(r"\s+", " ", text)
    text = text[:maxchar-6].strip() 
    # p_index = text.rfind(".") # trim the text to the last period. This will be nicer but results in problem with abbreviated words ending with period
    # text = text[:p_index + 1]
    if not text.endswith('.'):
        text = text[:-3]+'...'
    # not_ending = ('tzv.', 'např.', 'm n. m.','tj.','etc.')
    return text

def get_hashtags(page,lang):
    hash_title = re.sub(r"\([^)]*\)", "", page.title)
    hash_title = "#"+hash_title.title().replace(' ', '')

    hash_cats = list(page.categories.keys())
    hash_cats = [x.lower() for x in hash_cats]
    remove_cats = [
        "articles",
        "cs1",
        "wikidata",
        "wikipedia",
        "accuracy disputes",
        "commons category",
        "use mdy dates",
        "use dmy dates",
        "webarchive",
        "engvarb",
        "short description",
        " stubs",
        "narození",
        "úmrtí",
        "muži",
        "ženy",
        "kategorie:monitoring",
        "kategorie:údržba",
        "kategorie:pahýly"
        ] 
    filter_cond = lambda item: all(x not in item for x in remove_cats)
    hash_cats = list(filter(filter_cond, hash_cats))
    hash_cats = [item for item in hash_cats if len(item) <= 35]

    hash_cats = " ".join(hash_cats)
    hash_cats = re.sub("kategorie:|category:", "#", hash_cats)
    hash_cats = hash_cats.title().replace(' ', '')
    hash_cats = re.sub("#", " #", hash_cats)

    hash_cats = hash_cats.split()
    if hash_title in hash_cats:
        hash_cats.remove(hash_title)
    sorted_list = sorted(hash_cats, key=len)
    hash_cats_list = sorted_list[:5]
    hash_cats = " ".join(hash_cats_list)

    hashtags = unidecode(hash_title + ' ' +hash_cats)
    hashtags = re.sub(r"[\(\[].*?[\)\]]", "", hashtags)
    hashtags = re.sub(r"[^\w#\s]", "", hashtags)
    return hashtags

def get_url(page,lang):
    if lang == 'cs':
        url = 'https://cs.wikipedia.org/wiki/'+'_'.join(page.title.split())
    else:
        url = 'https://en.wikipedia.org/wiki/'+'_'.join(page.title.split())
    return url

def get_image(page,lang):
    try:
        title = page.title
        response = requests.get(IMG_REQUEST[lang]+title)
        json_data = json.loads(response.text)
        img_link = list(json_data['query']['pages'].values())[0]['original']['source']
        if img_link.endswith((".svg",".SVG")):
            raise ValueError('image is SVG')
        response = urllib.request.urlretrieve(img_link)
        return response[0]
    except:
        return None

def main():
    for l in ('en','cs'):
        for x in range(0, 10):
            try:
                categories = get_categories("categories.csv",l)
                random_category = random.choice(list(categories.keys()))
                random_page = get_page(random_category,l)
                while random_page.title.startswith(('Kategorie:','Category:')):   
                    random_page = get_page(random_category,l)
            
                post_head = f"{random_page.title} ({random_category} {categories[random_category]})"

                post_url = get_url(random_page,l)
                post_hashtags = get_hashtags(random_page,l)
                len_post = len(post_head)+len(post_url)+len(post_hashtags)
                post_body = get_text(random_page,500-len_post)

                post_content = f"{post_head}\n\n{post_body}\n\n{post_url}\n\n{post_hashtags}"
                wiki_image = get_image(random_page,l)

                mastodon = Mastodon(
                    access_token = mastodon_secrets[l],
                    api_base_url = 'https://mastodon.social/'
                )
                if wiki_image is None:
                    mastodon.status_post(post_content, language = l)
                else:
                   media = mastodon.media_post(wiki_image)
                   mastodon.status_post(post_content, media_ids= media, language = l)
                str_error = None
            except Exception as e:
                str_error = e
                pass
            if str_error:
                sleep(30)
            else:
                break

if __name__ == "__main__":
    main()
