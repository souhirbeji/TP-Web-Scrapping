from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json
import re
import subprocess
import os
from Scrape_web_articles import get_article_titles, articles_collection

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        return json.JSONEncoder.default(self, o)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.json_encoder = JSONEncoder

# Connexion à MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_scraper']
articles_collection = db['articles']

def serialize_mongo_data(data):
    if isinstance(data, dict):
        return {key: serialize_mongo_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_mongo_data(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.strftime('%Y-%m-%d %H:%M:%S')
    return data

@app.route('/')
def home():
    # Récupérer les articles des deux types
    web_articles = list(articles_collection.find({'type': 'web'}).sort('scraping_date', -1))
    marketing_articles = list(articles_collection.find({'type': 'marketing'}).sort('scraping_date', -1))
    
    # Sérialiser les données
    web_articles = serialize_mongo_data(web_articles)
    marketing_articles = serialize_mongo_data(marketing_articles)
    
    return render_template('index.html', 
                         web_articles=web_articles,
                         marketing_articles=marketing_articles)

@app.route('/scrape/<category>')
def scrape(category):
    try:
        if category == 'web':
            from Scrape_web_articles import get_article_titles
            result = get_article_titles("https://www.blogdumoderateur.com/web/")
        elif category == 'marketing':
            from Scrape_marketing_articles import get_marketing_articles
            result = get_marketing_articles("https://www.blogdumoderateur.com/marketing/")
        else:
            return jsonify({'success': False, 'error': 'Catégorie non valide'})

        # Sérialiser les données avant de les renvoyer
        serialized_result = serialize_mongo_data(result)
        return jsonify({'success': True, 'data': serialized_result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
    
    # Sérialiser les données avant de les renvoyer
    articles = serialize_mongo_data(articles)
    
    return jsonify({'articles': articles})

@app.route('/article/<article_id>')
def article_detail(article_id):
    # Récupérer l'article par son ID
    article = articles_collection.find_one({'_id': ObjectId(article_id)})
    
    if article:
        article = serialize_mongo_data(article)
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
