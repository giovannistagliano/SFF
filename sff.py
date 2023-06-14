r"""
Hodge-special fourfolds

This module provides support for Hodge-special fourfolds, such as cubic fourfolds and Gushel-Mukai fourfolds.
For some example see the function :meth:`fourfold`.

For more computational details, see the paper at https://www.tandfonline.com/doi/abs/10.1080/10586458.2023.2184882 and references therein.

.. NOTE::

    For some of the functions provided, you must have ``Macaulay2`` with the package ``SpecialFanoFourfolds`` (version 2.7.1 or later)
    installed on your computer; see https://faculty.math.illinois.edu/Macaulay2/doc/Macaulay2/share/doc/Macaulay2/SpecialFanoFourfolds/html/index.html.

AUTHORS:

- Giovanni Staglianò (2023-06-14): initial version

"""

#***************************************************************************************
#       Copyright (C) 2023 Giovanni Staglianò <giovannistagliano@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
#***************************************************************************************

from sage.structure.sage_object import SageObject
from sage.misc.cachefunc import cached_function
from sage.misc.latex import latex
from sage.misc.functional import symbolic_prod as product
from sage.matrix.constructor import matrix
from sage.rings.integer import Integer
from sage.rings.integer_ring import ZZ
from sage.rings.finite_rings.finite_field_constructor import GF
from sage.rings.rational_field import RationalField
from sage.calculus.functions import jacobian
from sage.features.interfaces import Macaulay2
from sage.interfaces.macaulay2 import macaulay2, sage
from sage.categories.fields import Fields
from sage.categories.homset import Hom
from sage.rings.infinity import Infinity
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.polynomial.multi_polynomial_ideal import MPolynomialIdeal
from sage.schemes.projective.projective_space import ProjectiveSpace
from sage.schemes.projective.projective_subscheme import AlgebraicScheme_subscheme_projective
from sage.schemes.projective.projective_morphism import SchemeMorphism_polynomial_projective_space, SchemeMorphism_polynomial_projective_space_field
from sage.schemes.generic.morphism import SchemeMorphism
from sage.rings.ideal import Ideal as ideal
from sage.functions.other import binomial
from sage.libs.singular.function_factory import singular_function
_minbase = singular_function('minbase')

__VERBOSE__ = False
def verbosity(b):
    r"""Change the default verbosity for some functions of this module.

    Use ``verbosity(True)`` to produce output messages by default. Verbosity can be disabled in the specific function you use.

    INPUT:

    :class:`bool`

    """
    if not isinstance(b,bool):
        raise TypeError("expected True or False")
    global __VERBOSE__
    __VERBOSE__ = b

class Embedded_projective_variety(AlgebraicScheme_subscheme_projective):
    r"""The class of closed subvarieties of projective spaces.

    This is a subclass of the class :class:`AlgebraicScheme_subscheme_projective`.
    It is designed to provide better support for projective surfaces and fourfolds.

    Constructing a closed subvariety of an ambient projective space.

    .. WARNING::

        You should not create objects of this class directly. The
        preferred method to construct such subvarieties is to use
        :meth:`projective_variety`.

    INPUT:

    - ``PP`` -- an ambient projective space
    - ``polys`` -- a list of homogeneous polynomials in the coordinate ring of ``PP``

    OUTPUT:

    The closed subvariety of ``PP`` defined by ``polys``

    EXAMPLES::

        sage: P, (x0,x1,x2,x3) = ProjectiveSpace(3, GF(101), 'x').objgens()
        sage: X = projective_variety([x0^2-x1*x2, x1^3+x2^3+x3^3], P); X     # the input P is optional
        curve of degree 6 and arithmetic genus 4 in PP^3 cut out by 2 hypersurfaces of degrees (2, 3)
        sage: X.ambient_space() is P
        True
        sage: X.defining_polynomials()
        (x0^2 - x1*x2, x1^3 + x2^3 + x3^3)
        sage: X.describe()
        dim:.................. 1
        codim:................ 2
        degree:............... 6
        sectional genus:...... 4
        generators:........... (2, 3)
        dim sing. l.:......... -1

    Here is another example using simple functions of the class.

    ::

        sage: from sage.misc.randstate import set_random_seed
        sage: set_random_seed(0)
        sage: K = GF(65521)
        sage: PP(4,K)
        PP^4
        sage: PP(4,K).empty()
        empty subscheme of PP^4
        sage: X = PP(4,K).empty().random(2,2,3)
        sage: X
        curve of degree 12 and arithmetic genus 13 in PP^4 cut out by 3 hypersurfaces of degrees (2, 2, 3)
        sage: X.describe()
        dim:.................. 1
        codim:................ 3
        degree:............... 12
        sectional genus:...... 13
        generators:........... (2, 2, 3)
        dim sing. l.:......... -1
        sage: X.dimension()
        1
        sage: X.codimension()
        3
        sage: X.degree()
        12
        sage: X.sectional_genus()
        13
        sage: X.ambient()
        PP^4
        sage: p = X.point(); p
        one-point scheme in PP^4 of coordinates [1, 52775, 1712, 653, 60565]
        sage: p.dimension() == 0 and p.degree() == 1 and p.is_subset(X)
        True

    You can also convert such varieties into ``Macaulay2`` objects.

    ::

        sage: X_ = macaulay2(X); X_                                          # optional - macaulay2
        curve in PP^4 cut out by 3 hypersurfaces of degrees 2^2 3^1
        <BLANKLINE>
        ProjectiveVariety, curve in PP^4
        sage: X_.cls()                                                       # optional - macaulay2
        EmbeddedProjectiveVariety
        <BLANKLINE>
        Type

    """
    def __init__(self, PP, polys = []):
        r"""See :class:`Embedded_projective_variety` for documentation."""
        if not _is_embedded_projective_variety(PP):
            raise TypeError("cannot interpret input as a projective variety")
        if PP.base_ring() not in Fields():
            raise ValueError("base ring must be a field")
        if len(polys) > 0:
            if PP.ambient_space() is not PP:
                raise ValueError("expected a projective ambient space")
            super().__init__(PP, polys)
        elif PP.ambient_space() is PP:
            super().__init__(PP, [])
        else:
            super().__init__(PP.ambient_space(),PP.defining_polynomials())
        self._homogeneous_components_ideal = {}

    def _repr_(self):
        r"""Return a string representation of the variety

        OUTPUT:

        A string.

        EXAMPLES::

            sage: PP(3).empty().random(2,2)._repr_()
            'curve of degree 4 and arithmetic genus 1 in PP^3 cut out by 2 hypersurfaces of degree 2'

        """
        return _expr_var_1(self)[0]

    def _latex_(self):
        r"""Return the LaTeX representation of ``self``.

        OUTPUT:

        A string.

        EXAMPLES::

            sage: X = PP(3).empty().random(2,2)
            sage: latex(X)
            \mbox{curve of degree } 4 \mbox{ and arithmetic genus } 1 \mbox{ in }\mathbb{P}^{ 3 } \mbox{ cut out by } 2 \mbox{ hypersurfaces of degree } 2

        """
        return _expr_var_1(self)[1]

    def dimension(self):
        r"""Return the dimension of the variety

        OUTPUT:

        An integer.

        EXAMPLES::

            sage: X = Veronese(1,3); X
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: X.dimension()
            1

        """
        try:
            return self._dimension
        except AttributeError:
            self._dimension = max(super().dimension(),-1)
            return self._dimension

    def codimension(self):
        r"""Return the codimension of the variety

        OUTPUT:

        An integer.

        EXAMPLES::

            sage: X = Veronese(1,3); X
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: X.codimension()
            2

        """
        try:
            return self._codimension
        except AttributeError:
            self._codimension = self.ambient_space().dimension() - self.dimension()
            return self._codimension

    def ambient(self):
        r"""Return the ambient projective space of the variety

        This is mathematically equal to the output of the :meth:`ambient_space` method.

        EXAMPLES::

            sage: X = Veronese(1,3); X
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: P = X.ambient(); P
            PP^3
            sage: type(P) is type(X)
            True

        """
        try:
            return self._ambient
        except AttributeError:
            if self.codimension() == 0:
                self._ambient = self
            else:
                self._ambient = Embedded_projective_variety(self.ambient_space())
            return self._ambient

    def degree(self):
        r"""Return the degree of the projective variety

        OUTPUT:

        An integer.

        EXAMPLES::

            sage: X = Veronese(1,3); X
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: X.degree()
            3

        """
        try:
            return self._degree
        except AttributeError:
            self._degree = super().degree()
            return self._degree

    def irreducible_components(self):
        r"""Return the irreducible components of the projective scheme ``self``.

        OUTPUT:

        A tuple of irreducible subschemes of the same ambient space of the scheme ``self``.

        EXAMPLES::

            sage: L = PP(4).empty().random(1,1,1)
            sage: C = PP(4).empty().random(1,1,2)
            sage: X = L + C
            sage: X.irreducible_components()
            [line in PP^4, conic curve in PP^4]

        """
        try:
            return self._list_of_irreducible_components
        except AttributeError:
            C = [Embedded_projective_variety(Y) for Y in super().irreducible_components()]
            if len(C) == 1 and C[0] == self:
                C = [self]
            self._list_of_irreducible_components = C
            return self._list_of_irreducible_components

    def hilbert_polynomial(self):
        r"""Return the Hilbert polynomial of the projective variety.

        OUTPUT:

        A polynomial over the rationals.

        EXAMPLES::

            sage: X = Veronese(1,3); X
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: X.hilbert_polynomial()
            3*t + 1

        """
        try:
            return self._hilbert_polynomial
        except AttributeError:
            self._hilbert_polynomial = self.defining_ideal().hilbert_polynomial()
            return self._hilbert_polynomial

    def sectional_genus(self):
        r"""Return the arithmetic genus of the sectional curve of the variety.

        OUTPUT:

        An integer.

        EXAMPLES::

            sage: X = Veronese(2,2); X
            surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2
            sage: X.sectional_genus()
            0

        """
        try:
            return self._sectional_genus
        except AttributeError:
            if not self.dimension() >= 1:
                raise ValueError("expected a positive dimensional scheme")
            P = self.hilbert_polynomial()
            t = PolynomialRing(RationalField(), 1, 't').gen()
            for i in range(self.dimension() - 1):
                P = P(t)-P(t-1)
            self._sectional_genus = Integer(1-P(0))
            return self._sectional_genus

    def topological_euler_characteristic(self, verbose=None, algorithm=None):
        r"""Return the topological Euler characteristic of the variety.

        .. WARNING::

            This uses a probabilistic approach which could give wrong answers
            (especially over finite fields of small order).

        With the input ``algorithm='macaulay2'`` the computation is transferred to ``Macaulay2``.

        OUTPUT:

        An integer.

        EXAMPLES::

            sage: X = Veronese(2,2); X
            surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2
            sage: X.topological_euler_characteristic()
            3

        """
        try:
            return self._topological_euler_characteristic
        except AttributeError:
            if verbose is None:
                verbose = __VERBOSE__
            if not isinstance(verbose,bool):
                raise TypeError("expected True or False")
            if algorithm not in (None, 'macaulay2', 'sage'):
                raise ValueError("keyword algorithm must be 'macaulay2' or 'sage'")
            if algorithm == 'macaulay2' or (algorithm is None and min(self.degrees_generators()) != max(self.degrees_generators()) and Macaulay2().is_present()):
                if verbose:
                    print("--topological_euler_characteristic(): transferring computation to Macaulay2...")
                return self._topological_Euler_characteristic_macaulay2(verbose=verbose)
            f = rational_map(self)
            m = f._degree_forms()
            d = f.projective_degrees()
            r = self.dimension()
            n = self.ambient().dimension()
            h = PolynomialRing(ZZ,'h',1).gens()[0]
            Segre_Class = sum([(-1)**(n-k-1) * sum([(-1)**i*binomial(n-k,i)*m**(n-k-i)*d[i] for i in range(n-k+1)]) * h**(n-k) for k in range(r+1)])
            Chern_Fulton_Class = Segre_Class * (1+h)**(n+1)
            self._topological_euler_characteristic = Integer(Chern_Fulton_Class.list()[n])
            return self._topological_euler_characteristic

    def _topological_Euler_characteristic_macaulay2(self, verbose=None):
        r"""See :meth:`topological_euler_characteristic` for documentation."""
        if verbose:
            print("-- running Macaulay2 function eulerCharacteristic()... --")
        X = macaulay2(self)
        e = X.eulerCharacteristic().sage()
        self._topological_euler_characteristic = Integer(e)
        if verbose:
            print("-- function eulerCharacteristic() has terminated. --")
        return self._topological_euler_characteristic

    def _raw_point(self):
        r"""An auxiliary function to pick random points on the variety defined over a finite field."""
        if self.dimension() <= 0:
            raise ValueError("expected a positive-dimensional scheme")
        if self.dimension() > 1:
            X = self.hyperplane_section(cache=False)
            j = X.embedding_as_hyperplane_section()
            p = j(X._raw_point())
            assert(p._is_point())
            return p
        if self.codimension() == 0:
            self.empty().random(*[1 for i in range(self.dimension())])
        if self.codimension() > 1:
            h = rational_map(self,[_random1(self.ambient().coordinate_ring()) for i in range(self.dimension()+2)])
            Y = h.image()
            p = h.inverse_image(Y._raw_point())
            assert(p._is_point())
            return p
        for i in range(10):
            X = self.hyperplane_section(cache=False)
            j = X.embedding_as_hyperplane_section()
            L = [q for q in X.irreducible_components() if q._is_point()]
            if len(L) == 0:
                continue
            p = j(L[0])
            assert(p._is_point())
            return p
        else:
            raise Exception("function _raw_point() failed: reached maximum number of 10 attempts to find rational point")

    def point(self, verbose=None, algorithm='sage'):
        r"""Pick a random point on the variety defined over a finite field.

        EXAMPLES::

            sage: X = Veronese(2,2)
            sage: with seed(0): p = X.point(); p
            one-point scheme in PP^5 of coordinates [1, 10850, 2338, 30739, 2409, 33291]
            sage: type(p) is type(X) and p.dimension() == 0 and p.degree() == 1 and p.is_subset(X)
            True

        With the input ``algorithm='macaulay2'`` the computation is transferred to ``Macaulay2``

        """
        if verbose is None:
            verbose = __VERBOSE__
        if not isinstance(verbose,bool):
            raise TypeError("expected True or False")
        if algorithm not in ('macaulay2', 'sage'):
            raise ValueError("keyword algorithm must be 'macaulay2' or 'sage'")
        if algorithm == 'sage':
            if self.codimension() == 0:
                return self.empty().random(*[1 for i in range(self.dimension())])
            if all(i == 1 for i in self.degrees_generators()) or hasattr(self,"_parametrization"):
                j = self.parametrize(verbose=verbose)
                q = j(j.source().point(verbose=verbose, algorithm='sage'))
                assert(q._is_point() and q.is_subset(self))
                return q
            return self._raw_point()
        if verbose:
            print("-- running Macaulay2 function point()... --")
        X = macaulay2(self)
        pointOnX = X.point()
        c = pointOnX.coordinates().sage()
        v = list(self.ambient_space().coordinate_ring().gens())
        M = matrix([v, c])
        polys = _minbase(ideal(M.minors(2)))
        assert((ideal(polys)).ring() is self.ambient().coordinate_ring())
        p = Embedded_projective_variety(self.ambient_space(),polys)
        p._coordinate_list = c
        assert(p._is_point() and p.is_subset(self))
        p._macaulay2_object = pointOnX
        if verbose:
            print("-- function point() has terminated. --")
        return p

    def _is_point(self):
        r"""Return ``True`` if ``self`` is a point, ``False`` otherwise."""
        try:
            return self.__is_Point
        except AttributeError:
            if not all(i == 1 for i in self.degrees_generators()):
                self.__is_Point = False
                return self.__is_Point
            self.__is_Point = self.dimension() == 0 and self.codimension() == self.ambient().dimension()
            return self.__is_Point

    def _coordinates(self):
        r"""Return the homogeneous coordinates of a point."""
        try:
            return self._coordinate_list
        except AttributeError:
            if not self._is_point():
                raise ValueError("expected a point")
            I = self.defining_ideal()
            M = jacobian(I.gens(),I.ring().gens()).change_ring(I.ring().base_ring())
            assert((M * matrix([I.ring().gens()]).transpose()).list() == I.gens())
            c = M.right_kernel_matrix().list()
            assert(len(c) == self.ambient().dimension() + 1)
            self._coordinate_list = c
            return self._coordinate_list

    def _describe(self, verbose=None):
        r"""Return a brief description of the variety, see :meth:`describe`.

        OUTPUT:

        A string.

        """
        if verbose is None:
            verbose = __VERBOSE__
        d = self.dimension()
        s = "dim:.................. " + str(d)
        if verbose:
            print(s)
        sf = s
        if d <= -1:
            return(sf)
        c = self.codimension()
        s = "codim:................ " + str(c)
        if verbose:
            print(s)
        sf = sf + '\n' + s
        if c > self.ambient().dimension():
            return(sf)
        e = self.degree()
        s = "degree:............... " + str(e)
        if verbose:
            print(s)
        sf = sf + '\n' + s
        if c >= self.ambient().dimension():
            return(sf)
        g = self.sectional_genus()
        s = "sectional genus:...... " + str(g)
        if verbose:
            print(s)
        sf = sf + '\n' + s
        gens = self.degrees_generators()
        s = "generators:........... " + str(gens)
        if verbose:
            print(s)
        sf = sf + '\n' + s
        sing_loc = self.singular_locus()
        dim_sing_loc = sing_loc.dimension()
        s = "dim sing. l.:......... " + str(dim_sing_loc)
        if verbose:
            print(s)
        sf = sf + '\n' + s
        if dim_sing_loc <= -1:
            return(sf)
        s = "gens. sing. l.:....... " + str(sing_loc.degrees_generators())
        if verbose:
            print(s)
        sf = sf + '\n' + s
        return(sf)

    def describe(self):
        r"""Print a brief description of the variety.

        OUTPUT:

        Nothing.

        EXAMPLES::

            sage: X = Veronese(2,2)
            sage: X.describe()
            dim:.................. 2
            codim:................ 3
            degree:............... 4
            sectional genus:...... 0
            generators:........... (2, 2, 2, 2, 2, 2)
            dim sing. l.:......... -1

        """
        self._describe(verbose=True)

    def degrees_generators(self):
        r"""Return the degrees of a minimal set of generators for the defining ideal of the variety.

        OUTPUT:

        A tuple of integers.

        EXAMPLES::

            sage: X = PP(4).empty().random(1,2,3,1)
            sage: X.degrees_generators()
            (1, 1, 2, 3)

        """
        try:
            return self._degrees_generators
        except AttributeError:
            self._degrees_generators = tuple([g.degree() for g in self.defining_polynomials()])
            return self._degrees_generators

    def singular_locus(self):
        r"""Return the singular locus of the variety.

        OUTPUT:

        :class:`Embedded_projective_variety`

        EXAMPLES::

            sage: X = Veronese(1,3)
            sage: X.singular_locus()
            empty subscheme of PP^3
            sage: type(_) is type(X) and _.is_subset(X)
            True
            sage: Y = surface(3,3,nodes=1); Y
            rational 1-nodal surface in PP^5 of degree 6 and sectional genus 1 cut out by 5 hypersurfaces of degrees (2, 2, 2, 3, 3)
            sage: Y.singular_locus()
            0-dimensional subscheme of degree 5 in PP^5

        """
        try:
            return self._singular_locus
        except AttributeError:
            self._singular_locus = Embedded_projective_variety(self.ambient_space(), _minbase(self.Jacobian()))
            return self._singular_locus

    def to_built_in_variety(self):
        r"""Return the same mathematical object but in the parent class.

        OUTPUT:

        :class:`AlgebraicScheme_subscheme_projective`

        EXAMPLES::

            sage: Veronese(1,3)
            cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            sage: _.to_built_in_variety()
            Closed subscheme of Projective Space of dimension 3 over Finite Field of size 33331 defined by:
            x2^2 - x1*x3,
            x1*x2 - x0*x3,
            x1^2 - x0*x2

        """
        try:
            return self._to_built_in_variety
        except AttributeError:
            self._to_built_in_variety = self.ambient_space().subscheme(self.defining_ideal())
            return self._to_built_in_variety

    def embedding_morphism(self, codomain=None):
        r"""Return the embedding morphism of the variety in its ambient space.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`

        EXAMPLES::

            sage: X = Veronese(1,2)
            sage: X.embedding_morphism()
            morphism defined by forms of degree 1
            source: conic curve in PP^2
            target: PP^2
            image: conic curve in PP^2

        """
        if codomain is not None:
            if not self.is_subset(codomain):
                raise Exception("expected containment")
            return(Rational_map_between_embedded_projective_varieties(self,codomain,self.coordinate_ring().gens()))
        try:
            return self._embedding_morphism
        except AttributeError:
            self._embedding_morphism = Rational_map_between_embedded_projective_varieties(self,self.ambient(),self.coordinate_ring().gens())
            self._embedding_morphism._closure_of_image = self
            self._embedding_morphism._is_birational = self._embedding_morphism.is_dominant()
            self._embedding_morphism._is_morphism = True
            return self._embedding_morphism

    def _homogeneous_component(self, n, trim=True):
        r"""Return a basis for the homogeneous component of degree ``n`` of the defining ideal of the variety.

        TESTS::

            sage: C = Veronese(1,3)
            sage: F = C._homogeneous_component(2); F
            [x2^2 - x1*x3, x1*x2 - x0*x3, x1^2 - x0*x2]
            sage: assert(C._homogeneous_component(2) is F)

        """
        if n in self._homogeneous_components_ideal:
            return self._homogeneous_components_ideal[n]
        if not isinstance(n,(int,Integer)):
            raise TypeError("expected an integer")
        if not isinstance(trim,bool):
            raise TypeError("expected True or False")
        I = self.defining_ideal()
        R = I.ring()
        B = []
        for g in I.gens():
            if g.degree() <= n:
                B = B + (g * ideal(R.gens()) ** (n-g.degree())).gens()
        if len(B) > 0 and trim:
            B = _minbase(ideal(B))
        if trim:
            self._homogeneous_components_ideal.update({n:B})
        return(B)

    def linear_span(self):
        r"""Return the linear span of the variety.

        OUTPUT:

        :class:`Embedded_projective_variety`

        EXAMPLES::

            sage: X = PP(5).empty().random(1,1,2)
            sage: X.linear_span()
            linear 3-dimensional subspace of PP^5
            sage: X.is_subset(_)
            True

        """
        L = self._homogeneous_component(1, trim=True)
        if len(L) == 0:
            return self.ambient()
        return Embedded_projective_variety(self.ambient_space(),L)

    def random(self, *args):
        r"""Return a random complete intersection containing the variety.

        INPUT:

        A tuple of positive integers ``(a,b,c,...)``

        OUTPUT:

        :class:`Embedded_projective_variety`, a random complete intersection of type ``(a,b,c,...)`` containing the variety.

        An exception is raised if such a complete intersection does not exist.

        EXAMPLES::

            sage: X = Veronese(1,5)
            sage: X.random(2,3)
            complete intersection of type (2, 3) in PP^5
            sage: X.is_subset(_)
            True

        """
        if len(args) == 0:
            return self.ambient()
        for i in args:
            if not(isinstance(i,(Integer,int)) and i>0):
                raise TypeError("expected a tuple of positive integers")
        if self.codimension() == 0:
            raise ValueError("no hypersurface contains the ambient space")
        if len(args) > self.codimension():
            raise ValueError("too many degrees are given")
        K = self.base_ring()
        L = []
        for i in set(args):
            B = self._homogeneous_component(i, trim=False)
            L.extend([sum([K.random_element() * g for g in B]) for i in range(args.count(i))])
        X = Embedded_projective_variety(self.ambient_space(),L)
        if X.codimension() != len(args):
            raise Exception("unable to construct complete intersection containing the variety, maybe too many degrees are given")
        else:
            return(X)

    def empty(self):
        r"""Return the empty subscheme of the variety (and of its ambient space)

        EXAMPLES::

            sage: X = PP(3)
            sage: X.empty()
            empty subscheme of PP^3

        """
        return(Embedded_projective_variety(self.ambient_space(),[self.ambient_space().coordinate_ring().one()]))

    def random_coordinate_change(self):
        r"""Apply a random coordinate change on the ambient projective space of ``self``.

        EXAMPLES::

            sage: from sage.misc.randstate import set_random_seed
            sage: set_random_seed(0)
            sage: C = Veronese(1,3,KK=GF(13))
            sage: C.defining_ideal()
            Ideal (x2^2 - x1*x3, x1*x2 - x0*x3, x1^2 - x0*x2) of Multivariate Polynomial Ring in x0, x1, x2, x3 over Finite Field of size 13
            sage: D = C.random_coordinate_change()
            sage: D.defining_ideal()
            Ideal (2*x0^2 + 5*x0*x1 - 4*x1^2 - 2*x0*x2 - x1*x2 + 3*x2^2 - 2*x0*x3 + x1*x3 + 2*x2*x3 + 6*x3^2, 6*x0^2 + x0*x1 + 5*x1^2 - x0*x2 - 4*x1*x2 - 2*x2^2 - x0*x3 - 4*x1*x3 - 6*x2*x3 + 4*x3^2, -5*x0^2 - 3*x0*x1 + 5*x1^2 - 3*x0*x2 + 5*x1*x2 + 6*x2^2 + 4*x0*x3 - x1*x3 + 4*x2*x3 - 2*x3^2) of Multivariate Polynomial Ring in x0, x1, x2, x3 over Finite Field of size 13

        TESTS::

            sage: h = D._from_random_coordinate_change
            sage: assert(h.source() is C and h.target() is D)
            sage: assert(h(C.point()).is_subset(D))

        """
        K = self.base_ring()
        n = self.ambient().dimension()
        A = matrix(K, [[K.random_element() for i in range(n+1)] for j in range(n+1)])
        B = A.inverse()
        f = rational_map(self.ambient(), self.ambient(), (matrix(self.ambient().coordinate_ring().gens()) * A).list())
        g = rational_map(self.ambient(), self.ambient(), (matrix(self.ambient().coordinate_ring().gens()) * B).list())
        Y = Embedded_projective_variety(self.ambient_space(), (g._to_ring_map()(self.defining_ideal())).gens())
        f = rational_map(self, Y, f.defining_polynomials())
        g = rational_map(Y, self, g.defining_polynomials())
        assert(f.compose(g) == 1 and g.compose(f) == 1)
        f._is_isomorphism, f._is_birational, f._is_dominant, f._is_morphism = True, True, True, True
        g._is_isomorphism, g._is_birational, g._is_dominant, g._is_morphism = True, True, True, True
        f._inverse_rational_map = g
        g._inverse_rational_map = f
        Y._from_random_coordinate_change = f
        return Y

    def is_subset(self,Y):
        r"""Return ``True`` if ``self`` is contained in ``Y``, ``False`` otherwise.

        OUTPUT:

        :class:`bool`

        TESTS::

            sage: X = surface(3,4)
            sage: Y = X.intersection(X.empty().random(2)); Y
            curve of degree 10 and arithmetic genus 6 in PP^5 cut out by 6 hypersurfaces of degree 2
            sage: assert(Y.is_subset(X) and (not X.is_subset(Y)) and X.is_subset(X.ambient()) and (not X.ambient().is_subset(X)))
            sage: assert(not(X.is_subset(PP(2))))

        """
        Y = _check_type_embedded_projective_variety(Y)
        if self is Y:
            return True
        I = self.defining_ideal()
        J = Y.defining_ideal()
        if I.ring() is not J.ring():
            return False
        for g in J.gens():
            if not(g in I):
                return False
        return True

    def __eq__(self, Y):
        r"""Return ``True`` if ``self`` is mathematically equal to ``Y``, ``False`` otherwise.

        OUTPUT:

        :class:`bool`

        TESTS::

            sage: X = Veronese(2,2)
            sage: Y = X.point()
            sage: X == Y
            False
            sage: X == Veronese(2,2)
            True
            sage: X is Veronese(2,2)
            False
            sage: Y == PP(3)
            False

        """
        if not self.is_subset(Y):
            return False
        return Y.is_subset(self)

    def __ne__(self, Y):
        return(not(self.__eq__(Y)))

    def _macaulay2_init_(self, macaulay2=None):
        r"""Get the corresponding embedded projective variety in Macaulay2."""
        if macaulay2 is None:
            from sage.interfaces.macaulay2 import macaulay2 as m2_default
            macaulay2 = m2_default
        try:
            return self._macaulay2_object
        except AttributeError:
            self._macaulay2_object = macaulay2(self.coordinate_ring()).projectiveVariety().removeUnderscores()
            self._macaulay2_object._sage_object = self
            return self._macaulay2_object

    def parametrize(self, verbose=None):
        r"""Try to return a rational parameterization of the variety.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`, a birational map from ``PP(n)`` to ``self``, where ``n`` is the dimension of ``X``.

        An exception is raised if something goes wrong.

        EXAMPLES::

            sage: S = surface(5,7,0,1)
            sage: h = S.parametrize()
            sage: h
            dominant rational map defined by forms of degree 5
            source: PP^2
            target: surface in PP^7 of degree 9 and sectional genus 3 cut out by 12 hypersurfaces of degree 2

            sage: L = PP(7).empty().random(1,1,1,1)
            sage: L.parametrize()
            dominant rational map defined by forms of degree 1
            source: PP^3
            target: linear 3-dimensional subspace of PP^7

            sage: L.ambient().parametrize()
            dominant rational map defined by forms of degree 1
            source: PP^7
            target: PP^7

            sage: with seed(0): p = PP(4,KK=GF(65521)).point(); p
            one-point scheme in PP^4 of coordinates [1, 37782, 10657, 17260, 21224]
            sage: p.parametrize()
            dominant rational map defined by forms of degree 1
            source: PP^0
            target: one-point scheme in PP^4 of coordinates [1, 37782, 10657, 17260, 21224]

            sage: Veronese(2,2).parametrize()
            dominant rational map defined by forms of degree 2
            source: PP^2
            target: surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2

            sage: C = Veronese(2,2).intersection(PP(5).empty().random(1)); C
            curve of degree 4 and arithmetic genus 0 in PP^5 cut out by 7 hypersurfaces of degrees (1, 2, 2, 2, 2, 2, 2)
            sage: C.parametrize(verbose=False)            # optional - macaulay2
            rational map defined by forms of degree 4
            source: PP^1
            target: curve of degree 4 and arithmetic genus 0 in PP^5 cut out by 7 hypersurfaces of degrees (1, 2, 2, 2, 2, 2, 2)

        """
        if verbose is None:
            verbose = __VERBOSE__
        try:
            return self._parametrization.make_dominant()
        except AttributeError:
            if self.codimension() == 0:
                f = self.embedding_morphism(self)
                assert(f.image() is self and f.is_dominant())
                self._parametrization = f
                return self._parametrization
            if all(i == 1 for i in self.degrees_generators()):
                I = self.defining_ideal()
                M = jacobian(I.gens(),I.ring().gens()).change_ring(I.ring().base_ring())
                assert((M * matrix([I.ring().gens()]).transpose()).list() == I.gens())
                P = ProjectiveSpace(self.dimension(), self.base_ring(), 'z')
                polys = (matrix(P.coordinate_ring().gens()) * M.right_kernel_matrix()).list()
                f = rational_map(P,self,polys)
                assert(f.image() is self and f.is_dominant())
                self._parametrization = f
                return self._parametrization
            X = macaulay2(self)
            if verbose:
                print("-- running Macaulay2 function parametrize()... --")
            try:
                psi = X.parametrize()
            except Exception as err:
                raise NotImplementedError(err)
            if verbose:
                print("-- function parametrize has successfully terminated. --")
            psi = _from_macaulay2map_to_sagemap(psi, Sage_Target = self)
            assert(psi.target() is self)
            return psi

    def intersection(self, other):
        r"""Return the scheme-theoretic intersection of ``self`` and ``other`` in their common ambient space.

        EXAMPLES::

            sage: o = PP(5).empty()
            sage: X = o.random(2,2)
            sage: Y = o.random(1,3)
            sage: X.intersection(Y)
            curve of degree 12 and arithmetic genus 13 in PP^5 cut out by 4 hypersurfaces of degrees (1, 2, 2, 3)

        """
        other = _check_type_embedded_projective_variety(other)
        if self.ambient() != other.ambient():
            raise ValueError("expected varieties in the same ambient projective space")
        I = self.defining_ideal() + other.defining_ideal()
        I = (I.saturation(I.ring().irrelevant_ideal()))[0]
        return Embedded_projective_variety(self.ambient_space(),_minbase(I))

    def union(self, other):
        r"""Return the scheme-theoretic union of ``self`` and ``other`` in their common ambient space.

        EXAMPLES::

            sage: P = PP(5)
            sage: X = P.point()
            sage: Y = P.point()
            sage: X.union(Y)
            0-dimensional subscheme of degree 2 in PP^5
            sage: X.union(Y) == X + Y
            True

        """
        other = _check_type_embedded_projective_variety(other)
        if self.ambient() != other.ambient():
            raise ValueError("expected varieties in the same ambient projective space")
        I = self.defining_ideal().intersection(other.defining_ideal())
        return Embedded_projective_variety(self.ambient_space(),_minbase(I))

    def __add__(self, other):
        return self.union(other)

    def difference(self, other):
        r"""Return the Zariski closure of the difference of ``self`` by ``other``.

        EXAMPLES::

            sage: X = Veronese(1,3)
            sage: Y = X.ambient().point()
            sage: Z = X.union(Y)
            sage: Z.difference(Y) == X and Z.difference(X) == Y
            True
            sage: Z - Y == X and Z - X == Y
            True

        """
        other = _check_type_embedded_projective_variety(other)
        if self.ambient() != other.ambient():
            raise ValueError("expected varieties in the same ambient projective space")
        I = (self.defining_ideal().saturation(other.defining_ideal()))[0]
        return Embedded_projective_variety(self.ambient_space(), _minbase(I))

    def __sub__(self, other):
        return self.difference(other)

    def hyperplane_section(self, cache=True):
        r"""Return a random hyperplane section of the variety.

        OUTPUT:

        :class:`Embedded_projective_variety`, the intersection of ``self`` with a random hyperplane of the ambient projective space.

        EXAMPLES::

            sage: X = Veronese(2,2)
            sage: H = X.hyperplane_section(); H
            curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2
            sage: j = H.embedding_as_hyperplane_section(); j
            rational map defined by forms of degree 1
            source: curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2
            target: surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2
            sage: j.source() is H and j.target() is X
            True
            sage: j.image()
            curve of degree 4 and arithmetic genus 0 in PP^5 cut out by 7 hypersurfaces of degrees (1, 2, 2, 2, 2, 2, 2)

        """
        if cache and hasattr(self,"_random_hyperplane_section"):
            return self._random_hyperplane_section
        H = self.ambient().empty().random(1)
        j = H.parametrize().super().restriction_from_target(self)
        X = j.source()
        X.embedding_as_hyperplane_section = lambda : j
        if cache:
            self._random_hyperplane_section = X
        return X

    def _change_of_coordinates_first_fundamental_point(self):
        r"""Take an automorphism of the ambient projective space that sends the point ``self``
        to the point ``(1,0,...,0)``. This is an auxiliary function for :meth:`cone_of_lines`.
        """
        a = self._coordinates() # expected a point
        j0 = 0
        while a[j0] == 0:
            j0 += 1
        n = self.ambient().dimension()
        A = matrix(self.base_ring(), [a] + [[1 if i == j else 0 for i in range(n+1)] for j in range(n+1) if j != j0])
        B = A.inverse()
        f = rational_map(self.ambient(), self.ambient(), (matrix(self.ambient().coordinate_ring().gens()) * A).list())
        g = rational_map(self.ambient(), self.ambient(), (matrix(self.ambient().coordinate_ring().gens()) * B).list())
        # assert(f.compose(g) == 1 and g(self)._coordinates() == [1]+[0 for i in range(n)])
        return (f,g)

    def cone_of_lines(self, point=None):
        r"""Return the union of the lines contained in ``self`` and passing through the point ``point``.
        If ``point`` is not given, a random point on ``self`` is used.

        EXAMPLES::

            sage: from sage.misc.randstate import set_random_seed
            sage: set_random_seed(12345)
            sage: Q = PP(3,KK=GF(333331)).empty().random(2); Q
            quadric surface in PP^3
            sage: p = Q.point()
            sage: Q.cone_of_lines(p).irreducible_components()
            [line in PP^3, line in PP^3]

        """
        if point is None:
            point = self.point()
        (f,g) = point._change_of_coordinates_first_fundamental_point()
        x0 = self.ambient().coordinate_ring().gen()
        polys = f._to_ring_map()(self.defining_ideal()).gens()
        Z = [pol.subs({x0:0}) for pol in polys]
        for pol in polys:
            Z.extend([pol.coefficient(x0 ** i) for i in range(1,pol.degree()+1)])
        V = Embedded_projective_variety(self.ambient_space(), _minbase(g._to_ring_map()(ideal(Z))))
        V = V.difference(point)
        assert(V.is_subset(self) and (point.is_subset(V) or V.dimension() < 0))

        def fast_dec(degree=Infinity):
            if V.dimension() != 1:
                raise Exception("cone of lines must have dimension 1")
            Y = V.hyperplane_section()
            h = rational_map([_random1(Y.ambient().coordinate_ring()),_random1(Y.ambient().coordinate_ring())])
            hY = h(Y)
            pts_on_PP1 = [q for q in hY.irreducible_components() if q.dimension() == 0 and q.degree() <= degree]
            W = [(Y.embedding_as_hyperplane_section()(Y.intersection(h.inverse_image(q)))).union(point) for q in pts_on_PP1]
            assert([(w.dimension(),w.degree()) for w in W] == [(0,q.degree()+1) for q in pts_on_PP1])
            return W

        V._fast_decomposition = fast_dec
        V._vertex_point = point
        return V

def _is_embedded_projective_variety(X):
    r"""whether ``X`` can be included in the class `Embedded_projective_variety``"""
    if isinstance(X,(Embedded_projective_variety,AlgebraicScheme_subscheme_projective)):
        return True
    if (hasattr(X,"ambient_space") and X is X.ambient_space() and X.is_projective()):
        return True
    return False

def _check_type_embedded_projective_variety(X):
    r"""check if ``X`` can be included in the class `Embedded_projective_variety``"""
    if not _is_embedded_projective_variety(X):
        raise TypeError("expected an embedded projective variety")
    if isinstance(X,Embedded_projective_variety):
        return X
    return Embedded_projective_variety(X)

@cached_function
def PP(n, KK=33331, var='x'):
    r"""Projective space of dimension ``n`` over ``KK``.

    EXAMPLES::

        sage: PP(5,33331,var='t')
        PP^5
        sage: _.coordinate_ring()
        Multivariate Polynomial Ring in t0, t1, t2, t3, t4, t5 over Finite Field of size 33331
        sage: PP(5,33331,var='t') is PP(5,GF(33331),var='t')
        True

    """
    if isinstance(KK,(int,Integer)):
        KK = GF(KK) if KK > 0 else QQ
        return PP(n, KK, var)
    return projective_variety(ProjectiveSpace(n, KK, var))

def projective_variety(I, PP=None):
    r"""Construct a projective variety.

    INPUT:

    ``I`` -- A homogeneous ideal in a polynomial ring over a field, or the list of its generators.

    ``PP`` -- (Optional) an ambient projective space whose coordinate ring is the polynomial ring of ``I``.

    OUTPUT:

    :class:`Embedded_projective_variety`, the projective variety defined by ``I``.

    EXAMPLES::

        sage: (x0,x1,x2,x3) = ProjectiveSpace(3, GF(101), 'x').gens()
        sage: I = [x0^2-x1*x2, x1^3+x2^3+x3^3]
        sage: X = projective_variety(I); X
        curve of degree 6 and arithmetic genus 4 in PP^3 cut out by 2 hypersurfaces of degrees (2, 3)

    You can also use this function to convert objects of the class :class:`AlgebraicScheme_subscheme_projective`
    into objects of the class :class:`Embedded_projective_variety`.

    ::

        sage: Y = X.ambient_space().subscheme(I); Y
        Closed subscheme of Projective Space of dimension 3 over Finite Field of size 101 defined by:
        x0^2 - x1*x2,
        x1^3 + x2^3 + x3^3
        sage: projective_variety(Y)
        curve of degree 6 and arithmetic genus 4 in PP^3 cut out by 2 hypersurfaces of degrees (2, 3)
        sage: _ == X
        True

    """
    if PP is None:
        if isinstance(I,Embedded_projective_variety):
            return I
        if _is_embedded_projective_variety(I):
            return Embedded_projective_variety(I)
        if isinstance(I,MPolynomialIdeal):
            return Embedded_projective_variety(ProjectiveSpace(I.ring()).subscheme(I))
        if isinstance(I,(tuple,list)):
            return projective_variety(ideal(I))
    else:
        if isinstance(I,(tuple,list)):
            return Embedded_projective_variety(PP, I)
        if isinstance(I,MPolynomialIdeal):
            return Embedded_projective_variety(PP, I.defining_polynomials())
    raise TypeError

class Rational_map_between_embedded_projective_varieties(SchemeMorphism_polynomial_projective_space_field):
    r"""The class of rational maps between closed subvarieties of projective spaces.

    This is a subclass of the class :class:`SchemeMorphism_polynomial_projective_space_field`.
    It is designed to provide better support for maps related to Hodge-special fourfolds.

    Constructing a rational map between projective subvarieties.

    .. WARNING::

        You should not create objects of this class directly. The
        preferred method to construct such maps is to use
        :meth:`rational_map`.

    INPUT:

    - ``X`` -- the source variety (optional).
    - ``Y`` -- the target variety (optional).
    - ``polys`` -- a list of homogeneous polynomials of the same degree in the coordinate ring of ``X``

    OUTPUT:

    The rational map from ``X`` to ``Y`` defined by ``polys``.

    If ``X`` and ``Y`` are not objects of the class :class:`Embedded_projective_variety`,
    they will be replaced by ``projective_variety(X)`` and ``projective_variety(Y)`` (if any exception occurs),
    see :meth:`projective_variety`.

    EXAMPLES::

        sage: X = PP(4,GF(33331))
        sage: Y = PP(5,GF(33331))
        sage: x0, x1, x2, x3, x4 = X.coordinate_ring().gens()
        sage: f = rational_map(X, Y, [x3^2-x2*x4, x2*x3-x1*x4, x1*x3-x0*x4, x2^2-x0*x4, x1*x2-x0*x3, x1^2-x0*x2]); f
        rational map defined by forms of degree 2
        source: PP^4
        target: PP^5
        sage: g = f.make_dominant(); g
        dominant rational map defined by forms of degree 2
        source: PP^4
        target: quadric hypersurface in PP^5

    You can also convert such rational maps into ``Macaulay2`` objects.

    ::

        sage: g_ = macaulay2(g); g_                                           # optional - macaulay2
        multi-rational map consisting of one single rational map
        source variety: PP^4
        target variety: hypersurface in PP^5 defined by a form of degree 2
        <BLANKLINE>
        MultirationalMap (rational map from PP^4 to hypersurface in PP^5)
        sage: g_.graph().last().inverse()                                     # optional - macaulay2
        multi-rational map consisting of 2 rational maps
        source variety: hypersurface in PP^5 defined by a form of degree 2
        target variety: 4-dimensional subvariety of PP^4 x PP^5 cut out by 9 hypersurfaces of multi-degrees (0,2)^1 (1,1)^8
        dominance: true
        degree: 1
        <BLANKLINE>
        MultirationalMap (birational map from hypersurface in PP^5 to 4-dimensional subvariety of PP^4 x PP^5)

    """
    def __init__(self, X, Y, polys):
        r"""See :class:`Rational_map_between_embedded_projective_varieties` for documentation."""
        if Y is None:
            if len(polys) > 0:
                Y = PP(len(polys)-1, X.base_ring(), 'y')
            else:
                Y = ProjectiveSpace(0, X.base_ring(), 'empty')
                Y = Embedded_projective_variety(Y,[Y.coordinate_ring().one()])
                polys = [X.coordinate_ring().one()]
        X = _check_type_embedded_projective_variety(X)
        Y = _check_type_embedded_projective_variety(Y)
        assert(isinstance(X,Embedded_projective_variety) and isinstance(Y,Embedded_projective_variety))
        if X.base_ring() is not Y.base_ring():
            raise ValueError("different base rings found")
        if not isinstance(polys,tuple):
            polys = tuple(polys)
        if len(polys) != Y.ambient().dimension() + 1:
            raise ValueError("got wrong number of polynomials")
        H = X.Hom(Y)
        gensR = matrix(polys).base_ring().gens()
        if len(gensR) != X.ambient().coordinate_ring().ngens():
            raise ValueError("expected polynomials in the coordinate ring of the source")
        s = dict(zip(gensR, X.ambient().coordinate_ring().gens()))
        polys = tuple([pol.subs(s) for pol in polys])
        SchemeMorphism_polynomial_projective_space.__init__(self, H, polys)
        assert(self.domain() is X)
        assert(self.codomain() is Y)
        # assert(self.defining_polynomials() == polys) # this fails
        degs = [g.lift().degree() if hasattr(g,"lift") and (not hasattr(g,"degree")) else g.degree() for g in [pol for pol in polys if pol != 0]]
        self.__degree_Forms = max(degs)
        assert(self.__degree_Forms == min(degs))
        self._source = X
        self._target = Y
        self._is_isomorphism = None
        self._is_birational = None
        self._is_dominant = True if self.target().dimension() < 0 else None
        self._is_morphism = None

    def _repr_(self):
        r"""Return a string representation of the rational map

        OUTPUT:

        A string.

        EXAMPLES::

            sage: veronese(1,4)._repr_()
            'rational map defined by forms of degree 4\nsource: PP^1\ntarget: PP^4'

        """
        if self.target().dimension() < 0:
            return("empty rational map" + "\nsource: " + self.source()._repr_() + "\ntarget: " + self.target()._repr_())
        type_map = "rational map"
        if hasattr(self,"_base_locus") or hasattr(self,"_list_of_representatives_of_map"):
            self.is_morphism()
        if self._is_morphism is True:
            type_map = "morphism"
        if self._is_isomorphism is True:
            type_map = "isomorphism"
        else:
            if self._is_birational is True:
                if self._is_morphism is True:
                    type_map = "birational morphism"
                else:
                    type_map = "birational map"
            else:
                if self._is_dominant is True:
                    if self._is_morphism is True:
                        type_map = "dominant morphism"
                    else:
                        type_map = "dominant rational map"
        M = type_map + " defined by forms of degree " + str(self._degree_forms()) + "\nsource: " + self.source()._repr_() + "\ntarget: " + self.target()._repr_()
        if hasattr(self,"_base_locus") and self._is_morphism is not True:
            M = M + "\nbase locus: " + self.base_locus()._repr_()
        if hasattr(self,"_list_of_representatives_of_map") and len(self._representatives()) > 1:
            M = M + "\ndegree sequence: " + str(tuple([f._degree_forms() for f in self._representatives()]))
        if hasattr(self,"_projective_degrees_list"):
            M = M + "\nprojective degrees: " + str(tuple(self.projective_degrees()))
        if hasattr(self,"_closure_of_image") and self._is_dominant is not True:
            M = M + "\nimage: " + self.image()._repr_()
        return M

    def _latex_(self):
        r"""Return the LaTeX representation of ``self``.

        OUTPUT:

        A string.

        EXAMPLES::

            sage: latex(veronese(1,4))
            \mbox{rational map defined by forms of degree } 4 \newline \mbox{source: } \mathbb{P}^{ 1 } \newline \mbox{target: } \mathbb{P}^{ 4 }

        """
        if self.target().dimension() < 0:
            return("\\mbox{empty rational map}" + "\\newline \\mbox{source: }" + latex(self.source()) + "\\newline \\mbox{target: }" + latex(self.target()))
        type_map = "rational map"
        if hasattr(self,"_base_locus") or hasattr(self,"_list_of_representatives_of_map"):
            self.is_morphism()
        if self._is_morphism is True:
            type_map = "morphism"
        if self._is_isomorphism is True:
            type_map = "isomorphism"
        else:
            if self._is_birational is True:
                if self._is_morphism is True:
                    type_map = "birational morphism"
                else:
                    type_map = "birational map"
            else:
                if self._is_dominant is True:
                    if self._is_morphism is True:
                        type_map = "dominant morphism"
                    else:
                        type_map = "dominant rational map"
        M = "\\mbox{" + type_map + " defined by forms of degree }" + latex(self._degree_forms()) + "\\newline \\mbox{source: }" + latex(self.source()) + "\\newline \\mbox{target: }" + latex(self.target())
        if hasattr(self,"_base_locus") and self._is_morphism is not True:
            M = M + "\\newline\\mbox{base locus: }" + latex(self.base_locus())
        if hasattr(self,"_list_of_representatives_of_map") and len(self._representatives()) > 1:
            M = M + "\\newline\\mbox{degree sequence: }" + latex(tuple([f._degree_forms() for f in self._representatives()]))
        if hasattr(self,"_projective_degrees_list"):
            M = M + "\\newline\\mbox{projective degrees: }" + latex(tuple(self.projective_degrees()))
        if hasattr(self,"_closure_of_image") and self._is_dominant is not True:
            M = M + "\\newline\\mbox{image: }" + latex(self.image())
        return M

    def source(self):
        r"""Return the source of the rational map

        OUTPUT:

        :class:`Embedded_projective_variety`, the source variety, which always coincides with ``projective_variety(self.domain())``.

        EXAMPLES::

            sage: f = veronese(1,4)
            sage: f.source()
            PP^1

        """
        return(self._source)

    def target(self):
        r"""Return the target of the rational map

        OUTPUT:

        :class:`Embedded_projective_variety`, the target variety, which always coincides with ``projective_variety(self.codomain())``.

        EXAMPLES::

            sage: f = veronese(1,4)
            sage: f.target()
            PP^4

        """
        return(self._target)

    def _degree_forms(self):
        r"""Return the common degree of the polynomials defining the map"""
        return(self.__degree_Forms)

    def super(self):
        r"""Return the composition of ``self`` with the embedding of the target in the ambient space.

        :class:`Rational_map_between_embedded_projective_varieties`

        EXAMPLES::

            sage: f = veronese(1,4).make_dominant(); f
            dominant rational map defined by forms of degree 4
            source: PP^1
            target: curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2
            sage: g = f.super(); g
            rational map defined by forms of degree 4
            source: PP^1
            target: PP^4
            image: curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2
            sage: g.super() is g
            True

        """
        try:
            return self._super_map
        except AttributeError:
            if self.target().ambient() is self.target():
                self._super_map = self
            else:
                self._super_map = Rational_map_between_embedded_projective_varieties(self.source(),self.target().ambient(),self.defining_polynomials())
                if self._is_dominant is True or hasattr(self,"_closure_of_image"):
                    self._super_map._closure_of_image = self.image()
                if hasattr(self,"_list_of_representatives_of_map"):
                    self._super_map._list_of_representatives_of_map = [Rational_map_between_embedded_projective_varieties(self.source(),self.target().ambient(),f.defining_polynomials()) for f in self._representatives(verbose=False)]
                self._super_map._is_morphism = self._is_morphism
                if hasattr(self,"_projective_degrees_list"):
                    self._super_map._projective_degrees_list = self.projective_degrees()
            return self._super_map

    def _to_ring_map(self):
        r"""Return the ring map from the coordinate ring of ``self.target()`` to the coordinate ring of ``self.source()`` defined by ``self.defining_polynomials()``"""
        try:
            return self.__to_ring_map
        except AttributeError:
            self.__to_ring_map = self.codomain().coordinate_ring().hom(self.defining_polynomials(),self.domain().coordinate_ring())
            return self.__to_ring_map

    def image(self, algorithm=None):
        r"""Return the (closure of the) image of the rational map.

        OUTPUT:

        :class:`Embedded_projective_variety`,  the closure of the image of ``self``, a subvariety of ``self.target()``.

        EXAMPLES::

            sage: f = veronese(1,4)
            sage: f.image()
            curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2

        TESTS::

            sage: f = f.restriction(f.source().point())
            sage: p = f.image(algorithm="built-in_kernel_ring_map")
            sage: assert(p._is_point())

        """
        if self._is_dominant is True:
            return(self.target())
        try:
            return self._closure_of_image
        except AttributeError:
            if algorithm == "built-in_kernel_ring_map":
                self._closure_of_image = Embedded_projective_variety(self.target().ambient_space(), _minbase(self.super()._to_ring_map().kernel()))
            else:
                K = self.source().base_ring()
                n = self.source().ambient().dimension()
                m = self.target().ambient().dimension()
                R = PolynomialRing(K,n+m+2,['x'+str(i) for i in range(n+1)]+['y'+str(j) for j in range(m+1)])
                x = R.gens()[:n+1]
                y = R.gens()[n+1:]
                s = dict(zip(self.source().ambient().coordinate_ring().gens(),x))
                F = [pol.subs(s) for pol in self.defining_polynomials()]
                I = [y[i] - F[i] for i in range(m+1)]
                if self.source().codimension() > 0:
                    I += [pol.subs(s) for pol in self.source().coordinate_ring().defining_ideal().gens()]
                I_sat = ideal(I).saturation(ideal(x))[0]
                I_sat_elim = I_sat.elimination_ideal(x,algorithm=algorithm)
                t = dict(zip(y,self.target().ambient().coordinate_ring().gens()))
                self._closure_of_image = Embedded_projective_variety(self.target().ambient_space(), _minbase(I_sat_elim.subs(t)))
            if self._closure_of_image == self.target():
                self._closure_of_image = self.target()
                self._is_dominant = True
            else:
                self._is_dominant = False
            return self._closure_of_image

    def __call__(self,Z):
        r"""Return the (closure of the) image of the variety ``Z`` via the rational map ``self``.

        INPUT:

        - ``Z``:class:`Embedded_projective_variety` -- a subvariety of ``self.source()``.

        OUTPUT:

        :class:`Embedded_projective_variety`, the closure of the image of ``Z`` via the rational map ``self``, a subvariety of ``self.target()``.

        EXAMPLES::

            sage: f = veronese(2,3)
            sage: p = f.source().point()
            sage: f(p).describe()
            dim:.................. 0
            codim:................ 9
            degree:............... 1
            sage: f.inverse_image(f(p)) == p
            True

        """
        Z = _check_type_embedded_projective_variety(Z)
        if not Z.is_subset(self.source()):
            raise ValueError("expected a subvariety of the source variety")
        return self.restriction(Z).image()

    def inverse_image(self, Z, trim=True):
        r"""Return the (closure of the) inverse image of the variety ``Z`` via the rational map ``self``.

        INPUT:

        - ``Z``:class:`Embedded_projective_variety` -- a subvariety of ``self.target().ambient()``.

        OUTPUT:

        :class:`Embedded_projective_variety`, the closure of the inverse image of ``Z`` via the rational map ``self``, a subvariety of ``self.source()``.

        EXAMPLES::

            sage: f = rational_map(Veronese(1,4)).make_dominant(); f
            dominant rational map defined by forms of degree 2
            source: PP^4
            target: quadric hypersurface in PP^5
            sage: Z = f.target().empty().random(1,1,1,1); Z
            line in PP^5
            sage: f.inverse_image(Z)
            0-dimensional subscheme of degree 2 in PP^4

        TESTS::

            sage: f = f.inverse()                                  # optional - macaulay2
            sage: W = f.target().empty().random(1,1,1,1)           # optional - macaulay2
            sage: f.inverse_image(W).describe()                    # optional - macaulay2
            dim:.................. 0
            codim:................ 5
            degree:............... 1

            sage: P = PP(5)
            sage: L = projective_variety(P.point().union(P.point())).random(1,1,1,1)
            sage: f = rational_map(L).restriction(L.random(2,2,2)).make_dominant(); f
            dominant rational map defined by forms of degree 1
            source: surface in PP^5 of degree 8 and sectional genus 5 cut out by 3 hypersurfaces of degree 2
            target: surface in PP^3 of degree 4 and sectional genus 3
            sage: q = f.inverse_image(f.target().point())          # optional - macaulay2
            sage: assert(q._is_point() and q.ambient() == P)       # optional - macaulay2

        """
        Z = _check_type_embedded_projective_variety(Z)
        if not Z.is_subset(self.super().target()):
            raise ValueError("expected a subvariety of the ambient target space")
        phi = self.super()._to_ring_map()
        B = ideal([phi(g) for g in phi.domain().gens()])
        J = Z.defining_ideal()
        phiJ = phi(J)
        R = phi.codomain()
        assert(R is self.source().coordinate_ring() and phiJ.ring() is R and B.ring() is R)
        if hasattr(R,"ambient") and hasattr(R,"defining_ideal"):
            phiJ = ideal([R.lift(g) for g in phiJ.gens()]) + R.defining_ideal()
            B = ideal([R.lift(b) for b in B.gens()]) + R.defining_ideal()
        assert(phiJ.ring() is self.source().ambient_space().coordinate_ring() and B.ring() is self.source().ambient_space().coordinate_ring())
        K = B.ring().base_ring()
        if len(set([b.degree() for b in B.gens()])) == 1:
            B = ideal(sum([K.random_element() * b for b in B.gens()]))
            assert(B.is_homogeneous())
        F = (phiJ.saturation(B))[0]
        assert(F.ring() is self.source().ambient_space().coordinate_ring())
        if trim:
            polys = _minbase(F)
        else:
            polys = F.gens()
        return Embedded_projective_variety(self.source().ambient_space(), polys)

    def _0th_projective_degree(self):
        r"""Return the first projective degree of the rational map (for internal use only)."""
        if self.source().dimension() > self.target().dimension():
            return 0
        L = self.target().empty().random(*[1 for i in range(self.source().dimension())])
        F = self.inverse_image(L,trim=False)
        assert(F.dimension() <= 0)
        if F.dimension() != 0:
            return 0
        return F.degree()

    def _restriction_to_general_hyperplane(self):
        r"""Return the restriction of the rational map to a random hyperplane section of the source variety (for internal use only).

        TESTS::

            sage: f = rational_map(Veronese(1,4)).make_dominant()
            sage: f._restriction_to_general_hyperplane()
            rational map defined by forms of degree 2
            source: PP^3
            target: quadric hypersurface in PP^5
            sage: f.inverse(verbose=False)._restriction_to_general_hyperplane()   # optional - macaulay2
            rational map defined by forms of degree 2
            source: quadric hypersurface in PP^4
            target: PP^4

        """
        j = self.source().empty().random(1).parametrize().super()
        if self.source().codimension() == 0:
            return j.compose(self)
        j = rational_map(j.inverse_image(self.source()), self.source(), j.defining_polynomials())
        return j.compose(self)

    def projective_degrees(self):
        r"""Return the projective degrees of the rational map

        .. WARNING::

            Currently, this uses a probabilistic approach which could give wrong answers
            (especially over finite fields of small order).

        OUTPUT:

        A list of integers.

        EXAMPLES::

            sage: (t0,t1,t2,t3,t4,t5,t6) = PP(6).coordinate_ring().gens()
            sage: f = rational_map(matrix([[t0,t1,t2,t3,t4],[t1,t2,t3,t4,t5],[t2,t3,t4,t5,t6]]).minors(3)); f
            rational map defined by forms of degree 3
            source: PP^6
            target: PP^9
            sage: f.projective_degrees()
            [1, 3, 9, 17, 21, 15, 5]

        TESTS::

            sage: F = macaulay2(f,'f')                          # optional - macaulay2
            sage: g = macaulay2('last(forceImage(f,image(f,2)), f = toRationalMap rationalMap(f,Dominant=>true), multirationalMap inverseMap(f))')   # optional - macaulay2
            sage: g = _from_macaulay2map_to_sagemap(g); g       # optional - macaulay2
            rational map defined by forms of degree 3
            source: 6-dimensional variety of degree 5 in PP^9 cut out by 5 hypersurfaces of degree 2
            target: PP^6
            base locus: 4-dimensional variety of degree 24 in PP^9 cut out by 12 hypersurfaces of degrees (2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3)
            sage: g.projective_degrees()                        # optional - macaulay2
            [5, 15, 21, 17, 9, 3, 1]

        """
        try:
            return self._projective_degrees_list
        except AttributeError:
            self._projective_degrees_list = []
            psi = self
            for i in range(self.source().dimension()):
                self._projective_degrees_list.append(psi._0th_projective_degree())
                psi = psi._restriction_to_general_hyperplane()
            self._projective_degrees_list.append(self.source().degree())
            self._projective_degrees_list.reverse()
            return self._projective_degrees_list

    def is_dominant(self):
        r"""Return ``True`` if ``self`` is a dominant rational map, ``False`` otherwise.

        OUTPUT:

        :class:`bool`, whether ``self.image() == self.target()``

        TESTS::

            sage: f = veronese(1,3)
            sage: f.is_dominant()
            False
            sage: g = f.make_dominant()
            sage: g.is_dominant()
            True

        """
        if self._is_dominant is None:
            self._is_dominant = self.image() == self.target()
        return self._is_dominant

    def make_dominant(self):
        r"""Return a new rational map with the same source variety and same defining polynomials but with ``self.target()`` replaced by ``self.image()``

        EXAMPLES::

            sage: f = veronese(1,4); f
            rational map defined by forms of degree 4
            source: PP^1
            target: PP^4
            sage: f.make_dominant()
            dominant rational map defined by forms of degree 4
            source: PP^1
            target: curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2

        """
        try:
            return self._dominant_map
        except AttributeError:
            if self.is_dominant():
                self._dominant_map = self
            else:
                self._dominant_map = Rational_map_between_embedded_projective_varieties(self.source(),self.image(),self.defining_polynomials())
                self._dominant_map._is_dominant = True
            return self._dominant_map

    def compose(self,f):
        r"""Return the composition of ``self`` with the rational map ``f``.

        INPUT:

        - ``f``:class:`Rational_map_between_embedded_projective_varieties` -- a rational map such that ``f.source() == self.target()``.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`, the composition of ``self`` with ``f``.

        EXAMPLES::

            sage: f = rational_map(Veronese(1,4))
            sage: g = rational_map(f.target().point())
            sage: f.compose(g)
            rational map defined by forms of degree 2
            source: PP^4
            target: PP^4
            sage: _.projective_degrees()
            [1, 2, 4, 4, 2]

        """
        g = f * self
        assert(g.domain() is self.domain() and g.codomain() is f.codomain())
        if isinstance(f,Rational_map_between_embedded_projective_varieties):
            Y = f.target()
        else:
            Y = f.codomain()
        g = Rational_map_between_embedded_projective_varieties(self.source(),Y,g.defining_polynomials())
        if isinstance(f,Rational_map_between_embedded_projective_varieties):
            if self._is_isomorphism is True and f._is_isomorphism is True:
                g._is_isomorphism = True
            if self._is_birational is True and f._is_birational is True:
                g._is_birational = True
            if self._is_dominant is True and f._is_dominant is True:
                g._is_dominant = True
            if self._is_morphism is True and f._is_morphism is True:
                g._is_morphism = True
        return g

    def restriction(self,X):
        r"""Return the restriction of ``self`` to the variety ``X``.

        INPUT:

        - ``X``:class:`Embedded_projective_variety` -- a subvariety of ``self.source()``.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`, the restriction of ``self`` to ``X``.

        TESTS::

            sage: X = fourfold(surface(1,ambient=7,KK=GF(3331)))
            sage: f = rational_map(X.surface(),1); f
            rational map defined by forms of degree 1
            source: PP^7
            target: PP^4
            sage: g = f.restriction(X.ambient_fivefold()); g
            rational map defined by forms of degree 1
            source: complete intersection of type (2, 2) in PP^7
            target: PP^4

        """
        Y = None if self.source().codimension() == 0 else self.source()
        j = X.embedding_morphism(Y)
        return(j.compose(self))

    def restriction_from_target(self,Y):
        r"""Return the restriction of ``self`` to the inverse image of the variety ``Y``.

        INPUT:

        - ``Y``:class:`Embedded_projective_variety` -- a subvariety of ``self.target().ambient()``.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`, the restriction of ``self`` to the inverse image of ``Y``.

        See also the methods: :meth:`inverse_image` and :meth:`restriction`.

        EXAMPLES::

            sage: f = veronese(2,2)
            sage: Y = f.target().empty().random(1)
            sage: f.restriction_from_target(Y)
            rational map defined by forms of degree 2
            source: conic curve in PP^2
            target: hyperplane in PP^5

        """
        if Y is self.target():
            return self
        X = self.inverse_image(Y)
        return Rational_map_between_embedded_projective_varieties(X, Y, self.defining_polynomials())

    def _macaulay2_init_(self, macaulay2=None):
        r"""Get the corresponding rational map in Macaulay2.

        TESTS::

            sage: f = veronese(1,4)
            sage: macaulay2(f)                # optional - macaulay2
            multi-rational map consisting of one single rational map
            source variety: PP^1
            target variety: PP^4
            <BLANKLINE>
            MultirationalMap (rational map from PP^1 to PP^4)

        """
        if macaulay2 is None:
            from sage.interfaces.macaulay2 import macaulay2 as m2_default
            macaulay2 = m2_default
        try:
            return self._macaulay2_object
        except AttributeError:
            X = macaulay2(self.source())
            F = macaulay2([list(self.defining_polynomials())])
            F = F.matrix().substitute(X.ambient().ring().vars()).entries()
            Y = macaulay2(self.target())
            if (macaulay2('SpecialFanoFourfolds.Options.Version >= "2.7.1"')).sage():
                self._macaulay2_object = X.Hom(Y)._operator(' ',F)
            else:
                h = (X.ring().map(Y.ring(),F.flatten())).rationalMap().multirationalMap()
                self._macaulay2_object = (h.multirationalMap(Y))._operator('|',X)
            self._macaulay2_object._sage_object = self
            return self._macaulay2_object

    def __eq__(self,other):
        r"""Return ``True`` if ``self`` is mathematically equal to ``other``, ``False`` otherwise.

        OUTPUT:

        :class:`bool`

        """
        if isinstance(other,(int,Integer)) and other == 1:
            if self.source() is not self.target():
                if __VERBOSE__:
                    print("-- rational map with source and target different --")
                return False
            return self.__eq__(self.source().embedding_morphism(codomain=self.target()))
        if not isinstance(other,(Rational_map_between_embedded_projective_varieties,SchemeMorphism_polynomial_projective_space_field)):
            raise TypeError("expected a rational map")
        if self is other:
            return True
        if self.source() is not other.source():
            if __VERBOSE__:
                print("-- rational maps with different sources --")
            return False
        if self.target() is not other.target():
            if __VERBOSE__:
                print("-- rational maps with different targets --")
            return False
        F = self.defining_polynomials()
        G = other.defining_polynomials()
        R = self.source().coordinate_ring()
        M = matrix(R,[F,G])
        for P in M.minors(2):
            if not P.is_zero():
                return False
        else:
            return True

    def __ne__(self,other):
        return(not(self.__eq__(other)))

    def inverse(self, check=True, verbose=None, algorithm='macaulay2'):
        r"""Return the inverse of the birational map.

        OUTPUT:

        :class:`Rational_map_between_embedded_projective_varieties`, the inverse rational map of ``self`` if ``self`` is birational, otherwise an exception is raised.

        EXAMPLES::

            sage: f = veronese(1,5).make_dominant()
            sage: g = f.inverse(); g                                         # optional - macaulay2
            birational morphism defined by forms of degree 1
            source: curve of degree 5 and arithmetic genus 0 in PP^5 cut out by 10 hypersurfaces of degree 2
            target: PP^1
            degree sequence: (1, 1, 1, 1, 1)
            sage: f.compose(g) == 1                                          # optional - macaulay2
            True

        With the input ``algorithm='macaulay2'`` the computation is transferred to ``Macaulay2`` (this is currently the only option).

        """
        if hasattr(self,"_inverse_rational_map"):
            return self._inverse_rational_map
        if self._is_birational is None and self.source().dimension() != self.target().dimension():
            self._is_birational = False
        if self._is_birational is False or self._is_dominant is False:
            raise ValueError("the rational map is not birational")
        if verbose is None:
            verbose = __VERBOSE__
        if not (isinstance(check,bool) and isinstance(verbose,bool)):
            raise TypeError("expected True or False")
        if algorithm != 'macaulay2':
            raise NotImplementedError("inverse of a birational map using built-in functions")
        f = macaulay2(self)
        if verbose:
            print("-- running Macaulay2 function inverse()... --")
        try:
            g = f.inverse(macaulay2("Verify")._operator('=>',macaulay2(-1)))
        except Exception as err:
            raise Exception(err)
        g = _from_macaulay2map_to_sagemap(g, self.target(), self.source())
        assert(g.source() is self.target() and g.target() is self.source())
        if check:
            p = self.source().point(verbose=False, algorithm=algorithm)
            assert(g(self(p)) == p)
            q = self.target().point(verbose=False, algorithm=algorithm)
            assert(self(g(q)) == q)
            if verbose:
                print("-- function inverse() has successfully terminated. --")
            self._is_birational = True
            assert(g._is_birational is True)
            g._inverse_rational_map = self
            self._inverse_rational_map = g
        return g

    def _representatives(self, verbose=None, algorithm='macaulay2'):
        r"""Return a minimal set of generators for the module of representatives of the rational map ``self``.

        This is used internally by the functions :meth:`base_locus` and :meth:`is_morphism`.
        """
        try:
            return self._list_of_representatives_of_map
        except AttributeError:
            if verbose is None:
                verbose = __VERBOSE__
            if not isinstance(verbose,bool):
                raise TypeError("expected True or False")
            if algorithm != 'macaulay2':
                raise NotImplementedError("representatives of a rational map using built-in functions")
            f = macaulay2(self).toRationalMap()
            if verbose:
                print("-- running Macaulay2 function to compute representatives of map... --")
            n = f.maps().length().sage()
            assert(isinstance(n,(int,Integer)))
            reprs = [macaulay2(i).matrix(f).entries().flatten().sage() for i in range(n)]
            s = dict(zip(matrix(reprs).base_ring().gens(), self.source().ambient_space().coordinate_ring().gens()))
            reprsN = [[pol.subs(s) for pol in repr] for repr in reprs]
            maps = [Rational_map_between_embedded_projective_varieties(self.source(),self.target(),F) for F in reprsN]
            if verbose:
                print("-- computation of representatives has terminated. --")
            self._list_of_representatives_of_map = maps
            return self._list_of_representatives_of_map

    def base_locus(self, verbose=None, algorithm='macaulay2'):
        r"""Return the base locus of the rational map ``self``.

        OUTPUT:

        :class:`Embedded_projective_variety` -- a subvariety of ``self.source()``.

        EXAMPLES::

            sage: f = rational_map(Veronese(1,3),Veronese(1,3).point().defining_polynomials()).make_dominant(); f
            dominant rational map defined by forms of degree 1
            source: cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            target: conic curve in PP^2
            sage: f.base_locus(verbose=False)                  # optional - macaulay2
            empty subscheme of PP^3
            sage: f                                            # optional - macaulay2
            dominant morphism defined by forms of degree 1
            source: cubic curve of arithmetic genus 0 in PP^3 cut out by 3 hypersurfaces of degree 2
            target: conic curve in PP^2
            degree sequence: (1, 1)

        This is used internally by the method :meth:`is_morphism`.
        """
        try:
            return self._base_locus
        except AttributeError:
            I = ideal(matrix([f.defining_polynomials() for f in self._representatives(verbose=verbose,algorithm=algorithm)]).minors(1))
            I = I + self.source().defining_ideal()
            I = (I.saturation(I.ring().irrelevant_ideal()))[0]
            self._base_locus = Embedded_projective_variety(self.source().ambient_space(),_minbase(I))
            return self._base_locus

    def is_morphism(self, verbose=None, algorithm='macaulay2'):
        r"""Return ``True`` if ``self`` is a morphism, ``False`` otherwise.

        OUTPUT:

        :class:`bool`, whether ``self.base_locus().dimension() == -1``

        """
        if self._is_morphism is None:
            self._is_morphism = self.base_locus(verbose=verbose,algorithm=algorithm).dimension() < 0
        return self._is_morphism

    def to_built_in_map(self):
        r"""Return the same mathematical object but in the parent class.

        OUTPUT:

        :class:`SchemeMorphism_polynomial_projective_space_field`

        EXAMPLES::

            sage: rational_map(Veronese(1,3))
            rational map defined by forms of degree 2
            source: PP^3
            target: PP^2
            sage: _.to_built_in_map()
            Scheme morphism:
              From: Closed subscheme of Projective Space of dimension 3 over Finite Field of size 33331 defined by:
              0
              To:   Closed subscheme of Projective Space of dimension 2 over Finite Field of size 33331 defined by:
              0
              Defn: Defined on coordinates by sending (x0 : x1 : x2 : x3) to
                    (x2^2 - x1*x3 : x1*x2 - x0*x3 : x1^2 - x0*x2)

        """
        try:
            return self._to_built_in_map
        except AttributeError:
            self._to_built_in_map = Hom(self.source().to_built_in_variety(),self.target().to_built_in_variety())(self.defining_polynomials())
            return self._to_built_in_map

    def random_coordinate_change(self):
        r"""Apply random coordinate changes on the ambient projective spaces of the source and target of ``self``.

        EXAMPLES::

            sage: from sage.misc.randstate import set_random_seed
            sage: set_random_seed(0)
            sage: f = veronese(1,3,KK=GF(13)); f
            rational map defined by forms of degree 3
            source: PP^1
            target: PP^3
            sage: f.defining_polynomials()
            (t1^3, t0*t1^2, t0^2*t1, t0^3)
            sage: g = f.random_coordinate_change(); g
            rational map defined by forms of degree 3
            source: PP^1
            target: PP^3
            sage: g.defining_polynomials()
            (-t0^3 - 6*t0^2*t1 - t0*t1^2 - 6*t1^3,
            5*t0^3 - 4*t0^2*t1 - 5*t0*t1^2 - 2*t1^3,
            4*t0^3 + 4*t0^2*t1 + t0*t1^2 + 4*t1^3,
            -t0^3 + 3*t0^2*t1 + 4*t0*t1^2 - t1^3)

        """
        f = self.source().random_coordinate_change()._from_random_coordinate_change.inverse()
        g = self.target().random_coordinate_change()._from_random_coordinate_change
        return f.compose(self).compose(g)

def rational_map(*args, **kwargs):
    r"""Construct a rational map from a projective variety to another.

    INPUT:

    - ``X`` -- the source variety (optional).
    - ``Y`` -- the target variety (optional).
    - ``polys`` -- a list of homogeneous polynomials of the same degree in the coordinate ring of ``X``

    OUTPUT:

    :class:`Rational_map_between_embedded_projective_varieties`, the rational map from ``X`` to ``Y`` defined by ``polys``.

    EXAMPLES::

        sage: x0, x1, x2, x3, x4 = PP(4,GF(33331)).coordinate_ring().gens()
        sage: rational_map([x3^2-x2*x4, x2*x3-x1*x4, x1*x3-x0*x4, x2^2-x0*x4, x1*x2-x0*x3, x1^2-x0*x2])
        rational map defined by forms of degree 2
        source: PP^4
        target: PP^5

    If we pass as input a projective variety and an integer ``d``, we get the rational map defined by the
    hypersurfaces of degree ``d`` that contain the given variety.

    ::

        sage: X = Veronese(1,4)
        sage: rational_map(X,2)
        rational map defined by forms of degree 2
        source: PP^4
        target: PP^5

    You can also use this function to convert objects of the class :class:`SchemeMorphism_polynomial_projective_space_field`
    into objects of the class :class:`Rational_map_between_embedded_projective_varieties`.

    ::

        sage: g = _.to_built_in_map()
        sage: rational_map(g)
        rational map defined by forms of degree 2
        source: PP^4
        target: PP^5

    """
    if len(args) == 3 and (args[0] is None or _is_embedded_projective_variety(args[0])) and (args[1] is None or _is_embedded_projective_variety(args[1])) and isinstance(args[2],(tuple,list)):
        polys = args[2]
        if args[0] is None and len(polys)==0:
            raise ValueError("expected a non-empty list of polynomials")
        X = projective_variety(args[0]) if args[0] is not None else projective_variety((ideal(polys)).ring().ideal())
        return Rational_map_between_embedded_projective_varieties(X, args[1], polys)
    if len(args) == 2 and _is_embedded_projective_variety(args[0]) and isinstance(args[1],(tuple,list)):
        return rational_map(args[0],None,args[1])
    if len(args) == 1 and isinstance(args[0],(tuple,list)):
        return rational_map(None,None,args[0])
    if len(args) == 2 and _is_embedded_projective_variety(args[0]) and isinstance(args[1],(int,Integer)):
        Z = projective_variety(args[0])
        d = args[1]
        E = Z._homogeneous_component(d)
        return rational_map(Z.ambient(), None, E)
    if len(args) == 1 and _is_embedded_projective_variety(args[0]):
        Z = args[0]
        d = max(Z.degrees_generators())
        return rational_map(Z,d)
    if len(args) == 1 and isinstance(args[0],Rational_map_between_embedded_projective_varieties):
            return args[0]
    if len(args) == 1 and isinstance(args[0],(SchemeMorphism_polynomial_projective_space_field, SchemeMorphism)):
            return rational_map(args[0].domain(),args[0].codomain(),args[0].defining_polynomials())
    if len(args) == 3 and _is_embedded_projective_variety(args[0]) and _is_embedded_projective_variety(args[1]) and isinstance(args[2],Rational_map_between_embedded_projective_varieties):
        if args[0] is args[2].source() and args[1] is args[2].target():
            return args[2]
        return rational_map(args[0],args[1],args[2].defining_polynomials())
    raise NotImplementedError

def veronese(n, d, KK=33331, var='x'):
    r"""Return the Veronese embedding.

    OUTPUT:

    :class:`Rational_map_between_embedded_projective_varieties`

    EXAMPLES::

        sage: veronese(2,3)
        rational map defined by forms of degree 3
        source: PP^2
        target: PP^9

    """
    if isinstance(KK,(int,Integer)):
        KK = GF(KK) if KK > 0 else QQ
        return veronese(n, d, KK=KK, var=var)
    return Rational_map_between_embedded_projective_varieties(PP(n,KK=KK,var='t'), PP(binomial(n+d,n)-1,KK=KK,var=var), PP(n,KK=KK,var='t').empty()._homogeneous_component(d))

def Veronese(n, d, KK=33331, var='x'):
    r"""Return the image of the Veronese embedding.

    OUTPUT:

    :class:`Embedded_projective_variety`

    EXAMPLES::

        sage: Veronese(2,2)
        surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2

    """
    f = veronese(n, d, KK=KK, var='x')
    X = f.image()
    X._parametrization = f  #f.make_dominant()
    return X

class _Rational_projective_surface(Embedded_projective_variety):
    r"""The class of objects created by the function ``surface``, see :meth:`surface`.

    .. WARNING::

        You should not create objects of this class directly. The
        preferred method to construct such surfaces is to use
        :meth:`surface`.

    """
    def _repr_(self):
        r"""Return a string representation of the surface"""
        s = _expr_var_1(super())[0]
        if s[0:7] == "surface":
            nodes = str(self._finite_number_of_nodes) + "-nodal " if hasattr(self,"_finite_number_of_nodes") and self._finite_number_of_nodes > 0 else ""
            s = "rational " + nodes + s
            if not self._is_ambient_space_forced:
                s = s + " (the image of the plane via the linear system " + str(self._linear_system) + ")"
        return s

    def _latex_(self):
        r"""Return the LaTeX representation of ``self``.

        EXAMPLES::

            sage: S = surface(3,1,1)
            sage: latex(S)
            \mbox{rational } \mbox{surface in }\mathbb{P}^{ 5 } \mbox{ of degree } 4 \mbox{ and sectional genus } 0 \mbox{ cut out by } 6 \mbox{ hypersurfaces of degree } 2 \mbox{ (the image of the plane via the linear system } \left[3, 1, 1\right] \mbox{)}

        """
        (s,s_l) = _expr_var_1(super())
        if s[0:7] == "surface":
            nodes = latex(self._finite_number_of_nodes) + "\\mbox{-nodal } " if hasattr(self,"_finite_number_of_nodes") and self._finite_number_of_nodes > 0 else ""
            s_l = "\\mbox{rational }" + nodes + s_l
            if not self._is_ambient_space_forced:
                s_l = s_l + "\\mbox{ (the image of the plane via the linear system }" + latex(self._linear_system) + "\\mbox{)}"
        return s_l

def surface(*args, KK=33331, ambient=None, nodes=None, virtual=False):
    r"""Return a rational surface in a projective space of dimension ``ambient`` over the field ``KK``.

    INPUT:

    - a tuple (a,i,j,k,...) of integers.

    - a base field ``KK`` or its characteristic.

    OUTPUT:

    :class:`Embedded_projective_variety`, the rational surface over ``KK`` obtained as the image
    of the plane via the linear system of curves of degree ``a`` having ``i`` general base points
    of multiplicity 1, ``j`` general base points of multiplicity 2, ``k`` general base points
    of multiplicity 3, and so on.

    EXAMPLES::

        sage: surface(3,1,1)
        rational surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 1, 1])

    """
    v = args
    for i in v:
        if not(isinstance(i,(Integer,int))):
            raise TypeError("expected a tuple of integers")
    if virtual:
        if nodes is not None:
            raise NotImplementedError("keyword 'nodes' must be None with virtual='True'")
        return _Virtual_rational_projective_surface(*args, KK=KK, ambient=ambient)
    R = PP(2,KK=KK,var='t').coordinate_ring()
    I = ideal(R.one())
    for i in range(1,len(v)):
        for j in range(v[i]):
            I = I.intersection((ideal([_random1(R), _random1(R)]) ** i))
    I = I.saturation(ideal(R.gens()))[0]
    f = rational_map(projective_variety(I),v[0])
    if nodes is not None:
        if not isinstance(nodes,(int,Integer)):
            raise TypeError("nodes must be an integer")
        if nodes > 0:
            N = f.target().empty()
            for i in range(nodes):
                p1 = f(f.source().point(verbose=False))
                p2 = f(f.source().point(verbose=False))
                N = N.union((p1.union(p2)).linear_span().point(verbose=False))
            f = f.compose(rational_map(N.linear_span()))
    ambient_changed = False
    if ambient is not None:
        if not isinstance(ambient,(int,Integer)):
            raise TypeError("ambient must be an integer")
        if ambient != f.target().dimension():
            H = [_random1(f.target().coordinate_ring()) for i in range(ambient+1)]
            h = rational_map(f.target(),None,H)
            f = f.compose(h)
            ambient_changed = True
    S = f.image()
    if S.dimension() != 2:
        raise Exception("failed to construct the surface")
    S = _Rational_projective_surface(S)
    S._linear_system = list(v)
    if nodes is not None and nodes > 0 and S.linear_span().dimension() >= 5:
        S._finite_number_of_nodes = nodes
    S._is_ambient_space_forced = (nodes is not None and nodes > 0) or ambient_changed
    S._parametrization = f  #f.make_dominant()
    return S

class _Virtual_projective_surface(Embedded_projective_variety):
    r"""The class of virtual projective surfaces."""
    def __init__(self, ambient, degree, sectional_genus, constant_coefficient_hilbert_polynomial, topological_euler_characteristic, KK=33331):
        Embedded_projective_variety.__init__(self, PP(ambient, KK=KK).empty())
        self._dimension = 2
        self._degree = degree
        self._sectional_genus = sectional_genus
        self._constant_coefficient_hilbert_polynomial = constant_coefficient_hilbert_polynomial
        self._topological_euler_characteristic = topological_euler_characteristic

    def _repr_(self):
        r"""Return a string representation of the virtual surface."""
        rational = "rational " if hasattr(self, "_linear_system") else ""
        s = "virtual " + rational + "surface in PP^" + str(self.ambient().dimension()) + " of degree " + str(self.degree()) + " and sectional genus " + str(self.sectional_genus())
        for i, a in zip(range(1,4), [" hyperplane(s)", " quadric hypersurface(s)", " cubic hypersurface(s)"]):
            if self._dim_homogeneous_component(i) > 0:
                s = s + " cut out by at least " + str(self._dim_homogeneous_component(i)) + a
                break
        return s

    def hilbert_polynomial(self):
        r"""Return the Hilbert polynomial of the virtual projective variety."""
        try:
            return self._hilbert_polynomial
        except AttributeError:
            t = PolynomialRing(QQ, 1, 't').gen()
            self._hilbert_polynomial = (1/2)*(self.degree())*t**2 + ((1/2)*(self.degree())+1-(self.sectional_genus()))*t + self._constant_coefficient_hilbert_polynomial
            return self._hilbert_polynomial

    def _dim_homogeneous_component(self, n):
        r"""Return the expected dimension for the homogeneous component of degree ``n`` of the defining ideal of the virtual surface."""
        return max(Integer(binomial(self.ambient().dimension()+n,n) - self.hilbert_polynomial()(n)), 0)

class _Virtual_rational_projective_surface(_Virtual_projective_surface, _Rational_projective_surface):
    r"""The class of virtual rational surfaces.

    TESTS::

        sage: S = surface(5,8,0,1, virtual=True); S
        virtual rational surface in PP^6 of degree 8 and sectional genus 3 cut out by at least 7 quadric hypersurface(s)
        sage: S.materialize()
        rational surface in PP^6 of degree 8 and sectional genus 3 cut out by 7 hypersurfaces of degree 2 (the image of the plane via the linear system [5, 8, 0, 1])
        sage: S = surface(4,8, ambient=5, virtual=True); S
        virtual rational surface in PP^5 of degree 8 and sectional genus 3 cut out by at least 13 cubic hypersurface(s)
        sage: S.materialize()
        rational surface in PP^5 of degree 8 and sectional genus 3 cut out by 13 hypersurfaces of degree 3

    """
    def __init__(self, *args, KK=33331, ambient=None):
        v = args
        N = binomial(v[0]+2,2) - 1 - sum([r * binomial(i+1,2) for i, r in enumerate(v[1:], start=1)])
        if N < 3:
            raise ValueError("expected ambient projective space of dimension at least 3, got " + str(N))
        if ambient is None:
            ambient = N
        if N < 5 or ambient < 5:
            print("warning: ambient projective space should be of dimension at least 5")
        degS = v[0] ** 2 - sum([r * (i ** 2) for i, r in enumerate(v[1:], start=1)])
        gS = binomial(v[0]-1,2) - sum([r * binomial(i,2) for i, r in enumerate(v[1:], start=1)]) # [Hartshorne's book, p. 389, Cor. 3.7]
        chiOS = 1
        c2TS = 3 + sum(v[1:])
        _Virtual_projective_surface.__init__(self, ambient, degS, gS, chiOS, c2TS, KK=KK)
        self._linear_system = list(v)

    def materialize(self):
        r"""Return a surface with the same invariants as the virtual surface."""
        if hasattr(self, "_materialization"):
            return self._materialization
        S = surface(*self._linear_system, KK=self.ambient().base_ring(), ambient=self.ambient().dimension(), nodes=None, virtual=False)
        if S.degree() != self.degree():
            raise Exception("failed to materialize the virtual surface, wrong degree")
        if S.sectional_genus() != self.sectional_genus():
            raise Exception("failed to materialize the virtual surface, wrong sectional genus")
        if S.hilbert_polynomial().constant_coefficient() != self.hilbert_polynomial().constant_coefficient():
            raise Exception("failed to materialize the virtual surface, wrong Hilbert polynomial")
        if S.linear_span().codimension() != self._dim_homogeneous_component(1):
            raise Exception("failed to materialize the virtual surface, wrong linear span")
        if S.linear_span().codimension() == 0:
            if S.degrees_generators().count(2) != self._dim_homogeneous_component(2):
                print("warning: got wrong number of quadrics in materialization of virtual surface")
            elif S.degrees_generators().count(2) == 0 and S.degrees_generators().count(3) != self._dim_homogeneous_component(3):
                print("warning: got wrong number of cubics in materialization of virtual surface")
        if S.topological_euler_characteristic() != self.topological_euler_characteristic():
            raise Exception("failed to materialize the virtual surface, wrong topological Euler characteristic")
        self._materialization = S
        return S

class Hodge_special_fourfold(Embedded_projective_variety):
    r"""The class of Hodge-special fourfolds

    This is a subclass of the class :class:`Embedded_projective_variety`.
    An object of this class is just a (smooth) projective variety of dimension 4,
    although it is better to think of ``X`` as a pair ``(S, X)``, where ``X`` is the fourfold
    and ``S`` is a particular special surface contained in ``X``. Usually there is also a
    fixed ambient fivefold ``V`` where ``S`` and ``X`` live.

    Constructing a Hodge-special fourfold.

    .. WARNING::

        You should not create objects of this class directly. The
        preferred method to construct such fourfolds is to use
        :meth:`fourfold`.

    INPUT:

    - ``S`` :class:`Embedded_projective_variety` -- an irreducible surface.
    - ``X`` :class:`Embedded_projective_variety` -- a smooth fourfold containing the surface ``S``.
    - ``V`` :class:`Embedded_projective_variety` -- a fivefold where ``X`` is a hypersurface (optional).

    OUTPUT:

    The Hodge-special fourfold corresponding to the pair ``(S,X)``.

    If the input fourfold ``X`` is missing, it will be chosen randomly.
    So, typically we just specify the surface ``S``. For instance,
    if ``S`` is a surface in ``PP^5``, then ``fourfold(S)`` returns a random cubic
    fourfold containing ``S``;
    if ``S`` is a surface in ``PP^7``, then ``fourfold(S)`` returns a random
    complete intersection of 3 quadrics containing ``S`` and contained
    in a complete intersection ``V`` of 2 quadrics.

    EXAMPLES::

        sage: S = surface(3,4)
        sage: X = fourfold(S); X
        Cubic fourfold of discriminant 14 = 3*13-5^2 containing a rational surface in PP^5 of degree 5 and sectional genus 1 cut out by 5 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 4])
        sage: X.surface()
        rational surface in PP^5 of degree 5 and sectional genus 1 cut out by 5 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 4])
        sage: X.ambient_fivefold()
        PP^5

    You can also convert such fourfolds into ``Macaulay2`` objects.

    ::

        sage: X_ = macaulay2(X); X_                                                  # optional - macaulay2
        hypersurface in PP^5 defined by a form of degree 3
        <BLANKLINE>
        ProjectiveVariety, cubic fourfold containing a surface of degree 5 and sectional genus 1
        sage: X_.surface()                                                           # optional - macaulay2
        surface in PP^5 cut out by 5 hypersurfaces of degree 2
        <BLANKLINE>
        ProjectiveVariety, surface in PP^5

    """
    def __init__(self, S, X, V=None, check=True):
        r"""See :class:`Hodge_special_fourfold` for documentation."""
        S = _check_type_embedded_projective_variety(S)
        X = _check_type_embedded_projective_variety(X)
        if V is not None:
            V = _check_type_embedded_projective_variety(V)
        super().__init__(X)
        if self.dimension() != 4:
            raise ValueError("expected a fourfold")
        if S.dimension() != 2:
            raise ValueError("expected a surface")
        if not S.is_subset(X):
            raise ValueError("the surface must be contained in the fourfold")
        if V is None and self.ambient().dimension() == 5:
            V = self.ambient()
        if V is not None:
            if V.dimension() != 5:
                raise ValueError("expected a fivefold")
            if not X.is_subset(V):
                raise ValueError("the fourfold must be contained in the fivefold")
            if check and V.singular_locus().dimension() >= 0:
                raise ValueError("the ambient fivefold is not smooth")
            self._ambient_fivefold = V
        if check and self.singular_locus().dimension() >= 0:
            raise ValueError("the fourfold is not smooth")
        self._surface = S

    def _repr_(self):
        r"""Return a string representation of the fourfold """
        return("Hodge-special fourfold of degree " + str(self.degree()) + " in PP^" + str(self.ambient().dimension()) + " containing a " + str(self.surface()))

    def _latex_(self):
        r"""Return the LaTeX representation of ``self``.

        OUTPUT:

        A string.

        EXAMPLES::

            sage: S = surface(3,3)
            sage: X = fourfold(S,S.random(2,2))
            sage: latex(X)
            \mbox{Hodge-special fourfold of degree } 4 \mbox{ in } \mathbb{P}^{ 6 } \mbox{ containing a } \mbox{rational } \mbox{surface in }\mathbb{P}^{ 6 } \mbox{ of degree } 6 \mbox{ and sectional genus } 1 \mbox{ cut out by } 9 \mbox{ hypersurfaces of degree } 2 \mbox{ (the image of the plane via the linear system } \left[3, 3\right] \mbox{)}

        """
        return("\\mbox{Hodge-special fourfold of degree }" + latex(self.degree()) + "\\mbox{ in }" + latex(self.ambient()) + "\\mbox{ containing a }" + latex(self.surface()))

    def surface(self):
        r"""Return the special surface contained in the fourfold.

        OUTPUT:

        :class:`Embedded_projective_variety`,  the surface of ``self``.

        EXAMPLES::

            sage: S = surface(3,4)
            sage: X = fourfold(S)
            sage: X.surface() is S
            True

        """
        return(self._surface)

    def ambient_fivefold(self):
        r"""Return the ambient fivefold of the fourfold.

        OUTPUT:

        :class:`Embedded_projective_variety`,  the ambient fivefold of ``self``.

        EXAMPLES::

            sage: S = surface(3,4)
            sage: X = fourfold(S)
            sage: X.ambient_fivefold()
            PP^5

        """
        try:
            return self._ambient_fivefold
        except AttributeError:
            raise Exception("cannot find ambient fivefold")

    def _lattice_intersection_matrix(self, verbose=None):
        r"""Return the matrix from which we compute the discriminant of ``self``."""
        try:
            return self.__lattice_intersection_Matrix
        except AttributeError:
            r = self.codimension()
            a = list(self.degrees_generators())
            if len(a) != r:
                raise NotImplementedError("expected a special fourfold which is a complete intersection")
            S = self.surface()
            HS2 = S.degree()
            KSHS = 2*(S.sectional_genus())-2-HS2
            chiOS = Integer(S.hilbert_polynomial().constant_coefficient())
            c2TS = S.topological_euler_characteristic(verbose=verbose)
            KS2 = 12*chiOS-c2TS
            n = S._finite_number_of_nodes if hasattr(S,"_finite_number_of_nodes") else 0
            S2 = 2*n + (binomial(r+5,2) - (r+5)*(sum(a)) + (sum(a)) ** 2 - sum([a[i]*a[j] for i in range(r) for j in range(i+1,r)])) * HS2 + (r+5-sum(a)) * KSHS + KS2 - c2TS
            self.__lattice_intersection_Matrix = matrix([[self.degree(),HS2],[HS2,S2]])
            return self.__lattice_intersection_Matrix

    def discriminant(self, verbose=None):
        r"""Return the discriminant of the special fourfold.

        OUTPUT:

        An integer, the discriminant of ``self``.

        In several cases, such as that of cubic fourfolds, this is
        the discriminant of the saturated lattice spanned by ``h^2`` and ``S``,
        where ``S`` is the class of the surface of ``X`` and ``h``
        denotes the class of a hyperplane section of ``X``.
        For theoretical details, we refer to Hassett's papers on cubic fourfolds.

        EXAMPLES::

            sage: S = surface(3,4)
            sage: X = fourfold(S)
            sage: X.discriminant()
            14

        """
        if verbose is None:
            verbose = __VERBOSE__
        if isinstance(self,GushelMukai_fourfold):
            try:
                return self._discriminant_of_GM_fourfold
            except AttributeError:
                if verbose:
                    print("-- running Macaulay2 function discriminant(GM fourfold)... --")
                X = macaulay2(self)
                d = X.discriminant().sage()
                assert(isinstance(d,(int,Integer)))
                a,b = X.cycleClass().last().sage()
                assert(isinstance(a,(int,Integer)) and isinstance(b,(int,Integer)))
                self._discriminant_of_GM_fourfold = d
                self._class_of_surface_in_the_Grass = (a,b)
                if verbose:
                    print("-- function discriminant(GM fourfold) has successfully terminated. --")
                return self._discriminant_of_GM_fourfold
        return(self._lattice_intersection_matrix(verbose=verbose).determinant())

    def _macaulay2_init_(self, macaulay2=None):
        r"""Get the corresponding special fourfold in Macaulay2."""
        if macaulay2 is None:
            from sage.interfaces.macaulay2 import macaulay2 as m2_default
            macaulay2 = m2_default
        try:
            return self._macaulay2_object
        except AttributeError:
            X = Embedded_projective_variety._macaulay2_init_(self)
            S = macaulay2(self.surface())
            V = macaulay2(self.ambient_fivefold())
            self._macaulay2_object = S.specialFourfold(X,V)
            self._macaulay2_object._sage_object = self
            return self._macaulay2_object

    def map_from_fivefold(self, verbose=None, algorithm='sage'):
        r"""(For internal use only) Return the map from the ambient fivefold of ``self``
        defined by the linear system of hypersurfaces containing the surface of ``self`` and
        of degree equal to the degree of ``self`` as a hypersurface in its ambient fivefold.
        """
        try:
            return self._the_map_from_the_fivefold
        except AttributeError:
            if verbose is None:
                verbose = __VERBOSE__
            if algorithm == 'macaulay2':
                if verbose:
                    print("--computing map_from_fivefold using Macaulay2...")
                X = macaulay2(self)
                f = X.map()
                if verbose:
                    print("--computing image of map_from_fivefold using Macaulay2...")
                # X.recognize()
                X.imageOfAssociatedMap()
                if verbose:
                    print("--computation of image of map_from_fivefold terminated.")
                self._the_map_from_the_fivefold = _from_macaulay2map_to_sagemap(f.removeUnderscores().multirationalMap(), Sage_Source=self.ambient_fivefold())
                assert(hasattr(self._the_map_from_the_fivefold,"_closure_of_image"))
                return self._the_map_from_the_fivefold
            if algorithm == 'sage':
                # This needs to be improved!
                I = ideal(self.surface()._homogeneous_component(self._degree_as_hypersurface))
                if self.ambient_fivefold().codimension() > 1:
                    I = I.change_ring(self.ambient_fivefold().coordinate_ring())
                phi = rational_map(self.ambient_fivefold(), I.gens())
                if verbose:
                    print("--computing image of map_from_fivefold (using sage)...")
                phi.image()
                if verbose:
                    print("--computation of image of map_from_fivefold terminated.")
                self._the_map_from_the_fivefold = phi
                return self._the_map_from_the_fivefold
            raise ValueError("keyword algorithm must be 'macaulay2' or 'sage'")

    def congruence(self, degree=None, num_checks=3, point=None, verbose=None, algorithm_for_image='sage', algorithm_for_point='sage', macaulay2_detectCongruence = False):
        r"""Detect and return a congruence of secant curves for the surface of ``self`` in the ambient fivefold of ``self``.

        This function works similar to the ``Macaulay2`` function ``detectCongruence``, documented at
        https://faculty.math.illinois.edu/Macaulay2/doc/Macaulay2/share/doc/Macaulay2/SpecialFanoFourfolds/html/_detect__Congruence.html.
        See also the paper at https://www.tandfonline.com/doi/abs/10.1080/10586458.2023.2184882
        for more computational details.

        INPUT:

        ``degree`` -- an optional integer, the degree of the curves of the congruence.

        ``num_checks`` -- an optional integer with default value 3, check that the congruence works by testing so many random points on the ambient fivefold.

        ``point`` -- optional, a point on the ambient fivefold. This is only useful when you want to perform calculations on infinite fields, where the function :meth:`point` might not work.

        ``verbose`` -- a boolean value, turn on or off verbose output.

        ``algorithm_for_image`` -- possible values are ``sage`` (by default) and ``macaulay2``, with ``algorithm_for_image='macaulay2'`` the computation of the image of the map :meth:`map_from_fivefold` is performed using ``Macaulay2`` (this is recommended if you have ``Macaulay2`` installed).

        ``algorithm_for_point`` -- possible values are ``sage`` (by default) and ``macaulay2``, with ``algorithm_for_point='macaulay2'`` the computation of random points is performed using ``Macaulay2``.

        ``macaulay2_detectCongruence`` -- a boolean value, default value false, with ``macaulay2_detectCongruence=True`` the whole computation is performed using the ``Macaulay2`` function ``detectCongruence``.

        OUTPUT:

        A congruence of curves, which behaves like a function that sends a point ``p`` on the ambient fivefold
        to the curve of the congruence passing through ``p``.

        EXAMPLES::

            sage: X = fourfold(surface(3,1,1,KK=GF(65521))); X
            Cubic fourfold of discriminant 14 = 3*10-4^2 containing a rational surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 1, 1])
            sage: f = X.congruence(algorithm_for_image='macaulay2'); f                                            # optional - macaulay2
            Congruence of 2-secant lines
            to: rational surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 1, 1])
            in: PP^5
            sage: p = X.ambient_fivefold().point()
            sage: f(p)                                                                                            # optional - macaulay2
            line in PP^5

            sage: X = fourfold("GM 4-fold of discriminant 26('')",GF(65521)); X                                   # optional - macaulay2
            Gushel-Mukai fourfold of discriminant 26('') containing a surface in PP^8 of degree 9 and sectional genus 2 cut out by 19 hypersurfaces of degree 2, class of the surface in GG(1,4): (5, 4)
            sage: f = X.congruence(macaulay2_detectCongruence=True, num_checks=1, verbose=True); f                # optional - macaulay2
            -- running Macaulay2 function detectCongruence()... --
            number lines contained in the image of the quadratic map and passing through a general point: 6
            number 1-secant lines = 5
            number 3-secant conics = 1
            -- function detectCongruence() has terminated. --
            -- checking congruence (1 of 1)...
            Congruence of 3-secant conics
            to: surface in PP^8 of degree 9 and sectional genus 2 cut out by 19 hypersurfaces of degree 2
            in: 5-dimensional variety of degree 5 in PP^8 cut out by 5 hypersurfaces of degree 2
            sage: p = X.ambient_fivefold().point()                                                                # optional - macaulay2
            sage: f(p)                                                                                            # optional - macaulay2
            conic curve in PP^8

            sage: X = fourfold("3-nodal septic scroll", GF(61001)); X                                             # optional - macaulay2
            Cubic fourfold of discriminant 26 = 3*25-7^2 containing a surface in PP^5 of degree 7 and sectional genus 0 cut out by 13 hypersurfaces of degree 3
            sage: X.congruence(algorithm_for_image='macaulay2', num_checks=2)                                     # optional - macaulay2
            Congruence of 5-secant conics
            to: surface in PP^5 of degree 7 and sectional genus 0 cut out by 13 hypersurfaces of degree 3
            in: PP^5

        """
        if macaulay2_detectCongruence:
            return self._detect_congruence_using_macaulay2(Degree=degree, verbose=verbose).check(num_checks,algorithm_for_point=algorithm_for_point,verbose=verbose)

        if verbose is None:
            verbose = __VERBOSE__
        f = self.map_from_fivefold(verbose=verbose, algorithm=algorithm_for_image)

        def dim_and_degree(X):
            return(X.dimension(), X.degree())

        def function_congruence(p, degree=None, verbose=false):
            if degree is None and hasattr(self,"_possible_degrees_for_curves_of_congruence") and len(self._possible_degrees_for_curves_of_congruence) == 0:
                raise Exception("function 'congruence' failed (with previous runs)")
            p = _check_type_embedded_projective_variety(p)
            if not (p._is_point() and p.is_subset(self.ambient_fivefold())):
                raise Exception("expected a point on the ambient fivefold")
            q = f(p)
            if verbose:
                print("--computing cone of lines (using sage)...")
            V = f.image().cone_of_lines(point=q)
            if verbose:
                print("--computing partial decomposition of cone of lines...")
            D = V._fast_decomposition(degree=1)
            if len(D) == 0:
                self._possible_degrees_for_curves_of_congruence = set()
                raise Exception("function 'congruence' failed")
            if verbose:
                print("--computing inverse images of lines...")
            curves = [f.inverse_image(q.linear_span()) for q in D]
            if verbose:
                print("--analyzing " + str(len(curves)) + " curve(s) in the ambient fivefold...")
            degs = [C.degree() for C in curves] if degree is None else [degree]
            if degree is None and hasattr(self,"_possible_degrees_for_curves_of_congruence"):
                degs = list(set(degs).intersection(self._possible_degrees_for_curves_of_congruence))
                if len(degs) == 0:
                    raise Exception("function 'congruence' failed (with previous runs)")
            W = []
            for d in degs:
                E = [C for C in curves if dim_and_degree(C) == (1,d) and dim_and_degree(C.intersection(self.surface())) == (0, d * self._degree_as_hypersurface - 1)]
                if len(E) == 1:
                    W.extend(E)
            if degree is None and len(W) > 1:
                if not hasattr(self,"_possible_degrees_for_curves_of_congruence"):
                    self._possible_degrees_for_curves_of_congruence = set([w.degree() for w in W])
                else:
                    self._possible_degrees_for_curves_of_congruence = self._possible_degrees_for_curves_of_congruence.intersection(set([w.degree() for w in W]))
                    if len(self._possible_degrees_for_curves_of_congruence) == 0:
                        raise Exception("function 'congruence' failed (with previous runs)")
                if verbose:
                    print("found possible degrees for curves of congruences: " + str(self._possible_degrees_for_curves_of_congruence) + ", rerunning the computation using another point...")
                return function_congruence(self.ambient_fivefold().point(verbose=verbose, algorithm=algorithm_for_point), degree=None, verbose=verbose)
            if len(W) == 0:
                raise Exception("function 'congruence' failed")
                self._possible_degrees_for_curves_of_congruence = set()
            assert(p.is_subset(W[0]))
            self._possible_degrees_for_curves_of_congruence = set([w.degree() for w in W])
            return W[0]

        p = self.ambient_fivefold().point(verbose=verbose, algorithm=algorithm_for_point) if point is None else point
        try:
            Curve = function_congruence(p, degree=degree, verbose=verbose)
        except Exception as err:
            raise Exception(err)
        d = Curve.degree()

        def function_congruence_with_degree(p):
            return function_congruence(p, degree=d, verbose=false)

        congr = _Congruence_of_secant_curves_to_surface(function_congruence_with_degree, None, d, self)

        try:
            congr.check(num_checks, verbose=verbose, algorithm_for_point=algorithm_for_point)
        except Exception:
            raise Exception("congruence check failed")
        return congr

    def fano_map(self, verbose=None):
        r"""Return the Fano map from the ambient fivefold.

        The surface contained in the fourfold ``self`` must admit
        a congruence of secant curves inside the ambient fivefold.
        The generic curve of this congruence can be realized
        as the generic fiber of the returned map. See also :meth:`detect_congruence`.

        EXAMPLES::

            sage: X = fourfold(surface(3,4))
            sage: X.fano_map(verbose=false)                     # optional - macaulay2
            dominant rational map defined by forms of degree 2
            source: PP^5
            target: PP^4
        """
        if verbose is None:
            verbose = __VERBOSE__
        X = macaulay2(self)
        if verbose:
            print("-- running Macaulay2 function fanoMap()... --")
        try:
            f = X.fanoMap().multirationalMap()
        except Exception as err:
            raise Exception(err)
        F = _from_macaulay2map_to_sagemap(f,Sage_Source = self.ambient_fivefold())
        if verbose:
            print("-- function fanoMap() has successfully terminated. --")
        return F

    def random_coordinate_change(self):
        r"""Apply a random coordinate change on the ambient projective space of ``self``.

        EXAMPLES::

            sage: from sage.misc.randstate import set_random_seed
            sage: set_random_seed(1234567)
            sage: X = fourfold(Veronese(2,2,KK=101)); X
            Cubic fourfold of discriminant 20 = 3*12-4^2 containing a surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2
            sage: X.surface().defining_polynomials()
            (x4^2 - x3*x5,
            x2*x4 - x1*x5,
            x2*x3 - x1*x4,
            x2^2 - x0*x5,
            x1*x2 - x0*x4,
            x1^2 - x0*x3)
            sage: Y = X.random_coordinate_change(); Y
            Cubic fourfold of discriminant 20 = 3*12-4^2 containing a surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2
            sage: Y.surface().defining_polynomials()
            (x2^2 - 28*x0*x3 + 31*x1*x3 + 15*x2*x3 + 32*x3^2 + 9*x0*x4 - 34*x1*x4 + 33*x2*x4 + 37*x3*x4 - x4^2 - 18*x0*x5 - 37*x1*x5 + 32*x2*x5 - 22*x3*x5 + x4*x5 + 20*x5^2,
            x1*x2 - 46*x0*x3 + 15*x1*x3 + 28*x2*x3 - 13*x3^2 - 32*x0*x4 - 44*x1*x4 + 27*x2*x4 + 19*x3*x4 - 29*x4^2 + 28*x0*x5 + 48*x1*x5 - 10*x2*x5 - 48*x3*x5 - 33*x4*x5 + 6*x5^2,
            x0*x2 + 6*x0*x3 - 9*x1*x3 - 47*x2*x3 + 34*x3^2 + 40*x0*x4 + 15*x1*x4 + 39*x2*x4 + 17*x3*x4 + 23*x4^2 - x0*x5 + 43*x1*x5 - 38*x2*x5 + 8*x3*x5 - 46*x4*x5 + 49*x5^2,
            x1^2 - 11*x0*x3 + 44*x1*x3 + 30*x2*x3 + 26*x3^2 + 45*x0*x4 + 41*x1*x4 + 9*x2*x4 + 19*x3*x4 + 13*x4^2 - 15*x0*x5 - 8*x1*x5 + 31*x2*x5 - 43*x3*x5 - 23*x5^2,
            x0*x1 - 14*x0*x3 + 9*x1*x3 - 27*x2*x3 + 31*x3^2 + 48*x0*x4 + 28*x1*x4 - 9*x2*x4 - 41*x3*x4 - 12*x4^2 + 48*x0*x5 - 25*x1*x5 + 28*x2*x5 - 35*x3*x5 - 28*x4*x5 - 40*x5^2,
            x0^2 - 26*x0*x3 - x1*x3 - 6*x2*x3 + x3^2 - 4*x0*x4 + 9*x1*x4 - 9*x2*x4 + 17*x3*x4 - 24*x4^2 + 46*x0*x5 + 16*x1*x5 - 5*x2*x5 + 13*x3*x5 + 8*x4*x5 + 26*x5^2)

        """
        V = self.ambient_fivefold().random_coordinate_change()
        S = V._from_random_coordinate_change(self.surface())
        X = V._from_random_coordinate_change(self)
        return fourfold(S,X,V,check=False)

    def parameter_count(self, verbose=None):
        r"""Count of parameters.

        This just runs the ``Macaulay2`` function ``parameterCount``, documented at
        https://faculty.math.illinois.edu/Macaulay2/doc/Macaulay2/share/doc/Macaulay2/SpecialFanoFourfolds/html/_parameter__Count.html.
        See also the paper at https://www.tandfonline.com/doi/abs/10.1080/10586458.2023.2184882
        for more computational details.

        OUTPUT:

        An integer and a tuple of three integers.

        EXAMPLES::

            sage: X = fourfold(surface(3,1,1)); X
            Cubic fourfold of discriminant 14 = 3*10-4^2 containing a rational surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 1, 1])
            sage: X.parameter_count(verbose=True)                                          # optional - macaulay2
            -- running Macaulay2 function parameterCount()... --
            S: smooth rational normal scroll surface of degree 4 in PP^5
            X: smooth cubic hypersurface in PP^5
            (assumption: dim Ext^1(I_{S,P^5},O_S) = 0)
            h^0(N_{S,P^5}) = 29
            h^1(O_S(3)) = 0, and h^0(I_{S,P^5}(3)) = 28 = h^0(O_(P^5)(3)) - \chi(O_S(3));
            in particular, h^0(I_{S,P^5}(3)) is minimal
            h^0(N_{S,P^5}) + 27 = 56
            h^0(N_{S,X}) = 2
            dim{[X] : S ⊂ X} >= 54
            dim P(H^0(O_(P^5)(3))) = 55
            codim{[X] : S ⊂ X} <= 1
            -- function parameterCount() has terminated. --
            (1, (28, 29, 2))

            sage: X = fourfold('1',GF(33331)); X                                           # optional - macaulay2
            Gushel-Mukai fourfold of discriminant 10(') containing a quadric surface in PP^8, class of the surface in GG(1,4): (1, 1)
            sage: X.parameter_count(verbose=True)                                          # optional - macaulay2
            -- running Macaulay2 function parameterCount()... --
            S: smooth quadric surface in PP^8
            X: GM fourfold containing S
            Y: del Pezzo fivefold containing X
            h^1(N_{S,Y}) = 0
            h^0(N_{S,Y}) = 8
            h^1(O_S(2)) = 0, and h^0(I_{S,Y}(2)) = 31 = h^0(O_Y(2)) - \chi(O_S(2));
            in particular, h^0(I_{S,Y}(2)) is minimal
            h^0(N_{S,Y}) + 30 = 38
            h^0(N_{S,X}) = 0
            dim{[X] : S ⊂ X ⊂ Y} >= 38
            dim P(H^0(O_Y(2))) = 39
            codim{[X] : S ⊂ X ⊂ Y} <= 1
            -- function parameterCount() has terminated. --
            (1, (31, 8, 0))

        """
        if verbose is None:
            verbose = __VERBOSE__
        try:
            return self._macaulay2_parameter_count
        except AttributeError:
            if verbose:
                print("-- running Macaulay2 function parameterCount()... --")
            X = macaulay2(self,'X')
            if verbose:
                _print_partial_M2_output("parameterCount(X,Verbose=>true);")
            self._macaulay2_parameter_count = X.parameterCount().sage()
            if verbose:
                print("-- function parameterCount() has terminated. --")
            return self._macaulay2_parameter_count

    def _associated_surface_construction(self, verbose=None):
        r"""Construction via Macaulay2 of associated K3 surfaces to rational cubic fourfolds and rational GM fourfolds,
        and associated Castelnuovo surfaces to rational complete intersections of three quadrics in PP^7 (for internal use only).
        For better documentation see :class:`Cubic_fourfold`.
        """
        if verbose is None:
            verbose = __VERBOSE__
        s = "associatedK3surface" if not isinstance(self,_Intersection_of_three_quadrics_in_P7) else "associatedCastelnuovoSurface"
        try:
            return self._macaulay2_associated_surface_construction
        except AttributeError:
            if verbose:
                print("-- running Macaulay2 function " + s + "()... --")
            X = macaulay2(self,'X')
            if verbose:
                _print_partial_M2_output(s + "(X,Verbose=>true);")
            U = X.associatedK3surface() if not isinstance(self,_Intersection_of_three_quadrics_in_P7) else X.associatedCastelnuovoSurface()
            mu = _from_macaulay2map_to_sagemap(U.building()[0].removeUnderscores(),Sage_Source=self.ambient_fivefold())
            U_non_minimal = _from_macaulay2_to_sage(U.building()[1].removeUnderscores(),Sage_Ambient_Space=mu.target().ambient_space())
            L = _from_macaulay2_to_sage(U.building()[2][0].removeUnderscores(),Sage_Ambient_Space=mu.target().ambient_space())
            C = _from_macaulay2_to_sage(U.building()[2][1].removeUnderscores(),Sage_Ambient_Space=mu.target().ambient_space())
            f = _from_macaulay2map_to_sagemap(U.building()[3].removeUnderscores(),Sage_Source=U_non_minimal)
            assert(mu.source() is self.ambient_fivefold() and U_non_minimal.is_subset(mu.target()) and L.is_subset(U_non_minimal) and C.is_subset(U_non_minimal) and f.source() is U_non_minimal and f.image().dimension() == 2)
            self._macaulay2_associated_surface_construction = (mu, U_non_minimal, (L,C), f)
            if verbose:
                print("-- function " + s + "() has terminated. --")
            return self._macaulay2_associated_surface_construction

    def _detect_congruence_using_macaulay2(self, Degree=None, verbose=None):
        r"""Detect and return a congruence of secant curves using ``Macaulay2``."""
        try:
            return self._macaulay2_detect_congruence
        except AttributeError:
            if verbose is None:
                verbose = __VERBOSE__
            if verbose:
                print("-- running Macaulay2 function detectCongruence()... --")
            X = macaulay2(self,'X')
            X.recognize() # this can speed up the computation
            if verbose:
                m2_str = "CONGRUENCE = detectCongruence(X,Verbose=>true);" if Degree is None else "CONGRUENCE = detectCongruence(X," + str(Degree) + ",Verbose=>true);"
                _print_partial_M2_output(m2_str)
                f = macaulay2('CONGRUENCE')
            else:
                f = X.detectCongruence() if Degree is None else X.detectCongruence(Degree)
            deg_congr = f.sharp('"degree"').sage()

            def f_s(p):
                p = _check_type_embedded_projective_variety(p)
                if not (p._is_point() and p.is_subset(self.ambient_fivefold())):
                    raise Exception("expected a point on the ambient fivefold")
                C = f(p)
                D = _from_macaulay2_to_sage(C,self.ambient_space())
                assert(p.is_subset(D) and D.is_subset(self.ambient_fivefold()) and D.dimension() == 1 and D.degree() == deg_congr)
                return D

            g = _Congruence_of_secant_curves_to_surface(f_s, f, deg_congr, self)
            if Degree is None:
                self._macaulay2_detect_congruence = g
            if verbose:
                print("-- function detectCongruence() has terminated. --")
            return g

class _Congruence_of_secant_curves_to_surface(SageObject):
    r"""The class of objects created by the function :meth:`congruence`."""
    def __init__(self, f_s, f, deg_congr, X):
        self._function_on_points = f_s
        self._macaulay2_object = f
        self._degree = deg_congr
        self._fourfold = X
    def _repr_(self):
        curves_word = {
            1:"lines",
            2:"conics",
            3:"cubic curves",
            4:"quartic curves",
            5:"quintic curves",
            6:"sextic curves",
            7:"septic curves",
            8:"octic curves",
            9:"nonic curves"
        }
        d = self._degree
        a = self._fourfold._degree_as_hypersurface
        return "Congruence of " + str(a*d - 1) + "-secant " + (curves_word[d] if d <= 9 else "curves of degree " + str(d)) + "\nto: " + self._fourfold.surface()._repr_() + "\nin: " + self._fourfold.ambient_fivefold()._repr_()
    def __call__(self, p):
        return self._function_on_points(p)
    def _macaulay2_init_(self, macaulay2=None):
        if macaulay2 is None:
            from sage.interfaces.macaulay2 import macaulay2 as m2_default
            macaulay2 = m2_default
        return self._macaulay2_object
    def check(self, i=1, verbose=None, algorithm_for_point=None):
        if verbose is None:
            verbose = __VERBOSE__
        if algorithm_for_point is None:
            algorithm_for_point = 'sage' if self._macaulay2_object is None else 'macaulay2'
        V = self._fourfold.ambient_fivefold()
        for j in range(i):
            if verbose:
                print("-- checking congruence ("+str(j+1)+" of "+str(i)+")...")
            self(V.point(verbose=False, algorithm=algorithm_for_point))
        return self

class _Intersection_of_three_quadrics_in_P7(Hodge_special_fourfold):
    r"""The class of Hodge-special complete intersections of three quadrics in ``PP^7``."""
    def __init__(self, S, X, V=None, check=True):
        super().__init__(S,X,V,check=check)
        if not(self.degrees_generators() == (2,2,2) and self.ambient_fivefold().degrees_generators() == (2,2)):
            raise Exception("something went wrong in constructing complete intersections of three quadrics in PP^7")
        self._degree_as_hypersurface = 2

    def _repr_(self):
        return("Complete intersection of 3 quadrics in PP^7 of discriminant " + str(self.discriminant(verbose=False)) + " = 8*" + str(self._lattice_intersection_matrix()[1,1]) + "-" + str(self._lattice_intersection_matrix()[0,1]) + "^2" + " containing a " + str(self.surface()))

    def _latex_(self):
        r"""Return the LaTeX representation of the fourfold.

        OUTPUT:

        A string.

        EXAMPLES::

            sage: X = fourfold(surface(1,ambient=7))
            sage: latex(X)
            \mbox{Complete intersection of } 3 \mbox{ quadrics in } \mathbb{P}^{ 7 } \mbox{ of discriminant } 31 = \det \left(\begin{array}{rr}
            8 & 1 \\
            1 & 4
            \end{array}\right) \mbox{ containing a } \mbox{plane in }\mathbb{P}^{ 7 }

        """
        return("\\mbox{Complete intersection of }" + latex(3) + "\\mbox{ quadrics in }" + latex(self.ambient()) + "\\mbox{ of discriminant }" + latex(self.discriminant(verbose=False)) + " = \\det " + latex(self._lattice_intersection_matrix()) + "\\mbox{ containing a }" + latex(self.surface()))

    def ambient_fivefold(self):
        try:
            return self._ambient_fivefold
        except AttributeError:
            print("setting ambient fivefold...")
            self._ambient_fivefold = self.random(2,2)
            return self._ambient_fivefold

    def Castelnuovo(self, verbose=None):
        r"""Associated Castelnuovo surfaces.

        This function works similar to :meth:`K3`.

        EXAMPLES::

            sage: X = fourfold(surface(1,ambient=7)); X
            Complete intersection of 3 quadrics in PP^7 of discriminant 31 = 8*4-1^2 containing a plane in PP^7
            sage: T = X.Castelnuovo(verbose=False); T                                                             # optional - macaulay2
            surface in PP^4 of degree 9 and sectional genus 9 cut out by 4 hypersurfaces of degrees (3, 4, 4, 4)
            sage: building = T.building() # a tuple of 4 objects obtained in the construction of T                # optional - macaulay2
            sage: building[0] # the first of which is the Fano map                                                # optional - macaulay2
            dominant rational map defined by forms of degree 1
            source: complete intersection of type (2, 2) in PP^7
            target: PP^4

        """
        self._associated_surface_construction(verbose=verbose)
        T = self._macaulay2_associated_surface_construction[3].image()
        T.building = lambda : self._macaulay2_associated_surface_construction
        return T

class _Virtual_intersection_of_three_quadrics_in_P7(_Intersection_of_three_quadrics_in_P7):
    r"""The class of virtual Hodge-special complete intersections of three quadrics in ``PP^7``.

    TESTS::

        sage: S = surface(5,7,0,1, virtual=True); S
        virtual rational surface in PP^7 of degree 9 and sectional genus 3 cut out by at least 12 quadric hypersurface(s)
        sage: X = fourfold(S); X
        Complete intersection of 3 quadrics in PP^7 of discriminant 47 = 8*16-9^2 containing a virtual rational surface in PP^7 of degree 9 and sectional genus 3 cut out by at least 12 quadric hypersurface(s)

    """
    def __init__(self, S, check=True):
        if not isinstance(S,_Virtual_projective_surface):
            raise TypeError("expected a virtual surface")
        if S.ambient().dimension() != 7:
            raise ValueError("expected a surface in PP^7")
        if check and S._dim_homogeneous_component(2) < 3:
            raise ValueError("the surface must be contained in a complete intersection of three quadrics")
        Embedded_projective_variety.__init__(self,S)
        self._dimension = 4
        self._degree = 8
        self._degrees_generators = (2,2,2)
        self._surface = S

    def ambient_fivefold(self):
        raise NotImplementedError

    def Castelnuovo(self, verbose=None):
        raise NotImplementedError

class Cubic_fourfold(Hodge_special_fourfold):
    r"""The class of Hodge-special cubic fourfolds in ``PP^5``."""
    def __init__(self, S, X, V=None, check=True):
        super().__init__(S,X,V,check=check)
        if not(self.degree() == 3 and self.codimension() == 1 and len(self.degrees_generators()) == 1):
            raise Exception("something went wrong in constructing cubic fourfold in PP^5")
        self._degree_as_hypersurface = 3

    def _repr_(self):
        return("Cubic fourfold of discriminant " + str(self.discriminant(verbose=False)) + " = 3*" + str(self._lattice_intersection_matrix()[1,1]) + "-" + str(self._lattice_intersection_matrix()[0,1]) + "^2" + " containing a " + str(self.surface()))

    def _latex_(self):
        r"""Return the LaTeX representation of the cubic fourfold.

        OUTPUT:

        A string.

        EXAMPLES::

            sage: X = fourfold(surface(3,4))
            sage: latex(X)
            \mbox{Cubic fourfold of discriminant } 14 = \det \left(\begin{array}{rr}
            3 & 5 \\
            5 & 13
            \end{array}\right) \mbox{ containing a } \mbox{rational } \mbox{surface in }\mathbb{P}^{ 5 } \mbox{ of degree } 5 \mbox{ and sectional genus } 1 \mbox{ cut out by } 5 \mbox{ hypersurfaces of degree } 2 \mbox{ (the image of the plane via the linear system } \left[3, 4\right] \mbox{)}

        """
        return("\\mbox{Cubic fourfold of discriminant }" + latex(self.discriminant(verbose=False)) + " = \\det " + latex(self._lattice_intersection_matrix()) + "\\mbox{ containing a }" + latex(self.surface()))

    def K3(self, verbose=None):
        r"""Associated K3 surfaces to rational cubic fourfolds.

        This just runs the ``Macaulay2`` function ``associatedK3surface``, documented at
        https://faculty.math.illinois.edu/Macaulay2/doc/Macaulay2/share/doc/Macaulay2/SpecialFanoFourfolds/html/_associated__K3surface_lp__Special__Cubic__Fourfold_rp.html.
        See also the paper at https://www.tandfonline.com/doi/abs/10.1080/10586458.2023.2184882
        for more computational details.

        OUTPUT:

        :class:`Embedded_projective_variety`, a (minimal) K3 surface associated to ``self``.

        EXAMPLES::

            sage: X = fourfold(surface(3,1,1)); X
            Cubic fourfold of discriminant 14 = 3*10-4^2 containing a rational surface in PP^5 of degree 4 and sectional genus 0 cut out by 6 hypersurfaces of degree 2 (the image of the plane via the linear system [3, 1, 1])
            sage: T = X.K3(verbose=False); T                                                            # optional - macaulay2
            surface in PP^8 of degree 14 and sectional genus 8 cut out by 15 hypersurfaces of degree 2
            sage: building = T.building() # a tuple of 4 objects obtained in the construction of T      # optional - macaulay2
            sage: building[0] # the first of which is the Fano map                                      # optional - macaulay2
            dominant rational map defined by forms of degree 2
            source: PP^5
            target: quadric hypersurface in PP^5

        """
        self._associated_surface_construction(verbose=verbose)
        T = self._macaulay2_associated_surface_construction[3].image()
        T.building = lambda : self._macaulay2_associated_surface_construction
        return T

class _Virtual_cubic_fourfold(Cubic_fourfold):
    r"""The class of virtual Hodge-special cubic fourfolds in ``PP^5``.

    TESTS::

        sage: S = surface(10,0,0,10, virtual=True); S
        virtual rational surface in PP^5 of degree 10 and sectional genus 6 cut out by at least 10 cubic hypersurface(s)
        sage: X = fourfold(S); X
        Cubic fourfold of discriminant 38 = 3*46-10^2 containing a virtual rational surface in PP^5 of degree 10 and sectional genus 6 cut out by at least 10 cubic hypersurface(s)

    """
    def __init__(self, S, check=True):
        if not isinstance(S,_Virtual_projective_surface):
            raise TypeError("expected a virtual surface")
        if S.ambient().dimension() != 5:
            raise ValueError("expected a surface in PP^5")
        if check and S._dim_homogeneous_component(3) == 0:
            raise ValueError("the surface must be contained in cubic hypersurface")
        Embedded_projective_variety.__init__(self,S)
        self._dimension = 4
        self._degree = 3
        self._degrees_generators = (3,)
        self._surface = S

    def K3(self, verbose=None):
        raise NotImplementedError

class GushelMukai_fourfold(Hodge_special_fourfold):
    r"""The class of Hodge-special Gushel-Mukai fourfolds in ``PP^8``

    TESTS::

        sage: X = fourfold("17", GF(33331)); X                  # optional - macaulay2
        Gushel-Mukai fourfold of discriminant 20 containing a surface in PP^8 of degree 9 and sectional genus 2 cut out by 19 hypersurfaces of degree 2, class of the surface in GG(1,4): (6, 3)
        sage: assert(X.base_ring().characteristic() == 33331)   # optional - macaulay2

    """
    def __init__(self, S, X, V=None, check=True):
        super().__init__(S,X,V,check=check)
        if not(self.ambient().dimension() == 8 and self.degrees_generators() == (2,2,2,2,2,2) and self.degree() == 10 and self.sectional_genus() == 6):
            raise Exception("something went wrong in constructing Gushel-Mukai fourfold in PP^8")
        self._degree_as_hypersurface = 2

    def _repr_(self):
        d = self.discriminant(verbose=False)
        (a,b) = self._class_of_surface_in_the_Grass
        e = ""
        if d % 8 == 2:
            if (a+b) % 2 == 0 and b % 2 == 1:
                e = "(')"
            elif (a+b) % 2 == 1 and b % 2 == 0:
                e = "('')"
            else:
                raise Exception("Internal error encountered.")
        return("Gushel-Mukai fourfold of discriminant " + str(d) + e + " containing a " + str(self.surface()) + ", class of the surface in GG(1,4): " + str((a,b)))

    def _latex_(self):
        r"""Return the LaTeX representation of the Gushel-Mukai fourfold."""
        return("\\mbox{Gushel-Mukai fourfold of discriminant }" + latex(self.discriminant(verbose=False)) + "\\mbox{ containing a }" + latex(self.surface()))

    def K3(self, verbose=None):
        r"""Associated K3 surfaces to rational Gushel-Mukai fourfolds.

        This just runs the ``Macaulay2`` function ``associatedK3surface``, documented at
        https://faculty.math.illinois.edu/Macaulay2/doc/Macaulay2/share/doc/Macaulay2/SpecialFanoFourfolds/html/_associated__K3surface_lp__Special__Gushel__Mukai__Fourfold_rp.html.
        See also the paper at https://www.tandfonline.com/doi/abs/10.1080/10586458.2023.2184882
        for more computational details.

        OUTPUT:

        :class:`Embedded_projective_variety`, a (minimal) K3 surface associated to ``self``.

        EXAMPLES::

            sage: X = fourfold('6'); X                                                                # optional - macaulay2
            Gushel-Mukai fourfold of discriminant 10('') containing a plane in PP^8, class of the surface in GG(1,4): (1, 0)
            sage: T = X.K3(verbose=False); T                                                          # optional - macaulay2
            surface in PP^6 of degree 10 and sectional genus 6 cut out by 6 hypersurfaces of degree 2
            sage: building = T.building() # a tuple of 4 objects obtained in the construction of T    # optional - macaulay2
            sage: building[0] # the first of which is the Fano map                                    # optional - macaulay2
            dominant rational map defined by forms of degree 1
            source: 5-dimensional variety of degree 5 in PP^8 cut out by 5 hypersurfaces of degree 2
            target: quadric hypersurface in PP^5

        """
        self._associated_surface_construction(verbose=verbose)
        T = self._macaulay2_associated_surface_construction[3].image()
        T.building = lambda : self._macaulay2_associated_surface_construction
        return T

def fourfold(S, X=None, V=None, check=True):
    r"""Construct Hodge-special fourfolds.

    The typical input for this function is a triple consisting of a surface ``S``, a fourfold ``X`` containing ``S``,
    and a fivefold ``V`` containing ``X``. The output is an object of the class :class:`Hodge_special_fourfold`.

    EXAMPLES::

        sage: S = surface(4,5,1,KK=GF(65521)); S
        rational surface in PP^6 of degree 7 and sectional genus 2 cut out by 8 hypersurfaces of degree 2 (the image of the plane via the linear system [4, 5, 1])
        sage: X = S.random(2,3); X
        complete intersection of type (2, 3) in PP^6
        sage: V = X.random(2); V
        quadric hypersurface in PP^6
        sage: F = fourfold(S,X,V); F
        Hodge-special fourfold of degree 6 in PP^6 containing a rational surface in PP^6 of degree 7 and sectional genus 2 cut out by 8 hypersurfaces of degree 2 (the image of the plane via the linear system [4, 5, 1])
        sage: F == X and F.surface() is S and F.ambient_fivefold() is V
        True
        sage: F.discriminant()
        65

    We can use this function to retrieve fourfolds constructed with ``Macaulay2``.

    EXAMPLES::

        sage: G = macaulay2('specialGushelMukaiFourfold schubertCycle({3,1},GG(1,4))')                                    # optional - macaulay2
        sage: G.describe()                                                                                                # optional - macaulay2
        Special Gushel-Mukai fourfold of discriminant 10('')
        containing a surface in PP^8 of degree 1 and sectional genus 0
        cut out by 6 hypersurfaces of degree 1
        and with class in G(1,4) given by s_(3,1)
        Type: ordinary
        (case 6 of Table 1 in arXiv:2002.07026)
        sage: fourfold(G)                                                                                                 # optional - macaulay2
        Gushel-Mukai fourfold of discriminant 10('') containing a plane in PP^8, class of the surface in GG(1,4): (1, 0)
        sage: macaulay2(_) is G                                                                                           # optional - macaulay2
        True

    Some constructions can be done by passing a description and an optional base field.

    EXAMPLES::

        sage: fourfold('general cubic 4-fold of discriminant 38',GF(65521))                                               # optional - macaulay2
        Cubic fourfold of discriminant 38 = 3*46-10^2 containing a surface in PP^5 of degree 10 and sectional genus 6 cut out by 10 hypersurfaces of degree 3

    Some calculations can be performed very fast using virtual fourfolds (although this may provide meaningless answers).

    EXAMPLES::

        sage: S = surface(4,8,ambient=5,virtual=True); S
        virtual rational surface in PP^5 of degree 8 and sectional genus 3 cut out by at least 13 cubic hypersurface(s)
        sage: X = fourfold(S); X
        Cubic fourfold of discriminant 14 = 3*26-8^2 containing a virtual rational surface in PP^5 of degree 8 and sectional genus 3 cut out by at least 13 cubic hypersurface(s)

    """
    if isinstance(S,str):
        if not(V is None and check is True and (X is None or isinstance(X,(int,Integer)) or X in Fields())):
            raise TypeError
        return _special_fourfold_from_m2(S, i=X)
    if isinstance(S,sage.interfaces.abc.Macaulay2Element) and S.instance(macaulay2('HodgeSpecialFourfold')).sage():
        if not(X is None and V is None and check is True):
            raise TypeError
        Z = S.removeUnderscores()
        A = ProjectiveSpace(Z.ambient().ring().sage())
        F = _from_macaulay2_to_sage(Z,A)
        F._macaulay2_object = S
        return F
    if isinstance(S,_Virtual_projective_surface):
        if X is not None or V is not None:
            raise Exception("fourfold and ambient fivefold don't have to be passed along with a virtual surface")
        if S.ambient().dimension() == 5:
            return _Virtual_cubic_fourfold(S, check=check)
        if S.ambient().dimension() == 7:
            return _Virtual_intersection_of_three_quadrics_in_P7(S, check=check)
        raise NotImplementedError("Hodge-special fourfold containing a virtual surface in PP^" + str(S.ambient().dimension()))
    S = _check_type_embedded_projective_variety(S)
    if X is not None:
        X = _check_type_embedded_projective_variety(X)
    if V is not None:
        V = _check_type_embedded_projective_variety(V)
    n = S.ambient().dimension()
    if n == 7:
        if X is None:
            if V is None:
                V = S.random(2,2)
            X = V.intersection(S.random(2))
        if V is None:
            V = X.random(2,2)
        return _Intersection_of_three_quadrics_in_P7(S,X,V,check)
    if n == 5:
        if X is None:
            X = S.random(3)
        return Cubic_fourfold(S,X,V,check)
    if X is None:
        raise Exception("missing fourfold in input")
    if n == 8 and X.degree() == 10 and X.sectional_genus() == 6 and X.degrees_generators() == (2,2,2,2,2,2):
        return GushelMukai_fourfold(S,X,V,check)
    return Hodge_special_fourfold(S,X,V,check)

def _special_fourfold_from_m2(s, i=None):
    r"""Special fourfolds constructed with Macaulay2."""
    if not isinstance(s,str):
        raise TypeError("expected a string")
    if not(i is None or isinstance(i,(int,Integer)) or i in Fields()):
        raise TypeError("expected an integer or a field")
    t = ')' if i is None else ', ' + str(i) + ')' if isinstance(i,(int,Integer)) else ', ' + macaulay2(i).toExternalString().sage() + ')'
    XinM2 = macaulay2('specialFourfold("' + s + '"' + t).removeUnderscores()
    V = ProjectiveSpace(XinM2.ambient().ring().sage())
    return(_from_macaulay2_to_sage(XinM2,V))

def _expr_var_0(Dim, DimAmbient):
    if DimAmbient < 0:
        return("empty scheme", "\\mbox{empty scheme}")
    if Dim < 0 and DimAmbient < 1:
        return("empty scheme", "\\mbox{empty scheme}") # provisional
    if Dim < 0:
        return("empty subscheme of PP^" + str(DimAmbient), "\\mbox{empty subscheme of }\\mathbb{P}^{" + latex(DimAmbient) + "}")
    if Dim == DimAmbient:
        return("PP^" + str(DimAmbient), "\\mathbb{P}^{" + latex(DimAmbient) + "}")
    if Dim == 1:
        return("curve in PP^" + str(DimAmbient), "\\mbox{curve in }" + "\\mathbb{P}^{" + latex(DimAmbient) + "}")
    if Dim == 2:
        return("surface in PP^" + str(DimAmbient), "\\mbox{surface in }" + "\\mathbb{P}^{" + latex(DimAmbient) + "}")
    if DimAmbient - Dim == 1:
        return("hypersurface in PP^" + str(DimAmbient), "\\mbox{hypersurface in }" + "\\mathbb{P}^{" + latex(DimAmbient) + "}")
    if Dim == 3:
        return("threefold in PP^" + str(DimAmbient), "\\mbox{threefold in }" + "\\mathbb{P}^{" + latex(DimAmbient) + "}")
    return(str(Dim) + "-dimensional subvariety of PP^" + str(DimAmbient), latex(Dim) + "\\mbox{-dimensional subvariety of }" + "\\mathbb{P}^{" + latex(DimAmbient) + "}")

def _expr_var_1(X):
    k = X.dimension()
    n = X.ambient().dimension()
    if k < 0 or k >= n:
        return _expr_var_0(k,n)
    degs = X.degrees_generators()
    if k == 0:
        if X._is_point():
            c = " of coordinates " + str(X._coordinates())
            c_l = "\\mbox{ of coordinates }" + latex(X._coordinates())
            return("one-point scheme in PP^" + str(n) + c, "\\mbox{one-point scheme in }" + "\\mathbb{P}^{" + latex(n) + "}" + c_l)
        else:
            return("0-dimensional subscheme of degree " + str(X.degree()) + " in PP^" + str(n), latex(0) + "\\mbox{-dimensional subscheme of degree }" + latex(X.degree())  + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}")
    cutOut = ""
    if len(degs) > 1:
        if degs.count(degs[0]) == len(degs):
            cutOut = " cut out by " + str(len(degs)) + " hypersurfaces of degree " + str(degs[0])
        else:
            cutOut = " cut out by " + str(len(degs)) + " hypersurfaces of degrees " + str(tuple(degs))
    cutOut_l = ""
    if len(degs) > 1:
        if degs.count(degs[0]) == len(degs):
            cutOut_l = "\\mbox{ cut out by }" + latex(len(degs)) + "\\mbox{ hypersurfaces of degree }" + latex(degs[0])
        else:
            cutOut_l = "\\mbox{ cut out by }" + latex(len(degs)) + "\\mbox{ hypersurfaces of degrees }" + latex(tuple(degs))
    if k == 1:
        if degs.count(1) == len(degs) and X.degree() == 1:
            return("line in PP^" + str(n), "\\mbox{line in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if X.degree() == 2 and X.sectional_genus() == 0:
            return("conic curve in PP^" + str(n), "\\mbox{conic curve in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if X.degree() == 3:
            return("cubic curve of arithmetic genus " + str(X.sectional_genus()) + " in PP^" + str(n) + cutOut, "\\mbox{cubic curve of arithmetic genus }" + latex(X.sectional_genus()) + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}" + cutOut_l)
        return("curve of degree " + str(X.degree()) + " and arithmetic genus " + str(X.sectional_genus()) + " in PP^" + str(n) + cutOut, "\\mbox{curve of degree }" + latex(X.degree()) + "\\mbox{ and arithmetic genus }" + latex(X.sectional_genus()) + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}" + cutOut_l)
    if k == 2:
        if degs.count(1) == len(degs) and X.degree() == 1:
            return("plane in PP^" + str(n), "\\mbox{plane in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if X.degree() == 2:
            return("quadric surface in PP^" + str(n), "\\mbox{quadric surface in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if X.degree() == 3:
            return("cubic surface in PP^" + str(n) + cutOut, "\\mbox{cubic surface in }" + "\\mathbb{P}^{" + latex(n) + "}" + cutOut_l)
        return("surface in PP^" + str(n) + " of degree " + str(X.degree()) + " and sectional genus " + str(X.sectional_genus()) + cutOut, "\\mbox{surface in }\\mathbb{P}^{" + latex(n) + "}" + "\\mbox{ of degree }" + latex(X.degree()) + "\\mbox{ and sectional genus }" + latex(X.sectional_genus()) + cutOut_l)
    if len(degs) == 1 and n - k == 1 and degs[0] == X.degree():
        if degs[0] == 1:
            return("hyperplane in PP^" + str(n), "\\mbox{hyperplane in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if degs[0] == 2:
            return("quadric hypersurface in PP^" + str(n), "\\mbox{quadric hypersurface in }" + "\\mathbb{P}^{" + latex(n) + "}")
        if degs[0] == 3:
            return("cubic hypersurface in PP^" + str(n), "\\mbox{cubic hypersurface in }" + "\\mathbb{P}^{" + latex(n) + "}")
        return("hypersurface of degree " + str(X.degree()) + " in PP^" + str(n), "\\mbox{hypersurface of degree }" + latex(X.degree()) + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}")
    if len(degs) == n - k and X.degree() == product(degs):
        if degs.count(1) == len(degs):
            return("linear " + str(k) + "-dimensional subspace of PP^" + str(n),   "\\mbox{linear }" + latex(X.dimension()) + "\\mbox{-dimensional subspace of }\\mathbb{P}^{" + latex(n) + "}")
        return("complete intersection of type " + str(tuple(degs)) + " in PP^" + str(n), "\\mbox{complete intersection of type }" + latex(tuple(degs)) + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}")
    return(str(k) + "-dimensional variety of degree " + str(X.degree()) + " in PP^" + str(n) + cutOut, latex(k) + "\\mbox{-dimensional variety of degree }" + latex(X.degree()) + "\\mbox{ in }\\mathbb{P}^{" + latex(n) + "}" + cutOut_l)

def _random1(R):
    return(sum([R.random_element(degree=0) * x for x in R.gens()]))

def _from_macaulay2_to_sage(X, Sage_Ambient_Space):
    r"""Convert varieties and special fourfolds from Macaulay2 to Sage.

    TESTS::

        sage: S_sage = surface(3,1,1)
        sage: V = S_sage.ambient_space()
        sage: S_m2 = macaulay2(S_sage)                                                 # optional - macaulay2
        sage: assert(_from_macaulay2_to_sage(S_m2,V) is S_sage)                        # optional - macaulay2
        sage: Y_m2 = S_m2.ambient()                                                    # optional - macaulay2
        sage: Y_sage = _from_macaulay2_to_sage(Y_m2,V)                                 # optional - macaulay2
        sage: assert(macaulay2(Y_sage) is Y_m2)                                        # optional - macaulay2
        sage: Z_m2 = S_m2.point()                                                      # optional - macaulay2
        sage: Z_sage = _from_macaulay2_to_sage(Z_m2,V)                                 # optional - macaulay2
        sage: assert(macaulay2(Z_sage) is Z_m2)                                        # optional - macaulay2
        sage: X_sage = fourfold(S_sage)                                                # optional - macaulay2
        sage: X_m2 = macaulay2(X_sage)                                                 # optional - macaulay2
        sage: assert(_from_macaulay2_to_sage(X_m2,V) is X_sage)                        # optional - macaulay2
        sage: assert(macaulay2(X_sage.surface()) == X_m2.surface())                    # optional - macaulay2
        sage: assert(macaulay2(X_sage.ambient_fivefold()) == X_m2.ambientFivefold())   # optional - macaulay2

    """
    if not isinstance(X,sage.interfaces.abc.Macaulay2Element):
        raise TypeError("expected a Macaulay2 object")
    try:
        return X._sage_object
    except AttributeError:
        if X.instance('HodgeSpecialFourfold').sage():
            varX = _from_macaulay2_to_sage(X.ring().projectiveVariety(), Sage_Ambient_Space)
            varS = _from_macaulay2_to_sage(X.surface(), Sage_Ambient_Space)
            varV = _from_macaulay2_to_sage(X.ambientFivefold(), Sage_Ambient_Space)
            if not hasattr(varS,"_finite_number_of_nodes"):
                varS._finite_number_of_nodes = X.surface().numberNodes().sage()
                assert(isinstance(varS._finite_number_of_nodes,(int,Integer)))
            X._sage_object = fourfold(varS,varX,varV,check=False)
            X._sage_object._macaulay2_object = X
            return X._sage_object
        if X.instance('EmbeddedProjectiveVariety').sage():
            polys = X.ideal().sage().gens()
            s = dict(zip(matrix(polys).base_ring().gens(), Sage_Ambient_Space.coordinate_ring().gens()))
            polys = [pol.subs(s) for pol in polys]
            X._sage_object = Embedded_projective_variety(Sage_Ambient_Space, polys)
            X._sage_object._macaulay2_object = X
            return X._sage_object
        raise NotImplementedError

def _from_macaulay2map_to_sagemap(f, Sage_Source=None, Sage_Target=None):
    r"""Convert rational maps from Macaulay2 to Sage.

    TESTS::

        sage: C = macaulay2(projective_variety(Veronese(1,4).to_built_in_variety()))       # optional - macaulay2
        sage: f = C.parametrize().inverse()                                                # optional - macaulay2
        sage: g = _from_macaulay2map_to_sagemap(f); g                                      # optional - macaulay2
        birational map defined by forms of degree 1
        source: curve of degree 4 and arithmetic genus 0 in PP^4 cut out by 6 hypersurfaces of degree 2
        target: PP^1
        sage: assert(macaulay2(g) is f)                                                    # optional - macaulay2

    """
    if not isinstance(f,sage.interfaces.abc.Macaulay2Element):
        raise TypeError("expected a Macaulay2 object")
    if not f.instance('MultirationalMap').sage():
        raise ValueError("expected a Macaulay2 object of type multi-rational map")
    try:
        return f._sage_object
    except AttributeError:
        if Sage_Source is None:
            Sage_Source = _from_macaulay2_to_sage(f.source(), ProjectiveSpace(f.source().ambient().ring().sage()))
        if Sage_Target is None:
            Sage_Target = _from_macaulay2_to_sage(f.target(), ProjectiveSpace(f.target().ambient().ring().sage()))
        if (macaulay2('SpecialFanoFourfolds.Options.Version >= "2.7.1"')).sage():
            polys = f.entries().flatten().sage()
        else:
            polys = f.matrix().entries().flatten().sage()
        s = dict(zip(matrix(polys).base_ring().gens(), Sage_Source.ambient().coordinate_ring().gens()))
        polys = [pol.subs(s) for pol in polys]
        f._sage_object = Rational_map_between_embedded_projective_varieties(Sage_Source,Sage_Target,polys)
        f._sage_object._macaulay2_object = f
        if not f.sharp('"isDominant"')._operator('===',macaulay2('null')).sage():
            f._sage_object._is_dominant = f.sharp('"isDominant"').sage()
            assert(isinstance(f._sage_object._is_dominant,bool))
        if not f.sharp('"isBirational"')._operator('===',macaulay2('null')).sage():
            f._sage_object._is_birational = f.sharp('"isBirational"').sage()
            assert(isinstance(f._sage_object._is_birational,bool))
        if f._sage_object._is_dominant is not True and (not hasattr(f._sage_object,"_closure_of_image")) and (not f.sharp('"image"')._operator('===',macaulay2('null')).sage()):
            Z = _from_macaulay2_to_sage(f.image(), Sage_Target.ambient_space())
            assert(Z.is_subset(f._sage_object.target()))
            f._sage_object._closure_of_image = Z
        if f._sage_object._is_morphism is not True and (not hasattr(f._sage_object,"_list_of_representatives_of_map")) and (not f.toRationalMap().sharp('"maps"')._operator('===',macaulay2('null')).sage()):
            assert(macaulay2(f._sage_object) is f)
            f._sage_object._representatives(verbose=False,algorithm='macaulay2')
            assert(hasattr(f._sage_object,"_list_of_representatives_of_map"))
        return f._sage_object

def _print_partial_M2_output(m2_str):
    w = str(macaulay2.eval(m2_str))
    lineNumber = int(str(macaulay2.eval('lineNumber')))-1
    lineNumber = str(macaulay2.eval('concatenate(interpreterDepth:"o") | toString(' + str(lineNumber) + ')'))
    i = w.find(lineNumber)
    if i != -1:
        w = w[:i]
    while w[-1] == "\n":
        w = w[:len(w)-1]
    print(w)

def update_macaulay2_packages():
    r"""Update some ``Macaulay2`` packages to their latest version.

    Execute the command ``update_macaulay2_packages()`` to download in your current directory
    all the ``Macaulay2`` packages needed to the functions of this module.
    You don't need to do this if you use the development version of ``Macaulay2``.
    """
    import os
    inp = input('Do you want to download or update all the needed files in the current directory: ' + os.getcwd() + "? (y/n) ")
    if inp not in ('y', 'Y', 'yes', 'Yes', 'YES'):
        print('## Update not executed. ##')
        return
    print('Downloading files in ' + os.getcwd() + '...')
    s1 = "curl -s -o Cremona.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona.m2 && mkdir -p Cremona && curl -s -o Cremona/tests.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/tests.m2 && curl -s -o Cremona/documentation.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/documentation.m2 && curl -s -o Cremona/examples.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/examples.m2 &&curl -s -o MultiprojectiveVarieties.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/MultiprojectiveVarieties.m2 && curl -s -o SpecialFanoFourfolds.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/SpecialFanoFourfolds.m2"
    os.system(s1)
    s2 = "curl -s -o Resultants.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Resultants.m2 && curl -s -o SparseResultants.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/SparseResultants.m2"
    os.system(s2)
    s3 = "curl -s -o PrebuiltExamplesOfRationalFourfolds.m2 https://raw.githubusercontent.com/giovannistagliano/PrebuiltExamplesOfRationalFourfolds/main/PrebuiltExamplesOfRationalFourfolds.m2"
    os.system(s3)
    if os.path.isfile('Cremona.m2') and os.path.isdir('Cremona') and os.path.isfile('Cremona/tests.m2') and os.path.isfile('Cremona/documentation.m2') and os.path.isfile('Cremona/examples.m2') and os.path.isfile('MultiprojectiveVarieties.m2') and os.path.isfile('SpecialFanoFourfolds.m2') and os.path.isfile('Resultants.m2') and os.path.isfile('SparseResultants.m2') and os.path.isfile('PrebuiltExamplesOfRationalFourfolds.m2'):
        print('Download successfully completed.')
    else:
        raise FileNotFoundError("something went wrong")
    print('## You should restart Sage and reload this module.')

def _set_macaulay2_():
    r"""Setting of ``Macaulay2``."""
    if not (Macaulay2().is_present() and macaulay2.version() >= (1, 21)):
        if __name__ == "__main__":
            print("Please, install Macaulay2 version 1.21 or newer to use the module sff.py")
        return
    macaulay2('needsPackage "SpecialFanoFourfolds"')
    if __name__ == "__main__" and not (macaulay2('SpecialFanoFourfolds.Options.Version >= "2.7.1"')).sage():
        print(r"""Your version of some Macaulay2 package is outdated. Please, execute the command:

update_macaulay2_packages()

to download in your current directory all the updated packages needed to the functions of the module sff.py.

Alternatively, you may execute the following command in a Unix/Linux shell: curl -s -o Cremona.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona.m2 && mkdir -p Cremona && curl -s -o Cremona/tests.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/tests.m2 && curl -s -o Cremona/documentation.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/documentation.m2 && curl -s -o Cremona/examples.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/Cremona/examples.m2 &&curl -s -o MultiprojectiveVarieties.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/MultiprojectiveVarieties.m2 && curl -s -o SpecialFanoFourfolds.m2 https://raw.githubusercontent.com/Macaulay2/M2/development/M2/Macaulay2/packages/SpecialFanoFourfolds.m2
""")
    macaulay2.options.after_print = True
    macaulay2('importFrom_MultiprojectiveVarieties {"coordinates"}')
    macaulay2('importFrom_SpecialFanoFourfolds {"eulerCharacteristic", "numberNodes", "fanoMap", "recognize", "imageOfAssociatedMap"}')
    macaulay2('importFrom_Cremona {"maps"}')
    # I got problems switching from M2 to sage objects due to underscores in the variables.
    # This interim M2 code solves the problem.
    macaulay2.eval(r"""
removeUnderscores = method()
removeUnderscores (Ring, ZZ) := memoize((K, n) -> (
    assert(isField K);
    if n>30 then return K[vars(52..52+n)];
    (x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10) := (local x0,local x1,local x2,local x3,local x4,local x5,local x6,local x7,local x8,local x9,local x10);
    (x11,x12,x13,x14,x15,x16,x17,x18,x19,x20) := (local x11,local x12,local x13,local x14,local x15,local x16,local x17,local x18,local x19,local x20);
    (x21,x22,x23,x24,x25,x26,x27,x28,x29,x30) := (local x21,local x22,local x23,local x24,local x25,local x26,local x27,local x28,local x29,local x30);
    K[take((x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10)|(x11,x12,x13,x14,x15,x16,x17,x18,x19,x20)|(x21,x22,x23,x24,x25,x26,x27,x28,x29,x30),n+1)]
));
removeUnderscores EmbeddedProjectiveVariety := X -> (
    if X.cache#?"removeUnderscores" then return X.cache#"removeUnderscores";
    P := removeUnderscores(coefficientRing X,dim ambient X);
    Y := projectiveVariety(sub(ideal X,vars P),Saturate=>false);
    if codim Y > 0 then assert(ambient Y === projectiveVariety P) else assert(ambient Y == projectiveVariety P);
    if X.cache#?"euler" then Y.cache#"euler" = X.cache#"euler";
    if X.cache#?"FiniteNumberOfNodes" then Y.cache#"FiniteNumberOfNodes" = X.cache#"FiniteNumberOfNodes";
    if codim ambientVariety X > 0 then Y % removeUnderscores(ambientVariety X);
    Y.cache#"removeUnderscores" = Y;
    X.cache#"removeUnderscores" = Y
);
removeUnderscores RationalMap := f -> (
    if f#"map".cache#?"removeUnderscores" then return f#"map".cache#"removeUnderscores";
    P1 := removeUnderscores(coefficientRing f, f#"dimAmbientTarget");
    P2 := removeUnderscores(coefficientRing f, f#"dimAmbientSource");
    g := sub(f,P1,P2);
    g#"map".cache#"removeUnderscores" = g;
    f#"map".cache#"removeUnderscores" = g
);
removeUnderscores MultirationalMap := f -> (
    if f.cache#?"removeUnderscores" then return f.cache#"removeUnderscores";
    g := multirationalMap removeUnderscores toRationalMap f;
    g.cache#"removeUnderscores" = g;
    f.cache#"removeUnderscores" = g
);
removeUnderscores (EmbeddedProjectiveVariety,MultirationalMap) := (X,f) -> (
    if f.cache#?("removeUnderscores",X) then return f.cache#("removeUnderscores",X);
    g := removeUnderscores f;
    local h;
    if SpecialFanoFourfolds.Options.Version >= "2.7.1" then (
        h = (Hom(X,target g)) entries sub(matrix entries g,vars ring ambient X);
    ) else (
        h = multirationalMap rationalMap map(ring X,ring target g,sub(matrix g,vars ring ambient X));
        assert(ring source h === ring X);
        h#"source" = X;
    );
    h.cache#("removeUnderscores",X) = h;
    f.cache#("removeUnderscores",X) = h
);
removeUnderscores (EmbeddedProjectiveVariety,RationalMap) := (X,f) -> (
    if f#"map".cache#?("removeUnderscores",X) then return f#"map".cache#("removeUnderscores",X);
    g := toRationalMap removeUnderscores(X,multirationalMap f);
    g#"map".cache#("removeUnderscores",X) = g;
    f#"map".cache#("removeUnderscores",X) = g
);
removeUnderscores HodgeSpecialFourfold := X -> (
    if X.cache#?("removeUnderscores",surface X, ambientFivefold X) then return X.cache#("removeUnderscores",surface X, ambientFivefold X);
    Y := specialFourfold(removeUnderscores surface X, removeUnderscores projectiveVariety ring X, removeUnderscores ambientFivefold X, InputCheck=>0);
    S := surface Y;
    V := ambientFivefold Y;
    if (surface X).cache#?("AssociatedMapFromFivefold",ambientFivefold X) then S.cache#("AssociatedMapFromFivefold",V) = removeUnderscores(V,map X);
    if (surface X).cache#?("fanoMap",ambientFivefold X) then (
        mu := removeUnderscores(V,fanoMap X);
        mu#"map".cache#"multiplicityFanoMap" = ((fanoMap X)#"map").cache#"multiplicityFanoMap";
        S.cache#("fanoMap",V) = mu;
    );
    if (surface X).cache#?("surfaceDeterminingInverseOfFanoMap",ideal X) then (
        originalU := (surface X).cache#("surfaceDeterminingInverseOfFanoMap",ideal X);
        U := removeUnderscores originalU;
        S.cache#("surfaceDeterminingInverseOfFanoMap",ideal Y) = U;
        if originalU.cache#?"exceptionalCurves" then (
            L := (removeUnderscores first originalU.cache#"exceptionalCurves") % U;
            C := (removeUnderscores last originalU.cache#"exceptionalCurves") % U;
            U.cache#"exceptionalCurves" = (L,C);
        );
        if originalU.cache#?"MapToMinimalK3Surface" then U.cache#"MapToMinimalK3Surface" = removeUnderscores(U, originalU.cache#"MapToMinimalK3Surface");
    );
    Y.cache#("removeUnderscores",surface Y, ambientFivefold Y) = Y;
    X.cache#("removeUnderscores",surface X, ambientFivefold X) = Y
);
""")

_set_macaulay2_()

if __name__ == "__main__":
    print("""┌─────────────────────────────────────┐
 sff.py version 1.0, date: 2023-06-14""" +
("\n with SpecialFanoFourfolds.m2 v. " + macaulay2('SpecialFanoFourfolds.Options.Version').sage() if Macaulay2().is_present() else "\n Macaulay2 not present") +
"""
└─────────────────────────────────────┘""")
