from django.test import TestCase
from mop.brokers import ogle
from tom_targets.tests.factories import SiderealTargetFactory
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np

class TestOgleBroker(TestCase):
    def setUp(self):
        self.params = {
                        'years': ['2022', '2023'],
                        'events': {'OGLE-2023-BLG-0001': ('17:53:44.28', '-28:40:04.6'),
                                   'OGLE-2023-BLG-0002': ('17:54:01.37', '-28:26:55.9'),
                                   'OGLE-2023-BLG-0003': ('18:00:00.3', '-27:30:00.5'),
                                   'OGLE-2023-BLG-0004': ('17:20:15.0', '-28:30:30.0')},
                        'photometry': np.array([
                                [2459795.61659, 21.078, 0.288, 5.21, 386.0],
                                [2459795.65233, 20.418, 0.179, 5.75, 401.0],
                                [2459795.68540, 20.710, 0.277, 6.47, 416.0],
                                [2459796.51954, 20.482, 0.282, 7.07, 481.0],
                                [2459796.62883, 20.621, 0.237, 5.91, 412.0],
                                [2459796.66275, 20.645, 0.223, 5.49, 420.0],
                                [2459797.53976, 20.256, 0.285, 7.47, 645.0],
                                [2459798.71855, 20.042, 0.290, 6.56, 1507.0],
                                [2459804.52573, 20.667, 0.270, 4.91, 691.0]
                        ])
        }

    def test_fetch_lens_model_parameters(self):
        broker = ogle.OGLEBroker()
        events = broker.fetch_lens_model_parameters(self.params['years'])
        assert(type(events) == type({}))
        assert(len(events) > 0)
        for key, value in events.items():
            assert(type(value) == type(()))
            assert(len(value) == 2)

    def test_ingest_ogle_events(self):
        broker = ogle.OGLEBroker()
        test_target = SiderealTargetFactory.create()
        (target_list, new_targets) = broker.ingest_events(self.params['events'])
        assert(type(target_list) == type([]))
        for target in target_list:
            assert(type(target) == type(test_target))

    def test_read_ogle_lightcurve(self):
        test_target = self.generate_test_target()

        broker = ogle.OGLEBroker()
        photometry = broker.read_ogle_lightcurve(test_target)
        assert(type(photometry) == type(np.array([])))

    def test_ingest_ogle_photometry(self):
        test_target = self.generate_test_target()

        broker = ogle.OGLEBroker()
        status = broker.ingest_ogle_photometry(test_target, self.params['photometry'])
        assert(status == 'OK')

        assert(test_target.latest_data_hjd > 0.0)
        assert(test_target.latest_data_utc != None)

    def generate_test_target(self, target_name=None):

        test_target = SiderealTargetFactory.create()
        if not target_name:
            target_name = 'OGLE-2023-BLG-0001'
        s = SkyCoord(self.params['events'][target_name][0], self.params['events'][target_name][1],
                     unit=(u.hourangle, u.deg), frame='icrs')
        test_target.name = target_name
        test_target.ra = s.ra.deg
        test_target.dec = s.dec.deg

        return test_target

    def test_sort_targets(self):
        list_of_targets = []
        for target_name,coords in self.params['events'].items():
            t = self.generate_test_target(target_name=target_name)
            list_of_targets.append(t)

        broker = ogle.OGLEBroker()
        ordered_list_of_targets = broker.sort_target_list(list_of_targets)
        assert(ordered_list_of_targets[0].name == list_of_targets[-1].name)
        assert(len(ordered_list_of_targets) == len(list_of_targets))

    def test_random_selection_targets(self):
        list_of_targets = []
        new_targets = []
        for target_name, coords in self.params['events'].items():
            t = self.generate_test_target(target_name=target_name)
            list_of_targets.append(t)
            new_targets.append(t)
        ntargets = min(100, len(list_of_targets))

        broker = ogle.OGLEBroker()
        selected_targets = broker.select_random_targets(list_of_targets, new_targets, ntargets=ntargets)
        assert(len(selected_targets) == ntargets)
