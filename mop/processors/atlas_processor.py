import mimetypes

from astropy import units
from astropy.io import ascii
from astropy.time import Time, TimezoneInfo
from astropy.table import Table, Column
import numpy as np

from tom_dataproducts.data_processor import DataProcessor
from tom_dataproducts.exceptions import InvalidFileFormatException


class AtlasProcessor(DataProcessor):

    def data_type_override(self):
        return 'photometry'

    def process_data(self, data_product):
        """
        Routes a atlas processing call to a method specific to a file-format.

        :param data_product: Photometric DataProduct which will be processed into the specified format for database
        ingestion
        :type data_product: DataProduct

        :returns: python list of 3-tuples, each with a timestamp and corresponding data, and source
        :rtype: list
        """

        try:
            mimetype = mimetypes.guess_type(data_product.data.path)[0]
        except NotImplementedError:
            mimetype = 'text/plain'
        if mimetype in self.PLAINTEXT_MIMETYPES:
            photometry = self._process_photometry_from_plaintext(data_product)
            return [(datum.pop('timestamp'), datum, datum.pop('source', 'ATLAS')) for datum in photometry]
        else:
            raise InvalidFileFormatException('Unsupported file type')

    def _parse_atlas_data(self, data_aws):
        """
        Function to parse the returned contents of the ATLAS photometry, as read from AWS storage.

        For reasons that are unclear, astropy.io's reader doesn't handle this data format
        """

        # Read the AWS data object into a list of lines, removing any zero-length entries
        line_list = [x for x in data_aws.read().split('\n') if len(x) > 0]

        # Allowing for the first header line, parse the data lines
        data = []
        for line in line_list[1:]:
            entry = line.replace('\n','').split()
            data.append({'##MJD': entry[0],
                         'm': entry[1],
                         'dm': entry[2],
                         'uJy': entry[3],
                         'duJy': entry[4],
                         'F': entry[5]})
        print('ATLAS data: ', data)

        return data

    def _process_photometry_from_plaintext(self, data_product):
        """
        Processes the photometric data from a plaintext file into a list of dicts. File is read using astropy as
        specified in the below documentation. The file is expected to be a multi-column delimited space delimited
        text file, as produced by the ATLAS forced photometry service at https://fallingstar-data.com/forcedphot
        See https://fallingstar-data.com/forcedphot/resultdesc/ for a description of the output format.

        The header looks like this:
        ###MJD   m   dm  uJy   duJy F err chi/N   RA  Dec   x   y  maj  min   phi  apfit mag5sig Sky   Obs

        :param data_product: ATLAS Photometric DataProduct which will be processed into a list of dicts
        :type data_product: DataProduct

        :returns: python list containing the photometric data from the DataProduct
        :rtype: list
        """
        from django.core.files.storage import default_storage

        photometry = []
        signal_to_noise_cutoff = 3.0  # cutoff to turn magnitudes into non-detection limits

        # Here we replace the usual function to read from disk with one that can read from AWS
        #data = astropy.io.ascii.read(data_product.data.path)
        data_aws = default_storage.open(data_product.data.name, 'r')

        data = self._parse_atlas_data(data_aws)

        if len(data) < 1:
            raise InvalidFileFormatException('Empty table or invalid file type')

        try:
            for datum in data:
                time = Time(float(datum['##MJD']), format='mjd')
                utc = TimezoneInfo(utc_offset=0*units.hour)
                time.format = 'datetime'
                value = {
                    'timestamp': time.to_datetime(timezone=utc),
                    'filter': str(datum['F']),
                    'telescope': 'ATLAS',
                }
                # If the signal is in the noise, calculate the non-detection limit from the reported flux uncertainty.
                # see https://fallingstar-data.com/forcedphot/resultdesc/
                signal_to_noise = float(datum['uJy']) / float(datum['duJy'])
                if signal_to_noise <= signal_to_noise_cutoff:
                    value['limit'] = 23.9 - 2.5 * np.log10(signal_to_noise_cutoff * float(datum['duJy']))
                else:
                    value['magnitude'] = float(datum['m'])
                    value['error'] = float(datum['dm'])

                photometry.append(value)
        except Exception as e:
            raise InvalidFileFormatException(e)

        return photometry
