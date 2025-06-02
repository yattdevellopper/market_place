"""
URL configuration for marketplace_project project.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView # Pour les redirections simples

# Importez la vue de profil utilisateur directement depuis boutiques.views
# Assurez-vous que cette vue existe et est correctement définie dans boutiques/views.py
from boutiques.views import user_profile_view # Assurez-vous que cette vue existe

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Inclut toutes les URLs de votre application 'boutiques'
    path('', include('boutiques.urls')),

    # Inclut les URLs d'authentification par défaut de Django (login, logout, password_reset, etc.)
    # Ces URLs seront préfixées par 'accounts/'
    path('accounts/', include('django.contrib.auth.urls')),

    # Définit une URL spécifique pour le profil de l'utilisateur après connexion.
    # Cette URL est souvent la cible par défaut de Django après une connexion réussie.
    # Elle pointe directement vers la vue 'user_profile_view' que nous avons définie.
    path('user_profile', user_profile_view, name='user_profile'),

    # URL pour l'inscription. Elle inclut les URLs de votre application 'registration'.
    # Assurez-vous que 'registration.urls' contient la vue d'inscription.
    path('register/', include('registration.urls')),
]
# Servir les fichiers média en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Si vous avez aussi des fichiers statiques qui posent problème (CSS, JS, etc.)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Servir les fichiers médias seulement en mode développement
# NE JAMAIS FAIRE CELA EN PRODUCTION ! Utilisez un serveur web (Nginx/Apache).
