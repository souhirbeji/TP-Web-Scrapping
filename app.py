from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import re
import subprocess
import os
from Scrape_web_articles import get_article_titles, articles_collection

app = Flask(__name__, template_folder='templates', static_folder='static')

# Connexion à MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_scraper']
articles_collection = db['articles']

@app.route('/')
def home():
    # Récupérer les derniers articles de MongoDB
    latest_articles = articles_collection.find().sort('scraping_date', -1).limit(1)
    latest_data = next(latest_articles, None)
    return render_template('index.html', data=latest_data)

@app.route('/scrape')
def scrape():
    # Déclencher un nouveau scraping
    base_url = "https://www.blogdumoderateur.com/web/"
    result = get_article_titles(base_url)
    return render_template('index.html', data=result)

@app.route('/search')
def search():
    # Récupérer les paramètres de recherche
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    author = request.args.get('author', '')
    category = request.args.get('category', '')
    subcategory = request.args.get('subcategory', '')
    title_query = request.args.get('title', '')
    
    # Construire la requête MongoDB
    query = {}
    
    if start_date and end_date:
        query['publish_date'] = {
            '$gte': start_date,
            '$lte': end_date
        }
    elif start_date:
        query['publish_date'] = {'$gte': start_date}
    elif end_date:
        query['publish_date'] = {'$lte': end_date}
    
    if author and author != 'all':
        query['author'] = author
    
    if category and category != 'all':
        query['category'] = category
    
    if subcategory and subcategory != 'all':
        query['subcategory'] = subcategory
    
    if title_query:
        query['title'] = {'$regex': title_query, '$options': 'i'}
    
    # Exécuter la requête
    articles = list(articles_collection.find(query).sort('publish_date', -1))
    
    # Convertir les _id en str pour la sérialisation JSON
    for article in articles:
        article['_id'] = str(article['_id'])
        # Formatage des dates pour l'affichage
        if 'scraped_at' in article and isinstance(article['scraped_at'], datetime):
            article['scraped_at'] = article['scraped_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'articles': articles})

@app.route('/article/<article_id>')
def article_detail(article_id):
    # Récupérer l'article par son ID
    from bson.objectid import ObjectId
    article = articles_collection.find_one({'_id': ObjectId(article_id)})
    
    if article:
        article['_id'] = str(article['_id'])
        if 'scraped_at' in article and isinstance(article['scraped_at'], datetime):
            article['scraped_at'] = article['scraped_at'].strftime('%Y-%m-%d %H:%M:%S')
        return render_template('article_detail.html', article=article)
    else:
        return "Article non trouvé", 404

@app.route('/scrape', methods=['POST'])
def scrape_new_article():
    url = request.form.get('article_url', '')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Exécuter le script de scraping
    try:
        result = subprocess.run(
            ['python', 'Scraper.py', 'scrape', url], 
            capture_output=True, 
            text=True,
            check=True
        )
        return jsonify({
            'success': True,
            'message': 'Article scrapé avec succès',
            'output': result.stdout
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': 'Erreur lors du scraping',
            'error': e.stderr
        }), 500

@app.route('/categories')
def get_categories():
    # Récupérer toutes les catégories et sous-catégories
    categories = articles_collection.distinct('category')
    subcategories_by_cat = {}
    
    for cat in categories:
        if cat:  # Vérifier que la catégorie n'est pas None ou vide
            subcats = articles_collection.distinct('subcategory', {'category': cat})
            subcategories_by_cat[cat] = [s for s in subcats if s]
    
    return jsonify({
        'categories': categories,
        'subcategories': subcategories_by_cat
    })

if __name__ == '__main__':
    app.run(debug=True)
