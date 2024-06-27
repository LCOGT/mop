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
                'event_set': {
                    'OGLE-2023-BLG-0363': (270.771375, -29.73827777777778),
                    'OGLE-2023-BLG-0363': (270.771375, -29.73827777777778),
                    'OGLE-2023-BLG-0455': (270.77, -29.737),
                },
                'unique_events': [
                    'OGLE-2023-BLG-0363',
                    'OGLE-2023-BLG-0455'
                ]
            }
        }

    def test_fetch_alerts(self):
        broker = moa.MOABroker()
        new_targets = []

        for name,coords in self.params['duplicate_events']['event_set'].items():
            target, result = broker.ingest_event(name, coords[0], coords[1])

            if 'new_target' in result:
                new_targets.append(target.name)

        assert (len(new_targets) == len(self.params['duplicate_events']['unique_events']))

        for t in new_targets:
            assert (t.name in self.params['duplicate_events']['unique_events'])
