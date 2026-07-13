"""Cheap structural invariant checks.

These run before the isomorphism engine. Any difference means the graphs
cannot be isomorphic, so the engine is skipped — and, unlike a bare
yes/no from Bliss/Saucy, each failed invariant yields a human-readable
mismatch for the student.
"""
from collections import Counter

from .graph_builder import ColorTable, field_color_key


def _mismatch(code, message, teacher=None, student=None):
    return {'code': code, 'message': message, 'teacher': teacher, 'student': student}


def _counter_diff(code, what, tc, sc, describe=str):
    """One mismatch entry per key whose multiplicity differs."""
    out = []
    for key in sorted(set(tc) | set(sc), key=str):
        t, s = tc.get(key, 0), sc.get(key, 0)
        if t != s:
            out.append(_mismatch(
                code,
                f'teacher has {t} {what} {describe(key)}; student has {s}',
                teacher=t, student=s,
            ))
    return out


def _table_signature(t):
    """A table's shape, ignoring its name: sorted multiset of field color keys."""
    return tuple(sorted(field_color_key(f) for f in t.fields))


def _describe_signature(sig):
    return '{' + ', '.join(ColorTable.describe(k) for k in sig) + '}'


def _rel_endpoint_key(diagram, r):
    fields = {f.id: f for t in diagram.tables for f in t.fields}
    src = field_color_key(fields[r.start_field])
    dst = field_color_key(fields[r.end_field])
    # one_to_one is direction-less, so compare its endpoints as an unordered pair
    if r.cardinality == 'one_to_one' and dst < src:
        src, dst = dst, src
    return (src, dst, r.cardinality)


def _describe_endpoint(key):
    src, dst, card = key
    return f'{ColorTable.describe(src)} -> {ColorTable.describe(dst)} ({card})'


def compare(teacher, student):
    """Compare two parsed Diagrams. Returns a list of mismatch dicts (empty = all invariants agree)."""
    mismatches = []

    for code, what, tn, sn in (
        ('table_count', 'tables', len(teacher.tables), len(student.tables)),
        ('field_count', 'fields',
         sum(len(t.fields) for t in teacher.tables),
         sum(len(t.fields) for t in student.tables)),
        ('relationship_count', 'relationships',
         len(teacher.relationships), len(student.relationships)),
    ):
        if tn != sn:
            mismatches.append(_mismatch(
                code, f'teacher has {tn} {what}, student has {sn}', teacher=tn, student=sn))

    # multiset of field signatures (type + constraints), diagram-wide
    mismatches += _counter_diff(
        'field_types', 'field(s) of',
        Counter(field_color_key(f) for t in teacher.tables for f in t.fields),
        Counter(field_color_key(f) for t in student.tables for f in t.fields),
        describe=ColorTable.describe,
    )

    # multiset of whole-table shapes
    mismatches += _counter_diff(
        'table_composition', 'table(s) with fields',
        Counter(_table_signature(t) for t in teacher.tables),
        Counter(_table_signature(t) for t in student.tables),
        describe=_describe_signature,
    )

    # relationship cardinalities
    mismatches += _counter_diff(
        'cardinality', 'relationship(s) of cardinality',
        Counter(r.cardinality for r in teacher.relationships),
        Counter(r.cardinality for r in student.relationships),
    )

    # relationship endpoint signatures (what kind of field points at what kind of field)
    mismatches += _counter_diff(
        'relationship_endpoints', 'relationship(s)',
        Counter(_rel_endpoint_key(teacher, r) for r in teacher.relationships),
        Counter(_rel_endpoint_key(student, r) for r in student.relationships),
        describe=_describe_endpoint,
    )

    return mismatches
