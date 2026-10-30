from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GALOIS_ROOT = ROOT.parent / "Galois"
BUILD = GALOIS_ROOT / "build" / "lonestar" / "analytics" / "distributed"

DATASETS = [
    ROOT / "datasets" / "coPapersDBLP.gr",
    ROOT / "datasets" / "belgium_osm.gr",
    ROOT / "datasets" / "rgg_n_2_22_s0.gr",
    ROOT / "datasets" / "sol-LiveJournal1_sym_clear.gr",
]

BINARIES = {
    "bfs": BUILD / "bfs" / "bfs-push-dist",
    "sssp": BUILD / "sssp" / "sssp-push-dist",
    "pr": BUILD / "pagerank" / "pagerank-pull-dist",
    "tc": BUILD / "triangle-counting" / "triangle-counting-dist",
}
