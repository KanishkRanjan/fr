"""Saucy backend (vendor/saucy engine + vendor/saucy_cli.c driver).

Input: the original saucy "amorph" format —
    <n> <e> <p>
    <p-1 cumulative color-block boundaries>
    <e edge pairs>            (0-based vertices)
The format requires vertices to be numbered so that equal-colored vertices
form contiguous ascending blocks, so we renumber and translate back.
Output: one generator per line in cycle notation `(0 1)(2 3)` — 0-based.
"""
from .native import NativeGroupEngine, resolve_binary


class SaucyEngine(NativeGroupEngine):
    name = 'Saucy'
    cycle_base = 0
    input_suffix = '.amorph'

    def binary(self):
        return resolve_binary('SAUCY_BIN', 'saucy', 'saucy_bin')

    def write_input(self, graph, path):
        order = sorted(range(graph.n), key=lambda v: (graph.colors[v], v))
        new_id = [0] * graph.n
        for idx, old in enumerate(order):
            new_id[old] = idx

        # cumulative boundaries between the color blocks (all but the last)
        boundaries = []
        for idx in range(1, graph.n):
            if graph.colors[order[idx]] != graph.colors[order[idx - 1]]:
                boundaries.append(idx)
        p = len(boundaries) + 1

        lines = [f'{graph.n} {len(graph.edges)} {p}']
        lines += [str(b) for b in boundaries]
        lines += [f'{new_id[u]} {new_id[v]}' for u, v in graph.edges]
        with open(path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        return new_id
