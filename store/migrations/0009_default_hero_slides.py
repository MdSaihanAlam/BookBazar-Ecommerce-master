from django.db import migrations


def add_default_slides(apps, schema_editor):
    """Start the admin with the slides the home page already showed: three featured books and free shipping."""
    HeroSlide = apps.get_model('eco', 'HeroSlide')
    Book = apps.get_model('eco', 'Book')
    if HeroSlide.objects.exists():
        return

    books = Book.objects.filter(is_available=True, featured=True).order_by('-created_at')[:3]
    for order, (book, tone) in enumerate(zip(books, ['indigo', 'teal', 'rose']), start=1):
        HeroSlide.objects.create(book=book, tone=tone, icon='book', sort_order=order)

    HeroSlide.objects.create(
        eyebrow='Free shipping',
        eyebrow_bn='ফ্রি শিপিং',
        title='From our shelves to your door, anywhere',
        title_bn='আমাদের তাক থেকে আপনার দরজায়, যেকোনো জায়গায়',
        text='On every order, no minimum',
        text_bn='প্রতিটি অর্ডারে, কোনো ন্যূনতম সীমা নেই',
        button_label='Browse books',
        button_label_bn='বই দেখুন',
        link='/products/',
        icon='globe',
        tone='orange',
        sort_order=10,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('eco', '0008_hero_slides'),
    ]

    operations = [
        migrations.RunPython(add_default_slides, migrations.RunPython.noop),
    ]
