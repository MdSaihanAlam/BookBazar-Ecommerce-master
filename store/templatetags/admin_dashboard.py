from datetime import timedelta

from django import template
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from store.models import Book, Order, Payment

register = template.Library()

LOW_STOCK = 5


def changelist(model, query=''):
    url = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')
    return f'{url}?{query}' if query else url


def order_status(order):
    """A short label and badge style for where an order is in its life cycle."""
    if order.refund_granted:
        return 'Refunded', 'is-danger'
    if order.refund_requested:
        return 'Refund requested', 'is-warning'
    if order.received:
        return 'Received', 'is-success'
    if order.being_delivered:
        return 'On the way', 'is-brand'
    return 'To ship', 'is-warning'


@register.simple_tag
def admin_dashboard():
    """Headline numbers and short lists for the admin home page."""
    month_ago = timezone.now() - timedelta(days=30)
    paid_orders = Order.objects.filter(ordered=True)
    available = Book.objects.filter(is_available=True)
    customers = get_user_model().objects.filter(is_staff=False)

    recent_orders = []
    for order in paid_orders.select_related('user').order_by('-ordered_date')[:6]:
        label, style = order_status(order)
        recent_orders.append({
            'order': order,
            'url': reverse('admin:eco_order_change', args=[order.pk]),
            'total': order.get_total(),
            'status': label,
            'status_style': style,
        })

    low_stock = available.filter(stock_quantity__lt=LOW_STOCK)
    return {
        'revenue_30d': Payment.objects.filter(timestamp__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0,
        'revenue_total': Payment.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'orders_total': paid_orders.count(),
        'orders_30d': paid_orders.filter(ordered_date__gte=month_ago).count(),
        'to_ship': paid_orders.filter(being_delivered=False, received=False).count(),
        'refunds_open': paid_orders.filter(refund_requested=True, refund_granted=False).count(),
        'books': available.count(),
        'low_stock_count': low_stock.count(),
        'customers': customers.count(),
        'customers_30d': customers.filter(date_joined__gte=month_ago).count(),
        'recent_orders': recent_orders,
        'low_stock': low_stock.select_related('author').order_by('stock_quantity', 'title')[:6],
        'links': {
            'orders': changelist(Order, 'ordered__exact=1'),
            'to_ship': changelist(Order, 'ordered__exact=1&being_delivered__exact=0&received__exact=0'),
            'refunds': changelist(Order, 'refund_requested__exact=1&refund_granted__exact=0'),
            'books': changelist(Book),
            'low_stock': changelist(Book, f'is_available__exact=1&stock_quantity__lt={LOW_STOCK}'),
            'customers': changelist(get_user_model(), 'is_staff__exact=0'),
            'payments': changelist(Payment),
        },
    }
