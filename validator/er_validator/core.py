"""Validation pipeline: parse -> build colored graphs -> invariant checks -> isomorphism engine."""
import os

from .diagnostics import compare
from .engines import get_engine
from .graph_builder import ColorTable, build_graph
from .name_matcher import compare_entities
from .schema import parse_diagram

DEFAULT_ALGORITHM = 'bliss'


def default_algorithm():
    return os.environ.get('VALIDATOR_ALGORITHM', DEFAULT_ALGORITHM)


def validate(teacher_doc, student_doc, algorithm=None):
    """Validate a student's diagram export against the teacher's reference.

    Both arguments are dicts in the editor's JSON export format.
    Returns the response dict described in the README.
    Raises SchemaError (bad input) or EngineError (native tool trouble).
    """
    engine = get_engine(algorithm or default_algorithm())

    teacher = parse_diagram(teacher_doc, who='teacher')
    student = parse_diagram(student_doc, who='student')

    colors = ColorTable()  # shared: identical signatures -> identical color ids
    tg = build_graph(teacher, colors)
    sg = build_graph(student, colors)

    stats = {
        'teacher_nodes': tg.n, 'student_nodes': sg.n,
        'teacher_edges': len(tg.edges), 'student_edges': len(sg.edges),
        'engine_ran': False, 'engine_ms': None,
    }

    mismatches = compare(teacher, student)
    if not mismatches:
        result = engine.are_isomorphic(tg, sg)
        stats['engine_ran'] = True
        stats['engine_ms'] = round(result.engine_ms, 3)
        if not result.isomorphic:
            mismatches.append({
                'code': 'structural',
                'message': 'field counts, types and constraints all match, '
                           'but the relationship wiring differs from the reference model',
                'teacher': None, 'student': None,
            })

    # Name comparison is advisory: structure decides is_valid, names inform grading.
    names = compare_entities(
        [t.name for t in teacher.tables],
        [t.name for t in student.tables],
    )

    return {
        'is_valid': not mismatches,
        'algorithm_used': engine.name,
        'mismatches': mismatches,
        'names': names,
        'stats': stats,
    }
