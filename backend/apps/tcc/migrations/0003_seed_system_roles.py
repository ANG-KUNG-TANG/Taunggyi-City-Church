from django.db import migrations


INITIAL_ROLES = [
    {
        "code": "ZONE_LEADER",
        "name": "Zone Leader",
        "description": "Manages members and activities within assigned zones.",
    },
    {
        "code": "PASTOR",
        "name": "Pastor",
        "description": "Has church-wide operational and pastoral access.",
    },
    {
        "code": "ADMINISTRATOR",
        "name": "Administrator",
        "description": "Manages staff accounts, roles, and system administration.",
    },
]


def create_system_roles(apps, schema_editor):
    Role = apps.get_model("tcc", "Role")
    db_alias = schema_editor.connection.alias

    for role_data in INITIAL_ROLES:
        Role.objects.using(db_alias).get_or_create(
            code=role_data["code"],
            defaults={
                "name": role_data["name"],
                "description": role_data["description"],
                "is_system_role": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tcc", "0002_rebuild_user_and_add_rbac"),
    ]

    operations = [
        migrations.RunPython(
            create_system_roles,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
