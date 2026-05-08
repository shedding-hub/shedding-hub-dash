"""
Shedding Hub Dashboard - New Version
Using shedding_hub package functions for visualization and statistics
"""

### Import packages
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend before any other matplotlib imports
matplotlib.rcParams['axes.formatter.use_mathtext'] = False
matplotlib.rcParams['axes.formatter.useoffset'] = False
matplotlib.rcParams['text.usetex'] = False

import dash
from dash import Dash, html, dcc, callback, Output, Input, State, ALL, MATCH, ctx
import pandas as pd
import json
import sys

# Import shedding_hub package functions
try:
    from shedding_hub import load_dataset
    from shedding_hub.viz import (
        plot_time_course,
        plot_shedding_heatmap,
        plot_mean_trajectory,
        plot_value_distribution_by_time,
        plot_detection_probability,
        plot_clearance_curve
    )
    from shedding_hub.stats import (
        calc_shedding_summary,
        calc_detection_summary,
        calc_clearance_summary,
        calc_value_summary,
        calc_dataset_summary,
        compare_datasets
    )
    from shedding_hub.shedding_peak import (
        calc_shedding_peak,
        plot_shedding_peaks,
    )
    from shedding_hub.shedding_duration import (
        calc_shedding_duration,
        plot_shedding_durations,
    )
    SHEDDING_HUB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import shedding_hub: {e}")
    SHEDDING_HUB_AVAILABLE = False

import os
import glob
import yaml
from pathlib import Path
import io
import base64
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


### Global Variables
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Data containers (to be populated)
datasets = {}  # Dict of {dataset_id: dataset_dict}
list_biomarker = []
list_specimen = []
list_reference_events = []
dataset_study_map = {}  # Map dataset_id to study info


### Data Loading Functions
def load_data():
    """Load all YAML datasets from the data directory"""
    global datasets, dataset_study_map

    data_dir = Path("data")
    if not data_dir.exists():
        print(f"Warning: Data directory '{data_dir}' not found")
        return

    yaml_files = [f for f in data_dir.glob("*.yaml") if not f.stem.startswith('.')]
    print(f"Loading {len(yaml_files)} datasets...", end=" ", flush=True)

    for yaml_file in yaml_files:
        try:
            # Load YAML file
            with open(yaml_file, 'r', encoding='utf-8') as f:
                dataset = yaml.safe_load(f)

            # Extract dataset ID from filename
            dataset_id = yaml_file.stem
            dataset['dataset_id'] = dataset_id

            # Store dataset
            datasets[dataset_id] = dataset

            # Store study info for dropdown (use dataset_id as label for brevity)
            dataset_study_map[dataset_id] = {
                'label': dataset_id,
                'value': dataset_id
            }

        except Exception as e:
            print(f"\nError loading {yaml_file}: {e}")

    print(f"Done! Loaded {len(datasets)} datasets")


def get_unique_values():
    """Extract unique biomarkers, specimens, and reference events from datasets"""
    global list_biomarker, list_specimen, list_reference_events

    biomarkers = set()
    specimens = set()
    reference_events = set()

    for dataset_id, dataset in datasets.items():
        analytes = dataset.get('analytes', {})
        for analyte_name, analyte_info in analytes.items():
            # Collect biomarkers
            biomarker = analyte_info.get('biomarker')
            if biomarker:
                biomarkers.add(biomarker)

            # Collect specimens
            specimen = analyte_info.get('specimen')
            if isinstance(specimen, list):
                specimens.add("+".join(specimen))
            elif specimen:
                specimens.add(specimen)

            # Collect reference events
            ref_event = analyte_info.get('reference_event')
            if ref_event:
                reference_events.add(ref_event)

    list_biomarker = sorted(list(biomarkers))
    list_specimen = sorted(list(specimens))
    list_reference_events = sorted(list(reference_events))

    print(f"Found {len(list_biomarker)} biomarkers, {len(list_specimen)} specimens, {len(list_reference_events)} reference events")


def create_welcome_overview():
    """Build an overview of all loaded datasets for the welcome page."""
    # Summary counts
    total_participants = 0
    rows = []
    for ds_id in sorted(datasets.keys()):
        ds = datasets[ds_id]
        analytes = ds.get('analytes', {})
        participants = ds.get('participants', [])
        n_participants = len(participants)
        total_participants += n_participants

        # Collect biomarkers and specimens for this dataset
        bms = set()
        specs = set()
        for a_info in analytes.values():
            bm = a_info.get('biomarker')
            if bm:
                bms.add(bm)
            sp = a_info.get('specimen')
            if isinstance(sp, list):
                specs.add("+".join(sp))
            elif sp:
                specs.add(sp)

        # Build DOI link for the study name
        doi = ds.get('doi', '')
        if doi:
            doi_url = doi if doi.startswith('http') else f"https://doi.org/{doi}"
            id_cell = html.Td(html.A(ds_id, href=doi_url, target="_blank"), className="td-bold")
        else:
            id_cell = html.Td(ds_id, className="td-bold")

        rows.append(html.Tr([
            id_cell,
            html.Td(ds.get('title', 'N/A')[:80] + ('...' if len(ds.get('title', '')) > 80 else '')),
            html.Td(', '.join(sorted(bms))),
            html.Td(', '.join(sorted(specs))),
            html.Td(str(n_participants), className="td-center"),
            html.Td(str(len(analytes)), className="td-center"),
        ]))

    overview = html.Div(
        className="welcome-overview",
        children=[
            html.H3("Pathogen Shedding Data Analytics"),
            html.P("Explore viral shedding patterns across different biomarkers, specimens, and time courses. "
                   "Click 'Create New Tab' to start."),

            # Summary cards
            html.Div(
                className="summary-cards",
                children=[
                    _summary_card("Datasets", len(datasets)),
                    _summary_card("Biomarkers", len(list_biomarker)),
                    _summary_card("Specimens", len(list_specimen)),
                    _summary_card("Reference Events", len(list_reference_events)),
                    _summary_card("Total Participants", total_participants),
                ],
            ),

            # Dataset table
            html.H5("Available Datasets"),
            html.Div(
                className="dataset-table-wrapper",
                children=[
                    html.Table(
                        className="dataset-table",
                        children=[
                            html.Thead(html.Tr([
                                html.Th("ID"),
                                html.Th("Title"),
                                html.Th("Biomarker(s)"),
                                html.Th("Specimen(s)"),
                                html.Th("Participants"),
                                html.Th("Analytes"),
                            ])),
                            html.Tbody(rows),
                        ],
                    ),
                ],
            ),
        ],
    )
    return overview


def _summary_card(label, value):
    """Create a small summary card with a number and label."""
    return html.Div(
        className="summary-card",
        children=[
            html.H3(str(value)),
            html.P(label),
        ],
    )


### Dashboard Component Functions
def create_banner():
    """Create the dashboard banner/header"""
    return html.Div(
        id="banner",
        className="banner",
        children=[
            html.Img(src="assets/sh_logo.png"),
        ],
    )


def create_description_card():
    """Create the description and welcome card"""
    return html.Div(
        id="description-card",
        children=[
            html.H5("Shedding Hub Dashboard"),
        ],
    )


def create_dataset_browser():
    """Create a dataset browser grouped by pathogen/biomarker."""
    # Group datasets by all their biomarkers (a dataset may appear under multiple groups)
    pathogen_groups = {}
    for ds_id in sorted(datasets.keys()):
        ds = datasets[ds_id]
        analytes = ds.get('analytes', {})
        bms = set()
        for a_info in analytes.values():
            bm = a_info.get('biomarker')
            if bm:
                bms.add(bm)
        if not bms:
            bms = {"Other"}
        for bm in bms:
            pathogen_groups.setdefault(bm, []).append(ds_id)

    # Build browser sections
    sections = []
    for pathogen in sorted(pathogen_groups.keys()):
        ds_ids = pathogen_groups[pathogen]
        study_buttons = []
        for ds_id in ds_ids:
            study_buttons.append(
                html.Button(
                    ds_id,
                    id={"type": "browser-study-btn", "dataset_id": ds_id, "pathogen": pathogen},
                    className="browser-study-item",
                    n_clicks=0,
                )
            )
        sections.append(
            html.Div(className="browser-pathogen-group", children=[
                html.Div(
                    [html.Span("▶ ", className="collapse-indicator"), pathogen],
                    id={"type": "browser-pathogen-header", "pathogen": pathogen},
                    className="browser-pathogen-header",
                    n_clicks=0,
                ),
                html.Div(
                    study_buttons,
                    id={"type": "browser-study-list", "pathogen": pathogen},
                    className="browser-study-list",
                    style={"display": "none"},
                ),
            ])
        )

    return html.Div(
        id="control-card",
        children=[
            html.Button(
                "＋ New Tab",
                id="create-tab-btn",
                n_clicks=0,
                className="btn-full-width btn-primary",
            ),
            html.Hr(),
            html.H6("Datasets"),
            html.P("Click a study to open it", className="browser-hint"),
            html.Div(
                id="dataset-browser",
                className="dataset-browser",
                children=sections,
            ),
        ],
    )


### Initialize the Dash app
app = Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)
app.title = "Shedding Hub Dashboard"

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <!-- Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-03Z7167J99"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-03Z7167J99');
        </script>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

server = app.server

load_data()
get_unique_values()


### App Layout
app.layout = html.Div(
    id="app-container",
    children=[
        # Hidden stores for tab management
        dcc.Store(id="tab-configs", data={}),  # Store tab configurations
        dcc.Store(id="tab-counter", data=0),   # Counter for tab IDs

        # Modal for creating new tab
        html.Div(
            id="new-tab-modal",
            style={"display": "none"},
            children=[
                html.Div(
                    className="modal-dialog",
                    children=[
                        html.H4("Create New Tab"),
                        html.Hr(),

                        html.P("Tab Name:"),
                        dcc.Input(
                            id="new-tab-name",
                            type="text",
                            placeholder="Enter tab name...",
                            className="modal-input",
                        ),

                        html.P("Study Type:"),
                        dcc.RadioItems(
                            id="new-tab-study-type",
                            options=[
                                {"label": "Individual Study", "value": "individual"},
                                {"label": "Multiple Studies", "value": "multiple"},
                            ],
                            value="individual",
                            className="modal-radio",
                        ),

                        html.P("Content Type:"),
                        dcc.RadioItems(
                            id="new-tab-content-type",
                            options=[
                                {"label": "Summary Statistics", "value": "statistics"},
                                {"label": "Plots/Visualizations", "value": "plots"},
                            ],
                            value="plots",
                            className="modal-radio",
                        ),

                        # Study selection (shown based on study type)
                        html.Div(
                            id="study-selection-container",
                            children=[
                                html.P("Select Study/Studies:"),
                                dcc.Dropdown(
                                    id="new-tab-study-select",
                                    options=[],
                                    multi=False,
                                    placeholder="Select a study...",
                                    className="modal-radio",
                                ),
                            ],
                        ),

                        html.Div(id="new-tab-error-msg",
                                 style={"color": "red", "fontSize": "0.85em", "marginTop": "6px"}),

                        html.Hr(),
                        html.Div(
                            className="modal-footer",
                            children=[
                                html.Button("Cancel", id="cancel-tab-btn", n_clicks=0),
                                html.Button("Create", id="confirm-tab-btn", n_clicks=0,
                                          className="btn-primary"),
                            ],
                        ),
                    ],
                ),
                # Overlay background
                html.Div(className="modal-overlay"),
            ],
        ),

        # Loading overlay — blocks input while callbacks are running
        html.Div(id="loading-overlay", className="loading-overlay"),

        # Plot lightbox
        html.Div(
            id="plot-lightbox",
            className="lightbox-overlay",
            style={"display": "none"},
            children=[
                html.Span("×", id="lightbox-close", className="lightbox-close"),
                html.Img(id="lightbox-img", className="lightbox-img", src=""),
            ],
        ),

        # Two-column layout
        html.Div(
            className="columns-row",
            children=[
                # Left column - Controls
                html.Div(
                    id="left-column",
                    children=[
                        create_description_card(),
                        create_dataset_browser(),
                    ],
                ),

                # Right column - Tab-based interface
                html.Div(
                    id="right-column",
                    children=[
                        html.Div(
                            id="tabs-container",
                            children=[
                                dcc.Tabs(
                                    id="main-tabs",
                                    value="welcome-tab",
                                    children=[
                                        dcc.Tab(
                                            label="Welcome",
                                            value="welcome-tab",
                                            children=[create_welcome_overview()],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


### Callbacks

# Tab Management Callbacks

@callback(
    Output("new-tab-modal", "style"),
    Output("new-tab-name", "value"),
    Output("new-tab-error-msg", "children"),
    Input("create-tab-btn", "n_clicks"),
    Input("cancel-tab-btn", "n_clicks"),
    Input("confirm-tab-btn", "n_clicks"),
    State("new-tab-modal", "style"),
    State("tab-counter", "data"),
    State("new-tab-study-type", "value"),
    State("new-tab-study-select", "value"),
    prevent_initial_call=True
)
def toggle_new_tab_modal(create_clicks, cancel_clicks, confirm_clicks, current_style, tab_counter, study_type, selected_studies):
    """Show/hide the new tab creation modal and set default tab name"""
    if ctx.triggered_id == "create-tab-btn":
        default_name = f"Tab {tab_counter + 1}"
        return {"display": "block"}, default_name, ""
    elif ctx.triggered_id == "cancel-tab-btn":
        return {"display": "none"}, "", ""
    elif ctx.triggered_id == "confirm-tab-btn":
        if study_type == "multiple" and not selected_studies:
            return current_style, dash.no_update, "Please select at least one study."
        return {"display": "none"}, "", ""
    return current_style, "", ""


@callback(
    Output("new-tab-study-select", "multi"),
    Input("new-tab-study-type", "value")
)
def update_study_select_mode(study_type):
    """Enable multi-select for multiple studies, single-select for individual"""
    return study_type == "multiple"


@callback(
    Output("new-tab-name", "value", allow_duplicate=True),
    Input("new-tab-study-select", "value"),
    State("new-tab-study-type", "value"),
    prevent_initial_call=True
)
def auto_name_tab_from_study(selected_study, study_type):
    """Auto-fill tab name with the study ID when a single study is selected."""
    if study_type == "individual" and selected_study:
        return selected_study
    return dash.no_update


@callback(
    Output("main-tabs", "children", allow_duplicate=True),
    Output("tab-configs", "data", allow_duplicate=True),
    Output("main-tabs", "value", allow_duplicate=True),
    Input({"type": "close-tab-btn", "tab_id": ALL}, "n_clicks"),
    State("main-tabs", "children"),
    State("tab-configs", "data"),
    State("main-tabs", "value"),
    prevent_initial_call=True
)
def close_tab(n_clicks_list, current_tabs, tab_configs, current_active_tab):
    """Close a tab when the close button is clicked"""
    # Check if any close button was clicked
    if not any(n_clicks_list) or not ctx.triggered:
        return current_tabs, tab_configs, current_active_tab

    # Get the tab_id of the clicked close button
    triggered_id = ctx.triggered_id
    if not triggered_id or triggered_id == ".":
        return current_tabs, tab_configs, current_active_tab

    tab_id_to_remove = triggered_id["tab_id"]

    # Remove the tab from the configs
    if tab_id_to_remove in tab_configs:
        del tab_configs[tab_id_to_remove]

    # Remove the tab from the tab list
    updated_tabs = [tab for tab in current_tabs if tab.get("props", {}).get("value") != tab_id_to_remove]

    # If we're closing the currently active tab, switch to the Welcome tab
    new_active_tab = current_active_tab
    if current_active_tab == tab_id_to_remove:
        new_active_tab = "welcome-tab"

    return updated_tabs, tab_configs, new_active_tab


@callback(
    Output("main-tabs", "children"),
    Output("tab-configs", "data"),
    Output("tab-counter", "data"),
    Output("main-tabs", "value"),
    Input("confirm-tab-btn", "n_clicks"),
    State("new-tab-name", "value"),
    State("new-tab-study-type", "value"),
    State("new-tab-content-type", "value"),
    State("new-tab-study-select", "value"),
    State("main-tabs", "children"),
    State("tab-configs", "data"),
    State("tab-counter", "data"),
    prevent_initial_call=True
)
def create_new_tab(n_clicks, tab_name, study_type, content_type, selected_studies,
                   current_tabs, tab_configs, tab_counter):
    """Create a new tab with user-specified configuration"""
    if not n_clicks or not tab_name:
        return current_tabs, tab_configs, tab_counter, None
    if study_type == "multiple" and not selected_studies:
        return current_tabs, tab_configs, tab_counter, None

    # Generate new tab ID
    new_tab_id = f"tab-{tab_counter}"
    tab_counter += 1

    # Store tab configuration
    tab_configs[new_tab_id] = {
        "name": tab_name,
        "study_type": study_type,
        "content_type": content_type,
        "selected_studies": selected_studies,
    }

    # Create new tab content based on configuration
    tab_content = create_tab_content(new_tab_id, tab_configs[new_tab_id])

    # Add new tab to existing tabs
    new_tab = dcc.Tab(
        label=tab_name,
        value=new_tab_id,
        children=[tab_content],
    )

    current_tabs.append(new_tab)

    return current_tabs, tab_configs, tab_counter, new_tab_id


def _is_ct_unit(unit):
    """Return True if the unit string indicates a CT (cycle threshold) value."""
    if not unit:
        return False
    unit_lower = str(unit).lower()
    return "cycle threshold" in unit_lower or unit_lower == "ct"


def _get_dataset_filter_options(selected_studies):
    """Extract available biomarkers, specimens, reference events, and value types from selected dataset(s)."""
    biomarkers = set()
    specimens = set()
    ref_events = set()
    has_concentration = False
    has_ct = False

    # Normalize to list
    if isinstance(selected_studies, str):
        study_ids = [selected_studies]
    elif isinstance(selected_studies, list):
        study_ids = selected_studies
    else:
        study_ids = []

    for ds_id in study_ids:
        ds = datasets.get(ds_id, {})
        for a_info in ds.get('analytes', {}).values():
            bm = a_info.get('biomarker')
            if bm:
                biomarkers.add(bm)
            sp = a_info.get('specimen')
            if isinstance(sp, list):
                specimens.add("+".join(sp))
            elif sp:
                specimens.add(sp)
            ref = a_info.get('reference_event')
            if ref:
                ref_events.add(ref)
            unit = a_info.get('unit')
            if _is_ct_unit(unit):
                has_ct = True
            else:
                has_concentration = True

    value_types = []
    if has_concentration:
        value_types.append({"label": "Concentration", "value": "concentration"})
    if has_ct:
        value_types.append({"label": "Ct Values", "value": "ct"})

    return sorted(biomarkers), sorted(specimens), sorted(ref_events), value_types


def _normalize_filter(val):
    """Normalize a multi-select dropdown value to a single value or None.
    Returns the single value if exactly one is selected, else None (no filter)."""
    if isinstance(val, list):
        return val[0] if len(val) == 1 else None
    return val


def _get_individual_plot_combinations(dataset, biomarker_filter, specimen_filter, value_type_filter, ref_event_filter=None):
    """Return sorted list of (biomarker, specimen, value_type, reference_event) tuples that exist
    in the dataset and match the active filter selections."""
    combos = set()
    for a_info in dataset.get('analytes', {}).values():
        bm = a_info.get('biomarker')
        sp = a_info.get('specimen')
        if isinstance(sp, list):
            sp = "+".join(sp)
        unit = a_info.get('unit')
        vt = 'ct' if _is_ct_unit(unit) else 'concentration'
        re = a_info.get('reference_event')
        if bm and sp:
            combos.add((bm, sp, vt, re))

    bm_set = set(biomarker_filter) if isinstance(biomarker_filter, list) else ({biomarker_filter} if biomarker_filter else None)
    sp_set = set(specimen_filter) if isinstance(specimen_filter, list) else ({specimen_filter} if specimen_filter else None)
    re_set = set(ref_event_filter) if isinstance(ref_event_filter, list) else ({ref_event_filter} if ref_event_filter else None)

    filtered = []
    for bm, sp, vt, re in sorted(combos):
        if bm_set and bm not in bm_set:
            continue
        if sp_set and sp not in sp_set:
            continue
        if value_type_filter and vt != value_type_filter:
            continue
        if re_set and re not in re_set:
            continue
        filtered.append((bm, sp, vt, re))
    return filtered


def _create_filter_bar(tab_id, filter_prefix, selected_studies=None, study_type=None):
    """Create an inline filter bar for a tab, scoped to the selected dataset(s)."""
    bms, specs, evts, value_types = _get_dataset_filter_options(selected_studies)

    # Default to all available options selected (except Value Type: first only)
    default_bm = bms if bms else []
    default_spec = specs if specs else []
    default_evt = evts if evts else []
    default_value_type = value_types[0]["value"] if value_types else None

    # For multi-study tabs, show an editable dropdown to add/remove studies
    all_study_ids = sorted(datasets.keys())
    studies_row = None
    if study_type == "multiple" and selected_studies:
        study_list = [selected_studies] if isinstance(selected_studies, str) else selected_studies
        studies_row = html.Div(
            className="tab-filter-studies-row",
            children=[
                html.Label("Selected Studies"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-studies", "tab_id": tab_id},
                    options=[{"label": s, "value": s} for s in all_study_ids],
                    value=study_list,
                    multi=True,
                    placeholder="Select studies...",
                    className="studies-display-dropdown",
                ),
            ],
        )

    filters_row = html.Div(
        className="tab-filter-bar",
        children=[
            html.Div(className="tab-filter-item", children=[
                html.Label("Biomarker"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-biomarker", "tab_id": tab_id},
                    options=[{"label": bm, "value": bm} for bm in bms],
                    value=default_bm,
                    multi=True,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Specimen"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-specimen", "tab_id": tab_id},
                    options=[{"label": sp, "value": sp} for sp in specs],
                    value=default_spec,
                    multi=True,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Reference Event"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-ref-event", "tab_id": tab_id},
                    options=[{"label": evt, "value": evt} for evt in evts],
                    value=default_evt,
                    multi=True,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Value Type"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-value-type", "tab_id": tab_id},
                    options=value_types,
                    value=default_value_type,
                    clearable=False,
                ),
            ]),
        ],
    )

    children = [studies_row, filters_row] if studies_row else [filters_row]
    return html.Div(className="tab-filter-container", children=children)


def create_tab_content(tab_id, config):
    """Generate tab content based on configuration"""
    study_type = config["study_type"]
    content_type = config["content_type"]

    # Common header with close button
    header = html.Div(
        className="tab-header",
        children=[
            html.H4(
                f"{config['name']}{' - Summary Statistics' if content_type == 'statistics' else ''}"
                f"{' - Multi-Study Comparison' if study_type == 'multiple' and content_type == 'plots' else ''}",
            ),
            html.Button(
                "✕ Close Tab",
                id={"type": "close-tab-btn", "tab_id": tab_id},
                n_clicks=0,
                className="btn-close-tab",
            ),
        ],
    )

    # Use different filter prefixes so plot and stats callbacks have matching array lengths
    filter_prefix = "plot-filter" if content_type == "plots" else "stats-filter"

    if content_type == "statistics":
        return html.Div(
            className="tab-content-wrapper",
            children=[
                header,
                _create_filter_bar(tab_id, filter_prefix, config.get("selected_studies"), study_type=study_type),
                html.Hr(),
                html.Div(id={"type": "tab-content", "tab_id": tab_id}),
            ],
        )
    else:  # plots
        if study_type == "individual":
            plot_options = [
                {"label": "Shedding Heatmap", "value": "heatmap"},
                {"label": "Value Distribution", "value": "distribution"},
                {"label": "Time Course Trajectories", "value": "time_course"},
                {"label": "Mean Trajectory", "value": "mean_trajectory"},
                {"label": "Detection Probability", "value": "detection"},
                {"label": "Clearance Curve", "value": "clearance"},
            ]
        else:
            plot_options = [
                {"label": "Shedding Peak Comparison", "value": "peak_compare"},
                {"label": "Shedding Duration Comparison", "value": "duration_compare"},
            ]

        return html.Div(
            className="tab-content-wrapper",
            children=[
                header,
                _create_filter_bar(tab_id, filter_prefix, config.get("selected_studies"), study_type=study_type),
                html.Hr(),

                html.P("Select Plot Type:"),
                dcc.Dropdown(
                    id={"type": "plot-type-select", "tab_id": tab_id},
                    options=plot_options,
                    value=plot_options[0]["value"],
                    className="plot-type-dropdown",
                ),

                html.Div(
                    id={"type": "tab-plot", "tab_id": tab_id},
                    className="plot-container",
                ),
            ],
        )


# Dynamic callbacks for tab content updates
@callback(
    Output({"type": "tab-plot", "tab_id": ALL}, "children"),
    Input({"type": "plot-type-select", "tab_id": ALL}, "value"),
    Input({"type": "plot-filter-biomarker", "tab_id": ALL}, "value"),
    Input({"type": "plot-filter-specimen", "tab_id": ALL}, "value"),
    Input({"type": "plot-filter-ref-event", "tab_id": ALL}, "value"),
    Input({"type": "plot-filter-value-type", "tab_id": ALL}, "value"),
    Input({"type": "plot-filter-studies", "tab_id": ALL}, "value"),
    Input("tab-configs", "data"),
)
def update_tab_plots(plot_types, biomarkers, specimens, ref_events, value_types, studies_inputs, tab_configs):
    """Update plots in all tabs based on per-tab filters and plot type selection"""
    if not SHEDDING_HUB_AVAILABLE:
        return [html.Div("Shedding Hub package not available", className="error-message")] * max(len(plot_types), 1)

    if not plot_types:
        return []

    # Get plot tabs in the order they appear
    plot_tabs = [(k, v) for k, v in tab_configs.items() if v.get("content_type") == "plots"]

    plot_elements = []
    multi_study_tab_idx = 0  # separate counter: studies_inputs only has entries for multi-study tabs
    for idx, plot_type in enumerate(plot_types):
        if idx >= len(plot_tabs):
            plot_elements.append(html.Div("Tab configuration error", className="error-message"))
            continue

        tab_id, config = plot_tabs[idx]
        study_type = config.get("study_type")
        selected_studies = config.get("selected_studies")

        # Value type is always single-select
        value_type = _normalize_filter(value_types[idx] if idx < len(value_types) else None) or "concentration"

        try:
            if study_type == "individual":
                biomarker_filter = biomarkers[idx] if idx < len(biomarkers) else None
                specimen_filter = specimens[idx] if idx < len(specimens) else None
                ref_event_filter = ref_events[idx] if idx < len(ref_events) else None
                if not selected_studies:
                    plot_element = html.Div("Please select a study in the tab creation", className="error-message")
                elif selected_studies not in datasets:
                    plot_element = html.Div(f"Dataset '{selected_studies}' not found", className="error-message")
                else:
                    dataset = datasets[selected_studies]
                    print(f"Generating plot: {plot_type} for dataset: {selected_studies}")
                    plot_element = generate_individual_plot(
                        dataset, plot_type, biomarker_filter, specimen_filter, ref_event_filter, value_type
                    )
            else:
                # Pass raw filter lists to comparison plot; it resolves combinations internally
                biomarker = biomarkers[idx] if idx < len(biomarkers) else None
                specimen = specimens[idx] if idx < len(specimens) else None
                reference_event = ref_events[idx] if idx < len(ref_events) else None
                # Use the live dropdown value directly to avoid race condition with tab-configs.
                # studies_inputs only contains entries for multi-study tabs, so use multi_study_tab_idx
                # rather than idx (which counts all tabs including individual ones).
                selected_studies = studies_inputs[multi_study_tab_idx] if multi_study_tab_idx < len(studies_inputs) else selected_studies
                multi_study_tab_idx += 1
                if isinstance(selected_studies, str):
                    selected_studies = [selected_studies]
                if not selected_studies:
                    plot_element = html.Div("Please select studies in the tab creation", className="error-message")
                else:
                    study_datasets = [datasets[sid] for sid in selected_studies if sid in datasets]
                    if not study_datasets:
                        plot_element = html.Div("No valid datasets found", className="error-message")
                    else:
                        print(f"Generating comparison plot: {plot_type} for {len(study_datasets)} datasets")
                        plot_element = generate_comparison_plot(
                            study_datasets, plot_type, biomarker, specimen, reference_event, value_type
                        )

            plot_elements.append(plot_element)

        except Exception as e:
            print(f"Error generating plot for tab {tab_id}: {e}")
            import traceback
            traceback.print_exc()
            plot_elements.append(html.Div(f"Error: {str(e)}", className="error-message"))

    return plot_elements


def _safe_tight_layout(*args, **kwargs):
    """Wrapper around plt.tight_layout that catches mathtext parsing errors."""
    try:
        _original_tight_layout(*args, **kwargs)
    except (ValueError, Exception):
        pass  # Skip tight_layout if mathtext parsing fails


# Monkey-patch plt.tight_layout so the shedding_hub viz functions don't crash
_original_tight_layout = plt.tight_layout
plt.tight_layout = _safe_tight_layout


def matplotlib_to_img_src(mpl_fig):
    """Convert matplotlib figure to base64 encoded image source."""
    buf = io.BytesIO()
    try:
        mpl_fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    except (ValueError, Exception):
        # Fallback: save without bbox_inches='tight' if mathtext parsing fails
        buf.seek(0)
        buf.truncate()
        mpl_fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(mpl_fig)

    return f'data:image/png;base64,{img_base64}'


def _call_viz_function(func, *args, **kwargs):
    """Safely call a shedding_hub viz function and return the matplotlib figure."""
    return func(*args, **kwargs)


# Descriptions for each plot type (from viz.py docstrings)
PLOT_DESCRIPTIONS = {
    "time_course": (
        "Individual participant shedding trajectories over time. "
        "Faceted line plots showing biomarker measurements for each participant, "
        "organized by specimen type."
    ),
    "mean_trajectory": (
        "Mean/median trajectory with confidence bands across participants. "
        "Shows the central tendency of measurements over time with a shaded band "
        "showing the uncertainty range."
    ),
    "detection": (
        "Detection probability (proportion of positive measurements) over time. "
        "Shows the probability of detecting a positive measurement at each time bin, "
        "with 95% confidence intervals."
    ),
    "clearance": (
        "Kaplan-Meier style clearance curve showing proportion still shedding over time. "
        "Clearance is defined as the time of the last positive measurement for each participant."
    ),
    "heatmap": (
        "Heatmap of shedding intensity over time across participants. "
        "Rows represent participants, columns represent time bins, and color intensity "
        "represents measurement values."
    ),
    "distribution": (
        "Distribution of measurement values at each time bin. "
        "Box plots showing how measurement values are distributed at different time points, "
        "useful for understanding variability in shedding patterns."
    ),
    "peak_compare": (
        "Comparison of shedding peak timing across multiple studies. "
        "Horizontal box plots (min, Q1, median, Q3, max) for each study, "
        "color-coded by specimen type."
    ),
    "duration_compare": (
        "Comparison of shedding duration across multiple studies. "
        "Range bars show min, mean, and max shedding duration for each study, "
        "color-coded by specimen type."
    ),
}


def _make_single_plot(dataset, plot_type, bm, sp, vt, ref_event=None):
    """Generate one matplotlib figure for the given (biomarker, specimen, value_type, ref_event) combo."""
    kwargs = {'biomarker': bm, 'specimen': sp}
    if ref_event:
        kwargs['reference_event'] = ref_event
    if plot_type == "time_course":
        kwargs['value'] = vt
        kwargs['figsize_width_per_specimen'] = 10
        kwargs['figsize_height'] = 6
        kwargs['max_nparticipant'] = 20
        return _call_viz_function(plot_time_course, dataset, **kwargs)
    elif plot_type == "mean_trajectory":
        kwargs['value'] = vt
        kwargs['figsize'] = (10, 6)
        return _call_viz_function(plot_mean_trajectory, dataset, **kwargs)
    elif plot_type == "detection":
        kwargs['figsize'] = (10, 6)
        return _call_viz_function(plot_detection_probability, dataset, **kwargs)
    elif plot_type == "clearance":
        kwargs['figsize'] = (10, 6)
        return _call_viz_function(plot_clearance_curve, dataset, **kwargs)
    elif plot_type == "heatmap":
        kwargs['value'] = vt
        kwargs['figsize'] = (12, 6)
        return _call_viz_function(plot_shedding_heatmap, dataset, **kwargs)
    elif plot_type == "distribution":
        kwargs['value'] = vt
        return _call_viz_function(plot_value_distribution_by_time, dataset, **kwargs)
    else:
        raise ValueError(f"Unknown plot type: {plot_type}")


def generate_individual_plot(dataset, plot_type, biomarker_filter, specimen_filter, ref_event_filter, value_type_filter):
    """Generate one plot per (biomarker, specimen, value_type, reference_event) combination present in the dataset."""
    combos = _get_individual_plot_combinations(dataset, biomarker_filter, specimen_filter, value_type_filter, ref_event_filter)

    if not combos:
        return html.Div("No data matches the selected filters.", className="error-message")

    # Table shows all combinations regardless of value type filter
    all_combos = _get_individual_plot_combinations(dataset, biomarker_filter, specimen_filter, None, ref_event_filter)
    header = html.Tr([html.Th("Biomarker"), html.Th("Specimen"), html.Th("Reference Event"), html.Th("Value Type")])
    rows = [html.Tr([html.Td(bm), html.Td(sp), html.Td(re or ""), html.Td(vt.capitalize())]) for bm, sp, vt, re in all_combos]
    summary = html.Div([
        html.P(f"{len(all_combos)} combination(s) found in this dataset:", className="combo-summary-title"),
        html.Table([header] + rows, className="combo-summary-table"),
    ], className="combo-summary")

    # One plot per combination
    plot_items = []
    for bm, sp, vt, re in combos:
        label = f"{bm}  |  {sp}" + (f"  |  {re}" if re else "") + f"  |  {vt.capitalize()}"
        try:
            mpl_fig = _make_single_plot(dataset, plot_type, bm, sp, vt, ref_event=re)
            img_src = matplotlib_to_img_src(mpl_fig)
            plot_items.append(html.Div([
                html.P(label, className="combo-plot-label"),
                html.Img(src=img_src, className="plot-img"),
            ], className="combo-plot-item"))
        except Exception as e:
            print(f"Error generating plot for ({bm}, {sp}, {vt}, {re}): {e}")
            import traceback
            traceback.print_exc()
            plot_items.append(html.Div([
                html.P(label, className="combo-plot-label"),
                html.Div(f"Error: {str(e)}", className="error-message"),
            ], className="combo-plot-item"))

    description = PLOT_DESCRIPTIONS.get(plot_type, "")
    return html.Div([
        html.Div(plot_items, className="combo-plots-container"),
        html.P(description, className="plot-description"),
        summary,
    ])


def _resolve_filter_list(selected, available):
    """Return the sorted list of values to plot given a filter selection and what exists in the data.
    None or empty list → all available values. String → single-item list. List → intersection with available."""
    available_set = set(available)
    if not selected:
        return sorted(available_set)
    if isinstance(selected, str):
        return [selected] if selected in available_set else sorted(available_set)
    resolved = [v for v in selected if v in available_set]
    return resolved if resolved else sorted(available_set)


def _arrange_plots_in_rows(img_srcs, max_per_row=2):
    """Wrap a list of base64 image srcs into a 2-column grid (same layout as individual plots)."""
    items = [html.Div(html.Img(src=src, className="plot-img"), className="combo-plot-item") for src in img_srcs]
    return [html.Div(items, className="combo-plots-container")]


def _build_comparison_summary(datasets_list, biomarker_filter, specimen_filter, ref_event_filter, value_type_filter):
    """Return a summary div listing unique (study, biomarker, specimen, reference_event, value_type) combos."""
    combos = []
    bm_set = set(biomarker_filter) if isinstance(biomarker_filter, list) else ({biomarker_filter} if biomarker_filter else None)
    sp_set = set(specimen_filter) if isinstance(specimen_filter, list) else ({specimen_filter} if specimen_filter else None)
    re_set = set(ref_event_filter) if isinstance(ref_event_filter, list) else ({ref_event_filter} if ref_event_filter else None)

    for dataset in datasets_list:
        study = dataset.get('dataset_id', '')
        for a_info in dataset.get('analytes', {}).values():
            bm = a_info.get('biomarker')
            sp = a_info.get('specimen')
            if isinstance(sp, list):
                sp = "+".join(sp)
            unit = a_info.get('unit')
            vt = 'ct' if _is_ct_unit(unit) else 'concentration'
            re = a_info.get('reference_event')
            if not bm or not sp:
                continue
            if bm_set and bm not in bm_set:
                continue
            if sp_set and sp not in sp_set:
                continue
            if re_set and re not in re_set:
                continue
            if value_type_filter and vt != value_type_filter:
                continue
            combos.append((study, bm, sp, re or '', vt))

    combos = sorted(set(combos))
    if not combos:
        return None

    header = html.Tr([html.Th("Study"), html.Th("Biomarker"), html.Th("Specimen"), html.Th("Reference Event"), html.Th("Value Type")])
    rows = [html.Tr([html.Td(s), html.Td(bm), html.Td(sp), html.Td(re), html.Td(vt.capitalize())]) for s, bm, sp, re, vt in combos]
    return html.Div([
        html.P(f"{len(combos)} combination(s) across selected studies:", className="combo-summary-title"),
        html.Table([header] + rows, className="combo-summary-table"),
    ], className="combo-summary")


def generate_comparison_plot(datasets_list, plot_type, biomarker, specimen, reference_event, value_type):
    """Generate comparison plots for multiple studies, one subplot per filter combination."""
    try:
        if plot_type == "peak_compare":
            dfs = []
            for dataset in datasets_list:
                try:
                    df = calc_shedding_peak(dataset, output='summary')
                    if not df.empty:
                        dfs.append(df)
                except Exception as e:
                    print(f"Error calculating shedding peak for {dataset.get('dataset_id')}: {e}")

            if not dfs:
                return html.Div("No valid shedding peak data found for selected studies.", className="error-message")

            combined_df = pd.concat(dfs, ignore_index=True)

            # Resolve each filter to the list of values to iterate over
            bm_list = _resolve_filter_list(biomarker, combined_df['biomarker'].dropna().unique())
            # Resolve reference events per biomarker to avoid non-existent combinations
            existing_combos = set(zip(combined_df['biomarker'], combined_df['reference_event']))

            img_srcs = []
            for bm in bm_list:
                bm_ref_events = [ref for (b, ref) in existing_combos if b == bm]
                ref_list = _resolve_filter_list(reference_event, bm_ref_events)
                for ref_evt in ref_list:
                    if (bm, ref_evt) not in existing_combos:
                        continue
                    try:
                        mpl_fig = plot_shedding_peaks(combined_df, min_nparticipant=1, biomarker=bm, reference_event=ref_evt)
                        img_srcs.append(matplotlib_to_img_src(mpl_fig))
                    except Exception as e:
                        print(f"Skipping peak plot for biomarker={bm}, ref_event={ref_evt}: {e}")

            if not img_srcs:
                return html.Div("No data to display for the selected filters.", className="error-message")

            description = PLOT_DESCRIPTIONS.get(plot_type, "")
            summary = _build_comparison_summary(datasets_list, biomarker, specimen, reference_event, None)
            children = _arrange_plots_in_rows(img_srcs) + [html.P(description, className="plot-description")]
            if summary:
                children.append(summary)
            return html.Div(children)

        elif plot_type == "duration_compare":
            dfs = []
            for dataset in datasets_list:
                try:
                    df = calc_shedding_duration(dataset, output='summary')
                    if not df.empty:
                        dfs.append(df)
                except Exception as e:
                    print(f"Error calculating shedding duration for {dataset.get('dataset_id')}: {e}")

            if not dfs:
                return html.Div("No valid shedding duration data found for selected studies.", className="error-message")

            combined_df = pd.concat(dfs, ignore_index=True)

            bm_list = _resolve_filter_list(biomarker, combined_df['biomarker'].dropna().unique())

            img_srcs = []
            for bm in bm_list:
                try:
                    mpl_fig = plot_shedding_durations(combined_df, biomarker=bm)
                    img_srcs.append(matplotlib_to_img_src(mpl_fig))
                except Exception as e:
                    print(f"Skipping duration plot for biomarker={bm}: {e}")

            if not img_srcs:
                return html.Div("No data to display for the selected filters.", className="error-message")

            description = PLOT_DESCRIPTIONS.get(plot_type, "")
            summary = _build_comparison_summary(datasets_list, biomarker, specimen, reference_event, None)
            children = _arrange_plots_in_rows(img_srcs) + [html.P(description, className="plot-description")]
            if summary:
                children.append(summary)
            return html.Div(children)

        else:
            return html.Div(f"Unknown comparison plot type: {plot_type}", className="error-message")

    except Exception as e:
        print(f"Error in generate_comparison_plot: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {str(e)}", className="error-message")


@callback(
    Output({"type": "tab-content", "tab_id": ALL}, "children"),
    Input({"type": "stats-filter-biomarker", "tab_id": ALL}, "value"),
    Input({"type": "stats-filter-specimen", "tab_id": ALL}, "value"),
    Input({"type": "stats-filter-ref-event", "tab_id": ALL}, "value"),
    Input({"type": "stats-filter-value-type", "tab_id": ALL}, "value"),
    Input("tab-configs", "data"),
)
def update_tab_statistics(biomarkers, specimens, ref_events, value_types, tab_configs):
    """Update statistics tables in all statistics tabs"""
    stats_tabs = [(k, v) for k, v in tab_configs.items() if v.get("content_type") == "statistics"]

    if not SHEDDING_HUB_AVAILABLE:
        return [html.Div("Shedding Hub package not available")] * max(len(biomarkers), 1)

    if not biomarkers:
        return []

    contents = []
    for idx, (tab_id, config) in enumerate(stats_tabs):
        study_type = config.get("study_type")
        selected_studies = config.get("selected_studies")

        biomarker = _normalize_filter(biomarkers[idx] if idx < len(biomarkers) else None)
        specimen = _normalize_filter(specimens[idx] if idx < len(specimens) else None)
        reference_event = _normalize_filter(ref_events[idx] if idx < len(ref_events) else None)
        value_type = _normalize_filter(value_types[idx] if idx < len(value_types) else None) or "concentration"

        try:
            if study_type == "individual":
                if not selected_studies:
                    content = html.Div("Please select a study in the tab creation")
                elif selected_studies not in datasets:
                    content = html.Div(f"Dataset '{selected_studies}' not found")
                else:
                    dataset = datasets[selected_studies]
                    print(f"Generating statistics for dataset: {selected_studies}")
                    content = generate_individual_statistics(
                        dataset, biomarker, specimen, reference_event, value_type
                    )
            else:
                if isinstance(selected_studies, str):
                    selected_studies = [selected_studies]
                if not selected_studies:
                    content = html.Div("Please select studies in the tab creation")
                else:
                    study_datasets = [datasets[sid] for sid in selected_studies if sid in datasets]
                    if not study_datasets:
                        content = html.Div("No valid datasets found")
                    else:
                        print(f"Generating comparison statistics for {len(study_datasets)} datasets")
                        content = generate_comparison_statistics(
                            study_datasets, biomarker, specimen, reference_event, value_type
                        )

            contents.append(content)

        except Exception as e:
            print(f"Error generating statistics for tab {tab_id}: {e}")
            import traceback
            traceback.print_exc()
            contents.append(html.Div(f"Error: {str(e)}"))

    return contents


@callback(
    Output("tab-configs", "data", allow_duplicate=True),
    Input({"type": "plot-filter-studies", "tab_id": ALL}, "value"),
    Input({"type": "stats-filter-studies", "tab_id": ALL}, "value"),
    State({"type": "plot-filter-studies", "tab_id": ALL}, "id"),
    State({"type": "stats-filter-studies", "tab_id": ALL}, "id"),
    State("tab-configs", "data"),
    prevent_initial_call=True,
)
def sync_studies_to_tab_configs(plot_studies, stats_studies, plot_ids, stats_ids, tab_configs):
    """Keep tab-configs in sync when the studies filter is changed interactively."""
    for i, sid in enumerate(plot_ids or []):
        tab_id = sid["tab_id"]
        if tab_id in tab_configs and i < len(plot_studies):
            tab_configs[tab_id]["selected_studies"] = plot_studies[i] or []
    for i, sid in enumerate(stats_ids or []):
        tab_id = sid["tab_id"]
        if tab_id in tab_configs and i < len(stats_studies):
            tab_configs[tab_id]["selected_studies"] = stats_studies[i] or []
    return tab_configs


@callback(
    Output({"type": "plot-filter-biomarker", "tab_id": MATCH}, "options"),
    Output({"type": "plot-filter-biomarker", "tab_id": MATCH}, "value"),
    Output({"type": "plot-filter-specimen", "tab_id": MATCH}, "options"),
    Output({"type": "plot-filter-specimen", "tab_id": MATCH}, "value"),
    Output({"type": "plot-filter-ref-event", "tab_id": MATCH}, "options"),
    Output({"type": "plot-filter-ref-event", "tab_id": MATCH}, "value"),
    Input({"type": "plot-filter-studies", "tab_id": MATCH}, "value"),
    prevent_initial_call=True,
)
def update_plot_filters_on_studies_change(selected_studies):
    """Refresh biomarker/specimen/event filter options when studies selection changes."""
    bms, specs, evts, _ = _get_dataset_filter_options(selected_studies or [])
    return (
        [{"label": bm, "value": bm} for bm in bms], bms,
        [{"label": sp, "value": sp} for sp in specs], specs,
        [{"label": evt, "value": evt} for evt in evts], evts,
    )


@callback(
    Output({"type": "stats-filter-biomarker", "tab_id": MATCH}, "options"),
    Output({"type": "stats-filter-biomarker", "tab_id": MATCH}, "value"),
    Output({"type": "stats-filter-specimen", "tab_id": MATCH}, "options"),
    Output({"type": "stats-filter-specimen", "tab_id": MATCH}, "value"),
    Output({"type": "stats-filter-ref-event", "tab_id": MATCH}, "options"),
    Output({"type": "stats-filter-ref-event", "tab_id": MATCH}, "value"),
    Input({"type": "stats-filter-studies", "tab_id": MATCH}, "value"),
    prevent_initial_call=True,
)
def update_stats_filters_on_studies_change(selected_studies):
    """Refresh biomarker/specimen/event filter options when studies selection changes."""
    bms, specs, evts, _ = _get_dataset_filter_options(selected_studies or [])
    return (
        [{"label": bm, "value": bm} for bm in bms], bms,
        [{"label": sp, "value": sp} for sp in specs], specs,
        [{"label": evt, "value": evt} for evt in evts], evts,
    )


def _dataframe_to_dash_table(df):
    """Convert a pandas DataFrame to a Dash HTML table."""
    # Format numeric values
    formatted_df = df.copy()
    for col in formatted_df.columns:
        formatted_df[col] = formatted_df[col].apply(
            lambda x: str(int(x)) if isinstance(x, (int, float)) and not pd.isna(x) and float(x) == int(x)
                      else f'{x:.2f}' if isinstance(x, (int, float)) and not pd.isna(x)
                      else str(x) if not pd.isna(x) else ''
        )

    # Create table header with sortable columns
    header = html.Thead(
        html.Tr([html.Th(col, className="sortable-th") for col in formatted_df.columns])
    )

    # Create table body
    rows = []
    for _, row in formatted_df.iterrows():
        rows.append(html.Tr([html.Td(row[col]) for col in formatted_df.columns]))
    body = html.Tbody(rows)

    return html.Table([header, body], className="stats-table")


def generate_individual_statistics(dataset, biomarker, specimen, reference_event, value_type):
    """Generate statistics table for individual study"""
    try:
        # Get dataset summary
        dataset_summary = calc_dataset_summary(dataset)

        # Get shedding summary
        kwargs = {}
        if biomarker:
            kwargs['biomarker'] = biomarker
        if specimen:
            kwargs['specimen'] = specimen

        shedding_summary = calc_shedding_summary(dataset, **kwargs)

        # Convert shedding summary to DataFrame and then to Dash table
        shedding_df = pd.DataFrame(shedding_summary)
        shedding_table = _dataframe_to_dash_table(shedding_df)

        # Create display
        content = html.Div([
            html.H5("Dataset Overview"),
            html.P(f"Dataset ID: {dataset_summary['dataset_id']}"),
            html.P(f"Title: {dataset_summary.get('title', 'N/A')}"),
            html.P(f"Participants: {dataset_summary['n_participants']}"),
            html.P(f"Measurements: {dataset_summary['n_measurements']}"),
            html.P(f"Biomarkers: {', '.join(dataset_summary['biomarkers'])}"),
            html.P(f"Specimens: {', '.join(dataset_summary['specimens'])}"),

            html.Hr(),
            html.H5("Shedding Summary"),
            html.Div(shedding_table, className="stats-table-wrapper")
        ])

        return content

    except Exception as e:
        print(f"Error in generate_individual_statistics: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {str(e)}")


def generate_comparison_statistics(datasets_list, biomarker, specimen, reference_event, value_type):
    """Generate comparison statistics for multiple studies"""
    try:
        # Prepare arguments
        kwargs = {}
        if biomarker:
            kwargs['biomarker'] = biomarker
        if specimen:
            kwargs['specimen'] = specimen
        if value_type:
            kwargs['value'] = value_type

        # Compare datasets
        comparison = compare_datasets(datasets_list, **kwargs)

        # Convert comparison to DataFrame and then to Dash table
        comparison_df = pd.DataFrame(comparison)
        comparison_table = _dataframe_to_dash_table(comparison_df)

        # Create display
        content = html.Div([
            html.H5("Multi-Study Comparison"),
            html.P(f"Comparing {len(datasets_list)} studies"),
            html.P(f"Filters: Biomarker={biomarker or 'All'}, Specimen={specimen or 'All'}, Value Type={value_type or 'All'}"),

            html.Hr(),
            html.Div(comparison_table, className="stats-table-wrapper")
        ])

        return content

    except Exception as e:
        print(f"Error in generate_comparison_statistics: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {str(e)}")


# Study list for modal
@callback(
    Output("new-tab-study-select", "options"),
    Input("new-tab-modal", "style")
)
def populate_study_list(modal_style):
    """Populate the study list in the new tab modal"""
    return [dataset_study_map[ds_id] for ds_id in sorted(dataset_study_map.keys())]


# Toggle biomarker section visibility callback
@callback(
    Output({"type": "browser-study-list", "pathogen": ALL}, "style"),
    Output({"type": "browser-pathogen-header", "pathogen": ALL}, "children"),
    Input({"type": "browser-pathogen-header", "pathogen": ALL}, "n_clicks"),
    State({"type": "browser-study-list", "pathogen": ALL}, "style"),
    State({"type": "browser-pathogen-header", "pathogen": ALL}, "children"),
    prevent_initial_call=True
)
def toggle_biomarker_section(n_clicks_list, current_styles, current_children):
    """Toggle visibility of dataset list when biomarker header is clicked."""
    if not any(n_clicks_list) or not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise dash.exceptions.PreventUpdate

    clicked_pathogen = triggered_id["pathogen"]

    # Get list of all pathogens in order
    pathogens = [match["id"]["pathogen"] for match in ctx.inputs_list[0]]

    new_styles = []
    new_children = []

    for i, pathogen in enumerate(pathogens):
        current_style = current_styles[i] or {}
        current_child = current_children[i]

        if pathogen == clicked_pathogen:
            # Toggle this section
            is_hidden = current_style.get("display") == "none"
            if is_hidden:
                new_styles.append({"display": "block"})
                # Update indicator to ▼ (expanded)
                new_children.append([html.Span("▼ ", className="collapse-indicator"), pathogen])
            else:
                new_styles.append({"display": "none"})
                # Update indicator to ▶ (collapsed)
                new_children.append([html.Span("▶ ", className="collapse-indicator"), pathogen])
        else:
            # Keep current state
            new_styles.append(current_style)
            new_children.append(current_child)

    return new_styles, new_children


# Browser click-to-create-tab callback
@callback(
    Output("main-tabs", "children", allow_duplicate=True),
    Output("tab-configs", "data", allow_duplicate=True),
    Output("tab-counter", "data", allow_duplicate=True),
    Output("main-tabs", "value", allow_duplicate=True),
    Input({"type": "browser-study-btn", "dataset_id": ALL, "pathogen": ALL}, "n_clicks"),
    State("main-tabs", "children"),
    State("tab-configs", "data"),
    State("tab-counter", "data"),
    prevent_initial_call=True
)
def browser_create_tab(n_clicks_list, current_tabs, tab_configs, tab_counter):
    """Create a new plot tab when a dataset is clicked in the browser."""
    if not any(n_clicks_list) or not ctx.triggered:
        return current_tabs, tab_configs, tab_counter, None

    triggered_id = ctx.triggered_id
    if not triggered_id or triggered_id == ".":
        return current_tabs, tab_configs, tab_counter, None

    ds_id = triggered_id["dataset_id"]

    new_tab_id = f"tab-{tab_counter}"
    tab_counter += 1

    tab_configs[new_tab_id] = {
        "name": ds_id,
        "study_type": "individual",
        "content_type": "plots",
        "selected_studies": ds_id,
    }

    tab_content = create_tab_content(new_tab_id, tab_configs[new_tab_id])
    new_tab = dcc.Tab(label=ds_id, value=new_tab_id, children=[tab_content])
    current_tabs.append(new_tab)

    return current_tabs, tab_configs, tab_counter, new_tab_id




### Run the app
if __name__ == '__main__':
    # Run the app (data already loaded during initialization)
    app.run(host= '0.0.0.0', debug=True, use_reloader=False)
