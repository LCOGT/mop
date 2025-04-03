from django.test import TestCase
from mop.brokers import moa
from tom_targets.tests.factories import SiderealTargetFactory
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np

class TestMoaBroker(TestCase):
    def setUp(self):
        self.params = {
            'duplicate_events': {
                'event_set': [
                    ('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778, 'new_target'),
                    ('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778, 'existing_target_exact_name'),
                    ('OGLE-2023-BLG-0455', 270.77, -29.737, 'new_target'),
                    ('Gaia24amp', 260.43202, -28.84063, 'new_target'),
                    ('OGLE-2024-BLG-0014', 260.43202, -28.84063, 'existing_target_new_alias')
                ],
                'unique_events': [
                    'OGLE-2023-BLG-0363',
                    'OGLE-2023-BLG-0455',
                    'Gaia24amp'
                ],
            },
            'moa_url_2024': 'https://www.massey.ac.nz/~iabond/moa/alert2024/index.dat',
            'moa_url_2025': 'https://moaprime.massey.ac.nz/alerts/index/moa/2025'
        }

    def test_fetch_alerts(self):
        broker = moa.MOABroker()
        new_targets = []

        for params in self.params['duplicate_events']['event_set']:
            target, result = broker.ingest_event(params[0], params[1], params[2])
            assert(result == params[3])
            if 'new_target' in result:
                new_targets.append(target)

        print('New targets: ', new_targets)
        assert (len(new_targets) == len(self.params['duplicate_events']['unique_events']))

        for t in new_targets:
            assert (t.name in self.params['duplicate_events']['unique_events'])

    def test_fetch_event_list_pre2025(self):

        broker = moa.MOABroker()
        events = broker.fetch_event_list_pre2025(self.params['moa_url_2024'])

        test_event = 'MOA-2024-BLG-001'
        assert(type(events) == type({}))
        assert(len(events) > 0)
        assert('RA' in events[test_event].keys())
        assert('Dec' in events[test_event].keys())
        assert('MOA_params' in events[test_event].keys())