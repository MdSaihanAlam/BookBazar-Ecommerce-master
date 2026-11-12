import json
import random
import string
from functools import wraps

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import BadHeaderError, EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView, View
from django.views.generic.list import MultipleObjectMixin

from .forms import AddressForm, CategoryForm, ContactForm, PaymentForm, ProductForm
from .currency import SESSION_CURRENCY, browser_country, format_money, request_currency
from .hero import hero_slides
from .middleware import SESSION_LANGUAGE, activate_user_language
from .models import Address, Book, Cart, CartItem, Category, Coupon, Order, OrderItem, Payment, Wishlist

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def is_ajax(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('content-type', '')
    )


def ajax_login_required(view):
    """Like login_required, but AJAX callers get a JSON 401 with a login URL instead of a redirect."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        next_url = request.headers.get('referer') or request.get_full_path()
        if is_ajax(request):
            login_url = redirect_to_login(next_url)['Location']
            return JsonResponse({'success': False, 'message': _('Please log in first.'), 'login_url': login_url}, status=401)
        return redirect_to_login(request.get_full_path())
    return wrapper


def category_list():
    return Category.objects.annotate(
        total_books=Count('books', filter=Q(books__is_available=True))
    )


def search_books(queryset, query):
    return queryset.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(author__name__icontains=query)
        | Q(additional_authors__icontains=query)
        | Q(isbn__icontains=query)
        | Q(isbn13__icontains=query)
        | Q(category__name__icontains=query)
    ).distinct()


def get_session_coupon(request):
    """Return the promo code applied from the cart page, if it is still valid."""
    data = request.session.get('applied_coupon')
    if not data:
        return None
    coupon = Coupon.objects.filter(id=data.get('id'), active=True).first()
    if coupon and coupon.is_valid():
        return coupon
    request.session.pop('applied_coupon', None)
    return None


def get_default_shipping_address(user):
    return Address.objects.filter(user=user, address_type='S', default=True).first()


# ==================== HOME & BROWSE ====================

def home(request):
    available = Book.objects.filter(is_available=True).select_related('author', 'category')
    featured_books = available.filter(featured=True)[:8]

    context = {
        'featured_books': featured_books,
        'hero_slides': hero_slides(featured_books[:3] or available.order_by('-created_at')[:3]),
        'new_arrivals': available.order_by('-created_at')[:10],
        'deals': available.filter(discount_price__isnull=False, discount_price__lt=F('price'))[:4],
        'categories': category_list().order_by('-total_books')[:6],
        'promo': Coupon.objects.filter(
            active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now()
        ).order_by('-amount').first(),
        'stats': {
            'books': available.count(),
            'authors': available.exclude(author=None).values('author').distinct().count(),
            'categories': Category.objects.count(),
        },
    }
    return render(request, 'store/home.html', context)


def browse_books(request):
    queryset = Book.objects.filter(is_available=True).select_related('author', 'category').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    if query:
        queryset = search_books(queryset, query)

    page_obj = Paginator(queryset, 12).get_page(request.GET.get('page'))

    context = {
        'queryset': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'categories': category_list(),
        'query': query,
    }
    return render(request, 'store/browse_books.html', context)


class SearchView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        url = reverse('store:product-list')
        if query:
            url += '?' + request.GET.urlencode()
        return redirect(url)


@require_POST
def set_preferences(request):
    """Save the language and currency picked in the site's language & currency menu.
    Guests keep them for the session; signed-in users also get them saved to their profile."""
    language = request.POST.get('language')
    currency = request.POST.get('currency')
    language = language if language in dict(settings.LANGUAGES) else None
    currency = currency if currency in settings.CURRENCIES else None
    if language:
        request.session[SESSION_LANGUAGE] = language
    if currency:
        request.session[SESSION_CURRENCY] = currency

    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    if profile:
        if language:
            profile.language = language
        if currency:
            profile.currency = currency
        profile.save(update_fields=['language', 'currency', 'updated_at'])

    activate_user_language(request)
    next_url = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        next_url = reverse('store:home')
    return redirect(next_url)


def search_suggest(request):
    """Live results for the search palette; with no query it returns featured books to start from."""
    query = request.GET.get('q', '').strip()[:80]
    books = Book.objects.filter(is_available=True).select_related('author')
    categories = category_list()
    if query:
        books = search_books(books, query)
        categories = categories.filter(name__icontains=query)
    else:
        books = books.order_by('-featured', '-created_at')
        categories = categories.order_by('-total_books')

    return JsonResponse({
        'books': [{
            'title': book.title,
            'author': book.author.name if book.author else '',
            'url': book.get_absolute_url(),
            'cover': book.image_url,
            'price': float(book.final_price),
        } for book in books[:6]],
        'categories': [{
            'name': category.name,
            'url': category.get_absolute_url(),
            'count': category.total_books,
        } for category in categories[:4]],
    })


# ==================== CART ====================

@login_required
def cart_view(request):
    cart, _created = Cart.objects.get_or_create(user=request.user)
    coupon = get_session_coupon(request)
    coupon_discount = min(float(coupon.amount), cart.final_total) if coupon else 0
    context = {
        'cart': cart,
        'cart_items': cart.items.select_related('book', 'book__author').all(),
        'coupon': coupon,
        'coupon_discount': coupon_discount,
        'order_total': cart.final_total - coupon_discount,
    }
    return render(request, 'store/basket.html', context)


@ajax_login_required
def add_to_cart(request, slug):
    book = get_object_or_404(Book, slug=slug)
    cart, _created = Cart.objects.get_or_create(user=request.user)
    cart_item = CartItem.objects.filter(cart=cart, book=book).first()
    in_cart = cart_item.quantity if cart_item else 0

    try:
        quantity = max(int(json.loads(request.body or '{}').get('quantity', 1)), 1)
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        quantity = 1

    if not book.is_available or in_cart + quantity > book.stock_quantity:
        message = (_("Sorry, %(title)s is out of stock.") % {'title': book.title} if not book.is_available
                   else _("Only %(count)s copies of %(title)s are available.") % {'count': book.stock_quantity, 'title': book.title})
        if is_ajax(request):
            return JsonResponse({'success': False, 'message': message})
        messages.warning(request, message)
        return redirect(book.get_absolute_url())

    if cart_item:
        cart_item.quantity = F('quantity') + quantity
        cart_item.save(update_fields=['quantity'])
    else:
        CartItem.objects.create(cart=cart, book=book, quantity=quantity)

    message = _("%(title)s added to your cart!") % {'title': book.title}
    if is_ajax(request):
        return JsonResponse({'success': True, 'message': message, 'total_items': cart.total_items})
    messages.success(request, message)
    return redirect('store:cart')


def cart_totals(cart):
    return {
        'subtotal': cart.subtotal,
        'total_discount': cart.total_discount,
        'final_total': cart.final_total,
        'total_items': cart.total_items,
    }


def mini_cart(request):
    """Cart contents for the slide-out cart drawer."""
    if not request.user.is_authenticated:
        return JsonResponse({'items': [], 'subtotal': 0, 'total_discount': 0, 'final_total': 0, 'total_items': 0})
    cart, _created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('book', 'book__author')
    return JsonResponse({
        'items': [{
            'id': item.id,
            'title': item.book.title,
            'author': item.book.author.name if item.book.author else '',
            'url': item.book.get_absolute_url(),
            'cover': item.book.image_url,
            'quantity': item.quantity,
            'total': float(item.final_price),
        } for item in items],
        **cart_totals(cart),
    })


@ajax_login_required
@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    try:
        action = json.loads(request.body or '{}').get('action')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': _('Invalid request')}, status=400)

    if action == 'increase':
        if cart_item.quantity >= cart_item.book.stock_quantity:
            return JsonResponse({
                'success': False,
                'error': _("Only %(count)s copies available.") % {'count': cart_item.book.stock_quantity}
            })
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    elif action == 'remove':
        cart_item.delete()

    removed = action == 'remove'
    return JsonResponse({
        'success': True,
        'item_quantity': 0 if removed else cart_item.quantity,
        'item_total': 0 if removed else cart_item.final_price,
        **cart_totals(cart_item.cart),
    })


@ajax_login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = cart_item.cart
    book_title = cart_item.book.title
    cart_item.delete()

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'message': _("%(title)s removed from cart") % {'title': book_title},
            **cart_totals(cart),
        })
    messages.info(request, _("%(title)s removed from cart") % {'title': book_title})
    return redirect("store:cart")


@login_required
def order_summary(request):
    return redirect("store:cart")


@login_required
def remove_from_cart_legacy(request, slug):
    book = get_object_or_404(Book, slug=slug)
    deleted, _details = CartItem.objects.filter(cart__user=request.user, book=book).delete()
    if deleted:
        messages.info(request, _("%(title)s removed from cart") % {'title': book.title})
    else:
        messages.info(request, _("Item not found in cart"))
    return redirect("store:cart")


@login_required
def remove_single_item_from_cart(request, slug):
    book = get_object_or_404(Book, slug=slug)
    cart_item = CartItem.objects.filter(cart__user=request.user, book=book).first()
    if not cart_item:
        messages.info(request, _("Item not found in cart"))
    elif cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
        messages.info(request, _("%(title)s quantity updated") % {'title': book.title})
    else:
        cart_item.delete()
        messages.info(request, _("%(title)s removed from cart") % {'title': book.title})
    return redirect("store:cart")


# ==================== PRODUCTS & CATEGORIES ====================

class EcoIndex(ListView):
    model = Book
    template_name = 'store/category.html'
    context_object_name = 'queryset'
    paginate_by = 12

    def get_queryset(self):
        return Book.objects.select_related('author', 'category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = category_list()
        return context


class EcoDetail(DetailView):
    model = Book
    template_name = 'store/book_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        user = self.request.user
        context['categories'] = category_list()
        context['related_items'] = (
            Book.objects.filter(category=book.category, is_available=True)
            .exclude(pk=book.pk).select_related('author')[:5]
        )
        context['in_wishlist'] = user.is_authenticated and Wishlist.objects.filter(user=user, book=book).exists()
        context['in_cart'] = user.is_authenticated and CartItem.objects.filter(cart__user=user, book=book).exists()
        address = get_default_shipping_address(user) if user.is_authenticated else None
        context['ship_country'] = address.country.name if address else None
        return context


class CategoryDetail(DetailView, MultipleObjectMixin):
    model = Category
    template_name = 'store/category.html'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        object_list = Book.objects.filter(category=self.object).select_related('author')
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['categories'] = category_list()
        return context


# ==================== CHECKOUT & PAYMENT ====================

@login_required
def check_shipping_address(request):
    return JsonResponse({
        'has_shipping_address': get_default_shipping_address(request.user) is not None
    })


class Checkout(LoginRequiredMixin, View):
    def get_cart(self):
        cart, _created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def get(self, *args, **kwargs):
        cart = self.get_cart()
        cart_items = cart.items.select_related('book')
        if not cart_items.exists():
            messages.info(self.request, _("Your cart is empty"))
            return redirect("store:cart")

        shipping_address = get_default_shipping_address(self.request.user)
        if not shipping_address:
            messages.warning(self.request, _("Please set up your default shipping address before checkout."))
            return redirect('store:shipping-address')

        coupon = get_session_coupon(self.request)
        coupon_discount = min(float(coupon.amount), cart.final_total) if coupon else 0
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'default_shipping_address': shipping_address,
            'coupon': coupon,
            'coupon_discount': coupon_discount,
            'order_total': cart.final_total - coupon_discount,
        }
        return render(self.request, "store/checkout.html", context)

    @transaction.atomic
    def post(self, *args, **kwargs):
        user = self.request.user
        cart = self.get_cart()
        cart_items = cart.items.select_related('book')
        if not cart_items.exists():
            messages.info(self.request, _("Your cart is empty"))
            return redirect("store:cart")

        shipping_address = get_default_shipping_address(user)
        if not shipping_address:
            messages.warning(self.request, _("Please set up your default shipping address before checkout."))
            return redirect('store:shipping-address')

        for item in cart_items:
            if item.quantity > item.book.stock_quantity:
                messages.warning(
                    self.request,
                    _("Only %(count)s copies of %(title)s are available.") % {'count': item.book.stock_quantity, 'title': item.book.title}
                )
                return redirect("store:cart")

        # Rebuild the pending order from the current cart contents
        order, _created = Order.objects.get_or_create(user=user, ordered=False)
        OrderItem.objects.filter(user=user, ordered=False).delete()
        order.items.set([
            OrderItem.objects.create(user=user, book=item.book, quantity=item.quantity)
            for item in cart_items
        ])
        order.shipping_address = shipping_address
        order.billing_address = shipping_address
        order.coupon = get_session_coupon(self.request)
        order.save()
        return redirect('store:payment', payment_option='stripe')


class PaymentView(LoginRequiredMixin, View):
    def get_order(self):
        order = Order.objects.filter(user=self.request.user, ordered=False).first()
        if order and order.items.exists() and order.shipping_address:
            return order
        return None

    def get(self, *args, **kwargs):
        order = self.get_order()
        if not order:
            messages.warning(self.request, _("Please complete checkout first."))
            return redirect("store:checkout")
        context = {
            'order': order,
            'order_total': order.get_total(),
            'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        }
        return render(self.request, "store/payment.html", context)

    def post(self, *args, **kwargs):
        order = self.get_order()
        if not order:
            messages.warning(self.request, _("Please complete checkout first."))
            return redirect("store:checkout")

        form = PaymentForm(self.request.POST)
        if not form.is_valid():
            messages.warning(self.request, _("Please enter your card details."))
            return redirect(self.request.path)

        amount = int(round(order.get_total() * 100))
        try:
            charge_id = 'free-order'
            if amount > 0:
                charge = stripe.Charge.create(
                    amount=amount,
                    currency='usd',
                    source=form.cleaned_data['stripeToken'],
                    description=f"BookBazar order for {self.request.user.email}",
                )
                charge_id = charge['id']
        except stripe.CardError as e:
            messages.warning(self.request, e.user_message or _("Your card was declined."))
            return redirect(self.request.path)
        except stripe.StripeError:
            messages.warning(self.request, _("Payment could not be processed. You have not been charged."))
            return redirect(self.request.path)

        self.complete_order(order, charge_id, amount)
        messages.success(self.request, _("Your order was placed successfully! Reference: %(ref)s") % {'ref': order.ref_code})
        return redirect("store:home")

    @transaction.atomic
    def complete_order(self, order, charge_id, amount):
        user = self.request.user
        order.payment = Payment.objects.create(stripe_charge_id=charge_id, user=user, amount=amount / 100)
        order.ordered = True
        order.ordered_date = timezone.now()
        order.ref_code = create_ref_code()
        order.save()

        for item in order.items.select_related('book'):
            book = item.book
            book.stock_quantity = max(book.stock_quantity - item.quantity, 0)
            book.save()
        order.items.update(ordered=True)

        CartItem.objects.filter(cart__user=user).delete()
        self.request.session.pop('applied_coupon', None)


# ==================== WISHLIST ====================

class WishSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        wish = Wishlist.objects.filter(user=self.request.user).select_related('book', 'book__author')
        return render(self.request, 'store/customer_wishlist.html', {'object': wish})


@ajax_login_required
def add_to_wish(request, slug):
    book = get_object_or_404(Book, slug=slug)
    _wish, created = Wishlist.objects.get_or_create(book=book, user=request.user)
    message = _("Book was added to your wishlist") if created else _("Book was already in your wishlist")

    if is_ajax(request):
        return JsonResponse({'success': True, 'message': message, 'created': created})

    if created:
        messages.info(request, message)
    else:
        messages.warning(request, message)
    return redirect('store:product-detail', slug=book.slug)


@ajax_login_required
def remove_from_wish(request, slug):
    book = get_object_or_404(Book, slug=slug)
    deleted, _details = Wishlist.objects.filter(book=book, user=request.user).delete()

    if is_ajax(request):
        if deleted:
            return JsonResponse({'success': True, 'message': _('Book removed from your wishlist')})
        return JsonResponse({'success': False, 'message': _('Book not found in your wishlist')}, status=404)

    if deleted:
        messages.info(request, _("Book was removed from your wishlist."))
    else:
        messages.error(request, _("Book not found in your wishlist."))
    return redirect("store:wish-summary")


# ==================== COUPONS ====================

@require_POST
def apply_promo_code(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': _('Please log in to apply promo codes.')})

    try:
        promo_code = json.loads(request.body or '{}').get('promo_code', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': _('Invalid request.')}, status=400)

    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return JsonResponse({'success': False, 'message': _('Please add items to your cart first.')})

    coupon = Coupon.objects.filter(code__iexact=promo_code, active=True).first()
    if not coupon:
        return JsonResponse({'success': False, 'message': _('Invalid or expired promo code.')})
    if not coupon.is_valid():
        return JsonResponse({'success': False, 'message': _('This promo code has expired.')})

    request.session['applied_coupon'] = {'code': coupon.code, 'amount': float(coupon.amount), 'id': coupon.id}

    discount_amount = min(float(coupon.amount), cart.final_total)
    new_final_total = cart.final_total - discount_amount
    return JsonResponse({
        'success': True,
        'message': _('Promo code applied! %(amount)s discount added.') % {
            'amount': format_money(discount_amount, request_currency(request)),
        },
        'discount_amount': discount_amount,
        'cart_data': {
            'subtotal': cart.subtotal,
            'final_total': new_final_total,
            'total_items': cart.total_items,
            'total_discount': cart.total_discount + discount_amount,
            'grand_total': new_final_total,
        }
    })


# ==================== CONTACT ====================

class ContactView(FormView):
    form_class = ContactForm
    success_url = reverse_lazy('store:contact')
    template_name = 'store/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = category_list()
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        email = EmailMessage(
            subject=f"BookBazar Contact: {data['subject']}",
            body=f"Name: {data['name']}\nEmail: {data['email']}\n\nMessage:\n{data['message']}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[data['email']],
        )
        try:
            email.send(fail_silently=False)
        except (BadHeaderError, OSError):
            messages.error(self.request, _("There was an error sending your message. Please try again later."))
            return self.form_invalid(form)
        messages.success(self.request, _("Your message has been sent successfully!"))
        return super().form_valid(form)


# ==================== SHIPPING ADDRESSES ====================

def unset_other_defaults(user, address):
    Address.objects.filter(
        user=user, address_type=address.address_type, default=True
    ).exclude(pk=address.pk).update(default=False)


@login_required
def shipping_address_view(request):
    shipping_addresses = Address.objects.filter(user=request.user, address_type='S').order_by('-default')
    from_checkout = request.GET.get('from_checkout') == 'true'

    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.address_type = 'S'
            # The first address is always the default
            if not shipping_addresses.filter(default=True).exists():
                address.default = True
            address.save()
            if address.default:
                unset_other_defaults(request.user, address)
            messages.success(request, _('Shipping address saved successfully!'))
            if from_checkout:
                return redirect('store:checkout')
            return redirect('store:shipping-address')
        messages.error(request, _('Please correct the errors below.'))
    else:
        form = AddressForm(initial={'address_type': 'S', 'country': browser_country(request)})

    context = {
        'form': form,
        'shipping_addresses': shipping_addresses,
        'default_shipping_address': shipping_addresses.filter(default=True).first(),
        'categories': category_list(),
    }
    return render(request, 'store/shipping_address.html', context)


@login_required
@require_POST
def delete_address(request, address_id):
    address = Address.objects.filter(id=address_id, user=request.user).first()
    if not address:
        if is_ajax(request):
            return JsonResponse({'success': False, 'error': _('Address not found')}, status=404)
        messages.error(request, _('Address not found'))
        return redirect('store:shipping-address')

    address_title = f"{address.street_address}, {address.city}"
    was_default = address.default
    address.delete()
    if was_default:
        replacement = Address.objects.filter(user=request.user, address_type=address.address_type).first()
        if replacement:
            replacement.default = True
            replacement.save()

    message = _('Address "%(address)s" deleted successfully!') % {'address': address_title}
    if is_ajax(request):
        return JsonResponse({'success': True, 'message': message})
    messages.success(request, message)
    return redirect('store:shipping-address')


@login_required
@require_POST
def set_default_address(request, address_id):
    address = Address.objects.filter(id=address_id, user=request.user).first()
    if not address:
        if is_ajax(request):
            return JsonResponse({'success': False, 'error': _('Address not found')}, status=404)
        messages.error(request, _('Address not found'))
        return redirect('store:shipping-address')

    address.default = True
    address.save()
    unset_other_defaults(request.user, address)

    message = _('Default shipping address updated successfully!')
    if is_ajax(request):
        return JsonResponse({'success': True, 'message': message})
    messages.success(request, message)
    return redirect('store:shipping-address')


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save()
            if address.default:
                unset_other_defaults(request.user, address)
            messages.success(request, _('Address updated successfully!'))
            return redirect('store:shipping-address')
    else:
        form = AddressForm(instance=address)

    context = {
        'form': form,
        'editing': True,
        'address': address,
        'shipping_addresses': Address.objects.filter(user=request.user, address_type='S').order_by('-default'),
        'categories': category_list(),
    }
    return render(request, 'store/shipping_address.html', context)


# ==================== PRODUCT MANAGEMENT (STAFF ONLY) ====================

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ManageFormMixin:
    template_name = 'store/manage_form.html'
    success_url = reverse_lazy('store:home')
    page_title = ''
    success_message = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.page_title
        return context

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AddProductView(StaffRequiredMixin, ManageFormMixin, CreateView):
    model = Book
    form_class = ProductForm
    page_title = gettext_lazy('Add New Book')
    success_message = gettext_lazy('Book added successfully!')


class EditProductView(StaffRequiredMixin, ManageFormMixin, UpdateView):
    model = Book
    form_class = ProductForm
    page_title = gettext_lazy('Edit Book')
    success_message = gettext_lazy('Book updated successfully!')


class DeleteProductView(StaffRequiredMixin, View):
    def post(self, request, slug):
        product = get_object_or_404(Book, slug=slug)
        product_title = product.title
        product.delete()
        messages.success(request, _('Book "%(title)s" deleted successfully!') % {'title': product_title})
        return redirect('store:home')


class AddCategoryView(StaffRequiredMixin, ManageFormMixin, CreateView):
    model = Category
    form_class = CategoryForm
    page_title = gettext_lazy('Add New Category')
    success_message = gettext_lazy('Category added successfully!')
