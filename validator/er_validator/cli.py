"""CLI: python -m er_validator.cli teacher.json student.json [--algorithm bliss|saucy]

Exit codes: 0 = valid, 1 = not valid, 2 = error (bad input / engine failure).
"""
import argparse
import json
import sys

from . import EngineError, SchemaError, validate
from .core import default_algorithm


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='er_validator',
        description="Validate a student's ER diagram export against a teacher's reference "
                    'via colored-graph isomorphism (Bliss / Saucy).')
    ap.add_argument('teacher', help="teacher's reference diagram JSON (editor export)")
    ap.add_argument('student', help="student's diagram JSON (editor export)")
    ap.add_argument('-a', '--algorithm', default=default_algorithm(),
                    choices=['bliss', 'saucy'], help='isomorphism backend (default: %(default)s)')
    ap.add_argument('--compact', action='store_true', help='single-line JSON output')
    args = ap.parse_args(argv)

    try:
        with open(args.teacher) as f:
            teacher = json.load(f)
        with open(args.student) as f:
            student = json.load(f)
    except (OSError, ValueError) as e:
        print(f'error: could not read input file: {e}', file=sys.stderr)
        return 2

    try:
        result = validate(teacher, student, args.algorithm)
    except (SchemaError, EngineError) as e:
        print(f'error: {e}', file=sys.stderr)
        return 2

    print(json.dumps(result) if args.compact else json.dumps(result, indent=2))
    return 0 if result['is_valid'] else 1


if __name__ == '__main__':
    sys.exit(main())
