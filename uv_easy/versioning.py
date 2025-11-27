"""
버전 관리 및 Git 태그 관련 기능
"""

from typing import Tuple

import click

from .utils import get_pyproject_path, load_toml, save_toml, run_command

try:
    from importlib.metadata import version as get_installed_version, PackageNotFoundError
except ImportError:
    # Python < 3.8
    from importlib_metadata import version as get_installed_version, PackageNotFoundError


def get_version() -> str:
    """
    패키지 버전을 반환합니다.
    
    패키징 후에는 importlib.metadata에서 읽고,
    개발 중에는 pyproject.toml에서 읽습니다.
    """
    # 1. 설치된 패키지에서 버전 읽기 시도
    try:
        return get_installed_version("uv-easy")
    except PackageNotFoundError:
        pass
    
    # 2. 실패하면 pyproject.toml에서 읽기 시도
    try:
        data = load_toml()
        return data.get('project', {}).get('version', '0.0.0')
    except Exception:
        pass
    
    return "0.0.0"


def read_version() -> str:
    """pyproject.toml에서 현재 버전을 읽어옵니다. (빌드번호 제외)"""
    try:
        data = load_toml()
        version = data['project']['version']
        # 빌드번호가 포함된 경우 제거 (예: "0.2.9+1" -> "0.2.9")
        if '+' in version:
            version = version.split('+')[0]
        return version
    except Exception as e:
        click.echo(f"[ERROR] 버전을 읽는 중 오류가 발생했습니다: {e}", err=True)
        return "0.0.0" 


def write_version(version: str) -> None:
    """pyproject.toml에 새로운 버전을 씁니다."""
    data = load_toml()
    data['project']['version'] = version
    save_toml(data)
    click.echo(f"[OK] 버전이 {version}으로 업데이트되었습니다.")


def parse_version(version: str) -> Tuple[int, int, int]:
    """버전 문자열을 파싱하여 (major, minor, patch) 튜플을 반환합니다."""
    try:
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError("버전 형식이 올바르지 않습니다. (예: 1.2.3)")
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as e:
        click.echo(f"[ERROR] 버전 파싱 오류: {e}", err=True)
        raise click.Abort()


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
        raise click.Abort()
    
    return f"{major}.{minor}.{patch}"


def get_current_branch() -> str:
    """현재 Git 브랜치 이름을 반환합니다."""
    try:
        # 1. git branch --show-current
        result = run_command("git branch --show-current", capture_output=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # 2. fallback: git symbolic-ref refs/remotes/origin/HEAD
        result = run_command("git symbolic-ref refs/remotes/origin/HEAD", capture_output=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip().split('/')[-1]
            
    except Exception:
        pass
        
    return "main"


def create_git_tag(version: str, push: bool = True) -> None:
    """Git 태그를 생성하고 푸시합니다."""
    tag_name = f"v{version}"
    
    click.echo(f"[TAG] Git 태그 '{tag_name}' 생성 중...")
    run_command(f"git tag {tag_name}")
    
    if push:
        current_branch = get_current_branch()
        click.echo(f"[PUSH] Git 태그 '{tag_name}' 푸시 중... (브랜치: {current_branch})")
        run_command(f"git push origin {current_branch} --tags")
        click.echo(f"[OK] Git 태그 '{tag_name}' 생성 및 푸시 완료")
    else:
        click.echo(f"[OK] Git 태그 '{tag_name}' 생성 완료 (푸시 안함)")


def analyze_git_commits() -> str:
    """Git 커밋 로그를 분석하여 버전 증가 타입을 결정합니다."""
    try:
        result = run_command("git log --oneline -10", capture_output=True, check=False)
        
        if result.returncode != 0:
            click.echo("[WARNING] Git 로그를 읽을 수 없습니다. patch 버전으로 증가합니다.")
            return "patch"
        
        commits = result.stdout.strip().split('\n')
        
        has_breaking_change = False
        has_feat = False
        has_fix = False
        
        for commit in commits:
            commit_msg = commit.lower()
            if 'breaking change' in commit_msg or '!' in commit_msg:
                has_breaking_change = True
            elif 'feat' in commit_msg: 
                has_feat = True
            elif 'fix' in commit_msg:
                has_fix = True
        
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


def read_build_number() -> int:
    """pyproject.toml에서 현재 빌드번호를 읽어옵니다."""
    try:
        data = load_toml()
        return data.get('tool', {}).get('uv_easy', {}).get('build_number', 0)
    except Exception as e:
        click.echo(f"[WARNING] 빌드번호 읽기 실패: {e}. 0으로 간주합니다.")
        return 0


def write_build_number(build_number: int) -> None:
    """pyproject.toml에 새로운 빌드번호를 씁니다."""
    data = load_toml()
    
    if 'tool' not in data:
        data['tool'] = {}
    if 'uv_easy' not in data['tool']:
        data['tool']['uv_easy'] = {}
    
    data['tool']['uv_easy']['build_number'] = build_number
    save_toml(data)
    click.echo(f"[OK] 빌드번호 업데이트: {build_number}")


def increment_build_number() -> int:
    """빌드번호를 증가시키고 반환합니다."""
    current_build = read_build_number()
    new_build = current_build + 1
    write_build_number(new_build)
    return new_build


def init_build_number() -> None:
    """빌드번호를 0으로 초기화합니다."""
    write_build_number(0)
    click.echo("[OK] 빌드번호 초기화 완료")


def get_version_with_build() -> str:
    """현재 버전과 빌드번호를 조합하여 반환합니다."""
    version = read_version()
    build_number = read_build_number()
    
    if build_number > 0:
        return f"{version}+{build_number}"
    return version


def write_version_with_build() -> None:
    """버전을 빌드번호와 함께 업데이트합니다."""
    version_with_build = get_version_with_build()
    data = load_toml()
    data['project']['version'] = version_with_build
    save_toml(data)
    click.echo(f"[OK] 버전이 {version_with_build}으로 업데이트되었습니다.")


def get_final_version() -> str:
    """pyproject.toml에서 최종 버전을 읽어옵니다."""
    try:
        data = load_toml()
        return data['project']['version']
    except Exception:
        return "0.0.0"


def write_version_file(version_file: str) -> None:
    """
    지정된 파일에 __version__ 변수를 씁니다.
    """
    final_version = get_final_version()
    # Path 처리 개선
    version_file_path = get_pyproject_path().parent / version_file
    
    try:
        if version_file_path.exists():
            with open(version_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            version_line_found = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('__version__'):
                    lines[i] = f'__version__ = "{final_version}"'
                    version_line_found = True
                    break
            
            if version_line_found:
                new_content = '\n'.join(lines)
            else:
                new_content = content 
                if not content.endswith('\n'):
                     new_content += '\n'
                new_content += f'__version__ = "{final_version}"\n'
        else:
            new_content = f'__version__ = "{final_version}"\n'
        
        version_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(version_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        click.echo(f"[OK] 버전 파일 업데이트: {version_file} (버전: {final_version})")
    except Exception as e:
        click.echo(f"[ERROR] 버전 파일 쓰기 실패: {e}", err=True)
        raise click.Abort()
