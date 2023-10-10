import networkx as nx
from collections import defaultdict


class Mapper:
    def __init__(self, onto_x, map_xy, onto_y, map_yx):
        self.onto_x = onto_x
        self.map_xy = map_xy
        self.onto_y = onto_y
        self.map_yx = map_yx
        self.strategies = []
        self.results = defaultdict(float)

    def _ingest_dtdl(self, ontology, ontology_name):
        for item in ontology:
            if item.get("@type") == "Interface" and not item.get("deprecated", False):
                id = item["@id"]
                self.graph.add_node(
                    id,
                    name=item.get("displayName", ""),
                    description=item.get("description", ""),
                    ontology=ontology_name,
                )
                parents = item.get("extends", [])
                if isinstance(parents, str):
                    parents = [parents]
                for parent in parents:
                    self.graph.add_edge(id, parent, relationship="extends")

    def _ingest_mappings(self):
        for mapping in (self.map_xy, self.map_yx):
            for item in mapping.get("InterfaceRemaps", []):
                input_dtmi = item.get("InputDtmi")
                output_dtmi = item.get("OutputDtmi")

                if input_dtmi and output_dtmi:
                    self.graph.add_edge(input_dtmi, output_dtmi, relationship="mapsTo")
                else:
                    if not input_dtmi:
                        print(f"Missing InputDtmi for mapping: {item}")
                    if not output_dtmi:
                        print(f"Missing OutputDtmi for mapping: {item}")

    def _ingest_ontology_names(self):
        self.ontology_name_x = self.map_xy["Header"]["InputOntologies"][0]["Name"]
        self.ontology_name_y = self.map_yx["Header"]["InputOntologies"][0]["Name"]

    def initialize_graph(self):
        self.graph = nx.DiGraph()
        self._ingest_ontology_names()
        self._ingest_dtdl(self.onto_x, self.ontology_name_x)
        self._ingest_dtdl(self.onto_y, self.ontology_name_y)
        self._ingest_mappings()

    def add_strategy(self, strategy, weight: float = 1.0):
        """Adds a strategy with its corresponding weight."""
        self.strategies.append((strategy, weight))

    def execute(self):
        """Executes each strategy and applies the corresponding weight to its result."""
        self.initialize_graph()
        self.add_strategy(ProximityMapper(self.graph))
        for strategy, weight in self.strategies:
            results = strategy.execute()

            for key, inner_dict in results.items():
                if key not in self.results:
                    self.results[key] = defaultdict(float)

                for inner_key, inner_value in inner_dict.items():
                    self.results[key][inner_key] += inner_value * weight

    def map(self, klass: str, ns) -> str:  # dtmi -> dtmi
        pass


class ProximityMapper():
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def execute(self):
        # Identify unmapped nodes
        unmapped = []
        for node in self.graph.nodes():
            has_maps_to = False
            for _, _, edge_data in self.graph.out_edges(node, data=True):
                if edge_data.get("relationship") == "mapsTo":
                    has_maps_to = True
                    break
            if not has_maps_to:
                unmapped.append(node)

        suggested_mappings = defaultdict(lambda: defaultdict(int))
        for node in unmapped:
            # Get node's parent mappings
            for parent, _, edge_data in self.graph.in_edges(node, data=True):
                if edge_data.get("relationship") == "extends":
                    for _, mapping, edge_data in self.graph.out_edges(
                        parent, data=True
                    ):
                        if edge_data.get("relationship") == "mapsTo":
                            suggested_mappings[node][mapping] += 1

                            # Get children of mappings
                            for _, child, edge_data in self.graph.out_edges(
                                mapping, data=True
                            ):
                                if edge_data.get("relationship") == "extends":
                                    suggested_mappings[node][child] += 1

        weighted_mappings = self.calculate_weighted_mappings(suggested_mappings)
        return weighted_mappings

    def calculate_weighted_mappings(self, possible_mappings):
        weighted_mappings = defaultdict(lambda: defaultdict(float))
        for node, mappings in possible_mappings.items():
            total_visits = sum(mappings.values())
            for mapping, visits in mappings.items():
                weighted_mappings[node][mapping] = (
                    visits / total_visits if total_visits > 0 else 0
                )
        return weighted_mappings


# class StringSimilarityMapper(MappingStrategy):
