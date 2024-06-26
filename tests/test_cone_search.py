from django.test import TestCase
from tom_targets.models import Target
from tom_targets.tests.factories import SiderealTargetFactory
from django.core.exceptions import ValidationError
from django.conf import settings

class TestMergeExtraParams(TestCase):
    """
    Class describing tests of the functions to merge the extra parameters associated with
    duplicated Targets.
    """

    def setUp(self):
        self.target_coordinates = [
            [244.60583333333332, -54.078833333333336, 'OGLE-2023-GD-0011'],
            [276.2508, -21.0287, 'OGLE-2024-BLG-0002'],
            [260.3587, -29.4469, 'OGLE-2024-BLG-0280'],
            [268.5057, -28.44886, 'OGLE-2023-BLG-0002'],
            [268.5057083333333, -28.44886111111111, 'OGLE-2023-BLG-0002']
        ]
        self.radius = 2.0   # Arseconds

        for target in self.target_coordinates:
            t = SiderealTargetFactory.create()
            t.ra = target[0]
            t.dec = target[1]
            t.save()

        # Input for duplicate targets test
        t1 = SiderealTargetFactory.create()
        t1.name = 'OGLE-2023-BLG-0363'
        t1.ra = 270.771375
        t1.dec = -29.73827777777778
        t2 = SiderealTargetFactory.create()
        t2.name = 'MOA-2023-BLG-123'
        t2.ra = 270.771375
        t2.dec = -29.73827777777778
        self.duplicates = [t1, t2]

    def test_match_cone_search(self):
        for target in self.target_coordinates:
            print('Searching on target coordinates for ' + target[2] + ' ' + str(target[0]) + ' ' + str(target[1]))
            nearby_targets = Target.matches.match_cone_search(
                target[0],
                target[1],
                self.radius)

            assert(len(nearby_targets) > 0)

    def test_match_duplicates(self):
        print(settings)
        t1 = self.duplicates[0]
        t1.save()
        t2 = self.duplicates[1]
        with self.assertRaises(ValidationError):
            t2.save()
