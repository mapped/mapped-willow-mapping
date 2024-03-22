// <copyright file="MappedHttpOntologyMappingLoader.cs" company="Mapped">
// Copyright (c) Mapped. All rights reserved.
// </copyright>

namespace Mapped.Ontologies.Mappings.OntologyMapper.Mapped
{
    using System.Text.Json;
    using Microsoft.Extensions.Logging;

    /// <summary>
    /// Ontology mapping loader implementation that loads mappings from a
    /// resource file embedded within the assembly.
    /// </summary>
    public class MappedHttpOntologyMappingLoader : IOntologyMappingLoader
    {
        private readonly ILogger logger;
        private readonly string resourceUrl = string.Empty;

        /// <summary>
        /// Initializes a new instance of the <see cref="MappedHttpOntologyMappingLoader"/> class.
        /// </summary>
        /// <param name="logger">Logging implementation.</param>
        /// <param name="resourceUrl">Http Url to ontology mappings file.</param>
        public MappedHttpOntologyMappingLoader(ILogger logger, string resourceUrl)
        {
            if (string.IsNullOrWhiteSpace(resourceUrl))
            {
                throw new ArgumentNullException(nameof(resourceUrl));
            }

            this.logger = logger;
            this.resourceUrl = resourceUrl;
        }

        /// <inheritdoc/>
        public OntologyMapping LoadOntologyMapping()
        {
            throw new NotImplementedException();
        }

        /// <inheritdoc/>
        public async Task<OntologyMapping> LoadOntologyMappingAsync()
        {
            logger.LogInformation("Loading Ontology Mapping file: {ResourceUrl}", resourceUrl);

            var options = new JsonSerializerOptions
            {
                ReadCommentHandling = JsonCommentHandling.Skip,
            };

            using (HttpClient httpClient = new HttpClient())
            {
                if (httpClient != null)
                {
                    var result = await httpClient.GetStringAsync(resourceUrl);
                    OntologyMapping? mappings;
                    try
                    {
                        mappings = JsonSerializer.Deserialize<OntologyMapping>(result, options);
                    }
                    catch (JsonException jex)
                    {
                        throw new MappingFileException("Mappings file '{ResourceUrl}' is malformed.", resourceUrl, jex);
                    }

                    if (mappings == null)
                    {
                        throw new MappingFileException("Mappings file '{ResourceUrl}' is empty.", resourceUrl);
                    }

                    return mappings;
                }
                else
                {
                    throw new FileNotFoundException(resourceUrl);
                }
            }
        }
    }
}
