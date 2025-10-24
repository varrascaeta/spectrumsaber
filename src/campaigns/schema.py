# Strawberry imports
import strawberry
import strawberry_django
from strawberry.types import Info
# gqlauth imports
from gqlauth.core.types_ import GQLAuthError, GQLAuthErrors
from gqlauth.core.utils import get_user
# Project imports
from src.campaigns.types import *


@strawberry.type
class CampaignQuery:
    # Coverage
    @strawberry.field
    def coverages(
        self,
        info: Info,
        filters: CoverageFilter | None = None,
    ) -> list[CoverageType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = Coverage.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def campaigns(
        self,
        info: Info,
        filters: CampaignFilter | None = None,
    ) -> list[CampaignType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = Campaign.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def data_points(
        self,
        info: Info,
        filters: DataPointFilter | None = None,
    ) -> list[DataPointType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = DataPoint.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def categories(
        self,
        info: Info,
        filters: CategoryFilter | None = None,
    ) -> list[CategoryType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = Category.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def measurements(
        self,
        info: Info,
        filters: MeasurementFilter | None = None,
    ) -> list[MeasurementType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = Measurement.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def districts(
        self,
        info: Info,
        filters: DistrictFilter | None = None,
    ) -> list[DistrictType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = District.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def measuring_tools(
        self,
        info: Info,
        filters: MeasuringToolFilter | None = None,
    ) -> list[MeasuringToolType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = MeasuringTool.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs

    @strawberry.field
    def spreadsheets(
        self,
        info: Info,
        filters: SpreadsheetFilter | None = None,
    ) -> list[SpreadsheetType]:
        user = get_user(info)
        if not user.is_authenticated:
            raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)

        qs = Spreadsheet.objects.all()
        if filters:
            qs = strawberry_django.filters.apply(filters, qs)
        return qs
