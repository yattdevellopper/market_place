# registration/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from boutiques.models import UserProfile # Important pour créer le profil du vendeur

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Créer un UserProfile pour le nouvel utilisateur
            UserProfile.objects.create(user=user)
            login(request, user) # Connecte l'utilisateur après l'inscription
            return redirect('home') # Redirige vers la page d'accueil
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})