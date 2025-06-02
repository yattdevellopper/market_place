# boutiques/forms.py

from django import forms
from .models import UserProfile, Shop, Product, ProductImage, ProductVideo, Order, OrderItem, Review # Assurez-vous d'importer tous les modèles nécessaires
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _ # Pour les traductions si vous internationalisez

# --- Formulaires d'Administration de Boutique et Produit ---

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'description', 'logo', 'banner_image', 'is_active']
        labels = {
            'name': 'Nom de la boutique',
            'description': 'Description de la boutique',
            'logo': 'Logo de la boutique',
            'banner_image': 'Image de bannière',
            'is_active': 'Boutique active ?',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'is_available']
        labels = {
            'category': 'Catégorie',
            'name': 'Nom du produit',
            'description': 'Description détaillée',
            'price': 'Prix',
            'stock': 'Quantité en stock',
            'is_available': 'Disponible à la vente ?',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Formsets pour les images et vidéos de produits
ProductImageFormSet = inlineformset_factory(
    Product, ProductImage,
    fields=['image', 'alt_text'],
    extra=1,
    can_delete=True,
    widgets={
        'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

ProductVideoFormSet = inlineformset_factory(
    Product, ProductVideo,
    fields=['video_file', 'youtube_url'], # Assurez-vous que ces champs sont corrects dans votre modèle ProductVideo
    extra=1,
    can_delete=True,
    widgets={
        'video_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Ex: https://www.youtube.com/watch?v=dQw4w9WgXcQ'}),
    }
)

# --- Formulaire pour les Avis (Reviews) ---

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        labels = {
            'rating': 'Note',
            'comment': 'Votre avis',
        }
        widgets = {
            'rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Partagez votre expérience avec ce produit...'}),
        }

# --- Formulaire d'Adresse de Livraison (pour le Checkout) ---

class ShippingAddressForm(forms.Form): # Utilisation de forms.Form car ce n'est pas lié directement à un modèle
    address_line1 = forms.CharField(
        label='Adresse Ligne 1',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro et nom de rue'})
    )
    address_line2 = forms.CharField(
        label='Adresse Ligne 2 (optionnel)',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Appartement, Bâtiment, etc.'})
    )
    city = forms.CharField(
        label='Ville',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre ville'})
    )
    postal_code = forms.CharField(
        label='Code Postal',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code postal'})
    )
    country = forms.CharField(
        label='Pays',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre pays'})
    )

# --- Formulaire de Mise à Jour de Statut de Commande (pour les Vendeurs) ---

class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'tracking_number', 'shipping_provider']
        labels = {
            'status': 'Statut de la commande',
            'tracking_number': 'Numéro de suivi',
            'shipping_provider': 'Transporteur',
        }
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro de suivi'}),
            'shipping_provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: DHL, La Poste'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limite les choix de statut pour les vendeurs
        # Un vendeur ne peut pas marquer une commande comme 'pending', 'delivered', 'completed', 'cancelled', 'refunded'
        # Ces statuts sont gérés par le système ou le client.
        self.fields['status'].choices = [
            ('processing', 'En cours de traitement'),
            ('shipped', 'Expédiée'),
        ]

        # Désactiver le formulaire si la commande est déjà dans un état final pour le vendeur
        if self.instance and self.instance.status in ['delivered', 'completed', 'cancelled', 'refunded']:
            for field_name, field in self.fields.items():
                field.widget.attrs['disabled'] = True
            messages.info(self.request, "Cette commande est dans un état final et ne peut plus être modifiée par le vendeur.")


    def clean_status(self):
        # Assurez-vous que l'utilisateur n'essaie pas de forcer un statut non autorisé
        status = self.cleaned_data['status']
        if status in ['pending', 'delivered', 'completed', 'cancelled', 'refunded']:
            # Permet de remonter le statut de 'pending' à 'processing' si c'est le cas initial
            if self.instance and self.instance.status == 'pending' and status == 'processing':
                return status
            raise forms.ValidationError(_("Vous ne pouvez pas définir ce statut pour la commande."))
        return status

    # Le __init__ de OrderStatusUpdateForm peut nécessiter le 'request' pour les messages
    # Si vous passez 'request' dans le kwargs du formulaire lors de son instanciation dans la vue:
    # `form = OrderStatusUpdateForm(request.POST, instance=order, request=request)`
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) # Récupère request si passé
        super().__init__(*args, **kwargs)
        # Limite les choix de statut pour les vendeurs
        self.fields['status'].choices = [
            ('processing', 'En cours de traitement'),
            ('shipped', 'Expédiée'),
        ]

        # Désactiver le formulaire si la commande est déjà dans un état final pour le vendeur
        if self.instance and self.instance.status in ['delivered', 'completed', 'cancelled', 'refunded']:
            for field_name, field in self.fields.items():
                field.widget.attrs['disabled'] = True
            if self.request: # Affiche le message seulement si request est disponible
                messages.info(self.request, "Cette commande est dans un état final et ne peut plus être modifiée par le vendeur.")

# --- Formulaire de Profil Utilisateur ---

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address_line1', 'address_line2', 'city', 'postal_code', 'country', 'is_seller']
        labels = {
            'phone_number': 'Numéro de téléphone',
            'address_line1': 'Adresse Ligne 1',
            'address_line2': 'Adresse Ligne 2 (optionnel)',
            'city': 'Ville',
            'postal_code': 'Code Postal',
            'country': 'Pays',
            'is_seller': 'Devenir vendeur ?',
        }
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: +223 77 12 34 56'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro et nom de rue'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Appartement, Bâtiment, etc.'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre ville'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code postal'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre pays'}),
            'is_seller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # J'ai supprimé la boucle générique `for field_name, field in self.fields.items():`
        # car vous définissez déjà des widgets spécifiques pour chaque champ, ce qui est mieux.

        # Logique pour désactiver 'is_seller' si l'utilisateur est déjà un vendeur
        # Cela empêche un utilisateur de décocher 'is_seller' une fois qu'il est vendeur,
        # la gestion du statut de vendeur devenant alors une tâche administrative.
        if self.instance and self.instance.is_seller:
            self.fields['is_seller'].widget.attrs['disabled'] = True
            self.fields['is_seller'].help_text = "Vous êtes déjà enregistré comme vendeur. Contactez l'administrateur pour modifier ce statut."
        else:
            self.fields['is_seller'].help_text = "Cochez cette case pour devenir un vendeur et créer votre boutique. Une fois vendeur, ce statut ne peut être modifié que par un administrateur."

    def clean_is_seller(self):
        # Si le champ 'is_seller' est désactivé (disabled) dans le formulaire,
        # sa valeur ne sera pas présente dans `self.cleaned_data`.
        # Nous devons donc récupérer la valeur existante de l'instance.
        if self.instance and self.instance.is_seller:
            return self.instance.is_seller # Conserver la valeur existante si l'utilisateur est déjà un vendeur
        return self.cleaned_data.get('is_seller', False) # Sinon, utiliser la valeur soumise ou False par défaut