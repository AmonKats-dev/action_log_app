from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q
from django.core.validators import RegexValidator

def assign_users_to_departments(apps, schema_editor):
    User = apps.get_model('users', 'User')
    DepartmentUnit = apps.get_model('departments', 'DepartmentUnit')
    Role = apps.get_model('users', 'Role')

    # Get IN and PAS department units
    in_unit = DepartmentUnit.objects.filter(name='IN').first()
    pas_unit = DepartmentUnit.objects.filter(name='PAS').first()

    if not in_unit or not pas_unit:
        return

    # Get Commissioner and Assistant Commissioner roles
    commissioner_role = Role.objects.filter(name='commissioner').first()
    assistant_commissioner_role = Role.objects.filter(name='assistant_commissioner').first()

    # Get all users except Commissioner and Assistant Commissioner
    users = User.objects.exclude(
        Q(role=commissioner_role) | Q(role=assistant_commissioner_role)
    )

    # Assign users to departments
    for user in users:
        # If user already has a department unit, skip
        if user.department_unit:
            continue

        # Assign to IN or PAS based on some criteria (e.g., even/odd ID)
        user.department_unit = in_unit if user.id % 2 == 0 else pas_unit
        user.save()

def reverse_migration(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.all().update(department_unit=None)

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(
                blank=True,
                max_length=17,
                validators=[
                    RegexValidator(
                        regex=r'^\+?1?\d{9,15}$',
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
                    )
                ]
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='department_unit',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='departments.departmentunit'
            ),
        ),
        migrations.RunPython(assign_users_to_departments, reverse_migration),
    ] 