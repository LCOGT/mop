import dash
from dash import html, dash_table
from django_plotly_dash import DjangoDash
from django.conf import settings

# Needs to receive an object_list of Targets from a FilterView
app = DjangoDash('TargetlistTable')

# Table columns should be customized according to whatever the user
# has specified in the settings.
table_columns = [{'name':col, 'type':typ} for col,typ in settings.TARGETLIST_FIELDS]

object_list = [
    {'names': 'Target1', 'RA': 245.0, 'Dec': -29.0, 'tE': 20.0, 'u0': 0.1, 't0': 2450000.0, 'mag_now': 17.5}
]

# Compile the data for the table
table_data = []
for target in object_list:
    table_data.append(
        [{col: target[col]} for col,typ in settings.TARGETLIST_FIELDS],
    )


def generate_table(object_list, column_definitions):
    table_rows = []
    for target in object_list:
        table_rows.append(html.Tr(
            [html.Td(target[col]) for col, typ in column_definitions]
        ))

    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col,typ in column_definitions])
        ),
        table_rows
    ])


# Create the table application
app.layout = html.Div([
    generate_table(object_list, settings.TARGETLIST_FIELDS)
])

print('Got here')