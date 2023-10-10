import json
import os
from mapper.mapper import Mapper, ProximityMapper
from handler import DTDLHandler
from mappings.mappings import Mappings


def main():
    # Load ontologies
    mapped_package_name = "mapped.ontologies.core.dtdl"
    mapped_ontology = DTDLHandler(mapped_package_name)
    mapped_ontology.process()

    willow_package_name = "willowinc.ontology.dtdlv3"
    willow_ontology = DTDLHandler(willow_package_name)
    willow_ontology.process()

    # Load mappings
    mapped_mappings = Mappings(
        "Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json"
    )
    mapped_mappings.parse()
    willow_mappings = Mappings(
        "Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json"
    )
    willow_mappings.parse()

    # Find gaps
    missing_willow_interfaces = set(willow_ontology.interfaces) - set(
        willow_mappings.interface_inputs
    )
    missing_mapped_interfaces = set(mapped_ontology.interfaces) - set(
        mapped_mappings.interface_inputs
    )
    missing_willow_relationships = set(willow_ontology.relationships) - set(
        willow_mappings.relationship_inputs
    )
    missing_mapped_relationships = set(mapped_ontology.relationships) - set(
        mapped_mappings.relationship_inputs
    )
    missing_willow_namespaces = set(willow_ontology.namespaces) - set(
        willow_mappings.relationship_inputs
    )
    missing_mapped_namespaces = set(mapped_ontology.namespaces) - set(
        mapped_mappings.namespace_inputs
    )

    mapped_gaps =  {
        "missing_namespaces": sorted(list(missing_mapped_namespaces)),
        "missing_relationships": sorted(list(missing_mapped_relationships)),
        "missing_interfaces": sorted(list(missing_mapped_interfaces)),
    }

    willow_gaps = {
        "missing_namespaces": sorted(list(missing_willow_namespaces)),
        "missing_relationships": sorted(list(missing_willow_relationships)),
        "missing_interfaces": sorted(list(missing_willow_interfaces)),
    }

    output_directory = "scripts/mapping_diagnostics/output"
    os.makedirs(output_directory, exist_ok=True)

    with open(os.path.join(output_directory, "mapped_gaps.json"), "w") as file:
        json.dump(mapped_gaps, file, indent=2)

    with open(os.path.join(output_directory, "willow_gaps.json"), "w") as file:
        json.dump(willow_gaps, file, indent=2)
    
    m = Mapper(
        mapped_ontology.content, 
        mapped_mappings.content, 
        willow_ontology.content, 
        willow_mappings.content, 
    )
    m.execute()


if __name__ == "__main__":
    main()
