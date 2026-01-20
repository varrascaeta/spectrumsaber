# Django imports
from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

# Project imports
from src.places.models import Country, District, Province


# Utils
def get_admin_link(obj, app, model, name_field="name"):
    return mark_safe(
        '<a href="{}">{}</a>'.format(
            reverse(
                "admin:{}_{}_change".format(app, model._meta.model_name),
                args=(obj.id,),
            ),
            getattr(obj, name_field),
        )
    )


# Filters
class CountryFilter(AutocompleteFilter):
    title = "Country"
    field_name = "country"


class ProvinceFilter(AutocompleteFilter):
    title = "Province"
    field_name = "province"


class DistrictFilter(AutocompleteFilter):
    title = "District"
    field_name = "district"


# Inlines
class ProvinceInline(admin.TabularInline):
    model = Province
    extra = 0
    fields = ("get_link", "code")
    readonly_fields = ("get_link",)
    ordering = ("name",)

    def get_link(self, obj):
        return get_admin_link(obj, "places", Province)

    get_link.short_description = "Province"


class DistrictInline(admin.TabularInline):
    model = District
    extra = 0
    fields = ("get_link", "code")
    readonly_fields = ("get_link",)
    ordering = ("name",)

    def get_link(self, obj):
        return get_admin_link(obj, "places", District)

    get_link.short_description = "District"


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "code")
    inlines = [ProvinceInline]

    fieldsets = [
        ("Country Details", {"fields": ("name", "code")}),
    ]


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "code")
    inlines = [DistrictInline]
    list_filter = (CountryFilter,)

    fieldsets = [
        ("Province Details", {"fields": ("name", "code", "country")}),
    ]


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "code", "province")
    list_filter = (ProvinceFilter,)

    fieldsets = [
        ("District Details", {"fields": ("name", "code", "province")}),
    ]
