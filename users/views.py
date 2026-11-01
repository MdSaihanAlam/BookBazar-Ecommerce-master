from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.views import generic
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from store.middleware import activate_user_language
from store.models import Address, Order
from .forms import CustomUserCreationForm, ProfileEditForm
from .models import UserProfile


class RegisterView(generic.CreateView):
    template_name = 'users/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('store:home')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('store:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, _('Welcome %(email)s! Your account has been created successfully.') % {'email': self.object.email})
        return response


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            activate_user_language(request)
            messages.success(request, _('Welcome back, %(email)s!') % {'email': user.email})
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('store:home')
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form, 'next': next_url or ''})


def logout_view(request):
    was_signed_in = request.user.is_authenticated
    logout(request)
    activate_user_language(request)
    if was_signed_in:
        messages.info(request, _('You have been logged out.'))
    return redirect('store:home')


@login_required
def profile_view(request):
    UserProfile.objects.get_or_create(user=request.user)
    context = {
        'user': request.user,
        'orders': (Order.objects.filter(user=request.user, ordered=True)
                   .select_related('payment').order_by('-ordered_date')[:10]),
        'default_address': Address.objects.filter(user=request.user, address_type='S', default=True).first(),
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit_view(request):
    profile, _created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            if request.POST.get('remove_photo') == 'true' and profile.profile_photo:
                profile.profile_photo.delete(save=False)
                profile.profile_photo = None
            request.user.profile = form.save()
            activate_user_language(request)
            messages.success(request, _('Profile updated successfully!'))
            return redirect('users:profile')
        messages.error(request, _('Please correct the errors below.'))
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
            error = _("All fields are required.")
        elif new_password != confirm_password:
            error = _("New passwords don't match.")
        elif not request.user.check_password(current_password):
            error = _("Current password is incorrect.")
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
            messages.success(request, _("Password changed successfully!"))
            return redirect('users:profile')

    return render(request, 'users/change_password.html', {'user': request.user})
