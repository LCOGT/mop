from tom_targets.models import Target, TargetName
import logging

logger = logging.getLogger(__name__)

def check_target_unique(name, ra, dec):
    """Function to verify that a new candidate Target is unique and does not have a matching
    entry in the database.

    This matches against both target name and sky position.
    """
    name_qs = Target.objects.filter(name=name)

    search_radius = 2.0  # arcsec

    cone_search_qs = Target.matches.match_cone_search(ra, dec, search_radius)

    result_qs = name_qs | cone_search_qs

    if result_qs.count() > 0:
        return False
    else:
        return True

def check_target_name_unique(name):
    """Function to verify that a new candidate Target has a unique name"""
    qs = Target.objects.filter(name=name)

    if qs.count() > 0:
        return False
    else:
        return True


def check_target_alias_unique(name):
    """Function to verify that a new candidate Target has a unique name"""
    qs = TargetName.objects.filter(name=name)

    if qs.count() > 0:
        return False
    else:
        return True

def check_target_coordinates_unique(ra, dec, radius=2.0):
    """Function to verify that a new candidate Target is unique and does not have a matching
    entry in the database.
    This performs a cone search on the object's RA and Dec with a default radius of 2 arcsec.
    """

    qs = Target.matches.match_cone_search(ra, dec, radius)

    if qs.count() > 0:
        return False
    else:
        return True

def get_or_create_event(name, ra, dec, radius=2.0, debug=False):
    """
    Function to fetch a matching event from the database if one exists with
    either matching coordinates or a matching name
    """

    # An exact name matches both the target name and aliases
    name_unique = check_target_name_unique(name)
    alias_unique = check_target_alias_unique(name)
    coords_unique = check_target_coordinates_unique(ra, dec, radius=radius)
    if debug:
        print('Validating candidate event: name_unique=' + repr(name_unique)
                    + ' alias_unique=' + repr(alias_unique)
                    + ' coords_unique=' + repr(coords_unique))

    # If no matches are found at all, create a new target
    if name_unique and alias_unique and coords_unique:
        t = Target.objects.create(
            name=name,
            ra=ra,
            dec=dec,
            type='SIDEREAL',
            epoch=2000
        )
        logger.info('Created new Target ' + t.name + ', pk=' + str(t.pk))
        return t, 'new_target'

    # If a matching target is found by name, return that target
    if not name_unique and alias_unique:
        t = Target.objects.get(name=name)
        created = False
        logger.info('Matched Target by exact name ' + t.name + ', pk=' + str(t.pk))
        return t, 'existing_target_exact_name'

    if name_unique and not alias_unique:
        tn = TargetName.objects.get(name=name)
        t = Target.objects.get(pk=tn.target_id)
        created = False
        logger.info('Matched Target ' + name + ' by alias to ' + t.name + ', pk=' + str(t.pk))
        return t, 'existing_target_existing_alias'

    # If a match is found in coordinates but not name, check to see if there is an alias
    # already.  If so, return the alias Target.  If not, n
    if not coords_unique and name_unique and alias_unique:
        qs = Target.matches.match_cone_search(ra, dec, radius)
        t = qs[0]
        tn = TargetName.objects.create(target=t, name=name)
        created = 'existing_target_new_alias'
        logger.info('Matched Target ' + name + ' by coordinates to ' + t.name + ', pk=' + str(t.pk)
                    + ' created new alias ' + tn.name)
        return t, created
