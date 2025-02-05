### Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import yaml
import fsspec, glob, re
from pathlib import Path

### Customized Functions
# return unknown for variables not in yaml
def key_missing(x,key):
    try:
        return x[key]
    except KeyError:
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
fs = fsspec.filesystem("github", org="shedding-hub", repo="shedding-hub")
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
        list_analyte.append([re.split(r'[\\.]+', list_file[df])[1],
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

### Initialize the app
app = Dash(__name__)
server = app.server

### App layout
app.layout = [
    html.Div(children='Shedding Hub - Analytes Summarization'),
    html.Hr(),
    dcc.RadioItems(options=['biomarker', 'specimen', 'reference_event'], value='biomarker', inline=True, id='controls-and-radio-item'),
    dash_table.DataTable(data=df_analyte.to_dict('records'), page_size=10),
    dcc.Graph(figure={}, id='controls-and-graph')
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
    app.run(host= '0.0.0.0', debug=True)