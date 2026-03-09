import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

REPO_URL = "https://github.com/quzhi1/ChineseHistoricalSource.git"


def download_data(raw_dir: str) -> Path:
    """Download the ChineseHistoricalSource JSON data via sparse git clone."""
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)

    repo_path = raw_path / "ChineseHistoricalSource"
    json_dir = repo_path / "json"

    if json_dir.exists() and any(json_dir.glob("*.json")):
        console.print(f"[green]数据已存在: {json_dir}[/green]")
        return json_dir

    console.print("[yellow]正在下载二十四史数据...[/yellow]")

    if repo_path.exists():
        import shutil
        shutil.rmtree(repo_path)

    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO_URL],
        cwd=str(raw_path),
        check=True,
    )
    subprocess.run(
        ["git", "sparse-checkout", "set", "json"],
        cwd=str(repo_path),
        check=True,
    )

    console.print(f"[green]下载完成: {json_dir}[/green]")
    return json_dir
