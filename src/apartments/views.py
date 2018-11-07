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

    def get_initial(self):
        initial = super(ContactView, self).get_initial()
        if self.request.method == 'GET' and self.agg_data:
            for k, v in self.agg_data.items():
                if 'min' in v:
                    fieldname = '{}_from'.format(k)
                    initial[fieldname] = v['min']
                if 'max' in v:
                    fieldname = '{}_to'.format(k)
                    initial[fieldname] = v['max']
        return initial

    def form_valid(self, form):
        comparsion_ops = {'from': 'gte', 'to': 'lte'}  # Convert form field names to ES operators
        terms = {}
        ranges = defaultdict(dict)
        for field, data in form.cleaned_data.items():
            if data == '':
                continue
            if '_from' in field or '_to' in field:  # range fields
                *field_part, postfix = field.split('_')
                field_name = '_'.join(field_part)
                ranges[field_name][comparsion_ops[postfix]] = data
            elif field == 'rooms_number':  # Choices
                field_choices = dict(form.fields[field].choices)
                terms[field] = str(field_choices[int(data[0])])  # TODO make multiselect
            elif field in ['mortgage', 'mortgage_mil', 'balcony']:  # Boolean fields
                if isinstance(data, bool):
                    terms[field] = data
                if isinstance(data, str) and data.isdigit():
                    terms[field] = bool(int(data))
        must = []
        for term, value in terms.items():
            must.append({"term": {term: value}})
        for field, value in ranges.items():
            must.append({"range": {field: value}})
        query = {"bool": {"must": must}}
        self.get_aggregation_data(query)
        return self.render_to_response(self.get_context_data(form=form))
