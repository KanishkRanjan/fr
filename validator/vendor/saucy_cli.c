/*
 * saucy_cli.c — minimal standalone driver for the vendored saucy engine
 * (vendor/saucy/src/ssaucy.c, by Darga/Liffiton/Katebi, University of Michigan).
 *
 * The upstream repo wraps saucy for R, so its I/O layer needs Rcpp. This file
 * replaces only that I/O layer: it reads the original "amorph" graph format
 * and prints the automorphism generators saucy finds, one per line, in cycle
 * notation, e.g.  (0 3)(1 4)(2 5)
 *
 * amorph format (whitespace-separated integers, vertices 0-based, and
 * vertices MUST be numbered so equal-colored vertices are contiguous):
 *   n e p            # vertices, edges, number of colors
 *   b1 ... b(p-1)    # cumulative end index of color blocks 0..p-2
 *   u1 v1            # e undirected edges
 *   ...
 */
#include <stdio.h>
#include <stdlib.h>
#include "saucy.h"

static char *marks;

static int
print_automorphism(int n, const int *gamma, int nsupp, int *support, void *arg)
{
	int i, j, k;
	(void)arg;
	for (i = 0; i < nsupp; ++i) {
		k = support[i];
		if (marks[k]) continue;
		marks[k] = 1;
		printf("(%d", k);
		for (j = gamma[k]; j != k; j = gamma[j]) {
			marks[j] = 1;
			printf(" %d", j);
		}
		printf(")");
	}
	printf("\n");
	for (i = 0; i < nsupp; ++i) marks[support[i]] = 0;
	return 1; /* keep searching */
}

int
main(int argc, char **argv)
{
	int n, e, p, i, u, v;
	int *eu, *ev, *adj, *pos, *edg, *colors;
	struct saucy *s;
	struct saucy_graph sg;
	struct saucy_stats stats;
	FILE *f;

	if (argc != 2) {
		fprintf(stderr, "usage: %s <graph.amorph>\n", argv[0]);
		return 2;
	}
	f = fopen(argv[1], "r");
	if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
	if (fscanf(f, "%d %d %d", &n, &e, &p) != 3 || n <= 0 || e < 0 || p <= 0) {
		fprintf(stderr, "bad header\n"); return 2;
	}

	colors = malloc(n * sizeof(int));
	eu = malloc((e ? e : 1) * sizeof(int));
	ev = malloc((e ? e : 1) * sizeof(int));
	adj = calloc(n + 1, sizeof(int));
	pos = calloc(n + 1, sizeof(int));
	edg = malloc((2 * e + 1) * sizeof(int));
	marks = calloc(n, 1);
	if (!colors || !eu || !ev || !adj || !pos || !edg || !marks) {
		fprintf(stderr, "out of memory\n"); return 2;
	}

	/* colors from cumulative block boundaries */
	for (i = 0, v = 0; i < p - 1; ++i) {
		if (fscanf(f, "%d", &u) != 1 || u < v || u > n) {
			fprintf(stderr, "bad color boundary\n"); return 2;
		}
		while (v < u) colors[v++] = i;
	}
	while (v < n) colors[v++] = p - 1;

	/* edges -> CSR adjacency (both directions) */
	for (i = 0; i < e; ++i) {
		if (fscanf(f, "%d %d", &eu[i], &ev[i]) != 2 ||
		    eu[i] < 0 || eu[i] >= n || ev[i] < 0 || ev[i] >= n) {
			fprintf(stderr, "bad edge %d\n", i); return 2;
		}
		++adj[eu[i] + 1]; ++adj[ev[i] + 1];
	}
	fclose(f);
	for (i = 1; i <= n; ++i) adj[i] += adj[i - 1];
	for (i = 0; i < n; ++i) pos[i] = adj[i];
	for (i = 0; i < e; ++i) {
		edg[pos[eu[i]]++] = ev[i];
		edg[pos[ev[i]]++] = eu[i];
	}

	sg.n = n;
	sg.e = e;
	sg.adj = adj;
	sg.edg = edg;

	s = saucy_alloc(n);
	if (!s) { fprintf(stderr, "saucy_alloc failed\n"); return 2; }
	saucy_search(s, &sg, 0, colors, print_automorphism, NULL, &stats);
	fprintf(stderr, "group size: %fe%d  gens: %d  nodes: %d\n",
		stats.grpsize_base, stats.grpsize_exp, stats.gens, stats.nodes);
	saucy_free(s);
	return 0;
}
