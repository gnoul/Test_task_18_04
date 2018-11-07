from django.conf import settings
from django.db import models
import django.db.models.options as options
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    'es_index_name', 'es_type_name', 'es_mapping'
)


ROOMS_TYPES = (
    (0, _('Studio')),
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
)


class Apartments(models.Model):

    description = models.TextField(verbose_name=_('Description'))
    price = models.IntegerField(verbose_name=_('Price'))
    location = models.CharField(blank=True, max_length=250, verbose_name=_('Location'))
    house_type = models.CharField(blank=True, max_length=20, verbose_name=_('House type'))  # TODO change to ForeignKey
    rooms_number = models.IntegerField(choices=ROOMS_TYPES, verbose_name=_('Rooms number'))
    floor = models.IntegerField(verbose_name=_('Floor'))
    floors_number = models.IntegerField(verbose_name=_('Floor number'))
    balcony = models.BooleanField(default=False, verbose_name=_('Balcony'))
    mortgage = models.BooleanField(default=False, verbose_name=_('Mortgage'))
    mortgage_mil = models.BooleanField(default=False, verbose_name=_('Military mortgage'))
    company = models.CharField(max_length=60, verbose_name=_('Company name'))

    class Meta:
        es_index_name = 'apartments'
        es_type_name = 'apartments'
        es_mapping = {
            'properties': {
                'description': {"type": "text"},
                'price': {"type": "integer"},
                'location': {"type": "text"},
                'house_type': {"type": "text"},
                'rooms_number': {"type": "keyword"},
                'floor': {"type": "integer"},
                'floors_number': {"type": "integer"},
                'balcony': {"type": "boolean"},
                'mortgage': {"type": "boolean"},
                'mortgage_mil': {"type": "boolean"},
                'company': {"type": "text"}
            }
        }

    def to_index(self):
        data = {}
        mapping = self._meta.es_mapping
        for field_name in mapping['properties'].keys():
            data[field_name] = self.field_to_index(field_name)
        return data

    def field_to_index(self, field_name):
        if hasattr(self, 'get_{0}_display'.format(field_name)):
            field_es_value = getattr(self, 'get_{0}_display'.format(field_name))()
        else:
            field_es_value = getattr(self, field_name)
        return field_es_value


@receiver(post_save, sender=Apartments)
def apartment_sync_to_es(sender, instance, **kwargs):
    index_name = instance._meta.es_index_name
    settings.ES.index(index=index_name,
                      doc_type=instance._meta.es_type_name,
                      body=instance.to_index(),
                      id=instance.pk)
