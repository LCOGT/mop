from tom_targets.models import Target
from astropy.coordinates import SkyCoord, Galactic
from astropy import units as u
from django.contrib.auth.models import Group, User
from django.db import connection
from guardian.shortcuts import assign_perm
import datetime
import os
import logging
import psutil

logger = logging.getLogger(__name__)
process = psutil.Process()

def fetch_extra_param(target, key):
    string_keys = ['Classification', 'Category', 'Observing_mode', 'Sky_location',
                   'Gaia_Source_ID', 'Interferometry_mode', 'Mag_now_passband']
    if key in target.extra_fields.keys():
        if key in string_keys:
            value = target.extra_fields[key]
        else:
            try:
                value = float(target.extra_fields[key])
            except ValueError:
                value = None
            except TypeError:
                value = None
    elif key in target.tags.keys():
        if key in string_keys:
            value = target.extra_fields[key]
        else:
            try:
                value = float(target.tags[key])
            except ValueError:
                value = None
            except TypeError:
                value = None
    else:
        value = None

    return value

def add_gal_coords(target):
    """Function to add Galactic coordinates to a target"""

    # Exception handling for manually-created targets where the coordinates can be stored as a string
    if type(target.ra) == type('test') or type(target.dec) == type('test'):
        target.ra = float(target.ra)
        target.dec = float(target.dec)

    s = SkyCoord(ra=target.ra * u.degree, dec=target.dec * u.degree, frame='icrs')
    target.galactic_lng = s.galactic.l.value
    target.galactic_lat = s.galactic.b.value
    target.save()

def open_targets_to_OMEGA_team(target_list):
    """Function to assign the correct permissions for all OMEGA team members to see the target given"""

    omega_group = Group.objects.filter(name='OMEGA').first()
    if not omega_group:
        omega_group = Group.objects.filter(name='OMEGA-II').first()
    logger.info('TARGET PERMISSIONS: adding permissions for user group ' + repr(omega_group) +
                ' for ' + str(len(target_list)) + ' targets')

    if omega_group:
        for target in target_list:
            logger.info('PERMISSIONS set for ' + target.name)
            assign_perm('tom_targets.view_target', omega_group, target)
            assign_perm('tom_targets.change_target', omega_group, target)

def checkpoint():
    """Function to output the number of database connections and memory useage in MB"""

    logger.info('CHECKPOINT: N DB connections: '
                + str(len(connection.queries)) + ', memory: '
                + str(round(psutil.Process(os.getpid()).memory_info().rss / 1048576, 2)) + 'MiB')

