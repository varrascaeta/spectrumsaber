import serpy


class BaseSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    path = serpy.Field()
    description = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class CampaignSerializer(BaseSerializer):
    coverage_id = serpy.Field()
    date = serpy.Field()
    external_id = serpy.Field()


class DataPointSerializer(BaseSerializer):
    campaign_id = serpy.Field()
    order = serpy.Field()
    latitude = serpy.Field()
    longitude = serpy.Field()


class MeasurementSerializer(BaseSerializer):
    category_id = serpy.Field()
    data_point_id = serpy.Field()