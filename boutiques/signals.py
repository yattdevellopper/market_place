# boutiques/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import OrderItem, Order # Assurez-vous d'importer les modèles corrects

@receiver(post_save, sender=OrderItem)
@receiver(post_delete, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """
    Met à jour le prix total de la commande chaque fois qu'un OrderItem est enregistré ou supprimé.
    """
    order = instance.order
    # Utilisez calculate_total_price pour re-calculer le total à partir des articles actuels
    order.total_price = order.calculate_total_price()
    order.save()