"""Exercise the workflow's commit step against local Git repositories."""

import os
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/render-cards.yml"


def commit_script():
    step = WORKFLOW.read_text().split(
        "      - name: Commit the rendered cards to this branch\n", 1
    )[1]
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


@pytest.fixture
def repositories(tmp_path):
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Renderer test",
        GIT_AUTHOR_EMAIL="renderer@example.test",
        GIT_COMMITTER_NAME="Renderer test",
        GIT_COMMITTER_EMAIL="renderer@example.test",
        CARD_BRANCH="cards/share-cards",
    )

    def git(repo, *args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    origin = tmp_path / "origin.git"
    origin.mkdir()
    git(origin, "init", "--bare")
    work = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(work))
    git(work, "checkout", "-b", env["CARD_BRANCH"])
    rendered = work / "cards/campaigns/example/rendered"
    rendered.mkdir(parents=True)
    (rendered / "current.png").write_bytes(b"old image")
    (rendered / "obsolete.png").write_bytes(b"obsolete image")
    (work / "source.txt").write_text("original text")
    git(work, "add", ".")
    git(work, "commit", "-m", "Original source and images")
    git(work, "push", "origin", f"HEAD:refs/heads/{env['CARD_BRANCH']}")
    writer = tmp_path / "writer"
    git(tmp_path, "clone", "--branch", env["CARD_BRANCH"], str(origin), str(writer))
    (rendered / "current.png").write_bytes(b"fresh image")
    return work, writer, rendered, env, git


def run_commit_step(work, env):
    return subprocess.run(
        # GitHub runs a step with these flags when the workflow names shell: bash.
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", commit_script()],
        cwd=work / "cards",
        env=env,
        capture_output=True,
        text=True,
    )


def test_workflow_targets_only_branches():
    workflow = WORKFLOW.read_text()
    assert '    branches: ["**"]' in workflow
    assert "    if: github.ref_type == 'branch'" in workflow
    assert "CARD_BRANCH: ${{ github.ref_name }}" in workflow
    assert "${{" not in commit_script()


def test_commit_step_pushes_current_images_and_deletions(repositories):
    work, writer, rendered, env, git = repositories
    (rendered / "obsolete.png").unlink()
    result = run_commit_step(work, env)
    assert result.returncode == 0, result.stderr
    git(writer, "pull", "--ff-only")
    remote_images = writer / "cards/campaigns/example/rendered"
    assert (remote_images / "current.png").read_bytes() == b"fresh image"
    assert not (remote_images / "obsolete.png").exists()
    assert git(work, "status", "--porcelain") == ""


def push_from_writer(writer, env, git, path, text, message):
    target = writer / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    git(writer, "add", path)
    git(writer, "commit", "-m", message)
    git(writer, "push", "origin", f"HEAD:refs/heads/{env['CARD_BRANCH']}")
    return git(writer, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "path",
    ["cards/campaigns/example/cards.toml", "cards/make_cards.py", ".github/workflows/render-cards.yml"],
)
def test_commit_step_skips_when_card_inputs_change(repositories, path):
    # A push that changes a card input starts its own run, which draws the newer text.
    work, writer, _, env, git = repositories
    rendered_source = git(work, "rev-parse", "HEAD")
    newer = push_from_writer(writer, env, git, path, "newer input", "New card input")
    result = run_commit_step(work, env)
    assert result.returncode == 0, result.stderr
    assert "card inputs changed" in result.stdout
    assert git(work, "rev-parse", "HEAD") == rendered_source
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == newer
    assert (writer / "cards/campaigns/example/rendered/current.png").read_bytes() == b"old image"


def test_commit_step_commits_on_top_when_only_other_files_change(repositories):
    # A push outside the push paths starts no run, so this run's cards still have to land.
    work, writer, rendered, env, git = repositories
    (rendered / "obsolete.png").unlink()
    newer = push_from_writer(writer, env, git, "source.txt", "newer text", "New text outside cards/")
    result = run_commit_step(work, env)
    assert result.returncode == 0, result.stderr
    assert "committing these cards on top" in result.stdout
    git(writer, "pull", "--ff-only")
    assert git(writer, "rev-parse", "HEAD^") == newer
    remote_images = writer / "cards/campaigns/example/rendered"
    assert (remote_images / "current.png").read_bytes() == b"fresh image"
    assert not (remote_images / "obsolete.png").exists()
    assert (writer / "source.txt").read_text() == "newer text"
    assert git(writer, "show", "--name-only", "--format=", "HEAD").split() == [
        "cards/campaigns/example/rendered/current.png",
        "cards/campaigns/example/rendered/obsolete.png",
    ]


def test_commit_step_fails_when_the_branch_is_rewritten(repositories):
    work, writer, _, env, git = repositories
    (writer / "source.txt").write_text("rewritten text")
    git(writer, "commit", "--amend", "-am", "Rewritten history")
    git(writer, "push", "--force", "origin", f"HEAD:refs/heads/{env['CARD_BRANCH']}")
    rewritten = git(writer, "rev-parse", "HEAD")
    result = run_commit_step(work, env)
    assert result.returncode == 1
    assert "rewritten" in result.stdout
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == rewritten


@pytest.mark.parametrize(
    "message",
    ["Fix a typo [skip ci]", "Fix a typo [CI SKIP]", "Fix a typo [no ci]", "Fix a typo\n\n\nskip-checks: true"],
)
def test_commit_step_fails_when_a_newer_input_commit_skips_ci(repositories, message):
    # A push that skips CI starts no run, so nothing would draw its text: say so.
    work, writer, _, env, git = repositories
    newer = push_from_writer(writer, env, git, "cards/campaigns/example/cards.toml", "newer input", message)
    result = run_commit_step(work, env)
    assert result.returncode == 1
    assert "skips CI" in result.stdout
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == newer


# Before each of the step's pushes, while races remain, push a commit to the
# same branch from the writer's clone, as if someone pushed during the render.
RACING_GIT = """#!/bin/sh
if [ "$1" = "push" ]; then
  echo attempted >> "$PUSH_ATTEMPTS"
  n=$(grep -c . "$PUSH_ATTEMPTS")
  if [ "$n" -le "$RACES" ]; then
    mkdir -p "$(dirname "$RACE_WRITER/$RACE_PATH")"
    echo "race $n" >> "$RACE_WRITER/$RACE_PATH"
    "$REAL_GIT" -C "$RACE_WRITER" add -- "$RACE_PATH" || exit $?
    "$REAL_GIT" -C "$RACE_WRITER" commit --quiet -m "Race $n" || exit $?
    "$REAL_GIT" -C "$RACE_WRITER" push --quiet origin "HEAD:refs/heads/$CARD_BRANCH" || exit $?
  fi
fi
exec "$REAL_GIT" "$@"
"""


def racing(tmp_path, env, writer, path, races):
    wrapper_dir = tmp_path / "bin"
    wrapper_dir.mkdir()
    wrapper = wrapper_dir / "git"
    wrapper.write_text(RACING_GIT)
    wrapper.chmod(0o755)
    attempts = tmp_path / "push-attempts"
    race_env = dict(
        env,
        PATH=f"{wrapper_dir}{os.pathsep}{env['PATH']}",
        REAL_GIT=shutil.which("git"),
        RACE_WRITER=str(writer),
        RACE_PATH=path,
        RACES=str(races),
        PUSH_ATTEMPTS=str(attempts),
    )
    return race_env, attempts


def test_commit_step_retries_when_other_files_land_after_the_fetch(repositories, tmp_path):
    # The README-style push starts no run, so the step checks again and commits on top.
    work, writer, rendered, env, git = repositories
    (rendered / "obsolete.png").unlink()
    race_env, attempts = racing(tmp_path, env, writer, "source.txt", races=1)
    result = run_commit_step(work, race_env)
    assert result.returncode == 0, result.stderr
    assert attempts.read_text().splitlines() == ["attempted", "attempted"]
    assert "checking it again" in result.stdout
    git(writer, "pull", "--ff-only")
    assert git(writer, "log", "-1", "--format=%s", "HEAD^") == "Race 1"
    remote_images = writer / "cards/campaigns/example/rendered"
    assert (remote_images / "current.png").read_bytes() == b"fresh image"
    assert not (remote_images / "obsolete.png").exists()
    assert git(writer, "show", "--name-only", "--format=", "HEAD").split() == [
        "cards/campaigns/example/rendered/current.png",
        "cards/campaigns/example/rendered/obsolete.png",
    ]


def test_commit_step_leaves_inputs_that_land_after_the_fetch_to_their_own_run(repositories, tmp_path):
    work, writer, _, env, git = repositories
    race_env, attempts = racing(tmp_path, env, writer, "cards/campaigns/example/cards.toml", races=1)
    result = run_commit_step(work, race_env)
    assert result.returncode == 0, result.stderr
    assert attempts.read_text().splitlines() == ["attempted"]
    assert "card inputs changed" in result.stdout
    race = git(writer, "rev-parse", "HEAD")
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == race
    assert (writer / "cards/campaigns/example/rendered/current.png").read_bytes() == b"old image"


def test_commit_step_gives_up_after_five_attempts(repositories, tmp_path):
    work, writer, _, env, git = repositories
    race_env, attempts = racing(tmp_path, env, writer, "source.txt", races=99)
    result = run_commit_step(work, race_env)
    assert result.returncode == 1
    assert len(attempts.read_text().splitlines()) == 5
    assert "kept moving" in result.stdout
    race = git(writer, "rev-parse", "HEAD")
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == race
    assert (writer / "cards/campaigns/example/rendered/current.png").read_bytes() == b"old image"


def test_commit_step_reports_a_refused_push_without_retrying(repositories):
    # A remote that refuses the push itself (branch protection, say) won't change
    # its mind on a retry, so the step stops and points at git's error.
    work, writer, _, env, git = repositories
    origin = work.parent / "origin.git"
    attempts = work.parent / "receive-attempts"
    hook = origin / "hooks/pre-receive"
    hook.write_text(f'#!/bin/sh\necho attempted >> "{attempts}"\necho "refused by policy" >&2\nexit 1\n')
    hook.chmod(0o755)
    before = git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0]
    result = run_commit_step(work, env)
    assert result.returncode == 1
    assert "refused the push" in result.stdout
    assert "kept moving" not in result.stdout
    assert attempts.read_text().splitlines() == ["attempted"]
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == before


REWINDING_GIT = """#!/bin/sh
if [ "$1" = "push" ] && [ ! -e "$REWOUND" ]; then
  touch "$REWOUND"
  "$REAL_GIT" -C "$RACE_WRITER" push --quiet --force origin "$REWIND_TO:refs/heads/$CARD_BRANCH" || exit $?
fi
exec "$REAL_GIT" "$@"
"""


def test_commit_step_does_not_undo_a_rewind_during_the_push(repositories, tmp_path):
    # Someone pushes a README change, then force-pushes the branch back while the
    # step pushes. The step's commit sits on the dropped change, so pushing it
    # would bring that change back; the lease refuses it and the step starts over.
    work, writer, rendered, env, git = repositories
    original = git(writer, "rev-parse", "HEAD")
    dropped = push_from_writer(writer, env, git, "source.txt", "text that gets dropped", "Change that gets dropped")
    wrapper_dir = tmp_path / "bin"
    wrapper_dir.mkdir()
    wrapper = wrapper_dir / "git"
    wrapper.write_text(REWINDING_GIT)
    wrapper.chmod(0o755)
    race_env = dict(
        env,
        PATH=f"{wrapper_dir}{os.pathsep}{env['PATH']}",
        REAL_GIT=shutil.which("git"),
        RACE_WRITER=str(writer),
        REWIND_TO=original,
        REWOUND=str(tmp_path / "rewound"),
    )
    result = run_commit_step(work, race_env)
    assert result.returncode == 0, result.stderr
    assert "checking it again" in result.stdout
    tip = git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0]
    git(writer, "fetch", "--quiet", "origin")
    assert git(writer, "rev-parse", f"{tip}^") == original
    assert subprocess.run(
        ["git", "-C", str(writer), "merge-base", "--is-ancestor", dropped, tip], env=env
    ).returncode == 1
    assert git(writer, "show", f"{tip}:cards/campaigns/example/rendered/current.png") == "fresh image"


def test_workflow_names_bash_so_steps_run_with_pipefail():
    # The commit step's tests run it with -eo pipefail, which GitHub uses only
    # when the workflow names shell: bash.
    workflow = WORKFLOW.read_text()
    assert "    defaults:\n      run:\n" in workflow
    assert "        shell: bash\n" in workflow.split("    steps:", 1)[0]
