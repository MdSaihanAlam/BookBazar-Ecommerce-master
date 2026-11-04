from django.contrib import admin
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from mptt.admin import MPTTModelAdmin

from .admin_site import FriendlyAdminMixin
from .models import (
    Address,
    Author,
    Book,
    BookImage,
    BookReview,
    Cart,
    CartItem,
    Category,
    Coupon,
    Order,
    OrderItem,
    Payment,
    Publisher,
    Refund,
    Wishlist,
)
from .templatetags.admin_dashboard import LOW_STOCK, order_status


def badge(label, style=''):
    return format_html('<span class="bb-badge {}">{}</span>', style, label)


def money(amount):
    return f'${amount:,.2f}'


class StoreAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    pass


# ==================== FILTERS ====================

class StockFilter(admin.SimpleListFilter):
    title = 'stock'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return [('out', 'Out of stock'), ('low', f'Low (under {LOW_STOCK})'), ('in', 'In stock')]

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(stock_quantity=0)
        if self.value() == 'low':
            return queryset.filter(stock_quantity__gt=0, stock_quantity__lt=LOW_STOCK)
        if self.value() == 'in':
            return queryset.filter(stock_quantity__gte=LOW_STOCK)
        return queryset


class OrderStatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('to_ship', 'To ship'),
            ('on_the_way', 'On the way'),
            ('received', 'Received'),
            ('refund_requested', 'Refund requested'),
            ('refunded', 'Refunded'),
            ('unpaid', 'Not paid'),
        ]

    def queryset(self, request, queryset):
        paid = queryset.filter(ordered=True)
        return {
            'to_ship': paid.filter(being_delivered=False, received=False, refund_granted=False),
            'on_the_way': paid.filter(being_delivered=True, received=False, refund_granted=False),
            'received': paid.filter(received=True, refund_requested=False),
            'refund_requested': paid.filter(refund_requested=True, refund_granted=False),
            'refunded': paid.filter(refund_granted=True),
            'unpaid': queryset.filter(ordered=False),
        }.get(self.value(), queryset)


class CouponStatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [('live', 'Live'), ('scheduled', 'Scheduled'), ('expired', 'Expired'), ('off', 'Switched off')]

    def queryset(self, request, queryset):
        now = timezone.now()
        return {
            'live': queryset.filter(active=True, valid_from__lte=now, valid_to__gte=now),
            'scheduled': queryset.filter(active=True, valid_from__gt=now),
            'expired': queryset.filter(valid_to__lt=now),
            'off': queryset.filter(active=False),
        }.get(self.value(), queryset)


# ==================== CATALOG ====================

class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 0
    verbose_name_plural = 'More images'


@admin.register(Book)
class BookAdmin(StoreAdmin):
    list_display = ['cover', 'book', 'price', 'discounted_price', 'stock_quantity', 'featured', 'is_available']
    list_display_links = ['cover', 'book']
    list_select_related = ['author', 'category']
    list_editable = ['featured', 'price', 'is_available', 'stock_quantity']
    list_filter = [StockFilter, 'is_available', 'featured', 'category', 'format_type', 'condition', 'author']
    search_fields = [
        'title', 'author__name', 'additional_authors', 'isbn', 'isbn13', 'publisher__name', 'genre', 'description',
    ]
    autocomplete_fields = ['author', 'publisher', 'category']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['cover_preview', 'created_at', 'updated_at']
    inlines = [BookImageInline]
    save_on_top = True

    fieldsets = (
        ('Book', {
            'fields': ('title', 'author', 'additional_authors', 'description', 'excerpt'),
        }),
        ('Price & stock', {
            'fields': (('price', 'discount_price'), ('stock_quantity', 'is_available'), 'featured'),
            'description': 'Prices are in US dollars. Shoppers see them converted to their own currency.',
        }),
        ('Cover', {
            'fields': ('cover_preview', 'cover_image', 'additional_images'),
        }),
        ('Shelf & format', {
            'fields': ('category', 'genre', ('format_type', 'condition'), 'language'),
        }),
        ('Publishing details', {
            'fields': ('publisher', ('publication_date', 'edition'), 'pages', ('isbn', 'isbn13')),
            'classes': ('collapse',),
        }),
        ('Advanced', {
            'fields': ('slug', ('label1', 'label2', 'label3'), ('created_at', 'updated_at')),
            'classes': ('collapse',),
            'description': 'The slug is the book\'s web address, e.g. /product/dune/.',
        }),
    )

    actions = ['make_featured', 'make_unfeatured', 'mark_available', 'mark_unavailable', 'increase_stock', 'clear_stock']

    @admin.display(description='')
    def cover(self, obj):
        return format_html('<img class="bb-cover" src="{}" alt="">', obj.image_url)

    @admin.display(description='Current cover')
    def cover_preview(self, obj):
        return format_html('<img class="bb-cover bb-cover-lg" src="{}" alt="">', obj.image_url)

    @admin.display(description='Book', ordering='title')
    def book(self, obj):
        details = ' · '.join(filter(None, [obj.author.name if obj.author else '', obj.category.name if obj.category else '']))
        return format_html(
            '<strong>{}</strong><div class="bb-sub">{}</div>{}',
            obj.title, details or '—', self.stock_badge(obj),
        )

    def stock_badge(self, obj):
        if obj.stock_quantity == 0:
            return badge('Out of stock', 'is-danger')
        if obj.stock_quantity < LOW_STOCK:
            return badge(f'Only {obj.stock_quantity} left', 'is-warning')
        return ''

    @admin.display(description='Sale price')
    def discounted_price(self, obj):
        if obj.discount_price and obj.discount_price < obj.price:
            return format_html('${} <span class="bb-badge is-brand">−{}%</span>', obj.discount_price, obj.discount_percentage)
        return '—'

    @admin.action(description='Feature on the home page')
    def make_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} books are now featured.')

    @admin.action(description='Remove from the home page')
    def make_unfeatured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} books are no longer featured.')

    @admin.action(description='Put up for sale')
    def mark_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} books are now for sale.')

    @admin.action(description='Take off sale')
    def mark_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} books were taken off sale.')

    @admin.action(description='Add 10 copies to stock')
    def increase_stock(self, request, queryset):
        updated = queryset.update(stock_quantity=F('stock_quantity') + 10)
        self.message_user(request, f'Added 10 copies to {updated} books.')

    @admin.action(description='Set stock to 0')
    def clear_stock(self, request, queryset):
        updated = queryset.update(stock_quantity=0)
        self.message_user(request, f'Set stock to 0 for {updated} books.')


@admin.register(Category)
class CategoryAdmin(FriendlyAdminMixin, MPTTModelAdmin):
    list_display = ['name', 'book_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_books=Count('books'))

    @admin.display(description='Books', ordering='num_books')
    def book_count(self, obj):
        return obj.num_books


@admin.register(Author)
class AuthorAdmin(StoreAdmin):
    list_display = ['name', 'image_preview', 'book_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_books=Count('book'))

    @admin.display(description='Books', ordering='num_books')
    def book_count(self, obj):
        return obj.num_books


@admin.register(Publisher)
class PublisherAdmin(StoreAdmin):
    list_display = ['name', 'website']
    search_fields = ['name']


@admin.register(BookReview)
class BookReviewAdmin(StoreAdmin):
    list_display = ['book', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    list_editable = ['is_approved']
    list_select_related = ['book', 'user']
    search_fields = ['book__title', 'user__email', 'title']
    autocomplete_fields = ['book', 'user']


# ==================== SALES ====================

@admin.register(Order)
class OrderAdmin(StoreAdmin):
    list_display = ['reference', 'user', 'ordered_date', 'total', 'status', 'being_delivered', 'received']
    list_display_links = ['reference']
    list_select_related = ['user']
    list_editable = ['being_delivered', 'received']
    list_filter = [OrderStatusFilter, 'ordered_date']
    search_fields = ['ref_code', 'user__email', 'shipping_address__street_address', 'shipping_address__city']
    date_hierarchy = 'ordered_date'
    ordering = ['-ordered_date']
    autocomplete_fields = ['user', 'shipping_address', 'billing_address', 'payment', 'coupon']
    readonly_fields = ['reference', 'status', 'ordered_date', 'start_date', 'items_summary']
    save_on_top = True

    fieldsets = (
        ('Order', {
            'fields': (('reference', 'status'), 'user', ('ordered_date', 'start_date'), 'items_summary'),
        }),
        ('Progress', {
            'fields': (('ordered', 'being_delivered', 'received'), ('refund_requested', 'refund_granted')),
            'description': 'Tick "Being delivered" once the parcel is sent and "Received" when it arrives.',
        }),
        ('Delivery & payment', {
            'fields': ('shipping_address', 'billing_address', 'payment', 'coupon'),
        }),
    )

    actions = ['mark_delivered', 'mark_received', 'grant_refunds']

    @admin.display(description='Order', ordering='ref_code')
    def reference(self, obj):
        return f'#{obj.ref_code or obj.pk}'

    @admin.display(description='Total')
    def total(self, obj):
        return money(obj.get_total())

    @admin.display(description='Status')
    def status(self, obj):
        if not obj.ordered:
            return badge('Not paid')
        return badge(*order_status(obj))

    @admin.display(description='Items')
    def items_summary(self, obj):
        if not obj.pk:
            return '—'
        items = obj.items.select_related('book')
        rows = format_html_join(
            '', '<tr><td><img class="bb-cover" src="{}" alt=""></td><td><strong>{}</strong></td>'
                '<td class="bb-num">{} ×</td><td class="bb-num">{}</td></tr>',
            ((item.book.image_url, item.book.title, item.quantity, money(item.get_final_price())) for item in items),
        )
        coupon = ''
        if obj.coupon:
            coupon = format_html(
                '<tr><td></td><td>Promo code <span class="bb-badge is-brand">{}</span></td><td></td>'
                '<td class="bb-num">−{}</td></tr>', obj.coupon.code, money(obj.coupon.amount),
            )
        return format_html(
            '<table class="bb-items">{}{}<tr class="bb-items-total"><td></td><td>Total</td><td></td>'
            '<td class="bb-num">{}</td></tr></table>',
            rows, coupon, money(obj.get_total()),
        )

    @admin.action(description='Mark as sent (being delivered)')
    def mark_delivered(self, request, queryset):
        updated = queryset.update(being_delivered=True)
        self.message_user(request, f'{updated} orders marked as sent.')

    @admin.action(description='Mark as received')
    def mark_received(self, request, queryset):
        updated = queryset.update(received=True)
        self.message_user(request, f'{updated} orders marked as received.')

    @admin.action(description='Grant refund')
    def grant_refunds(self, request, queryset):
        updated = queryset.update(refund_granted=True)
        self.message_user(request, f'Refunds granted for {updated} orders.')


@admin.register(OrderItem)
class OrderItemAdmin(StoreAdmin):
    """Order lines are shown on each order's page; this list stays reachable but out of the menu."""
    list_display = ['book', 'user', 'quantity', 'line_total', 'ordered']
    list_filter = ['ordered']
    list_select_related = ['book', 'user']
    search_fields = ['user__email', 'book__title', 'book__author__name']
    autocomplete_fields = ['book', 'user']

    def has_module_permission(self, request):
        return False

    @admin.display(description='Total')
    def line_total(self, obj):
        return money(obj.get_final_price())


@admin.register(Payment)
class PaymentAdmin(StoreAdmin):
    list_display = ['stripe_charge_id', 'user', 'amount_display', 'timestamp']
    list_select_related = ['user']
    list_filter = ['timestamp']
    search_fields = ['user__email', 'stripe_charge_id']
    readonly_fields = ['timestamp', 'stripe_charge_id']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    @admin.display(description='Amount', ordering='amount')
    def amount_display(self, obj):
        return money(obj.amount)


@admin.register(Refund)
class RefundAdmin(StoreAdmin):
    list_display = ['order', 'email', 'short_reason', 'accepted']
    list_filter = ['accepted']
    list_editable = ['accepted']
    list_select_related = ['order']
    search_fields = ['order__ref_code', 'email', 'reason']
    autocomplete_fields = ['order']
    actions = ['accept_refunds', 'reject_refunds']

    @admin.display(description='Reason')
    def short_reason(self, obj):
        return obj.reason if len(obj.reason) <= 60 else obj.reason[:57] + '…'

    @admin.action(description='Accept refund requests')
    def accept_refunds(self, request, queryset):
        updated = queryset.update(accepted=True)
        self.message_user(request, f'{updated} refund requests accepted.')

    @admin.action(description='Reject refund requests')
    def reject_refunds(self, request, queryset):
        updated = queryset.update(accepted=False)
        self.message_user(request, f'{updated} refund requests rejected.')


# ==================== MARKETING ====================

@admin.register(Coupon)
class CouponAdmin(StoreAdmin):
    list_display = ['code', 'amount', 'status', 'valid_from', 'valid_to', 'active']
    list_editable = ['active', 'amount']
    list_filter = [CouponStatusFilter]
    search_fields = ['code']
    ordering = ['-valid_to']
    fieldsets = (
        (None, {
            'fields': ('code', 'amount', 'active'),
            'description': 'The discount is a fixed amount in US dollars, taken off the order total.',
        }),
        ('When it works', {'fields': (('valid_from', 'valid_to'),)}),
    )

    @admin.display(description='Status')
    def status(self, obj):
        now = timezone.now()
        if not obj.active:
            return badge('Switched off')
        if obj.valid_to < now:
            return badge('Expired', 'is-danger')
        if obj.valid_from > now:
            return badge('Scheduled', 'is-brand')
        return badge('Live', 'is-success')


# ==================== CUSTOMERS ====================

@admin.register(Address)
class AddressAdmin(StoreAdmin):
    list_display = ['user', 'full_name', 'street_address', 'city', 'country', 'address_type', 'default']
    list_select_related = ['user']
    list_filter = ['address_type', 'default', 'country']
    list_editable = ['default']
    search_fields = ['user__email', 'first_name', 'last_name', 'street_address', 'city', 'zip_code']
    autocomplete_fields = ['user']
    actions = ['set_default', 'unset_default']

    @admin.display(description='Name')
    def full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip() or '—'

    @admin.action(description='Make default address')
    def set_default(self, request, queryset):
        # Only one default per user and address type
        for address in queryset:
            Address.objects.filter(user=address.user, address_type=address.address_type).update(default=False)
        updated = queryset.update(default=True)
        self.message_user(request, f'{updated} addresses set as default.')

    @admin.action(description='Stop being the default')
    def unset_default(self, request, queryset):
        updated = queryset.update(default=False)
        self.message_user(request, f'{updated} addresses are no longer the default.')


@admin.register(Wishlist)
class WishlistAdmin(StoreAdmin):
    list_display = ['user', 'book', 'book_price', 'availability']
    list_select_related = ['user', 'book']
    search_fields = ['user__email', 'book__title', 'book__author__name']
    autocomplete_fields = ['user', 'book']

    @admin.display(description='Price')
    def book_price(self, obj):
        return money(obj.book.final_price)

    @admin.display(description='For sale')
    def availability(self, obj):
        return badge('Available', 'is-success') if obj.book.is_available else badge('Unavailable', 'is-danger')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ['book']


@admin.register(Cart)
class CartAdmin(StoreAdmin):
    list_display = ['user', 'item_count', 'updated_at']
    list_select_related = ['user']
    search_fields = ['user__email']
    inlines = [CartItemInline]
    ordering = ['-updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_items=Count('items', filter=Q(items__quantity__gt=0)))

    @admin.display(description='Items', ordering='num_items')
    def item_count(self, obj):
        return obj.total_items
