from django.core.management.base import BaseCommand
from tom_targets.models import Target
from mop.management.commands import run_TAP
import json

class Command(BaseCommand):
    """
    Command to convert fit covariance parameter output from their former strings to a JSONField
    """

    help = 'Command to convert existing TOM Targets with extra parameters to the new Microlensing Target'

    def handle(self, *args, **options):

        target_list = Target.objects.all()

        for t in target_list:
            print('Target ' + str(t.pk) + ' ' + t.name + ' has covar=' + repr(t.fit_covariance))
            matrix = run_TAP.load_covar_matrix(t.fit_covariance)
            payload = json.dumps(matrix.tolist())
            t.fit_covariance = {'covariance': payload}
            t.save()