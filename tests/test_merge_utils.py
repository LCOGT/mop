from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
from datetime import datetime, timedelta
from tom_targets.models import Target, TargetExtra, TargetName, TargetList
from tom_dataproducts.models import DataProduct, ReducedDatum, DataProductGroup
from tom_observations.models import ObservationRecord, ObservationGroup
from django_comments.models import Comment
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from mop.management.commands import merge_utils
import copy
import numpy as np
import json

class TestMergeExtraParams(TestCase):
    """
    Class describing tests of the functions to merge the extra parameters associated with
    duplicated Targets.
    """

    def setUp(self):

        u1 = User.objects.create(
            username = 'test1',
            first_name='Test',
            last_name='User1',
            email='test@lco.global'
        )

        self.primary_target = SiderealTargetFactory.create()
        self.primary_target.name = 'OGLE-2023-GD-0011'
        self.primary_target.ra = 244.6058
        self.primary_target.dec = -54.0788
        self.primary_target.save()
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

        current_site = Site.objects.get_current()
        c1 = Comment.objects.create(
            content_object = self.primary_target,
            user = u1,
            site = current_site,
            comment = 'Test comment for primary target'
        )
        self.primary_comments = [c1]

        self.targetlist1 = TargetList.objects.create(
            name = 'TESTGROUP1'
        )
        self.targetlist2 = TargetList.objects.create(
            name = 'TESTGROUP2'
        )
        self.targetlist1.targets.add(self.primary_target)

        datagroup = DataProductGroup.objects.create(
            name = 'TEST'
        )
        datagroup.save()

        usergroup = Group.objects.create(
            name = 'TEST'
        )

        obs1 = ObservationRecord.objects.create(
            target=self.primary_target,
            user = u1,
            facility = 'OGLE',
            parameters = {'tel': 'tel1', 'site': 'test_site'},
            observation_id = 'TEST012345',
            status = 'PENDING',
            scheduled_start = datetime.utcnow(),
            scheduled_end = datetime.utcnow() + timedelta(days=1)
        )

        obs2 = ObservationRecord.objects.create(
            target=self.primary_target,
            user = u1,
            facility = 'MOA',
            parameters = {'tel': 'tel_moa', 'site': 'NZ'},
            observation_id = 'TEST012345_moa',
            status = 'PENDING',
            scheduled_start = datetime.utcnow(),
            scheduled_end = datetime.utcnow() + timedelta(days=1)
        )

        obsgroup1 = ObservationGroup.objects.create(
            name= 'primary_target_obs1'
        )
        obsgroup1.observation_records.add(obs1)
        obsgroup1.save()

        obsgroup2 = ObservationGroup.objects.create(
            name= 'primary_target_moa',
        )
        obsgroup2.observation_records.add(obs2)
        obsgroup2.save()

        self.primary_observations = {
            'records': [ obs1, obs2 ],
            'groups': [ obsgroup1, obsgroup2 ]
            }

        dp1 = DataProduct.objects.create(
            target=self.primary_target,
            observation_record = obs1,
            data = 'path/to/dataproduct',
            data_product_type = 'photometry'
        )

        rd1 = ReducedDatum.objects.create(
            target=self.primary_target,
            data_product = dp1,
            source_name = 'OGLE',
            data_type = 'photometry',
            timestamp = datetime.utcnow(),
            value = {'datum': 1, 'filter': 'I'}
        )
        self.primary_target_data = [rd1]

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

        self.targetlist2.targets.add(tmatch1)

        c2 = Comment.objects.create(
            content_object = tmatch1,
            user = u1,
            site = current_site,
            comment = 'This is the first matching target'
        )
        self.matched_comments = [c2]

        obs3 = ObservationRecord.objects.create(
            target=tmatch1,
            user = u1,
            facility = 'LCO',
            parameters = {'tel': 'tel2', 'site': 'test_site2'},
            observation_id = 'TEST012345',
            status = 'PENDING',
            scheduled_start = datetime.utcnow(),
            scheduled_end = datetime.utcnow() + timedelta(days=1)
        )

        obsgroup3 = ObservationGroup.objects.create(
            name= 'match_target1_obs3',
        )
        obsgroup3.observation_records.add(obs3)
        obsgroup3.save()

        dp2 = DataProduct.objects.create(
            target=tmatch1,
            observation_record = obs3,
            data = 'path/to/dataproduct2',
            data_product_type = 'photometry'
        )

        rd2 = ReducedDatum.objects.create(
            target=tmatch1,
            data_product = dp2,
            source_name = 'OMEGA',
            data_type = 'photometry',
            timestamp = datetime.utcnow()+timedelta(seconds=5),
            value = {'datum': 2, 'filter': 'ip'}
        )

        obs4 = ObservationRecord.objects.create(
            target=tmatch1,
            user = u1,
            facility = 'LCO',
            parameters = {'tel': 'tel3', 'site': 'test_site2'},
            observation_id = 'TEST012345',
            status = 'PENDING',
            scheduled_start = datetime.utcnow(),
            scheduled_end = datetime.utcnow() + timedelta(days=1)
        )

        obsgroup4 = ObservationGroup.objects.create(
            name= 'match_target2_obs4'
        )
        obsgroup4.observation_records.add(obs4)
        obsgroup4.save()

        dp3 = DataProduct.objects.create(
            target=tmatch1,
            observation_record = obs4,
            data = 'path/to/dataproduct3',
            data_product_type = 'photometry'
        )

        rd3 = ReducedDatum.objects.create(
            target=tmatch1,
            data_product = dp3,
            source_name = 'OMEGA',
            data_type = 'photometry',
            timestamp = datetime.utcnow()+timedelta(seconds=5),
            value = {'datum': 2, 'filter': 'gp'}
        )
        self.matching_data = [rd2, rd3]
        self.matching_observations = {
            'groups': [obsgroup3, obsgroup4],
            'records': [obs3, obs4]
        }

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

        self.targetlist2.targets.add(tmatch2)

        c3 = Comment.objects.create(
            content_object = tmatch2,
            user = u1,
            site = current_site,
            comment = 'This is the second matching target'
        )
        self.matched_comments = [c3]

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

        # Case 4: Unknown classification should return the correct default
        primary_value = None
        matching_values = [None]
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
        #primary_extras = TargetExtra.objects.prefetch_related('target').filter(
        #    target=self.primary_target
        #)
        #matching_extras = [TargetExtra.objects.prefetch_related('target').filter(
        #    target=t
        #) for t in self.matching_targets]

        primary_target = self.primary_target
        primary_extras = {
            'alive': 'True',
            'classification': 'Microlensing PSPL',
            'category': 'Microlensing stellar/planet',
            'observing_mode': 'No',
            'sky_location': 'Outside HCZ',
            't0': 2460250.35249, 't0_error': 12.5903,
            'u0': 0.03534, 'u0_error': 0.02202,
            'tE': 561.22371, 'tE_error': 345.92664,
            'piEN': 0.0, 'piEN_error': 0.0,
            'piEE': 0.0, 'piEE_error': 0.0,
            'rho': 0.0, 'rho_error': 0.0,
            's': 0.0, 's_error': 0.0,
            'q': 0.0, 'q_error': 0.0,
            'alpha': 0.0, 'alpha_error': 0.0,
            'source_magnitude': 21.441, 'source_mag_error': 0.95,
            'blend_magnitude': 17.083, 'blend_mag_error': 0.016,
            'baseline_magnitude': 17.064, 'baseline_mag_error': 0.029,
            'mag_now': 17.025974731225308,
            'mag_now_passband': 'r',
            'chi2': 442.668, 'red_chi2': 1.456,
            'ks_test': 0.0, 'sw_test': 0.0, 'ad_test': 0.0,
            'latest_data_hjd': 2460381.71751,
            'latest_data_utc': datetime.strptime('2024-03-12 05:13:12', '%Y-%m-%d %H:%M:%S'),
            'last_fit': 2460357.2341402094,
            'gaia_source_id': '5932197868479814784',
            'gmag': 14.794, 'gmag_error': 0.950,
            'rpmag': 13.997, 'rpmag_error': 0.004,
            'bpmag': 15.386, 'bpmag_error': 0.003,
            'bprp': 1.389, 'bprp_error': 0.005,
            'reddening_bprp': 0.434,
            'extinction_g': 0.807,
            'distance': 1633.447,
            'teff': 5273.100,
            'logg': 3.571,
            'metallicity': -0.461,
            'ruwe': 0.988,
            'fit_covariance': np.array([[158.51576993236475, 0.16372556481462214, -3388.3607590059523, 2261.3296123477203, -2227.6127022007736, 244.02706784265388, 580.3463381396842], [0.1637255648188461, 0.00048501511377786424, -7.239103340213104, 4.29417346129722, -3.9776575909984615, 0.8190087230185701, 0.3767950063501391], [-3388.3607590577244, -7.239103340176121, 119665.23755300675, -72479.7371796398, 67520.33407888561, -12315.121823446232, -9827.661978948556], [2261.3296123745995, 4.294173461264639, -72479.73717947576, 44789.39465333189, -42390.148884754446, 7121.305330631102, 6917.413322829993], [-2227.6127022235464, -3.9776575909625453, 67520.3340786448, -42390.14888470157, 41126.37034912327, -6445.933227498593, -6974.959644178107], [244.02706784633108, 0.8190087230160944, -12315.121823448651, 7121.305330643988, -6445.933227516768, 60115.57018104401, -325475.47981646954], [580.3463381597052, 0.37679500635393676, -9827.661979167286, 6917.41332300709, -6974.959644367404, -325475.4798164549, 1814011.1049841202]]),
            'tap_priority': 5.74586, 'tap_priority_error': 3.66766,
            'tap_priority_longte': 74.82983, 'tap_priority_longte_error': 46.12355,
            'interferometry_mode': 'Dual Field Wide',
            'interferometry_guide_star': 1.0,
            'interferometry_candidate': 'True',
            'spectras': 0.0,
            'mag_peak_J': 9.420, 'mag_peak_J_error': 0.950,
            'mag_peak_H': 8.802, 'mag_peak_H_error': 0.950,
            'mag_peak_K': 8.653, 'mag_peak_K_error': 0.950,
            'mag_base_J': 13.063, 'mag_base_H': 12.445, 'mag_base_K': 12.295,
            'interferometry_interval': 0.0,
            'YSO': 'False', 'QSO': 'False', 'galaxy': 'False',
            'TNS_name': 'None', 'TNS_class': 'None'
        }
        primary_target.store_parameter_set(primary_extras)

        tmatch1 = self.matching_targets[0]
        tmatch1_extras = copy.deepcopy(primary_extras)
        tmatch1_extras['alive'] = 'True'
        tmatch1_extras['classification'] = 'Unclassified poor fit'
        tmatch1_extras['category'] = 'RR Lyrae'
        tmatch1_extras['QSO'] = 'True'
        tmatch1.store_parameter_set(tmatch1_extras)

        tmatch2 = self.matching_targets[1]
        tmatch2_extras = copy.deepcopy(primary_extras)
        tmatch2_extras['alive'] = 'False'
        tmatch2_extras['classification'] = 'Unclassified poor fit'
        tmatch2_extras['category'] = 'Pulsator'
        tmatch2_extras['QSO'] = 'False'
        tmatch2.store_parameter_set(tmatch2_extras)

        matching_targets = [tmatch1, tmatch2]

        result = merge_utils.merge_extra_params(primary_target, matching_targets)

        expected_result = tmatch1_extras = copy.deepcopy(primary_extras)
        expected_result['category'] = 'Microlensing stellar/planet'
        expected_result['QSO'] = 'True'

        for key, value in expected_result.items():
            if key != 'fit_covariance':
                assert(str(result[key]) == str(value))
            else:
                data = json.loads(result[key])
                data = np.array(data)
                np.testing.assert_allclose(data, value, rtol=1e-2)

    def test_merge_names(self):
        aliases = TargetName.objects.filter(target=self.primary_target)

        merge_utils.merge_names(self.primary_target, self.matching_targets)

        aliases = TargetName.objects.filter(target=self.primary_target)

        name_set = [x.name for x in aliases]

        for t in self.matching_targets:
            assert(t.name in name_set)

        # Test special case of nearby targets which are close to the boundary of the typical 2" search radius
        t1 = SiderealTargetFactory.create()
        t1.name = 'MOA-2023-BLG-119'
        t1.ra = 270.77190417
        t1.dec = -29.73846667
        t2 = SiderealTargetFactory.create()
        t2.name = 'MOA-2023-BLG-123'
        t2.ra = 270.77113333
        t2.dec = -29.73841111
        t3 = SiderealTargetFactory.create()
        t3.name = 'OGLE-2023-BLG-0363'
        t3.ra = 270.771375
        t3.dec = -29.73827778

        # t3 is already an alias of t2:
        tn = TargetName.objects.create(target=t2, name=t3.name)

        merge_utils.merge_names(t1, [t2, t3])

        aliases = TargetName.objects.filter(target=t1)
        name_set = [x.name for x in aliases]
        for t in [t2, t3]:
            assert(t.name in name_set)

    def test_merge_data_products(self):

        # Call function to transfer ownership of the data products of the matched targets to
        # the primary target
        primary_data = ReducedDatum.objects.filter(target=self.primary_target)
        matched_data = [ReducedDatum.objects.filter(target=x) for x in self.matching_targets]

        merge_utils.merge_data_products(self.primary_target,
                            primary_data,
                            self.matching_targets,
                            matched_data)

        # Query the DB to retrieve all data now associated with the primary target
        updated_data = ReducedDatum.objects.filter(
            target=self.primary_target
        )

        # Check that the resulting list of data matches the test data
        # provided for both the primary and matching targets
        expected_data = self.primary_target_data + self.matching_data

        assert(len(updated_data) == len(expected_data))
        for rd in updated_data:
            assert(rd in expected_data)

    def test_merge_targetgroups(self):
        """
        Method to test the merging of TargetLists.
        If matching targets are assigned to a TargetGroup that the primary target is NOT already
        a member of, then the primary target should be added to that Target Group.
        """

        targetlists = TargetList.objects.all()

        merge_utils.merge_targetgroups(targetlists, self.primary_target, self.matching_targets)

        # The primary target was assigned to target list 1, but the other matching targets
        # were assigned to target list 2.  So this function should have added the primary target
        # to target list 2.
        test_lists = TargetList.objects.filter(targets__in=[self.primary_target.pk])
        assert(self.targetlist1 in test_lists)
        assert(self.targetlist2 in test_lists)

    def test_merge_comments(self):

        # Retrieve the comments for all matching targets and transfer ownership of them to the primary target
        matching_comments = [Comment.objects.filter(object_pk=x.pk) for x in self.matching_targets]

        merge_utils.merge_comments(matching_comments, self.primary_target)

        # Retrieve all comments associated with the primary target and check this now includes all the
        # comments for the matching targets
        results = Comment.objects.filter(object_pk=self.primary_target.pk)
        for c in self.matched_comments:
            assert(c in results)

    def test_merge_observations(self):

        # Test that the function works for observation records
        obs_records = [ObservationRecord.objects.filter(target=t) for t in self.matching_targets]

        merge_utils.merge_observations(obs_records, self.primary_target)

        test_obs_records = ObservationRecord.objects.filter(target=self.primary_target)

        expected_obsrecords = self.primary_observations['records'] + self.matching_observations['records']

        assert(len(test_obs_records) == len(expected_obsrecords))
        for entry in test_obs_records:
            assert(entry in expected_obsrecords)
            assert(entry.target == self.primary_target)

    def test_sanity_check_data_sources(self):

        # This should not raise any errors
        datums_qs = ReducedDatum.objects.filter(target=self.primary_target)

        merge_utils.sanity_check_data_sources(self.primary_target, datums_qs)

        # This should raise an OSError:
        dp1 = DataProduct.objects.create(
            target=self.primary_target,
            observation_record=self.primary_observations['records'][0],
            data='path/to/dataproduct',
            data_product_type='photometry'
        )
        rd1 = ReducedDatum.objects.create(
            target=self.primary_target,
            data_product=dp1,
            source_name='UNKNOWN',
            data_type='photometry',
            timestamp=datetime.utcnow(),
            value={'datum': 1, 'filter': 'I'}
        )
        datums_qs = ReducedDatum.objects.filter(target=self.primary_target)

        with self.assertRaises(OSError):
            merge_utils.sanity_check_data_sources(self.primary_target, datums_qs)
