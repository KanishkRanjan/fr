"""Bliss backend (vendor/bliss, github.com/digraphs/bliss).

Input: DIMACS graph format with vertex colors —
    p edge <n> <m>
    n <vertex> <color>     (1-based vertices)
    e <u> <v>
Output: lines like `Generator: (1,3)(2,4)` — 1-based, comma-separated cycles.
"""
from .native import NativeGroupEngine, resolve_binary


class BlissEngine(NativeGroupEngine):
    name = 'Bliss'
    cycle_base = 1
    input_suffix = '.dimacs'

    def binary(self):
        return resolve_binary('BLISS_BIN', 'bliss', 'bliss/bliss')

    def write_input(self, graph, path):
        lines = [f'p edge {graph.n} {len(graph.edges)}']
        lines += [f'n {v + 1} {c + 1}' for v, c in enumerate(graph.colors)]
        lines += [f'e {u + 1} {v + 1}' for u, v in graph.edges]
        with open(path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        return None  # numbering unchanged
