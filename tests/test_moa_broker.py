from django.test import TestCase
from mop.brokers import moa
from tom_targets.tests.factories import SiderealTargetFactory
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np
from os import path, getcwd

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
            'moa_url_2024': path.join(getcwd(), 'tests', 'data', 'MOA_alerts_index_2024.dat'),
            'moa_url_2025': path.join(getcwd(), 'tests', 'data', 'MOA_alerts_index_2025.html'),
            'events': {
                'MOA-2025-BLG-0001': {
                    'RA': 266.64634167, 'Dec': -3428699169,
                    'moa_params': ['MOA-2025-BLG-0001', 30268.15, 18.38]
                    }
            }
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

    def test_parse_event_list_pre2025(self):

        # Load test URL content
        with open(self.params['moa_url_2024'], 'r') as f:
            content = f.read()

        broker = moa.MOABroker()
        events = broker.parse_event_list_pre2025(content)

        test_event = 'MOA-2024-BLG-001'
        assert(type(events) == type({}))
        assert(len(events) > 0)
        assert('RA' in events[test_event].keys())
        assert('Dec' in events[test_event].keys())
        assert('MOA_params' in events[test_event].keys())

    def test_parse_event_list_2025(self):

        # Load test data
        with open(self.params['moa_url_2025'], 'r') as f:
            content = f.read()

        broker = moa.MOABroker()
        events = broker.parse_event_list_2025(content)

        test_event = 'MOA-2025-BLG-0001'
        assert(type(events) == type({}))
        assert(len(events) > 0)
        assert('RA' in events[test_event].keys())
        assert('Dec' in events[test_event].keys())

    def test_parse_event_pages_2025(self):
        broker = moa.MOABroker()

        events = broker.parse_event_pages_2025(self.params['events'])

        print(events)