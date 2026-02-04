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

from dash import Dash, html, dcc, callback, Output, Input, State, ALL, ctx
import pandas as pd
import json
import sys

# Add the parent directory to path to import shedding_hub
sys.path.insert(0, r"C:\Users\Haili\OneDrive - Emory University\EPI Class\Liuhua Shi RA\Shedding_hub\09072024_Training\Environment\shedding-hub")

# Import shedding_hub package functions
try:
    from shedding_hub import load_dataset
    from shedding_hub.viz import (
        plot_time_course,
        plot_time_courses,
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
                specimens.update(specimen)
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
                specs.update(sp)
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
    # Group datasets by biomarker; assign each dataset to ONE group only (first biomarker)
    pathogen_groups = {}
    assigned = set()
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
        # Assign to first biomarker alphabetically to avoid duplicate IDs
        primary_bm = sorted(bms)[0]
        if ds_id not in assigned:
            pathogen_groups.setdefault(primary_bm, []).append(ds_id)
            assigned.add(ds_id)

    # Build browser sections
    sections = []
    for pathogen in sorted(pathogen_groups.keys()):
        ds_ids = pathogen_groups[pathogen]
        study_buttons = []
        for ds_id in ds_ids:
            study_buttons.append(
                html.Button(
                    ds_id,
                    id={"type": "browser-study-btn", "dataset_id": ds_id},
                    className="browser-study-item",
                    n_clicks=0,
                )
            )
        sections.append(
            html.Div(className="browser-pathogen-group", children=[
                html.H6(pathogen, className="browser-pathogen-header"),
                html.Div(study_buttons, className="browser-study-list"),
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

        # Banner
        create_banner(),

        # Left column - Controls
        html.Div(
            id="left-column",
            className="three columns",
            children=[
                create_description_card(),
                create_dataset_browser(),
            ],
        ),

        # Right column - Tab-based interface
        html.Div(
            id="right-column",
            className="nine columns",
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
)


### Callbacks

# Tab Management Callbacks

@callback(
    Output("new-tab-modal", "style"),
    Output("new-tab-name", "value"),
    Input("create-tab-btn", "n_clicks"),
    Input("cancel-tab-btn", "n_clicks"),
    Input("confirm-tab-btn", "n_clicks"),
    State("new-tab-modal", "style"),
    State("tab-counter", "data"),
    prevent_initial_call=True
)
def toggle_new_tab_modal(create_clicks, cancel_clicks, confirm_clicks, current_style, tab_counter):
    """Show/hide the new tab creation modal and set default tab name"""
    if ctx.triggered_id == "create-tab-btn":
        # Generate default tab name based on current tab count
        default_name = f"Tab {tab_counter + 1}"
        return {"display": "block"}, default_name
    elif ctx.triggered_id in ["cancel-tab-btn", "confirm-tab-btn"]:
        return {"display": "none"}, ""
    return current_style, ""


@callback(
    Output("new-tab-study-select", "multi"),
    Input("new-tab-study-type", "value")
)
def update_study_select_mode(study_type):
    """Enable multi-select for multiple studies, single-select for individual"""
    return study_type == "multiple"


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


def _get_dataset_filter_options(selected_studies):
    """Extract available biomarkers, specimens, and reference events from selected dataset(s)."""
    biomarkers = set()
    specimens = set()
    ref_events = set()

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
                specimens.update(sp)
            elif sp:
                specimens.add(sp)
            ref = a_info.get('reference_event')
            if ref:
                ref_events.add(ref)

    return sorted(biomarkers), sorted(specimens), sorted(ref_events)


def _create_filter_bar(tab_id, filter_prefix, selected_studies=None):
    """Create an inline filter bar for a tab, scoped to the selected dataset(s)."""
    bms, specs, evts = _get_dataset_filter_options(selected_studies)

    # Default to first option for each filter
    default_bm = bms[0] if bms else None
    default_spec = specs[0] if specs else None
    default_evt = evts[0] if evts else None

    return html.Div(
        className="tab-filter-bar",
        children=[
            html.Div(className="tab-filter-item", children=[
                html.Label("Biomarker"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-biomarker", "tab_id": tab_id},
                    options=[{"label": bm, "value": bm} for bm in bms],
                    value=default_bm,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Specimen"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-specimen", "tab_id": tab_id},
                    options=[{"label": sp, "value": sp} for sp in specs],
                    value=default_spec,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Reference Event"),
                dcc.Dropdown(
                    id={"type": f"{filter_prefix}-ref-event", "tab_id": tab_id},
                    options=[{"label": evt, "value": evt} for evt in evts],
                    value=default_evt,
                    placeholder="All",
                ),
            ]),
            html.Div(className="tab-filter-item", children=[
                html.Label("Value Type"),
                dcc.RadioItems(
                    id={"type": f"{filter_prefix}-value-type", "tab_id": tab_id},
                    options=[
                        {"label": "Concentration", "value": "concentration"},
                        {"label": "Ct Values", "value": "ct"},
                    ],
                    value="concentration",
                    className="tab-filter-radio",
                ),
            ]),
        ],
    )


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
                _create_filter_bar(tab_id, filter_prefix, config.get("selected_studies")),
                html.Hr(),
                html.Div(id={"type": "tab-content", "tab_id": tab_id}),
            ],
        )
    else:  # plots
        if study_type == "individual":
            plot_options = [
                {"label": "Time Course Trajectories", "value": "time_course"},
                {"label": "Mean Trajectory", "value": "mean_trajectory"},
                {"label": "Detection Probability", "value": "detection"},
                {"label": "Clearance Curve", "value": "clearance"},
                {"label": "Shedding Heatmap", "value": "heatmap"},
                {"label": "Value Distribution", "value": "distribution"},
            ]
        else:
            plot_options = [
                {"label": "Comparison Time Courses", "value": "time_courses_compare"},
                {"label": "Comparison Detection", "value": "detection_compare"},
                {"label": "Comparison Clearance", "value": "clearance_compare"},
            ]

        return html.Div(
            className="tab-content-wrapper",
            children=[
                header,
                _create_filter_bar(tab_id, filter_prefix, config.get("selected_studies")),
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
    Input("tab-configs", "data"),
)
def update_tab_plots(plot_types, biomarkers, specimens, ref_events, value_types, tab_configs):
    """Update plots in all tabs based on per-tab filters and plot type selection"""
    if not SHEDDING_HUB_AVAILABLE:
        return [html.Div("Shedding Hub package not available", className="error-message")] * max(len(plot_types), 1)

    if not plot_types:
        return []

    # Get plot tabs in the order they appear
    plot_tabs = [(k, v) for k, v in tab_configs.items() if v.get("content_type") == "plots"]

    plot_elements = []
    for idx, plot_type in enumerate(plot_types):
        if idx >= len(plot_tabs):
            plot_elements.append(html.Div("Tab configuration error", className="error-message"))
            continue

        tab_id, config = plot_tabs[idx]
        study_type = config.get("study_type")
        selected_studies = config.get("selected_studies")

        # Per-tab filter values
        biomarker = biomarkers[idx] if idx < len(biomarkers) else None
        specimen = specimens[idx] if idx < len(specimens) else None
        reference_event = ref_events[idx] if idx < len(ref_events) else None
        value_type = value_types[idx] if idx < len(value_types) else "concentration"

        try:
            if study_type == "individual":
                if not selected_studies:
                    plot_element = html.Div("Please select a study in the tab creation", className="error-message")
                elif selected_studies not in datasets:
                    plot_element = html.Div(f"Dataset '{selected_studies}' not found", className="error-message")
                else:
                    dataset = datasets[selected_studies]
                    print(f"Generating plot: {plot_type} for dataset: {selected_studies}")
                    plot_element = generate_individual_plot(
                        dataset, plot_type, biomarker, specimen, reference_event, value_type
                    )
            else:
                if not selected_studies or not isinstance(selected_studies, list):
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
    "time_courses_compare": (
        "Comparison of individual participant shedding trajectories across multiple datasets. "
        "Grid of faceted plots with each column representing a different study and rows "
        "representing different specimen types."
    ),
    "detection_compare": (
        "Comparison of detection probability across multiple studies. "
        "Shows the proportion of positive measurements over time for each study."
    ),
    "clearance_compare": (
        "Comparison of Kaplan-Meier clearance curves across multiple studies. "
        "Shows the proportion of participants still shedding over time for each study."
    ),
}


def generate_individual_plot(dataset, plot_type, biomarker, specimen, reference_event, value_type):
    """Generate plot for individual study - returns html.Img element."""
    kwargs = {}
    if biomarker:
        kwargs['biomarker'] = biomarker
    if specimen:
        kwargs['specimen'] = specimen

    try:
        if plot_type == "time_course":
            # Uses figsize_width_per_specimen and figsize_height
            if value_type:
                kwargs['value'] = value_type
            kwargs['figsize_width_per_specimen'] = 10
            kwargs['figsize_height'] = 6
            mpl_fig = _call_viz_function(plot_time_course, dataset, **kwargs)

        elif plot_type == "mean_trajectory":
            if value_type:
                kwargs['value'] = value_type
            kwargs['figsize'] = (10, 6)
            mpl_fig = _call_viz_function(plot_mean_trajectory, dataset, **kwargs)

        elif plot_type == "detection":
            kwargs['figsize'] = (10, 6)
            mpl_fig = _call_viz_function(plot_detection_probability, dataset, **kwargs)

        elif plot_type == "clearance":
            kwargs['figsize'] = (10, 6)
            mpl_fig = _call_viz_function(plot_clearance_curve, dataset, **kwargs)

        elif plot_type == "heatmap":
            if value_type:
                kwargs['value'] = value_type
            kwargs['figsize'] = (12, 6)
            mpl_fig = _call_viz_function(plot_shedding_heatmap, dataset, **kwargs)

        elif plot_type == "distribution":
            if value_type:
                kwargs['value'] = value_type
            mpl_fig = _call_viz_function(plot_value_distribution_by_time, dataset, **kwargs)

        else:
            return html.Div(f"Unknown plot type: {plot_type}", className="error-message")

        img_src = matplotlib_to_img_src(mpl_fig)
        description = PLOT_DESCRIPTIONS.get(plot_type, "")
        return html.Div([
            html.Img(src=img_src, className="plot-img"),
            html.P(description, className="plot-description"),
        ])

    except Exception as e:
        print(f"Error in generate_individual_plot: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {str(e)}", className="error-message")


def generate_comparison_plot(datasets_list, plot_type, biomarker, specimen, reference_event, value_type):
    """Generate comparison plot for multiple studies - returns html.Img element"""
    kwargs = {}
    if biomarker:
        kwargs['biomarker'] = biomarker
    if specimen:
        kwargs['specimen'] = specimen

    try:
        if plot_type == "time_courses_compare":
            # Uses figsize_width_per_study and figsize_height_per_specimen
            if value_type:
                kwargs['value'] = value_type
            kwargs['figsize_width_per_study'] = 5
            kwargs['figsize_height_per_specimen'] = 4
            mpl_fig = plot_time_courses(datasets_list, **kwargs)

        elif plot_type == "detection_compare":
            n_datasets = len(datasets_list)
            mpl_fig, axes = plt.subplots(n_datasets, 1,
                                         figsize=(10, 5 * n_datasets), sharex=True)
            if n_datasets == 1:
                axes = [axes]

            for idx, dataset in enumerate(datasets_list):
                try:
                    temp_fig = plot_detection_probability(dataset, figsize=(10, 5), **kwargs)
                    temp_ax = temp_fig.gca()
                    for line in temp_ax.get_lines():
                        axes[idx].plot(line.get_xdata(), line.get_ydata(),
                                     label=f"{dataset.get('dataset_id', 'Unknown')}")
                    axes[idx].set_ylabel('Proportion Positive')
                    axes[idx].legend()
                    axes[idx].set_title(dataset.get('dataset_id', 'Unknown'))
                    plt.close(temp_fig)
                except Exception as e:
                    print(f"Error plotting detection for {dataset.get('dataset_id')}: {e}")

            axes[-1].set_xlabel('Time (days)')
            mpl_fig.suptitle('Detection Probability Comparison')
            plt.tight_layout()

        elif plot_type == "clearance_compare":
            n_datasets = len(datasets_list)
            mpl_fig, axes = plt.subplots(n_datasets, 1,
                                         figsize=(10, 5 * n_datasets), sharex=True)
            if n_datasets == 1:
                axes = [axes]

            for idx, dataset in enumerate(datasets_list):
                try:
                    temp_fig = plot_clearance_curve(dataset, figsize=(10, 5), **kwargs)
                    temp_ax = temp_fig.gca()
                    for line in temp_ax.get_lines():
                        axes[idx].plot(line.get_xdata(), line.get_ydata(),
                                     label=f"{dataset.get('dataset_id', 'Unknown')}")
                    axes[idx].set_ylabel('Proportion Still Shedding')
                    axes[idx].legend()
                    axes[idx].set_title(dataset.get('dataset_id', 'Unknown'))
                    plt.close(temp_fig)
                except Exception as e:
                    print(f"Error plotting clearance for {dataset.get('dataset_id')}: {e}")

            axes[-1].set_xlabel('Time (days)')
            mpl_fig.suptitle('Clearance Curve Comparison')
            plt.tight_layout()

        else:
            return html.Div(f"Unknown comparison plot type: {plot_type}", className="error-message")

        img_src = matplotlib_to_img_src(mpl_fig)
        description = PLOT_DESCRIPTIONS.get(plot_type, "")
        return html.Div([
            html.Img(src=img_src, className="plot-img"),
            html.P(description, className="plot-description"),
        ])

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

        biomarker = biomarkers[idx] if idx < len(biomarkers) else None
        specimen = specimens[idx] if idx < len(specimens) else None
        reference_event = ref_events[idx] if idx < len(ref_events) else None
        value_type = value_types[idx] if idx < len(value_types) else "concentration"

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
                if not selected_studies or not isinstance(selected_studies, list):
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


def _dataframe_to_dash_table(df):
    """Convert a pandas DataFrame to a Dash HTML table."""
    # Format numeric values
    formatted_df = df.copy()
    for col in formatted_df.columns:
        formatted_df[col] = formatted_df[col].apply(
            lambda x: f'{x:.2f}' if isinstance(x, (int, float)) and not pd.isna(x) else str(x) if not pd.isna(x) else ''
        )

    # Create table header
    header = html.Thead(
        html.Tr([html.Th(col) for col in formatted_df.columns])
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


# Browser click-to-create-tab callback
@callback(
    Output("main-tabs", "children", allow_duplicate=True),
    Output("tab-configs", "data", allow_duplicate=True),
    Output("tab-counter", "data", allow_duplicate=True),
    Output("main-tabs", "value", allow_duplicate=True),
    Input({"type": "browser-study-btn", "dataset_id": ALL}, "n_clicks"),
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
    app.run(debug=True, use_reloader=False)
