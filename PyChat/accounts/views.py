from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import UserLoginForm, UserRegistrationForm, UserSettingsForm


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect('conversation_list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('conversation_list')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('conversation_list')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('conversation_list')
            form.add_error(None, 'Invalid username or password')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'profile_user': request.user,
    })


@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    if request.method == 'POST':
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            messages.success(request, 'Your settings have been updated.')
            return redirect('accounts:settings')
    else:
        form = UserSettingsForm()

    return render(request, 'accounts/settings.html', {'form': form})
