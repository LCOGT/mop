from django.shortcuts import redirect
from django.urls import reverse
from django.core.management import call_command
from django.views.generic import TemplateView
from django.shortcuts import render
from io import StringIO
from plotly.graph_objs import Scatter
import plotly.offline as opy
import plotly.graph_objs as go
from tom_observations.models import Target
from tom_targets.views import TargetDetailView


class MOPTargetDetailView(TargetDetailView):

    def get(self, request, *args, **kwargs):
        fit_event = request.GET.get('fit_event', False)
        print(fit_event)
        if fit_event:
            target_id = self.get_object().id
            target_name = self.get_object().name
            out = StringIO()
            print(target_id,target_name)
            call_command('fit_event_PSPL', target_name, cores=0, stdout=out)
            return redirect(reverse('tom_targets:detail', args=(target_id,)))

        TAP_event = request.GET.get('tap_event', False)
        print(TAP_event)
        if TAP_event:
            target_id = self.get_object().id
            target_name = self.get_object().name
            out = StringIO()
            print(target_id,target_name)
            call_command('run_TAP', target_name, stdout=out)
            return redirect(reverse('tom_targets:detail', args=(target_id,)))
        return super().get(request, *args, **kwargs)

class ProductivityView(TemplateView):
    template_name = 'productivity.html'

    def get_context_data(self, **kwargs):
        context = super(ProductivityView, self).get_context_data(**kwargs)

        x = [-2,-1,0,1,2]
        y = [1, 1, 1, 1, 1]
        y1 = [2, 2, 2, 2, 2]
        y2 = [3, 3, 3, 3, 3]
        #Easy to make multiple plot lines if they are all in a pandas dataframe
        #Make the colors by observatory name, but plot by stage: Not Executed, Executed, and Pending

        layout=go.Layout(title="Reqs vs Obs", xaxis={'title':'Date'}, yaxis={'title':''},
                         template='simple_white')
        fig = go.Figure(layout=layout) #color='name of the observatory column')

        # Add traces
        fig.add_trace(go.Scatter(x=x, y=y,
                    mode='markers',
                    marker={'color': 'red', 'symbol': 100, 'size': 10},
                    name='Not Executed'))
        fig.add_trace(go.Scatter(x=x, y=y1,
                    mode='markers',
                    marker={'color': 'green', 'symbol': 0, 'size': 10},
                    name='Executed'))
        fig.add_trace(go.Scatter(x=x, y=y2,
                    mode='markers',
                    marker={'color': 'blue', 'symbol': 117, 'size': 10},
                    name='Pending'))


        div = opy.plot(fig, auto_open=False, output_type='div')

        context['graph'] = div

        return context

class TimeAllocView(TemplateView):
    template_name = 'time-alloc.html'

    def get_context_data(self, **kwargs):
        return {'targets': Target.objects.all()}
