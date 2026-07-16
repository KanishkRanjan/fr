import pytest

from er_validator.name_matcher import (
    are_synonyms,
    compare_entities,
    jaro_similarity,
    jaro_winkler_similarity,
    levenshtein_distance,
    levenshtein_similarity,
    normalize_name,
    singularize,
)

# ---------------------------- normalization ----------------------------

@pytest.mark.parametrize('raw, expected', [
    ('OrderDetails', 'order detail'),
    ('customer_orders', 'customer order'),
    ('Customer-Orders', 'customer order'),
    ('  Products  ', 'product'),
    ('categories', 'category'),
    ('addresses', 'address'),
    ('statuses', 'status'),
    ('boxes', 'box'),
    ('User!!', 'user'),
    ('user', 'user'),
    ('', ''),
    (None, ''),
])
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


@pytest.mark.parametrize('plural, singular', [
    ('people', 'person'), ('children', 'child'), ('wolves', 'wolf'),
    ('knives', 'knife'), ('heroes', 'hero'), ('analysis', 'analysis'),
    ('staff', 'staff'), ('matches', 'match'),
])
def test_singularize(plural, singular):
    assert singularize(plural) == singular


# --------------------------- string metrics ----------------------------

def test_levenshtein():
    assert levenshtein_distance('kitten', 'sitting') == 3
    assert levenshtein_distance('', 'abc') == 3
    assert levenshtein_distance('same', 'same') == 0
    assert levenshtein_similarity('', '') == 1.0
    assert levenshtein_similarity('abcd', 'abcx') == 0.75


def test_jaro_winkler():
    assert jaro_similarity('', '') == 1.0
    assert jaro_similarity('a', '') == 0.0
    assert jaro_similarity('abc', 'abc') == 1.0
    # classic reference value
    assert jaro_winkler_similarity('martha', 'marhta') == pytest.approx(0.9611, abs=1e-4)
    # prefix bonus only applies above 0.7
    assert jaro_winkler_similarity('abc', 'xyz') == jaro_similarity('abc', 'xyz')


# ------------------------------ synonyms -------------------------------

def test_synonyms_from_default_ontology():
    result = compare_entities(['Customer'], ['Client'])
    assert result['matched'][0]['type'] == 'semantic'
    assert result['score'] == 100


def test_custom_ontology():
    assert are_synonyms('gadget', 'widget', custom_ontology=[['Gadgets', 'Widgets']])
    assert not are_synonyms('gadget', 'widget')


# ---------------------------- full compare -----------------------------

def test_exact_beats_everything():
    result = compare_entities(['Orders'], ['order'])
    assert result['matched'][0]['type'] == 'exact'
    assert result['missing'] == [] and result['extra'] == []
    assert result['score'] == 100


def test_fuzzy_match_and_weight():
    result = compare_entities(['Customer'], ['Custommer'])
    m = result['matched'][0]
    assert m['type'] == 'fuzzy' and m['score'] >= 0.8
    assert result['score'] == 80  # default fuzzy weight


def test_missing_and_extra():
    result = compare_entities(['Customer', 'Order'], ['Order', 'Warehouse42'])
    assert result['missing'] == ['Customer']
    assert result['extra'] == ['Warehouse42']
    # one exact of two teachers = 50, minus extra penalty 1.67, rounded
    assert result['score'] == 48


def test_greedy_pairing_prefers_closest():
    # 'Ordr' is closer to 'Order' than 'OrderLine' is; closest pair wins first
    result = compare_entities(['Order', 'OrderLine'], ['Ordr', 'OrderLines'])
    pairs = {m['teacher']: m['student'] for m in result['matched']}
    assert pairs == {'OrderLine': 'OrderLines', 'Order': 'Ordr'}
    assert pairs['OrderLine'] == 'OrderLines'


def test_empty_inputs():
    assert compare_entities([], [])['score'] == 100
    assert compare_entities([], ['Anything'])['score'] == 0
    assert compare_entities(['Anything'], [])['score'] == 0
    assert compare_entities(['Anything'], [])['missing'] == ['Anything']


def test_one_to_one_matching():
    # a single student name can only consume one teacher name
    result = compare_entities(['User', 'Users'], ['user'])
    assert len(result['matched']) == 1
    assert len(result['missing']) == 1


def test_scoring_breakdown_consistency():
    result = compare_entities(['A_Table', 'B_Table', 'Customer'],
                              ['a table', 'Client', 'Bogus'])
    b = result['scoring_breakdown']
    assert b['matched_count'] == b['exact_count'] + b['semantic_count'] + b['fuzzy_count']
    assert b['total_teacher_count'] == 3
    assert b['final_score'] == result['score']
