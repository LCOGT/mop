from django.test import TestCase
from tom_targets.models import Target
from tom_targets.tests.factories import SiderealTargetFactory
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.conf import settings
from microlensing_targets.match_managers import validators
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
        # Note we don't test for duplicated names here because this
        # raises a lower-level IntegrityError from the keyword match
        self.duplicates = [
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('MOA-2023-BLG-123', 270.771375, -29.73827777777778),
             False),
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('Gaia24bnb', 347.02747, 3.18862),
             True),
        ]

        self.duplicate_names = [
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             False),
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('Gaia24bnb', 347.02747, 3.18862),
             True),
        ]

        self.duplicate_positions = [
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('MOA-2023-BLG-123', 270.771375, -29.73827777777778),
             False),
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('Gaia24bnb', 347.02747, 3.18862),
             True),
        ]

        self.test_event_create = [
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             'existing_target_exact_name'),
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('MOA-2023-BLG-123', 270.771375, -29.73827777777778),
             'existing_target_new_alias'),
            (('OGLE-2023-BLG-0363', 270.771375, -29.73827777777778),
             ('Gaia24bnb', 347.02747, 3.18862),
             'new_target'),
        ]
    def test_match_cone_search(self):
        for target in self.target_coordinates:
            print('Searching on target coordinates for ' + target[2] + ' ' + str(target[0]) + ' ' + str(target[1]))
            nearby_targets = Target.matches.match_cone_search(
                target[0],
                target[1],
                self.radius)

            assert(len(nearby_targets) > 0)

    def test_match_duplicates(self):
        """Test to ensure that we cannot create two targets at the same sky position
        with different names without raising an error.

        Note that this test doesn't use the SiderealTargetFactory but rather creates the targets
        directly.  This is because generating a target and using the target.save() method
        doesn't trigger the validation step that would test for duplication.
        """

        for (target1,target2, expected_result) in self.duplicates:
            # Clear the DB of the entries from the previous test
            qs = Target.objects.filter(name=target1[0])
            if qs.count() > 0:
                qs[0].delete()

            # Set up the pre-existing target of the pair
            t1 = Target.objects.create(name=target1[0], ra=target1[1], dec=target1[2])

            # Check to see if the new target of the pair triggers the validator
            result = validators.check_target_unique(target2[0], target2[1], target2[2])

            assert(result == expected_result)

    def test_check_target_name_unique(self):
        for (target1,target2, expected_result) in self.duplicate_names:
            # Clear the DB of the entries from the previous test
            qs = Target.objects.filter(name=target1[0])
            if qs.count() > 0:
                qs[0].delete()

            # Set up the pre-existing target of the pair
            t1 = Target.objects.create(name=target1[0], ra=target1[1], dec=target1[2])

            # Check to see if the new target of the pair triggers the validator
            result = validators.check_target_name_unique(target2[0])

            assert(result == expected_result)

    def test_check_target_coordinates_unique(self):
        for (target1, target2, expected_result) in self.duplicate_positions:
            # Clear the DB of the entries from the previous test
            qs = Target.objects.filter(name=target1[0])
            if qs.count() > 0:
                qs[0].delete()

            # Set up the pre-existing target of the pair
            t1 = Target.objects.create(name=target1[0], ra=target1[1], dec=target1[2])

            # Check to see if the new target of the pair triggers the validator
            result = validators.check_target_coordinates_unique(target2[1], target2[2])

            assert (result == expected_result)

    def test_get_or_create_event(self):
        for (target1, target2, expected_result) in self.test_event_create:
            # Set up the pre-existing target of the pair
            t1 = Target.objects.create(name=target1[0], ra=target1[1], dec=target1[2])

            # Get or create the event
            t2, result = validators.get_or_create_event(target2[0], target2[1], target2[2])

            assert(type(t2) == type(t1))
            assert(expected_result == result)

            # Clear the DB of the entries from the previous test
            t1.delete()
            t2.delete()

        # Also check the case of existing target, existing alias (second test case should establish this):
        (target1, target2, expected_result) = self.test_event_create[1]
        t1 = Target.objects.create(name=target1[0], ra=target1[1], dec=target1[2])
        t2, result = validators.get_or_create_event(target2[0], target2[1], target2[2])
        assert (result == 'existing_target_new_alias')
        assert (t2 == t1)
        t3, result = validators.get_or_create_event(target2[0], target2[1], target2[2])
        assert (result == 'existing_target_existing_alias')
        assert (t3 == t1)