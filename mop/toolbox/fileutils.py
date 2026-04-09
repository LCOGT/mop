from os import path
import numpy as np
from astropy.table import Table, Column
import logging
import csv

logger = logging.getLogger(__name__)

def load_ogle_lc(input_file, filter_id):
    """
    Function to load an OGLE lightcurve from a dat-format input file downloaded from the project website
    """

    with open(input_file) as f:
        raw_data = np.loadtxt(f)

    lc_data = Table([
        Column(name='HJD', data=raw_data[:,0]),
        Column(name='mag', data=raw_data[:,1]),
        Column(name='mag_error', data=raw_data[:,2]),
        Column(name='filter', data=[filter_id]*len(raw_data))
    ])

    return lc_data

def ogle_to_mop_format(lc_data, output_file):
    """
    Function to output Table format lightcurve data, potentially in multiple filters,
    to CSV format files suitable for upload to the MOP system.  If data from multiple
    filters is included, multiple lightcurve files will be created.
    """

    filter_set = np.unique(lc_data['filter'].data)

    file_root_name = (path.basename(output_file)).split('.')[0]
    output_file_root = path.join(path.dirname(output_file), file_root_name)

    for f in filter_set:
        file_path = output_file_root + '_' + str(f) + '.csv'
        idx = np.where(lc_data['filter'] == f)[0]

        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(['time', 'filter', 'magnitude', 'error'])
            for i in idx:
                writer.writerow([
                    lc_data['HJD'][i],
                    lc_data['filter'][i],
                    lc_data['mag'][i],
                    lc_data['mag_error'][i]
                ])

        logger.info('Output ' + f + '-band lightcurve to ' + file_path)
