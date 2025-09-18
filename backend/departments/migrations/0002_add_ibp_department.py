from django.db import migrations

def add_ibp_department(apps, schema_editor):
    Department = apps.get_model('departments', 'Department')
    DepartmentUnit = apps.get_model('departments', 'DepartmentUnit')
    
    # Create IBP department if it doesn't exist
    ibp_dept, created = Department.objects.get_or_create(
        name='IBP Department',
        code='IBP',
        defaults={
            'description': 'Integrated Business Planning Department'
        }
    )
    
    # Create IBP unit
    DepartmentUnit.objects.get_or_create(
        department=ibp_dept,
        name='IBP Unit',
        unit_type='infrastructure',
        defaults={
            'description': 'Integrated Business Planning Unit'
        }
    )

def remove_ibp_department(apps, schema_editor):
    Department = apps.get_model('departments', 'Department')
    Department.objects.filter(code='IBP').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_ibp_department, remove_ibp_department),
    ] 