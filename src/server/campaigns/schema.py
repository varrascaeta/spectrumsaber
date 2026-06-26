# Standard imports
from datetime import date

# Strawberry imports
import strawberry
import strawberry_django

# gqlauth imports
from gqlauth.core.types_ import GQLAuthError, GQLAuthErrors
from gqlauth.core.utils import get_user
from strawberry.types import Info

# Project imports
from server.campaigns.gql_types import (
    CampaignFilter,
    CampaignType,
    CategoryFilter,
    CategoryType,
    CoverageFilter,
    CoverageType,
    DataPointFilter,
    DataPointType,
    DistrictFilter,
    DistrictType,
    MeasurementFilter,
    MeasurementType,
)
from server.campaigns.models import (
    Campaign,
    Category,
    Coverage,
    DataPoint,
    Measurement,
)
from server.places.models import District


def _authenticated_qs(info: Info, model):
    user = get_user(info)
    if not user.is_authenticated:
        raise GQLAuthError(code=GQLAuthErrors.UNAUTHENTICATED)
    return model.objects.all()


def _apply(filters, qs):
    return strawberry_django.filters.apply(filters, qs) if filters else qs


@strawberry.type
class CampaignQuery:
    @strawberry.field
    def coverages(self, info: Info, filters: CoverageFilter | None = None) -> list[CoverageType]:
        return _apply(filters, _authenticated_qs(info, Coverage))

    @strawberry.field
    def campaigns(
        self,
        info: Info,
        filters: CampaignFilter | None = None,
        date_gte: date | None = None,
        date_lte: date | None = None,
    ) -> list[CampaignType]:
        qs = _authenticated_qs(info, Campaign)
        if date_gte:
            qs = qs.filter(date__gte=date_gte)
        if date_lte:
            qs = qs.filter(date__lte=date_lte)
        return _apply(filters, qs)

    @strawberry.field
    def data_points(self, info: Info, filters: DataPointFilter | None = None) -> list[DataPointType]:
        return _apply(filters, _authenticated_qs(info, DataPoint))

    @strawberry.field
    def categories(self, info: Info, filters: CategoryFilter | None = None) -> list[CategoryType]:
        return _apply(filters, _authenticated_qs(info, Category))

    @strawberry.field
    def measurements(self, info: Info, filters: MeasurementFilter | None = None) -> list[MeasurementType]:
        return _apply(filters, _authenticated_qs(info, Measurement))

    @strawberry.field
    def districts(self, info: Info, filters: DistrictFilter | None = None) -> list[DistrictType]:
        return _apply(filters, _authenticated_qs(info, District))
