# Labs

The lab tasks, acceptance checklists and exemplar artifacts live in the course. This folder holds what the repository side needs.

- `checks/`: one script per lab, run by `.github/workflows/labs.yml` on every pull request to your fork. Each prints one line per checkable criterion, green or red, and skips when the lab's artifacts are not on the branch. The course calls them `labs/check-02` through `labs/check-07` and `labs/check-capstone`.
- `05/drill/cost.py`: the tests-first drill from the testing module's bar lesson, a docstring over a body that raises.

Your own lab artifacts go in `labs/02/`, `labs/03/`, `labs/04/`, `labs/05/`, `labs/06/` and `labs/07/` on your fork, in the shapes each lab names. The capstone's artifacts go in `capstone/`.

Run a check locally from the repository root, for example `python labs/checks/check_03.py`. It compares your branch with `origin/main`.
