### Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import yaml
import fsspec, os, glob, re
from pathlib import Path

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME") # Store username in env vars
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from Render env vars

### Customized Functions
# return unknown for variables not in yaml
def key_missing(x,key):
    try:
        return x[key]
    except KeyError:
        return 'unknown'
    except TypeError:
        return 'unknown'

# return the joined list if multiple specimens combined;
def list_join(x):
    if isinstance(x, list):
        return '; '.join(x)
    else:
        return x

### Incorporate data
# recursive copy all yaml files from the shedding-hub repository;
destination = Path.cwd()/"data"
destination.mkdir(exist_ok=True, parents=True)
fs = fsspec.filesystem("github", org="shedding-hub", repo="shedding-hub",username=GITHUB_USERNAME,token=GITHUB_TOKEN)
fs.get(fs.glob("data/**/*.yaml"), destination.as_posix(), recursive=True)

# load the yaml;
list_file = glob.glob("data/*.yaml")
list_yaml = []
for file in list_file:
    list_yaml.append(yaml.safe_load(Path(file).read_text()))

# extract the analytes from yaml list;
list_analyte = []
for df in range(0,len(list_yaml)):
    for analyte in list_yaml[df]['analytes']:
        list_analyte.append([re.split(r'[\\.]+', list_file[df])[0],
                             analyte,
                             list_yaml[df]['analytes'][analyte]['biomarker'],
                             key_missing(list_yaml[df]['analytes'][analyte],'gene_target'), # For not required variables;
                             list_join(list_yaml[df]['analytes'][analyte]['specimen']), # join the list if multiple specimens;
                             list_yaml[df]['analytes'][analyte]['unit'],
                             list_yaml[df]['analytes'][analyte]['limit_of_detection'],
                             list_yaml[df]['analytes'][analyte]['limit_of_quantification'],
                             list_yaml[df]['analytes'][analyte]['reference_event']
                            ])
df_analyte = pd.DataFrame(list_analyte, columns=['ID', 'analyte', 'biomarker', 'gene_target', 'specimen', 'unit', 'LOD', 'LOQ', 'reference_event'])

# extract the participants information from yaml list;
list_participant = []
for df in range(0,len(list_yaml)):
    for participant_id in range(0,len(list_yaml[df]['participants'])):
        list_participant.append([re.split(r'[\\.]+', list_file[df])[0],
                                 participant_id+1, #start from 1;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'age'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'sex'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'race'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'ethnicity'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'vaccinated') # For not required variables;
                                ])
df_participant = pd.DataFrame(list_participant, columns=['ID', 'participant_ID', 'age', 'sex', 'race', 'ethnicity', 'vaccinated'])

# extract the measurements from yaml list;
list_measurement = []
for df in range(0,len(list_yaml)):
    for participant_id in range(0,len(list_yaml[df]['participants'])):
        for measurement_id in range(0,len(list_yaml[df]['participants'][participant_id]['measurements'])):
            list_measurement.append([re.split(r'[\\.]+', list_file[df])[0],
                                     participant_id+1, #start from 1;
                                     measurement_id+1, #start from 1;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'analyte'), # For not required variables;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'time'), # For not required variables;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'value') # For not required variables;
                                    ])
df_measurement = pd.DataFrame(list_measurement, columns=['ID', 'participant_ID', 'measurement_ID', 'analyte', 'time', 'value'])

### Create some static graphs
temp_analyte = df_analyte.loc[(df_analyte["biomarker"]=="SARS-CoV-2") & (df_analyte["specimen"]=="stool") & (df_analyte["reference_event"]=="symptom onset")]
temp_participant = df_participant.loc[df_participant['ID'].isin(temp_analyte['ID'])]
temp_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(temp_analyte['ID']+temp_analyte['analyte'])]

fig_scatter1 = px.scatter(temp_measurement, x='time', y='value', log_y=True, color="ID", title='SARS-CoV-2 Shedding Data for Stool Samples', labels={"time": "Days after Symptom Onset", "value": "Viral Load (gc/mL or gc/dry gram)", "ID": "Study"})

### Initialize the app
app = Dash(__name__)
server = app.server

### App layout
app.layout = [
    html.Div(children='Shedding Hub - Analytes Summarization'),
    html.Hr(),
    dcc.RadioItems(options=['biomarker', 'specimen', 'reference_event'], value='biomarker', inline=True, id='controls-and-radio-item'),
    dash_table.DataTable(data=df_analyte.to_dict('records'), page_size=10),
    dcc.Graph(figure={}, id='controls-and-graph'),
    dcc.Graph(
        id='scatter-plot-1',
        figure=fig_scatter1
    )
]

### Add controls to build the interaction
@callback(
    Output(component_id='controls-and-graph', component_property='figure'),
    Input(component_id='controls-and-radio-item', component_property='value')
)
def update_graph(col_chosen):
    fig = px.bar(pd.DataFrame({col_chosen:df_analyte[col_chosen].value_counts().index.tolist(),'count':df_analyte[col_chosen].value_counts().tolist()}),x=col_chosen, y="count")
    return fig

### Run the app
if __name__ == '__main__':
    app.run(host= '0.0.0.0', debug=True) # for app deployment at render.com;
#    app.run(debug=True) # for local development;