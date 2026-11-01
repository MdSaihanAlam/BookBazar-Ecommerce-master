from django.conf import settings
from django.utils import translation


def user_language(user):
    """The site language for a user: their profile choice if the site is translated into it, else the default."""
    supported = {code for code, _name in settings.LANGUAGES}
    if user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.language in supported:
            return profile.language
    return settings.LANGUAGE_CODE


def activate_user_language(request):
    """Switch the current request to the user's language, e.g. right after they sign in or change it."""
    translation.activate(user_language(request.user))
    request.LANGUAGE_CODE = translation.get_language()


class UserLanguageMiddleware:
    """Show the site in the language chosen on the signed-in user's profile."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = user_language(request.user)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', language)
        translation.deactivate()
        return response
