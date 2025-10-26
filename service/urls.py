# Django imports
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt


# Extra imports
from strawberry.django.views import AsyncGraphQLView

# Project imports
from service.schema import schema


urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="about.html"),
        name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path("admin/", admin.site.urls),
    re_path(r'^graphql/?$', csrf_exempt(AsyncGraphQLView.as_view(schema=schema)), name='graphql'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
