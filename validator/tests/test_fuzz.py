"""Property-based stress tests.

For random diagrams:
  * every semantics-preserving scramble (rename, reorder, renumber ids, flip
    relationship drawing direction, add redundant PK flags) must validate;
  * every guaranteed-semantic mutation (type/constraint change, added/removed
    field or relationship, 1:1 <-> N:1 change) must NOT validate.
"""
import copy
import random

import pytest

from er_validator import validate

TYPES = ['INT', 'BIGINT', 'VARCHAR', 'TEXT', 'DATE', 'DATETIME', 'BOOLEAN', 'DECIMAL']
CARDS = ['one_to_one', 'one_to_many', 'many_to_one']
FLIP = {'one_to_many': 'many_to_one', 'many_to_one': 'one_to_many', 'one_to_one': 'one_to_one'}


def gen_diagram(seed):
    rng = random.Random(seed)
    seq = [0]

    def uid():
        seq[0] += 1
        return seq[0]

    tables = []
    for ti in range(rng.randint(1, 5)):
        fields = []
        n_fields = 0 if rng.random() < 0.05 else rng.randint(1, 5)
        for fi in range(n_fields):
            pk = fi == 0 and rng.random() < 0.8
            fields.append({
                'id': uid(), 'name': f't{ti}f{fi}', 'type': rng.choice(TYPES),
                'pk': pk, 'notNull': pk or rng.random() < 0.4,
                'unique': (not pk) and rng.random() < 0.2,
                'increment': pk and rng.random() < 0.5, 'def': '',
            })
        tables.append({'id': uid(), 'name': f'table{ti}', 'x': 0, 'y': 0,
                       'color': '#4a7fd6', 'fields': fields})

    all_fields = [(t['id'], f['id']) for t in tables for f in t['fields']]
    rels = []
    if len(all_fields) >= 2:
        for _ in range(rng.randint(0, min(6, len(all_fields)))):
            (st, sf), (et, ef) = rng.sample(all_fields, 2)
            rels.append({'id': uid(), 'cardinality': rng.choice(CARDS),
                         'startTable': st, 'startField': sf,
                         'endTable': et, 'endField': ef})
    return {'title': 'fuzz', 'seq': seq[0] + 1, 'tables': tables, 'relationships': rels}


def scramble(doc, seed):
    """Every transformation here is meaning-preserving by definition."""
    rng = random.Random(seed)
    doc = copy.deepcopy(doc)

    # fresh id space
    remap = {}
    for t in doc['tables']:
        remap[t['id']] = None
        for f in t['fields']:
            remap[f['id']] = None
    ids = list(range(5000, 5000 + len(remap)))
    rng.shuffle(ids)
    for old, new in zip(list(remap), ids):
        remap[old] = new

    rng.shuffle(doc['tables'])
    for ti, t in enumerate(doc['tables']):
        t['id'] = remap[t['id']]
        t['name'] = f'renamed_{rng.randint(0, 10 ** 6)}'
        t['color'] = '#c163b9'
        t['x'], t['y'] = rng.randint(-999, 999), rng.randint(-999, 999)
        rng.shuffle(t['fields'])
        for f in t['fields']:
            f['id'] = remap[f['id']]
            f['name'] = f'col_{rng.randint(0, 10 ** 6)}'
            if f['pk']:                       # redundant on a PK, must not matter
                if rng.random() < 0.5:
                    f['unique'] = True
                if rng.random() < 0.5:
                    f['notNull'] = False

    rng.shuffle(doc['relationships'])
    for i, r in enumerate(doc['relationships']):
        r['id'] = 9000 + i
        r['startTable'] = remap[r['startTable']]
        r['startField'] = remap[r['startField']]
        r['endTable'] = remap[r['endTable']]
        r['endField'] = remap[r['endField']]
        if rng.random() < 0.5:                # opposite drag direction, same picture
            r['startTable'], r['endTable'] = r['endTable'], r['startTable']
            r['startField'], r['endField'] = r['endField'], r['startField']
            r['cardinality'] = FLIP[r['cardinality']]
    doc['seq'] = 99999
    doc['title'] = 'scrambled'
    return doc


def mutate(doc, seed):
    """Apply one mutation that is guaranteed to change the diagram's meaning.
    Returns None if the drawn mutation is not applicable to this diagram."""
    rng = random.Random(seed)
    doc = copy.deepcopy(doc)
    fields = [(t, f) for t in doc['tables'] for f in t['fields']]
    kind = rng.choice(['type', 'not_null', 'unique', 'pk', 'add_field',
                       'del_field', 'del_rel', 'one_one_flip'])

    if kind == 'type' and fields:
        t, f = rng.choice(fields)
        f['type'] = rng.choice([x for x in TYPES if x != f['type']])
    elif kind == 'not_null':
        cand = [f for _, f in fields if not f['pk']]
        if not cand:
            return None
        f = rng.choice(cand)
        f['notNull'] = not f['notNull']
    elif kind == 'unique':
        cand = [f for _, f in fields if not f['pk']]
        if not cand:
            return None
        f = rng.choice(cand)
        f['unique'] = not f['unique']
    elif kind == 'pk' and fields:
        t, f = rng.choice(fields)
        f['pk'] = not f['pk']
    elif kind == 'add_field' and doc['tables']:
        t = rng.choice(doc['tables'])
        t['fields'].append({'id': 77777, 'name': 'extra', 'type': 'INT', 'pk': False,
                            'notNull': False, 'unique': False, 'increment': False, 'def': ''})
    elif kind == 'del_field':
        cand = [(t, f) for t, f in fields
                if not any(r['startField'] == f['id'] or r['endField'] == f['id']
                           for r in doc['relationships'])]
        if not cand:
            return None
        t, f = rng.choice(cand)
        t['fields'].remove(f)
    elif kind == 'del_rel':
        if not doc['relationships']:
            return None
        doc['relationships'].pop(rng.randrange(len(doc['relationships'])))
    elif kind == 'one_one_flip':
        if not doc['relationships']:
            return None
        r = rng.choice(doc['relationships'])
        r['cardinality'] = 'many_to_one' if r['cardinality'] == 'one_to_one' else 'one_to_one'
    else:
        return None
    return doc


@pytest.mark.parametrize('seed', range(40))
def test_scrambled_diagram_is_equivalent(seed):
    original = gen_diagram(seed)
    scrambled = scramble(original, seed + 1)
    r = validate(original, scrambled, 'bliss')
    assert r['is_valid'] is True, (seed, r['mismatches'])


@pytest.mark.parametrize('seed', range(40, 100))
def test_mutated_diagram_is_not_equivalent(seed):
    original = gen_diagram(seed)
    mutated = mutate(original, seed + 1)
    if mutated is None:
        pytest.skip('mutation not applicable to this random diagram')
    r = validate(original, mutated, 'bliss')
    assert r['is_valid'] is False, (seed, 'mutation went undetected')
