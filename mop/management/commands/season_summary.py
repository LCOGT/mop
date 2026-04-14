from django.core.management.base import BaseCommand
from tom_dataproducts.models import ReducedDatum
from tom_observations.models import ObservationRecord
from tom_targets.models import Target, TargetName, TargetList
from django.db.models import Q
from datetime import datetime, timezone

class Command(BaseCommand):

    help = 'Summarize targets and data acquired over a given interval'
    def add_arguments(self, parser):
        parser.add_argument('start_date', help='Start date of time range in YYYY-MM-DD format')
        parser.add_argument('end_date', help='End date of time range in YYYY-MM-DD format')

    def handle(self, *args, **options):

        # Parse the time range given
        start_date = datetime.strptime(options['start_date'], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(options['end_date'], "%Y-%m-%d").replace(tzinfo=timezone.utc)

        # Identify a queryset of events with ObservationRecords with timestamps between
        # the given start and end dates.  Scheduled start and end timestamps are not always
        # populated since this is only done on update from the scheduler, so we have to
        # extract this from the parameters
        targets = []
        qs = ObservationRecord.objects.all()
        for obs in qs:
            try:
                obs_start = datetime.fromisoformat(obs.parameters['start']).replace(tzinfo=timezone.utc)

            except KeyError:
                obs_ts = obs.parameters['requests'][0]['windows'][0]['start']
                obs_start = datetime.strptime(
                    obs_ts,
                    "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)

            if obs_start >= start_date and obs_start <= end_date:
                if obs.target not in targets: targets.append(Target.objects.get(id=obs.target.pk))

        print('Found ' + str(len(targets)) + ' targets with observation records')

        # For those targets, review the ReducedDatums obtained
        datums = ReducedDatum.objects.filter(target__in=targets).order_by("timestamp")
        event_data = {x: {} for x in targets}
        nstellar = 0
        nlong = 0
        min_obs = 10 # Threshold for meaningful observations
        te_thresh = 100 # tE threshold for long events
        for mulens in event_data.keys():
            mulens.get_reduced_data(datums.filter(target=mulens))
            event_data[mulens] = {key: len(arr) for key,arr in mulens.datasets.items()}

            print(mulens.name + ' : tE=' + str(mulens.tE) + 'd '
                  + ' '.join([key + '=' + str(count) for key,count in event_data[mulens].items()]))

            # Check what data OMEGA obtained
            for key in mulens.datasets.keys():
                if 'OMEGA' in key and len(mulens.datasets[key]) >= min_obs:
                    if mulens.tE < te_thresh:
                        nstellar += 1
                    else:
                        nlong += 1

        print('OMEGA observations of ' + str(nstellar) + ' stellar targets')
        print('OMEGA observations of ' + str(nlong) + ' long-timescale targets')
