// -----------------------------------------------------------------------
// <copyright file="PropertyProjectionComparer.cs" company="Mapped">
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
    internal class PropertyProjectionComparer : IEqualityComparer<PropertyProjection>
    {
        /// <summary>
        /// Compares two Property Projections for equality.
        /// </summary>
        /// <param name="x">Input Property Projection 1.</param>
        /// <param name="y">Input Property Projection 2.</param>
        /// <returns>Returns true if equal, false if not.</returns>
        public bool Equals(PropertyProjection? x, PropertyProjection? y)
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

            foreach (var inputName in y.InputPropertyNames)
            {
                if (!x.InputPropertyNames.Contains(inputName))
                {
                    return false;
                }
            }

            return true;
        }

        /// <inheritdoc/>
        public int GetHashCode([DisallowNull] PropertyProjection obj)
        {
            return obj.InputPropertyNames.OrderBy(x => x).GetHashCode();
        }
    }
}
