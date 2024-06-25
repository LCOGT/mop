from django.test import TestCase
from tom_targets.tests.factories import SiderealTargetFactory
import json
import numpy as np

# Create your tests here.
class TestParameterLoad(TestCase):
    """
    Suite of tests to verify the methods load custom parameters properly
    """

    def setUp(self):
        self.test_cases = []
        t1 = SiderealTargetFactory.create()
        t1.name = 'Gaia23cqg'
        t1.ra = 223.61302
        t1.dec = 51.40936
        covar = np.array([
            [7.50843171e+02, -1.48057899e-01,  6.18529283e+02, -1.80681898e+04, 1.35817217e+04,  -1.82237158e+04,
             1.53886706e+04, 5.28582936e+04, -5.42862831e+04],
            [-1.48057899e-01, 5.74858660e-04, -7.47280158e-02, -1.74518940e+01, 1.90389195e+01, 6.34806867e+01,
             -6.38378289e+01, -4.50560725e+01, 5.25932590e+01],
            [6.18529283e+02, -7.47280158e-02, 7.02622032e+02, -1.74739432e+04, 1.08163128e+04, -1.97851100e+04,
             1.53351735e+04, 4.93352786e+04, 5.32002101e+04],
            [-1.80681898e+04, -1.74518940e+01, 1.74739432e+04, 1.82182520e+07, -1.84407854e+07, -7.33099352e+06,
             7.62580956e+06, -2.51230610e+07, 2.72019285e+07],
            [1.35817217e+04, 1.90389195e+01, 1.08163128e+04, -1.84407854e+07, 1.88178048e+07, 7.79026463e+06,
             -8.04056529e+06, 2.51432425e+07, -2.71990758e+07],
            [-1.82237158e+04, 6.34806867e+01, -1.97851100e+04, -7.33099352e+06, 7.79026463e+06, 1.86479328e+07,
             -1.89179324e+07, -9.43375601e+06, 1.07965329e+07],
            [1.53886706e+04, -6.38378289e+01, 1.53351735e+04, 7.62580956e+06, -8.04056529e+06, -1.89179324e+07,
             1.92814127e+07, 9.32691603e+06, -1.06726424e+07],
            [5.28582936e+04, -4.50560725e+01, 4.93352786e+04, 2.51230610e+07, 2.51432425e+07, 9.43375601e+06,
             9.32691603e+06, 5.94598882e+07, -6.45854470e+07],
            [-5.42862831e+04, 5.25932590e+01, -5.32002101e+04, 2.72019285e+07, -2.71990758e+07, 1.07965329e+07,
             -1.06726424e+07, -6.45854470e+07, 7.12153587e+07]
        ])
        t1.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t1, covar))

        t2 = SiderealTargetFactory.create()
        t2.name = 'OGLE-2023-BLG-0358'
        t2.ra = 267.73029166666663
        t2.dec = -29.406499999999998
        covar = np.array([
            [5.896644803219248, -8.420701912004672, 0.43496001906945164, -0.13524726301089462],
            [-8.420701912004693, 18.898038141275293, 1.523564940298867, -0.459894739200238],
            [0.4349600190694435, 1.5235649402988811, 0.8498806875729258, -0.34717724484103435],
            [-0.13524726301089257, -0.4598947392002415, -0.3471772448410346, 11.071809175704187]
        ])
        t2.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t2, covar))

        t3 = SiderealTargetFactory.create()
        t3.name = 'OGLE-2023-BLG-1276'
        t3.ra = 265.96966666666657
        t3.dec = -24.470805555555554
        covar = np.array([
            [8.76084758e-01, 2.50769809e-02, 1.50920370e-01, 1.05804314e+02, -1.05859037e+02],
            [2.50769809e-02, 7.35727712e-02, -3.22495649e+00, 4.94891311e+02, -4.94645386e+02],
            [1.50920370e-01, -3.22495649e+00, 1.45747939e+02, -2.18743280e+04, 2.18619636e+04],
            [1.05804314e+02, 4.94891311e+02, -2.18743280e+04, 3.34077405e+06, -3.33911468e+06]
        ])
        t3.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t3, covar))

        t4 = SiderealTargetFactory.create()
        t4.name = 'Gaia24ada'
        t4.ra = 283.14101
        t4.dec = 42.31333
        covar = np.array([])
        t4.fit_covariance = {'covariance': json.dumps(covar.tolist())}
        self.test_cases.append((t4, covar))
    def test_load_fit_covariance(self):

        for test_case, expected_result in self.test_cases:
            result = test_case.load_fit_covariance()

            assert(result == expected_result).all()
            assert(type(result) == type(expected_result))