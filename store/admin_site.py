from django.contrib import admin


class BookBazarAdminSite(admin.AdminSite):
    """The admin, with models grouped by what staff are doing rather than by code module."""

    site_header = 'BookBazar admin'
    site_title = 'BookBazar admin'
    index_title = 'Store overview'

    # (section name, key used in CSS classes, models as "app_label.model_name"); anything unlisted lands in "Other"
    SECTIONS = [
        ('Catalog', 'catalog', ['eco.book', 'eco.category', 'eco.author', 'eco.publisher', 'eco.bookreview']),
        ('Sales', 'sales', ['eco.order', 'eco.payment', 'eco.refund']),
        ('Marketing', 'marketing', ['eco.heroslide', 'eco.coupon']),
        ('Customers', 'customers', ['users.customuser', 'users.userprofile', 'eco.address', 'eco.wishlist', 'eco.cart']),
        ('Access', 'access', ['auth.group']),
    ]

    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        if app_label:
            # A single app's own index page keeps Django's layout
            return apps

        models = {
            f"{app['app_label']}.{model['object_name'].lower()}": model
            for app in apps for model in app['models']
        }
        sections = []
        for name, key, wanted in self.SECTIONS:
            section_models = [models.pop(label) for label in wanted if label in models]
            if section_models:
                sections.append(self._section(name, key, section_models))
        if models:
            sections.append(self._section('Other', 'other', sorted(models.values(), key=lambda m: m['name'])))
        return sections

    @staticmethod
    def _section(name, key, models):
        return {
            'name': name,
            'app_label': key,
            'app_url': models[0]['admin_url'],
            'has_module_perms': True,
            'models': models,
        }


class FriendlyAdminMixin:
    """Plain page titles ("Books", "Edit book") instead of Django's "Select book to change"."""

    empty_value_display = '—'
    list_per_page = 25

    def changelist_view(self, request, extra_context=None):
        title = self.model._meta.verbose_name_plural
        extra_context = {'title': title[:1].upper() + title[1:], **(extra_context or {})}
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        name = self.model._meta.verbose_name
        if object_id is None:
            title = f'Add {name}'
        elif self.has_change_permission(request):
            title = f'Edit {name}'
        else:
            title = f'View {name}'
        extra_context = {'title': title, **(extra_context or {})}
        return super().changeform_view(request, object_id, form_url, extra_context)
