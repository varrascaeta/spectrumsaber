# Generated by Django 5.0.4 on 2024-06-25 18:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0009_is_valid_base_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvalidCampaign',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('campaigns.campaign',),
        ),
        migrations.CreateModel(
            name='InvalidCoverage',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('campaigns.coverage',),
        ),
        migrations.CreateModel(
            name='InvalidDataPoint',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('campaigns.datapoint',),
        ),
        migrations.CreateModel(
            name='InvalidMeasurement',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('campaigns.measurement',),
        ),
    ]
