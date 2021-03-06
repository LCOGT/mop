from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from tom_alerts.alerts import GenericBroker, GenericQueryForm
from django import forms
from tom_targets.models import Target
from tom_observations import facility
from tom_dataproducts.models import ReducedDatum
import urllib.request
import requests
from tom_alerts.brokers.mars import MARSQueryForm, MARSBroker
from tom_alerts.models import BrokerQuery
import numpy as np
import json
from astropy.time import Time, TimezoneInfo

BROKER_URL = 'https://www.astro.caltech.edu/~pmroz/microlensing/table.html'


class ZTFIPACQueryForm(GenericQueryForm):
    target_name = forms.CharField(required=False)
    cone = forms.CharField(
        required=False,
        label='Cone Search',
        help_text='RA,Dec,radius in degrees'
    )

    def clean(self):
        if len(self.cleaned_data['target_name']) == 0 and \
                        len(self.cleaned_data['cone']) == 0:
            raise forms.ValidationError(
                "Please enter either a target name or cone search parameters"
                )


class ZTFIPACBroker(GenericBroker):

    name = 'ZTFIPAC'
    form = ZTFIPACQueryForm

    def fetch_alerts(self,):
        mars = MARSBroker()

        #download from ZTF web server (i.e. Przemek webpage)
        ztf_ipac = urllib.request.urlopen(BROKER_URL).readlines()
        
        list_of_events = [str(i)[6:-8] for i in ztf_ipac if '<td>ZTF' in str(i)]
        list_of_mars_links = [str(i).split('"')[1] for i in ztf_ipac if '<td><a href="https://mars.lco.global/' in str(i)]


        for index,event in enumerate(list_of_events):

            try:
                MARS_candidates = requests.get(list_of_mars_links[index]+'&format=json').json()
                cone_search = str(MARS_candidates['results'][0]['candidate']['ra'])+','+str(MARS_candidates['results'][0]['candidate']['dec'])+','+str(0.0001)
                mars_form = MARSQueryForm({'cone':cone_search,'query_name':'Query ZTF IPAC : '+event, 'broker':'MARS'})
                mars_form.is_valid()
                query = BrokerQuery.objects.create(
                               name='Query ZTF IPAC : '+event,
                               broker=mars.name,
                               parameters=mars_form.serialize_parameters()
                                               )
                alerts = mars.fetch_alerts(query.parameters_as_dict)
                alerts = [*alerts]  

                name = event
                ra = np.median([alert['candidate']['ra'] for alert in alerts])
                dec = np.median([alert['candidate']['dec'] for alert in alerts])
                
                try:
                
                    target = Target.objects.get(name=name)
                
                except:
                
                    target, created =  Target.objects.get_or_create(name=name,ra=ra,dec=dec,type='SIDEREAL',epoch=2000)


                    if created:

                       target.save()
                   

                filters = {1: 'g_ZTF', 2: 'r_ZTF', 3: 'i_ZTF'}


                for alert in alerts:
                   try:


                       if all([key in alert['candidate'] for key in ['jd', 'magpsf', 'fid', 'sigmapsf']]):
                          jd = Time(alert['candidate']['jd'], format='jd', scale='utc')
                          jd.to_datetime(timezone=TimezoneInfo())
                          
                          if alert['candidate']['isdiffpos'] == 't':
                              signe = 1
                          else:
                              signe = -1
                              
                          flux = 10**(-0.4*alert['candidate']['magnr'])+signe*10**(-0.4*alert['candidate']['magpsf'])
                          eflux = ((10**(-0.4*alert['candidate']['magnr'])*alert['candidate']['sigmagnr'])**2+(signe*10**(-0.4*alert['candidate']['magpsf'])*alert['candidate']['sigmapsf'])**2)**0.5
                          
                          mag = -2.5*np.log10(flux)
                          emag = eflux/flux
                          
                          value = {
                                   'magnitude': mag,
                                   'filter': filters[alert['candidate']['fid']],
                                   'error': emag
                                   }
                                   
                          existing_point =   ReducedDatum.objects.filter(source_name='IRSA',timestamp=jd.to_datetime(timezone=TimezoneInfo()))

                                                                            
                          if existing_point.count() == 0:                                               
                              rd, created = ReducedDatum.objects.get_or_create(
                                            timestamp=jd.to_datetime(timezone=TimezoneInfo()),
                                            value=json.dumps(value),
                                            source_name='IRSA',
                                            data_type='photometry',
                                            target=target)
                              rd.save()
                          else:
                              rd, created = ReducedDatum.objects.update_or_create(
                                            timestamp=existing_point[0].timestamp,
                                            value=existing_point[0].value,
                                            source_name='IRSA',
                                            data_type='photometry',
                                            target=target,
                                            defaults={'value':json.dumps(value)})
                              rd.save()
                   except:

                          pass
            except:
                  pass


    def to_generic_alert(self, alert):
        pass
