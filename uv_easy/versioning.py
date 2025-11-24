"""
버전 관리 및 Git 태그 관련 기능
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
import toml

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Python < 3.8
    from importlib_metadata import version, PackageNotFoundError


def get_pyproject_path() -> Path:
    """pyproject.toml 파일의 경로를 반환합니다."""
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"
    
    if not pyproject_path.exists():
        click.echo("[ERROR] pyproject.toml 파일을 찾을 수 없습니다.", err=True)
        sys.exit(1)
    
    return pyproject_path


def get_version() -> str:
    """
    패키지 버전을 반환합니다.
    
    패키징 후에는 importlib.metadata에서 읽고,
    개발 중에는 pyproject.toml에서 읽습니다.
    """
    # 먼저 설치된 패키지에서 버전 읽기 시도
    try:
        return version("uv-easy")
    except PackageNotFoundError:
        pass
    
    # 실패하면 pyproject.toml에서 읽기 시도
    try:
        current_dir = Path.cwd()
        pyproject_path = current_dir / "pyproject.toml"
        
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
                return data['project']['version']
    except Exception:
        pass
    
    # 모든 방법이 실패하면 기본값 반환
    return "0.0.0"


def read_version() -> str:
    """pyproject.toml에서 현재 버전을 읽어옵니다."""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
            return data['project']['version']
    except Exception as e:
        click.echo(f"[ERROR] 버전을 읽는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)


def write_version(version: str) -> None:
    """pyproject.toml에 새로운 버전을 씁니다."""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        data['project']['version'] = version
        
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)
            
        click.echo(f"[OK] 버전이 {version}으로 업데이트되었습니다.")
    except Exception as e:
        click.echo(f"[ERROR] 버전을 쓰는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)


def parse_version(version: str) -> Tuple[int, int, int]:
    """버전 문자열을 파싱하여 (major, minor, patch) 튜플을 반환합니다."""
    try:
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError("버전 형식이 올바르지 않습니다. (예: 1.2.3)")
        
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as e:
        click.echo(f"[ERROR] 버전 파싱 오류: {e}", err=True)
        sys.exit(1)


def increment_version(version: str, increment_type: str) -> str:
    """버전을 증가시킵니다."""
    major, minor, patch = parse_version(version)
    
    if increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "patch":
        patch += 1
    else:
        click.echo(f"[ERROR] 잘못된 증가 타입: {increment_type}", err=True)
        sys.exit(1)
    
    return f"{major}.{minor}.{patch}"


def run_command(command: str, check: bool = True) -> subprocess.Popen:
    """명령어를 실행합니다."""
    try:
        proc = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            shell=False
        )
        stdout = proc.stdout.read()  # str
        stderr = proc.stderr.read()  # str
        proc.wait()
        
        if check and proc.returncode != 0:
            click.echo(f"[ERROR] 명령어 실행 실패: returncode={proc.returncode}", err=True)
            if stdout:
                click.echo(f"stdout: {stdout}", err=True)
            if stderr:
                click.echo(f"stderr: {stderr}", err=True)
            sys.exit(1)
        
        # CompletedProcess와 유사한 객체를 반환하기 위해 속성 설정
        result = proc
        result.stdout_text = stdout
        result.stderr_text = stderr
        return result
    except Exception as e:
        click.echo(f"[ERROR] 명령어 실행 실패: {e}", err=True)
        sys.exit(1)


def get_current_branch() -> str:
    """현재 Git 브랜치 이름을 반환합니다."""
    try:
        proc = subprocess.Popen(
            ["git", "branch", "--show-current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        output = proc.stdout.read()  # str
        proc.wait()
        
        if proc.returncode == 0 and output.strip():
            return output.strip()
        else:
            # fallback: 기본 브랜치 확인
            proc = subprocess.Popen(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            output = proc.stdout.read()  # str
            proc.wait()
            
            if proc.returncode == 0:
                # refs/remotes/origin/main -> main
                return output.strip().split('/')[-1]
            else:
                # 최종 fallback
                return "main"
                
    except Exception:
        return "main"


def create_git_tag(version: str, push: bool = True) -> None:
    """Git 태그를 생성하고 푸시합니다."""
    tag_name = f"v{version}"
    
    # Git 태그 생성
    click.echo(f"[TAG] Git 태그 '{tag_name}' 생성 중...")
    result = run_command(f"git tag {tag_name}")
    
    if push:
        # 현재 브랜치 확인
        current_branch = get_current_branch()
        click.echo(f"[PUSH] Git 태그 '{tag_name}' 푸시 중... (브랜치: {current_branch})")
        run_command(f"git push origin {current_branch} --tags")
        click.echo(f"[OK] Git 태그 '{tag_name}' 생성 및 푸시 완료")
    else:
        click.echo(f"[OK] Git 태그 '{tag_name}' 생성 완료 (푸시 안함)")


def analyze_git_commits() -> str:
    """Git 커밋 로그를 분석하여 버전 증가 타입을 결정합니다."""
    try:
        # 최근 커밋들 가져오기
        proc = subprocess.Popen(
            ["git", "log", "--oneline", "-10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        output = proc.stdout.read()  # str
        proc.wait()
        
        if proc.returncode != 0:
            click.echo("[WARNING] Git 로그를 읽을 수 없습니다. patch 버전으로 증가합니다.")
            return "patch"
        
        commits = output.strip().split('\n')
        
        # 커밋 메시지 분석
        has_breaking_change = False
        has_feat = False
        has_fix = False
        
        for commit in commits:
            commit_msg = commit.lower()
            if 'breaking change' in commit_msg or '!' in commit_msg:
                has_breaking_change = True
            elif commit_msg.startswith('feat'):
                has_feat = True
            elif commit_msg.startswith('fix'):
                has_fix = True
        
        # 버전 증가 타입 결정
        if has_breaking_change:
            return "major"
        elif has_feat:
            return "minor"
        elif has_fix:
            return "patch"
        else:
            return "patch"
            
    except Exception as e:
        click.echo(f"[WARNING] 커밋 분석 중 오류: {e}. patch 버전으로 증가합니다.")
        return "patch"
