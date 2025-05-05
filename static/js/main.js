$(document).ready(function() {
    // Fonction pour charger les articles
    function loadArticles(filters = {}) {
        $.get('/search', filters, function(response) {
            const articlesList = $('#articlesList');
            articlesList.empty();
            
            response.articles.forEach(article => {
                articlesList.append(`
                    <div class="col-md-4 mb-4">
                        <div class="card article-card">
                            <img src="${article.thumbnail || '/static/img/default.jpg'}" 
                                 class="card-img-top article-image" 
                                 alt="${article.title}">
                            <div class="card-body">
                                <h5 class="card-title">${article.title}</h5>
                                <p class="article-meta">
                                    <small>
                                        Par ${article.author} - ${article.publish_date}
                                    </small>
                                </p>
                                <p class="card-text">${article.summary || 'Pas de résumé disponible'}</p>
                                <a href="/article/${article._id}" class="btn btn-primary">Lire plus</a>
                            </div>
                        </div>
                    </div>
                `);
            });
        });
    }

    // Gérer la soumission du formulaire de recherche
    $('#searchForm').on('submit', function(e) {
        e.preventDefault();
        const filters = $(this).serialize();
        loadArticles(filters);
    });

    // Charger les articles au chargement de la page
    loadArticles();
});

function scrapeArticles(category) {
    const button = $(`button[onclick="scrapeArticles('${category}')"]`);
    button.prop('disabled', true);
    button.html(`<i class="fas fa-spinner fa-spin"></i> Chargement...`);

    $.get(`/scrape/${category}`)
        .done(function(data) {
            if (data.success) {
                location.reload();
            }
        })
        .fail(function(error) {
            console.error('Erreur:', error);
            alert('Erreur lors du scraping');
        })
        .always(function() {
            button.prop('disabled', false);
            button.html(`<i class="fas fa-sync"></i> Actualiser ${category.charAt(0).toUpperCase() + category.slice(1)}`);
        });
}

function renderArticle(article, container) {
    // ...existing code...
}

// ...existing code...
