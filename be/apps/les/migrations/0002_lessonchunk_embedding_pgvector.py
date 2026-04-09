from django.db import migrations
from pgvector.django import HnswIndex, VectorExtension, VectorField


class Migration(migrations.Migration):

    dependencies = [
        ('lesson_ingestion', '0001_initial'),
    ]

    operations = [
        VectorExtension(),
        migrations.AddField(
            model_name='lessoncontentchunk',
            name='embedding',
            field=VectorField(dimensions=768, null=True, blank=True),
        ),
        migrations.AddIndex(
            model_name='lessoncontentchunk',
            index=HnswIndex(
                name='lesson_chunk_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
