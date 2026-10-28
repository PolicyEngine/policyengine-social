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
        ["bash", "-e", "-c", commit_script()],
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


def test_commit_step_skips_superseded_source(repositories):
    work, writer, _, env, git = repositories
    rendered_source = git(work, "rev-parse", "HEAD")
    (writer / "source.txt").write_text("newer text")
    git(writer, "commit", "-am", "New source")
    git(writer, "push", "origin", f"HEAD:refs/heads/{env['CARD_BRANCH']}")
    result = run_commit_step(work, env)
    assert result.returncode == 0, result.stderr
    assert "branch moved" in result.stdout
    assert git(work, "rev-parse", "HEAD") == rendered_source
    assert (writer / "cards/campaigns/example/rendered/current.png").read_bytes() == b"old image"
    assert (writer / "source.txt").read_text() == "newer text"


def test_commit_step_does_not_retry_a_rejected_push(repositories, tmp_path):
    work, writer, _, env, git = repositories
    (writer / "source.txt").write_text("text pushed during the render push")
    git(writer, "commit", "-am", "Race with renderer")
    newer_sha = git(writer, "rev-parse", "HEAD")
    wrapper_dir = tmp_path / "bin"
    wrapper_dir.mkdir()
    wrapper = wrapper_dir / "git"
    wrapper.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "push" ]; then\n'
        '  echo attempted >> "$PUSH_ATTEMPTS"\n'
        '  "$REAL_GIT" -C "$RACE_WRITER" push origin "HEAD:refs/heads/$CARD_BRANCH" || exit $?\n'
        'fi\n'
        'exec "$REAL_GIT" "$@"\n'
    )
    wrapper.chmod(0o755)
    attempts = tmp_path / "push-attempts"
    race_env = dict(
        env,
        PATH=f"{wrapper_dir}{os.pathsep}{env['PATH']}",
        REAL_GIT=shutil.which("git"),
        RACE_WRITER=str(writer),
        PUSH_ATTEMPTS=str(attempts),
    )
    result = run_commit_step(work, race_env)
    assert result.returncode != 0
    assert attempts.read_text().splitlines() == ["attempted"]
    assert git(work, "rev-parse", "HEAD^") != newer_sha
    assert git(writer, "ls-remote", "origin", f"refs/heads/{env['CARD_BRANCH']}").split()[0] == newer_sha
    assert (writer / "cards/campaigns/example/rendered/current.png").read_bytes() == b"old image"
