"""Entity name comparison: normalize -> exact -> semantic (ontology) -> fuzzy.

Port of the Entity_engine compare approach (github.com/Divyapahuja31/Entity_engine):
names are normalized (camelCase split, lowercased, singularized), then matched
in three stages of decreasing confidence:

  1. exact     -- identical normalized forms
  2. semantic  -- both names appear in the same synonym group of the ontology
  3. fuzzy     -- max(Jaro-Winkler, Levenshtein) similarity above a threshold,
                  closest pairs matched first

Unmatched teacher names are "missing", unmatched student names are "extra",
and a 0-100 score is computed from per-stage weights minus penalties.
"""
import json
import re
from pathlib import Path

_ONTOLOGY_PATH = Path(__file__).parent / 'ontology.json'
_default_ontology = None


def default_ontology():
    """Synonym groups shipped with the package (lists of interchangeable names)."""
    global _default_ontology
    if _default_ontology is None:
        _default_ontology = json.loads(_ONTOLOGY_PATH.read_text())
    return _default_ontology


# ---------------------------- normalization ----------------------------

_IRREGULAR_SINGULARS = {
    'people': 'person', 'children': 'child', 'men': 'man', 'women': 'woman',
    'teeth': 'tooth', 'feet': 'foot', 'mice': 'mouse', 'geese': 'goose',
    'indices': 'index', 'matrices': 'matrix', 'criteria': 'criterion',
}

_UNCOUNTABLE = {
    'staff', 'series', 'species', 'news', 'equipment', 'information',
    'money', 'media', 'data', 'goods', 'personnel',
}


def singularize(word):
    """Rule-based English singularizer covering the plural forms common in ER names."""
    if not word or word in _UNCOUNTABLE:
        return word
    if word in _IRREGULAR_SINGULARS:
        return _IRREGULAR_SINGULARS[word]
    if len(word) > 4 and word.endswith('ies'):
        return word[:-3] + 'y'
    if word.endswith('ives'):                       # knives, wives, lives
        return word[:-3] + 'fe'
    if len(word) > 4 and word.endswith('ves'):      # shelves, wolves
        return word[:-3] + 'f'
    if word.endswith(('ses', 'xes', 'zes', 'ches', 'shes', 'oes')):
        return word[:-2]                            # statuses, boxes, matches, heroes
    if word.endswith(('ss', 'us', 'is')):           # address, status, analysis
        return word
    if word.endswith('s'):
        return word[:-1]
    return word


def normalize_name(name):
    """Normalize an entity name to a canonical comparable form.

    OrderDetails -> "order detail", customer_orders -> "customer order".
    """
    if not name or not isinstance(name, str):
        return ''
    cleaned = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    cleaned = cleaned.lower().strip()
    cleaned = re.sub(r'[^a-z0-9\s_-]', '', cleaned)
    words = [w for w in re.split(r'[\s_-]+', cleaned) if w]
    if words:
        words[-1] = singularize(words[-1])
    return ' '.join(words)


# --------------------------- string similarity --------------------------

def levenshtein_distance(s1, s2):
    m, n = len(s1), len(s2)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                cur[j] = prev[j - 1]
            else:
                cur[j] = 1 + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur
    return prev[n]


def levenshtein_similarity(s1, s2):
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - levenshtein_distance(s1, s2) / max_len


def jaro_similarity(s1, s2):
    len1, len2 = len(s1), len(s2)
    if len1 == 0 and len2 == 0:
        return 1.0
    if len1 == 0 or len2 == 0:
        return 0.0

    match_window = max(max(len1, len2) // 2 - 1, 0)
    matches1 = [False] * len1
    matches2 = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_window)
        end = min(len2, i + match_window + 1)
        for j in range(start, end):
            if not matches2[j] and s1[i] == s2[j]:
                matches1[i] = matches2[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len1):
        if matches1[i]:
            while not matches2[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

    return (matches / len1 + matches / len2
            + (matches - transpositions / 2) / matches) / 3.0


def jaro_winkler_similarity(s1, s2, p=0.1):
    jaro = jaro_similarity(s1, s2)
    if jaro < 0.7:
        return jaro
    prefix = 0
    for c1, c2 in zip(s1[:4], s2[:4]):
        if c1 != c2:
            break
        prefix += 1
    return jaro + prefix * p * (1.0 - jaro)


# ------------------------------ synonyms -------------------------------

def are_synonyms(word1, word2, custom_ontology=(), ontology=()):
    """True if both (already-normalized) words appear in the same synonym group."""
    for group_list in (custom_ontology, ontology):
        for group in group_list:
            normalized = {normalize_name(w) for w in group}
            if word1 in normalized and word2 in normalized:
                return True
    return False


# ------------------------------ matching -------------------------------

DEFAULT_WEIGHTS = {'exact': 100, 'semantic': 100, 'fuzzy': 80}
DEFAULT_PENALTIES = {'extra': 1.67, 'missing': 0}
DEFAULT_SIMILARITY_THRESHOLD = 0.8


def compare_entities(teacher_names, student_names,
                     weights=None, penalties=None,
                     similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
                     custom_ontology=(), ontology=None):
    """Match student entity names against teacher reference names.

    Returns {'score', 'matched', 'missing', 'extra', 'scoring_breakdown'};
    each matched entry has teacher/student raw names, the match type
    ('exact' | 'semantic' | 'fuzzy'), a 0-1 score and a details string.
    """
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    penalties = {**DEFAULT_PENALTIES, **(penalties or {})}
    if ontology is None:
        ontology = default_ontology()

    def entries(names):
        return [{'raw': n, 'normalized': normalize_name(n), 'matched': False}
                for n in (names or []) if n and n.strip()]

    teachers = entries(teacher_names)
    students = entries(student_names)
    matched = []

    # Stage 1: exact matches on normalized form
    for s in students:
        for t in teachers:
            if not t['matched'] and not s['matched'] and s['normalized'] == t['normalized']:
                t['matched'] = s['matched'] = True
                matched.append({
                    'teacher': t['raw'], 'student': s['raw'],
                    'type': 'exact', 'score': 1.0,
                    'details': 'Exact match (normalized)',
                })
                break

    # Stage 2: semantic matches via ontology synonym groups
    for s in students:
        if s['matched']:
            continue
        for t in teachers:
            if t['matched']:
                continue
            if are_synonyms(s['normalized'], t['normalized'], custom_ontology, ontology):
                t['matched'] = s['matched'] = True
                matched.append({
                    'teacher': t['raw'], 'student': s['raw'],
                    'type': 'semantic', 'score': 1.0,
                    'details': f"Semantic equivalence ('{t['normalized']}' ~ '{s['normalized']}')",
                })
                break

    # Stage 3: fuzzy matches, closest pairs first
    candidates = []
    for s in students:
        if s['matched']:
            continue
        for t in teachers:
            if t['matched']:
                continue
            similarity = max(
                jaro_winkler_similarity(s['normalized'], t['normalized']),
                levenshtein_similarity(s['normalized'], t['normalized']),
            )
            if similarity >= similarity_threshold:
                candidates.append((similarity, s, t))

    candidates.sort(key=lambda c: c[0], reverse=True)
    for similarity, s, t in candidates:
        if not s['matched'] and not t['matched']:
            s['matched'] = t['matched'] = True
            matched.append({
                'teacher': t['raw'], 'student': s['raw'],
                'type': 'fuzzy', 'score': similarity,
                'details': f'Fuzzy match ({similarity * 100:.0f}% similarity)',
            })

    missing = [t['raw'] for t in teachers if not t['matched']]
    extra = [s['raw'] for s in students if not s['matched']]

    # Scoring: weighted matches over teacher count, minus missing/extra penalties
    counts = {'exact': 0, 'semantic': 0, 'fuzzy': 0}
    match_score_sum = 0.0
    for m in matched:
        counts[m['type']] += 1
        match_score_sum += weights[m['type']] / 100

    total_teacher_count = len(teachers)
    if total_teacher_count > 0:
        base_score = match_score_sum / total_teacher_count * 100
    else:
        base_score = 100.0 if not students else 0.0

    total_missing_penalty = len(missing) * penalties['missing']
    total_extra_penalty = len(extra) * penalties['extra']
    raw_score = base_score - total_missing_penalty - total_extra_penalty
    score = max(0, min(100, round(raw_score)))

    return {
        'score': score,
        'matched': matched,
        'missing': missing,
        'extra': extra,
        'scoring_breakdown': {
            'total_teacher_count': total_teacher_count,
            'matched_count': len(matched),
            'exact_count': counts['exact'],
            'semantic_count': counts['semantic'],
            'fuzzy_count': counts['fuzzy'],
            'base_score': round(base_score, 2),
            'missing_count': len(missing),
            'missing_penalty_unit': penalties['missing'],
            'total_missing_penalty': round(total_missing_penalty, 2),
            'extra_count': len(extra),
            'extra_penalty_unit': penalties['extra'],
            'total_extra_penalty': round(total_extra_penalty, 2),
            'raw_score': round(raw_score, 2),
            'final_score': score,
        },
    }
