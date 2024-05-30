from django.core.management.base import BaseCommand

from tom_targets.base_models import BaseTarget
from tom_targets.models import Target

class Command(BaseCommand):
    """
    Command to convert existing TOM Targets with extra parameters to the new Microlensing Target
    """

    help = 'Command to convert existing TOM Targets with extra parameters to the new Microlensing Target'

    def handle(self, *args, **options):
        # Ensure the Target is a subclass of BaseTarget
        if Target != BaseTarget and issubclass(Target, BaseTarget):
            self.stdout.write(f'{Target} is a subclass of BaseTarget, updating existing Targets.')
            base_targets = BaseTarget.objects.all()
            targets = Target.objects.all()
            for base_target in base_targets:
                # If the base_target is not already in the new target model, update it
                # Note: subclassed models share a PK with their parent
                if not targets.filter(pk=base_target.pk).exists():
                    self.stdout.write(f'Updating {base_target}...')
                    target = Target(basetarget_ptr_id=base_target.pk)  # Create a new target with the base_target PK
                    target.__dict__.update(base_target.__dict__)       # add base_target fields to target dictionary
                    target.save()
            self.stdout.write(f'{Target.objects.count()} Targets updated.')

        return