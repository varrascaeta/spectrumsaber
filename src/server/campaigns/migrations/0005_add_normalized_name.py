"""
Add normalized_name to BaseFile concrete models and Category.

normalized_name stores the lowercase-stripped version of name, enabling
case-insensitive DB-level filtering without relying on lookup transforms.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0004_alter_complimentarydata_complement_type"),
    ]

    operations = [
        # Category
        migrations.AddField(
            model_name="category",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        # BaseFile concrete models
        migrations.AddField(
            model_name="coverage",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="campaign",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="datapoint",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="measurement",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="complimentarydata",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="unmatchedfile",
            name="normalized_name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]
