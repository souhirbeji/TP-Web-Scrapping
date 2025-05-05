import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from pymongo import MongoClient
import sys

# Connexion à MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_scraper']
articles_collection = db['articles']


def scrape_article(url):
    """Scrape un article du Blog du Modérateur et le stocke dans MongoDB"""
    print(f"Scraping de l'article: {url}")
    
    # Récupération de la page
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de la récupération de la page: {e}")
        return None
    
    # Parsing HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Initialisation du dictionnaire pour stocker les données
    article_data = {
        'url': url,
        'scraped_at': datetime.now()
    }
    
    # 1. Extraction du titre
    try:
        title = soup.find('h1', class_='entry-title').text.strip()
        article_data['title'] = title
    except:
        print("Erreur: Impossible d'extraire le titre")
    
    # 2. Extraction de l'image miniature principale
    try:
        # Chercher l'élément img avec la classe wp-post-image
        thumbnail_img = soup.find('img', class_='wp-post-image')
        if thumbnail_img and 'src' in thumbnail_img.attrs:
            article_data['thumbnail'] = thumbnail_img['src']
            print(f"Image miniature trouvée: {article_data['thumbnail']}")
        else:
            print("Aucune image miniature avec classe wp-post-image trouvée")
            
        # Si aucune image trouvée, chercher dans les autres structures
        if 'thumbnail' not in article_data:
            # Chercher dans figure.article-hat-img
            thumbnail_figure = soup.find('figure', class_='article-hat-img')
            if thumbnail_figure and thumbnail_figure.find('img'):
                article_data['thumbnail'] = thumbnail_figure.find('img').get('src')
                print(f"Image miniature trouvée (figure): {article_data['thumbnail']}")
            elif thumbnail_figure and thumbnail_figure.find('a'):
                article_data['thumbnail'] = thumbnail_figure.find('a').get('href')
                print(f"Image miniature trouvée (lien): {article_data['thumbnail']}")
                
    except Exception as e:
        print(f"Erreur lors de l'extraction de l'image miniature: {e}")
    
    # 3. Extraction des catégories et sous-catégories
    try:
        # Chercher les tags comme sous-catégories
        sous_categories = [div.get_text(strip=True) for div in soup.find_all('div', class_='favtag mb-1')]
        sous_categories = list(set(sous_categories))  # Remove duplicates
        
        # Chercher dans les méta-catégories
        category_link = soup.find('a', class_='post-category')
        if category_link:
            article_data['category'] = category_link.text.strip()
            article_data['subcategory'] = category_link.text.strip()
            
        if sous_categories:
            article_data['tags'] = sous_categories
            
    except Exception as e:
        print(f"Erreur: Impossible d'extraire les catégories: {e}")
    # 4. Extraction du résumé
    try:
        # Recherche du résumé avec différentes stratégies
        summary_container = (
            soup.find(class_='article-hat t-quote pb-md-8 pb-5') or 
            soup.find(class_=lambda c: c and 'article-hat' in c)
        )
        
        if summary_container:
            # Extraire le texte du paragraphe ou du conteneur complet
            summary_text = summary_container.find('p')
            article_data['summary'] = (summary_text.text if summary_text else summary_container.text).strip()
            
            # Afficher un aperçu du résumé
            preview = article_data['summary'][:50] + "..." if len(article_data['summary']) > 50 else article_data['summary']
            print(f"Résumé trouvé: {preview}")
        else:
            print("Aucun résumé trouvé")
            article_data['summary'] = ""
            
    except Exception as e:
        print(f"Erreur lors de l'extraction du résumé: {e}")
        article_data['summary'] = ""

    # 5. Extraction de la date de publication
    try:
        date_tag = soup.find('time', class_='entry-date published updated')
        
        if date_tag and date_tag.has_attr('datetime'):
            date_str = date_tag['datetime']
            try:
                # Format ISO avec fuseau horaire
                date = datetime.strptime(date_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                article_data['publish_date'] = date.strftime('%Y-%m-%d')
                print(f"Date publiée: {article_data['publish_date']}")
            except:
                # En cas d'échec, conserver la date brute
                article_data['publish_date'] = date_str
        elif date_tag:
            article_data['publish_date'] = date_tag.text.strip()
    except Exception as e:
        print(f"Erreur date: {e}")
    
    # 6. Extraction de l'auteur
    try:
        author_img = soup.select_one('div.meta-picture img')
        author = author_img['alt'].strip() if author_img and author_img.has_attr('alt') else "Auteur inconnu"
        article_data['author'] = author  # Ajoutez cette ligne
        print(f"Auteur trouvé: {author}")
    except Exception as e:
        author = "Auteur inconnu"
        article_data['author'] = author  # Ajoutez aussi cette ligne
        print(f"Erreur lors de l'extraction de l'auteur: {e}")
    
    # 7. Extraction des images avec leurs descriptions
    try:
        images_dict = {}
        seen_urls = set()  # Pour éviter les doublons
        
        # Trouver toutes les images de la page
        all_images = soup.find_all('img')
        
        for index, img in enumerate(all_images, 1):
            img_src = img.get('src') or img.get('data-src', '')
            
            # Vérifier si l'URL est valide et pas déjà vue
            if not img_src or img_src in seen_urls:
                continue
                
            seen_urls.add(img_src)
            
            # Récupérer toutes les informations possibles sur l'image
            description = {
                'alt_text': img.get('alt', ''),
                'title': img.get('title', ''),
                'class': img.get('class', []),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            }

            # Chercher le contexte de l'image
            parent_figure = img.find_parent('figure')
            if parent_figure:
                figcaption = parent_figure.find('figcaption')
                if figcaption:
                    description['caption'] = figcaption.text.strip()
                    
            # Chercher si l'image est dans un lien
            parent_link = img.find_parent('a')
            if parent_link:
                description['link_url'] = parent_link.get('href', '')
                description['link_title'] = parent_link.get('title', '')

            # Ajouter l'image au dictionnaire
            images_dict[str(index)] = {
                'url': img_src,
                'description': description
                # Suppression de 'location'
            }

        if images_dict:
            article_data['images'] = images_dict
            print(f"Nombre total d'images trouvées: {len(images_dict)}")
            # Suppression des statistiques de localisation
    except Exception as e:
        print(f"Erreur lors de l'extraction des images: {e}")
        article_data['images'] = {}

    # Enregistrer dans MongoDB
    try:
        # Vérifier si l'article existe déjà
        existing = articles_collection.find_one({'url': url})
        
        if existing:
            # Mise à jour et suppression du champ ordered_lists s'il existe
            result = articles_collection.update_one(
                {'_id': existing['_id']},
                {
                    '$set': article_data,
                    '$unset': {'ordered_lists': ""}  # Supprime le champ ordered_lists
                }
            )
            print(f"Article mis à jour dans MongoDB: {result.modified_count} document modifié")
            return existing['_id']
        else:
            # Insertion
            result = articles_collection.insert_one(article_data)
            print(f"Article enregistré dans MongoDB avec l'ID: {result.inserted_id}")
            return result.inserted_id
    except Exception as e:
        print(f"Erreur lors de l'enregistrement dans MongoDB: {e}")
    
    return article_data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Pour scraper un article: python scraper.py scrape URL_ARTICLE")
        print("  Pour rechercher par catégorie: python scraper.py search CATEGORIE [SOUS_CATEGORIE]")
        print("  Pour lister les sous-catégories: python scraper.py subcategories URL_PAGE")
    else:
        command = sys.argv[1]
        
        if command == "scrape" and len(sys.argv) > 2:
            scrape_article(sys.argv[2])
        
        elif command == "search":
            category = None
            subcategory = None
            
            if len(sys.argv) > 2:
                category = sys.argv[2]
            
            if len(sys.argv) > 3:
                subcategory = sys.argv[3]
            
            get_articles_by_category(category, subcategory)
        
        elif command == "subcategories" and len(sys.argv) > 2:
            try:
                response = requests.get(sys.argv[2])
                soup = BeautifulSoup(response.content, 'html.parser')
                subcategories = get_subcategories(soup)
                print("\n--- Sous-catégories disponibles ---")
                for subcat in subcategories:
                    print(f"Nom: {subcat['name']}")
                    print(f"URL: {subcat['url']}")
                    print(f"Catégorie parent: {subcat['parent_category']}")
                    print("------------------------------")
            except Exception as e:
                print(f"Erreur lors de la récupération des sous-catégories: {e}")
        
        else:
            print("Commande non reconnue.")
            print("Usage:")
            print("  Pour scraper un article: python scraper.py scrape URL_ARTICLE")
            print("  Pour rechercher par catégorie: python scraper.py search CATEGORIE [SOUS_CATEGORIE]")
            print("  Pour lister les sous-catégories: python scraper.py subcategories URL_PAGE")
