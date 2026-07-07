from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum

class Command(BaseCommand):

    def handle(self, *args, **options):

        qs = ReducedDatum.objects.filter(data_type='photometry')

        BANDPASS_FIELDS = ('bandpass', 'filter', 'band', 'f')

        bad = []
        for rd in qs:
            value = rd.value or {}
            bandpass = self.pop_first(value, BANDPASS_FIELDS)
            print(rd.pk, bandpass)
            unit = value.get('unit')
            if bandpass and len(str(bandpass)) > 32:
                bad.append((rd.pk, rd.target_id, rd.source_name, 'bandpass', str(bandpass)))
            if unit and len(str(unit)) > 32:
                bad.append((rd.pk, rd.target_id, rd.source_name, 'unit', str(unit)))

        print(f'Found {len(bad)} offending rows')
        for row in bad[:50]:
            print(row)

    def pop_first(self, d, keys):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None