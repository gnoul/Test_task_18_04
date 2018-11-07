from collections import defaultdict
from django.conf import settings
from django.views.generic.edit import FormView


from .forms import FilterForm
from .models import Apartments


class ContactView(FormView):
    template_name = 'filter.html'
    form_class = FilterForm
    aggs_dict = {
        "price": {"extended_stats": {"field": "price"}},
        "rooms_number": {"terms": {"field": "rooms_number"}},
        "mortgage": {"terms": {"field": "mortgage"}},
        "mortgage_mil": {"terms": {"field": "mortgage_mil"}},
        "balcony": {"terms": {"field": "balcony"}},
        "floor": {"extended_stats": {"field": "floor"}},
        "floors_number": {"extended_stats": {"field": "floors_number"}},
    }
    filter_dict = {}
    agg_data = {}

    def get(self, request, *args, **kwargs):
        self.get_aggregation_data()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['aggregation'] = self.agg_data
        return context

    def get_aggregation_data(self, query=None):
        es_query = {'aggs': self.aggs_dict, 'size': 0}
        if query:
            es_query['query'] = query
        es_result = settings.ES.search(index=Apartments._meta.es_index_name,
                                       doc_type=Apartments._meta.es_type_name,
                                       body=es_query)
        self.agg_data = {}
        for field, value in es_result['aggregations'].items():
            buckets = value.get('buckets')
            if buckets:
                res_dict = {}
                for bucket in buckets:
                    name = bucket.get('key_as_string', bucket.get('key'))
                    count = bucket.get('doc_count')
                    res_dict[name] = count
                self.agg_data[field] = res_dict
            else:
                self.agg_data[field] = {k: v for k, v in value.items() if k in ['min', 'max', 'count']}

    def form_valid(self, form):
        # response = super().form_valid(form)
        comparsion_ops = {'from': 'gte', 'to': 'lte'}  # Convert form field names to ES operators
        terms = {}
        ranges = defaultdict(dict)
        for field in form.cleaned_data:
            if field:
                if '_from' in field or '_to' in field:  # range fields
                    *field_part, postfix = field.split('_')
                    field_name = '_'.join(field_part)
                    ranges[field_name][comparsion_ops[postfix]] = form.cleaned_data[field]
                elif field == 'rooms_number':
                    field_choices = dict(form.fields['rooms_number'].choices)
                    terms[field] = str(field_choices[int(form.cleaned_data[field][0])])
                elif field in ['mortgage', 'mortgage_mil', 'balcony']:  # Boolean fields
                    terms[field] = form.cleaned_data[field]
        must = []
        for term, value in terms.items():
            must.append({"term": {term: value}})
        for field, value in ranges.items():
            must.append({"range": {field: value}})
        query = {"bool": {"must": must}}
        self.get_aggregation_data(query)
        return self.render_to_response(self.get_context_data(form=form))
