// -----------------------------------------------------------------------
// <copyright file="ObjectTransformationComparer.cs" company="Mapped">
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
    internal class ObjectTransformationComparer : IEqualityComparer<ObjectTransformation>
    {
        /// <summary>
        /// Compares two Property Projections for equality.
        /// </summary>
        /// <param name="x">Input Property Projection 1.</param>
        /// <param name="y">Input Property Projection 2.</param>
        /// <returns>Returns true if equal, false if not.</returns>
        public bool Equals(ObjectTransformation? x, ObjectTransformation? y)
        {
            if (x == null || y == null)
            {
                return false;
            }

            if (x.InputPropertyName != y.InputPropertyName || x.OutputPropertyName != y.OutputPropertyName || x.OutputDtmiFilter != y.OutputDtmiFilter)
            {
                return false;
            }

            return true;
        }

        /// <inheritdoc/>
        public int GetHashCode([DisallowNull] ObjectTransformation obj)
        {
            return (obj.InputPropertyName + obj.OutputPropertyName + obj.OutputDtmiFilter).GetHashCode();
        }
    }
}
