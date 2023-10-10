from ontology import loader
from ontology import parser

class DTDLHandler:
    def __init__(self, package_id, content_filename=None):
        self.package_id = package_id 
        self.content_filename = content_filename
        self.content = None
        self.dtdl_parser = None

    def process(self):
        nuget_loader = loader.NugetLoader(self.package_id)
        self.content = nuget_loader.load(self.content_filename)
        self.dtdl_parser = parser.DTDLParser(self.content)
        self.dtdl_parser.parse()
    
    @property
    def interfaces(self):
        if self.dtdl_parser:
            return self.dtdl_parser.interfaces
        return None

    @property
    def namespaces(self):
        if self.dtdl_parser:
            return self.dtdl_parser.namespaces
        return None

    @property
    def relationships(self):
        if self.dtdl_parser:
            return self.dtdl_parser.relationships
        return None
