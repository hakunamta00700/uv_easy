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
    """pyproject.toml에서 현재 버전을 읽어옵니다. (빌드번호 제외)"""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
            version = data['project']['version']
            # 빌드번호가 포함된 경우 제거 (예: "0.2.9+1" -> "0.2.9")
            if '+' in version:
                version = version.split('+')[0]
            return version
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


def read_build_number() -> int:
    """pyproject.toml에서 현재 빌드번호를 읽어옵니다."""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
            # [tool.uv_easy] 섹션에서 빌드번호 읽기
            if 'tool' in data and 'uv_easy' in data['tool']:
                return data['tool']['uv_easy'].get('build_number', 0)
            return 0
    except Exception as e:
        click.echo(f"[WARNING] 빌드번호를 읽는 중 오류가 발생했습니다: {e}. 기본값 0을 사용합니다.")
        return 0


def write_build_number(build_number: int) -> None:
    """pyproject.toml에 새로운 빌드번호를 씁니다."""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        # [tool.uv_easy] 섹션 생성 또는 업데이트
        if 'tool' not in data:
            data['tool'] = {}
        if 'uv_easy' not in data['tool']:
            data['tool']['uv_easy'] = {}
        
        data['tool']['uv_easy']['build_number'] = build_number
        
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)
            
        click.echo(f"[OK] 빌드번호가 {build_number}으로 업데이트되었습니다.")
    except Exception as e:
        click.echo(f"[ERROR] 빌드번호를 쓰는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)


def increment_build_number() -> int:
    """빌드번호를 증가시키고 반환합니다."""
    current_build = read_build_number()
    new_build = current_build + 1
    write_build_number(new_build)
    return new_build


def init_build_number() -> None:
    """빌드번호를 0으로 초기화합니다."""
    write_build_number(0)
    click.echo("[OK] 빌드번호가 0으로 초기화되었습니다.")


def get_version_with_build() -> str:
    """현재 버전과 빌드번호를 조합하여 반환합니다."""
    version = read_version()
    build_number = read_build_number()
    
    # 버전에서 이미 +빌드번호가 있는지 확인
    if '+' in version:
        # 기존 +빌드번호 제거
        version = version.split('+')[0]
    
    if build_number > 0:
        return f"{version}+{build_number}"
    return version


def write_version_with_build() -> None:
    """버전을 빌드번호와 함께 업데이트합니다."""
    version_with_build = get_version_with_build()
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        data['project']['version'] = version_with_build
        
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)
            
        click.echo(f"[OK] 버전이 {version_with_build}으로 업데이트되었습니다.")
    except Exception as e:
        click.echo(f"[ERROR] 버전을 쓰는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)


def get_final_version() -> str:
    """pyproject.toml에서 최종 버전을 읽어옵니다 (빌드번호 포함 여부와 관계없이)."""
    pyproject_path = get_pyproject_path()
    
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
            return data['project']['version']
    except Exception as e:
        click.echo(f"[ERROR] 버전을 읽는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)


def write_version_file(version_file: str) -> None:
    """
    지정된 파일에 __version__ 변수를 씁니다.
    
    Args:
        version_file: 버전을 쓸 파일 경로
    """
    final_version = get_final_version()
    version_file_path = Path(version_file)
    
    try:
        # 파일이 존재하는 경우 기존 내용 확인
        if version_file_path.exists():
            with open(version_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # __version__ 라인 찾기 및 교체
            lines = content.split('\n')
            version_line_found = False
            
            for i, line in enumerate(lines):
                # __version__ = 로 시작하는 라인 찾기
                if line.strip().startswith('__version__'):
                    lines[i] = f'__version__ = "{final_version}"'
                    version_line_found = True
                    break
            
            if version_line_found:
                # 기존 라인 교체
                new_content = '\n'.join(lines)
            else:
                # __version__ 라인이 없으면 파일 끝에 추가
                if content and not content.endswith('\n'):
                    new_content = content + '\n'
                else:
                    new_content = content
                new_content += f'__version__ = "{final_version}"\n'
        else:
            # 파일이 없으면 새로 생성
            new_content = f'__version__ = "{final_version}"\n'
        
        # 파일 쓰기
        version_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(version_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        click.echo(f"[OK] 버전 파일이 업데이트되었습니다: {version_file} (버전: {final_version})")
    except Exception as e:
        click.echo(f"[ERROR] 버전 파일을 쓰는 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)