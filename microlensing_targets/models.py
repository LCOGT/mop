from django.db import models
from tom_targets.models import BaseTarget
from astropy.time import Time
from datetime import datetime
import json
import logging
import pytz
import numpy as np

logger = logging.getLogger(__name__)

# Create your models here.
class MicrolensingTarget(BaseTarget):
    """
    Customized Target model including attributes relating the observation and modeling of microlensing events
    """

    # Microlensing-specific fields
    alive = models.BooleanField(default=True)
    classification = models.CharField(max_length=50, default='Microlensing PSPL')
    category = models.CharField(max_length=50, default='Microlensing stellar/planet')
    observing_mode = models.CharField(max_length=20, default=' No')
    sky_location = models.CharField(max_length=20, default='Unknown')
    t0 = models.FloatField(default=0)
    t0_error = models.FloatField(default=0)
    u0 = models.FloatField(default=0)
    u0_error = models.FloatField(default=0)
    tE = models.FloatField(default=0)
    tE_error = models.FloatField(default=0)
    piEN = models.FloatField(default=0)
    piEN_error = models.FloatField(default=0)
    piEE = models.FloatField(default=0)
    piEE_error = models.FloatField(default=0)
    rho = models.FloatField(default=0)
    rho_error = models.FloatField(default=0)
    s = models.FloatField(default=0)
    s_error = models.FloatField(default=0)
    q = models.FloatField(default=0)
    q_error = models.FloatField(default=0)
    alpha = models.FloatField(default=0)
    alpha_error = models.FloatField(default=0)
    source_magnitude = models.FloatField(default=0)
    source_mag_error = models.FloatField(default=0)
    blend_magnitude = models.FloatField(default=0)
    blend_mag_error = models.FloatField(default=0)
    baseline_magnitude = models.FloatField(default=0)
    baseline_mag_error = models.FloatField(default=0)
    gaia_source_id = models.CharField(max_length=30, default='')
    gmag = models.FloatField(default=0)
    gmag_error = models.FloatField(default=0)
    rpmag = models.FloatField(default=0)
    rpmag_error = models.FloatField(default=0)
    bpmag = models.FloatField(default=0)
    bpmag_error = models.FloatField(default=0)
    bprp = models.FloatField(default=0)
    bprp_error = models.FloatField(default=0)
    reddening_bprp = models.FloatField(default=0)
    extinction_g = models.FloatField(default=0)
    #distance = models.FloatField(default=0)        # In BaseTarget model
    teff = models.FloatField(default=0)
    logg = models.FloatField(default=0)
    metallicity = models.FloatField(default=0)
    ruwe = models.FloatField(default=0)
    fit_covariance = models.JSONField(default=dict)
    tap_priority = models.FloatField(default=0)
    tap_priority_error = models.FloatField(default=0)
    tap_priority_longte = models.FloatField(default=0)
    tap_priority_longte_error = models.FloatField(default=0)
    interferometry_mode = models.CharField(max_length=30, default='')
    interferometry_guide_star = models.FloatField(default=0)
    interferometry_candidate = models.BooleanField(default=False)
    spectras = models.FloatField(default=0)
    last_fit = models.FloatField(default=2446756.50000)
    chi2 = models.FloatField(default=99999.9999)
    red_chi2 = models.FloatField(default=99999.9999)
    ks_test = models.FloatField(default=0)
    sw_test = models.FloatField(default=0)
    ad_test = models.FloatField(default=0)
    latest_data_hjd = models.FloatField(default=0)
    latest_data_utc = models.DateTimeField(null=True)
    mag_now = models.FloatField(default=0)
    mag_now_passband = models.CharField(max_length=10, default='')
    mag_peak_J = models.FloatField(default=0)
    mag_peak_J_error = models.FloatField(default=0)
    mag_peak_H = models.FloatField(default=0)
    mag_peak_H_error = models.FloatField(default=0)
    mag_peak_K = models.FloatField(default=0)
    mag_peak_K_error = models.FloatField(default=0)
    mag_base_J = models.FloatField(default=0)
    mag_base_H = models.FloatField(default=0)
    mag_base_K = models.FloatField(default=0)
    interferometry_interval = models.FloatField(default=0)
    YSO = models.BooleanField(default=False)
    QSO = models.BooleanField(default=False)
    galaxy = models.BooleanField(default=False)
    TNS_name = models.CharField(max_length=20, default='None')
    TNS_class = models.CharField(max_length=30, default='None')

    class Meta:
        verbose_name = "target"
        permissions = (
            ('view_target', 'View Target'),
            ('add_target', 'Add Target'),
            ('change_target', 'Change Target'),
            ('delete_target', 'Delete Target')
        )

    def get_target_names(self, qs):
        """Attributes the names associated with this target"""
        for name in qs:
            self.targetnames.append(name.name)


    def get_reduced_data(self, qs):
        """Extracts the timeseries data from a QuerySet of ReducedDatums, and
        creates the necessary arrays"""

        # Store the complete set of results
        self.red_data = qs

        # Unpack the lightcurve data:
        self.repackage_lightcurves(self.red_data)

        # Extract the timestamp of the last observation
        time = [Time(i.timestamp).jd for i in self.red_data if i.data_type == 'photometry']
        if len(time) > 0:
            self.first_observation = min(time)
            self.last_observation = max(time)
        else:
            self.first_observation = None
            self.last_observation = None

        # Identify any pre-existing datasets of specific categories, if available
        self.existing_model = None
        self.gsc_results = None
        self.aoft_table = None
        self.neighbours = []
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

    def repackage_lightcurves(self, qs):
        """Method to sort through a QuerySet of the ReducedDatums for a given event and repackage the data as a
         dictionary of individual lightcurves in PyLIMA-compatible format for different facilities.
         Note that not all of the QuerySet of ReducedDatums may be photometry, so some sorting is required.
         """

        datasets = {}

        for rd in qs:
            if rd.data_type == 'photometry' and rd.source_name != 'Interferometry_predictor':
                # Identify different lightcurves from the filter label given
                passband = rd.value['filter']
                if passband in datasets.keys():
                    lc = datasets[passband]
                else:
                    lc = []

                # Append the datapoint to the corresponding dataset
                try:
                    lc.append([Time(rd.timestamp).jd, rd.value['magnitude'], rd.value['error']])
                except:
                    lc.append([Time(rd.timestamp).jd, rd.value['magnitude'], 1.0])

                datasets[passband] = lc

        # Count the total number of datapoints available, and convert the
        # accumulated lightcurves into numpy arrays:
        ndata = 0
        for passband, lc in datasets.items():
            ndata += len(lc)
            datasets[passband] = np.array(lc)

        self.datasets = datasets
        self.ndata = ndata

    def check_need_to_fit(self):
        """
        Evaluates whether or not this MicrolensingTarget has an up-to-date model fit, or
        is due for re-modeling.
        """
        reason = 'OK'
        self.need_to_fit = True

        if self.last_observation:
            if self.last_fit:
                if (float(self.last_observation) < float(self.last_fit)):
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
        """Method to store in the TOM the timeseries lightcurve corresponding to a fitted model.
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
                source_location=self.name,
                data_type='lc_model',
                target=self
            )

            rd.save()
            self.existing_model = rd

        # If there is a pre-existing model, update it
        else:
            self.existing_model.timestamp = model_time
            self.existing_model.value = data
            self.existing_model.source_name = 'MOP'
            self.existing_model.source_location = self.name
            self.existing_model.data_type = 'lc_model'
            self.existing_model.target = self
            self.existing_model.defaults = {'value': data}
            self.existing_model.save()

    def store_model_parameters(self, model_params):
        """Function to store the fitted model parameters in the TOM"""

        parameters = ['alive', 'last_fit',
                      't0', 't0_error', 'u0', 'u0_error', 'tE', 'tE_error',
                      'piEN', 'piEN_error', 'piEE', 'piEE_error',
                      'source_magnitude', 'source_mag_error',
                      'blend_magnitude', 'blend_mag_error',
                      'baseline_magnitude', 'baseline_mag_error',
                      'fit_covariance', 'chi2', 'red_chi2',
                      'ks_test', 'ad_test', 'sw_test']

        for key in parameters:
            if key == 'fit_covariance':
                data = json.dumps(model_params['Fit_covariance'].tolist())
            else:
                data = model_params[key]
            setattr(self, key, data)
            self.save()

    def store_parameter_set(self, parameters):
        """Method to store a flexible set of target attributes"""

        for key, data in parameters.items():
            if key == 'fit_covariance':
                data = json.dumps(data.tolist())
            setattr(self, key, data)
            self.save()