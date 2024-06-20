from django.test import TestCase
from tom_targets.models import Target
from tom_targets.tests.factories import SiderealTargetFactory

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

    def test_match_cone_search(self):
        for target in self.target_coordinates:
            print('Searching on target coordinates for ' + target[2] + ' ' + str(target[0]) + ' ' + str(target[1]))
            nearby_targets = Target.matches.match_cone_search(
                target[0],
                target[1],
                self.radius)

            assert(len(nearby_targets) > 0)