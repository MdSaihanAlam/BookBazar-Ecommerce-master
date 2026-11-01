from django.apps import AppConfig


class StoreConfig(AppConfig):
    name = 'store'
    # The app was first created as "eco"; keeping that label means the existing database
    # tables (eco_book, eco_order, ...) and migration history still match.
    label = 'eco'
    verbose_name = 'Store'
