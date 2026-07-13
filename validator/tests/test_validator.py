import copy
import json
from pathlib import Path

import pytest

from er_validator import SchemaError, validate

FIXTURES = Path(__file__).parent / 'fixtures'
ENGINES = ['bliss', 'saucy']

# ---------- helpers to build editor-shaped export documents ----------

_next_id = [1000]


def _uid():
    _next_id[0] += 1
    return _next_id[0]


def field(name, type='INT', pk=False, notNull=False, unique=False, increment=False, def_=''):
    return {'id': _uid(), 'name': name, 'type': type, 'pk': pk,
            'notNull': notNull, 'unique': unique, 'increment': increment, 'def': def_}


def pk_field(name='id'):
    return field(name, 'INT', pk=True, notNull=True, increment=True)


def table(name, fields):
    return {'id': _uid(), 'name': name, 'x': 0, 'y': 0, 'color': '#4a7fd6', 'fields': fields}


def rel(start_table, start_field, end_table, end_field, cardinality='many_to_one'):
    return {'id': _uid(), 'cardinality': cardinality,
            'startTable': start_table['id'], 'startField': start_field['id'],
            'endTable': end_table['id'], 'endField': end_field['id']}


def doc(tables, relationships):
    return {'title': 'test', 'seq': 1, 'tables': tables, 'relationships': relationships}


def users_posts():
    """users(id PK, email VARCHAR UNIQUE NN) <- posts(id PK, user_id INT NN, title VARCHAR NN)"""
    u_id, u_email = pk_field(), field('email', 'VARCHAR', notNull=True, unique=True)
    users = table('users', [u_id, u_email])
    p_id, p_uid, p_title = pk_field(), field('user_id', notNull=True), field('title', 'VARCHAR', notNull=True)
    posts = table('posts', [p_id, p_uid, p_title])
    return doc([users, posts], [rel(posts, p_uid, users, u_id)])


def codes(result):
    return {m['code'] for m in result['mismatches']}


# ------------------------------- tests -------------------------------

@pytest.mark.parametrize('engine', ENGINES)
def test_identical_diagrams_are_valid(engine):
    d = users_posts()
    r = validate(d, copy.deepcopy(d), engine)
    assert r['is_valid'] is True
    assert r['algorithm_used'] == engine.capitalize()
    assert r['mismatches'] == []
    assert r['stats']['engine_ran'] is True


@pytest.mark.parametrize('engine', ENGINES)
def test_renamed_and_reordered_is_still_valid(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    for t in student['tables']:
        t['name'] = t['name'] + '_renamed'
        for f in t['fields']:
            f['name'] = 'x_' + f['name']
    student['tables'].reverse()  # table order must not matter either
    r = validate(teacher, student, engine)
    assert r['is_valid'] is True


@pytest.mark.parametrize('engine', ENGINES)
def test_changed_data_type_fails(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['tables'][1]['fields'][1]['type'] = 'VARCHAR'  # posts.user_id INT -> VARCHAR
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert 'field_types' in codes(r)
    assert r['stats']['engine_ran'] is False  # pre-checks caught it


@pytest.mark.parametrize('engine', ENGINES)
def test_dropped_not_null_fails(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['tables'][0]['fields'][1]['notNull'] = False  # users.email
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert 'field_types' in codes(r)


@pytest.mark.parametrize('engine', ENGINES)
def test_missing_relationship_fails(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['relationships'] = []
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert 'relationship_count' in codes(r)


@pytest.mark.parametrize('engine', ENGINES)
def test_flipped_cardinality_fails(engine):
    # same endpoints, cardinality reversed -> semantically "one post, many users"
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['relationships'][0]['cardinality'] = 'one_to_many'
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert codes(r) & {'cardinality', 'relationship_endpoints'}


@pytest.mark.parametrize('engine', ENGINES)
def test_drawing_direction_does_not_matter(engine):
    """A -(many_to_one)-> B drawn as B -(one_to_many)-> A is the same diagram."""
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    rel_ = student['relationships'][0]
    rel_['startTable'], rel_['endTable'] = rel_['endTable'], rel_['startTable']
    rel_['startField'], rel_['endField'] = rel_['endField'], rel_['startField']
    rel_['cardinality'] = 'one_to_many'
    r = validate(teacher, student, engine)
    assert r['is_valid'] is True, r['mismatches']


@pytest.mark.parametrize('engine', ENGINES)
def test_one_to_one_direction_does_not_matter(engine):
    """one_to_one has '1' on both ends — either drag direction must match."""
    def diagram(reverse):
        u_id, p_id = pk_field(), pk_field()
        u_bio = field('bio', 'TEXT')
        users = table('users', [u_id])
        profile = table('profile', [p_id, u_bio])
        r_ = rel(profile, p_id, users, u_id, 'one_to_one') if not reverse \
            else rel(users, u_id, profile, p_id, 'one_to_one')
        return doc([users, profile], [r_])
    r = validate(diagram(False), diagram(True), engine)
    assert r['is_valid'] is True, r['mismatches']


@pytest.mark.parametrize('engine', ENGINES)
def test_redundant_flags_on_pk_do_not_matter(engine):
    """PRIMARY KEY implies NOT NULL and UNIQUE — toggling those redundant
    flags on a PK field must not change the verdict."""
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    for t_ in student['tables']:
        for f_ in t_['fields']:
            if f_['pk']:
                f_['unique'] = True     # redundant on a PK
                f_['notNull'] = False   # a PK is NOT NULL regardless
    r = validate(teacher, student, engine)
    assert r['is_valid'] is True, r['mismatches']


@pytest.mark.parametrize('engine', ENGINES)
def test_unique_still_matters_on_non_pk_fields(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['tables'][0]['fields'][1]['unique'] = False  # users.email UNIQUE dropped
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert 'field_types' in codes(r)


@pytest.mark.parametrize('engine', ENGINES)
def test_one_to_one_vs_many_to_one_still_differs(engine):
    teacher = users_posts()
    student = copy.deepcopy(teacher)
    student['relationships'][0]['cardinality'] = 'one_to_one'
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    assert 'cardinality' in codes(r)


def _two_targets(wire_both_to_a):
    """Tables A, B identical; C, D identical, each with one FK field.
    Teacher wires C->A and D->B; the buggy student wires C->A and D->A."""
    a_id, b_id = pk_field(), pk_field()
    a, b = table('a', [a_id]), table('b', [b_id])
    c_id, c_ref = pk_field(), field('ref', notNull=True)
    d_id, d_ref = pk_field(), field('ref', notNull=True)
    c, d = table('c', [c_id, c_ref]), table('d', [d_id, d_ref])
    rels = [rel(c, c_ref, a, a_id),
            rel(d, d_ref, a if wire_both_to_a else b, a_id if wire_both_to_a else b_id)]
    return doc([a, b, c, d], rels)


@pytest.mark.parametrize('engine', ENGINES)
def test_engine_catches_wiring_difference_invariants_miss(engine):
    """All pre-check invariants agree here — only real isomorphism detects the difference."""
    teacher = _two_targets(wire_both_to_a=False)
    student = _two_targets(wire_both_to_a=True)
    r = validate(teacher, student, engine)
    assert r['stats']['engine_ran'] is True   # pre-checks all passed
    assert r['is_valid'] is False
    assert codes(r) == {'structural'}


@pytest.mark.parametrize('engine', ENGINES)
def test_symmetric_relabeling_is_valid(engine):
    """Same shape with the FK targets swapped is isomorphic — engine must accept."""
    r = validate(_two_targets(False), _two_targets(False), engine)
    assert r['is_valid'] is True


@pytest.mark.parametrize('engine', ENGINES)
def test_self_referencing_fk(engine):
    e_id, e_mgr = pk_field(), field('manager_id')
    emp = table('employee', [e_id, e_mgr])
    d = doc([emp], [rel(emp, e_mgr, emp, e_id)])
    r = validate(d, copy.deepcopy(d), engine)
    assert r['is_valid'] is True


@pytest.mark.parametrize('engine', ENGINES)
def test_empty_diagrams(engine):
    empty = doc([], [])
    assert validate(empty, copy.deepcopy(empty), engine)['is_valid'] is True
    r = validate(users_posts(), empty, engine)
    assert r['is_valid'] is False
    assert 'table_count' in codes(r)


@pytest.mark.parametrize('engine', ENGINES)
def test_real_hospital_export_against_reference(engine):
    teacher = json.loads((FIXTURES / 'teacher_hospital.json').read_text())
    student = json.loads((FIXTURES / 'student_hospital.json').read_text())
    r = validate(teacher, student, engine)
    assert r['is_valid'] is False
    # the student made Patient.hospital_id a VARCHAR instead of INT
    assert 'field_types' in codes(r)
    assert any('VARCHAR' in m['message'] for m in r['mismatches'])


@pytest.mark.parametrize('engine', ENGINES)
def test_engines_agree_on_fixed_hospital(engine):
    teacher = json.loads((FIXTURES / 'teacher_hospital.json').read_text())
    student = json.loads((FIXTURES / 'student_hospital.json').read_text())
    # fix the student's mistake -> must validate despite different names/positions
    student['tables'][2]['fields'][2]['type'] = 'INT'
    r = validate(teacher, student, engine)
    assert r['is_valid'] is True, r['mismatches']


def test_unknown_algorithm_rejected():
    from er_validator.engines import EngineError
    with pytest.raises(EngineError):
        validate(users_posts(), users_posts(), 'nauty')


def test_malformed_input_rejected():
    with pytest.raises(SchemaError):
        validate({'tables': 'nope'}, users_posts())
    with pytest.raises(SchemaError):
        # relationship pointing at a field that is not in the referenced table
        d = users_posts()
        d['relationships'][0]['startField'] = 99999
        validate(d, users_posts())
