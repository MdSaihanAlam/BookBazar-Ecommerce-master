from django import template

from store.currency import DEFAULT_CURRENCY, format_money

register = template.Library()


@register.simple_tag(takes_context=True)
def money(context, amount_usd):
    """Show a US dollar amount in the visitor's currency: {% money book.price %} or {% money total as total_text %}."""
    currency = context.get('currency') or {}
    return format_money(amount_usd, currency.get('code', DEFAULT_CURRENCY))
