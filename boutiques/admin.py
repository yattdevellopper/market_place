# boutiques/admin.py

from django.contrib import admin
from .models import (
    UserProfile, Category, Shop, Product, ProductImage, ProductVideo,
    CartItem, Order, OrderItem, Review # Assurez-vous que tous vos modèles sont importés ici
)

# --- Administration des Utilisateurs et Profils ---
# Vous pouvez décommenter et adapter ce bloc si vous souhaitez intégrer UserProfile
# directement dans l'administration du modèle User de Django.
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import User

# class UserProfileInline(admin.StackedInline):
#     model = UserProfile
#     can_delete = False
#     verbose_name_plural = 'profile'
#     fk_name = 'user'

# class CustomUserAdmin(BaseUserAdmin):
#     inlines = (UserProfileInline,)
#     list_display = BaseUserAdmin.list_display + ('is_seller_display',)
#
#     def is_seller_display(self, obj):
#         return obj.userprofile.is_seller if hasattr(obj, 'userprofile') else False
#     is_seller_display.boolean = True
#     is_seller_display.short_description = 'Vendeur'
#
# admin.site.unregister(User)
# admin.site.register(User, CustomUserAdmin)

# Autrement, enregistrez simplement UserProfile comme ceci si vous ne personnalisez pas l'Admin User
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_seller', 'phone_number', 'city', 'country', 'postal_code')
    list_filter = ('is_seller', 'country')
    search_fields = ('user__username', 'phone_number', 'city', 'postal_code', 'country')
    raw_id_fields = ('user',)
    # Correction des champs d'adresse
    fieldsets = (
        (None, {
            'fields': ('user', 'phone_number', 'address_line1', 'address_line2', 'city', 'country', 'postal_code', 'is_seller')
        }),
    )
    autocomplete_fields = ('user',)


# --- Administration des Catégories ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


# --- Administration des Boutiques ---
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'owner')
    search_fields = ('name', 'description', 'owner__username', 'owner__email')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('owner',)
    autocomplete_fields = ('owner',) # Autocomplétion pour le propriétaire


# --- Administration des Produits ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    # Assurez-vous que 'order' est un champ dans votre modèle ProductImage si vous le laissez ici
    fields = ['image', 'alt_text'] # Retiré 'order' si non présent dans models.py


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1
    # Assurez-vous que 'caption' et 'order' sont des champs dans votre modèle ProductVideo si vous les laissez ici
    # Changé 'video_url' en 'youtube_url' pour correspondre au modèle
    fields = ['video_file', 'youtube_url'] # Retiré 'caption' et 'order' si non présents dans models.py


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'category', 'price', 'stock', 'is_available', 'created_at')
    list_filter = ('is_available', 'shop', 'category')
    search_fields = ('name', 'description', 'shop__name', 'category__name')
    # prepopulated_fields devrait être basé sur le nom du produit, pas la boutique (ForeignKey)
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('shop', 'category',)
    inlines = [ProductImageInline, ProductVideoInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            # Suppression de 'main_image' qui n'est pas un champ de modèle direct
            'fields': ('shop', 'category', 'name', 'slug', 'description', 'price', 'stock', 'is_available')
        }),
        ('Dates et Horodatage', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    actions = ['make_available', 'make_unavailable']

    def make_available(self, request, queryset):
        queryset.update(is_available=True)
        self.message_user(request, "Produits sélectionnés marqués comme disponibles.")
    make_available.short_description = "Marquer les produits sélectionnés comme disponibles"

    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)
        self.message_user(request, "Produits sélectionnés marqués comme indisponibles.")
    make_unavailable.short_description = "Marquer les produits sélectionnés comme indisponibles"


# --- Administration des Articles du Panier ---
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'total', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'product__name')
    raw_id_fields = ('user', 'product')
    readonly_fields = ('total',)


# --- Administration des Commandes ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # CORRECTION : 'subtotal' au lieu de 'get_total_price'
    readonly_fields = ('product_name', 'price_at_purchase', 'quantity', 'subtotal')
    # CORRECTION : 'subtotal' au lieu de 'get_total_price'
    fields = ('product', 'product_name', 'price_at_purchase', 'quantity', 'subtotal')
    autocomplete_fields = ('product',)

    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'total_price', 'status', 'created_at', 'updated_at',
        'shipping_city', 'shipping_country', 'tracking_number'
    )
    list_filter = ('status', 'created_at', 'shipping_country')
    search_fields = (
        'user__username', 'id', 'shipping_city', 'shipping_postal_code',
        'tracking_number'
    )
    raw_id_fields = ('user',)
    inlines = [OrderItemInline]
    readonly_fields = ('total_price', 'created_at', 'updated_at', 'shipping_address_line1',
                       'shipping_address_line2', 'shipping_city', 'shipping_postal_code',
                       'shipping_country')
    fieldsets = (
        (None, {
            'fields': (('user', 'status'), 'total_price', ('created_at', 'updated_at')),
        }),
        ('Informations de Livraison', {
            'fields': ('shipping_address_line1', 'shipping_address_line2',
                       ('shipping_city', 'shipping_postal_code'), 'shipping_country'),
        }),
        ('Suivi de Commande', {
            'fields': ('tracking_number', 'shipping_provider'),
        }),
    )

    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_completed']

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, "Commandes sélectionnées marquées comme 'En cours de traitement'.")
    mark_as_processing.short_description = "Marquer comme 'En cours de traitement'"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, "Commandes sélectionnées marquées comme 'Expédiée'.")
    mark_as_shipped.short_description = "Marquer comme 'Expédiée'"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, "Commandes sélectionnées marquées comme 'Livrée'.")
    mark_as_delivered.short_description = "Marquer comme 'Livrée'"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, "Commandes sélectionnées marquées comme 'Terminée'.")
    mark_as_completed.short_description = "Marquer comme 'Terminée'"


# --- Administration des Avis (Reviews) ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at', 'comment_snippet')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')
    raw_id_fields = ('product', 'user')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'rating', 'comment')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def comment_snippet(self, obj):
        return obj.comment[:75] + '...' if obj.comment and len(obj.comment) > 75 else obj.comment
    comment_snippet.short_description = 'Commentaire'