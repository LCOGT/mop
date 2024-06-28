import numpy as np
from mop.toolbox.mop_classes import MicrolensingEvent

def psi_derivatives_squared(t,te,u0,t0):
    """if you prefer to have the derivatives for a simple
       error propagation without correlation
    """
    x0 = u0**2
    x1 = te**(-2)
    x2 = (t - t0)**2
    x3 = x1*x2
    x4 = x0 + x3
    x5 = x2/te**3
    x6 = x4*x5
    x7 = x4 + 4.0
    x8 = x5*x7
    x9 = (x4*x7)**0.5
    x10 = 1/(x4*x7)
    x11 = x10/x9
    x12 = x10*x9
    x13 = 0.125/(0.5*x0 + 0.5*x3 + 0.5*x9 + 1)**2
    x14 = u0*x4
    x15 = u0*x7
    x16 = x1*(-2*t + 2*t0)
    x17 = (1/2)*x16
    x18 = x17*x4
    x19 = x17*x7

    c0 = 16.0*(x11*(x6 + x8) - x13*(-x12*(-x6 - x8) + 2*x5))**2
    c1 = 16.0*(x11*(-x14 - x15) - x13*(-2*u0 - x12*(x14 + x15)))**2
    c2 = 16.0*(x11*(-x18 - x19) - x13*(-x12*(x18 + x19) - x16))**2
    #i.e. for te, u0, to
    return [c0, c1, c2 ]

def TAP_planet_priority_error(time_now, t0_pspl, u0_pspl, tE_pspl, covariance):
    """
    This function calculates the priority for ranking
    microlensing events based on the planet probability psi
    as defined by Dominik 2009 and estimates the cost of
    observations based on an empiric RMS estimate
    obtained from a DANDIA reduction of K2C9 Sinistro
    observations from 2016. It expects the overhead to be
    60 seconds and also return the current Paczynski
    light curve magnification.
    """

    # Catch invalid input
    if len(covariance) == 0 or np.isnan(t0_pspl) or np.isnan(u0_pspl) or np.isnan(tE_pspl):
        return 0.0

    usqr = u0_pspl**2 + ((time_now - t0_pspl) / tE_pspl)**2

    dpsipdu = -8*(usqr+2)/(usqr*(usqr+4)**1.5)
    dpsipdu += 4*(usqr**0.5*(usqr+4)**0.5+usqr+2)/(usqr+2+(usqr+4)**0.5)**2*1/(usqr+4)**0.5

    dUdto = -(time_now - t0_pspl) / (tE_pspl ** 2 *usqr**0.5)
    dUduo = u0_pspl/ usqr**0.5
    dUdtE = -(time_now - t0_pspl) ** 2 / (tE_pspl ** 3 * usqr**0.5)

    print(covariance, dpsipdu, dUdto, dUdtE, dUduo)
    Jacob = np.zeros(len(covariance))
    Jacob[0] = dpsipdu*dUdto
    Jacob[1] = dpsipdu*dUduo
    Jacob[2] = dpsipdu*dUdtE

    error_psip = np.dot(Jacob.T,np.dot(covariance,Jacob))**0.5

    # Intercept NaN values and set them to zero as NaN entries
    # are non-retrievable from the DB
    if np.isnan(error_psip):
        error_psip = 0.0

    return error_psip #/ (calculate_exptime_omega_sdss_i(mag) + 60.)

def TAP_planet_priority(time_now, t0_pspl, u0_pspl, tE_pspl):
    """
    This function calculates the priority for ranking
    microlensing events based on the planet probability psi
    as defined by Dominik 2009 and estimates the cost of
    observations based on an empiric RMS estimate
    obtained from a DANDIA reduction of K2C9 Sinistro
    observations from 2016. It expects the overhead to be
    60 seconds and also return the current Paczynski
    light curve magnification.
    """

    # Catch invalid input
    if np.isnan(t0_pspl) or np.isnan(u0_pspl) or np.isnan(tE_pspl) \
            or t0_pspl == 0.0 or tE_pspl == 0.0:
        return 0.0

    usqr = u0_pspl**2 + ((time_now - t0_pspl) / tE_pspl)**2
    pspl_deno = (usqr * (usqr + 4.))**0.5
    if pspl_deno < 1e-10:
        pspl_deno = 10000.
    psip = 4.0 / (pspl_deno) - 2.0 / (usqr + 2.0 + pspl_deno)

    # Intercept NaN values and set them to zero as NaN entries
    # are non-retrievable from the DB
    if np.isnan(psip):
        psip = 0.0

    return psip

def TAP_long_event_priority(t_now, t_last, t_E, t_E_base = 75.):
    """
    This function calculates priority of a long microlensing event.
    If the event has a timescale equal to t_E_base, and was not
    observed for t_obs_gap days, the priority should be close to 10.
    If the event was not observed for more than 10 days,
    the priority is boosted by 10.
    If the fit was bad (indicated by t_E being a NaN), than
    the priority drops to 0.
    Inspired by Horn et al. 2009.

    :param t_now: current JD
    :param t_last: JD of the latest datapoint in any lightcurve
                    assigned to the dataset
    :param t_E: Einstein timescale of the event
    :param t_E_base: cutoff point for long tE event

    :return: priority of the long microlensing event
    """

    # Catch invalid input
    if np.isnan(t_E) or t_E == 0.0:
        return 0.0

    if (np.isnan(t_E)):
        # t_E may hit the fit bounds. This means, the fit was
        # wrong. In this case the event should not be observed
        # and wait for a better estimate of the values.
        psi = np.nan
    else:
        t_obs_gap = 2.

        # Events with t_E of t_E_base days will have priority 10.
        psi = t_E / t_E_base

        # If the event was not observed for t_obs_gap days the priority
        # should rise.
        delta_t = t_now - t_last
        x = (delta_t / t_obs_gap) - t_obs_gap
        psi *= 10. / (1. + np.exp(-x))

        # KK: Boosting turned off, short timescale events were promoted.
        # The event priority should be boosted if it was not
        # observed for more than 10 days and it is a long event.
        # if (delta_t > 10.):
        #     psi *= 10.

    # Intercept NaN values and set them to zero as NaN entries
    # are non-retrievable from the DB
    if np.isnan(psi):
        psi = 0.0

    return psi

def TAP_long_event_priority_error(t_E, covariance, t_E_base = 75.):
    """
    This function calculates error of the priority
    of a long microlensing event.

    :param t_E: Einstein timescale of the event
    :param covariance: covariance matrix
    :param t_E_base: cutoff point for long tE event

    :return: error of the priority of the long microlensing event.
    """

    # Catch invalid input
    if len(covariance) == 0 or np.isnan(t_E):
        return 0.0

    if(np.isnan(t_E)):
        err_psi = 0.
    else:
        # Simple derevative
        err_t_E = np.sqrt(covariance[2,2])
        err_psi = 10. *  err_t_E / t_E_base

    # Intercept NaN values and set them to zero as NaN entries
    # are non-retrievable from the DB
    if np.isnan(err_psi):
        err_psi = 0.0

    return err_psi

def check_planet_priority(planet_priority, planet_priority_error, mag_baseline, mag_now, t_0, time_now):
    '''
    This function checks if the event status should be changed to priority stellar event.

    :param planet_priority: value of the TAP_priority for the event
    :param planet_priority_error: error of the priority
    :param mag_baseline: baseline magnitude of the event
    :param mag_now: current magnitude of the event
    :param t_0: Predicted time of event peak, JD
    :param time_now: Current time in JD
    '''

    # Criterion on the priority uncertainty depends on whether the event has reached the
    # peak or not, with greater flexibility allowed prior to the peak
    criterion1 = (planet_priority > 10)
    if time_now >= t_0:
        # Loosened post-peak from 3 sigma to 2 sigma.
        criterion2 = (planet_priority / planet_priority_error > 2)
    else:
        criterion2 = (planet_priority / planet_priority_error > 1)
    # Loosening criterion 3 to observe more potential planetary candidates
    # Might need  based on the survey (some might require amplitude of 2.0
    # to remove spurious planetary candidates).
    # If event is brighter than 17.5 -> lower ampl. limit.
    # If it's dimmer - 2 mag limit, we don't want to use up too much 1m time
    # on very dim events.
    if mag_now < 17.5:
        criterion3 = (mag_baseline - mag_now > 0.3)
    else:
        criterion3 = (mag_baseline - mag_now > 2.)
    criterion4 = (mag_now < 19.)

    if criterion1 and criterion2 and criterion3 and criterion4:
        return True
    else:
        return False

def check_long_priority(long_priority, long_priority_error,
                        t_E, t_E_error, mag_now,
                        mag_baseline, red_chi2,
                        t_0, time_now):
    '''
    This function checks if the event status should be changed to priority stellar event.

    :param long_priority: value of the TAP_priority_longE for the event
    :param long_priority_error: error of the priority
    :param t_E: Einstein timescale of the best fitting model
    :param t_E: uncertianity of the Einstein timescale of the best fitting model
    :param red_chi2: chi2 over degrees of freedom of the best fitting model
    :param mag_now: current magnitude of the event
    :param t_0: Predicted time of event peak, JD
    :param time_now: Current time in JD
    '''

    # Check for conditions which will cause numerical instability
    if long_priority_error < 1e-5:
        return None

    # Criterion on the priority uncertainty depends on whether the event has reached the
    # peak or not, with greater flexibility allowed prior to the peak
    criterion1 = (long_priority > 10.0)
    if time_now >= t_0:
        # Loosened post-peak from 3 sigma to 2 sigma.
        criterion2 = (long_priority / long_priority_error > 2)
    else:
        criterion2 = (long_priority / long_priority_error > 1)
    # Loosened criterion3, changed from 3 sigma to 1
    criterion3 = (t_E / t_E_error > 1.0)
    criterion4 = (mag_now < 17.5)
    criterion5 = (red_chi2 < 20.0)
    criterion6 = (mag_baseline - mag_now > 0.3)

    if criterion1 and criterion2 and criterion3 and criterion4 and criterion5 and criterion6:
        # and (((t_0 - t_now - (3. * (t_0_error + t_E_error))) / t_E) < 1.2)): # turning off events should be handled by Alive status
        if(long_priority > 50.):
            return 'priority'
        else:
            return 'regular'
    else:
        return None