from bs4 import BeautifulSoup
import requests
from pymongo import MongoClient
from datetime import datetime

# Connexion à MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_scraper']
articles_collection = db['articles']

def get_article_titles(page_url):
    """Récupère les titres, images, résumés et dates des articles"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(page_url, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        articles_data = {
            'page_url': page_url,
            'scraping_date': datetime.now().strftime('%Y-%m-%d'),
            'articles': {}
        }
        
        for index, article in enumerate(soup.find_all('article'), 1):
            article_data = {}
            
            # Extraction du titre
            h3_title = article.find('h3', class_='entry-title')
            if h3_title:
                article_data['title'] = h3_title.text.strip()
            
            # Extraction du résumé
            summary_container = (
                article.find(class_='article-hat t-quote pb-md-8 pb-5') or 
                article.find(class_=lambda c: c and 'article-hat' in c)
            )
            if summary_container:
                summary_text = summary_container.find('p')
                article_data['summary'] = (summary_text.text if summary_text else summary_container.text).strip()
            
            # Extraction de la date
            date_tag = article.find('time', class_='entry-date published updated')
            if date_tag and date_tag.has_attr('datetime'):
                try:
                    date_str = date_tag['datetime']
                    date = datetime.strptime(date_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                    article_data['publish_date'] = date.strftime('%Y-%m-%d')
                except ValueError:
                    article_data['publish_date'] = date_tag.text.strip()
            
            # Extraction de l'auteur - méthode unique
            author_link = article.find('a', class_='author-name')
            article_data['author'] = author_link.text.strip() if author_link else "Auteur inconnu"
            print(f"Auteur trouvé: {article_data['author']}")
            
            # Extraction des images
            images = {}
            for img_index, img in enumerate(article.find_all('img'), 1):
                img_src = img.get('src') or img.get('data-src', '')
                if img_src:
                    images[f'image_{img_index}'] = {
                        'url': img_src,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    }
            article_data['images'] = images
            
            articles_data['articles'][f'article_{index}'] = article_data
            print(f"Article {index} traité: {article_data.get('title', 'Sans titre')}")
        
        # Sauvegarde dans MongoDB
        if articles_data['articles']:
            articles_collection.insert_one(articles_data)
            print(f"Sauvegardé {len(articles_data['articles'])} articles dans MongoDB")
        
        return articles_data
            
    except Exception as e:
        print(f"Erreur: {e}")
        return {}

if __name__ == "__main__":
    try:
        base_url = "https://www.blogdumoderateur.com/web/"
        print("Début du scraping des titres...")
        result = get_article_titles(base_url)
        print(f"Total des articles trouvés: {len(result.get('articles', {}))}")
        
    except Exception as e:
        print(f"Erreur critique: {e}")
    finally:
        client.close()