from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

DEFAULT_CURRENCY = 'usd'


def user_currency(user):
    """The currency code a user prefers, falling back to US dollars."""
    if user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.currency in settings.CURRENCIES:
            return profile.currency
    return DEFAULT_CURRENCY


def currency_info(code):
    info = settings.CURRENCIES.get(code, settings.CURRENCIES[DEFAULT_CURRENCY])
    return {'code': code, **info}


def format_money(amount_usd, code=DEFAULT_CURRENCY):
    """Convert a US dollar amount and format it with the currency symbol, e.g. '৳1,220' or '$9.99'."""
    info = currency_info(code)
    value = Decimal(str(amount_usd or 0)) * Decimal(str(info['rate']))
    places = Decimal(1).scaleb(-info['decimals'])
    value = value.quantize(places, rounding=ROUND_HALF_UP)
    return f"{info['symbol']}{value:,.{info['decimals']}f}"
