"""
프로젝트 초기화 및 생성 관련 기능
"""

import sys
from pathlib import Path
from typing import Literal

import click
import toml

from . import __version__ as uv_easy_version


def get_pyproject_path() -> Path:
    """pyproject.toml 파일의 경로를 반환합니다."""
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"
    
    if not pyproject_path.exists():
        click.echo("❌ pyproject.toml 파일을 찾을 수 없습니다.", err=True)
        click.echo("   현재 디렉토리에서 pyproject.toml이 있는 프로젝트 루트로 이동하세요.", err=True)
        sys.exit(1)
    
    return pyproject_path


def create_project_structure(
    package_name: str,
    use_cli: Literal["click", "argparse"] = "click"
) -> None:
    """
    새로운 CLI 프로젝트 구조를 생성합니다.
    
    Args:
        package_name: 생성할 패키지 이름
        use_cli: 사용할 CLI 라이브러리 ('click' 또는 'argparse')
    """
    pyproject_path = get_pyproject_path()
    project_root = pyproject_path.parent
    package_dir = project_root / package_name
    
    # 패키지 디렉토리가 이미 존재하는지 확인
    if package_dir.exists():
        click.echo(f"❌ '{package_name}' 디렉토리가 이미 존재합니다.", err=True)
        sys.exit(1)
    
    # 패키지 디렉토리 생성
    package_dir.mkdir(parents=True, exist_ok=False)
    click.echo(f"✅ '{package_name}' 디렉토리를 생성했습니다.")
    
    # __init__.py 생성
    init_content = f'''"""
{package_name} 패키지
"""

__version__ = "0.1.0"
'''
    init_file = package_dir / "__init__.py"
    init_file.write_text(init_content, encoding='utf-8')
    click.echo(f"✅ '{package_name}/__init__.py' 파일을 생성했습니다.")
    
    # __main__.py 생성
    main_content = f'''"""
{package_name} 패키지의 메인 진입점
"""

import sys
from pathlib import Path

# 패키지 루트를 sys.path에 추가하여 절대 import 가능하게 함
_package_dir = Path(__file__).parent
_project_root = _package_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 절대 import 사용
from {package_name}.cli import main

if __name__ == "__main__":
    main()
'''
    main_file = package_dir / "__main__.py"
    main_file.write_text(main_content, encoding='utf-8')
    click.echo(f"✅ '{package_name}/__main__.py' 파일을 생성했습니다.")
    
    # cli.py 생성
    if use_cli == "click":
        cli_content = f'''"""
{package_name} CLI 진입점
"""

import sys
from pathlib import Path

import click
import toml


def get_version():
    """pyproject.toml에서 버전을 읽어옵니다."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
                return data.get('project', {{}}).get('version', '0.1.0')
    except Exception:
        pass
    
    # pyproject.toml을 읽을 수 없으면 __init__.py에서 가져오기
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "0.1.0"


@click.group()
def cli():
    """{package_name} CLI"""
    pass


@cli.command()
def version():
    """버전을 표시합니다."""
    version_str = get_version()
    click.echo(version_str)


def main():
    """CLI 진입점"""
    cli()
'''
    else:  # argparse
        cli_content = f'''"""
{package_name} CLI 진입점
"""

import argparse
import sys
from pathlib import Path

import toml


def get_version():
    """pyproject.toml에서 버전을 읽어옵니다."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
                return data.get('project', {{}}).get('version', '0.1.0')
    except Exception:
        pass
    
    # pyproject.toml을 읽을 수 없으면 __init__.py에서 가져오기
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "0.1.0"


def create_parser():
    """argparse 파서를 생성합니다."""
    parser = argparse.ArgumentParser(
        description="{package_name} CLI",
        prog="{package_name}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")
    
    # version 명령어
    version_parser = subparsers.add_parser("version", help="버전을 표시합니다")
    
    return parser


def main():
    """CLI 진입점"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == "version":
        print(get_version())
    elif args.command is None:
        parser.print_help()
        sys.exit(1)
'''
    
    cli_file = package_dir / "cli.py"
    cli_file.write_text(cli_content, encoding='utf-8')
    click.echo(f"✅ '{package_name}/cli.py' 파일을 생성했습니다 ({use_cli} 사용).")
    
    # pyproject.toml 설정 통합 업데이트
    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        # [project] 섹션 설정
        if 'project' not in data:
            data['project'] = {}
        
        # 프로젝트 이름이 없으면 설정
        if 'name' not in data['project']:
            data['project']['name'] = package_name.replace('_', '-')
        
        # 버전이 없으면 추가
        if 'version' not in data['project']:
            data['project']['version'] = "0.1.0"
        
        # requires-python이 없으면 추가
        if 'requires-python' not in data['project']:
            data['project']['requires-python'] = ">=3.9"
        
        # dependencies가 없으면 빈 리스트로 초기화
        if 'dependencies' not in data['project']:
            data['project']['dependencies'] = []
        
        # CLI 라이브러리 의존성 추가 (중복 방지)
        if use_cli == "click":
            click_dep = "click>=8.0.0"
            if not any(dep.startswith("click") for dep in data['project']['dependencies']):
                data['project']['dependencies'].append(click_dep)
        
        # toml 의존성 추가 (버전 확인용)
        toml_dep = "toml>=0.10.0"
        if not any(dep.startswith("toml") for dep in data['project']['dependencies']):
            data['project']['dependencies'].append(toml_dep)
        
        # [project.scripts] 섹션 설정
        if 'scripts' not in data['project']:
            data['project']['scripts'] = {}
        
        # 스크립트 추가 (패키지명으로)
        script_entry = f"{package_name}.cli:main"
        data['project']['scripts'][package_name] = script_entry
        
        # [project.urls] 섹션 설정 (없으면 기본값 추가)
        if 'urls' not in data['project']:
            project_name_for_url = data['project'].get('name', package_name.replace('_', '-'))
            data['project']['urls'] = {
                "Homepage": f"https://github.com/hakunamta00700/{project_name_for_url}",
                "Repository": f"https://github.com/hakunamta00700/{project_name_for_url}",
                "Issues": f"https://github.com/hakunamta00700/{project_name_for_url}/issues",
                "Documentation": f"https://github.com/hakunamta00700/{project_name_for_url}#readme"
            }
        
        # [build-system] 섹션 설정
        if 'build-system' not in data:
            data['build-system'] = {
                'requires': ['hatchling'],
                'build-backend': 'hatchling.build'
            }
        
        # [tool.uv] 섹션 설정
        if 'tool' not in data:
            data['tool'] = {}
        if 'uv' not in data['tool']:
            data['tool']['uv'] = {}
        data['tool']['uv']['package'] = True
        
        # [tool.hatch.build.targets.wheel] 섹션 설정
        if 'hatch' not in data['tool']:
            data['tool']['hatch'] = {}
        if 'build' not in data['tool']['hatch']:
            data['tool']['hatch']['build'] = {}
        if 'targets' not in data['tool']['hatch']['build']:
            data['tool']['hatch']['build']['targets'] = {}
        if 'wheel' not in data['tool']['hatch']['build']['targets']:
            data['tool']['hatch']['build']['targets']['wheel'] = {}
        
        # wheel 패키지 설정
        data['tool']['hatch']['build']['targets']['wheel']['packages'] = [package_name]
        
        # 파일에 쓰기
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)
        
        click.echo(f"✅ pyproject.toml을 완전히 설정했습니다:")
        click.echo(f"   - [project] 섹션 (name, version, dependencies)")
        click.echo(f"   - [project.scripts] 섹션 ({package_name} 스크립트 추가)")
        click.echo(f"   - [project.urls] 섹션")
        click.echo(f"   - [build-system] 섹션")
        click.echo(f"   - [tool.uv] 섹션 (package = true)")
        click.echo(f"   - [tool.hatch.build.targets.wheel] 섹션")
        click.echo(f"   실행: {package_name} version")
        
    except Exception as e:
        click.echo(f"❌ pyproject.toml 업데이트 중 오류가 발생했습니다: {e}", err=True)
        sys.exit(1)
    
    # 다음 단계 안내
    click.echo("\n💡 다음 단계:")
    click.echo("   1. uv sync로 의존성 설치")
    click.echo(f"   2. {package_name} version으로 테스트")
    click.echo("   3. uv_easy version up으로 버전 관리 시작")
    
    click.echo(f"\n✅ '{package_name}' 프로젝트 구조 생성이 완료되었습니다!")

