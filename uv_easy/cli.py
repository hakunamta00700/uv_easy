"""
uv_easy CLI 진입점
"""

from pathlib import Path

import click

from .versioning import (
    read_version,
    write_version,
    increment_version,
    create_git_tag,
    analyze_git_commits,
    get_version,
    init_build_number,
)
from .builder import clean_build_artifacts, build_package, install_package
from .publisher import publish_to_pypi
from .changelog import generate_changelog
from .workflow import generate_github_workflow, generate_git_cliff_config
from .project import create_project_structure, setup_pypi_urls


def version_callback(ctx, param, value):
    """버전 출력 콜백 함수"""
    if not value:
        return
    click.echo(f"uv_easy {get_version()}")
    ctx.exit()


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="버전 정보를 출력합니다",
    expose_value=False,
    is_eager=True,
    callback=version_callback,
)
@click.pass_context
def cli(ctx):
    """uv를 더 쉽게 사용하기 위한 도구"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group()
def version():
    """버전 관리 명령어"""
    pass


@version.command()
@click.option("--major", is_flag=True, help="메이저 버전을 증가시킵니다")
@click.option("--minor", is_flag=True, help="마이너 버전을 증가시킵니다")
@click.option("--patch", is_flag=True, help="패치 버전을 증가시킵니다")
@click.option(
    "--auto", is_flag=True, help="Git 커밋을 분석하여 자동으로 버전을 증가시킵니다"
)
@click.option("--no-push", is_flag=True, help="Git 태그를 푸시하지 않습니다")
def up(major: bool, minor: bool, patch: bool, auto: bool, no_push: bool):
    """pyproject.toml의 버전을 증가시키고 Git 태그를 생성합니다."""
    # 옵션 확인
    manual_options = [major, minor, patch]
    if auto and sum(manual_options) > 0:
        click.echo(
            "❌ --auto 옵션과 다른 버전 옵션을 함께 사용할 수 없습니다.", err=True
        )
        return

    if not auto and sum(manual_options) != 1:
        click.echo(
            "❌ --major, --minor, --patch 중 하나만 선택하거나 --auto를 사용하세요.",
            err=True,
        )
        return

    # 현재 버전 읽기
    current_version = read_version()
    click.echo(f"현재 버전: {current_version}")

    # 증가 타입 결정
    if auto:
        increment_type = analyze_git_commits()
        click.echo(f"커밋 분석 결과: {increment_type} 버전 증가")
    elif major:
        increment_type = "major"
    elif minor:
        increment_type = "minor"
    else:  # patch
        increment_type = "patch"

    # 새 버전 계산
    new_version = increment_version(current_version, increment_type)

    # 버전 업데이트
    write_version(new_version)

    # Git 태그 생성 및 푸시
    create_git_tag(new_version, push=not no_push)


@version.command()
def show():
    """현재 버전을 표시합니다."""
    current_version = read_version()
    click.echo(f"현재 버전: {current_version}")


@cli.command()
@click.option("--tag", help="특정 태그에 대한 changelog 생성")
@click.option("--output", "-o", default="CHANGELOG.md", help="출력 파일명")
def changelog(tag: str, output: str):
    """git-cliff를 사용하여 changelog를 생성합니다."""
    generate_changelog(tag=tag, output_file=output)


@cli.command()
@click.option("--no-version-up", is_flag=True, help="버전을 증가시키지 않습니다")
@click.option("--major", is_flag=True, help="메이저 버전을 증가시킵니다")
@click.option("--minor", is_flag=True, help="마이너 버전을 증가시킵니다")
@click.option("--patch", is_flag=True, help="패치 버전을 증가시킵니다")
@click.option(
    "--auto", is_flag=True, help="Git 커밋을 분석하여 자동으로 버전을 증가시킵니다"
)
@click.option("--install", is_flag=True, help="빌드 후 현재 환경에 설치합니다")
@click.option("--no-push", is_flag=True, help="Git 태그를 푸시하지 않습니다")
@click.option("--no-build-number", is_flag=True, help="빌드번호를 증가시키지 않고 빌드합니다. 버전에 빌드번호가 포함되지 않습니다.")
@click.option("--version-file", type=str, default=None, help="빌드 전에 __version__ 변수를 쓸 파일 경로를 지정합니다.")
def build(
    no_version_up: bool,
    major: bool,
    minor: bool,
    patch: bool,
    auto: bool,
    install: bool,
    no_push: bool,
    no_build_number: bool,
    version_file: str,
):
    """패키지를 빌드합니다."""
    # 버전 증가 옵션 확인
    version_options = [major, minor, patch]
    if not no_version_up and not auto and sum(version_options) != 1:
        click.echo(
            "❌ --major, --minor, --patch 중 하나만 선택하거나 --auto를 사용하거나 --no-version-up을 사용하세요.",
            err=True,
        )
        return

    # 1. 빌드 정리
    clean_build_artifacts()

    # 2. 버전 증가 (옵션에 따라)
    if not no_version_up:
        current_version = read_version()
        click.echo(f"현재 버전: {current_version}")

        if auto:
            increment_type = analyze_git_commits()
            click.echo(f"커밋 분석 결과: {increment_type} 버전 증가")
        elif major:
            increment_type = "major"
        elif minor:
            increment_type = "minor"
        else:  # patch
            increment_type = "patch"

        new_version = increment_version(current_version, increment_type)
        write_version(new_version)

        # Git 태그 생성 및 푸시
        create_git_tag(new_version, push=not no_push)

    # 3. 빌드 실행
    # build_package 내부에서 version_file 처리 및 빌드번호 관리 수행
    build_package(increment_build=not no_build_number, version_file=version_file)

    # 4. 설치 (옵션에 따라)
    if install:
        install_package()


@cli.command()
@click.option("--test", is_flag=True, help="TestPyPI에 업로드합니다")
@click.option(
    "--json", "json_output", is_flag=True, help="JSON 형태로 결과를 출력합니다"
)
def publish(test: bool, json_output: bool):
    """dist 디렉토리의 패키지를 PyPI 또는 TestPyPI에 업로드합니다."""
    publish_to_pypi(test=test, json_output=json_output)


@cli.group()
def init():
    """초기화 명령어"""
    pass


@init.command()
@click.option("--test", is_flag=True, help="TestPyPI용 workflow 생성")
@click.option("--release", is_flag=True, help="GitHub Release 자동화 포함")
def workflow(test: bool, release: bool):
    """GitHub Actions workflow 파일을 생성합니다."""
    generate_github_workflow(test=test, release=release)


@init.command()
def cliff_config():
    """git-cliff 설정 파일을 생성합니다."""
    generate_git_cliff_config()


@cli.command()
def init_buildnumber():
    """빌드번호를 0으로 초기화합니다."""
    init_build_number()


@cli.command()
def ready_pypi():
    """pyproject.toml에 PyPI 배포를 위한 project.urls를 추가합니다."""
    setup_pypi_urls()


@cli.command()
@click.argument("package_name")
@click.option(
    "--use",
    type=click.Choice(["click", "argparse"], case_sensitive=False),
    default="click",
    help="사용할 CLI 라이브러리 (click 또는 argparse)",
)
def startproject(package_name: str, use: str):
    """
    새로운 CLI 프로젝트 구조를 생성합니다.
    """
    create_project_structure(package_name, use_cli=use.lower())


def main():
    """CLI 진입점"""
    cli()


if __name__ == "__main__":
    main()
