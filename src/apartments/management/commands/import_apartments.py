import os
import json
from itertools import islice

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk

from apartments.models import Apartments


def create_index():
    indices_client = IndicesClient(client=settings.ES)
    index_name = Apartments._meta.es_index_name
    if not indices_client.exists(index_name):
        indices_client.create(index=index_name)
        indices_client.put_mapping(
            doc_type=Apartments._meta.es_type_name,
            body=Apartments._meta.es_mapping,
            index=index_name
        )


def load_apartments_data(filename, batchsize=100):
    with open(filename, 'r') as ifile:
        data = json.load(ifile)
        fields = [i.name for i in Apartments._meta.fields]
        batch = []
        for i, d in enumerate(data):
            try:
                item_data = {k: v for k, v in d.items() if k in fields}
                if item_data['rooms_number'] == 'Студия':
                    item_data['rooms_number'] = 0
                item_data['balcony'] = True if 'balcony' in item_data and item_data['balcony'] else False
                batch.append(Apartments(**item_data))
                if i % batchsize == 0:
                    Apartments.objects.bulk_create(batch, batchsize)
                    batch = []
            except ValueError:
                pass  # TODO add error logging
        Apartments.objects.bulk_create(batch)


def fill_es(model, batchsize=100):
    all_objs = model.objects.all().iterator()
    while True:
        batch = list(islice(all_objs, batchsize))
        if not batch:
            break
        data = [
            convert_for_bulk(s, 'index') for s in batch
        ]
        bulk(client=settings.ES, actions=data, stats_only=True)


def convert_for_bulk(django_object, action=None):
    data = django_object.to_index()
    metadata = {
        '_op_type': action,
        '_index': django_object._meta.es_index_name,
        '_type': django_object._meta.es_type_name,
        '_id': django_object.pk
    }
    data.update(**metadata)
    return data


class Command(BaseCommand):
    help = "Load initial dato"

    def add_arguments(self, parser):
        parser.add_argument('--filename')

    def handle(self, *args, **options):
        filename = options.get('filename')
        if os.path.isfile(filename):
            create_index()
            load_apartments_data(filename)
            fill_es(Apartments)
        else:
            raise CommandError('File {} does not exist'.format(filename))
