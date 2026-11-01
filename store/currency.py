from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils.translation import gettext_lazy as _

DEFAULT_CURRENCY = 'usd'
SESSION_CURRENCY = 'currency'

CURRENCY_NAMES = {
    'usd': _('US dollar'),
    'eur': _('Euro'),
    'gbp': _('British pound'),
    'bdt': _('Bangladeshi taka'),
    'inr': _('Indian rupee'),
    'cad': _('Canadian dollar'),
    'aud': _('Australian dollar'),
    'jpy': _('Japanese yen'),
}

# Used to pick a sensible currency for first-time visitors from their browser's language list
REGION_CURRENCIES = {
    'US': 'usd', 'GB': 'gbp', 'BD': 'bdt', 'IN': 'inr', 'CA': 'cad', 'AU': 'aud', 'JP': 'jpy',
    **{region: 'eur' for region in (
        'AT', 'BE', 'CY', 'DE', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'IE', 'IT',
        'LT', 'LU', 'LV', 'MT', 'NL', 'PT', 'SI', 'SK',
    )},
}
LANGUAGE_CURRENCIES = {'bn': 'bdt', 'ja': 'jpy', 'de': 'eur', 'fr': 'eur', 'it': 'eur', 'nl': 'eur', 'fi': 'eur', 'el': 'eur'}


def browser_locales(accept_language):
    """(language, region) pairs from an Accept-Language header, in the order the browser lists them."""
    for part in accept_language.split(','):
        language, _sep, region = part.split(';')[0].strip().replace('_', '-').partition('-')
        yield language.lower(), region[:2].upper()


def browser_country(request):
    """The two-letter country of the visitor's first regional browser language (e.g. GB for en-GB), if any."""
    for _language, region in browser_locales(request.headers.get('accept-language', '')):
        if len(region) == 2 and region.isalpha():
            return region
    return None


def guess_currency(accept_language):
    """The currency matching the first browser language that names a known region or language, if any."""
    for language, region in browser_locales(accept_language):
        code = REGION_CURRENCIES.get(region) or LANGUAGE_CURRENCIES.get(language)
        if code in settings.CURRENCIES:
            return code
    return None


def request_currency(request):
    """The visitor's currency: their profile choice, then the one picked this session, then a guess from the browser."""
    user = request.user
    if user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.currency in settings.CURRENCIES:
            return profile.currency
    code = request.session.get(SESSION_CURRENCY)
    if code in settings.CURRENCIES:
        return code
    return guess_currency(request.headers.get('accept-language', '')) or DEFAULT_CURRENCY


def currency_info(code):
    if code not in settings.CURRENCIES:
        code = DEFAULT_CURRENCY
    return {'code': code, 'name': CURRENCY_NAMES.get(code, code.upper()), **settings.CURRENCIES[code]}


def format_money(amount_usd, code=DEFAULT_CURRENCY):
    """Convert a US dollar amount and format it with the currency symbol, e.g. '৳1,220' or '$9.99'."""
    info = currency_info(code)
    value = Decimal(str(amount_usd or 0)) * Decimal(str(info['rate']))
    places = Decimal(1).scaleb(-info['decimals'])
    value = value.quantize(places, rounding=ROUND_HALF_UP)
    return f"{info['symbol']}{value:,.{info['decimals']}f}"
