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
                     'Klens_error': 0.02,
                     'Kneighbours1': [12.0, 8.5, 10.7, 10.9],
                     'Kneighbours2': [13.5, 11.5, 13.5, 12.6]}
        test_star2 = {'Gmag': 8.0,
                     'BPRP': 0.3,
                     'u0': 0.01,
                     'u0_error': 0.01,
                     'Klens': 9.0,
                     'Klens_error': 0.02,
                     'Kneighbours1': [9.5, 8.0, 10.7, 10.9]}
        gaia_results = {
            'integers': {
                'gaia_source_id': 4090514384506170112,
                'interferometry_guide_star': 0,
            },
            'strings': {
                'interferometry_mode': 'No',
            },
            'infinite': {
                'interferometry_interval': np.inf
            },
            'floats': {
                'gmag': [14.635431, 3],
                'rpmag': [13.388377, 3],
                'bpmag': [16.365704, 3],
                'bprp': [2.977326, 3],
                'reddening_bprp': [1.8286999464035034, 3],
                'extinction_g': [3.335200071334839, 3],
                'distance': [3223.7322, 2],
                'teff': [4696.2, 1],
                'logg': [2.1198, 2],
                'metallicity': [-0.1919, 2],
                'ruwe': [0.97, 1],
                'mag_base_J': [11.345669404897574, 3],
                'mag_base_H': [10.311202259386521, 3],
                'mag_base_K': [9.91359681641258, 3],
                'mag_peak_J': [8.710477886261481, 3],
                'mag_peak_J_error': [0.09991039186734962, 3],
                'mag_peak_H': [7.676010740750428, 3],
                'mag_peak_H_error': [0.09991039186734962, 3],
                'mag_peak_K': [7.278405297776487, 3],
                'mag_peak_K_error': [0.09991039186734962, 3]
            }
        }
        self.params = {
            'test_event': self.st,
            'test_catalog': neighbours,
            'test_star': test_star,
            'test_star2': test_star2,
            'gaia_results_test_event': gaia_results
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
        assert(len(stars_table.columns) == 17)

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
        # If successful, the target should now have populated entries for
        # 1) Gaia stellar information
        # 2) A reduceddatum labeled 'Interferometry_predictor'
        # (Other outputs are tested by separate unittests)
        st = self.params['test_event']
        for key, test_value in self.params['gaia_results_test_event']['integers'].items():
            assert(getattr(st, key) == test_value)
        for key, test_value in self.params['gaia_results_test_event']['strings'].items():
            assert(getattr(st, key) == test_value)
        for key, test_value in self.params['gaia_results_test_event']['infinite'].items():
            assert(np.isinf(getattr(st, key)))
        for key, test_value in self.params['gaia_results_test_event']['floats'].items():
            np.testing.assert_almost_equal(getattr(st, key), test_value[0], decimal=test_value[1])

        qs = ReducedDatum.objects.filter(
            target=st,
            source_name='Interferometry_predictor'
        )
        assert(qs.count() > 0)

    def test_search_gsc_catalog(self):
        (gsc_table, AOFT_table) = interferometry_prediction.search_gsc_catalog(self.params['test_event'])
        print(gsc_table)
        print(AOFT_table)
        
        assert(type(gsc_table) == type(Table([])))
        assert(type(AOFT_table) == type(Table([])))

    def test_predict_peak_brightness(self):
        mag_peak, mag_peak_error = interferometry_prediction.predict_peak_brightness(
            self.params['test_star']['Klens'],
            self.params['test_star']['Klens_error'],
            self.params['test_star']['u0'],
            self.params['test_star']['u0_error'],
            )

        assert(type(mag_peak) == np.float64)
        assert(type(mag_peak_error) == np.float64)
        assert(mag_peak < self.params['test_star']['Klens'])
        assert(mag_peak_error < mag_peak)

    def test_predict_period_above_brightness_threshold(self):
        target = self.st
        Kbase = 16.5

        test_interval = self.params['lc'][:,0].max() - self.params['lc'][:,0].min()
        qs = ReducedDatum.objects.filter(source_name='MOP', data_type='lc_model',
                                         source_location=target.name)

        interval = interferometry_prediction.predict_period_above_brightness_threshold(target, Kbase, Kthreshold=14.0)

        assert(type(interval) == np.float64 or type(interval) == float)
        assert(interval < test_interval)

    def test_gravity_target_selection(self):
        Kpeak = 13.5
        interval = 4.0
        gsc_table = Table([
                Column(name='AOstar', data=np.array([0.0,0.0,0.0,1.0,1.0])),
                Column(name='FTstar', data=np.array([1.0,0.0,1.0,0.0,0.0]))
        ])
        interferometry_prediction.gravity_target_selection(self.st, Kpeak, interval, gsc_table, Kthreshold=14.0)

        assert(self.st.interferometry_candidate)
