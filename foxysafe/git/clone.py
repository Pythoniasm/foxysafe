import json
import os
from multiprocessing import Pool
from pathlib import Path

from beartype import beartype
from beartype.typing import Any
from loguru import logger as log

import git
from gitlab.v4.objects import Group, Project, Snippet


@beartype
def clone_project(args) -> dict[str, Any]:
    """Clone a GitLab project to a local path."""
    project: Project
    target_path: str

    result = {
        "project_name": "",
        "project_url": "",
        "project_id": 0,
        "project_path": "",
        "is_cloned": False,
        "submodules": list(),
        "is_submodules_updated": False,
        "branches": list(),
        "is_branches_updated": False,
        "success": False,
    }
    try:
        project, target_path = args

        result.update(
            {
                "project_name": project.name,
                "project_url": project.web_url,
                "project_id": project.id,
                "project_path": target_path,
            }
        )
        log.info(f"Cloning project: {project.name} <{project.web_url}> to {target_path}...")

        repository = None
        try:
            repository = git.Repo.clone_from(
                project.web_url,
                target_path,
            )
            result["is_cloned"] = True
            log.info(f"Cloning {project.name} has completed.")
        except Exception as e:
            log.warning(f"Cloning {project.name} has failed: {e}")

        if repository:
            if repository.submodules:
                try:
                    result["submodules"] = [submodule.url for submodule in repository.submodules]
                    log.info("Update submodules...")
                    repository.submodule_update(recursive=True, init=True)
                    result["is_submodules_cloned"] = True
                    log.info("Updated submodules.")
                except Exception as e:
                    log.warning(f"Updating submodules has failed: {e}")

            remote_branches = repository.git.branch("--all").replace("remotes/", "").split("\n")[2:]
            remote_branches = [b.strip() for b in remote_branches]
            log.debug(f"Found {len(remote_branches)} remote branches: {remote_branches}")
            result["branches"] = remote_branches
            if len(remote_branches) > 1:
                for remote_branch in remote_branches:
                    try:
                        local_branch = remote_branch.replace("origin/", "").strip()
                        remote_branch = remote_branch.strip()
                        repository.git.branch("--track", local_branch, remote_branch)
                        log.debug(f"Tracking branch {remote_branch}.")
                    except Exception:
                        log.warning(f"Tracking branch {remote_branch} has failed.")

                try:
                    log.info("Pulling all additional branches...")
                    repository.git.fetch("--all")
                    repository.git.pull("--all")

                    result["is_branches_updated"] = True
                except Exception as e:
                    log.warning(f"Pulling all additional branches has failed: {e}")

            else:
                log.info("No additional branches to pull.")
                result["is_branches_updated"] = True

            with open(Path(target_path) / f"../project_{project.id}.json", "w", encoding="utf-8") as f:
                json.dump(project.asdict(), f, indent=4, sort_keys=True)

            result["success"] = (
                True
                if result["is_cloned"]
                and (bool(result["submodules"]) is result["is_submodules_updated"])
                and result["is_branches_updated"]
                else False
            )

    except KeyboardInterrupt:
        log.warning(f"Cloning {project.name} has been interrupted.")
        result["success"] = False
    except Exception as e:
        log.error(f"Cloning {project.name} has failed: {e}")
        result["success"] = False
    finally:
        return result


@beartype
def clone_wiki(args) -> dict[str, Any]:
    """Clone a GitLab project to a local path."""
    obj: Group | Project
    target_path: str

    result = {
        "wiki_name": "",
        "wiki_url": "",
        "wiki_id": 0,
        "wiki_path": "",
        "is_cloned": False,
        "submodules": list(),
        "is_submodules_updated": False,
        "branches": list(),
        "is_branches_updated": False,
        "success": False,
    }
    try:
        obj, target_path = args
        result.update(
            {
                "wiki_name": obj.name + " Wiki",
                "wiki_url": obj.web_url + ".wiki.git",
                "wiki_id": obj.id,
                "wiki_path": target_path,
            }
        )
        log.info(f"Cloning wiki: {result['wiki_name']} <{result['wiki_url']}> to {target_path}...")

        repository = None
        try:
            repository = git.Repo.clone_from(
                result["wiki_url"],
                target_path,
            )
            result["is_cloned"] = True
            log.info(f"Cloning {result['wiki_name']} has completed.")
        except Exception as e:
            log.warning(f"Cloning {result['wiki_name']} has failed: {e}")

        if repository:
            if repository.submodules:
                try:
                    result["submodules"] = [submodule.url for submodule in repository.submodules]
                    log.info("Update submodules...")
                    repository.submodule_update(recursive=True, init=True)
                    result["is_submodules_cloned"] = True
                    log.info("Updated submodules.")
                except Exception as e:
                    log.warning(f"Updating submodules has failed: {e}")

            remote_branches = repository.git.branch("--all").replace("remotes/", "").split("\n")[2:]
            remote_branches = [b.strip() for b in remote_branches]
            log.debug(f"Found {len(remote_branches)} remote branches: {remote_branches}")
            result["branches"] = remote_branches
            if len(remote_branches) > 1:
                for remote_branch in remote_branches:
                    try:
                        local_branch = remote_branch.replace("origin/", "").strip()
                        remote_branch = remote_branch.strip()
                        repository.git.branch("--track", local_branch, remote_branch)
                        log.debug(f"Tracking branch {remote_branch}.")
                    except Exception:
                        log.warning(f"Tracking branch {remote_branch} has failed.")

                try:
                    log.info("Pulling all additional branches...")
                    repository.git.fetch("--all")
                    repository.git.pull("--all")

                    result["is_branches_updated"] = True
                except Exception as e:
                    log.warning(f"Pulling all additional branches has failed: {e}")

            else:
                log.info("No additional branches to pull.")
                result["is_branches_updated"] = True

            result["success"] = (
                True
                if result["is_cloned"]
                and (bool(result["submodules"]) is result["is_submodules_updated"])
                and result["is_branches_updated"]
                else False
            )

    except KeyboardInterrupt:
        log.warning(f"Cloning {result['wiki_name']} has been interrupted.")
        result["success"] = False
    except Exception as e:
        log.error(f"Cloning {result['wiki_name']} has failed: {e}")
        result["success"] = False
    finally:
        return result


@beartype
def clone_snippet(args) -> dict[str, Any]:
    """Clone a GitLab snippet to a local path."""
    snippet: Snippet
    target_path: str

    result = {
        "snippet_title": "",
        "snippet_url": "",
        "snippet_id": 0,
        "snippet_path": "",
        "is_cloned": False,
        "success": False,
    }
    try:
        snippet, target_path = args

        result.update(
            {
                "snippet_title": snippet.title,
                "snippet_url": snippet.web_url,
                "snippet_id": snippet.id,
                "snippet_path": target_path,
            }
        )
        log.info(f"Cloning snippet: {snippet.id} <{snippet.web_url}> to {target_path}...")

        repository = None
        try:
            repository = git.Repo.clone_from(snippet.web_url.replace("/-/", "/"), target_path)
            result["is_cloned"] = True
            log.info(f"Cloning {snippet.id} has completed.")
        except Exception as e:
            log.warning(f"Cloning {snippet.id} has failed: {e}")

        if repository:
            with open(Path(target_path) / f"../snippet_{snippet.id}.json", "w", encoding="utf-8") as f:
                json.dump(snippet.asdict(), f, indent=4, sort_keys=True)

            result["success"] = True if result["is_cloned"] else False

    except KeyboardInterrupt:
        log.warning(f"Cloning {snippet.id} has been interrupted.")
        result["success"] = False
    except Exception as e:
        log.error(f"Cloning {snippet.id} has failed: {e}")
        result["success"] = False
    finally:
        return result


@beartype
def clone_projects(projects: dict[str, Project], backup_dir: Path) -> None:
    """Clone GitLab projects to a local path.

    Args:
        projects (dict[str, Project]): GitLab projects dictionary.
        backup_dir (Path): Backup directory.
    """
    mapped_args = list()
    for project in projects.values():
        mapped_args.append((project, Path(backup_dir / project.path_with_namespace).resolve().as_posix()))

    with Pool(processes=min(1, os.cpu_count() - 2)) as pool:
        results = pool.map(clone_project, mapped_args)

    success = all(list(map(lambda x: x["success"], results)))
    log.info(f"Cloning {'has' if success else 'has not'} been completed successfully.")
    log.info(f"Successful clones: {list(map(lambda x: x['project_name'], filter(lambda x: x['success'], results)))}")
    if not success:
        log.warning(
            f"Failed clones: {list(map(lambda x: x['project_name'], filter(lambda x: not x['success'], results)))}"
        )

    log.info("See results.json for details.")
    with open(backup_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, sort_keys=True)


@beartype
def clone_wikis(obj: dict[str, Group | Project], backup_dir: Path) -> None:
    """Clone GitLab group or project wiki to a local path.

    Args:
        groups (dict[str, Group | Project]): GitLab groups dictionary.
        backup_dir (Path): Backup directory.
    """
    mapped_args = list()
    for obj in obj.values():
        mapped_args.append((obj, Path(backup_dir / f"{obj.path_with_namespace}.wiki").resolve().as_posix()))

    with Pool(processes=min(1, os.cpu_count() - 2)) as pool:
        results = pool.map(clone_wiki, mapped_args)

    success = all(list(map(lambda x: x["success"], results)))
    log.info(f"Cloning {'has' if success else 'has not'} been completed successfully.")
    log.info(f"Successful clones: {list(map(lambda x: x['wiki_name'], filter(lambda x: x['success'], results)))}")
    if not success:
        log.warning(
            f"Failed clones: {list(map(lambda x: x['wiki_name'], filter(lambda x: not x['success'], results)))}"
        )

    log.info("See results.json for details.")
    with open(backup_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, sort_keys=True)


@beartype
def clone_snippets(snippets: dict[int, Snippet], backup_dir: Path) -> None:
    """Clone GitLab snippets to a local path.

    Args:
        snippets (dict[int, Snippet]): GitLab snippets dictionary.
        backup_dir (Path):  Backup directory.
    """
    mapped_args = list()
    backup_dir = Path(backup_dir / "snippets")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for snippet in snippets.values():
        mapped_args.append((snippet, Path(backup_dir / f"{snippet.id}").resolve().as_posix()))

    with Pool(processes=min(1, os.cpu_count() - 2)) as pool:
        results = pool.map(clone_snippet, mapped_args)

    success = all(list(map(lambda x: x["success"], results)))
    log.info(f"Cloning {'has' if success else 'has not'} been completed successfully.")
    log.info(f"Successful clones: {list(map(lambda x: x['snippet_id'], filter(lambda x: x['success'], results)))}")
    if not success:
        log.warning(
            f"Failed clones: {list(map(lambda x: x['snippet_id'], filter(lambda x: not x['success'], results)))}"
        )

    log.info("See results.json for details.")
    with open(backup_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, sort_keys=True)
