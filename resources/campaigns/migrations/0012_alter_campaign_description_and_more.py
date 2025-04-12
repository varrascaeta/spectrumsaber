# Generated by Django 5.0.4 on 2025-04-05 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0011_alter_campaign_metadata_alter_campaign_path_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='coverage',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='datapoint',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='measurement',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='spreadsheet',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
