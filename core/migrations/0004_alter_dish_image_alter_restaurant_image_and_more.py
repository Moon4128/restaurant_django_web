from pathlib import Path
import shutil

from django.conf import settings
from django.db import migrations, models


def move_images_to_common_directory(apps, schema_editor):
    image_models = (
        apps.get_model('core', 'Dish'),
        apps.get_model('core', 'Restaurant'),
        apps.get_model('core', 'RestaurantBranch'),
    )
    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)

    for model in image_models:
        for instance in model.objects.exclude(image='').only('id', 'image'):
            old_name = str(instance.image.name)
            if '/' not in old_name:
                continue

            file_name = Path(old_name).name
            source = Path(settings.BASE_DIR) / old_name
            target = media_root / file_name
            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))

            instance.image.name = file_name
            instance.save(update_fields=['image'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_review_dish'),
    ]

    operations = [
        migrations.RunPython(
            move_images_to_common_directory,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='dish',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
        migrations.AlterField(
            model_name='restaurantbranch',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
