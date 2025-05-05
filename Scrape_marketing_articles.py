from bs4 import BeautifulSoup
import requests
from pymongo import MongoClient
from datetime import datetime

# Connexion à MongoDB - utilisation d'une collection différente pour le marketing
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_scraper']
articles_collection = db['articles']

def get_marketing_articles(page_url):
    """Récupère les articles de la section marketing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(page_url, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        articles_data = {
            'page_url': page_url,
            'scraping_date': datetime.now().strftime('%Y-%m-%d'),
            'type': 'marketing',  # Ajout du type
            'category': 'marketing',
            'articles': {}
        }
        
        # Cibler spécifiquement les articles de marketing
        for index, article in enumerate(soup.find_all('article', class_='post'), 1):
            article_data = {'category': 'marketing'}
            
            # Extraction du titre avec vérification supplémentaire pour les articles sponsorisés
            h3_title = article.find('h3', class_='entry-title')
            if h3_title:
                title_text = h3_title.text.strip()
                article_data['title'] = title_text
                article_data['is_sponsored'] = 'sponsorisé' in title_text.lower()
            
            # Extraction du résumé avec support des différents formats
            summary_container = (
                article.find(class_='article-hat') or 
                article.find(class_='entry-content') or
                article.find(class_='excerpt')
            )
            if summary_container:
                summary_text = summary_container.find('p')
                article_data['summary'] = (summary_text.text if summary_text else summary_container.text).strip()
            
            # Extraction de la date avec format spécifique au marketing
            date_tag = article.find('time', class_='entry-date published')
            if date_tag and date_tag.has_attr('datetime'):
                try:
                    date_str = date_tag['datetime']
                    date = datetime.strptime(date_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                    article_data['publish_date'] = date.strftime('%Y-%m-%d')
                except ValueError:
                    article_data['publish_date'] = date_tag.text.strip()
            
            # Extraction de l'auteur avec vérification du profil
            author_container = article.find('span', class_='author') or article.find('a', class_='author-name')
            if author_container:
                article_data['author'] = author_container.text.strip()
                author_link = author_container.find('a')
                if author_link:
                    article_data['author_profile'] = author_link.get('href', '')
            else:
                article_data['author'] = "Auteur inconnu"
            
            # Extraction des images avec gestion des lazy loading
            images = {}
            for img_index, img in enumerate(article.find_all('img'), 1):
                img_src = img.get('data-lazy-src') or img.get('src') or img.get('data-src', '')
                if img_src:
                    print(f"Image trouvée: {img_src}")
                    images[f'image_{img_index}'] = {
                        'url': img_src,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    }
            article_data['images'] = images
            
            # Ajout de tags spécifiques au marketing
            tags = article.find_all('a', class_='tag')
            if tags:
                article_data['tags'] = [tag.text.strip() for tag in tags]
            
            articles_data['articles'][f'article_{index}'] = article_data
            print(f"Article marketing {index} traité: {article_data.get('title', 'Sans titre')}")
        
        # Sauvegarde dans MongoDB
        if articles_data['articles']:
            articles_collection.insert_one(articles_data)
            print(f"Sauvegardé {len(articles_data['articles'])} articles marketing dans MongoDB")
        
        return articles_data
            
    except Exception as e:
        print(f"Erreur: {e}")
        return {}

if __name__ == "__main__":
    try:
        base_url = "https://www.blogdumoderateur.com/marketing/"
        print("Début du scraping des articles marketing...")
        result = get_marketing_articles(base_url)
        print(f"Total des articles marketing trouvés: {len(result.get('articles', {}))}")
        
    except Exception as e:
        print(f"Erreur critique: {e}")
    finally:
        client.close()
