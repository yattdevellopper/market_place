# boutiques/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # --- URLs de gestion du profil utilisateur (Corrigé pour utiliser user_profile_view) ---
    path('profile/', views.user_profile_view, name='user_profile'), # Affiche le profil existant

    # --- URLs de la page d'accueil et des listes publiques ---
    path('', views.home_view, name='home'), # Page d'accueil du marketplace

    # Boutiques
    path('shops/', views.shop_list_view, name='shop_list'), # Liste de toutes les boutiques
    path('shops/<slug:shop_slug>/', views.shop_detail_view, name='shop_detail'), # Détail d'une boutique

    # Produits
    path('products/', views.product_list_view, name='product_list'), # Liste de tous les produits
    path('products/<slug:product_slug>/', views.product_detail_view, name='product_detail'), # Détail d'un produit

    # Catégories
    path('categories/', views.category_list_view, name='category_list'), # Liste de toutes les catégories
    path('categories/<slug:slug>/', views.category_detail_view, name='category_detail'), # Détail d'une catégorie

    # Avis sur les produits
    path('product/<slug:product_slug>/review/', views.submit_review, name='submit_review'),

    # --- URLs du Panier ---
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('cart/add/<slug:product_slug>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),

    # --- URLs de la Commande (Checkout) ---
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation_view, name='order_confirmation'),

    # --- NOUVEAU : URLs de l'Historique des Commandes Client ---
    path('profile/orders/', views.user_orders_list, name='user_orders_list'),
    path('profile/orders/<int:order_id>/', views.user_order_detail, name='user_order_detail'),
    path('profile/orders/<int:order_id>/confirm-delivery/', views.confirm_order_delivery, name='confirm_order_delivery'),


    # --- URLs du Tableau de Bord Vendeur (Seller Dashboard) ---
    path('seller/dashboard/', views.seller_dashboard_home, name='seller_dashboard_home'),

    # CRUD pour les Boutiques du Vendeur
    path('seller/shops/', views.seller_shop_list_view, name='seller_shop_list'), # Liste les boutiques du vendeur
    path('seller/shop/create/', views.shop_create_view, name='create_shop'), # Créer une boutique
    path('seller/shop/<slug:shop_slug>/edit/', views.shop_update_view, name='edit_shop'), # Modifier une boutique
    path('seller/shop/<slug:shop_slug>/delete/', views.shop_delete_view, name='delete_shop'), # Supprimer une boutique

    # CRUD pour les Produits du Vendeur
    path('seller/products/', views.seller_products_list_view, name='seller_products_list'), # Liste tous les produits du vendeur
    path('seller/shop/<slug:shop_slug>/products/add/', views.seller_product_create_view, name='add_product'), # Ajouter un produit
    path('seller/shop/<slug:shop_slug>/products/<slug:product_slug>/edit/', views.seller_product_update_view, name='edit_product'), # Modifier un produit
    path('seller/shop/<slug:shop_slug>/products/<slug:product_slug>/delete/', views.seller_product_delete_view, name='delete_product'), # Supprimer un produit

    # Gestion des images et vidéos de produits (vues de suppression individuelles)
    path('seller/images/<int:pk>/delete/', views.delete_product_image, name='delete_product_image'),
    path('seller/videos/<int:pk>/delete/', views.delete_product_video, name='delete_product_video'),

    # Gestion des Commandes pour le Vendeur
    path('seller/orders/', views.seller_orders_list, name='seller_orders_list'),
    path('seller/orders/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),
    # L'URL seller_order_update_status a été supprimée car sa logique est intégrée dans seller_order_detail
]