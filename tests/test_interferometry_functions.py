from django.test import TestCase
from unittest import skip
from tom_targets.tests.factories import SiderealTargetFactory
from tom_dataproducts.models import ReducedDatum
from mop.toolbox import interferometry_prediction
from astropy.table import Table, Column
from mop.brokers import gaia
from astropy.coordinates import Angle
from astroquery.utils.commons import TableList
import numpy as np
from datetime import datetime

class TestInterferomeinterferometry_predictiontryFunctions(TestCase):
    def setUp(self):
        self.st = SiderealTargetFactory.create()
        self.st.ra = 274.2974
        self.st.dec = -22.3452
        self.st.u0 = 0.08858
        self.st.u0_error = 0.0003
        self.st.baseline_magnitude = 17.989
        self.st.save()
        neighbours = gaia.query_gaia_dr3(self.st, radius=Angle(5.0/3600.0, "deg"))
        test_star = {'Gmag': 14.0,
                     'BPRP': 0.3,
                     'u0': 0.01,
                     'u0_error': 0.01,
                     'Klens': 9.0,
                     'Kneighbours1': [12.0, 8.5, 10.7, 10.9],
                     'Kneighbours2': [13.5, 11.5, 13.5, 12.6]}
        test_star2 = {'Gmag': 8.0,
                     'BPRP': 0.3,
                     'u0': 0.01,
                     'u0_error': 0.01,
                     'Klens': 9.0,
                     'Kneighbours1': [9.5, 8.0, 10.7, 10.9]}
        self.params = {
            'test_event': self.st,
            'test_catalog': neighbours,
            'test_star': test_star,
            'test_star2': test_star2
                       }
        lc = np.zeros((100,2))
        lc[:,0] = 2460000.0 + np.arange(2460000.0,2460100.0,1.0)
        lc[:,1].fill(16.5)
        lc[50:75,1].fill(13.2)
        self.params['lc'] = lc
        model_time = datetime.strptime('2018-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        rd, created = ReducedDatum.objects.get_or_create(
            timestamp=model_time,
            value={
            'lc_model_time': lc[:,0].tolist(),
            'lc_model_magnitude': lc[:,1].tolist()
            },
            source_name='MOP',
            source_location=self.st.name,
            data_type='lc_model',
            target=self.st
        )

    def test_convert_Gmag_to_JHK(self):

        (J, H, K) = interferometry_prediction.convert_Gmag_to_JHK(self.params['test_catalog'][0]['Gmag'],
                                                                 self.params['test_catalog'][0]['BP-RP'])
        for passband in [J, H, K]:
            assert(len(passband) == len(self.params['test_catalog'][0]['Gmag']))

    def test_find_companion_stars(self):

        stars_table = interferometry_prediction.find_companion_stars(self.params['test_event'],
                                                                    self.params['test_catalog'])

        assert(type(stars_table) == type(Table([])))
        assert(len(stars_table) <= len(self.params['test_catalog'].values()[0]))
        assert(len(stars_table.columns) == 4)

    def test_estimate_target_peak_phot_uncertainties(self):
        peak_phot = interferometry_prediction.estimate_target_peak_phot_uncertainties(self.params['test_star']['Gmag'],
                                                                                      self.params['test_star']['BPRP'],
                                                                                      self.params['test_star']['u0'],
                                                                                      self.params['test_star']['u0_error'])
        assert(peak_phot['Gerror'] < 2.0)

    def test_interferometry_decision(self):
        (mode1, guide1) = interferometry_prediction.interferometry_decision(self.params['test_star']['Gmag'],
                                                                           self.params['test_star']['BPRP'],
                                                                            self.params['test_star']['Kneighbours1'])
        assert(mode1 == 'Dual Field Wide')
        assert(guide1 == 1)

        (mode2, guide2) = interferometry_prediction.interferometry_decision(self.params['test_star']['Gmag'],
                                                                           self.params['test_star']['BPRP'],
                                                                           self.params['test_star']['Kneighbours2'])
        assert (mode2 == 'No')
        assert (guide2 == 0)

        (mode2, guide2) = interferometry_prediction.interferometry_decision(self.params['test_star2']['Gmag'],
                                                                           self.params['test_star2']['BPRP'],
                                                                           self.params['test_star2']['Kneighbours1'])
        assert (mode2 == 'Single Field')
        assert (guide2 == 0)

    def test_evaluate_target_for_interferometry(self):
        interferometry_prediction.evaluate_target_for_interferometry(self.params['test_event'])

    def test_search_gsc_catalog(self):
        (gsc_table, AOFT_table) = interferometry_prediction.search_gsc_catalog(self.params['test_event'])
        print(gsc_table)
        print(AOFT_table)
        
        assert(type(gsc_table) == type(Table([])))
        assert(type(AOFT_table) == type(Table([])))

    def test_predict_peak_brightness(self):
        mag_peak = interferometry_prediction.predict_peak_brightness(self.params['test_star']['Klens'],
                                                                       self.params['test_star']['u0'])

        assert(type(mag_peak) == np.float64)
        assert(mag_peak < self.params['test_star']['Klens'])

    def test_predict_period_above_brightness_threshold(self):
        target = self.st
        Kbase = 11.0

        test_interval = self.params['lc'][:,0].max() - self.params['lc'][:,0].min()

        interval = interferometry_prediction.predict_period_above_brightness_threshold(target, Kbase, Kthreshold=14.0)

        assert(type(interval) == np.float64)
        assert(interval == test_interval)

    def test_gravity_target_selection(self):
        Kpeak = 13.5
        interval = 4.0
        gsc_table = Table([
                Column(name='AOstar', data=np.array([0.0,0.0,0.0,1.0,1.0])),
                Column(name='FTstar', data=np.array([1.0,0.0,1.0,0.0,0.0]))
        ])
        interferometry_prediction.gravity_target_selection(self.st, Kpeak, interval, gsc_table, Kthreshold=14.0)
        print(self.st.extra_fields)

        assert(self.st.extra_fields['Interferometry_candidate'])
