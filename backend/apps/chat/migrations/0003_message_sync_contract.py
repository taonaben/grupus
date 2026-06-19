from django.db import migrations, models


def backfill_server_sequences(apps, schema_editor):
    Message = apps.get_model("chat", "Message")

    channel_ids = (
        Message.objects.order_by()
        .values_list("channel_id", flat=True)
        .distinct()
    )

    for channel_id in channel_ids:
        messages = Message.objects.filter(channel_id=channel_id).order_by(
            "created_at", "id"
        )
        for sequence, message in enumerate(messages, start=1):
            Message.objects.filter(pk=message.pk).update(server_sequence=sequence)


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0002_messagereaction_alter_message_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="client_message_id",
            field=models.CharField(
                blank=True,
                help_text="Client-generated message id used for idempotent create retries",
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="client_mutation_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Client-generated mutation id used for retry traceability",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="server_sequence",
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text="Monotonic per-channel sequence used for sync ordering",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="message",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_server_sequences, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["channel", "server_sequence"],
                name="chat_messag_channel_1e78e7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["channel", "deleted_at"],
                name="chat_messag_channel_5f79a0_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="message",
            constraint=models.UniqueConstraint(
                condition=models.Q(server_sequence__isnull=False),
                fields=("channel", "server_sequence"),
                name="unique_message_channel_sequence",
            ),
        ),
    ]
