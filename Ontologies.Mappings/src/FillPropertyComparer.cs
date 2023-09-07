// -----------------------------------------------------------------------
// <copyright file="FillPropertyComparer.cs" company="Mapped">
// Copyright (c) Mapped. All rights reserved.
// </copyright>
// -----------------------------------------------------------------------

namespace Mapped.Ontologies.Mappings
{
    using System.Diagnostics.CodeAnalysis;
    using Mapped.Ontologies.Mappings.OntologyMapper;

    /// <summary>
    /// Compares to Property Projections for equality.
    /// </summary>
    internal class FillPropertyComparer : IEqualityComparer<FillProperty>
    {
        /// <summary>
        /// Compares two Fill Property objects for equality.
        /// </summary>
        /// <param name="x">Input Fill Property 1.</param>
        /// <param name="y">Input Fill Property 2.</param>
        /// <returns>Returns true if equal, false if not.</returns>
        public bool Equals(FillProperty? x, FillProperty? y)
        {
            if (x == null || y == null)
            {
                return false;
            }

            foreach (var inputName in x.InputPropertyNames)
            {
                if (!y.InputPropertyNames.Contains(inputName))
                {
                    return false;
                }
            }

            if (x.OutputPropertyName != y.OutputPropertyName || x.OutputDtmiFilter != y.OutputDtmiFilter)
            {
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public int GetHashCode([DisallowNull] FillProperty obj)
        {
            return (obj.InputPropertyNames.OrderBy(x => x).ToString() + obj.OutputPropertyName + obj.OutputDtmiFilter).GetHashCode();
        }
    }
}
