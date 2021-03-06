from __future__ import print_function, division, absolute_import
from __future__ import unicode_literals

from shapeops.shape import zsToBeziers, reduceShape, beziersToZs
from shapeops.intersections import (
    findAllSelfIntersections, findCrossIntersections, splitShape)
from shapeops.topoly import toPoly
from shapeops.rebuild import rebuildShape
from shapeops.error import (
    InvalidSubjectContourError, InvalidClippingContourError, ExecutionError)

import pyclipper


RESOLUTION = 1 << 17


class ops(object):
    intersection = pyclipper.CT_INTERSECTION
    union = pyclipper.CT_UNION
    difference = pyclipper.CT_DIFFERENCE
    xor = pyclipper.CT_XOR


class fillRules(object):
    evenodd = pyclipper.PFT_EVENODD
    nonzero = pyclipper.PFT_NONZERO


def _executeClipper(subjectPaths, clippingPaths, operation, subjectFillRule,
                    clippingFillRule):
    pc = pyclipper.Pyclipper()
    for i, p in enumerate(subjectPaths):
        try:
            pc.AddPath(p, pyclipper.PT_SUBJECT)
        except pyclipper.ClipperException:
            raise InvalidSubjectContourError(
                "contour %d is invalid for clipping" % i)
    for j, p in enumerate(clippingPaths):
        try:
            pc.AddPath(p, pyclipper.PT_CLIP)
        except pyclipper.ClipperException:
            raise InvalidClippingContourError(
                "contour %d is invalid for clipping" % j)
    try:
        solution = pc.Execute(operation, subjectFillRule, clippingFillRule)
    except pyclipper.ClipperException as exc:
        raise ExecutionError(exc)
    return solution


def boole(operation, subjectPaths, clippingPaths=[],
          subjectFillRule=fillRules.nonzero,
          clippingFillRule=fillRules.nonzero,
          resolution=RESOLUTION):
    error = 0.5 / resolution

    ss1 = zsToBeziers(subjectPaths)
    s1 = reduceShape(ss1)
    i1 = findAllSelfIntersections(s1, ss1, error)
    findCrossIntersections(s1, s1, i1, i1, True, error)

    if clippingPaths:
        ss2 = zsToBeziers(clippingPaths)
        s2 = reduceShape(ss2)
        i2 = findAllSelfIntersections(s2, ss2, error)
        findCrossIntersections(s2, s2, i2, i2, True, error)
        findCrossIntersections(s1, s2, i1, i2, False, error)

    for intersections in i1:
        intersections.sort()
    xs1 = splitShape(ss1, i1, error)

    if clippingPaths:
        for intersections in i2:
            intersections.sort()
        xs2 = splitShape(ss2, i2, error)
    else:
        xs2 = []

    pthash = {}
    pvhash = {}

    p1 = toPoly(xs1, 1, pthash, pvhash, resolution)
    p2 = toPoly(xs2, 2, pthash, pvhash, resolution) if clippingPaths else []

    solution_paths = _executeClipper(p1, p2, operation, subjectFillRule,
                                     clippingFillRule)

    result = rebuildShape(solution_paths, [None, xs1, xs2],
                          pthash, pvhash, resolution)

    return beziersToZs(result)


def union(subjectPaths, clippingPaths=[], **kwargs):
    return boole(ops.union, subjectPaths, clippingPaths, **kwargs)


def difference(subjectPaths, clippingPaths, **kwargs):
    return boole(ops.difference, subjectPaths, clippingPaths, **kwargs)


def intersection(subjectPaths, clippingPaths, **kwargs):
    return boole(ops.intersection, subjectPaths, clippingPaths, **kwargs)


def xor(subjectPaths, clippingPaths, **kwargs):
    return boole(ops.xor, subjectPaths, clippingPaths, **kwargs)


# for compatibility with caryll-shapeops interface
removeOverlap = union
