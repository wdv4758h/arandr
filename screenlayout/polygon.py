from math import sqrt

def vector(start, end):
    return tuple(b - a for (a, b) in zip(start, end))

class Minimum(object):
    """Tracker for the minimum of a value"""
    def __init__(self):
        self.value = None

    def offer(self, new_value):
        if self.value is None or new_value < self.value:
            self.value = new_value

class ConvexPolygon(list):
    """Counterclockwise convex closed 2D polygon, consisting of points that can
    be accessed as tuples. (It is considered closed, there is no need to have
    the first and last points equal.)

    Demanding convexity as it makes point checks easier.

    >>> p = ConvexPolygon([(2, 2), (4, 2), (4, 4), (2, 4)])
    >>> p.point_distance(3, 3)
    0
    >>> p.point_distance(5, 4)
    1.0
    >>> p.point_distance(4 + 3, 4 + 4) # don't tell my numerics professor
    5.0
    """

    segments = property(lambda self: tuple(zip(self, self[1:] + [self[0],])))

    def _transform_point_to_segments(self, x, y):
        """For each segment, yield the segment's length, and the coordinates
        (s, t) of the given point (x, y) relative to the segment, where s is
        along the segment, and t gets positive outside."""
        for a, b in self.segments:
            v = vector(a, b)
            n = (v[1], -v[0]) # normal vector to outside

            relative_point = (x - a[0], y - a[1])

            # be A a 2x2 matrix so A(0, 0) is a, A(1, 0) is b and A(0, 1) is b
            # rotated around a to the outside. (with a and b transformed
            # relative to a so we don't heave to deal with affine
            # transformation)
            #
            # then A^-1(x, y) is (s, t)
            #
            # A = [v[0] n[0]; v[1] n[1]]

            invdet = 1.0 / (v[0]*n[1] - n[0]*v[1])
            s, t = (
                    invdet * (n[1] * relative_point[0] - n[0] * relative_point[1]),
                    invdet * (-v[1] * relative_point[0] + v[0] * relative_point[1])
                    )

            seglen = sqrt(v[0]**2 + v[1]**2)

            yield seglen, s, t

    def point_distance(self, x, y):
        """Return 0 if the point (x, y) is inside, else the distance to the
        polygon."""
        min_positive = Minimum()
        for seglen, s, t in self._transform_point_to_segments(x, y):
            if t >= 0: # point is now definitely outside
                if 0 <= s <= 1:
                    min_positive.offer(t * seglen)
                elif s < 0:
                    min_positive.offer(seglen * sqrt(s**2 + t**2))
                else: # s > 1
                    min_positive.offer(seglen * sqrt((s-1)**2 + t**2))
        if min_positive.value is None:
            return 0 # point is inside
        else:
            return min_positive.value

if __name__ == "__main__":
    import doctest
    doctest.testmod()
