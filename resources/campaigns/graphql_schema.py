# Standard imports
# Extra imports
import graphene
from graphene_django import DjangoObjectType
# Project imports
from resources.campaigns.models import (
    Campaign,
    Category,
    Coverage,
    DataPoint,
    Measurement
)


class CampaignType(DjangoObjectType):
    class Meta:
        model = Campaign
        fields = "__all__"


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = "__all__"


class CoverageType(DjangoObjectType):
    class Meta:
        model = Coverage
        fields = "__all__"


class DataPointType(DjangoObjectType):
    class Meta:
        model = DataPoint
        fields = "__all__"


class MeasurementType(DjangoObjectType):
    class Meta:
        model = Measurement
        fields = "__all__"


class Query(graphene.ObjectType):
    campaigns = graphene.List(CampaignType)
    categories = graphene.List(CategoryType)
    coverages = graphene.List(CoverageType)
    data_points = graphene.List(DataPointType)
    measurements = graphene.List(MeasurementType)

    def resolve_campaigns(self, info):
        return Campaign.objects.all()

    def resolve_categories(self, info):
        return Category.objects.all()

    def resolve_coverages(self, info):
        return Coverage.objects.all()

    def resolve_data_points(self, info):
        return DataPoint.objects.all()

    def resolve_measurements(self, info):
        return Measurement.objects.all()


schema = graphene.Schema(query=Query)
