namespace Mapped.Ontologies.Mappings.OntologyMapper.Mapped.Test
{
    using DTDLParser;
    using Microsoft.Extensions.Logging;
    using Moq;
    using System.Reflection;
    using Xunit;
    using Xunit.Abstractions;

    public class WillowMappingValidationTests
    {
        private readonly ITestOutputHelper output;

        public WillowMappingValidationTests(ITestOutputHelper output)
        {
            this.output = output;
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json")]
        public void ValidateMappedDtmisAreValidFormat(string resourcePath)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);

            var exceptions = new List<string>();
            foreach (var mapping in ontologyMappingManager.OntologyMapping.InterfaceRemaps)
            {
                try
                {
                    var inputDtmi = new Dtmi(mapping.InputDtmi);
                }
                catch (ParsingException)
                {
                    exceptions.Add($"Invalid input DTMI: {mapping.InputDtmi}");
                }

                try
                {
                    var outputDtmi = new Dtmi(mapping.OutputDtmi);
                }
                catch (ParsingException)
                {
                    exceptions.Add($"Invalid output DTMI: {mapping.OutputDtmi}");
                }
            }

            // Verify that the Interface Remaps are unique for an input interface
            foreach (var interfaceRemap in ontologyMappingManager.OntologyMapping.InterfaceRemaps)
            {
                var matchingRemapsCount = ontologyMappingManager.OntologyMapping.InterfaceRemaps.Count(p => p.InputDtmi == interfaceRemap.InputDtmi);
                if (matchingRemapsCount > 1)
                {
                    exceptions.Add($"Duplicate InterfaceRemap: {interfaceRemap.InputDtmi}");
                    Console.WriteLine($"Duplicate InterfaceRemap: {interfaceRemap.InputDtmi}");
                }
            }

            // Verify that the Interface Remaps are unique for an input interface
            foreach (var relationshipRemap in ontologyMappingManager.OntologyMapping.RelationshipRemaps)
            {
                var matchingRemapsCount = ontologyMappingManager.OntologyMapping.RelationshipRemaps.Count(p => p.InputRelationship == relationshipRemap.InputRelationship);
                if (matchingRemapsCount > 1)
                {
                    exceptions.Add($"Duplicate RelationshipRemap: {relationshipRemap.InputRelationship}");
                }
            }

            // Verify that the property projections are unique for an output property, unless it is a collection, then the original name can be used.
            foreach (var projection in ontologyMappingManager.OntologyMapping.PropertyProjections)
            {
                var matchingProjectionsCount = ontologyMappingManager.OntologyMapping.PropertyProjections.Count(p => p.OutputPropertyName == projection.OutputPropertyName && projection.IsOutputPropertyCollection == false);
                if (matchingProjectionsCount > 1)
                {
                    exceptions.Add($"Duplicate PropertyProjection: {projection.OutputPropertyName}");
                }
            }

            // Verify that the fill properties are unique for an output property
            foreach (var fillProperty in ontologyMappingManager.OntologyMapping.FillProperties)
            {
                var matchingFillPropertyCount = ontologyMappingManager.OntologyMapping.FillProperties.Count(p => p.OutputPropertyName == fillProperty.OutputPropertyName);
                if (matchingFillPropertyCount > 1)
                {
                    exceptions.Add($"Duplicate FillProperty: {fillProperty.OutputPropertyName}");
                }
            }

            Assert.Empty(exceptions);
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "dtmi:org:brickschema:schema:Brick:Ablutions_Room;1", "dtmi:com:willowinc:Room;1")]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "dtmi:org:brickschema:schema:Brick:Ablutions;1", "dtmi:com:willowinc:Ablutions;1")]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", false, "dtmi:org:fakeschema:schema:Brick:Ablutions;1", null)]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "dtmi:org:brickschema:schema:Brick:CO2_Alarm_Setpoint;1", "dtmi:com:willowinc:CO2_Alarm_Setpoint;1")]
        public void ValidateInterfaceMappings(string resourcePath, bool isFound, string input, string? expected)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);

            var inputDtmi = new Dtmi(input);
            var result = ontologyMappingManager.TryGetInterfaceRemapDtmi(inputDtmi, out var dtmiRemap);

            Assert.Equal(isFound, result);

            if (isFound)
            {
                Assert.NotNull(dtmiRemap);
                Assert.Equal(expected, dtmiRemap.OutputDtmi);
            }
            else
            {
                Assert.Null(dtmiRemap);
            }
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", false, "isFedBy", "isFedBy")]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "floors", "isPartOf")]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "isLocationOf", "locatedIn")]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json", true, "hasPoint", "isCapabilityOf")]
        public void ValidateRelationshipMappings(string resourcePath, bool isFound, string inputRelationship, string? expected)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);

            var result = ontologyMappingManager.TryGetRelationshipRemap(inputRelationship, out var relationshipRemap);

            Assert.Equal(isFound, result);

            if (isFound)
            {
                Assert.NotNull(relationshipRemap);
                Assert.Equal(expected, relationshipRemap.OutputRelationship);
            }
            else
            {
                Assert.Null(relationshipRemap);
            }
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json")]
        public void ValidateSourceDtmisAreValid(string resourcePath)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);
            var modelParser = new ModelParser();
            var inputDtmi = LoadDtdl(new[] { "mapped_dtdl.json" });
            var inputModels = modelParser.Parse(inputDtmi);
            ontologyMappingManager.ValidateSourceOntologyMapping(inputModels, out var invalidSources);
            Console.WriteLine(invalidSources.Count());

            Assert.Empty(invalidSources);
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json")]
        public void ValidateTargetDtmisAreValid(string resourcePath)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);
            var modelParser = new ModelParser();
            var inputDtmi = LoadDtdl(new[] { "Willow.Ontology.Airport.DTDLv3.jsonld" });

            var inputModels = modelParser.Parse(inputDtmi);
            ontologyMappingManager.ValidateTargetOntologyMapping(inputModels, out var invalidSources);

            Assert.Empty(invalidSources);
        }

        [Theory]
        [InlineData("Mappings.v1.Willow.mapped_v1_dtdlv2_Willow.json")]
        public void ValidateTargetDtmisForAirportAreValid(string resourcePath)
        {
            var mockLogger = new Mock<ILogger>();
            var resourceLoader = new MappedOntologyMappingLoader(mockLogger.Object, resourcePath);
            var ontologyMappingManager = new OntologyMappingManager(resourceLoader);
            var modelParser = new ModelParser();
            var inputDtmi = LoadDtdl(new[] { "Willow.Ontology.Airport.DTDLv3.jsonld" });

            List<string> invalidSources = new List<string>();
            try
            {
                var inputModels = modelParser.Parse(inputDtmi);
                ontologyMappingManager.ValidateTargetOntologyMapping(inputModels, out invalidSources);
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex);
            }

            Assert.Empty(invalidSources);
        }

        private IEnumerable<string> LoadDtdl(string[] dtdlFiles)
        {
            var assembly = Assembly.GetExecutingAssembly();

            List<string> dtdls = new List<string>();

            foreach (var file in dtdlFiles)
            {
                var resourceName = assembly.GetManifestResourceNames().Single(str => str.EndsWith(file));

                using (Stream? stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        using (StreamReader reader = new StreamReader(stream))
                        {
                            string result = reader.ReadToEnd();
                            dtdls.Add(result);
                        }
                    }
                    else
                    {
                        throw new FileNotFoundException(resourceName);
                    }
                }
            }

            return dtdls;
        }
    }
}
