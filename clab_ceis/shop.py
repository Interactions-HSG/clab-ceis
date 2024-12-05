from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output
import ceis_data  # Assuming ceis_data.py is available and correctly implemented
import plotly.graph_objects as go
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd



# Initialize Dash App and CeisData
app = Dash(__name__, suppress_callback_exceptions=True)
data = ceis_data.CeisData()  # Initialize your CeisData instance
SPARQL_ENDPOINT = "http://localhost:7200/repositories/clab-ceis"



# Home Page Layout
def home_page():
    return html.Div(
        className="wrapper",
        children=[
            html.Header(
                html.H1("Welcome to Our Clothing Order Website", className="header-title"),
                className="card"
            ),
            html.Div(
                className="card",
                children=[
                    html.H2("Order a Skirt or a Top"),
                    html.P("Select the type of clothing you want to order:"),
                    html.Div(
                        className="order-form",
                        children=[
                            dcc.Link(
                                href="/skirt",
                                children=html.Div(
                                    className="product",
                                    children=[
                                        html.Img(
                                            src=app.get_asset_url("skirt.jpg"),
                                            alt="Skirt",
                                            className="product-image"
                                        ),
                                        html.Span("Skirt", className="product-label"),
                                    ],
                                ),
                            ),
                            dcc.Link(
                                href="/top",
                                children=html.Div(
                                    className="product",
                                    children=[
                                        html.Img(
                                            src=app.get_asset_url("top.jpg"),
                                            alt="Top",
                                            className="product-image"
                                        ),
                                        html.Span("Top", className="product-label"),
                                    ],
                                ),
                            ),
                        ],
                        style={"display": "flex", "gap": "20px"},
                    ),
                ],
            ),
            html.Footer(
                "© 2024 CeisShop. All rights reserved.",
                className="footer"
            ),
        ]
    )
# Skirt Page Layout
def skirt_page():
    return html.Div(
        className="product-detail",
        children=[
            html.H1("Skirt", className="product-title"),
            html.Div(
                className="product-content",
                children=[
                    html.Div(
                        className="product-image",
                        children=html.Img(
                            src=app.get_asset_url("skirt.jpg"),
                            alt="Skirt",
                            style={"width": "100%", "border-radius": "8px"},
                        )
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.P(
                                "This is a beautiful Skirt, perfect for any occasion. "
                                "Made with high-quality materials, this Skirt will make you look stunning.",
                                style={"font-size": "18px"},
                            ),
                            # Button to trigger SPARQL query
                            html.Button("Fetch Skirt Data", id="fetch-skirt-data"),
                            # DataTable to display SPARQL results
                            dash_table.DataTable(
                                id="skirt-data-table",
                                columns=[
                                    {"name": "Recipe", "id": "recipe", "presentation": "markdown"},
                                    {"name": "Fabric Block Design", "id": "fabricBlockDesign"},
                                    {"name": "Required Amount", "id": "requiredAmount"},
                                ],
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                    "margin-top": "20px",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "5px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=5,
                            ),

                        ],
                    ),
                ],
                style={"display": "flex", "gap": "20px"},
            ),
            dcc.Link("Back to Home", href="/", className="back-link"),
        ],
    )
# Top Page Layout
def top_page():
    return html.Div(
        className="product-detail",
        children=[
            html.H1("Top", className="product-title"),
            html.Div(
                className="product-content",
                children=[
                    html.Div(
                        className="product-image",
                        children=html.Img(
                            src=app.get_asset_url("top.jpg"),
                            alt="Top",
                            style={"width": "100%", "border-radius": "8px"},
                        )
                    ),
                    html.Div(
                        className="product-description",
                        children=[
                            html.P(
                                "This is a stylish top, ideal for cold weather. "
                                "It combines elegance with comfort, ensuring you stay warm and look great.",
                                style={"font-size": "18px"},
                            ),
                             # Button to trigger SPARQL query
                            html.Button("Fetch Top Data", id="fetch-top-data"),
                            # DataTable to display SPARQL results
                            dash_table.DataTable(
                                id="top-data-table",
                                columns=[
                                    {"name": "Recipe", "id": "recipe"}
                                ],
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                    "margin-top": "20px",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "5px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=5,
                            ),
                        ]
                    ),
                ],
                style={"display": "flex", "gap": "20px"},
            ),
            dcc.Link("Back to Home", href="/", className="back-link"),
        ],
    )
# Dashboard Page Layout
def dashboard_page():
    return html.Div(
        children=[
            
            # Resource Event Dashboard
            html.Div(
                children=[
                            html.P(
                                "Fabric Block",
                                style={"font-size": "30px"},
                            ),
                             # Button to trigger SPARQL query
                            html.Button("Fabric Block Data", id="fetch-fb-data"),
                            # DataTable to display SPARQL results
                            dash_table.DataTable(
                                id="fb-data-table",
                                columns=[
                                    {"name": "FabricBlock", "id": "fabricBlock"}
                                ],
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                    "margin-top": "20px",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "5px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=5,
                            ),
                        ]        
            ),
            html.Div(
                children=[
                            html.P(
                                "Material Available",
                                style={"font-size": "30px"},
                            ),
                             # Button to trigger SPARQL query
                            html.Button("Material Available", id="fetch-material-data"),
                            # DataTable to display SPARQL results
                            dash_table.DataTable(
                                id="material-data-table",
                                columns=[
                                    {"name": "Recipe", "id": "recipe"},
                                    {"name": "Fabric Block Design", "id": "fabricBlockDesign"},
                                    {"name": "Required Amount", "id": "requiredAmount"},
                                    {"name": "Available Amount", "id": "availableAmount"},
                                    {"name": "Ready For Assembly", "id": "readyForAssembly"},
                                ],
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                    "margin-top": "20px",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "5px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=5,
                            ),

                        ]        
            ),
            html.Div(
                children=[
                            html.P(
                                "Material Available",
                                style={"font-size": "30px"},
                            ),
                             # Button to trigger SPARQL query
                            html.Button("Location", id="fetch-location-data"),
                            # DataTable to display SPARQL results
                            dash_table.DataTable(
                                id="location-data-table",
                                columns=[
                                    {"name": "Location", "id": "location"},
                                    {"name": "Fabric Block Design", "id": "fabricBlockDesign"},
                                    {"name": "Count At Location", "id": "countAtLocation"},
                                ],
                                style_table={
                                    "overflowX": "auto",
                                    "width": "100%",
                                    "margin-top": "20px",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "5px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=5,
                            ),

                        ]        
            ),
            dcc.Link("Back to Home", href="/", style={"display": "block", "margin-top": "30px", "text-align": "center"}),
        ],
        style={"max-width": "1200px", "margin": "0 auto", "padding": "20px"},  # Centralize entire content
    )

def fetch_material():
    query = """
    PREFIX : <http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT 
        (STRAFTER(STR(?recipe), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?recipeName)
        (STRAFTER(STR(?fabricBlockDesign), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?fabricBlockDesignName)
        ?requiredAmount
        ?availableAmount
        (IF(?availableAmount >= ?requiredAmount, "Yes", "No") AS ?readyForAssembly)
    WHERE {
        # Link recipes to their requirements
        ?recipe :hasRequirement ?requirement .
        ?requirement :requiresFabricBlockDesign ?fabricBlockDesign .
        ?requirement :fabricBlockAmount ?requiredAmount .

        # Subquery to calculate available amount
        OPTIONAL {
            SELECT ?fabricBlockDesign (COUNT(?fabricBlock) AS ?availableAmount)
            WHERE {
                ?fabricBlock rdf:type :FabricBlock .
                ?fabricBlock :followsFabricBlockDesign ?fabricBlockDesign .
            }
            GROUP BY ?fabricBlockDesign
        }
    }

    """
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    try:
        # Query the endpoint and get results
        results = client.query().convert()  
        bindings = results['results']['bindings']
        
        data = [
            {
                'recipe': item['recipeName']['value'] if 'recipeName' in item else None,
                'fabricBlockDesign': item['fabricBlockDesignName']['value'] if 'fabricBlockDesignName' in item else None,
                'requiredAmount': int(item['requiredAmount']['value']) if 'requiredAmount' in item else 0,
                'availableAmount': int(item['availableAmount']['value']) if 'availableAmount' in item else 0,
                'readyForAssembly': item['readyForAssembly']['value'] if 'readyForAssembly' in item else "No"
            }
            for item in bindings
        ]

        # Debug: Print the parsed data
        print(data)

        return data

    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")
        return []
#resource event, fabricBlocks Dashboard
def fetch_fb():
    query = """
    PREFIX : <http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?fabricBlock
    WHERE {
        ?fabricBlock rdf:type :FabricBlock . 
}
    """
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    try:
        results = client.query().convert()
        
        # Extract the last part of the URI for each recipe
        return [
            {"fabricBlock": result["fabricBlock"]["value"].split("/")[-1]}  # Extracts only the last part
            for result in results["results"]["bindings"]
        ]
    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")
        return []

def fetch_skirt_recipes():
    query = """
    PREFIX : <http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT 
        (STRAFTER(STR(?recipe), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?recipeName)
        (STRAFTER(STR(?fabricBlockDesign), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?fabricBlockDesignName)
        ?requiredAmount
        (STRAFTER(STR(?pdfURL), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?pdfURLName)
    WHERE {
        # Fetch recipes
        ?design rdf:type/rdfs:subClassOf* :SkirtDesign .
        ?recipe :isRecipeOf ?design .
        
        # Link recipe to requirements
        ?recipe :hasRequirement ?requirement .
        ?requirement :requiresFabricBlockDesign ?fabricBlockDesign .
        ?requirement :fabricBlockAmount ?requiredAmount .
        
        # Optional PDF URL
        OPTIONAL {
            ?recipe :hasPDF ?pdfProperty .
            ?pdfProperty :URLtoPDF ?pdfURL .
        }
    }


    """
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    try:
        results = client.query().convert()
        bindings = results['results']['bindings']

        data = [
            {
                'recipe': item['recipeName']['value'].split("/")[-1] if 'recipeName' in item else None,  # Extract local name
                'fabricBlockDesign': item['fabricBlockDesignName']['value'].split("/")[-1] if 'fabricBlockDesignName' in item else None,  # Extract local name
                'requiredAmount': int(item['requiredAmount']['value']) if 'requiredAmount' in item else 0,  # Keep as integer
                'pdfURL': item['pdfURLName']['value'] if 'pdfURLName' in item else None,  # Keep full URL
            }
            for item in bindings
        ]

        print(data)
        return data

    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")
        return []

def fetch_top_recipes():
    query = """
    PREFIX : <http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?recipe
    WHERE {
      ?design rdf:type/rdfs:subClassOf* :TopDesign .
      ?recipe :isRecipeOf ?design .
    }
    """
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    try:
        results = client.query().convert()
        
        # Extract the last part of the URI for each recipe
        return [
            {"recipe": result["recipe"]["value"].split("/")[-1]}  # Extracts only the last part
            for result in results["results"]["bindings"]
        ]
    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")
        return []

def fetch_location():
    query = """
    PREFIX : <http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT 
        (STRAFTER(STR(?location), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?locationName)
        (STRAFTER(STR(?fabricBlockDesign), "http://www.semanticweb.org/sophi/ontologies/2024/10/untitled-ontology-20/") AS ?fabricBlockDesignName)
    WHERE 
    { 
        # Find all FabricBlockDesigns linked to requirements 
        ?requirement :requiresFabricBlockDesign ?fabricBlockDesign . 
        ?requirement :fabricBlockAmount ?requiredAmount . 
        # Subquery to calculate availableAmount 
        OPTIONAL{ 
  
    SELECT 
        ?fabricBlockDesign (COUNT(?fabricBlock) AS ?availableAmount) 
        WHERE { ?fabricBlock rdf:type :FabricBlock . 
        ?fabricBlock :followsFabricBlockDesign ?fabricBlockDesign . 
        }
      GROUP BY ?fabricBlockDesign 
      } 
      # The subquery result (availableAmount) is used in the main WHERE clause 
      }
    """
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    try:
        results = client.query().convert()
        print("Raw Results:", results)  # Debug raw results
        bindings = results['results']['bindings']
        print("Bindings:", bindings)  # Debug parsed bindings
        
        data = [
            {
                'location': item['locationName']['value'] if 'locationName' in item else None,
                'fabricBlockDesign': item['fabricBlockDesignName']['value'] if 'fabricBlockDesignName' in item else None,
                'countAtLocation': int(item['countAtLocation']['value']) if 'countAtLocation' in item else 0
            }
            for item in bindings
        ]

        print("Processed Data:", data)  # Debug final data
        return data

    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")
        return []


# Main Layout with Navigation Menu
app.layout = html.Div(
    children=[
        dcc.Location(id="url", refresh=False),  # Tracks the URL
        html.Div(
            className="menu",
            children=[
                dcc.Link("Home", href="/", className="menu-link", style={"margin-right": "20px"}),
                dcc.Link("Dashboard", href="/dashboard", className="menu-link", style={"margin-right": "20px"}),
                dcc.Link("Skirt", href="/skirt", className="menu-link", style={"margin-right": "20px"}),
                dcc.Link("Top", href="/top", className="menu-link"),
            ],  
            style={
                "background-color": "#f5f5f5",
                "padding": "10px",
                "display": "flex",
                "justify-content": "center",
            },
        ),
        html.Div(id="page-content", style={"padding": "20px"}),  # Dynamic content area
    ]
)

# Callback to Render Pages Dynamically
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/dashboard":
        return dashboard_page()
    elif pathname == "/skirt":
        return skirt_page()
    elif pathname == "/top":
        return top_page()
    else:
        return home_page()
    
@app.callback(
    Output("skirt-data-table", "data"),
    Input("fetch-skirt-data", "n_clicks"),
    prevent_initial_call=True
)

def update_skirt_table(n_clicks):
    try:
        # Fetch data from GraphDB
        data = fetch_skirt_recipes()
        return data
    except Exception as e:
        print(f"Error fetching SPARQL data: {e}")
        return []

@app.callback(
    Output("top-data-table", "data"),
    Input("fetch-top-data", "n_clicks"),
    prevent_initial_call=True
)

def update_top_table(n_clicks):
    try:
        # Fetch data from GraphDB
        data = fetch_top_recipes()
        return data
    except Exception as e:
        print(f"Error fetching SPARQL data: {e}")
        return []

@app.callback(
    Output("fb-data-table", "data"),
    Input("fetch-fb-data", "n_clicks"),
    prevent_initial_call=True
)

def update_fb_table(n_clicks):
    try:
        # Fetch data from GraphDB
        data = fetch_fb()
        return data
    except Exception as e:
        print(f"Error fetching SPARQL data: {e}")
        return []
    
@app.callback(
    Output("material-data-table", "data"),  
    Input("fetch-material-data", "n_clicks")  
)

def update_material_table(n_clicks):
    if n_clicks is None: 
        return []  
    try:
        # Fetch the material data
        material_data = fetch_material()
        return material_data 
    except Exception as e:
        print(f"Error updating material table: {e}")
        return [] 
        
@app.callback(
    Output("location-data-table", "data"),  
    Input("fetch-location-data", "n_clicks")  
)

def update_location_table(n_clicks):
    if n_clicks is None: 
        return []  
    try:
        # Fetch the material data
        material_data = fetch_location()
        return material_data 
    except Exception as e:
        print(f"Error updating material table: {e}")
        return [] 
            
# Data Callbacks for Resource Event Dashboard
@app.callback(
    Output("res-dashboard-table", "data", allow_duplicate=True),
    Input("flow-chart", "tapEdgeData"),
    prevent_initial_call=True
)
def onTapEdge(tapEdgeData):
    col_title = "EventTrigger"
    ce_data = data.get_data()
    filtered_data = ce_data[ce_data[col_title].str.contains(tapEdgeData["label"], case=False, na=False)]
    return filtered_data.to_dict("records")

@app.callback(
    Output("res-dashboard-table", "data"),
    Input("flow-chart", "tapNodeData"),
    prevent_initial_call=True
)
def onTapNode(tapNodeData):
    col_title = "TO"
    ce_data = data.get_data()
    filtered_data = ce_data[ce_data[col_title].str.contains(tapNodeData["label"], case=False, na=False)]
    return filtered_data.to_dict("records")

@app.callback(
    Output("res-dashboard-table", "data", allow_duplicate=True),
    [Input("update-button", "n_clicks")],
    prevent_initial_call=True
)
def update_material_table(n_clicks):
    return data.get_data().to_dict("records")


if __name__ == "__main__":
    app.run_server(debug=True)




#TO DO: refactoring
#resource event, fabricBlocks Dashboard
#Link recipes
#is material for recipe available 