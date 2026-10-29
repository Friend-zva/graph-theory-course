from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GALOIS_ROOT = ROOT.parent / "Galois"
BUILD = GALOIS_ROOT / "build" / "lonestar" / "analytics" / "distributed"

DATASETS = [
    ROOT / "datasets" / "coPapersDBLP.gr",
    ROOT / "datasets" / "roadNet-CA.gr",
    ROOT / "datasets" / "coAuthorsCiteseer.gr",
]

BINARIES = {
    "bfs": BUILD / "bfs" / "bfs-push-dist",
    "sssp": BUILD / "sssp" / "sssp-push-dist",
    "pr": BUILD / "pagerank" / "pagerank-pull-dist",
    "tc": BUILD / "triangle-counting" / "triangle-counting-dist",
}
