"""Shared core for engines that wrap a native automorphism-group tool.

Bliss computes the automorphism group of a vertex-colored graph — it does
not answer "are these two graphs isomorphic?" directly. The standard
reduction, used here:

    H = G1 ⊎ G2, plus apex1 joined to every vertex of G1 and apex2 joined
    to every vertex of G2, both apexes sharing a color used nowhere else.

    G1 ≅ G2  ⇔  some automorphism of H maps apex1 to apex2
             ⇔  apex1 and apex2 are in the same orbit of Aut(H),

and orbit membership is a union-find over the generator permutations the
tools print. The apexes keep the test correct even when the diagrams are
disconnected (isolated tables).

Subclasses implement only: binary discovery, input-file writing, and the
numeric base of the printed cycles.
"""
import json
import os
import re
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

from ..graph_builder import ColoredGraph
from .base import EngineError, EngineResult, IsomorphismEngine

VENDOR_DIR = Path(__file__).resolve().parents[2] / 'vendor'
_CYCLE_RE = re.compile(r'\(([^()]+)\)')


def resolve_binary(env_var, paths_key, fallback):
    """Env var > vendor/paths.json > conventional vendor path."""
    p = os.environ.get(env_var)
    if not p:
        try:
            p = json.loads((VENDOR_DIR / 'paths.json').read_text()).get(paths_key)
        except (OSError, ValueError):
            p = None
    p = Path(p) if p else VENDOR_DIR / fallback
    if not p.is_file():
        raise EngineError(
            f'{paths_key} binary not found at {p} — run validator/setup.sh '
            f'(or set ${env_var})')
    return str(p)


def build_apex_union(g1, g2):
    """Disjoint union of g1 and g2 plus the two apex vertices. Returns (H, apex1, apex2)."""
    off = g1.n
    h = ColoredGraph()
    apex_color = max(g1.colors + g2.colors, default=-1) + 1
    h.n = g1.n + g2.n + 2
    h.colors = list(g1.colors) + list(g2.colors) + [apex_color, apex_color]
    apex1, apex2 = g1.n + g2.n, g1.n + g2.n + 1
    h.edges = list(g1.edges)
    h.edges += [(u + off, v + off) for u, v in g2.edges]
    h.edges += [(apex1, v) for v in range(g1.n)]
    h.edges += [(apex2, off + v) for v in range(g2.n)]
    return h, apex1, apex2


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


_NUMERIC_CYCLE = re.compile(r'^[\d,\s]+$')


def parse_generator_cycles(text, base):
    """Yield cycles (lists of 0-based ints) from cycle notation anywhere in the
    output — 'Generator: (1,3)(2,4)' (bliss). Orbit
    union-find doesn't need cycles grouped per generator, so parsing the whole
    text also survives tools wrapping long permutations across lines. Cycles
    containing anything non-numeric (prose in parentheses) are ignored."""
    for body in _CYCLE_RE.findall(text):
        if not _NUMERIC_CYCLE.match(body):
            continue
        elems = [int(x) - base for x in re.split(r'[,\s]+', body.strip()) if x]
        if len(elems) >= 2:
            yield elems


class NativeGroupEngine(IsomorphismEngine):
    #: numeric base of vertices in the tool's printed cycles (bliss/DIMACS 1)
    cycle_base = 0
    timeout_s = 60
    input_suffix = '.txt'

    def binary(self):          # pragma: no cover - overridden
        raise NotImplementedError

    def write_input(self, graph, path):
        """Write `graph` in the tool's input format. May return a vertex
        renumbering map new_id[old_id] (or None if numbering is unchanged)."""
        raise NotImplementedError

    def are_isomorphic(self, g1, g2):
        t0 = time.perf_counter()

        # trivial and fast-fail cases (the engine needs a well-formed union anyway)
        if g1.n != g2.n or len(g1.edges) != len(g2.edges) or \
           Counter(g1.colors) != Counter(g2.colors):
            return EngineResult(False, (time.perf_counter() - t0) * 1000)
        if g1.n == 0:
            return EngineResult(True, (time.perf_counter() - t0) * 1000)

        h, apex1, apex2 = build_apex_union(g1, g2)

        with tempfile.NamedTemporaryFile(
                'w', suffix=self.input_suffix, prefix='er_iso_', delete=False) as tf:
            path = tf.name
        try:
            renum = self.write_input(h, path)
            if renum:
                apex1, apex2 = renum[apex1], renum[apex2]
            out = self._run(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

        uf = UnionFind(h.n)
        gens = 0
        for cycle in parse_generator_cycles(out, self.cycle_base):
            gens += 1
            for a, b in zip(cycle, cycle[1:]):
                if not (0 <= a < h.n and 0 <= b < h.n):
                    raise EngineError(f'{self.name}: generator vertex out of range')
                uf.union(a, b)

        iso = uf.find(apex1) == uf.find(apex2)
        return EngineResult(iso, (time.perf_counter() - t0) * 1000, generators=gens)


    def _run(self, path):
        cmd = [self.binary(), path]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            raise EngineError(f'{self.name}: timed out after {self.timeout_s}s')
        except OSError as e:
            raise EngineError(f'{self.name}: failed to execute {cmd[0]}: {e}')
        if proc.returncode != 0:
            raise EngineError(
                f'{self.name}: exited with code {proc.returncode}: '
                f'{(proc.stderr or proc.stdout).strip()[:400]}')
        return proc.stdout
