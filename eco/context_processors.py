from django.db.models import Sum

from .models import CartItem, Wishlist


def cart_count(request):
    """Cart size for the header badge and the user's wishlist, so book cards can show saved state."""
    count = 0
    wishlist_ids = set()
    if request.user.is_authenticated:
        count = CartItem.objects.filter(cart__user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
        wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True))
    return {'cart_count': count, 'wishlist_ids': wishlist_ids}
