from django.test import TestCase
from tom_targets.models import Target,TargetExtra
from unittest import skip
from tom_targets.tests.factories import SiderealTargetFactory
from mop.brokers import gaia
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.utils.commons import TableList
from astropy.coordinates import Angle

@skip("")
class TestGaia(TestCase):
    def setUp(self):
        self.st1 = SiderealTargetFactory.create()
        self.st1.name = 'Gaia23aiy'
        self.st1.ra = 241.2805
        self.st1.dec = -56.4367
        self.st2, created = Target.objects.get_or_create(name='TEST2',
                                                         ra=240.5,
                                                         dec=-35.0,
                                                         type='SIDEREAL',
                                                         epoch=2000)
        print('ST2: ',self.st2)
        print('ST2 extras: ',self.st2.extra_fields)
        self.params = {'target1': self.st1,
                       'target2': self.st2,
                       'radius': Angle(0.004, "deg")}

    def test_query_gaia_dr3(self):
        results = gaia.query_gaia_dr3(self.params['target'], radius=self.params['radius'])
        assert(type(results) == type(TableList([])))
        assert(len(results) > 0)
        print(results)
        for star in results:
            print(star.columns)

    @skip("")
    def test_fetch_gaia_dr3_entry(self):
        target = self.params['target']

        target = gaia.fetch_gaia_photometry(target)
        updated_target = Target.objects.all()[0]
        print(updated_target.extra_fields)
        print('TARGET: ',target.extra_fields)

        expected_minimum_fields = ['Gmag',
                           'RPmag',
                           'BPmag',
                           'BP-RP']

        for field in expected_minimum_fields:
            print('EXPECT field: ',field, target.extra_fields.keys())
            assert(field in target.extra_fields.keys())
            assert(target.extra_fields[field])
