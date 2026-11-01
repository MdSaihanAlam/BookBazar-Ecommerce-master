import datetime
import io
import textwrap
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from eco.models import Address, Author, Book, Category, Coupon, Publisher

DEMO_USER_EMAIL = 'demo@bookbazar.local'
DEMO_USER_PASSWORD = 'DemoReader2026!'

CATEGORIES = {
    'Science Fiction': 'Space, future worlds and big ideas.',
    'Mystery': 'Detectives, puzzles and whodunits.',
    "Children's Books": 'Stories for young readers.',
}

PUBLISHERS = ['Penguin Classics', 'HarperCollins', 'Vintage Books']

# (title, author, category, genre, format, year, price, discount, stock, featured, publisher, description)
BOOKS = [
    ('Pride and Prejudice', 'Jane Austen', 'Literature', 'CLASSIC', 'PAPERBACK', 1813, '12.99', '9.99', 40, True, 'Penguin Classics',
     'Elizabeth Bennet and Mr. Darcy navigate pride, prejudice and the marriage market of Regency England.'),
    ('Nineteen Eighty-Four', 'George Orwell', 'Fiction', 'FICTION', 'PAPERBACK', 1949, '14.50', None, 35, True, 'Penguin Classics',
     'In a society of total surveillance, Winston Smith begins to question the Party and its version of the truth.'),
    ('To Kill a Mockingbird', 'Harper Lee', 'Literature', 'CLASSIC', 'HARDCOVER', 1960, '18.00', '15.00', 25, True, 'HarperCollins',
     'Scout Finch grows up in a small Alabama town as her father defends a man the town has already judged.'),
    ('The Great Gatsby', 'F. Scott Fitzgerald', 'Literature', 'CLASSIC', 'PAPERBACK', 1925, '10.99', None, 30, False, 'Penguin Classics',
     'Nick Carraway is drawn into the glittering, hollow world of his mysterious neighbour Jay Gatsby.'),
    ('Dune', 'Frank Herbert', 'Science Fiction', 'SCI_FI', 'PAPERBACK', 1965, '19.99', '16.99', 20, True, 'Penguin Classics',
     'On the desert planet Arrakis, young Paul Atreides is caught up in a struggle over the most valuable substance in the universe.'),
    ('Foundation', 'Isaac Asimov', 'Science Fiction', 'SCI_FI', 'PAPERBACK', 1951, '15.99', None, 18, False, 'HarperCollins',
     'As a galactic empire declines, a mathematician sets out to shorten the dark age that will follow.'),
    ('The Hobbit', 'J.R.R. Tolkien', 'Fiction', 'FANTASY', 'HARDCOVER', 1937, '22.00', '18.50', 22, True, 'HarperCollins',
     'Bilbo Baggins leaves his comfortable home for an adventure with a wizard, thirteen dwarves and a dragon.'),
    ('The Hound of the Baskervilles', 'Arthur Conan Doyle', 'Mystery', 'MYSTERY', 'PAPERBACK', 1902, '9.99', '7.99', 28, False, 'Penguin Classics',
     'Sherlock Holmes and Dr. Watson investigate a legendary hound haunting a family on the Devon moors.'),
    ('Murder on the Orient Express', 'Agatha Christie', 'Mystery', 'MYSTERY', 'PAPERBACK', 1934, '13.99', None, 24, True, 'HarperCollins',
     'Snowbound on a luxury train, Hercule Poirot must find a killer among a carriage full of suspects.'),
    ('The Da Vinci Code', 'Dan Brown', 'Thiller', 'THRILLER', 'PAPERBACK', 2003, '16.99', '12.99', 30, False, 'Vintage Books',
     'A symbologist races across Europe to decode clues hidden in famous works of art.'),
    ('Romeo and Juliet', 'William Shakespeare', 'Drama', 'DRAMA', 'PAPERBACK', 1597, '8.99', None, 40, False, 'Penguin Classics',
     'Two young lovers from feuding families in Verona defy their houses, with tragic consequences.'),
    ('Death of a Salesman', 'Arthur Miller', 'Drama', 'DRAMA', 'PAPERBACK', 1949, '11.50', None, 15, False, 'Penguin Classics',
     'Ageing salesman Willy Loman confronts the gap between his dreams and the life he has actually lived.'),
    ("Charlotte's Web", 'E.B. White', "Children's Books", 'CHILDREN', 'HARDCOVER', 1952, '12.00', '9.50', 26, True, 'HarperCollins',
     'A pig named Wilbur and a clever spider named Charlotte form a friendship that changes everything on the farm.'),
    ('The Alchemist', 'Paulo Coelho', 'Fiction', 'FICTION', 'PAPERBACK', 1988, '14.00', '11.00', 32, False, 'HarperCollins',
     'A shepherd boy travels from Spain to Egypt in search of treasure and learns to follow his own path.'),
]

# Authors for books already in the database that have none
EXISTING_BOOK_AUTHORS = {
    'The English Patient': ('Michael Ondaatje', 'Literature'),
    'The Hunger Games': ('Suzanne Collins', None),
    'Harry potter': ('J.K. Rowling', None),
}

COUPONS = [('WELCOME10', '10.00'), ('READMORE5', '5.00')]

COVER_COLORS = ['#1e3a8a', '#7c2d12', '#065f46', '#581c87', '#9f1239', '#0f766e', '#92400e', '#334155']


def make_cover(title, author, color):
    width, height = 600, 900
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([30, 30, width - 30, height - 30], outline='#f8fafc', width=4)
    try:
        title_font = ImageFont.truetype('georgia.ttf', 54)
        author_font = ImageFont.truetype('georgia.ttf', 32)
    except OSError:
        title_font = author_font = ImageFont.load_default()

    y = 220
    for line in textwrap.wrap(title, width=16):
        line_width = draw.textlength(line, font=title_font)
        draw.text(((width - line_width) / 2, y), line, fill='#f8fafc', font=title_font)
        y += 70
    author_width = draw.textlength(author, font=author_font)
    draw.text(((width - author_width) / 2, height - 170), author, fill='#e2e8f0', font=author_font)

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = 'Add demo authors, books, coupons and a demo customer. Safe to run more than once.'

    def get_author(self, name):
        author, _ = Author.objects.get_or_create(slug=slugify(name), defaults={'name': name})
        return author

    @transaction.atomic
    def handle(self, *args, **options):
        for name, description in CATEGORIES.items():
            Category.objects.get_or_create(slug=slugify(name), defaults={'name': name, 'description': description})
        publishers = {name: Publisher.objects.get_or_create(name=name)[0] for name in PUBLISHERS}

        created = 0
        for index, (title, author, category, genre, format_type, year, price, discount, stock, featured, publisher, description) in enumerate(BOOKS):
            slug = slugify(title)
            if Book.objects.filter(slug=slug).exists():
                continue
            book = Book(
                title=title,
                slug=slug,
                author=self.get_author(author),
                category=Category.objects.get(name=category),
                genre=genre,
                format_type=format_type,
                publisher=publishers[publisher],
                publication_date=datetime.date(year, 1, 1),
                price=Decimal(price),
                discount_price=Decimal(discount) if discount else None,
                stock_quantity=stock,
                featured=featured,
                label1='B' if featured else 'N',
                description=description,
            )
            book.cover_image.save(f'demo-{slug}.png', make_cover(title, author, COVER_COLORS[index % len(COVER_COLORS)]), save=False)
            book.save()
            created += 1

        for title, (author, category) in EXISTING_BOOK_AUTHORS.items():
            book = Book.objects.filter(title=title, author__isnull=True).first()
            if book:
                book.author = self.get_author(author)
                if category and not book.category:
                    book.category = Category.objects.get(name=category)
                book.save()

        for code, amount in COUPONS:
            Coupon.objects.update_or_create(code=code, defaults={
                'amount': Decimal(amount),
                'active': True,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + datetime.timedelta(days=365),
            })

        User = get_user_model()
        user, user_created = User.objects.get_or_create(email=DEMO_USER_EMAIL)
        if user_created:
            user.set_password(DEMO_USER_PASSWORD)
            user.save()
        Address.objects.get_or_create(user=user, address_type='S', defaults={
            'first_name': 'Demo',
            'last_name': 'Reader',
            'email': DEMO_USER_EMAIL,
            'phone_number': '+8801700000000',
            'street_address': 'House 12, Road 5',
            'city': 'Dhaka',
            'zip_code': '1212',
            'country': 'BD',
            'default': True,
        })

        self.stdout.write(self.style.SUCCESS(
            f'Added {created} demo books. Coupons: {", ".join(c for c, _ in COUPONS)}. '
            f'Demo customer: {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD}'
        ))
