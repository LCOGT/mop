from django.shortcuts import redirect
from django.urls import reverse
from django.core.management import call_command
from django.conf import settings
from io import StringIO
from tom_targets.views import TargetDetailView
from tom_targets.models import Target, TargetExtra, TargetList
from tom_observations.models import ObservationRecord
from tom_observations.views import ObservationFilter
from tom_observations.utils import get_sidereal_visibility
from mop.toolbox.TAP import set_target_sky_location
from django.views.generic.edit import FormView
from django.contrib import messages
from mop.toolbox.obs_control import fetch_all_lco_requestgroups, parse_lco_requestgroups
from mop.forms import TargetClassificationForm, TargetSelectionForm
from tom_common.mixins import Raise403PermissionRequiredMixin
from django_filters.views import FilterView
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from datetime import datetime, timedelta
from mop.toolbox import utilities, querytools
from mop.toolbox.mop_classes import MicrolensingEvent
from django.views.generic.list import ListView
import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
import logging

logger = logging.getLogger(__name__)

class MOPTargetDetailView(TargetDetailView):

    def get_context_data(self, *args, **kwargs):
        """
        Adds the ``TargetClassificationForm`` to the context and prepopulates the hidden fields.

        :returns: context object
        :rtype: dict
        """

        t1 = datetime.utcnow()
        logger.info('STARTED GET_CONTEXT ' + str(t1))
        utilities.checkpoint()

        context = super().get_context_data(*args, **kwargs)
        context['class_form'] = TargetClassificationForm()
        target = self.get_object()
        target_data = querytools.fetch_data_for_targetset([target], check_need_to_fit=False, fetch_photometry=True)
        context['target'] = target_data[target.name]

        t2 = datetime.utcnow()
        logger.info('GET_CONTEXT took ' + str(t2 - t1))
        utilities.checkpoint()

        return context

    def get(self, request, *args, **kwargs):
        # Ensure that the target's location flag is set
        logger.info('STARTING TargetDetail page load: ' + str(datetime.utcnow()))

        t1 = datetime.utcnow()
        utilities.checkpoint()

        target = self.get_object()
        #if 'Sky_location' not in target.extra_fields.keys():
        #    set_target_sky_location(target)

        t2 = datetime.utcnow()
        logger.info('TARGETDETAIL: chk 1, time taken ' + str(t2 - t1))
        utilities.checkpoint()

        fit_event = request.GET.get('fit_event', False)
        if fit_event:
            target_id = self.get_object().id
            target_name = self.get_object().name
            out = StringIO()
            call_command('fit_event_PSPL', target_name, cores=0, stdout=out)
            return redirect(reverse('tom_targets:detail', args=(target_id,)))

        t3 = datetime.utcnow()
        logger.info('TARGETDETAIL: chk 2, time taken ' + str(t3 - t2))
        utilities.checkpoint()

        TAP_event = request.GET.get('tap_event', False)
        if TAP_event:
            target_id = self.get_object().id
            target_name = self.get_object().name
            out = StringIO()
            call_command('run_TAP', target_name, stdout=out)
            return redirect(reverse('tom_targets:detail', args=(target_id,)))

        t4 = datetime.utcnow()
        logger.info('TARGETDETAIL: chk 3, time taken ' + str(t4 - t3))
        utilities.checkpoint()

        logger.info('TARGETDETAIL: get took ' + str(t4 - t1))

        return super().get(request, *args, **kwargs)

class ActiveObsView(ListView):
    template_name = 'active_obs_list.html'
    paginate_by = 25
    strict = False
    model = ObservationRecord
    filterset_class = ObservationFilter
    permission_required = 'tom_targets.view_target'
    ordering = ['-created']

    def get_context_data(self, *args, **kwargs):
        """Method to retrieve data on targets which TAP has recommended for observation within the last 24hrs,
        and their associated observation records

        Returns:
            context     dict    Context data for webpage template
        """
        # Parameters to extract from the observation records
        target_keys = ['tE', 't0', 'Mag_now', 'Category', 'TAP_priority', 'TAP_priority_longtE']

        context = super().get_context_data(*args, **kwargs)

        # Provide a count of the number of targets returned to enable pagination of the results
        context['target_count'] = context['paginator'].count

        # Retrieve a list of Targets for which observations have recently been requested
        if self.request.user.is_authenticated:
            utc_threshold = datetime.utcnow() - timedelta(days=7.0)
            utcnow = datetime.utcnow()
            obs_qs = ObservationRecord.objects.filter(scheduled_start__gt=utc_threshold,
                                                      scheduled_end__gt=utcnow)

            # Build lists of the ObservationRecords and Targets, while respecting
            # user access permissions
            targets = {}
            for obs in obs_qs:
                if self.request.user.has_perm('tom_observations.view_observation'):
                    if 'requests' in obs.parameters.keys():
                        for request in obs.parameters['requests']:
                            obs_data = {}
                            obs_data['start'] = request['windows'][0]['start']
                            obs_data['end'] = request['windows'][0]['end']
                            obs_data['facility'] = 'LCO'
                            obs_data['observation_type'] = obs.parameters['observation_type']
                            obs_data['ipp_value'] = obs.parameters['ipp_value']
                            for c, config in enumerate(request['configurations']):
                                obs_data['c_' + str(c+1) + '_instrument_type'] = config['instrument_type']
                                for ic,inst_config in enumerate(config['instrument_configs']):
                                    obs_data['c_' + str(c+1) + '_ic_' + str(ic+1) + '_filter'] = inst_config['optical_elements']['filter']
                                    obs_data['c_' + str(c+1) + '_ic_' + str(ic+1) + '_exposure_time'] = inst_config['exposure_time']
                                    obs_data['c_' + str(c+1) + '_ic_' + str(ic+1) + '_exposure_count'] = inst_config['exposure_count']

                        if obs.target.name in targets.keys():
                            target_data = targets[obs.target.name]
                        else:
                            target_data = {'name': obs.target.name, 'obs_list': []}
                            for key in target_keys:
                                try:
                                    target_data[key] = obs.target.extra_fields[key]
                                except KeyError:
                                    target_data[key] = 'None'

                        target_data['obs_list'].append(obs_data)
                        targets[obs.target.name] = target_data

            context['targets'] = targets.values()
            
        else:
            context['targets'] = []
            context['obs_list'] = []

        # Retrieve a list of pending observations from the LCO Portal
        response = fetch_all_lco_requestgroups()
        pending_obs = parse_lco_requestgroups(response, short_form=False, pending_only=False)

        pending_obs_list = []
        for target, obs_info in pending_obs.items():
            for config in obs_info:
                config['target'] = target
                config['filters'] = ','.join(config['filters'])
                config['exposure_times'] = ','.join([str(x) for x in config['exposure_times']])
                config['exposure_counts'] = ','.join([str(x) for x in config['exposure_counts']])
                pending_obs_list.append(config)

        context['pending_obs'] = pending_obs_list

        context['query_string'] = self.request.META['QUERY_STRING']

        return context

class PriorityTargetsView(ListView):
    template_name = 'priority_targets_list.html'
    paginate_by = 25
    strict = False
    model = TargetExtra
    permission_required = 'tom_targets.view_target'

    def get_context_data(self, *args, **kwargs):
        """Method to retrieve data on targets which TAP has prioritized

        Returns:
            context     dict    Context data for webpage template
        """

        t1 = datetime.utcnow()
        logger.info('PRIORITYTARGETS started context get ' + str(t1))
        utilities.checkpoint()

        # Configure context
        context = super().get_context_data(*args, **kwargs)
        context['target_count'] = context['paginator'].count

        # Retrieve two lists of Targets, which have been prioritized as stellar and Black Hole candidates
        if self.request.user.is_authenticated:

            # Query for matching TargetExtra entries returns a list of Target PKs
            qs_stars = querytools.fetch_priority_targets(10.0, 'stellar')
            qs_bh = querytools.fetch_priority_targets(10.0, 'long_tE')

            logger.info('Priority querysets initially find ' \
                        + str(len(qs_stars)) + ' stellar candidate events and ' \
                        + str(len(qs_bh)) + ' BH candidate events')
            t2 = datetime.utcnow()
            logger.info('PRIORITYTARGETS took ' + str(t2 - t1))
            utilities.checkpoint()

            # Repackage the two lists to extract the parameters to display in the table.
            # This also checks to see if a Target is alive and not flagged as a known
            # variable before including it
            context['stellar_targets'] = self.extract_target_parameters(qs_stars, 'stellar')
            context['bh_targets'] = self.extract_target_parameters(qs_bh, 'bh')

            logger.info('After filtering priority targets, returning '\
                        + str(len(context['stellar_targets'])) + ' stellar candidate events and '\
                        + str(len(context['bh_targets'])) + ' BH candidate events')

        # If user is not logged in, return empty lists:
        else:
            context['stellar_targets'] = []
            context['bh_targets'] = []

        t2 = datetime.utcnow()
        logger.info('PRIORITYTARGETS finished context get ' + str(t2) + ' took ' + str(t2 - t1))
        utilities.checkpoint()

        return context

    def extract_target_parameters(self, targetset, target_category):
        t1 = datetime.utcnow()
        logger.info('PRIORITYTARGETS started extract at ' + str(t1))
        utilities.checkpoint()

        key_list = ['t0', 't0_error', 'u0', 'u0_error', 'tE', 'tE_error', 'mag_now', 'baseline_magnitude']

        #selected_targets = querytools.fetch_data_for_targetset(targetset, check_need_to_fit=False, fetch_photometry=False)

        priority = []
        target_data = []
        for mulens in targetset:
            target_info = {'name': mulens.name, 'id': mulens.id}

            if target_category == 'stellar':
                target_info['priority'] = round(float(mulens.tap_priority),3)
                # Not all entries have an uncertainty set, due to older versions of the code not storing it
                try:
                    target_info['priority_error'] = round(float(mulens.tap_priority_error),3)
                except AttributeError:
                    target_info['priority_error'] = np.nan
            else:
                target_info['priority'] = round(float(mulens.tap_priority_longte),3)
                try:
                    target_info['priority_error'] = round(float(mulens.tap_priority_longte_error),3)
                except AttributeError:
                    target_info['priority_error'] = np.nan

            for key in key_list:
                try:
                    target_info[key] = float(getattr(mulens, key))
                except AttributeError:
                    target_info[key] = np.nan
                except ValueError:
                    target_info[key] = np.nan
                if key == 't0':
                    target_info[key] = round((target_info[key] - 2460000.0), 3)
                else:
                    # Round floating point values where possible to save space in the table, catching
                    # NaN entries.  Skip in the event that the value is None or a string.
                    try:
                        if not np.isnan(target_info[key]):
                            target_info[key] = round(target_info[key], 3)
                    except:
                        pass

            target_data.append(target_info)
            priority.append(target_info['priority'])

        # Sort the returned list and cap it at a maximum of 20 events per table to avoid bad gateway errors
        max_entries = 20
        priority = np.array(priority)
        idx = np.argsort(priority)[::-1]
        sorted_targets = [target_data[x] for x in idx]
        if len(sorted_targets) > max_entries:
            sorted_targets = sorted_targets[0:max_entries]

        t2 = datetime.utcnow()
        logger.info('PRIORITYTARGETS finished data extract at ' + str(t2))
        logger.info('PRIORITY TARGETS extract function took ' + str(t2-t1))
        utilities.checkpoint()

        return sorted_targets

class TargetFacilitySelectionView(Raise403PermissionRequiredMixin, FormView):
    """
    View to select targets suitable to observe from a specific facility/location, taking into account target visibility
    from that site, as well as other user-defined constraints.
    """
    template_name = 'tom_targets/target_facility_selection.html'
    paginate_by = 25
    strict = False
    model = Target
    permission_required = 'tom_targets.view_target'
    form_class = TargetSelectionForm

    def get_context_data(self, *args, **kwargs):
        """
        Adds the ``TargetListShareForm`` to the context and prepopulates the hidden fields.
        :returns: context object
        :rtype: dict
        """
        context = super().get_context_data(*args, **kwargs)
        # Surely this needs to verify that the user has permission?
        context['form'] = TargetSelectionForm()

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to select targets suitable for observation from this facility

        :param request: The HTML request object
        :param args: Optional arguments if any
        :param kwargs: Optional kwargs if any
        :return: HTTPRequest
        """

        # Configuration:
        # Maximum airmass limit to consider a target visible
        # Number of intervals with which to calculate visibility throughout a single night
        airmass_max = 2.0
        visibiliy_intervals = 10
        context = super().get_context_data(*args, **kwargs)

        # Parse the date, handling exceptions
        try:
            start_time = datetime.strptime(request.POST.get('date') + 'T00:00:00', '%Y-%m-%dT%H:%M:%S')
            end_time = datetime.strptime(request.POST.get('date') + 'T23:59:59', '%Y-%m-%dT%H:%M:%S')

            # Gather the list of targets, either from the selected target list, or all targets accessible
            # to the user.  This produces a QuerySet either way.
            if len(request.POST.get('target_list')) > 0:
                targets = querytools.get_targetlist_alive_events(targetlist_name=request.POST.get('target_list'))
            else:
                targets = querytools.get_targetlist_alive_events(targetlist_name='all')
            logger.info('FacilitySelectView: Retrieved ' + str(len(targets)) + ' targets')

            # Configure output target table.
            # The displayed table can be extended to include selected extra_fields for each target,
            # if configured in the TOM's settings.py. So we set the list of table columns accordingly.
            table_columns = [
                'Target', 'RA', 'Dec', 'Site', 'Min airmass'
            ] + settings.SELECTION_EXTRA_FIELDS
            #for param in settings.SELECTION_EXTRA_FIELDS:
            #    table_columns.append(param)
            context['table_columns'] = table_columns
            context['observable_targets'] = []
            logger.info('FacilitySelectView: table columns: ' + repr(table_columns))

            # Calculate the visibility of all selected targets on the date given
            # Since some observatories include multiple sites, the visibiliy_data returned is always
            # a dictionary indexed by site code.  Our purpose here is to verify whether each target is ever
            # visible at lower airmass than the limit from any site - if so the target is considered to be visible
            objects = []
            observable_targets = []
            for object in targets:
                airmass_limit = 2.0 # Hardcoded for now
                logger.info('FacilitySelectView: calculating visibility for ' + object.name)
                visibility_data = get_sidereal_visibility(
                    object, start_time, end_time,
                    visibiliy_intervals, airmass_max,
                    observation_facility=request.POST.get('observatory')
                )
                logger.info('FacilitySelectView: Got visibility data')
                for site, vis_data in visibility_data.items():
                    airmass_data = np.array([x for x in vis_data[1] if x])
                    if len(airmass_data) > 0:
                        s = SkyCoord(object.ra, object.dec, frame='icrs', unit=(u.deg, u.deg))
                        target_data = [
                            s.ra.to_string(u.hour), s.dec.to_string(u.deg, alwayssign=True),
                            site, round(airmass_data.min(), 1)
                        ]

                        # Extract any requested extra parameters for this object, if available
                        for param in settings.SELECTION_EXTRA_FIELDS:
                            target_data.append(getattr(object, param))
                        objects.append(object)
                        observable_targets.append(target_data)
                        logger.info('FacilitySelectView: Got observable target ' + object.name)

            context['observable_targets'] = zip(objects, observable_targets)

        except ValueError:
            messages.add_message(request, messages.WARNING, "Invalid date given")

        return self.render_to_response(context)
