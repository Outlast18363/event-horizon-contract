# Event Horizon Contract · Chapter 1: Cold Start

A playable browser prototype of a story-driven programming game. You write LeetCode-style Python functions, and their return values decide what happens in the game world.

| Work order | Algorithm | LeetCode | Your function |
| --- | --- | --- | --- |
| ① Locate | Simulation | LC 657 / 874 (simplified) | `locate_rover(log, battery)` |
| ② Launch | Sort + two pointers | LC 881 Boats to Save People | `min_launches(crates, limit)` |
| ③ Verify | Sliding window + hash map | LC 567 Permutation in String | `is_chronite(scan, signature)` |

Each output feeds the next work order. Python 3.12 runs in the browser via [Pyodide](https://pyodide.org); no server-side code.

## Run it

Pyodide needs to be served over HTTP (opening `index.html` as a file won't work):

```bash
python3 -m http.server 8765
```

Then open http://localhost:8765.

## How to play

Each work order opens with a draft that's missing one piece. **RUN** checks your function against the calibration samples (free). The amber button hands it to the outpost, and the result plays out in the story and the ledger. The **?** button has a reference solution for each work order and a chapter restart.

## Layout

```
index.html              built game (single page)
pyodide/                Pyodide 0.26.4 core; stdlib is base64 text so it can be served as .txt
src/template.html       page source: markup, styles, game logic
src/harness.py          Python sandbox: AST instrumentation for the op budget
src/cm.css              CodeMirror 5 core styles, inlined at build time
src/build.py            inlines cm.css and harness.py into template.html -> index.html
```

After editing anything in `src/`, rebuild:

```bash
python3 src/build.py
```

## Design decisions on the doc's open questions

- **② return value:** only the launch count, matching LC 881.
- **72 h window and O₂:** atmosphere only; running out doesn't end the game.
- **Op budget (③):** each loop iteration or function call costs 1 op. Built-ins that walk a collection (`Counter`, `sorted`, `sum`, slicing, `in` on a list or string) cost one op per element. Comparing two dicts or lists costs 1. Budget is 1,000,000 ops per crate.
- **Language:** Python only.
