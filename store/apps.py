from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class BookBazarAdminConfig(AdminConfig):
    """Installs the BookBazar admin site in place of Django's default one."""
    default_site = 'store.admin_site.BookBazarAdminSite'


class StoreConfig(AppConfig):
    name = 'store'
    # The app was first created as "eco"; keeping that label means the existing database
    # tables (eco_book, eco_order, ...) and migration history still match.
    label = 'eco'
    verbose_name = 'Store'
