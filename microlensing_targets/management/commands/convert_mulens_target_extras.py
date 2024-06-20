from django.core.management.base import BaseCommand
from django.conf import settings

from tom_targets.base_models import BaseTarget
from tom_targets.models import Target, TargetExtra


class Command(BaseCommand):
    """
    This command converts a given TargetExtra into a model field in the current Target model.
    This requires a model field to already exist in your UserDefinedTarget model for each Extra Field you wish to
    convert. If you have not created a UserDefinedTarget model, you should follow the example given in the
    documentation: https://tom-toolkit.readthedocs.io/en/stable/targets/target_fields.html#extending-the-target-model

    Example:
        ./manage.py converttargetextras --target_extra redshift discovery_date --model_field redshift discovery_date

    This version of the code has been adapted from the TOM Toolkit's original code and customized for MOP.
    """

    help = 'A Helper command to convert target extras into UserDefinedTarget Fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target_extra',
            nargs='+',
            help='TargetExtra to convert into a model field. Accepts multiple TargetExtras. '
                 '(Leave blank for interactive.)'
        )
        parser.add_argument(
            '--model_field',
            nargs='+',
            default=[],  # Default to empty list to allow for interactive mode
            help='Model Fields for UserDefinedTarget to accept TargetExtra. Accepts multiple Model Fields. '
                 'Order must match --target_extra order for multiple entries. '
                 '(Leave blank for interactive.)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm each Target Extra -> Model Field conversion first.',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Provide a list of available TargetExtras and Model Fields.',
        )

        parser.add_argument(
            '--override',
            help='Override any current value of the custom model fields with the value in the corresponding target extra'
            'Enter true to override or leave blank to skip.',
        )
    def prompt_extra_field(self, extra_field_keys):
        """
        Interactive Mode -- Prompt the user to choose a TargetExtra to convert
        extra_field_keys: List of valid TargetExtra keys from settings.py
        """
        prompt = f'Which Extra Field would you like to convert?\n{self.style.WARNING(extra_field_keys)}\n'
        while True:
            chosen_extra = input(prompt)
            if chosen_extra in extra_field_keys:
                break
            else:
                self.stdout.write(self.style.ERROR("I don't recognize that field. "
                                                   "Please choose from the list."))
        return chosen_extra

    def prompt_model_field(self, model_field_keys, chosen_extra):
        """
        Interactive Mode -- Prompt the user to choose a Model Field to convert the TargetExtra into
        model_field_keys: list of valid fields available for the Target Model
        chosen_extra: key for the selected TargetExtra
        """
        prompt = f'What is the name of the model field you would like to convert {self.style.SUCCESS(chosen_extra)}' \
                 f' into? (Leave blank to skip)\n{self.style.WARNING(model_field_keys)}\n'
        while True:
            chosen_model_field = input(prompt)
            if chosen_model_field in model_field_keys:
                break
            elif not chosen_model_field:
                self.stdout.write(f'Skipping TargetExtra: {self.style.SUCCESS(chosen_extra)}.')
                return None
            else:
                self.stdout.write(self.style.ERROR("I don't recognize that field. "
                                                   "Please choose from the list."))
        return chosen_model_field

    def confirm_conversion(self, chosen_extra, chosen_model_field):
        """
        Interactive Mode -- Ask for confirmation before converting a Target Extra
        """
        prompt = (f'Are you sure that you want to convert the TargetExtra:{self.style.SUCCESS(chosen_extra)} to '
                  f'the {Target.__name__} model field:{self.style.SUCCESS(chosen_model_field)} for all Targets?\n'
                  f' {self.style.WARNING("(y/N)")}\n')
        while True:
            response = input(prompt).lower()
            if not response or response == 'n' or response == 'no':
                self.stdout.write(f'Skipping TargetExtra: {self.style.SUCCESS(chosen_extra)}.')
                return False
            elif response == 'y' or response == 'yes':
                return True
            else:
                self.stdout.write('Invalid response. Please try again.')

    def convert_target_extra(self, options, chosen_extra, chosen_model_field):
        """
        Perform the actual conversion from a `chosen_extra` to a `chosen_model_field` for each target that has one of
        these TargetExtras.

        chosen_extra: key for the selected TargetExtra.
        chosen_model_field: name of the selected Target field.
        """

        for extra in TargetExtra.objects.filter(key=chosen_extra):
            target = Target.objects.get(pk=extra.target.pk)
            self.stdout.write('Converting ' + chosen_extra + ' to ' + chosen_model_field + ' for ' + target.name)
            if getattr(target, chosen_model_field, None) and 'true' not in str(options['override']).lower():
                self.stdout.write(f"{self.style.ERROR('Warning:')} {target}.{chosen_model_field} "
                                  f"already has a value: {getattr(target, chosen_model_field)}. Skipping.")
                continue

            # Check for empty string entries for the Latest_data_UTC parameter
            if chosen_model_field == 'latest_data_utc' \
                and (len(str(extra.value)) == 0 or str(extra.value).lower() == 'none'):
                self.stdout.write(
                    f"Deleted invalid null value for {Target.__name__}.{chosen_model_field} {extra.value} for "
                    f"{target}.")
                extra.delete()

            else:
                # Check for null entries in FloatFields.  If this is the case, we skip the (invalid)
                # value and leave it with the default.
                try:
                    self.stdout.write(f"Setting {Target.__name__}.{chosen_model_field} to {extra.value} for "
                                      f"{target}.")
                    setattr(target, chosen_model_field, extra.value)
                    target.save()
                    extra.delete()
                except ValueError:
                    if extra.value == 'null':
                        extra.delete()
                        self.stdout.write(f"Deleted invalid null value for {Target.__name__}.{chosen_model_field} to {extra.value} for "
                                      f"{target}.")
    def mulens_param_mapping(self):
        """Method provides the mapping of the microlensing extra_params to the new custom Target model attributes"""

        param_map = {
            'Alive': 'alive',
            'Classification': 'classification',
            'Category': 'category',
            'Observing_mode': 'observing_mode',
            'Sky_location': 'sky_location',
            't0': 't0',
            't0_error': 't0_error',
            'u0': 'u0',
            'u0_error': 'u0_error',
            'tE': 'tE',
            'tE_error': 'tE_error',
            'piEN': 'piEN',
            'piEN_error': 'piEN_error',
            'piEE': 'piEE',
            'piEE_error': 'piEE_error',
            'rho': 'rho',
            'rho_error': 'rho_error',
            's': 's',
            's_error': 's_error',
            'q': 'q',
            'q_error': 'q_error',
            'alpha': 'alpha',
            'alpha_error': 'alpha_error',
            'Source_magnitude': 'source_magnitude',
            'Source_mag_error': 'source_mag_error',
            'Blend_magnitude': 'blend_magnitude',
            'Blend_mag_error': 'blend_mag_error',
            'Baseline_magnitude': 'baseline_magnitude',
            'Baseline_mag_error': 'baseline_mag_error',
            'Gaia_Source_ID': 'gaia_source_id',
            'Gmag': 'gmag',
            'Gmag_error': 'gmag_error',
            'RPmag': 'rpmag',
            'RPmag_error': 'rpmag_error',
            'BPmag': 'bpmag',
            'BPmag_error': 'bpmag_error',
            'BP-RP': 'bprp',
            'BP-RP_error': 'bprp_error',
            'Reddening(BP-RP)': 'reddening_bprp',
            'Extinction_G': 'extinction_g',
            'Distance': 'distance',
            'Teff': 'teff',
            'logg': 'logg',
            '[Fe/H]': 'metallicity',
            'RUWE': 'ruwe',
            'Fit_covariance': 'fit_covariance',
            'TAP_priority': 'tap_priority',
            'TAP_priority_error': 'tap_priority_error',
            'TAP_priority_longtE': 'tap_priority_longte',
            'TAP_priority_longtE_error': 'tap_priority_longte_error',
            'Interferometry_mode': 'interferometry_mode',
            'Interferometry_guide_star': 'interferometry_guide_star',
            'Interferometry_candidate': 'interferometry_candidate',
            'Spectras': 'spectras',
            'Last_fit': 'last_fit',
            'chi2': 'chi2',
            'red_chi2': 'red_chi2',
            'KS_test': 'ks_test',
            'SW_test': 'sw_test',
            'AD_test': 'ad_test',
            'Latest_data_HJD': 'latest_data_hjd',
            'Latest_data_UTC': 'latest_data_utc',
            'Mag_now': 'mag_now',
            'Mag_now_passband': 'mag_now_passband',
            'Mag_peak_J': 'mag_peak_J',
            'Mag_peak_J_error': 'mag_peak_J_error',
            'Mag_peak_H': 'mag_peak_H',
            'Mag_peak_H_error': 'mag_peak_H_error',
            'Mag_peak_K': 'mag_peak_K',
            'Mag_peak_K_error': 'mag_peak_K_error',
            'Mag_base_J': 'mag_base_J',
            'Mag_base_H': 'mag_base_H',
            'Mag_base_K': 'mag_base_K',
            'Interferometry_interval': 'interferometry_interval',
            'YSO': 'YSO',
            'QSO': 'QSO',
            'galaxy': 'galaxy',
            'TNS_name': 'TNS_name',
            'TNS_class': 'TNS_class',
        }

        return param_map

    def handle(self, *args, **options):
        chosen_extras = options['target_extra']
        chosen_model_fields = options['model_field']

        # Get all the extra field keys
        extra_field_keys = [field['name'] for field in settings.EXTRA_FIELDS]

        # Get all the new model fields
        target_model = Target
        model_field_keys = [field.name for field in target_model._meta.get_fields()
                            if field not in BaseTarget._meta.get_fields() and field.name != 'basetarget_ptr']

        if options['list']:
            self.stdout.write(f'Available TargetExtras: {self.style.WARNING(extra_field_keys)}')
            self.stdout.write(f'Available Model Fields: {self.style.WARNING(model_field_keys)}')
            return

        # If the user requests 'all' parameters, use the mapping method to build a list of
        # all of MOP's extra_params
        if 'all' in str(options['target_extra']).lower() and 'all' in str(options['model_field']).lower():
            param_map = self.mulens_param_mapping()
            chosen_extras = []
            chosen_model_fields = []
            for key, value in param_map.items():
                chosen_extras.append(key)
                chosen_model_fields.append(value)

        # If no Target Extras were provided, prompt user
        if not chosen_extras:
            chosen_extras = [self.prompt_extra_field(extra_field_keys)]

        self.stdout.write('Chosen extras: ' + repr(chosen_extras))

        for i, chosen_extra in enumerate(chosen_extras):
            self.stdout.write('Converting entries for ' + chosen_extra)

            # Check that inputs are valid.
            if chosen_extra not in extra_field_keys:
                self.stdout.write(self.style.ERROR(f"Skipping {chosen_extra} since it is not a valid TargetExtra."))
                continue
            try:
                chosen_model_field = chosen_model_fields[i]
            except IndexError:
                # If no Model Field was provided, prompt user
                chosen_model_field = self.prompt_model_field(model_field_keys, chosen_extra)
            if not chosen_model_field:
                continue
            if chosen_extra not in extra_field_keys:
                self.stdout.write(f'{self.style.ERROR("Warning:")} Skipping {chosen_extra} since it is not a valid'
                                  f' TargetExtra.')
                continue
            # Note that we have to override this check for the distance parameter, since this is a parameter in the
            # base Target model
            if chosen_model_field != 'distance':
                if chosen_model_field not in model_field_keys:
                    self.stdout.write(f'{self.style.ERROR("Warning:")} Skipping {chosen_model_field} since it is not a '
                                  f'valid target field for {Target.__name__}.')
                    continue

            if options['confirm']:
                confirmed = self.confirm_conversion(chosen_extra, chosen_model_field)
                if not confirmed:
                    continue

            self.convert_target_extra(options, chosen_extra, chosen_model_field)

        return
