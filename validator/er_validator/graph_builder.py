"""Convert a parsed Diagram into an undirected vertex-colored graph.

Mapping (per project spec):
  * one node per field, colored by (data_type, PK, NOT NULL, UNIQUE, AUTO_INCREMENT)
    — names are deliberately NOT part of the color (structural matching);
  * plain edges form a clique among the fields of the same table
    (encodes "these fields belong to one entity");
  * each relationship start->end becomes a 2-node chain
        startField — FK_SRC — FK_DST — endField
    the marker colors carry direction and cardinality, since Bliss colors
    vertices, not edges.
"""
from dataclasses import dataclass, field
from itertools import combinations


@dataclass
class ColoredGraph:
    n: int = 0
    edges: list = field(default_factory=list)   # list[(u, v)] undirected, 0-based
    colors: list = field(default_factory=list)  # colors[v] -> int color id
    labels: list = field(default_factory=list)  # labels[v] -> human string (debug only)


class ColorTable:
    """Interns color keys (tuples) to dense integer ids, shared by both graphs
    so identical field signatures get identical color ids on both sides."""

    def __init__(self):
        self._ids = {}
        self._keys = []

    def intern(self, key):
        if key not in self._ids:
            self._ids[key] = len(self._keys)
            self._keys.append(key)
        return self._ids[key]

    def key_of(self, color_id):
        return self._keys[color_id]

    @staticmethod
    def describe(key):
        """Human-readable form of a color key for mismatch messages."""
        kind = key[0]
        if kind == 'FIELD':
            _, dtype, pk, nn, uq, ai = key
            traits = [t for t, on in (
                ('PRIMARY KEY', pk), ('NOT NULL', nn), ('UNIQUE', uq), ('AUTO_INCREMENT', ai),
            ) if on]
            return dtype + (f' [{", ".join(traits)}]' if traits else '')
        if kind in ('FK_SRC', 'FK_DST'):
            return f'{kind} ({key[1]})'
        return str(key)


def field_color_key(f):
    # A primary key is NOT NULL and UNIQUE by definition, whatever the toggles
    # say — normalize so redundant flags can't cause phantom mismatches.
    if f.pk:
        return ('FIELD', f.type, True, True, False, f.increment)
    return ('FIELD', f.type, False, f.not_null, f.unique, f.increment)


def build_graph(diagram, color_table):
    g = ColoredGraph()
    vid = {}  # field id -> vertex index

    def add_vertex(color_key, label):
        v = g.n
        g.n += 1
        g.colors.append(color_table.intern(color_key))
        g.labels.append(label)
        return v

    for t in diagram.tables:
        for f in t.fields:
            vid[f.id] = add_vertex(field_color_key(f), f'{t.name}.{f.name}')
        for a, b in combinations(t.fields, 2):
            g.edges.append((vid[a.id], vid[b.id]))

    for r in diagram.relationships:
        # one_to_one has no direction ('1' on both ends) — give both markers the
        # same color so A->B and B->A produce isomorphic encodings. one_to_many
        # was already normalized into many_to_one by the parser.
        if r.cardinality == 'one_to_one':
            src_color = dst_color = ('FK', 'one_to_one')
        else:
            src_color, dst_color = ('FK_SRC', r.cardinality), ('FK_DST', r.cardinality)
        src_marker = add_vertex(src_color, f'fk{r.id}:src')
        dst_marker = add_vertex(dst_color, f'fk{r.id}:dst')
        g.edges.append((vid[r.start_field], src_marker))
        g.edges.append((src_marker, dst_marker))
        g.edges.append((dst_marker, vid[r.end_field]))

    return g
