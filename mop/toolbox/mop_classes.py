from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target,TargetExtra
from astropy.time import Time
from mop.toolbox import fittools
from datetime import datetime
import json
import logging
import pytz

logger = logging.getLogger(__name__)

class MicrolensingEvent():
    """
    Superclass designed to consolidate data associated with a single microlensing event in a 
    form convenient for processing
    """

    def __init__(self, t):
        self.name = t.name
        self.target = t
        try:
            self.ra = float(t.ra)
            self.dec = float(t.dec)
        except TypeError:
            self.ra = t.ra
            self.dec = t.dec
            logger.warning('MicrolensingEvent: Target ' + t.name + ' has invalid RA='
                           + repr(t.ra) + ', Dec=' + repr(t.dec))
        if t.galactic_lat and t.galactic_lng:
            self.galactic_lng = float(t.galactic_lng)
            self.galactic_lat = float(t.galactic_lat)
        else:
            self.galactic_lat = None
            self.galactic_lng = None
        self.targetnames = []
        self.red_data = None
        self.extras = None
        self.Last_fit = None
        self.first_observation = None
        self.last_observation = None
        self.existing_model = None
        self.neighbours = None
        self.gsc_results = None
        self.aoft_table = None
        self.pylima_model = None
        self.need_to_fit = True

    def __str__(self):
        return str(self.name)

    def set_extra_params(self, qs):
        """Extracts the key, value pairs from a QuerySet of ExtraFields and sets them as
        attributes of the Event"""
        self.extras = {}
        for par in qs:
            setattr(self, par.key, par.value)
            self.extras[par.key] = par

    def set_target_names(self, qs):
        """Attributes the names associated with this target"""
        for name in qs:
            self.targetnames.append(name.name)

    def set_reduced_data(self, qs):
        """Extracts the timeseries data from a QuerySet of ReducedDatums, and
        creates the necessary arrays"""

        # Store the complete set of results
        self.red_data = qs

        # Unpack the lightcurve data:
        (self.datasets, self.ndata) = fittools.repackage_lightcurves(self.red_data)

        # Extract the timestamp of the last observation
        time = [Time(i.timestamp).jd for i in self.red_data if i.data_type == 'photometry']
        if len(time) > 0:
            self.first_observation = min(time)
            self.last_observation = max(time)
        else:
            self.first_observation = None
            self.last_observation = None

        # Identify any pre-existing datasets of specific categories, if available
        for dset in qs:
            if dset.data_type == 'lc_model':
                self.existing_model = dset

            if dset.data_type == 'tabular' and dset.source_name == 'Interferometry_predictor':
                self.neighbours = dset

            if dset.data_type == 'tabular' and dset.source_name == 'GSC_query_results':
                self.gsc_results = dset

            if dset.data_type == 'tabular' and dset.source_name == 'AOFT_table':
                self.aoft_table = dset

            if self.existing_model and self.neighbours \
                    and self.gsc_results and self.aoft_table:
                break

    def check_need_to_fit(self):
        reason = 'OK'

        if self.last_observation:
            if self.Last_fit:
                if (float(self.last_observation) < float(self.Last_fit)):
                    self.need_to_fit = False
                    reason = 'Up to date model'
            else:
                reason = 'No previous model fit recorded'

        # If last_observation is not set, then there are no data to model
        else:
            self.need_to_fit = False
            reason = 'No last observation'

        return self.need_to_fit, reason

    def store_model_lightcurve(self, model):
        """Method to store in the TOM the timeseries lihgtcurve corresponding to a fitted model.
        The input is a model fit object from PyLIMA"""

        tz = pytz.timezone('utc')
        model_time = datetime.utcnow().replace(tzinfo=tz)

        # Extract the model lightcurve timeseries from the PyLIMA fit object
        data = {
            'lc_model_time': model.lightcurve_magnitude['time'].value.tolist(),
            'lc_model_magnitude': model.lightcurve_magnitude['mag'].value.tolist()
        }

        # If there is no existing model for this target, create one
        if not self.existing_model:
            rd = ReducedDatum.objects.create(
                timestamp=model_time,
                value=data,
                source_name='MOP',
                source_location=self.target.name,
                data_type='lc_model',
                target=self.target
            )

            rd.save()
            self.existing_model = rd

        # If there is a pre-existing model, update it
        else:
            self.existing_model.timestamp = model_time
            self.existing_model.value = data
            self.existing_model.source_name = 'MOP'
            self.existing_model.source_location = self.target.name
            self.existing_model.data_type = 'lc_model'
            self.existing_model.target = self.target
            self.existing_model.defaults = {'value': data}
            self.existing_model.save()

    def store_model_parameters(self, model_params):
        """Function to store the fitted model parameters in the TOM"""

        parameters = ['Alive', 'Last_fit',
                      't0', 't0_error', 'u0', 'u0_error', 'tE', 'tE_error',
                      'piEN', 'piEN_error', 'piEE', 'piEE_error',
                      'Source_magnitude', 'Source_mag_error',
                      'Blend_magnitude', 'Blend_mag_error',
                      'Baseline_magnitude', 'Baseline_mag_error',
                      'Fit_covariance', 'chi2', 'red_chi2',
                      'KS_test', 'AD_test', 'SW_test']

        for key in parameters:
            if key in self.extras.keys():
                if key == 'Fit_covariance':
                    data = json.dumps(model_params['Fit_covariance'].tolist())
                else:
                    data = model_params[key]
                self.extras[key].value = data
                self.extras[key].save()
            else:
                ep = TargetExtra.objects.create(
                    target = self.target,
                    key = key,
                    value = data
                    )
                ep.save()
                self.extras[key] = ep

    def store_parameter_set(self, parameters):

        for key, data in parameters.items():
            if key == 'Fit_covariance':
                data = json.dumps(data.tolist())
            setattr(self, key, data)
            if key in self.extras.keys():
                self.extras[key].value = data
                self.extras[key].save()
            else:
                ep = TargetExtra.objects.create(
                    target = self.target,
                    key = key,
                    value = data
                    )
                ep.save()
                self.extras[key] = ep