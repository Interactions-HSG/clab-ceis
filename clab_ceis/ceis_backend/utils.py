from SPARQLWrapper import SPARQLWrapper, JSON

SPARQL_ENDPOINT = "http://graphdb:7200/repositories/ceis-dev-local"


def get_bindings(file_name: str):
    with open(f"./queries/{file_name}.rq", "r", encoding="utf-8") as file:
        query = file.read()
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    results = client.query().convert()
    # if not dict
    if not isinstance(results, dict):
        raise ValueError("Invalid response from SPARQL endpoint")

    bindings = results.get("results", {}).get("bindings", [])
    print(bindings)
    if bindings and isinstance(bindings, list):
        return bindings
    raise ValueError("Invalid response from SPARQL endpoint")
