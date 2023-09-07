// <copyright file="MultifileOntologyMappingLoader.cs" company="Mapped">
// Copyright (c) Mapped. All rights reserved.
// </copyright>

namespace Mapped.Ontologies.Mappings.OntologyMapper.Mapped
{
    using System.Reflection;
    using System.Text.Json;
    using Microsoft.Extensions.Logging;

    /// <summary>
    /// Ontology mapping loader implementation that loads mappings from a
    /// resource file embedded within the assembly.
    /// </summary>
    public class MultifileOntologyMappingLoader : IOntologyMappingLoader
    {
        private readonly ILogger logger;
        private readonly List<string> resourcePaths;

        /// <summary>
        /// Initializes a new instance of the <see cref="MultifileOntologyMappingLoader"/> class.
        /// </summary>
        /// <param name="logger">Logging implementation.</param>
        /// <param name="resourcePaths">Paths to ontology mappings file embedded within assembly, using dot notation, e.g., <em>Mappings.v0.BrickRec.mapped_json_v0_dtdlv2_Brick_1_3-REC_4_0.json</em>.</param>
        public MultifileOntologyMappingLoader(ILogger logger, List<string> resourcePaths)
        {
            if (resourcePaths == null || !resourcePaths.Any())
            {
                throw new ArgumentNullException(nameof(resourcePaths));
            }

            this.logger = logger;
            this.resourcePaths = resourcePaths;
        }

        /// <inheritdoc/>
        public OntologyMapping LoadOntologyMapping()
        {
            OntologyMapping? mappings = null;

            foreach (var resourcePath in resourcePaths)
            {
                logger.LogInformation("Loading Ontology Mapping file: {fileName}", resourcePath);

                var assembly = Assembly.GetExecutingAssembly();
                var resources = assembly.GetManifestResourceNames();
                var resourceName = resources.Single(str => str.ToLowerInvariant().EndsWith(resourcePath.ToLowerInvariant()));

                var options = new JsonSerializerOptions
                {
                    ReadCommentHandling = JsonCommentHandling.Skip,
                };

                using (Stream? stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        using (StreamReader reader = new StreamReader(stream))
                        {
                            string result = reader.ReadToEnd();
                            try
                            {
                                var innerMappings = JsonSerializer.Deserialize<OntologyMapping>(result, options);

                                mappings = MergeMappings(mappings, innerMappings);
                            }
                            catch (JsonException jex)
                            {
                                throw new MappingFileException($"Mappings file '{resourcePath}' is malformed.", resourcePath, jex);
                            }

                            if (mappings == null)
                            {
                                throw new MappingFileException($"Mappings file '{resourcePath}' is empty.", resourcePath);
                            }
                        }
                    }
                    else
                    {
                        throw new FileNotFoundException(resourcePath);
                    }
                }
            }

            return mappings ?? new OntologyMapping();
        }

        private static OntologyMapping? MergeMappings(OntologyMapping? mappings, OntologyMapping? mappingsToMerge)
        {
            if (mappings == null)
            {
                return mappingsToMerge;
            }

            if (mappingsToMerge != null)
            {
                // These type of mappings should never result in duplicates. If they do, that will cause test failures before check-in.
                mappings.InterfaceRemaps.AddRange(mappingsToMerge.InterfaceRemaps);
                mappings.RelationshipRemaps.AddRange(mappingsToMerge.RelationshipRemaps);
                var propertyProjectionComparer = new PropertyProjectionComparer();
                var objectTransformationComparer = new ObjectTransformationComparer();
                var fillPropertyComparer = new FillPropertyComparer();

                // Property Projections may result in duplicates. Remove dupes.
                foreach (var mapping in mappingsToMerge.PropertyProjections)
                {
                    if (!mappings.PropertyProjections.Contains(mapping, propertyProjectionComparer))
                    {
                        mappings.PropertyProjections.Add(mapping);
                    }
                }

                // Object Transformations may result in duplicates. Remove dupes.
                foreach (var mapping in mappingsToMerge.ObjectTransformations)
                {
                    if (!mappings.ObjectTransformations.Contains(mapping, objectTransformationComparer))
                    {
                        mappings.ObjectTransformations.Add(mapping);
                    }
                }

                foreach (var mapping in mappingsToMerge.FillProperties)
                {
                    if (!mappings.FillProperties.Contains(mapping, fillPropertyComparer))
                    {
                        mappings.FillProperties.Add(mapping);
                    }
                }
            }

            return mappings;
        }
    }
}
