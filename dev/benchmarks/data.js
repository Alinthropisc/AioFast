window.BENCHMARK_DATA = {
  "lastUpdate": 1779712218508,
  "repoUrl": "https://github.com/Alinthropisc/AioFast",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "email": "Sayavdera@protonmail.com",
            "name": "Ali",
            "username": "Alinthropisc"
          },
          "committer": {
            "email": "Sayavdera@protonmail.com",
            "name": "Ali",
            "username": "Alinthropisc"
          },
          "distinct": true,
          "id": "6a2d5c838b1b503e11f36d33d9a8617946a0230b",
          "message": "ci: slim CI to Lint + Type Check\n\nDrop the multi-OS/Python test matrix and coverage job from ci.yml — they were\nflaky on macOS/Windows runners. Lint is the enforced gate; type-check runs\ninformationally (continue-on-error). Full test suite still runs locally and in\nthe nightly workflow.\n\nCo-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>",
          "timestamp": "2026-05-25T17:29:48+05:00",
          "tree_id": "993355a309d7da3fe555699975eec4b79c445637",
          "url": "https://github.com/Alinthropisc/AioFast/commit/6a2d5c838b1b503e11f36d33d9a8617946a0230b"
        },
        "date": 1779712217506,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/bench_container.py::test_bind_speed",
            "value": 508.34165674636404,
            "unit": "iter/sec",
            "range": "stddev: 0.0021574514201394444",
            "extra": "mean: 1.967180904277038 msec\nrounds: 491"
          },
          {
            "name": "benchmarks/bench_container.py::test_make_speed",
            "value": 6937.179364260991,
            "unit": "iter/sec",
            "range": "stddev: 0.00009446956693638025",
            "extra": "mean: 144.15080647212426 usec\nrounds: 1576"
          },
          {
            "name": "benchmarks/bench_container.py::test_singleton_speed",
            "value": 78930.11226489906,
            "unit": "iter/sec",
            "range": "stddev: 0.0000023503813422474305",
            "extra": "mean: 12.669435926353156 usec\nrounds: 5322"
          },
          {
            "name": "benchmarks/bench_container.py::test_resolve_with_deps",
            "value": 5598.6804502980085,
            "unit": "iter/sec",
            "range": "stddev: 0.00009913797605886391",
            "extra": "mean: 178.61351596638664 usec\nrounds: 2380"
          },
          {
            "name": "benchmarks/bench_routing.py::test_route_registration_speed",
            "value": 610.7557566691851,
            "unit": "iter/sec",
            "range": "stddev: 0.002473355389793139",
            "extra": "mean: 1.6373157175850388 msec\nrounds: 563"
          },
          {
            "name": "benchmarks/bench_routing.py::test_route_lookup_speed",
            "value": 120983.78618153888,
            "unit": "iter/sec",
            "range": "stddev: 0.0000010245400656490696",
            "extra": "mean: 8.265570383947793 usec\nrounds: 69604"
          }
        ]
      }
    ]
  }
}