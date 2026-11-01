from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views import generic
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import CustomUserCreationForm, ProfileEditForm
from .models import UserProfile


class RegisterView(generic.CreateView):
    template_name = 'users/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('eco:home')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('eco:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f'Welcome {self.object.email}! Your account has been created successfully.')
        return response


def login_view(request):
    if request.user.is_authenticated:
        return redirect('eco:home')

    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.email}!')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('eco:home')
        messages.error(request, 'Invalid email or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form, 'next': next_url or ''})


def logout_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'You have been logged out.')
    logout(request)
    return redirect('eco:home')


@login_required
def profile_view(request):
    UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
def profile_edit_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            if request.POST.get('remove_photo') == 'true' and profile.profile_photo:
                profile.profile_photo.delete(save=False)
                profile.profile_photo = None
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, 'users/profile_edit.html', {'user': request.user, 'form': form})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        error = None
        if not all([current_password, new_password, confirm_password]):
            error = "All fields are required."
        elif new_password != confirm_password:
            error = "New passwords don't match."
        elif not request.user.check_password(current_password):
            error = "Current password is incorrect."
        else:
            try:
                validate_password(new_password, request.user)
            except ValidationError as e:
                error = " ".join(e.messages)

        if error:
            messages.error(request, error)
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully!")
            return redirect('users:profile')

    return render(request, 'users/change_password.html', {'user': request.user})
