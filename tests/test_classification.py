from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target
from mop.toolbox import classifier_tools
from mop.management.commands import gaia_classifier

from mop.brokers import gaia as gaia_mop

from os import getcwd, path
import numpy as np
from astropy.time import Time, TimezoneInfo
from astropy.coordinates import SkyCoord
from astropy import units as u

class TestClassMicrolens(TestCase):
    """
    Class describing unittests for the target planet priority functions
    """
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        st1.name = 'Gaia23cnu'
        st1.ra = 284.1060
        st1.dec = -18.0808
        cwd = getcwd()
        lightcurve_file = path.join(cwd, 'tests/data/Gaia23cnu.csv')
        photometry = generate_test_ReducedDatums(st1, lightcurve_file, 'G')

        st1.t0 = 2460217.09
        st1.u0 = 0.34
        st1.te = 126.4
        st1.source_magnitude = 16.92
        st1.blend_magnitude = 16.50
        st1.baseline_magnitude = 15.94
        st1.chi2 = 6135.256
        st1.red_chi2 = 6.35
        st1.save()

        st1.datasets = photometry
        
        self.params = {
            'target': st1,
            't': 2460237.0,
            'lightcurve_file': lightcurve_file,
            'photometry': photometry,
            'Latest_data_HJD': 2460207.09
        }

    def test_check_YSO(self):
        coord = SkyCoord(ra=self.params['target'].ra, dec=self.params['target'].dec, unit=(u.degree, u.degree), frame='icrs')
        is_YSO = classifier_tools.check_YSO(coord)
        assert (type(is_YSO) == type(True))
        self.assertEqual(is_YSO, False)

    def test_check_QSO(self):
        coord = SkyCoord(ra=self.params['target'].ra, dec=self.params['target'].dec, unit=(u.degree, u.degree), frame='icrs')
        is_QSO = classifier_tools.check_QSO(coord)
        assert (type(is_QSO) == type(True))
        self.assertEqual(is_QSO, False)

    def test_check_galaxy(self):
        coord = SkyCoord(ra=self.params['target'].ra, dec=self.params['target'].dec, unit=(u.degree, u.degree), frame='icrs')
        is_galaxy = classifier_tools.check_galaxy(coord)
        assert (type(is_galaxy) == type(True))
        self.assertEqual(is_galaxy, False)

    def test_valid_blend(self):
        valid_blend = classifier_tools.check_valid_blend(self.params['target'])

        assert (type(valid_blend) == type(True))
        self.assertEqual(valid_blend, True)

    def test_valid_u0(self):
        target = self.params['target']
        valid_u0 = classifier_tools.check_valid_u0(target.u0)

        assert (type(valid_u0) == type(True))
        self.assertEqual(valid_u0, True)

    def test_valid_dmag(self):
        target = self.params['target']
        #photometry = gaia_classifier.retrieve_target_photometry(target)
        valid_dmag = classifier_tools.check_valid_dmag(target)

        assert (type(valid_dmag) == type(True))
        self.assertEqual(valid_dmag, True)

    def test_valid_chi2sq(self):
        valid_chi2sq = classifier_tools.check_valid_chi2sq(self.params['target'])

        assert (type(valid_chi2sq) == type(True))
        self.assertEqual(valid_chi2sq, True)

def generate_test_ReducedDatums(target, lightcurve_file, tel_label):
    """Taken from test_fittools, by R. Street. Modified to match this test case.
    Method generates a set of ReducedDatums for different telescopes, as is held in the TOM for a
    single target
    """

    lc = []
    ts_jds = np.loadtxt(lightcurve_file, delimiter=',', skiprows=2, usecols=1)
    mags = np.loadtxt(lightcurve_file, delimiter=',', skiprows=2, usecols=2, dtype='str')

    for i in range(len(mags)):
        if('untrusted' not in mags[i] and 'null' not in mags[i]):
            jd = Time(float(ts_jds[i]), format='jd', scale='utc')
            datum = {
                    'magnitude': float(mags[i]),
                    'filter': tel_label,
                    'error': gaia_mop.estimateGaiaError(float(mags[i]))
                    }
            rd, created = ReducedDatum.objects.get_or_create(
                timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                value=datum,
                source_name='Gaia',
                source_location=target.name,
                data_type='photometry',
                target=target)

            if created:
                lc.append( [float(ts_jds[i]), float(mags[i]), gaia_mop.estimateGaiaError(float(mags[i]))] )
    data = {'G': np.array(lc) }

    return data

class TestCheckKnownVariable(TestCase):
    def setUp(self):
        st1 = SiderealTargetFactory.create()
        st1.name = 'Gaia23avo'
        st1.ra = 20.4233
        st1.dec = 11.8307
        st1.YSO = False
        st1.QSO = True
        st1.galaxy = True
        st1.save()
        self.target = st1
        self.results = {
            'classification': 'Extra-galactic variable',
            'category': 'Active Galactic Nucleus'
        }

    def test_check_known_variable(self):
        classifier_tools.check_known_variable(self.target, coord=None)

        assert(self.target.classification == self.results['classification'])
        assert(self.target.category == self.results['category'])
