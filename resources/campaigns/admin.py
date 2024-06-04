# Django imports
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
# Extra imports
from rangefilter.filters import DateRangeFilter
from admin_auto_filters.filters import AutocompleteFilter
# Project imports
from resources.campaigns.models import (
    Category,
    Coverage,
    Campaign,
    DataPoint,
    Measurement
)


# Utils
def get_admin_link(obj, app, model, name_field="name"):
    return mark_safe('<a href="{}">{}</a>'.format(
        reverse(
            "admin:{}_{}_change".format(app, model._meta.model_name),
            args=(obj.id,)
        ),
        getattr(obj, name_field)
    ))


# Inlines
class DataPointInline(admin.TabularInline):
    model = DataPoint
    extra = 0
    fields = ("get_link", "order", "latitude", "longitude")
    readonly_fields = ("get_link",)
    ordering = ("order",)

    def get_link(self, obj):
        return get_admin_link(obj, "campaigns", DataPoint)

    get_link.short_description = "Data Point"


class MeasurementInline(admin.TabularInline):
    model = Measurement
    extra = 0
    fields = ("get_link", "path")
    readonly_fields = ("get_link",)
    ordering = ("name",)

    def get_link(self, obj):
        return get_admin_link(obj, "campaigns", Measurement)

    get_link.short_description = "Measurement"

    def __init__(self, parent_model, admin_site, category=None):
        self.category = category
        super().__init__(parent_model, admin_site)

    def get_queryset(self, request):
        base_qs = super().get_queryset(request)
        if self.category:
            return base_qs.filter(category=self.category)


# Filters
class CoverageFilter(AutocompleteFilter):
    title = "Coverage"
    field_name = "coverage"


class CampaignFilter(AutocompleteFilter):
    title = "Campaign"
    field_name = "campaign"


class DataPointFilter(AutocompleteFilter):
    title = "Data Point"
    field_name = "data_point"


# Admins
class BaseFileAdmin(admin.ModelAdmin):
    list_display = [
        "__str__", "ftp_created_at", "updated_at"
    ]
    readonly_fields = ("created_at", "updated_at")

    def get_fieldsets(self, request, obj):
        return [
            (
                "FTP Data",
                {
                    "fields": (
                        "path",
                        "ftp_created_at"
                    )
                }
            ),
            (
                "Metadata",
                {
                    "fields": (
                        ("description", "metadata"),
                    )
                }
            )
        ]


@admin.register(Coverage)
class CoverageAdmin(BaseFileAdmin):
    search_fields = ("name", "path")

    def get_fieldsets(self, request, obj):
        coverage_fieldsets = [
            (
                "Coverage Details",
                {
                    "fields": (
                        "name",
                    )
                }
            ),
        ]
        return coverage_fieldsets + super().get_fieldsets(request, obj)
    pass


@admin.register(Campaign)
class CampaignAdmin(BaseFileAdmin):
    search_fields = ("name", "path")
    list_filter = (
        ("date", DateRangeFilter),
        CoverageFilter
    )
    inlines = [
        DataPointInline
    ]

    def get_list_display(self, request):
        base = super().get_list_display(request)
        return base[:1] + ["get_coverage", "date"] + base[1:]

    def get_fieldsets(self, request, obj):
        campaign_fieldsets = [
            (
                "Campaign Details",
                {
                    "fields": (
                        "name",
                        "external_id",
                        "coverage",
                        "measuring_tool",
                        "district"
                    )
                }
            ),
        ]
        return campaign_fieldsets + super().get_fieldsets(request, obj)

    def get_coverage(self, obj):
        if obj.coverage:
            return get_admin_link(obj.coverage, "campaigns", Coverage)

    get_coverage.short_description = "Coverage"


@admin.register(DataPoint)
class DataPointAdmin(BaseFileAdmin):
    search_fields = ("name", "path", "campaign__name")
    list_filter = (
        CampaignFilter,
    )
    ordering = ("campaign", "order")

    def get_list_display(self, request):
        base = super().get_list_display(request)
        return base[:1] + ["get_campaign"] + base[1:]

    def get_fieldsets(self, request, obj):
        data_point_fieldsets = [
            (
                "Data Point Details",
                {
                    "fields": (
                        "name",
                        "order",
                        "campaign",
                        "latitude",
                        "longitude"
                    )
                }
            ),
        ]
        return data_point_fieldsets + super().get_fieldsets(request, obj)

    def get_campaign(self, obj):
        if obj.campaign:
            return get_admin_link(obj.campaign, "campaigns", Campaign)

    def get_inline_instances(self, request, obj):
        inlines = super().get_inline_instances(request, obj)
        if obj:
            for category in Category.objects.all():
                inline = type(
                    f'{category}MeasurementInline',
                    (MeasurementInline,),
                    {
                        'verbose_name': category,
                        'verbose_name_plural': f'{category} Measurements'
                    }
                )
                inlines.append(
                    inline(self.model, self.admin_site, category=category)
                )
        return inlines + super().get_inline_instances(request, obj)

    get_campaign.short_description = "Campaign"


@admin.register(Measurement)
class MeasurementAdmin(BaseFileAdmin):
    list_filter = (
        DataPointFilter,
    )

    def get_list_display(self, request):
        base = super().get_list_display(request)
        extra = ["get_category", "get_data_point", "get_campaign"]
        return base[:1] + extra + base[1:]

    def get_fieldsets(self, request, obj):
        data_point_fieldsets = [
            (
                "Measurement Details",
                {
                    "fields": (
                        "name",
                        "category",
                        "data_point",
                    )
                }
            ),
        ]
        return data_point_fieldsets + super().get_fieldsets(request, obj)

    def get_category(self, obj):
        if obj.category:
            return get_admin_link(obj.category, "campaigns", Category)

    def get_data_point(self, obj):
        if obj.data_point:
            return get_admin_link(obj.data_point, "campaigns", DataPoint)

    def get_campaign(self, obj):
        if obj.data_point and obj.data_point.campaign:
            return get_admin_link(
                obj.data_point.campaign, "campaigns", Campaign
            )

    get_category.short_description = "Category"
    get_data_point.short_description = "Data Point"
    get_campaign.short_description = "Campaign"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)

    list_display = [
        "__str__", "created_at",
    ]
