import unittest
from unittest import mock
from mop.brokers import asassn
from tom_dataproducts.models import ReducedDatum
from tom_targets.models import Target

BROKER_URL = 'http://www.astronomy.ohio-state.edu/asassn/transients.html'
broker = ASASSNBroker('ASAS-SN Broker')
fakedata = [['id', ['', '']], ['other', ['AT2021kdo (= Gaia21bxn)',
            'AT20210du(=Gaia21cqi)']], ['ATEL', ['', '']], ['RA', ['1:6:42.74', '8:8:36.48']],
            ['Dec', ['61:59:40.9', '-40:53:23.5']], ['Discovery', ['2021-06-9.44', '2021-06-12.74']],
            ['V/g', ['13.98', '15.46']], ['SDSS', ['', '']], ['DSS', ['', '']], ['Vizier', ['', '']],
            ['Spectroscopic Class', ['', '']],
            ['comments', ['known microlensing event or Be-type outburst, discovered 2021/04/16.801',
                            'known candidate Be-star or microlensing event, discovered 2021/06/01.188']]]


class TestActivity(unittest.TestCase):
    def SetUp(self, broker):
        self.broker = asassn.ASASSNBroker('ASAS-SN Broker')

    def test_open_webpage(self):
        '''
        Tests that the link to the transient table functions
        '''
        page_response = broker.open_webpage()
        self.assertEqual(200, page_response)

    def test_retrieve_transient_table(self):
        '''
        Tests that retrieve_transient_table() can read rows and there is at least 1 row in the table
        '''
        col = broker.retrieve_transient_table()
        self.assertFalse(len(col[0][1]) == 0)
        self.assertFalse(len(col[1][1]) == 0)
        self.assertFalse(len(col[2][1]) == 0)
        self.assertFalse(len(col[3][1]) == 0)
        self.assertFalse(len(col[4][1]) == 0)
        self.assertFalse(len(col[5][1]) == 0)
        self.assertFalse(len(col[6][1]) == 0)
        self.assertFalse(len(col[7][1]) == 0)
        self.assertFalse(len(col[8][1]) == 0)
        self.assertFalse(len(col[9][1]) == 0)
        self.assertFalse(len(col[10][1]) == 0)
        self.assertFalse(len(col[11][1]) == 0)

    def test_retrieve_microlensing_coordinates(self):
        '''
        Tests that the number of events created given mock data is correct
        '''
        with mock.patch('mytom.asassn.ASASSNBroker.retrieve_transient_table', return_value=fakedata):
            '''
            The length should be 2, given the fake data
            '''
            actual_result = broker.retrieve_microlensing_coordinates(fakedata)
            assert (len(actual_result) == 2)

    def test_fetch_alerts(self):
        '''
        Tests that fetch_alerts() returns an object of type Target
        '''
        table = broker.retrieve_transient_table()
        events = broker.retrieve_microlensing_coordinates(table)
        targetlist = broker.fetch_alerts(events)
        targettype = type(targetlist[0])
        self.assertTrue(targettype == Target)

    def test_find_and_ingest_photometry(self):
        '''
        Tests that find_and_ingest_photometry() returns at least one ReducedDatum object
        '''
        table = broker.retrieve_transient_table()
        events = broker.retrieve_microlensing_coordinates(table)
        targetlist = broker.fetch_alerts(events)
        rd_list = broker.find_and_ingest_photometry(events, targetlist)
        objecttype = type(rd_list[0])
        assert (objecttype == ReducedDatum)
