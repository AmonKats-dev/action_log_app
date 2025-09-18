from django.db import migrations

def update_ibp_unit_type(apps, schema_editor):
    Department = apps.get_model('departments', 'Department')
    DepartmentUnit = apps.get_model('departments', 'DepartmentUnit')
    
    # Get the IBP department
    ibp_dept = Department.objects.get(code='IBP')
    
    # Update the IBP unit type
    DepartmentUnit.objects.filter(
        department=ibp_dept,
        name='IBP Unit'
    ).update(unit_type='ibp')

def reverse_update_ibp_unit_type(apps, schema_editor):
    Department = apps.get_model('departments', 'Department')
    DepartmentUnit = apps.get_model('departments', 'DepartmentUnit')
    
    # Get the IBP department
    ibp_dept = Department.objects.get(code='IBP')
    
    # Revert the IBP unit type back to infrastructure
    DepartmentUnit.objects.filter(
        department=ibp_dept,
        name='IBP Unit'
    ).update(unit_type='infrastructure')

class Migration(migrations.Migration):
    dependencies = [
        ('departments', '0002_add_ibp_department'),
    ]

    operations = [
        migrations.RunPython(update_ibp_unit_type, reverse_update_ibp_unit_type),
    ] 