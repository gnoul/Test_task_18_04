from django import forms

from .models import ROOMS_TYPES


# ROOMS_TYPES_FORM = [(str(i[0].value), str(i[1])) for i in ROOMS_TYPES]

class FilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if 'field_attrs' in kwargs:  # Pass attrs to form fields
            field_attrs = kwargs.pop('field_attrs')
            for field, attrs in field_attrs.items():
                field = self.base_fields[field]
                field.widget.attrs.update(attrs)
        super(FilterForm, self).__init__(*args, **kwargs)

    price_from = forms.IntegerField(required=False)
    price_to = forms.IntegerField(required=False)
    floor_from = forms.IntegerField(required=False)
    floor_to = forms.IntegerField(required=False)
    floors_number_from = forms.IntegerField(required=False)
    floors_number_to = forms.IntegerField(required=False)
    rooms_number = forms.ChoiceField(required=False, choices=ROOMS_TYPES)  # TODO Need multiple selection
    balcony = forms.BooleanField(required=False)
    mortgage = forms.BooleanField(required=False)
    mortgage_mil = forms.BooleanField(required=False)
