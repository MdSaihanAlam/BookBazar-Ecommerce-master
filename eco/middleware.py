from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers

SESSION_LANGUAGE = 'language'


def request_language(request):
    """The site language for a visitor: their profile choice, then the one picked this session,
    then the best match from their browser. Only languages the site is translated into count."""
    supported = {code for code, _name in settings.LANGUAGES}
    user = request.user
    if user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.language in supported:
            return profile.language
    language = request.session.get(SESSION_LANGUAGE)
    if language in supported:
        return language
    return translation.get_language_from_request(request)


def activate_user_language(request):
    """Switch the current request to the visitor's language, e.g. right after they sign in or change it."""
    translation.activate(request_language(request))
    request.LANGUAGE_CODE = translation.get_language()


class UserLanguageMiddleware:
    """Show the site in the visitor's language."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        activate_user_language(request)
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', request.LANGUAGE_CODE)
        patch_vary_headers(response, ('Accept-Language',))
        translation.deactivate()
        return response
