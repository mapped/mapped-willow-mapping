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
                    self.results[key] = defaultdict(int)

                for inner_key, inner_value in inner_dict.items():
                    self.results[key][inner_key] += inner_value * weight

    def map(self, klass: str, ns) -> str:  # dtmi -> dtmi
        pass


class ProximityMapper:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.suggested_mappings = defaultdict(lambda: defaultdict(int))

    def identify_unmapped_nodes(self):
        # Identify unmapped nodes
        unmapped_nodes = []
        for node in self.graph.nodes():
            has_maps_to = False
            for _, _, edge_data in self.graph.out_edges(node, data=True):
                if edge_data.get("relationship") == "mapsTo":
                    has_maps_to = True
                    break
            if not has_maps_to:
                unmapped_nodes.append(node)
        return unmapped_nodes

    def identify_outward_edge_mappings(self, nodes):
        """
        Identify potential mappings for nodes by examining outward edges within the ontology.

        For each node in the list:
        1. Ascend to the node's immediate parent.
        2. Traverse through the mapping to reach the corresponding node within the ontology.
        3. Descend to collect children of that node.
        4. Accumulate these children and their parent node as potential mappings for the originating node.

        Parameters:
        - nodes: Nodes to determine potential mappings within the ontology.
        """
        for node in nodes:
            for parent, _, edge_data in self.graph.in_edges(node, data=True):
                if edge_data.get("relationship") == "extends":
                    for mapping, _, edge_data in self.graph.in_edges(parent, data=True):
                        if edge_data.get("relationship") == "mapsTo":
                            self.suggested_mappings[node][mapping] += 1

                            # Get children of mappings
                            for _, child, edge_data in self.graph.out_edges(
                                mapping, data=True
                            ):
                                if edge_data.get("relationship") == "extends":
                                    self.suggested_mappings[node][child] += 1

    def identify_inward_edge_mappings(self, nodes):
        """
        Identify potential mappings for nodes by examining inward edges from external ontology references.

        For each provided node:
        1. Traverse upwards to the node's immediate parent.
        2. Check if any nodes in the other ontology have mappings pointing to this parent.
        3. For nodes with such mappings, traverse downwards to retrieve their children.
        4. Return the externally referenced node and its children as potential mappings for the original node.

        Parameters:
        - nodes (List[Node]): A list of nodes for which to identify potential mappings based on external references.

        Returns:
        - Dictionary with original node as the key and potential mappings as the values.
        """
        for node in nodes:
            for parent, _, edge_data in self.graph.in_edges(node, data=True):
                if edge_data.get("relationship") == "extends":
                    for _, mapping, edge_data in self.graph.out_edges(
                        parent, data=True
                    ):
                        if edge_data.get("relationship") == "mapsTo":
                            self.suggested_mappings[node][mapping] += 1

                            # Get children of mappings
                            for _, child, edge_data in self.graph.out_edges(
                                mapping, data=True
                            ):
                                if edge_data.get("relationship") == "extends":
                                    self.suggested_mappings[node][child] += 1

    def execute(self):
        nodes = self.identify_unmapped_nodes()
        self.identify_outward_edge_mappings(nodes)
        self.identify_inward_edge_mappings(nodes)
        weighted_mappings = self.calculate_weighted_mappings()
        print(
            f"Suggesting mappings for {len(self.suggested_mappings)} entities with {len(nodes) - len(self.suggested_mappings)} remanaining unmapped entities."
        )
        return weighted_mappings

    def calculate_weighted_mappings(self):
        for node in self.suggested_mappings:
            # Sort the mappings for each node by weight in descending order
            self.suggested_mappings[node] = dict(sorted(self.suggested_mappings[node].items(), 
                                                key=lambda item: item[1], 
                                                reverse=True))
            # Convert defaultdict to regular dictionary for serialization
            normal_dict = {k: dict(v) for k, v in self.suggested_mappings.items()}

        # TODO: Remove
        import json
        with open("possible_mappings.json", "w") as f:
            json.dump(normal_dict, f, indent=4)

        return self.suggested_mappings 


# class StringSimilarityMapper(MappingStrategy):
