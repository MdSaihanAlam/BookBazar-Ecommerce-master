from django.contrib import admin
from django.utils.html import format_html
from mptt.admin import MPTTModelAdmin
from .models import (
    Author,
    Book,
    BookImage,
    BookReview,
    Cart,
    CartItem,
    Category,
    OrderItem,
    Order,
    Address,
    Payment,
    Coupon,
    Publisher,
    Refund,
    UserProfile,
    Wishlist
)
from .templatetags.admin_dashboard import order_status

admin.site.site_header = 'BookBazar admin'
admin.site.site_title = 'BookBazar admin'
admin.site.index_title = 'Store overview'


def badge(label, style=''):
    return format_html('<span class="bb-badge {}">{}</span>', style, label)


class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'image_preview']
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}


class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'website']
    search_fields = ['name']


class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 1

class BookAdmin(admin.ModelAdmin):
    list_display = [
        'cover',
        'book',
        'price',
        'discounted_price',
        'stock_quantity',
        'featured',
        'is_available',
    ]
    list_display_links = ['cover', 'book']
    list_select_related = ['author', 'category']
    list_per_page = 25
    list_filter = [
        'featured',
        'category',
        'author',
        'is_available',
        'genre',
        'format_type',
        'condition'
    ]
    list_editable = [
        'featured',
        'price',
        'is_available',
        'stock_quantity'
    ]
    search_fields = [
        'title',
        'author__name',
        'additional_authors',
        'isbn',
        'isbn13',
        'publisher__name',
        'genre',
        'description'
    ]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ['created_at', 'updated_at']
    inlines = [BookImageInline]

    actions = [
        'make_featured',
        'make_unfeatured',
        'mark_available',
        'mark_unavailable',
        'increase_stock',
        'clear_stock'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'author', 'additional_authors', 'isbn', 'isbn13', 'slug'
            )
        }),
        ('Categorization', {
            'fields': (
                'category', 'genre', 'format_type', 'condition'
            )
        }),
        ('Publishing & Pricing', {
            'fields': (
                'publisher', 'publication_date', 'edition', 'pages', 'language',
                'price', 'discount_price', 'featured'
            )
        }),
        ('Media & Content', {
            'fields': (
                'cover_image', 'additional_images', 'description', 'excerpt'
            )
        }),
        ('Inventory & Status', {
            'fields': (
                'stock_quantity', 'is_available', 'label1', 'label2', 'label3'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='')
    def cover(self, obj):
        return format_html('<img class="bb-cover" src="{}" alt="">', obj.image_url)

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
        if obj.stock_quantity < 5:
            return badge(f'Only {obj.stock_quantity} left', 'is-warning')
        return ''

    @admin.display(description='Sale price')
    def discounted_price(self, obj):
        if obj.discount_price and obj.discount_price < obj.price:
            return format_html('${} <span class="bb-badge is-brand">−{}%</span>', obj.discount_price, obj.discount_percentage)
        return '—'

    def make_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} books marked as featured.')
    make_featured.short_description = "Mark selected books as featured"

    def make_unfeatured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} books marked as not featured.')
    make_unfeatured.short_description = "Mark selected books as not featured"

    def mark_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} books marked as available.')
    mark_available.short_description = "Mark selected books as available"

    def mark_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} books marked as unavailable.')
    mark_unavailable.short_description = "Mark selected books as unavailable"

    def increase_stock(self, request, queryset):
        for book in queryset:
            book.stock_quantity += 10
            book.save()
        self.message_user(request, f'Increased stock by 10 for {queryset.count()} books.')
    increase_stock.short_description = "Increase stock by 10 for selected books"

    def clear_stock(self, request, queryset):
        updated = queryset.update(stock_quantity=0)
        self.message_user(request, f'Cleared stock for {updated} books.')
    clear_stock.short_description = "Clear stock (set to 0) for selected books"

class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'slug', 'book_count']
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['name']

    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Number of Books'

class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'book_display',
        'quantity',
        'get_final_price',
        'ordered'
    ]
    list_filter = ['ordered', 'user']
    search_fields = ['user__email', 'book__title', 'book__author__name']

    def book_display(self, obj):
        return str(obj.book)
    book_display.short_description = 'Book'

    def get_final_price(self, obj):
        return f"${obj.get_final_price():,.2f}"
    get_final_price.short_description = 'Total Price'

class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'reference',
        'user',
        'ordered_date',
        'total',
        'status',
        'being_delivered',
        'received',
        'refund_granted'
    ]
    list_display_links = ['reference']
    list_select_related = ['user']
    date_hierarchy = 'ordered_date'
    ordering = ['-ordered_date']
    list_per_page = 25
    list_filter = [
        'ordered',
        'ordered_date',
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted'
    ]
    search_fields = ['user__email', 'ref_code', 'shipping_address__street_address']
    list_editable = ['being_delivered', 'received', 'refund_granted']
    readonly_fields = ['ordered_date', 'start_date']

    actions = ['mark_delivered', 'mark_received', 'grant_refunds']

    @admin.display(description='Order', ordering='ref_code')
    def reference(self, obj):
        return f'#{obj.ref_code or obj.pk}'

    @admin.display(description='Total')
    def total(self, obj):
        return f'${obj.get_total():,.2f}'

    @admin.display(description='Status')
    def status(self, obj):
        if not obj.ordered:
            return badge('Not paid')
        return badge(*order_status(obj))

    def mark_delivered(self, request, queryset):
        updated = queryset.update(being_delivered=True)
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_delivered.short_description = "Mark selected orders as delivered"

    def mark_received(self, request, queryset):
        updated = queryset.update(received=True)
        self.message_user(request, f'{updated} orders marked as received.')
    mark_received.short_description = "Mark selected orders as received"

    def grant_refunds(self, request, queryset):
        updated = queryset.update(refund_granted=True)
        self.message_user(request, f'{updated} orders granted refunds.')
    grant_refunds.short_description = "Grant refunds for selected orders"

class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'apartment_address',
        'country',
        'zip_code',
        'address_type',
        'default'
    ]
    list_filter = ['country', 'address_type', 'default']
    search_fields = [
        'user__email',
        'street_address',
        'apartment_address',
        'zip_code'
    ]
    list_editable = ['default']

    actions = ['set_default', 'unset_default']

    def set_default(self, request, queryset):
        # Only one default per user and address type
        for address in queryset:
            Address.objects.filter(
                user=address.user, address_type=address.address_type
            ).update(default=False)
        updated = queryset.update(default=True)
        self.message_user(request, f'{updated} addresses set as default.')
    set_default.short_description = "Set selected addresses as default"

    def unset_default(self, request, queryset):
        updated = queryset.update(default=False)
        self.message_user(request, f'{updated} addresses unset as default.')
    unset_default.short_description = "Unset selected addresses as default"

class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'amount',
        'timestamp',
        'stripe_charge_id'
    ]
    list_filter = ['timestamp']
    search_fields = ['user__email', 'stripe_charge_id']
    readonly_fields = ['timestamp', 'stripe_charge_id']

class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'amount',
        'valid_from',
        'valid_to',
        'active'
    ]
    list_filter = ['active']
    search_fields = ['code']
    list_editable = ['active', 'amount']

class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'reason',
        'accepted',
        'email'
    ]
    list_filter = ['accepted']
    search_fields = ['order__ref_code', 'email', 'reason']
    list_editable = ['accepted']

    actions = ['accept_refunds', 'reject_refunds']

    def accept_refunds(self, request, queryset):
        updated = queryset.update(accepted=True)
        self.message_user(request, f'{updated} refund requests accepted.')
    accept_refunds.short_description = "Accept selected refund requests"

    def reject_refunds(self, request, queryset):
        updated = queryset.update(accepted=False)
        self.message_user(request, f'{updated} refund requests rejected.')
    reject_refunds.short_description = "Reject selected refund requests"

class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'stripe_customer_id',
        'one_click_purchasing',
        'get_orders_count',
        'get_addresses_count'
    ]
    search_fields = ['user__email', 'stripe_customer_id']
    list_filter = ['one_click_purchasing']

    def get_orders_count(self, obj):
        return obj.user.order_set.count()
    get_orders_count.short_description = 'Orders Count'

    def get_addresses_count(self, obj):
        return obj.user.address_set.count()
    get_addresses_count.short_description = 'Addresses Count'

class WishlistAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'book_display',
        'get_book_price',
        'get_book_availability'
    ]
    search_fields = ['user__email', 'book__title', 'book__author__name']

    def book_display(self, obj):
        return str(obj.book)
    book_display.short_description = 'Book'

    def get_book_price(self, obj):
        return f"${obj.book.price:.2f}"
    get_book_price.short_description = 'Price'

    def get_book_availability(self, obj):
        return badge('Available', 'is-success') if obj.book.is_available else badge('Unavailable', 'is-danger')
    get_book_availability.short_description = 'Available'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'updated_at']
    search_fields = ['user__email']
    inlines = [CartItemInline]


class BookReviewAdmin(admin.ModelAdmin):
    list_display = ['book', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    list_editable = ['is_approved']
    search_fields = ['book__title', 'user__email', 'title']


admin.site.register(Author, AuthorAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(BookReview, BookReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(Refund, RefundAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Wishlist, WishlistAdmin)