from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# Load Dataset with error handling
file_path = 'Songkhla_L2_with_Enhanced_Data.csv'  # Relative path for Render deployment
try:
    # Load dataset with enhanced handling for malformed rows
    data = pd.read_csv(
        file_path,
        sep=',',  # Explicit delimiter
        quotechar='"',  # Handle quoted strings
        engine='python',  # Use the Python engine for more flexible parsing
        on_bad_lines='skip'  # Skip problematic rows
    )
    print("Dataset loaded successfully.")
except pd.errors.ParserError as e:
    print("ParserError while loading the dataset:", e)
    exit()
except Exception as e:
    print("Unexpected error while loading the dataset:", e)
    exit()

# Constants for weights
W1, W2, W3, W4, W5 = 0.40, 0.25, 0.20, 0.05, 0.10

# Preprocessing data
try:
    # Calculate normalized values for each factor
    data['H'] = data['Household'] / data['Household'].max()
    data['I'] = data['Install'] / data['Install'].max()
    data['1-C'] = 1 - (data['Churn'] / data['Port Use']).clip(upper=1)  # Clip C to max 1
    data['M'] = data['Market Share True (%)'] / data['Market Share True (%)'].max()
    data['S'] = data['True Speed'].apply(lambda x: float(x.split()[0]) / 1000)  # Convert speed to numeric

    # Calculate Potential Score
    data['Potential Score'] = (
        W1 * data['H'] +
        W2 * data['I'] +
        W3 * data['1-C'] +
        W4 * data['M'] +
        W5 * data['S']
    )

    # Normalize Potential Score to 0-100%
    data['Potential Score'] = (data['Potential Score'] / data['Potential Score'].max()) * 100

except Exception as e:
    print("Error during preprocessing:", e)
    exit()

# Create Dash App
app = Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("TOL Sales Potential and Market Share Insights for South", style={'textAlign': 'center'}),

    # Filters
    html.Div([
        html.Label("Select Province:"),
        dcc.Dropdown(
            id='province-filter',
            options=[{'label': province, 'value': province} for province in data['Province'].unique()],
            placeholder="Select Province",
        ),
        html.Label("Select District:"),
        dcc.Dropdown(
            id='district-filter',
            placeholder="Select District",
        ),
        html.Label("Select Sub-district:"),
        dcc.Dropdown(
            id='subdistrict-filter',
            placeholder="Select Sub-district",
        ),
        html.Label("Select Happy Block:"),
        dcc.Dropdown(
            id='happyblock-filter',
            placeholder="Select Happy Block",
        ),
        html.Label("Net Add Filter:"),
        dcc.RangeSlider(
            id='net-add-slider',
            min=data['Net Add'].min(), max=data['Net Add'].max(), step=1,
            marks={i: str(i) for i in range(int(data['Net Add'].min()), int(data['Net Add'].max())+1, 10)},
            value=[data['Net Add'].min(), data['Net Add'].max()]
        ),
        html.Label("Potential Score Range:"),
        dcc.RangeSlider(
            id='potential-score-slider',
            min=0, max=100, step=1,
            marks={i: f"{i}%" for i in range(0, 101, 10)},
            value=[0, 100]
        ),
        html.Label("Port Utilization Range:"),
        dcc.RangeSlider(
            id='port-utilization-slider',
            min=0, max=100, step=1,
            marks={i: str(i) for i in range(0, 101, 10)},
            value=[0, 100]
        ),
        html.Label("Market Share True (%) Range:"),
        dcc.RangeSlider(
            id='market-share-true-slider',
            min=0, max=100, step=1,
            marks={i: str(i) for i in range(0, 101, 10)},
            value=[0, 100]
        ),
    ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),

    # Map Display
    dcc.Graph(id='map', style={'width': '65%', 'display': 'inline-block'})
])

# Callbacks for Filters
@app.callback(
    Output('district-filter', 'options'),
    Input('province-filter', 'value')
)
def update_district_filter(selected_province):
    if selected_province:
        filtered = data[data['Province'] == selected_province]
        return [{'label': district, 'value': district} for district in filtered['District'].unique()]
    return []

@app.callback(
    Output('subdistrict-filter', 'options'),
    [Input('province-filter', 'value'),
     Input('district-filter', 'value')]
)
def update_subdistrict_filter(selected_province, selected_district):
    filtered = data.copy()
    if selected_province:
        filtered = filtered[filtered['Province'] == selected_province]
    if selected_district:
        filtered = filtered[filtered['District'] == selected_district]
    return [{'label': subdistrict, 'value': subdistrict} for subdistrict in filtered['Sub-district'].unique()]

@app.callback(
    Output('happyblock-filter', 'options'),
    [Input('province-filter', 'value'),
     Input('district-filter', 'value'),
     Input('subdistrict-filter', 'value')]
)
def update_happyblock_filter(selected_province, selected_district, selected_subdistrict):
    filtered = data.copy()
    if selected_province:
        filtered = filtered[filtered['Province'] == selected_province]
    if selected_district:
        filtered = filtered[filtered['District'] == selected_district]
    if selected_subdistrict:
        filtered = filtered[filtered['Sub-district'] == selected_subdistrict]
    return [{'label': happy_block, 'value': happy_block} for happy_block in filtered['Happy Block'].unique()]

@app.callback(
    Output('map', 'figure'),
    [Input('province-filter', 'value'),
     Input('district-filter', 'value'),
     Input('subdistrict-filter', 'value'),
     Input('happyblock-filter', 'value'),
     Input('net-add-slider', 'value'),
     Input('potential-score-slider', 'value'),
     Input('port-utilization-slider', 'value'),
     Input('market-share-true-slider', 'value')]
)
def update_map(selected_province, selected_district, selected_subdistrict, selected_happyblock,
               net_add_range, potential_range, utilization_range, market_share_range):
    # Filter Data
    filtered_data = data.copy()
    if selected_province:
        filtered_data = filtered_data[filtered_data['Province'] == selected_province]
    if selected_district:
        filtered_data = filtered_data[filtered_data['District'] == selected_district]
    if selected_subdistrict:
        filtered_data = filtered_data[filtered_data['Sub-district'] == selected_subdistrict]
    if selected_happyblock:
        filtered_data = filtered_data[filtered_data['Happy Block'] == selected_happyblock]
    filtered_data = filtered_data[
        (filtered_data['Net Add'] >= net_add_range[0]) & 
        (filtered_data['Net Add'] <= net_add_range[1]) &
        (filtered_data['Potential Score'] >= potential_range[0]) & 
        (filtered_data['Potential Score'] <= potential_range[1]) &
        (filtered_data['Port Utilization (%)'] >= utilization_range[0]) &
        (filtered_data['Port Utilization (%)'] <= utilization_range[1]) &
        (filtered_data['Market Share True (%)'] >= market_share_range[0]) &
        (filtered_data['Market Share True (%)'] <= market_share_range[1])
    ]
    
    # Create Map
    fig = px.scatter_mapbox(
        filtered_data,
        lat="Latitude",
        lon="Longitude",
        size="Household",
        color="Potential Score",
        hover_name="Sub-district",
        hover_data={
            "Province": True,
            "District": True,
            "Sub-district": True,
            "Happy Block": True,
            "L2": True,
            "Port Use": True,
            "Port Available": True,
            "Market Share AIS (%)": True,
            "Market Share 3BB (%)": True,
            "Market Share NT (%)": True,
            "Market Share True (%)": True,
            "Install": True,
            "Churn": True,
            "% Churn": True,
            "Net Add": True,
        },
        color_continuous_scale=["red", "green"],
        title="Potential Score and Market Share Map",
        mapbox_style="open-street-map",
        zoom=9
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

# Run App
if __name__ == '__main__':
    app.run_server(debug=True)
