from django.test import TestCase
from django.conf import settings
from unittest import skip
from tom_targets.tests.factories import SiderealTargetFactory
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target, TargetExtra
import numpy as np
from os import getcwd, path
from mop.toolbox import fittools
from astropy.time import Time, TimeDelta, TimezoneInfo
from astropy import units as u
from astropy.table import Column, Table, QTable
from pyLIMA.models import PSPL_model
from pyLIMA.fits import TRF_fit
from pyLIMA import event
from pyLIMA import telescopes
from datetime import datetime
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class TestModelingTools(TestCase):
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        st1.name = 'OGLE-2023-BLG-0348'
        st1.ra = 271.1925
        st1.dec = -28.3164
        # Configure parameters added by retrival of data function
        st1.existing_model = None
        st1.first_observation = None
        st1.last_observation = None
        st1.gsc_results = None
        st1.aoft_table = None
        st1.neighbours = []
        st1.save()
        pevent = self.generate_test_pylima_event(st1)
        cwd = getcwd()
        lightcurve_file = path.join(cwd,'tests/data/OGLE-2023-BLG-0348_phot.dat')
        # Configuration for the different telescopes, dataset_label: [Npts, baseline_mag, median_sigma, tstart, cadence]
        self.tel_configs = {
            'I': [2000, 18.0, 0.01,
                  Time('2023-08-01T00:00:00.0', format='isot'),
                  TimeDelta(0.25*u.day)],
            'G': [100, 17.5, 0.005,
                  Time('2023-08-01T00:00:00.0', format='isot'),
                  TimeDelta(1.0*u.day)]
        }
        photometry = generate_test_ReducedDatums(st1, self.tel_configs)
        model = self.generate_test_pylima_model(pevent)
        model_params = {
            't0': 2560000.5,
            'u0': 0.01,
            'tE': 25.0,
            'piEN': 0.01,
            'piEE': -0.01,
            'source_magnitude': 20.0,
            'blend_magnitude': 22.0,
            'baseline_magnitude': 18.0,
            'fit_covariance': np.array([[ 6.87022167e-02,  3.98934577e-02, -3.93590563e-01, 1.94853293e+02, -1.94841317e+02],
                                        [ 3.98934577e-02,  1.85115375e-01, -1.99280530e+00, 9.00451030e+02, -9.00210742e+02],
                                        [-3.93590563e-01, -1.99280530e+00,  2.17189010e+01, -9.70655580e+03,  9.70368365e+03],
                                        [ 1.94853293e+02,  9.00451030e+02, -9.70655580e+03, 4.38193327e+06, -4.38077388e+06],
                                        [-1.94841317e+02, -9.00210742e+02,  9.70368365e+03,-4.38077388e+06,  4.37962601e+06]]),
            'chi2': 3000.0,
            'red_chi2': 1.02,
            'fit_parameters': OrderedDict(
                [('t0', [0, (2457790.87823, 2460180.67737)]),
                 ('u0', [1, (0.0, 1.0)]),
                 ('tE', [2, (0.1, 500)]),
                 ('fsource_Tel_0', [3, (0.0, 5445.026528424209)]),
                 ('fblend_Tel_0', [4, (-5445.026528424209, 5445.026528424209)])]
                )
            }
        self.params = {
            'target': st1,
            'lightcurve_file': lightcurve_file,
            'photometry': photometry,
            'pylima_event': pevent,
            'pylima_model': model,
            'model_params': model_params
            }

    def load_test_photometry(self, lightcurve_file):

        data = np.loadtxt(lightcurve_file)
        photometry = []
        for row in data:
            photometry.append([float(row[0]), float(row[1]), float(row[2])])

        datasets = {}
        datasets['I'] = np.array(photometry)

        return datasets

    def generate_test_pylima_event(self, target):
        pevent = event.Event(ra=target.ra, dec=target.dec)
        pevent.name = target.name
        return pevent
    
    def generate_test_pylima_model(self, pevent):
        pspl = PSPL_model.PSPLmodel(pevent)
        npts = 500
        data = [
            Column(name='time', data=np.linspace(2460000.0, 2460500.0, npts)),
            Column(name='mag', data=np.random.normal(loc=18.0, scale=0.5, size=npts))
        ]
        pspl.lightcurve_magnitude = Table(data)
        return pspl

    def test_fit_pspl_omega2(self):

        datasets = self.load_test_photometry(self.params['lightcurve_file'])

        (model_params, model_lightcurve) = fittools.fit_pspl_omega2(
                self.params['target'].ra, self.params['target'].dec, datasets)

        expected_keys = [
            't0', 'u0', 'tE', 'piEN', 'piEE',
            'source_magnitude', 'blend_magnitude', 'baseline_magnitude',
            'fit_covariance', 'chi2', 'red_chi2'
        ]

        for key in expected_keys:
            assert (key in model_params.keys())

    def test_repackage_lightcurves(self):

        (datasets, ndata) = fittools.repackage_lightcurves(self.params['photometry'])

        assert(type(datasets) == type({}))
        assert(len(datasets.keys()) == len(self.tel_configs.keys()))

        test_ndata = 0
        for tel, config in self.tel_configs.items():
            test_ndata += config[0]
        assert(ndata == test_ndata)

        for dname, config in self.tel_configs.items():
            datalist = datasets[dname]
            assert(type(datalist) == type(np.array([])))
            assert(len(datalist) == config[0])

    def test_store_model_lightcurve(self):

        fittools.store_model_lightcurve(self.params['target'], self.params['pylima_model'])

        qs = ReducedDatum.objects.filter(
            source_name='MOP',
            data_type='lc_model',
            source_location=self.params['target'].name
        )

        assert(qs.count() > 0)
        
    def test_event_alive(self):
        t0_fit = Time.now() + TimeDelta(2.0*u.day)
        tE_fit = 25.0
        last_obs_jd = (Time.now() - TimeDelta(0.1*u.day)).jd

        status = fittools.check_event_alive(t0_fit.jd, tE_fit, last_obs_jd)
        assert(status == True)

        t0_fit = Time.now() - TimeDelta(75.0 * u.day)
        tE_fit = 25.0

        status = fittools.check_event_alive(t0_fit.jd, tE_fit, last_obs_jd)
        assert(status == False)

    def test_store_model_parameters(self):

        self.params['target'].store_model_parameters(
            self.params['model_params']
        )

        qs = Target.objects.filter(name=self.params['target'].name)
        t = qs[0]

        for key, value in self.params['model_params'].items():
            if key != 'fit_covariance' and key != 'fit_parameters':
                test_value = getattr(t, key)
                assert(value == float(test_value))

    def test_store_parameter_set(self):

        self.params['target'].store_parameter_set({'alive': True})

        qs = Target.objects.filter(name=self.params['target'].name)
        t = qs[0]

        assert(t.alive == True)

    def test_pylima_telescopes_from_datasets(self):

        (datasets, ndata) = fittools.repackage_lightcurves(self.params['photometry'])

        tel_list = fittools.pylima_telescopes_from_datasets(datasets, emag_limit=None)

        assert(len(tel_list) == len(datasets))
        for tel in tel_list:
            assert(type(tel) == type(telescopes.Telescope()))

    def test_gather_model_parameters(self):

        # Load test dataset
        datasets = self.load_test_photometry(self.params['lightcurve_file'])

        # Fit a standard PSPL model
        pevent = self.params['pylima_event']
        tel_list = fittools.pylima_telescopes_from_datasets(datasets)
        for tel in tel_list:
            pevent.telescopes.append(tel)

        pevent.find_survey('Tel_0')
        pevent.check_event()
        pspl = PSPL_model.PSPLmodel(pevent, parallax=['None', 0.])
        pspl.define_model_parameters()
        model_fit = TRF_fit.TRFfit(pspl, loss_function='soft_l1')
        model_fit.fit()

        model_params = fittools.gather_model_parameters(pevent, model_fit)

        expected_keys = [
            't0', 't0_error', 'u0', 'u0_error', 'tE', 'tE_error',
            'piEN', 'piEN_error', 'piEE', 'piEE_error',
            'source_magnitude', 'source_mag_error',
            'blend_magnitude', 'blend_mag_error',
            'baseline_magnitude', 'baseline_mag_error',
            'fit_covariance', 'chi2', 'red_chi2'
        ]
        for key in expected_keys:
            assert(key in model_params.keys())

    def test_test_quality_of_model_fit(self):

        result = fittools.test_quality_of_model_fit(self.params['model_params'])

        self.assertTrue(result)

    def test_evaluate_model(self):

        revised_model = fittools.evaluate_model(self.params['model_params'])

        for key in ['t0', 'u0', 'tE']:
            assert(revised_model[key] == self.params['model_params'][key])

        bad_model = self.params['model_params']
        bad_model['tE'] = bad_model['fit_parameters']['tE'][1][1]

        revised_model = fittools.evaluate_model(bad_model, verbose=True)

        for key in ['t0', 'u0', 'tE']:
            assert(np.isnan(revised_model[key]))

    def test_generate_model_lightcurve(self):

        # Load test dataset
        datasets = self.load_test_photometry(self.params['lightcurve_file'])

        # Create PyLIMA event object with data
        pevent = self.params['pylima_event']
        tel_list = fittools.pylima_telescopes_from_datasets(datasets)
        for tel in tel_list:
            pevent.telescopes.append(tel)

        # Generate a model lightcurve
        model_tel = fittools.generate_model_lightcurve(pevent,
                                                       self.params['model_params'])

        assert(len(model_tel.lightcurve_magnitude) > 0)
        assert(model_tel.lightcurve_magnitude.colnames == ['time', 'mag', 'err_mag'])


def generate_test_ReducedDatums(target, tel_configs, source_name='OGLE'):
    """Method generates a set of ReducedDatums for different telescopes, as is held in the TOM for a
    single target"""

    data = []
    for tel_label, config in tel_configs.items():
        mags = np.random.normal(loc=config[1], scale=config[2], size=config[0])
        mag_errs = np.random.normal(loc=config[2], scale=config[2], size=config[0])
        for i in range(0,config[0],1):
            ts = config[3] + i*config[4]
            datum = {
                    'magnitude': mags[i],
                    'filter': tel_label,
                    'error': mag_errs[i]
                    }
            rd, created = ReducedDatum.objects.get_or_create(
                timestamp=ts.to_datetime(timezone=TimezoneInfo()),
                value=datum,
                source_name=source_name,
                source_location=target.name,
                data_type='photometry',
                target=target)

            if created:
                data.append(rd)

    return data