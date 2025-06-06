# Generated by Django 5.1.7 on 2025-03-24 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_alter_sourceimage_metadata_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourceimage",
            name="file",
            field=models.ImageField(default=None, upload_to="images/"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transformedimage",
            name="file",
            field=models.ImageField(default=None, upload_to="images/"),
            preserve_default=False,
        ),
    ]
