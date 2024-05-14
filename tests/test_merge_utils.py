from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
from datetime import datetime
from tom_targets.models import TargetExtra
from mop.management.commands import merge_utils
import copy

class TestMergeExtraParams(TestCase):
    """
    Class describing tests of the functions to merge the extra parameters associated with
    duplicated Targets.
    """

    def setUp(self):
        self.primary_target = SiderealTargetFactory.create()
        self.primary_target.name = 'OGLE-2023-GD-0011'
        self.primary_target.ra = 244.6058
        self.primary_target.dec = -54.0788
        self.primary_extras = {
            'Alive': 'True',
            'Classification': 'Microlensing PSPL',
            'Category': 'Microlensing stellar/planet',
            'Observing_mode': 'No',
            'Sky_location': 'Outside HCZ',
            't0': 2460250.35249, 't0_error': 12.5903,
            'u0': 0.03534, 'u0_error': 0.02202,
            'tE': 561.22371, 'tE_error': 345.92664,
            'piEN': 0.0, 'piEN_error': 0.0,
            'piEE': 0.0, 'piEE_error': 0.0,
            'rho': 0.0, 'rho_error': 0.0,
            's': 0.0, 's_error': 0.0,
            'q': 0.0, 'q_error': 0.0,
            'alpha': 0.0, 'alpha_error': 0.0,
            'Source_magnitude': 21.441, 'Source_mag_error': 0.95,
            'Blend_magnitude': 17.083, 'Bland_mag_error': 0.016,
            'Baseline_magnitude': 17.064, 'Baseline_mag_error': 0.029,
            'Mag_now': 17.025974731225308,
            'Mag_now_passband': 'r',
            'chi2': 442.668, 'red_chi2': 1.456,
            'KS_test': 0.0, 'SW_test': 0.0, 'AD_test': 0.0,
            'Latest_data_HJD': 2460381.71751,
            'Latest_data_UTC': datetime.strptime('2024-03-12 05:13:12', '%Y-%m-%d %H:%M:%S'),
            'Last_fit_JD': 2460357.2341402094,
            'Gaia_Source_ID': '5932197868479814784',
            'Gmag': 14.794, 'Gmag_error': 0.950,
            'RPmag': 13.997, 'RPmag_error': 0.004,
            'BPmag': 15.386, 'BPmag_error': 0.003,
            'BP-RP': 1.389, 'BP-RP_error': 0.005,
            'Reddening(BP-RP)': 0.434,
            'Extinction_G': 0.807,
            'Distance': 1633.447,
            'Teff': 5273.100,
            'logg': 3.571,
            '[Fe/H]': -0.461,
            'RUWE': 0.988,
            'Fit_covariance': '[[158.51576993236475, 0.16372556481462214, -3388.3607590059523, 2261.3296123477203, -2227.6127022007736, 244.02706784265388, 580.3463381396842], [0.1637255648188461, 0.00048501511377786424, -7.239103340213104, 4.29417346129722, -3.9776575909984615, 0.8190087230185701, 0.3767950063501391], [-3388.3607590577244, -7.239103340176121, 119665.23755300675, -72479.7371796398, 67520.33407888561, -12315.121823446232, -9827.661978948556], [2261.3296123745995, 4.294173461264639, -72479.73717947576, 44789.39465333189, -42390.148884754446, 7121.305330631102, 6917.413322829993], [-2227.6127022235464, -3.9776575909625453, 67520.3340786448, -42390.14888470157, 41126.37034912327, -6445.933227498593, -6974.959644178107], [244.02706784633108, 0.8190087230160944, -12315.121823448651, 7121.305330643988, -6445.933227516768, 60115.57018104401, -325475.47981646954], [580.3463381597052, 0.37679500635393676, -9827.661979167286, 6917.41332300709, -6974.959644367404, -325475.4798164549, 1814011.1049841202]]',
            'TAP_priority': 5.74586, 'TAP_priority_error': 3.66766,
            'TAP_priority_longtE': 74.82983, 'TAP_priority_longtE_error': 46.12355,
            'Interferometry_mode': 'Dual Field Wide',
            'Interferometry_guide_star': 1.0,
            'Interferometry_candidate': 'True',
            'Spectras': 0.0,
            'Last_fit': 2460357.2341402094,
            'Mag_peak_J': 9.420, 'Mag_peak_J_error': 0.950,
            'Mag_peak_H': 8.802, 'Mag_peak_H_error': 0.950,
            'Mag_peak_K': 8.653, 'Mag_peak_K_error': 0.950,
            'Mag_base_J': 13.063, 'Mag_base_H': 12.445, 'Mag_base_K': 12.295,
            'Interferometry_interval': 0.0,
            'YSO': 'False', 'QSO': 'False', 'galaxy': 'False',
            'TNS_name': 'None', 'TNS_class': 'None'
        }
        self.primary_target.save(extras = self.primary_extras)

        tmatch1 = SiderealTargetFactory.create()
        tmatch1.name = 'Gaia24amk'
        tmatch1.ra = 244.6058
        tmatch1.dec = -54.0787
        tmatch1_extras = copy.deepcopy(self.primary_extras)
        tmatch1_extras['Alive'] = 'False'
        tmatch1_extras['Classification'] = 'Microlensing binary'
        tmatch1_extras['Category'] = 'Microlensing stellar/planet'
        tmatch1_extras['Observing_mode'] = 'priority_stellar_event'
        tmatch1.save(extras = tmatch1_extras)

        tmatch2 = SiderealTargetFactory.create()
        tmatch2.name = 'MOA-2024-BLG-023'
        tmatch2.ra = 244.6058
        tmatch2.dec = -54.0789
        tmatch2_extras = copy.deepcopy(self.primary_extras)
        tmatch2_extras['Alive'] = 'True'
        tmatch2_extras['Classification'] = 'Unclassified poor fit'
        tmatch2_extras['Category'] = 'RR Lyrae'
        tmatch2_extras['QSO'] = 'True'
        tmatch2.save(extras = tmatch2_extras)

        self.matching_targets = [ tmatch1, tmatch2 ]
        self.matching_extras = [ tmatch1_extras, tmatch2_extras ]

        self.matched_params = {}
        for key in self.primary_extras.keys():
            self.matched_params[key] = [ tmatch1_extras[key], tmatch2_extras[key] ]

        self.update_params = copy.deepcopy(self.primary_extras)
        self.update_params['Alive'] = 'True'
        self.update_params['Classification'] = 'Microlensing binary'
        self.update_params['Category'] = 'Microlensing stellar/planet'
        self.update_params['Observing_mode'] = 'priority_stellar_event'
        self.update_params['QSO'] = 'True'

    def test_merge_boolean_value(self):
        # Parameter and expected results
        param_list = {'Alive': 'True',
                      'Interferometry_candidate': 'True',
                      'YSO': 'False',
                      'QSO': 'True',
                      'galaxy': 'False'}
        for param, result in param_list.items():
            merged_value = merge_utils.merge_boolean_value(
                self.primary_extras[param],
                self.matched_params[param]
            )
            assert(merged_value == result)

    def test_merge_obs_mode(self):

        # Case 1: matched target's mode overrides primary target's mode
        primary_param = 'No'
        matched_params = ['None', 'regular_long_event']
        result = merge_utils.merge_obs_mode(primary_param, matched_params)
        assert(result == 'regular_long_event')

        # Case 2: primary target's mode is higher priority than matched target's mode
        primary_param = 'priority_stellar_event'
        matched_params = ['None', 'priority_long_event']
        result = merge_utils.merge_obs_mode(primary_param, matched_params)
        assert(result == 'priority_stellar_event')

        # Case 3: matched target's mode is not None and higher priority than primary target
        primary_param = 'regular_long_event'
        matched_params = ['priority_stellar_event', 'priority_long_event']
        result = merge_utils.merge_obs_mode(primary_param, matched_params)
        assert(result == 'priority_stellar_event')

    def test_merge_classification(self):

        # Case 1: primary target's classification overrides matched target classifications
        primary_value = 'Microlensing binary'
        matching_values = ['Microlensing PSPL', 'Variable star']
        result = merge_utils.merge_classification(primary_value, matching_values)
        assert(result == 'Microlensing binary')

        # Case 2: primary target is unclassified, overriden by matched target class
        primary_value = 'Unclassified poor fit'
        matching_values = ['Microlensing PSPL', 'Variable star']
        result = merge_utils.merge_classification(primary_value, matching_values)
        assert(result == 'Microlensing PSPL')

        # Case 3: User-entered classifications
        primary_value = 'Unclassified poor fit'
        matching_values = ['Microlensing PSPL', 'Known Galaxy']
        result = merge_utils.merge_classification(primary_value, matching_values)
        assert(result == 'Microlensing PSPL')

        # Case 4: Unknown classification should return the correct default
        primary_value = 'None'
        matching_values = ['None', 'None']
        result = merge_utils.merge_classification(primary_value, matching_values)
        assert(result == 'Microlensing PSPL')


    def test_merge_category(self):

        # Case 1: primary target's category overrides those of the matched targets
        primary_value = 'Microlensing stellar/planet'
        matching_values = ['Stellar activity', 'Unclassified']
        result = merge_utils.merge_category(primary_value, matching_values)
        assert(result == 'Microlensing stellar/planet')

        # Case 2: matched target's category overrides the primary target's category
        primary_value = 'Unclassified'
        matching_values = ['Stellar activity', 'Unclassified']
        result = merge_utils.merge_category(primary_value, matching_values)
        assert(result == 'Stellar activity')

        # Case 3: matched target's category also includes microlensing
        primary_value = 'Microlensing stellar/planet'
        matching_values = ['Stellar activity', 'Microlensing long-tE']
        result = merge_utils.merge_category(primary_value, matching_values)
        assert(result == 'Microlensing stellar/planet')

        # Case 4: No known category, return sensible default
        primary_value = 'None'
        matching_values = ['None', 'None']
        result = merge_utils.merge_category(primary_value, matching_values)
        assert(result == 'Microlensing stellar/planet')

    def test_merge_extra_params(self):
        # The inputs to this function need to be QuerySets rather than dictionaries
        primary_extras = TargetExtra.objects.prefetch_related('target').filter(
            target=self.primary_target
        )
        matching_extras = [TargetExtra.objects.prefetch_related('target').filter(
            target=t
        ) for t in self.matching_targets]
        result = merge_utils.merge_extra_params(primary_extras, matching_extras)

        for key, value in self.update_params.items():
            assert(str(result[key]) == str(value))