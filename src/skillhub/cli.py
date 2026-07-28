"""Skillhub CLI — Typer-based interface."""

from __future__ import annotations

import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

# Force UTF-8 output on Windows to avoid GBK encoding errors
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from . import registry
from .config import disable_platform, enable_platform, load_config
from .installer import import_from_directory, init_skillhub
from .models import SkillTier
from .paths import get_skillhub_dir, get_skills_dir
from .syncer import SyncReport, doctor as run_doctor, get_enabled_platforms, sync_skills


app = typer.Typer(
    name="skillhub",
    help="Local centralized skill registry — install once, use everywhere",
    add_completion=False,
    no_args_is_help=True,
)
console = Console(highlight=False, emoji=False, legacy_windows=False)


# ---- init ----

@app.command()
def init() -> None:
    """初始化 skillhub：检测平台，导入现有技能。"""
    console.print("[bold]Initializing skillhub...[/bold]")
    console.print(f"Data directory: {get_skillhub_dir()}")

    result = init_skillhub()

    console.print()
    console.print(f"[green]✓ Detected {len(result['platforms_detected'])} platforms:[/green]")
    for p in result["platforms_detected"]:
        console.print(f"    • {p}")

    if result["import_counts"]:
        console.print()
        console.print("[green]✓ Imported skills:[/green]")
        for source, count in result["import_counts"].items():
            console.print(f"    • {source}: {count} skills")

    console.print()
    console.print("[dim]Run 'skillhub sync' to sync skills to all enabled platforms.[/dim]")


# ---- list ----

@app.command("list")
def list_skills(
    tier: Optional[str] = typer.Option(None, "--tier", help="Filter by tier: skill / server"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Show status for a specific platform"),
) -> None:
    """列出所有已安装的技能。"""
    skills = registry.list_skills(tier=tier)

    if not skills:
        console.print("[yellow]No skills found. Run 'skillhub init' first.[/yellow]")
        return

    table = Table(title=f"Installed Skills ({len(skills)})", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Tier", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Description", style="dim")

    for skill in skills:
        table.add_row(
            skill["id"],
            skill["name"],
            skill["tier"],
            skill["version"],
            (skill.get("description") or "")[:60],
        )

    console.print(table)

    # Show platform sync status
    if platform:
        sync_states = registry.list_sync_state(platform=platform)
        if sync_states:
            table2 = Table(title=f"Sync Status — {platform}")
            table2.add_column("Skill", style="cyan")
            table2.add_column("Status")
            table2.add_column("Last Synced")
            for s in sync_states:
                status_style = {
                    "synced": "green",
                    "skipped": "yellow",
                    "failed": "red",
                    "removed": "dim",
                }.get(s["status"], "white")
                table2.add_row(
                    s["skill_id"],
                    f"[{status_style}]{s['status']}[/{status_style}]",
                    s.get("synced_at", "—") and "N/A",
                )
            console.print(table2)


# ---- sync ----

@app.command()
def sync(
    platform: Optional[str] = typer.Option(None, "--platform", help="只同步指定平台"),
    skill: Optional[str] = typer.Option(None, "--skill", help="只同步指定技能"),
    dry_run: bool = typer.Option(False, "--dry-run", help="试运行，不做实际修改"),
) -> None:
    """把技能同步到所有启用的平台。"""
    console.print("[bold]Syncing skills...[/bold]")
    if dry_run:
        console.print("[yellow](dry run — no changes will be made)[/yellow]")

    report = sync_skills(platform_filter=platform, skill_filter=skill, dry_run=dry_run)

    table = Table(title="Sync Results", show_header=True)
    table.add_column("Skill", style="cyan")
    table.add_column("Platform")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    for r in report.results:
        style = {
            "synced": "green",
            "skipped": "yellow",
            "failed": "red",
            "removed": "dim",
        }.get(r.status, "white")
        table.add_row(
            r.skill_id,
            r.platform,
            f"[{style}]{r.status}[/{style}]",
            r.detail or r.error,
        )

    console.print(table)
    console.print()
    console.print(
        f"[green]Synced: {report.synced}[/green]  "
        f"[yellow]Skipped: {report.skipped}[/yellow]  "
        f"[red]Failed: {report.failed}[/red]"
    )


# ---- doctor ----

@app.command()
def doctor(
    fix: bool = typer.Option(False, "--fix", help="尝试自动修复问题"),
) -> None:
    """检查技能同步状态，修复断裂的链接。"""
    console.print("[bold]Running doctor check...[/bold]")

    issues = run_doctor(fix=fix)

    if not issues:
        console.print("[green]✓ All good — no issues found.[/green]")
        return

    table = Table(title=f"Issues Found ({len(issues)})")
    table.add_column("Skill", style="cyan")
    table.add_column("Platform")
    table.add_column("Type", style="yellow")
    table.add_column("Detail", style="dim")
    if fix:
        table.add_column("Fixed", style="green")

    for issue in issues:
        row = [
            issue["skill"],
            issue["platform"],
            issue["type"],
            issue["detail"],
        ]
        if fix:
            fixed = issue.get("fixed", False)
            row.append("[green]✓[/green]" if fixed else "[red]✗[/red]")
        table.add_row(*row)

    console.print(table)

    if not fix and issues:
        console.print()
        console.print("[dim]Run 'skillhub doctor --fix' to attempt auto-repair.[/dim]")


# ---- platforms ----

@app.command()
def platforms() -> None:
    """列出检测到的平台及其状态。"""
    all_platforms = registry.list_platforms()

    if not all_platforms:
        console.print("[yellow]No platforms detected. Run 'skillhub init' first.[/yellow]")
        return

    config = load_config()

    table = Table(title="Platforms")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Detected", justify="center")
    table.add_column("Enabled", justify="center")
    table.add_column("Skill Dir", style="dim")

    for p in all_platforms:
        is_enabled = p["name"] in config.enabled_platforms
        table.add_row(
            p["name"],
            p["display_name"],
            "[green]✓[/green]" if p["detected"] else "[red]✗[/red]",
            "[green]✓[/green]" if is_enabled else "[yellow]✗[/yellow]",
            p.get("skill_dir") or "—",
        )

    console.print(table)
    console.print()
    console.print("[dim]Use 'skillhub platforms enable <name>' or 'disable <name>' to toggle.[/dim]")


@app.command("platforms enable")
def platforms_enable(name: str) -> None:
    """启用一个平台适配器。"""
    enable_platform(name)
    registry.set_platform_enabled(name, True)
    console.print(f"[green]✓ Enabled platform: {name}[/green]")


@app.command("platforms disable")
def platforms_disable(name: str) -> None:
    """禁用一个平台适配器。"""
    disable_platform(name)
    registry.set_platform_enabled(name, False)
    console.print(f"[yellow]○ Disabled platform: {name}[/yellow]")


# ---- import ----

@app.command()
def import_cmd(
    from_platform: str = typer.Option(..., "--from", help="从哪个平台导入：workbuddy / claudecode / codex"),
    overwrite: bool = typer.Option(False, "--overwrite", help="覆盖已存在的技能"),
) -> None:
    """从指定平台批量导入技能。"""
    from .adapters import get_adapter

    adapter = get_adapter(from_platform)
    if not adapter:
        console.print(f"[red]✗ Unknown platform: {from_platform}[/red]")
        raise typer.Exit(1)

    if not adapter.is_installed():
        console.print(f"[red]✗ Platform not installed: {from_platform}[/red]")
        raise typer.Exit(1)

    if not adapter.skill_dir:
        console.print(f"[red]✗ Platform has no skill directory: {from_platform}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Importing from {from_platform}...[/bold]")
    imported = import_from_directory(from_platform, adapter.skill_dir, overwrite=overwrite)

    if imported:
        console.print(f"[green]✓ Imported {len(imported)} skills:[/green]")
        for s in imported[:10]:
            console.print(f"    • {s}")
        if len(imported) > 10:
            console.print(f"    ... and {len(imported) - 10} more")
    else:
        console.print("[yellow]No new skills imported (all already exist).[/yellow]")

    console.print()
    console.print("[dim]Run 'skillhub sync' to push newly imported skills to all platforms.[/dim]")


# Alias "import" since it's a reserved word in Python
app.command("import")(import_cmd)


if __name__ == "__main__":
    app()
