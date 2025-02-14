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
        list_analyte.append([re.split(r'[\\/.]+', list_file[df])[1],
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
df_analyte[' index'] = range(1, len(df_analyte) + 1)
list_biomarker = df_analyte["biomarker"].unique()
list_specimen = df_analyte["specimen"].unique()
#list_gene = df_analyte["gene_target"].unique()

# extract the participants information from yaml list;
list_participant = []
for df in range(0,len(list_yaml)):
    for participant_id in range(0,len(list_yaml[df]['participants'])):
        list_participant.append([re.split(r'[\\/.]+', list_file[df])[1],
                                 participant_id+1, #start from 1;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'age'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'sex'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'race'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'ethnicity'), # For not required variables;
                                 key_missing(key_missing(list_yaml[df]['participants'][participant_id],'attributes'),'vaccinated') # For not required variables;
                                ])
df_participant = pd.DataFrame(list_participant, columns=['ID', 'participant_ID', 'age', 'sex', 'race', 'ethnicity', 'vaccinated'])
df_participant[' index'] = range(1, len(df_participant) + 1)

# extract the measurements from yaml list;
list_measurement = []
for df in range(0,len(list_yaml)):
    for participant_id in range(0,len(list_yaml[df]['participants'])):
        for measurement_id in range(0,len(list_yaml[df]['participants'][participant_id]['measurements'])):
            list_measurement.append([re.split(r'[\\/.]+', list_file[df])[1],
                                     participant_id+1, #start from 1;
                                     measurement_id+1, #start from 1;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'analyte'), # For not required variables;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'time'), # For not required variables;
                                     key_missing(list_yaml[df]['participants'][participant_id]['measurements'][measurement_id],'value') # For not required variables;
                                    ])
df_measurement = pd.DataFrame(list_measurement, columns=['ID', 'participant_ID', 'measurement_ID', 'analyte', 'time', 'value'])
df_measurement[' index'] = range(1, len(df_measurement) + 1)

#functions to generate contents;
def description_card():
    """

    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Shedding Information Analytics"),
            html.H3("Welcome to the Shedding Hub Dashboard"),
            html.Div(
                id="intro",
                children="Explore the pathogen/biomarker shedding in different human specimens.",
            ),
        ],
    )

def generate_control_card():
    """

    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Select Biomarker"),
            dcc.Dropdown(
                id="biomarker-select",
                options=[{"label": i, "value": i} for i in list_biomarker],
                value="SARS-CoV-2",
            ),
            html.Br(),
            html.P("Select Specimen"),
            dcc.Dropdown(
                id="specimen-select",
                #options=[{"label": i, "value": i} for i in list_specimen],
                #value="stool",
            ),
            html.Br(),
            html.Br(),
            html.P("Select Gene Targets"),
            dcc.Dropdown(
                id="gene-select",
                multi=True,
            ),
            html.Br(),
            html.Div(
                id="reset-btn-outer",
                children=html.Button(id="reset-btn", children="Reset", n_clicks=0),
            ),
        ],
    )

### Initialize the app
app = Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)
app.title = "Shedding Hub Dashboard"

server = app.server

### App layout
app.layout = html.Div(
    id="app-container",
    children=[
        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[html.Img(src=app.get_asset_url("sh_logo.png"))],
        ),
        # Left column
        html.Div(
            id="left-column",
            className="three columns",
            children=[description_card(), generate_control_card()],
        ),
        # Right column
        html.Div(
            id="right-column",
            className="nine columns",
            children=[
                # Patient Volume Heatmap
                html.Div(
                    id="tables",
                    children=[
                        html.B("Data Tables"),
                        html.Hr(),
                        dcc.Tabs([
                            dcc.Tab(label='Participant Information', children=[
                                dash_table.DataTable(
                                    id='table-participant-paging-and-sorting',
                                    columns=[
                                        {'name': i, 'id': i, 'deletable': True} for i in sorted(df_participant.columns)
                                    ],
                                    page_current=0,
                                    page_size=10,
                                    page_action='custom',
                                    sort_action='custom',
                                    sort_mode='single',
                                    sort_by=[]
                                ),
                            ]),
                            dcc.Tab(label='Analyte Information', children=[
                                dash_table.DataTable(
                                    id='table-analyte-paging-and-sorting',
                                    columns=[
                                        {'name': i, 'id': i, 'deletable': True} for i in sorted(df_analyte.columns)
                                    ],
                                    page_current=0,
                                    page_size=10,
                                    page_action='custom',
                                    sort_action='custom',
                                    sort_mode='single',
                                    sort_by=[]
                                ),
                            ]),
                            dcc.Tab(label='Measurement', children=[
                                dash_table.DataTable(
                                    id='table-measurement-paging-and-sorting',
                                    columns=[
                                        {'name': i, 'id': i, 'deletable': True} for i in sorted(df_measurement.columns)
                                    ],
                                    page_current=0,
                                    page_size=10,
                                    page_action='custom',
                                    sort_action='custom',
                                    sort_mode='single',
                                    sort_by=[]
                                ),
                            ]),
                        ]),
                    ],
                ),
                # Patient Wait time by Department
                html.Div(
                    id="plots",
                    children=[
                        html.Hr(),
                        html.Div([
                                html.Div(dcc.Graph(id='scatter_plot_symptom_onset'), className="six columns"),
                                html.Div(dcc.Graph(id='scatter_plot_symptom_onset_ct'), className="six columns"),
                            ], className="row"
                        ),
                        html.Hr(),
                        html.Div([
                                html.Div(dcc.Graph(id='scatter_plot_confirmation'), className="six columns"),
                                html.Div(dcc.Graph(id='scatter_plot_confirmation_ct'), className="six columns"),
                            ], className="row"
                        ),
                        html.Hr(),
                        html.Div([
                                html.Div(dcc.Graph(id='scatter_plot_enrollment'), className="six columns"),
                                html.Div(dcc.Graph(id='scatter_plot_enrollment_ct'), className="six columns"),
                            ], className="row"
                        ),
                    ],
                ),
            ],
        ),
    ],
)

### Calls backs
@callback(
    Output('table-participant-paging-and-sorting', 'data'),
    Input('table-participant-paging-and-sorting', "page_current"),
    Input('table-participant-paging-and-sorting', "page_size"),
    Input('table-participant-paging-and-sorting', 'sort_by'),
)
def update_participant_table(page_current, page_size, sort_by):
    if len(sort_by):
        dff_participant = df_participant.sort_values(
            sort_by[0]['column_id'],
            ascending=sort_by[0]['direction'] == 'asc',
            inplace=False
        )
    else:
        # No sort is applied
        dff_participant = df_participant

    return dff_participant.iloc[
        page_current*page_size:(page_current+ 1)*page_size
    ].to_dict('records')

@callback(
    Output('table-analyte-paging-and-sorting', 'data'),
    Input('table-analyte-paging-and-sorting', "page_current"),
    Input('table-analyte-paging-and-sorting', "page_size"),
    Input('table-analyte-paging-and-sorting', 'sort_by'),
)
def update_analyte_table(page_current, page_size, sort_by):
    if len(sort_by):
        dff_analyte = df_analyte.sort_values(
            sort_by[0]['column_id'],
            ascending=sort_by[0]['direction'] == 'asc',
            inplace=False
        )
    else:
        # No sort is applied
        dff_analyte = df_analyte

    return dff_analyte.iloc[
        page_current*page_size:(page_current+ 1)*page_size
    ].to_dict('records')

@callback(
    Output('table-measurement-paging-and-sorting', 'data'),
    Input('table-measurement-paging-and-sorting', "page_current"),
    Input('table-measurement-paging-and-sorting', "page_size"),
    Input('table-measurement-paging-and-sorting', 'sort_by'),
)
def update_measurement_table(page_current, page_size, sort_by):
    if len(sort_by):
        dff_measurement = df_measurement.sort_values(
            sort_by[0]['column_id'],
            ascending=sort_by[0]['direction'] == 'asc',
            inplace=False
        )
    else:
        # No sort is applied
        dff_measurement = df_measurement

    return dff_measurement.iloc[
        page_current*page_size:(page_current+ 1)*page_size
    ].to_dict('records')

@app.callback(
    [Output('specimen-select', 'options'),
     Output('specimen-select', 'value')],
    Input('biomarker-select', 'value')
)
def update_items_dropdown(selected_biomarker):
    if selected_biomarker:
        items = df_analyte["specimen"][df_analyte["biomarker"]==selected_biomarker].unique()
        return [{'label': item, 'value': item} for item in items], items[0]
    return [], []

@app.callback(
    [Output('gene-select', 'options'),
     Output('gene-select', 'value')],
    Input('biomarker-select', 'value')
)
def update_items_dropdown(selected_biomarker):
    if selected_biomarker:
        items = df_analyte["gene_target"][df_analyte["biomarker"]==selected_biomarker].unique()
        return [{'label': item, 'value': item} for item in items], items
    return [], []

### Create some interactive graphs
@callback(
    Output('scatter_plot_symptom_onset', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="symptom onset") & (df_analyte["unit"]!="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=True, 
                    color="ID", #title=selected_biomarker + " Shedding Data for " + selected_specimen.capitalize() + " Samples", 
                    labels={"time": "Days after Symptom Onset", "value": "Viral Load (gc/mL or gc/gram or gc/swab)", "ID": "Study"})

    fig.update_layout(transition_duration=500, legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

@callback(
    Output('scatter_plot_confirmation', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="confirmation date") & (df_analyte["unit"]!="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=True, 
                    color="ID",
                    labels={"time": "Days after Confirmation", "value": "Viral Load (gc/mL or gc/gram or gc/swab)", "ID": "Study"})

    fig.update_layout(transition_duration=500, legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

@callback(
    Output('scatter_plot_enrollment', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="enrollment") & (df_analyte["unit"]!="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=True, 
                    color="ID", 
                    labels={"time": "Days after Enrollment", "value": "Viral Load (gc/mL or gc/gram or gc/swab)", "ID": "Study"})

    fig.update_layout(transition_duration=500, legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

@callback(
    Output('scatter_plot_symptom_onset_ct', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="symptom onset") & (df_analyte["unit"]=="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=False, 
                    color="ID",
                    labels={"time": "Days after Symptom Onset", "value": "Ct value", "ID": "Study"})

    fig.update_layout(transition_duration=500, yaxis_autorange="reversed",legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

@callback(
    Output('scatter_plot_confirmation_ct', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="confirmation date") & (df_analyte["unit"]=="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=False, 
                    color="ID",
                    labels={"time": "Days after Confirmation", "value": "Ct value", "ID": "Study"})

    fig.update_layout(transition_duration=500, yaxis_autorange="reversed",legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

@callback(
    Output('scatter_plot_enrollment_ct', 'figure'),
    Input('biomarker-select', 'value'),
    Input('specimen-select', 'value'),
    Input('gene-select', 'value'),
    )
def update_figure(selected_biomarker,selected_specimen,selected_gene):
    filtered_df_analyte = df_analyte.loc[(df_analyte["biomarker"]==selected_biomarker) & (df_analyte["specimen"]==selected_specimen) & (df_analyte["gene_target"].isin(selected_gene)) & (df_analyte["reference_event"]=="enrollment") & (df_analyte["unit"]=="cycle threshold")]
    filtered_df_participant = df_participant.loc[df_participant['ID'].isin(filtered_df_analyte['ID'])]
    filtered_df_measurement = df_measurement.loc[(df_measurement['ID']+df_measurement['analyte']).isin(filtered_df_analyte['ID']+filtered_df_analyte['analyte'])]

    fig = px.scatter(filtered_df_measurement, x='time', y='value', log_y=False, 
                    color="ID", 
                    labels={"time": "Days after Enrollment", "value": "Ct value", "ID": "Study"})

    fig.update_layout(transition_duration=500, yaxis_autorange="reversed",legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1)
    )

    return fig

### Run the app
if __name__ == '__main__':
    app.run(host= '0.0.0.0', debug=True) # for app deployment at render.com;
#    app.run(debug=True) # for local development;