# boutiques/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal # Important pour les prix
from django.conf import settings # <--- ADD THIS IMPORT!
from django.db.models import Avg, Sum, F # Assurez-vous d'importer F et Sum si vous utilisez les agrégats
from django.utils import timezone # Pour les champs de date et heure


# --- Modèles de base (ajustez selon vos besoins) ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_seller = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    # Ajoutez d'autres champs si nécessaire

    def __str__(self):
        return self.user.username + "'s Profile"

    # Vous pouvez ajouter une méthode pour obtenir l'adresse complète
    def get_full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.postal_code, self.country])
        return ', '.join(filter(None, parts)) # filter(None, parts) remove les éléments vides


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Shop(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=255, unique=True, verbose_name="Nom de la boutique")
    slug = models.SlugField(max_length=255, unique=True, blank=True,
                            help_text="Laissé vide pour générer automatiquement à partir du nom.")
    description = models.TextField(blank=True, verbose_name="Description")
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True, verbose_name="Logo")
    # Retire le ** de la fin :
    banner_image = models.ImageField(upload_to='shop_banners/', blank=True, null=True, verbose_name="Image de bannière")
    is_active = models.BooleanField(default=False, verbose_name="Active (visible au public)") # Les boutiques peuvent être désactivées par l'admin
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop_detail', kwargs={'shop_slug': self.slug})


class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.IntegerField(validators=[MinValueValidator(0)])
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shop', 'name') # Un produit doit être unique par nom dans une boutique
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.shop.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', kwargs={'product_slug': self.slug})

    @property
    def main_image(self):
        # Retourne la première image ou None si aucune
        return self.images.filter(is_main=True).first() or self.images.first() # Prioritize is_main image if available

    def get_average_rating(self):
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False) # Si vous voulez désigner une image principale

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video_file = models.FileField(upload_to='product_videos/', blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Video for {self.product.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.video_file and not self.youtube_url:
            raise ValidationError("You must provide either a video file or a YouTube URL.")
        if self.video_file and self.youtube_url:
            raise ValidationError("You cannot provide both a video file and a YouTube URL.")

    @property
    def youtube_id(self):
        # Extrait l'ID YouTube de l'URL
        if self.youtube_url:
            import re
            match = re.search(r'(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([^"&?/ ]{11})', self.youtube_url)
            return match.group(1) if match else None
        return None

# --- Modèles Panier et Commande ---

class CartItem(models.Model):
    """
    Représente un article dans le panier d'un utilisateur.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product') # Un utilisateur ne peut avoir qu'un seul enregistrement par produit

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.user.username}'s cart"

    @property
    def total(self):
        return self.quantity * self.product.price

class Order(models.Model):
    """
    Représente une commande passée par un utilisateur.
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]

    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    # Informations de livraison (copie au moment de la commande pour la persistance)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    shipping_city = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Détails de suivi (pour le vendeur)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_provider = models.CharField(max_length=100, blank=True, null=True) # Ex: DHL, La Poste

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande #{self.id} par {self.user.username if self.user else 'Utilisateur Inconnu'} - {self.get_status_display()}"

    def get_status_badge_color(self):
        # Renvoie une couleur de badge Bootstrap en fonction du statut
        if self.status == 'pending':
            return 'warning text-dark'
        elif self.status == 'processing':
            return 'primary'
        elif self.status == 'shipped':
            return 'info text-dark'
        elif self.status == 'delivered':
            return 'success'
        elif self.status == 'completed':
            return 'dark'
        elif self.status == 'cancelled':
            return 'danger'
        elif self.status == 'refunded':
            return 'secondary'
        return 'light text-dark' # Couleur par défaut

    def calculate_total_price(self):
        """Calcule le prix total de la commande en additionnant les sous-totaux des articles."""
        # Utilisez aggregate avec Sum pour une performance optimale sur la base de données**
        # 'items' est le related_name de ForeignKey de OrderItem vers Order**
        total_sum = self.items.aggregate(total=models.Sum(F('price_at_purchase') * F('quantity')))['total']
        return total_sum if total_sum is not None else Decimal('0.00')
class OrderItem(models.Model):
    """
    Représente un article individuel dans une commande.
    Ces données sont copiées au moment de l'achat pour la persistance.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True) # Garde une référence au produit original
    product_name = models.CharField(max_length=255) # Nom du produit au moment de l'achat
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) # Prix du produit au moment de l'achat
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('order', 'product') # Un produit ne peut apparaître qu'une fois par commande

    def __str__(self):
        return f"{self.quantity} x {self.product_name} dans la Commande #{self.order.id}"

    @property
    def subtotal(self):
        return self.quantity * self.price_at_purchase

# --- Modèles d'Avis (Reviews) ---
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)]) # Note de 1 à 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user') # Un utilisateur ne peut laisser qu'un avis par produit
        ordering = ['-created_at']

    def __str__(self):
        return f"Avis pour {self.product.name} par {self.user.username}"