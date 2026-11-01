from django.db.models import Sum

from .currency import currency_info, user_currency
from .models import CartItem, Wishlist


def cart_count(request):
    """Cart size for the header badge, the user's wishlist so book cards can show saved state,
    and the currency prices are shown in."""
    count = 0
    wishlist_ids = set()
    if request.user.is_authenticated:
        count = CartItem.objects.filter(cart__user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
        wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True))
    return {
        'cart_count': count,
        'wishlist_ids': wishlist_ids,
        'currency': currency_info(user_currency(request.user)),
    }
