# boutiques/templatetags/boutique_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_seller(order_items, user):
    """
    Filtre une liste d'OrderItems pour ne retourner que ceux qui
    appartiennent aux boutiques du vendeur spécifié.
    """
    seller_shops = user.shop_set.all() # Obtenez les boutiques du vendeur
    return [item for item in order_items if item.product.shop in seller_shops]





@register.filter
def total_price_for_seller(order_items):
    """
    Calcule le prix total pour une liste d'OrderItems (pour le vendeur).
    """
    total = sum(item.subtotal for item in order_items)
    return total