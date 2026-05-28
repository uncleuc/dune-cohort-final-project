import uuid

from django.db import migrations


def _generate_uuid_mapping(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('SELECT id FROM chat_conversation ORDER BY id')
        old_ids = [row[0] for row in cursor.fetchall()]

    old_to_new = {}
    for old_id in old_ids:
        try:
            uuid.UUID(str(old_id))
        except (ValueError, TypeError, AttributeError):
            old_to_new[str(old_id)] = str(uuid.uuid4())

    if not old_to_new:
        return

    with schema_editor.connection.cursor() as cursor:
        # Update child rows first so foreign keys still point to existing conversation IDs.
        for old_id, new_id in old_to_new.items():
            cursor.execute(
                'UPDATE chat_message SET conversation_id = %s WHERE conversation_id = %s',
                [new_id, old_id],
            )
            cursor.execute(
                'UPDATE chat_conversation_participants SET conversation_id = %s WHERE conversation_id = %s',
                [new_id, old_id],
            )

        # Update the conversation primary keys to valid UUID strings.
        for old_id, new_id in old_to_new.items():
            cursor.execute(
                'UPDATE chat_conversation SET id = %s WHERE id = %s',
                [new_id, old_id],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_alter_conversation_id'),
    ]

    operations = [
        migrations.RunPython(_generate_uuid_mapping, migrations.RunPython.noop),
    ]
