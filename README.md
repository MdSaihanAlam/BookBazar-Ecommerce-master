# 📚 BookBazar

An online bookstore built with **Django**. Readers can browse and search books, keep a wishlist, apply promo codes and pay by card through Stripe. The site is available in English and Bangla, and prices can be shown in several currencies.

## 🌟 Features
- Book catalogue with categories, search (press `Ctrl K` or `/` anywhere) and book pages
- Cart with a slide-out drawer, promo codes and Stripe checkout
- Wishlist, saved addresses, order history and account settings
- Language and currency picker for every visitor (English / বাংলা; USD, EUR, GBP, BDT, INR, CAD, AUD, JPY)
- Light and dark themes, mobile tab bar and page transitions
- Django admin for books, orders, coupons and users

## 🛠️ Tech stack
- **Backend:** Python 3.11, Django 4.2
- **Frontend:** Django templates, hand-written CSS and JavaScript (no framework)
- **Payments:** Stripe
- **Database:** SQLite by default

## 🗂️ Project layout
```
config/      Django project settings, root URLs, WSGI/ASGI entry points
store/       The shop: catalogue, cart, checkout, wishlist, addresses
users/       Custom email-based user model, sign-in, profile
templates/   HTML templates (store/ and users/)
static/      CSS, JavaScript and images (static/store/)
locale/      Translations (Bangla)
media/       Uploaded files such as book covers (not in git)
```

## 📦 Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/Saihan-DIU/BookBazar-Ecommerce-master.git
   cd BookBazar-Ecommerce-master
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create the database and some demo data**
   ```bash
   python manage.py migrate
   python manage.py seed_demo
   ```
5. **Create an admin account**
   ```bash
   python manage.py createsuperuser
   ```
6. **Run the development server**
   ```bash
   python manage.py runserver
   ```
   - Store: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## ⚙️ Configuration
Settings are read from environment variables (or a `.env` file):

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Standard Django settings |
| `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY` | Stripe keys (test keys are used by default) |
| `DATABASE_PATH` | Where the SQLite database lives |
| `RATE_EUR`, `RATE_GBP`, `RATE_BDT`, ... | Display exchange rates per US dollar |

## 🌍 Translations
After changing text in templates or Python code:
```bash
python manage.py makemessages -l bn
python manage.py compilemessages -l bn
```
Both commands need GNU gettext installed.

## 📜 License
Open source under the **MIT License**.

📌 **Developer:** Saihan | DIU
