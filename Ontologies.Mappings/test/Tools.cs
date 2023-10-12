namespace Mapped.Ontologies.Mappings.OntologyMapper.Mapped.Test
{
    using DTDLParser;
    using Microsoft.Extensions.Logging;
    using Moq;
    using System.Reflection;
    using Xunit;
    using Xunit.Abstractions;

    public class MappedMappingValidationTestTools
    {
        public static IEnumerable<string> LoadDtdls(string[] dtdlFiles)
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
