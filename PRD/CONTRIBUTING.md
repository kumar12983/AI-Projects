## Contributing

Follow these minimal Git workflow rules to keep branches clean and avoid surprises.

- **Branching**: create feature branches from `main` (e.g. `2026-02-08`).
- **Sync before work**: at the start of your session run:

```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b my-feature-branch
```

- **Rebase before push / PR**: keep your feature branch up-to-date with `main`:

```bash
git fetch origin
# from your feature branch:
git rebase origin/main
# resolve conflicts, then:
git rebase --continue
```

- **Push safely after a rebase**:

```bash
# if history was rewritten by rebase
git push --force-with-lease origin <your-branch>
# otherwise
git push origin <your-branch>
```

- **Merging to `main`**: prefer Pull Requests (GitHub) so CI and reviews run. After merge:

```bash
git checkout main
git pull origin main
```

- **Do not rebase public/shared branches**: avoid rewriting history for branches others use.

- **Quick checks**:

```bash
git branch --show-current        # current local branch
git branch -r                    # remote branches
git fetch origin && git log --oneline --decorate --graph origin/main..HEAD
```

If you want, we can add a CI workflow to run tests on PRs and on `main`.
