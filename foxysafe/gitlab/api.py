from beartype import beartype
from loguru import logger as log
from rich.pretty import pretty_repr
from rich.progress import Progress, track

from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError, GitlabListError
from gitlab.v4.objects import Group, Issue, Project, ProjectIssue, Snippet


@beartype
def gitlab_login(gitlab_server: str, gitlab_personal_access_token: str) -> Gitlab:
    """Login to GitLab instance.

    Args:
        gitlab_server (str): URL of GitLab instance.
        gitlab_personal_access_token (str): Personal access token for GitLab instance.

    Returns:
        Gitlab: GitLab api instance with logged in server connection.
    """

    api = Gitlab(url=gitlab_server, private_token=gitlab_personal_access_token)
    api.auth()
    log.info(f"Logged in as: {api.user.username} [UID {api.user.id}]")

    return api


@beartype
def get_gitlab_items(
    api: Gitlab,
    gitlab_group_ids: list[int] | None,
    gitlab_project_ids: list[int] | None,
    include_personal_projects: bool = False,
    include_wikis: bool = False,
    include_issues: bool = False,
    include_snippets: bool = False,
) -> tuple[
    dict[int, Group],
    dict[int, Project],
    dict[int, Group | Project],
    dict[int, Issue | ProjectIssue],
    dict[int, Snippet],
]:
    """Get GitLab group and projects as backup items.

    Args:
        api (Gitlab): Logged in GitLab api instance.
        gitlab_group_ids (list[int]): List of GitLab group ids.
        gitlab_project_ids (list[int]): List of GitLab project ids.
        include_personal_projects (bool, optional): Include personal projects in backup. Defaults to False.

    Returns:
        dict[int, Group]: Gitlab groups dictionary.
        dict[int, Project]: Gitlab projects dictionary.
    """

    gitlab_groups = dict()
    gitlab_projects = dict()
    gitlab_wikis = dict()
    if gitlab_group_ids:
        with Progress() as pbar:
            task_1 = pbar.add_task("Searching specified groups...", total=len(gitlab_group_ids))
            for gid in gitlab_group_ids:
                group = api.groups.get(gid)

                if group:
                    gitlab_groups, gitlab_projects = _recurse_group(api, group, gitlab_groups, gitlab_projects, pbar)

                pbar.update(task_1, advance=1)

    if gitlab_project_ids:
        for pid in track(gitlab_project_ids, description="Searching specified projects..."):
            try:
                project = api.projects.get(pid)
            except GitlabGetError:
                log.warning(f"Failed to get project for PID {pid}")

            if project:
                log.info(f"Found project: {project.name} [PID {project.id}]")
                gitlab_projects[project.id] = project
                gitlab_projects.update({project.id: project})

    if include_personal_projects:
        personal_projects = api.users.get(api.user.id).projects.list(all=True)
        for project in track(personal_projects, description="Searching personal projects..."):
            log.info(f"Found user project: {project.name} [PID {project.id}]")
            gitlab_projects.update({project.id: project})

    if include_wikis:
        for group in track(gitlab_groups.values(), description="Searching group wikis..."):
            try:
                if hasattr(group, "wikis") and (pages := group.wikis.list(all=True)):
                    log.info(f"Found wiki with {len(pages)} pages for group {group.name} [GID {group.id}]")
                    gitlab_wikis.update({f"G{group.id}": group})
            except GitlabListError:
                log.warning(f"Failed to get wiki for group {group.name} [GID {group.id}]")

        for project in track(gitlab_projects.values(), description="Searching project wikis..."):
            try:
                if hasattr(project, "wikis") and (pages := project.wikis.list(all=True)):
                    log.info(f"Found wiki with {len(pages)} pages for project {project.name} [PID {project.id}]")
                    gitlab_wikis.update({f"P{project.id}": project})
            except GitlabListError:
                log.warning(f"Failed to get wiki for project {project.name} [GID {project.id}]")

    gitlab_issues = dict()
    if include_issues:
        for pid in track(gitlab_projects.keys(), description="Searching issues..."):
            issues = api.projects.get(pid).issues.list(all=True)
            for issue in issues:
                log.info(f"Found issue: {issue.title} [IID {issue.iid}]")
                gitlab_issues.update({f"{pid}/{issue.iid}": issue})

    gitlab_snippets = dict()
    if include_snippets:
        snippets = api.snippets.list(all=True)
        for snippet in track(snippets, description="Searching snippets..."):
            log.info(f"Found snippet: {snippet.title} [SID {snippet.id}]")
            gitlab_snippets.update({snippet.id: snippet})

    log.debug(f"GitLab groups:\n{pretty_repr(gitlab_groups)}")
    log.debug(f"GitLab projects:\n{pretty_repr(gitlab_projects)}")
    log.debug(f"GitLab issues:\n{pretty_repr(gitlab_issues)}")
    log.debug(f"GitLab snippets:\n{pretty_repr(gitlab_snippets)}")

    return gitlab_groups, gitlab_projects, gitlab_wikis, gitlab_issues, gitlab_snippets


@beartype
def _recurse_group(
    api: Gitlab, group: Group, groups: dict[str, Group], projects: dict[str, Project], pbar: Progress
) -> tuple[dict[str, Group], dict[str, Project]]:
    """Recursively get GitLab subgroups and projects from a group

    Args:
        api (Gitlab): Logged in GitLab api instance.
        groups (list[int]): Gitlab groups dictionary.
        projects (list[int]): Gitlab projects dictionary.
        pbar (Progerss): Rich progress bar instance.

    Returns:
        dict[int, Group]: Gitlab groups dictionary.
        dict[int, Project]: Gitlab projects dictionary.
    """

    log.info(f"Found group: {group.name} [GID {group.id}]")
    groups.update({group.id: group})

    subgroups = group.subgroups.list(all=True)
    if subgroups:
        log.debug(f"Found {len(subgroups)} subgroups in group {group.name} [GID {group.id}]")
        task_11 = pbar.add_task("\tIterating subgroups...", total=len(subgroups))
        for subgroup in subgroups:
            subgroup = api.groups.get(subgroup.id)
            groups, projects = _recurse_group(api, subgroup, groups, projects, pbar)

            pbar.update(task_11, advance=1)

        pbar.remove_task(task_11)
    else:
        log.debug("Max group depth reached.")

    group_projects = group.projects.list(all=True)
    if group_projects:
        log.debug(f"Found {len(group_projects)} in {group.name} [GID {group.id}]")
        task_12 = pbar.add_task("\tIterating group projects...", total=len(group_projects))
        for project in group_projects:
            log.info("Found group project:" f"{project.name} [PID {project.id}] in group {group.name} [GID {group.id}]")
            projects.update({project.id: project})

            pbar.update(task_id=task_12, advance=1)

        pbar.remove_task(task_12)

    return groups, projects
