# Django imports
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
# Extra imports
from graphene_django.views import GraphQLView
# Project imports
from core_schema import schema


urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="about.html"),
        name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path("admin/", admin.site.urls),
    path("graphql/", GraphQLView.as_view(graphiql=True, schema=schema)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
