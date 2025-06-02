# boutiques/views.py
from django.http import Http404, HttpResponseRedirect # Ajoutez HttpResponseRedirect si vous l'utilisez

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test # Importez login_required
from django.forms import inlineformset_factory
from django.db.models import Sum, Q, Avg, Count
from django.contrib import messages
from django.db import transaction
from django import forms # Importez forms pour créer des formulaires simples directement dans les vues
from django.utils.text import slugify # Utilisez la version recommandée de slugify
from decimal import Decimal # Nécessaire pour les calculs de prix fiables

# Assurez-vous que ceux-ci sont importés une seule fois au début
from .models import Shop, Product, Category, UserProfile, ProductImage, ProductVideo, Order, OrderItem, Review, CartItem
from .forms import ShopForm, ProductForm, ProductImageFormSet, ProductVideoFormSet, ReviewForm, UserProfileForm 
# Importez les formulaires d'adresse de livraison et de statut de commande si définis dans forms.py
# (Je les avais mis dans forms.py dans les réponses précédentes, donc assurez-vous qu'ils y sont)
from .forms import ShippingAddressForm, OrderStatusUpdateForm # Assurez-vous que ces classes existent dans forms.py

# --- Décorateur personnalisé pour vérifier si l'utilisateur est un vendeur ---
def seller_required(function):
    def wrap(request, *args, **kwargs):
        # Assurez-vous que le profil existe et que l'utilisateur est un vendeur
        if hasattr(request.user, 'userprofile') and request.user.userprofile.is_seller: # Corrected from 'profile' to 'userprofile'
            return function(request, *args, **kwargs)
        else:
            messages.error(request, "Accès refusé. Vous devez être un vendeur pour accéder à cette page.")
            return redirect('home') # Ou une page spécifique d'accès refusé
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap

# --- Vues Publiques (READ) ---

def home_view(request):
    recent_products = Product.objects.filter(is_available=True).order_by('-created_at')[:8]
    active_shops = Shop.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_available=True))
    ).order_by('-created_at')[:4]
    categories = Category.objects.all()

    context = {
        'latest_products': recent_products,
        'active_shops': active_shops,
        'categories': categories,
    }
    return render(request, 'boutiques/home.html', context)

def shop_list_view(request):
    shops = Shop.objects.filter(is_active=True)
    query = request.GET.get('q')

    if query:
        shops = shops.filter(Q(name__icontains=query) | Q(description__icontains=query))
        messages.info(request, f"Résultats de recherche pour '{query}'")

    context = {
        'shops': shops,
        'current_query': query if query else '',
    }
    return render(request, 'boutiques/shop_list.html', context)

def shop_detail_view(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
    products = shop.products.filter(is_available=True).order_by('-created_at')
    return render(request, 'boutiques/shop_detail.html', {'shop': shop, 'products': products})

def product_list_view(request):
    products = Product.objects.filter(is_available=True)
    categories = Category.objects.all()

    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
        messages.info(request, f"Résultats de recherche pour '{query}'")

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        messages.info(request, f"Filtre appliqué : Catégorie '{category.name}'")

    if min_price:
        try:
            min_price = Decimal(min_price) # Use Decimal for prices
            products = products.filter(price__gte=min_price)
        except ValueError:
            messages.error(request, "Le prix minimum doit être un nombre valide.")

    if max_price:
        try:
            max_price = Decimal(max_price) # Use Decimal for prices
            products = products.filter(price__lte=max_price)
        except ValueError:
            messages.error(request, "Le prix maximum doit être un nombre valide.")

    context = {
        'products': products,
        'categories': categories,
        'current_query': query if query else '',
        'current_category': category_slug if category_slug else '',
        'current_min_price': str(min_price) if min_price else '', # Convert back to string for template
        'current_max_price': str(max_price) if max_price else '', # Convert back to string for template
    }
    return render(request, 'boutiques/product_list.html', context)


@login_required
def user_profile_view(request):
    # Récupère le profil utilisateur existant ou en crée un nouveau s'il n'existe pas
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            # Avant de sauvegarder, vérifiez si l'utilisateur a tenté de modifier 'is_seller'
            # si le champ est désactivé dans le formulaire.
            # Le champ désactivé ne sera pas dans request.POST, donc sa valeur ne sera pas modifiée
            # par form.save() s'il n'est pas dans clean_data.
            # C'est un peu plus complexe si vous voulez que l'utilisateur puisse SE MARQUER comme vendeur.
            # Si is_seller était désactivé, sa valeur de l'instance sera conservée.
            form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès.")
            return redirect('user_profile') # Redirige vers la même page de profil
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = UserProfileForm(instance=user_profile) # Pré-remplir le formulaire avec les données existantes

    context = {
        'form': form,
        'user_profile': user_profile,
    }
    return render(request, 'boutiques/user_profile.html', context)

def product_detail_view(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_available=True)
    images = product.images.all()
    videos = product.videos.all()

    reviews = product.reviews.all().order_by('-created_at')
    average_rating = product.get_average_rating()

    user_has_reviewed = False
    review_form = None

    if request.user.is_authenticated:
        if Review.objects.filter(product=product, user=request.user).exists():
            user_has_reviewed = True
        else:
            review_form = ReviewForm()

    context = {
        'product': product,
        'images': images,
        'videos': videos,
        'reviews': reviews,
        'average_rating': average_rating,
        'user_has_reviewed': user_has_reviewed,
        'review_form': review_form,
    }
    return render(request, 'boutiques/product_detail.html', context)

def category_list_view(request):
    categories = Category.objects.annotate(product_count=Count('products', filter=Q(products__is_available=True)))

    context = {
        'categories': categories,
    }
    return render(request, 'boutiques/category_list.html', context)

def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_available=True).order_by('-created_at')

    context = {
        'category': category,
        'products': products
    }
    return render(request, 'boutiques/category_detail.html', context)

# --- Vues du Tableau de Bord Vendeur (Seller Dashboard) ---

@login_required
@seller_required
def seller_dashboard_home(request):
    user_shops = Shop.objects.filter(owner=request.user)
    total_products = Product.objects.filter(shop__owner=request.user).count()

    total_orders_for_seller = Order.objects.filter(items__product__shop__owner=request.user).distinct().count()

    # Calcul du revenu mensuel pour les commandes complétées ou livrées qui concernent le vendeur
    from datetime import datetime
    from django.db.models import F # Assurez-vous d'importer F

    current_month = datetime.now().month
    current_year = datetime.now().year

    # Assurez-vous que le calcul agrégé est correct et qu'il gère les Decimals
    monthly_revenue = OrderItem.objects.filter(
        product__shop__owner=request.user,
        order__status__in=['delivered', 'completed'],
        order__created_at__month=current_month,
        order__created_at__year=current_year
    ).aggregate(
        total_month_revenue=Sum(F('price_at_purchase') * F('quantity'))
    )['total_month_revenue'] or Decimal('0.00') # Utiliser Decimal pour le défaut

    context = {
        'shop_count': user_shops.count(),
        'product_count': total_products,
        'order_count': total_orders_for_seller,
        'monthly_revenue': monthly_revenue,
    }
    return render(request, 'boutiques/vendeur_dashboard_home.html', context)

@login_required
@seller_required
def seller_shop_list_view(request):
    shops = Shop.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'boutiques/vendeur_shop_list.html', {'shops': shops})

# --- CRUD pour les Boutiques du Vendeur ---

@login_required
@seller_required
def shop_create_view(request):
    # Check if the user already has a shop
    if Shop.objects.filter(owner=request.user).exists():
        messages.warning(request, "Vous ne pouvez avoir qu'une seule boutique. Vous pouvez modifier votre boutique existante.")
        existing_shop = Shop.objects.filter(owner=request.user).first()
        return redirect('shop_update', shop_slug=existing_shop.slug) # Use shop_update instead of edit_shop

    # If the user is not marked as a seller, mark them now
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_seller: # Corrected from 'profile'
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.is_seller = True
        profile.save()
        messages.info(request, "Votre compte a été mis à jour pour vous permettre de créer une boutique.")

    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user
            # Ensure slug is generated if not provided or to guarantee uniqueness
            if not shop.slug:
                shop.slug = slugify(shop.name)
            try:
                shop.save()
                messages.success(request, f"Votre boutique '{shop.name}' a été créée avec succès !")
                return redirect('shop_detail', shop_slug=shop.slug)
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création de la boutique : {e}. Le nom ou le slug est peut-être déjà utilisé.")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ShopForm()
    return render(request, 'boutiques/create_shop.html', {'form': form})

@login_required
@seller_required
def shop_update_view(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    if request.method == 'POST':
        form = ShopForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, f"La boutique '{shop.name}' a été mise à jour.")
            return redirect('shop_detail', shop_slug=shop.slug)
    else:
        form = ShopForm(instance=shop)
    return render(request, 'boutiques/edit_shop.html', {'form': form, 'shop': shop})

@login_required
@seller_required
def shop_delete_view(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    if request.method == 'POST':
        shop.delete()
        messages.success(request, f"La boutique '{shop.name}' a été supprimée.")
        return redirect('seller_shop_list')
    return render(request, 'boutiques/vendeur_shop_confirm_delete.html', {'shop': shop})


# --- CRUD pour les Produits du Vendeur ---

@login_required
@seller_required
def seller_products_list_view(request):
    user_shops = Shop.objects.filter(owner=request.user)
    products = Product.objects.filter(shop__in=user_shops).order_by('-created_at')

    context = {
        'products': products,
        'user_shops': user_shops,
    }
    return render(request, 'boutiques/vendeur_products_list.html', context)


@login_required
@seller_required
def seller_product_create_view(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images')
        video_formset = ProductVideoFormSet(request.POST, request.FILES, prefix='videos')

        # print(f"Product Form Errors: {product_form.errors}") # Debugging
        # print(f"Image Formset Errors: {image_formset.errors}") # Debugging
        # print(f"Video Formset Errors: {video_formset.errors}") # Debugging

        if product_form.is_valid() and image_formset.is_valid() and video_formset.is_valid():
            product = product_form.save(commit=False)
            product.shop = shop
            if not product.slug:
                product.slug = slugify(product.name)
            try:
                product.save()
                # Save M2M fields like 'category' after product is saved for the first time
                product_form.save_m2m()

                image_formset.instance = product
                image_formset.save()

                video_formset.instance = product
                video_formset.save()

                messages.success(request, f"Le produit '{product.name}' a été ajouté à votre boutique.")
                return redirect('seller_products_list')
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de l'ajout du produit : {e}. Le nom ou le slug est peut-être déjà utilisé pour un autre produit dans cette boutique.")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        product_form = ProductForm()
        image_formset = ProductImageFormSet(prefix='images')
        video_formset = ProductVideoFormSet(prefix='videos')

    context = {
        'shop': shop,
        'product_form': product_form,
        'image_formset': image_formset,
        'video_formset': video_formset,
    }
    return render(request, 'boutiques/add_product.html', context)

@login_required
@seller_required
def seller_product_update_view(request, shop_slug, product_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    product = get_object_or_404(Product, slug=product_slug, shop=shop)

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product, prefix='images')
        video_formset = ProductVideoFormSet(request.POST, request.FILES, instance=product, prefix='videos')

        # print(f"Product Form Errors: {product_form.errors}") # Debugging
        # print(f"Image Formset Errors: {image_formset.errors}") # Debugging
        # print(f"Video Formset Errors: {video_formset.errors}") # Debugging

        if product_form.is_valid() and image_formset.is_valid() and video_formset.is_valid():
            product = product_form.save() # Saves product and M2M fields

            image_formset.save()
            video_formset.save()

            messages.success(request, f"Le produit '{product.name}' a été mis à jour.")
            return redirect('seller_products_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        product_form = ProductForm(instance=product)
        image_formset = ProductImageFormSet(instance=product, prefix='images')
        video_formset = ProductVideoFormSet(instance=product, prefix='videos')

    context = {
        'shop': shop,
        'product': product,
        'product_form': product_form,
        'image_formset': image_formset,
        'video_formset': video_formset,
    }
    return render(request, 'boutiques/edit_product.html', context)

@login_required
@seller_required
def seller_product_delete_view(request, shop_slug, product_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, owner=request.user)
    product = get_object_or_404(Product, slug=product_slug, shop=shop)

    if request.method == 'POST':
        product.delete()
        messages.success(request, f"Le produit '{product.name}' a été supprimé.")
        return redirect('seller_products_list')
    return render(request, 'boutiques/vendeur_product_confirm_delete.html', {'shop': shop, 'product': product})

# --- Vues pour la suppression d'images/vidéos individuelles ---
@login_required
@seller_required
def delete_product_image(request, pk):
    image = get_object_or_404(ProductImage, pk=pk, product__shop__owner=request.user)
    product_slug = image.product.slug
    shop_slug = image.product.shop.slug
    if request.method == 'POST':
        image.delete()
        messages.success(request, "Image supprimée avec succès.")
    return redirect('seller_product_update', shop_slug=shop_slug, product_slug=product_slug)

@login_required
@seller_required
def delete_product_video(request, pk):
    video = get_object_or_404(ProductVideo, pk=pk, product__shop__owner=request.user)
    product_slug = video.product.slug
    shop_slug = video.product.shop.slug
    if request.method == 'POST':
        video.delete()
        messages.success(request, "Vidéo supprimée avec succès.")
    return redirect('seller_product_update', shop_slug=shop_slug, product_slug=product_slug)

# --- Vues du Panier ---

def get_cart(request):
    """
    Récupère le contenu du panier depuis la session.
    Le panier est un dictionnaire: {product_id: {'name': ..., 'price': ..., 'quantity': ..., 'main_image_url': ...}}
    """
    if 'cart' not in request.session:
        request.session['cart'] = {}
    return request.session['cart']

def add_to_cart(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_available=True)
    cart = get_cart(request)

    quantity = int(request.POST.get('quantity', 1))
    if quantity <= 0: # Ensure quantity is positive
        messages.error(request, "La quantité doit être un nombre positif.")
        return redirect('product_detail', product_slug=product.slug)

    # Vérifier le stock disponible avant d'ajouter au panier
    current_quantity_in_cart = cart.get(str(product.id), {}).get('quantity', 0)
    if current_quantity_in_cart + quantity > product.stock:
        messages.error(request, f"Stock insuffisant pour '{product.name}'. Disponible : {product.stock}.")
        return redirect('product_detail', product_slug=product.slug)

    # Assurez-vous que l'image principale existe avant d'essayer d'accéder à son URL
    main_image_url = None
    if product.main_image and product.main_image.image: # Double check for product.main_image.image
        main_image_url = product.main_image.image.url # CORRECTION ICI

    product_id_str = str(product.id)
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += quantity
    else:
        cart[product_id_str] = {
            'name': product.name,
            'price': str(product.price), # Convert Decimal to string for JSON serialization
            'quantity': quantity,
            'main_image_url': main_image_url
        }

    request.session.modified = True
    messages.success(request, f"{quantity}x '{product.name}' a été ajouté à votre panier.")
    return redirect('cart_detail')

def remove_from_cart(request, product_id):
    cart = get_cart(request)
    product_id = str(product_id)

    if product_id in cart:
        item_name = cart[product_id]['name']
        del cart[product_id]
        request.session.modified = True
        messages.info(request, f"'{item_name}' a été retiré de votre panier.")
    return redirect('cart_detail')

def update_cart_quantity(request, product_id):
    cart = get_cart(request)
    product_id = str(product_id)

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity', 1))
            if new_quantity <= 0:
                return remove_from_cart(request, product_id)

            if product_id in cart:
                product_obj = get_object_or_404(Product, id=product_id)
                if new_quantity > product_obj.stock:
                    messages.error(request, f"Seulement {product_obj.stock} unités de '{product_obj.name}' sont disponibles.")
                    new_quantity = product_obj.stock # Ajuste la quantité au stock max
                    cart[product_id]['quantity'] = new_quantity
                else:
                    cart[product_id]['quantity'] = new_quantity

                request.session.modified = True
                messages.success(request, f"Quantité de '{cart[product_id]['name']}' mise à jour à {new_quantity}.")
            else:
                messages.error(request, "Cet article n'est plus dans votre panier.")
        except ValueError:
            messages.error(request, "Quantité invalide.")
    return redirect('cart_detail')

def cart_detail_view(request):
    cart = get_cart(request)
    cart_items = []
    total_price = Decimal('0.00') # Utilisez Decimal pour le total

    # Itérer sur une copie pour pouvoir modifier le panier original en cas de suppression
    for product_id, item_data in list(cart.items()):
        try:
            product = get_object_or_404(Product, id=product_id) # is_available check might be too restrictive here if user has it in cart
            # Vérifier la disponibilité et le stock
            if not product.is_available:
                messages.warning(request, f"Le produit '{item_data.get('name', 'nom inconnu')}' n'est plus disponible et a été retiré de votre panier.")
                del cart[product_id]
                request.session.modified = True
                continue # Passer à l'élément suivant

            if item_data['quantity'] > product.stock:
                messages.warning(request, f"Le stock de '{product.name}' est insuffisant. La quantité a été ajustée de {item_data['quantity']} à {product.stock}.")
                item_data['quantity'] = product.stock # Ajuste la quantité dans les données du panier
                request.session.modified = True # Le panier session sera modifié plus tard

            item_price = product.price
            item_total = item_price * Decimal(item_data['quantity']) # Utilisez Decimal pour le calcul
            total_price += item_total

            current_main_image_url = None
            if product.main_image and product.main_image.image: # Double check for product.main_image.image
                current_main_image_url = product.main_image.image.url # CORRECTION ICI

            cart_items.append({
                'product': product,
                'name': product.name,
                'quantity': item_data['quantity'],
                'price': item_price,
                'total': item_total,
                'main_image_url': current_main_image_url
            })
        except Product.DoesNotExist:
            messages.warning(request, f"Un produit (ID: {product_id}, '{item_data.get('name', 'nom inconnu')}') de votre panier n'existe plus ou n'est plus disponible et a été retiré.")
            del cart[product_id]
            request.session.modified = True

    # Après avoir traité tous les articles et potentiellement mis à jour les quantités,
    # réécrivez la session du panier pour s'assurer qu'elle est cohérente avec cart_items.
    # Ceci est important pour les ajustements de quantité dus au stock.
    request.session['cart'] = { str(item['product'].id): {
        'name': item['product'].name,
        'price': str(item['product'].price),
        'quantity': item['quantity'],
        'main_image_url': item['main_image_url']
    } for item in cart_items }


    return render(request, 'boutiques/cart_detail.html', {'cart_items': cart_items, 'total_price': total_price})


# --- Vues du Processus de Commande (Checkout) ---

@login_required
def checkout_view(request):
    # Utilisez le panier de session pour le checkout, plutôt que le modèle CartItem
    # Cela correspond à la logique add_to_cart / cart_detail_view
    session_cart = get_cart(request)
    cart_items_for_checkout = []
    total_cart_price = Decimal('0.00')
    errors = []

    if not session_cart:
        messages.warning(request, "Votre panier est vide. Veuillez ajouter des produits avant de passer commande.")
        return redirect('cart_detail')

    # Reconstruire les éléments du panier à partir de la session et vérifier le stock/disponibilité
    for product_id_str, item_data in session_cart.items():
        try:
            product = get_object_or_404(Product, id=int(product_id_str))

            if not product.is_available:
                errors.append(f"Le produit '{product.name}' n'est plus disponible et a été retiré de votre panier.")
                del session_cart[product_id_str] # Supprime du panier de session
                request.session.modified = True
                continue # Passer à l'élément suivant

            quantity = item_data['quantity']
            if quantity > product.stock:
                errors.append(f"Stock insuffisant pour '{product.name}'. Disponible: {product.stock}, Requis: {quantity}.")
                quantity = product.stock # Ajuste la quantité pour le checkout
                session_cart[product_id_str]['quantity'] = quantity # Met à jour la session
                request.session.modified = True

            item_total = product.price * Decimal(quantity)
            total_cart_price += item_total
            cart_items_for_checkout.append({
                'product': product,
                'quantity': quantity,
                'price': product.price,
                'total': item_total,
                # La main_image_url est déjà dans la session ou peut être récupérée ici si nécessaire
                'main_image_url': item_data.get('main_image_url')
            })
        except Product.DoesNotExist:
            errors.append(f"Un produit (ID: {product_id_str}, '{item_data.get('name', 'nom inconnu')}') de votre panier n'existe plus et a été retiré.")
            del session_cart[product_id_str]
            request.session.modified = True


    # Si le panier est vide après les vérifications (ex: tous les produits indisponibles)
    if not cart_items_for_checkout:
        messages.warning(request, "Votre panier est vide après vérification des produits disponibles.")
        return redirect('cart_detail')


    if request.method == 'POST':
        shipping_form = ShippingAddressForm(request.POST)
        if shipping_form.is_valid() and not errors: # Ne pas valider si des erreurs de stock existent
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    shipping_address_line1=shipping_form.cleaned_data['address_line1'],
                    shipping_address_line2=shipping_form.cleaned_data.get('address_line2', ''),
                    shipping_city=shipping_form.cleaned_data['city'],
                    shipping_postal_code=shipping_form.cleaned_data['postal_code'],
                    shipping_country=shipping_form.cleaned_data['country'],
                    total_price=total_cart_price,
                    status='pending'
                )

                for item_data in cart_items_for_checkout:
                    product = item_data['product']
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name, # Store name at time of purchase
                        price_at_purchase=product.price, # Store price at time of purchase
                        quantity=item_data['quantity'],
                    )
                    product.stock -= item_data['quantity']
                    product.save()

                # Vider le panier de session
                request.session['cart'] = {}
                request.session.modified = True

                messages.success(request, "Votre commande a été passée avec succès !")
                return redirect('order_confirmation', order_id=order.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire d'adresse de livraison ou les problèmes de stock.")
    else: # GET request
        shipping_form = ShippingAddressForm()
        if hasattr(request.user, 'userprofile') and request.user.userprofile.address_line1:
            shipping_form = ShippingAddressForm(initial={
                'address_line1': request.user.userprofile.address_line1,
                'address_line2': request.user.userprofile.address_line2,
                'city': request.user.userprofile.city,
                'postal_code': request.user.userprofile.postal_code,
                'country': request.user.userprofile.country,
            })

    return render(request, 'boutiques/checkout.html', {
        'shipping_form': shipping_form,
        'cart_items': cart_items_for_checkout, # Utilisez les items reconstruits pour le template
        'total_cart_price': total_cart_price,
        'errors': errors
    })

@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'pending':
        order.status = 'processing' # On met à jour le statut après "confirmation" de la commande
        order.save()
    return render(request, 'boutiques/order_confirmation.html', {'order': order})

# --- Vues pour le Tableau de Bord Vendeur (Gestion des commandes reçues) ---
@login_required
@seller_required
def seller_orders_list(request):
    seller_shops = Shop.objects.filter(owner=request.user)
    seller_orders = Order.objects.filter(
        items__product__shop__in=seller_shops
    ).distinct().order_by('-created_at')

    context = {
        'seller_orders': seller_orders,
    }
    return render(request, 'boutiques/vendeur_orders_list.html', context)

@login_required
@seller_required
def seller_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Vérifier que le vendeur est bien le propriétaire des produits dans cette commande
    if not OrderItem.objects.filter(order=order, product__shop__owner=request.user).exists():
        messages.error(request, "Vous n'êtes pas autorisé à voir cette commande.")
        return redirect('seller_orders_list')

    seller_order_items = OrderItem.objects.filter(order=order, product__shop__owner=request.user)

    # Utilisation du formulaire OrderStatusUpdateForm importé depuis .forms
    # plutôt que de le définir en interne
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            # La logique de validation (empêcher 'delivered', 'completed', etc.)
            # est maintenant gérée par la méthode clean_status du formulaire lui-même.
            form.save()
            messages.success(request, f"Le statut de la commande #{order.id} a été mis à jour à '{order.get_status_display()}'.")
            return redirect('seller_order_detail', order_id=order.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = OrderStatusUpdateForm(instance=order)

    context = {
        'order': order,
        'seller_order_items': seller_order_items,
        'form': form,
    }
    return render(request, 'boutiques/vendeur_order_detail.html', context)


# --- Nouvelles vues pour le Client (Historique des commandes et confirmation de réception) ---

@login_required
def user_orders_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'boutiques/user_orders_list.html', context)

@login_required
def user_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'boutiques/user_order_detail.html', context)

@login_required
def confirm_order_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'shipped':
        if request.method == 'POST':
            order.status = 'delivered'
            order.save()
            messages.success(request, f"Vous avez confirmé la réception de la commande #{order.id}. Merci !")
            return redirect('user_order_detail', order_id=order.id)
        else:
            messages.info(request, "Confirmez la réception de votre commande via le bouton sur la page de détail.")
            return redirect('user_order_detail', order_id=order.id)
    else:
        messages.error(request, f"Le statut actuel de la commande #{order.id} ne permet pas la confirmation de livraison.")
        return redirect('user_order_detail', order_id=order.id)


@login_required
def submit_review(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_available=True)

    if Review.objects.filter(product=product, user=request.user).exists():
        messages.error(request, "Vous avez déjà soumis un avis pour ce produit.")
        return redirect('product_detail', product_slug=product.slug)

    # Vérifiez si l'utilisateur a acheté ce produit et si la commande est livrée ou complétée
    # Cela évite que quelqu'un qui n'a pas acheté puisse laisser un avis
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status__in=['delivered', 'completed']
    ).exists()

    if not has_purchased:
        messages.warning(request, "Vous ne pouvez laisser un avis que pour les produits que vous avez achetés et dont la commande a été livrée ou complétée.")
        return redirect('product_detail', product_slug=product.slug)


    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Votre avis a été soumis avec succès !")
            return redirect('product_detail', product_slug=product.slug)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans votre avis.")
    else:
        form = ReviewForm() # Ce bloc est rarement atteint si la vue est POST-only

    # Ce return est un fallback si le formulaire n'est pas POST ou n'est pas valide
    return redirect('product_detail', product_slug=product.slug)