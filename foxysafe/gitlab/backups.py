import json
from pathlib import Path

from beartype import beartype
from loguru import logger as log
from omegaconf import DictConfig

from foxysafe.git.clone import clone_projects, clone_snippets, clone_wikis
from foxysafe.gitlab.api import get_gitlab_items, gitlab_login
from foxysafe.gitlab.download import (
    FILE_UPLOAD_PATTERN,
    download_file_from_url,
    find_matches,
    get_issue_attachment_urls,
    get_wiki_attachment_urls,
)
from gitlab.v4.objects import Group, Issue, Project, ProjectIssue, ProjectIssueNote, Snippet


@beartype
def gitlab_backup_routine(config: DictConfig, backup_dir: Path) -> None:
    api = gitlab_login(config.gitlab_server, config.gitlab_personal_access_token)

    gitlab_group_ids = list(config.gitlab_group_ids) if config.gitlab_group_ids else None
    gitlab_project_ids = list(config.gitlab_project_ids) if config.gitlab_project_ids else None

    log.info(f"Searching group: {config.gitlab_group_ids}")
    groups, projects, wikis, issues, snippets = get_gitlab_items(
        api,
        gitlab_group_ids,
        gitlab_project_ids,
        config.include_personal_projects,
        config.include_wikis,
        config.include_issues,
        config.include_snippets,
    )

    log.info(f"Found a total of {len(groups)} groups.")
    log.info(f"Found a total of {len(projects)} projects to backup.")
    log.info(f"Found a total of {len(wikis)} wikis to backup.")
    log.info(f"Found a total of {len(issues)} issues to backup.")
    log.info(f"Found a total of {len(snippets)} snippets to backup.")

    if projects:
        clone_projects(projects, backup_dir)

    if wikis:
        clone_wikis(wikis, backup_dir)
        for obj in wikis.values():
            log.info(f"Backing up wiki attachments for {obj.path_with_namespace}")
            try:
                backup_wiki_attachements(config, obj, obj.path_with_namespace, backup_dir)
            except Exception as e:
                log.error(f"Failed to backup wiki attachments for {obj.path_with_namespace}:\n{e}")

    if issues:
        for issue in issues.values():
            log.info(f"Backing up issue {issue.iid} for {projects[issue.project_id].path_with_namespace}")
            try:
                backup_issue(config, issue, projects[issue.project_id].path_with_namespace, backup_dir)
                for note in issue.notes.list(all=True):
                    log.info(f"Backing up issue note {note.id} for {projects[issue.project_id].path_with_namespace}")
                    try:
                        backup_issue(
                            config,
                            note,
                            projects[issue.project_id].path_with_namespace,
                            backup_dir,
                            True,
                            web_url=issue.web_url,
                        )
                    except Exception as e:
                        log.error(f"Failed to backup issue note {note.id}:\n{e}")
            except Exception as e:
                log.error(f"Failed to backup issue {issue.iid}:\n{e}")

    if snippets:
        clone_snippets(snippets, backup_dir)
        for snippet in snippets.values():
            log.info(f"Backing up snippet {snippet.id} for {snippet.path_with_namespace}")
            try:
                backup_snippet_attachements(config, snippet, backup_dir)
            except Exception as e:
                log.error(f"Failed to backup snippet {snippet.id}:\n{e}")


@beartype
def backup_wiki_attachements(
    config: DictConfig, obj: Group | Project, path_with_namespace: str, backup_dir: Path
) -> None:
    """Backup a GitLab wiki attachments.

    Args:
        config (DictConfig): Configuration settings.
        obj (Group | Project): The object to backup.
        path_with_namespace (str): The path with namespace of the project the object belongs to.
        backup_dir (Path): The directory to save the backup to.
    """

    download_dir = (Path(backup_dir / path_with_namespace) / ".wiki/attachements/").resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    file_urls = get_wiki_attachment_urls(obj, pattern=FILE_UPLOAD_PATTERN)
    if file_urls:
        log.info(f"\t\t\tDownloading attachments:\n{file_urls}")
        download_file_from_url(
            server=config.gitlab_server,
            username=config.gitlab_username,
            password=config.gitlab_password,
            file_urls=file_urls,
            download_dir=download_dir.as_posix(),
        )


@beartype
def backup_issue(
    config: DictConfig,
    obj: Issue | ProjectIssue | ProjectIssueNote,
    path_with_namespace: str,
    backup_dir: Path,
    is_note: bool = False,
    web_url: str = "",
) -> None:
    """Backup a GitLab issue and its attachments.

    Args:
        config (DictConfig): Configuration settings.
        issue (Issue): The issue object to backup.
        path_with_namespace (str): The path with namespace of the project the issue belongs to.
        backup_dir (Path): The directory to save the backup to.
    """

    if is_note:
        download_dir = (Path(backup_dir / path_with_namespace) / f"issues/{obj.issue_iid}/notes/{obj.id}/").resolve()
        json_path = (download_dir / f"{obj.id}.json").resolve()
        md_path = (download_dir / f"{obj.id}.md").resolve()
    else:
        download_dir = (Path(backup_dir / path_with_namespace) / f"issues/{obj.iid}/").resolve()
        json_path = (download_dir / f"{obj.iid}.json").resolve()
        md_path = (download_dir / f"{obj.iid}.md").resolve()

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(obj.attributes, f, sort_keys=True, indent=4)

    with open(md_path, "w", encoding="utf-8") as f:
        content = (
            obj.description.replace("/uploads/", "uploads/")
            if not is_note
            else obj.body.replace("/uploads/", "uploads/")
        )
        f.write(content)

    file_urls = get_issue_attachment_urls(obj, pattern=FILE_UPLOAD_PATTERN, is_note=is_note, web_url=web_url)
    if file_urls:
        log.info(f"\t\t\tDownloading attachments:\n{file_urls}")
        download_file_from_url(
            server=config.gitlab_server,
            username=config.gitlab_username,
            password=config.gitlab_password,
            file_urls=file_urls,
            download_dir=download_dir.as_posix(),
        )


@beartype
def backup_snippet_attachements(config: DictConfig, snippet: Snippet, backup_dir: Path) -> None:
    """Backup a GitLab issue and its attachments.

    Args:
        config (DictConfig): Configuration settings.
        snippet (Snippet): The snippet object to backup.
        path_with_namespace (str): The path with namespace of the project the snippet belongs to.
        backup_dir (Path): The directory to save the backup to.
    """

    download_dir = (Path(backup_dir) / f"snippets/{snippet.id}/").resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    snippet_path = download_dir / f"snippet_{snippet.id}.md"
    with open(snippet_path, "w", encoding="utf-8") as f:
        f.write(snippet.description.replace("/uploads/", "uploads/"))

    file_urls = find_matches(snippet.description, pattern=FILE_UPLOAD_PATTERN)
    if file_urls:
        log.info(f"\t\t\tDownloading attachments:\n{file_urls}")
        download_file_from_url(
            server=config.gitlab_server,
            username=config.gitlab_username,
            password=config.gitlab_password,
            file_urls=[f"{config.gitlab_server}/{url}" for url in file_urls],
            download_dir=download_dir.as_posix(),
        )
