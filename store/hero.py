"""The home page banner slides: the ones staff set up in the admin, or sensible automatic ones."""
from django.urls import reverse
from django.utils.translation import get_language, gettext as _

from .models import HeroSlide

ICON_CLASSES = {
    'book': 'fa-book-open',
    'truck': 'fa-truck-fast',
    'globe': 'fa-earth-asia',
    'tag': 'fa-tag',
    'gift': 'fa-gift',
    'star': 'fa-star',
}


def book_details(book, show_price=True):
    """The parts of a slide that can come from a book."""
    on_sale = book.is_on_sale
    return {
        'eyebrow': _('%(percent)s%% off this week') % {'percent': book.discount_percentage} if on_sale else _("Editor's pick"),
        'eyebrow_icon': 'fa-bolt' if on_sale else 'fa-star',
        'title': book.title,
        'text': book.author.name if book.author else _('Unknown author'),
        'link': book.get_absolute_url(),
        'price': book.final_price if show_price else None,
        'was_price': book.price if show_price and on_sale else None,
        'cover_url': book.image_url,
    }


def slide_from_model(slide, bangla):
    def pick(field):
        # Bangla readers get the Bangla wording when staff filled it in
        return (bangla and getattr(slide, f'{field}_bn')) or getattr(slide, field)

    data = {
        'tone': slide.tone,
        'eyebrow': '',
        'eyebrow_icon': ICON_CLASSES.get(slide.icon, 'fa-book-open'),
        'title': '',
        'text': '',
        'link': reverse('store:product-list'),
        'price': None,
        'was_price': None,
        'cover_url': None,
        'picture_url': None,
        'art_icon': ICON_CLASSES.get(slide.icon, 'fa-book-open'),
    }
    if slide.book:
        data.update(book_details(slide.book, slide.show_price))
    for field in ('eyebrow', 'title', 'text'):
        if pick(field):
            data[field] = pick(field)
    if slide.link:
        data['link'] = slide.link
    data['button_label'] = pick('button_label') or _('Shop now')
    if slide.image:
        data['picture_url'] = slide.image.url
        data['cover_url'] = None
    return data


def automatic_slides(books):
    """Used until staff add banner slides: the featured books, then free shipping."""
    tones = ['indigo', 'teal', 'rose']
    slides = []
    for tone, book in zip(tones, books):
        slides.append({'tone': tone, 'button_label': _('Shop now'), 'picture_url': None, 'art_icon': None,
                       **book_details(book)})
    slides.append({
        'tone': 'orange',
        'eyebrow': _('Free shipping'),
        'eyebrow_icon': 'fa-truck-fast',
        'title': _('From our shelves to your door, anywhere'),
        'text': _('On every order, no minimum'),
        'link': reverse('store:product-list'),
        'button_label': _('Browse books'),
        'price': None,
        'was_price': None,
        'cover_url': None,
        'picture_url': None,
        'art_icon': 'fa-earth-asia',
    })
    return slides


def hero_slides(fallback_books):
    bangla = (get_language() or '').startswith('bn')
    live = HeroSlide.objects.live().select_related('book', 'book__author')
    slides = [slide_from_model(slide, bangla) for slide in live]
    return slides or automatic_slides(fallback_books)
