"""
Changelog 생성 관련 기능 (git-cliff 통합)
"""

import sys
from pathlib import Path

import click

from .utils import run_command


def check_git_cliff_installed() -> bool:
    """git-cliff가 설치되어 있는지 확인합니다."""
    try:
        # check=True로 호출하여 실패 시 예외 발생 유도
        run_command(["git-cliff", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def install_git_cliff() -> None:
    """git-cliff를 설치합니다."""
    click.echo("[INSTALL] git-cliff 설치 중...")
    
    try:
        # uv를 사용하여 git-cliff 설치 확인 (실제 설치는 uvx 실행 시 자동 수행될 수 있음)
        run_command(["uvx", "git-cliff", "--version"], capture_output=True, check=True)
        click.echo("[OK] git-cliff가 설치되었습니다.")
    except Exception as e:
        click.echo(f"[ERROR] git-cliff 설치 중 오류: {e}", err=True)
        sys.exit(1)


def generate_changelog(tag: str = None, output_file: str = "CHANGELOG.md") -> None:
    """git-cliff를 사용하여 changelog를 생성합니다."""
    
    # git-cliff 설치 확인
    if not check_git_cliff_installed():
        click.echo("[WARNING] git-cliff가 설치되어 있지 않습니다. 설치를 시도합니다...")
        install_git_cliff()
    
    click.echo(f"[CHANGELOG] Changelog 생성 중... (출력: {output_file})")
    
    # git-cliff 명령어 구성 (uvx를 사용)
    cmd = ["uvx", "git-cliff", "--output", output_file]
    
    if tag:
        cmd.extend(["--tag", tag])
    
    try:
        run_command(cmd, capture_output=True, check=True)
        click.echo(f"[OK] Changelog가 {output_file}에 생성되었습니다.")
        
        # 생성된 파일 내용 미리보기
        if Path(output_file).exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    click.echo("\n[PREVIEW] 생성된 Changelog 미리보기:")
                    click.echo("─" * 50)
                    # 처음 20줄만 표시
                    lines = content.split('\n')[:20]
                    for line in lines:
                        click.echo(line)
                    if len(content.split('\n')) > 20:
                        click.echo("... (더 많은 내용이 있습니다)")
                    click.echo("─" * 50)
                else:
                    click.echo("[WARNING] 생성된 changelog가 비어있습니다.")
            
    except Exception as e:
        click.echo(f"[ERROR] Changelog 생성 중 오류: {e}", err=True)
        sys.exit(1)


def get_changelog_content(output_file: str = "CHANGELOG.md") -> str:
    """생성된 changelog 내용을 반환합니다."""
    changelog_path = Path(output_file)
    
    if not changelog_path.exists():
        return ""
    
    try:
        with open(changelog_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        click.echo(f"[ERROR] Changelog 읽기 오류: {e}", err=True)
        return ""
