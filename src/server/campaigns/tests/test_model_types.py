# Standard imports
import pytest

# Project imports
from server.campaigns.models import (
    CategoryType,
    ComplimentaryDataType,
)


@pytest.mark.django_db
class TestCategoryType:
    """Test CategoryType class methods"""

    def test_get_by_alias_radiance(self):
        """Test getting category by radiance alias"""
        result = CategoryType.get_by_alias("radiancia")
        assert result == CategoryType.RADIANCE
        result = CategoryType.get_by_alias("datoradiancia")
        assert result == CategoryType.RADIANCE

    def test_get_by_alias_reflectance(self):
        """Test getting category by reflectance alias"""
        result = CategoryType.get_by_alias("reflectancia")
        assert result == CategoryType.REFLECTANCE
        result = CategoryType.get_by_alias("datoreflectancia")
        assert result == CategoryType.REFLECTANCE

    def test_get_by_alias_avg_radiance(self):
        """Test getting category by average radiance alias"""
        result = CategoryType.get_by_alias("radianciapromedio")
        assert result == CategoryType.AVG_RADIANCE

    def test_get_by_alias_raw_data(self):
        """Test getting category by raw data alias"""
        assert CategoryType.get_by_alias("datocrudo") == CategoryType.RAW_DATA

    def test_get_by_alias_not_found(self):
        """Test getting category with invalid alias returns None"""
        assert CategoryType.get_by_alias("invalid_category") is None

    def test_get_by_path_with_radiance(self):
        """Test getting category from path containing radiance"""
        path = "/coverage/campaign/datapoint/radiancia/file.txt"
        assert CategoryType.get_by_path(path) == CategoryType.RADIANCE

    def test_get_by_path_with_reflectance(self):
        """Test getting category from path containing reflectance"""
        path = "/coverage/campaign/datapoint/reflectancia/file.txt"
        assert CategoryType.get_by_path(path) == CategoryType.REFLECTANCE

    def test_get_by_path_not_found(self):
        """Test getting category from path without category returns None"""
        path = "/coverage/campaign/datapoint/file.txt"
        assert CategoryType.get_by_path(path) is None


@pytest.mark.django_db
class TestComplimentaryDataType:
    """Test ComplimentaryDataType class methods"""

    def test_is_complimentary_with_datos_complementarios(self):
        """Test is_complimentary with 'datos complementarios' in path"""
        path = "/coverage/campaign/datoscomplementarios/file.txt"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_is_complimentary_with_fotos(self):
        """Test is_complimentary with 'fotos' alias"""
        path = "/coverage/campaign/fotos/image.jpg"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_is_complimentary_with_planilla_campo(self):
        """Test is_complimentary with 'planilla campo' alias"""
        path = "/coverage/campaign/planillacampo/data.xlsx"
        assert ComplimentaryDataType.is_complimentary(path) is True

    def test_get_by_alias_field_spreadsheet(self):
        """Test getting complimentary type by field spreadsheet alias"""
        result = ComplimentaryDataType.get_by_alias("planillacampo")
        assert result == ComplimentaryDataType.FIELD_SPREADSHEET

    def test_get_by_alias_lab_spreadsheet(self):
        """Test getting complimentary type by lab spreadsheet alias"""
        result = ComplimentaryDataType.get_by_alias("planillalaboratorio")
        assert result == ComplimentaryDataType.LAB_SPREADSHEET

    def test_get_by_alias_photos(self):
        """Test getting complimentary type by photos alias"""
        result = ComplimentaryDataType.get_by_alias("fotos")
        assert result == ComplimentaryDataType.PHOTOS

    def test_get_by_alias_not_found(self):
        """Test getting complimentary type with invalid alias returns None"""
        assert ComplimentaryDataType.get_by_alias("invalid") is None

    def test_get_by_path_with_fotos(self):
        """Test getting complimentary type from path with photos"""
        path = "/coverage/campaign/fotos/image.jpg"
        result = ComplimentaryDataType.get_by_path(path)
        assert result == ComplimentaryDataType.PHOTOS

    def test_get_by_path_default(self):
        """Test getting complimentary type from path defaults to
        COMPLIMENTARY_DATA"""
        path = "/coverage/campaign/datoscomplementarios/file.txt"
        result = ComplimentaryDataType.get_by_path(path)
        assert result == ComplimentaryDataType.COMPLIMENTARY_DATA
