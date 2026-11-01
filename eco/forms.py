from django import forms
from django_countries.widgets import CountrySelectWidget
from .models import Address, Book, Category
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _


class PaymentForm(forms.Form):
    stripeToken = forms.CharField()


class ContactForm(forms.Form):
    name = forms.CharField(
        label=_("Your name"),
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': _('Your full name')})
    )
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={'placeholder': _('Your email address')})
    )
    subject = forms.CharField(
        label=_("Subject"),
        widget=forms.TextInput(attrs={'placeholder': _('What is this about?')})
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={'placeholder': _('Your message...'), 'rows': 5})
    )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name.strip()) < 2:
            raise forms.ValidationError(_("Name must be at least 2 characters long."))
        return name.strip()

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if len(subject.strip()) < 5:
            raise forms.ValidationError(_("Subject must be at least 5 characters long."))
        return subject.strip()

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if len(message.strip()) < 10:
            raise forms.ValidationError(_("Message must be at least 10 characters long."))
        return message.strip()


class AddressForm(forms.ModelForm):
    first_name = forms.CharField(label=_("First name"), max_length=100)
    last_name = forms.CharField(label=_("Last name"), max_length=100)
    email = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}))
    phone_number = forms.CharField(
        label=_("Phone number"), max_length=20,
        help_text=_("Include your country code so the courier can reach you."),
        widget=forms.TextInput(attrs={'placeholder': '+44 20 7946 0958', 'autocomplete': 'tel'})
    )
    alternate_email = forms.EmailField(label=_("Alternate email"), required=False)
    is_business_address = forms.BooleanField(label=_("This is a business address"), required=False)
    city = forms.CharField(label=_("City"))

    class Meta:
        model = Address
        fields = [
            'first_name', 'last_name', 'street_address', 'apartment_address',
            'city', 'zip_code', 'country', 'email', 'phone_number',
            'alternate_email', 'is_business_address', 'default'
        ]
        labels = {
            'street_address': _("Street address"),
            'apartment_address': _("Apartment, suite, etc."),
            'zip_code': _("Postal code"),
            'country': _("Country"),
            'default': _("Use as my default delivery address"),
        }
        widgets = {
            'street_address': forms.TextInput(attrs={'placeholder': _('Street name and number'), 'autocomplete': 'address-line1'}),
            'apartment_address': forms.TextInput(attrs={'placeholder': _('Apartment, suite or floor (optional)'), 'autocomplete': 'address-line2'}),
            'country': CountrySelectWidget(attrs={'autocomplete': 'country'}),
            'zip_code': forms.TextInput(attrs={'placeholder': _('e.g. 10001 or SW1A 1AA'), 'autocomplete': 'postal-code'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'additional_authors',
            'isbn',
            'isbn13',
            'category',
            'genre',
            'format_type',
            'condition',
            'publisher',
            'publication_date',
            'edition',
            'pages',
            'language',
            'price',
            'discount_price',
            'label1',
            'label2',
            'label3',
            'cover_image',
            'additional_images',
            'description',
            'excerpt',
            'stock_quantity',
            'is_available',
            'slug'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter book title'
            }),
            'author': forms.Select(attrs={
                'class': 'form-control'
            }),
            'additional_authors': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter additional authors (comma separated)'
            }),
            'isbn': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ISBN (10 digits)'
            }),
            'isbn13': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ISBN-13 (13 digits)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'genre': forms.Select(attrs={
                'class': 'form-control'
            }),
            'format_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-control'
            }),
            'publisher': forms.Select(attrs={
                'class': 'form-control'
            }),
            'publication_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'edition': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter edition (e.g., First Edition)'
            }),
            'pages': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of pages',
                'min': '1'
            }),
            'language': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter language'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'label1': forms.Select(attrs={
                'class': 'form-control'
            }),
            'label2': forms.Select(attrs={
                'class': 'form-control'
            }),
            'label3': forms.Select(attrs={
                'class': 'form-control'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'additional_images': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter book description...'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter book excerpt...'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stock quantity',
                'min': '0'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank to generate from title'
            }),
        }
        labels = {
            'cover_image': 'Book Cover Image',
            'additional_images': 'Additional Images',
            'is_available': 'Available for purchase',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].required = True
        self.fields['category'].required = True
        self.fields['slug'].required = False
        self.fields['cover_image'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })
        self.fields['additional_images'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title.strip()) < 2:
            raise forms.ValidationError("Title must be at least 2 characters long.")
        return title.strip()

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if isbn and len(isbn.strip()) not in [10, 13]:
            raise forms.ValidationError("ISBN must be 10 or 13 digits long.")
        return isbn.strip() if isbn else isbn

    def clean_isbn13(self):
        isbn13 = self.cleaned_data.get('isbn13')
        if isbn13 and len(isbn13.strip()) != 13:
            raise forms.ValidationError("ISBN-13 must be exactly 13 digits long.")
        return isbn13.strip() if isbn13 else isbn13

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price

    def clean_discount_price(self):
        discount_price = self.cleaned_data.get('discount_price')
        price = self.cleaned_data.get('price')

        if discount_price:
            if discount_price <= 0:
                raise forms.ValidationError("Discount price must be greater than 0.")
            if price and discount_price >= price:
                raise forms.ValidationError("Discount price must be less than regular price.")

        return discount_price

    def clean_stock_quantity(self):
        stock_quantity = self.cleaned_data.get('stock_quantity')
        if stock_quantity is None or stock_quantity < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock_quantity

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
        if pages and pages <= 0:
            raise forms.ValidationError("Number of pages must be greater than 0.")
        return pages

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description.strip()) < 10:
            raise forms.ValidationError("Description must be at least 10 characters long.")
        return description.strip()

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug and Book.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A book with this slug already exists.")
        return slug

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category description',
                'rows': 3
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name').strip()
        if len(name) < 2:
            raise forms.ValidationError("Category name must be at least 2 characters long.")
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()

        return instance
