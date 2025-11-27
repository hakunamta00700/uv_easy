"""
빌드 및 정리 관련 기능
"""

from pathlib import Path
import shutil

import click

from .versioning import (
    increment_build_number, 
    write_version_with_build, 
    read_version, 
    write_version, 
    write_version_file
)
from .utils import run_command


def clean_build_artifacts() -> None:
    """빌드 잔여물을 정리합니다."""
    click.echo("[CLEAN] 빌드 잔여물 정리 중...")
    
    artifacts_to_remove = [
        "dist",
        "build", 
        "*.egg-info"
    ]
    
    for artifact in artifacts_to_remove:
        if artifact in ["dist", "build"]:
            # 디렉토리 삭제
            artifact_path = Path(artifact)
            if artifact_path.exists():
                shutil.rmtree(artifact_path)
                click.echo(f"  [OK] {artifact}/ 디렉토리 삭제됨")
        else:
            # 패턴 매칭으로 파일/디렉토리 삭제
            for file_path in Path(".").glob(artifact):
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                    click.echo(f"  [OK] {file_path.name}/ 디렉토리 삭제됨")
                elif file_path.is_file():
                    file_path.unlink()
                    click.echo(f"  [OK] {file_path.name} 삭제됨")


def build_package(increment_build: bool = True, version_file: str = None) -> None:
    """
    패키지를 빌드합니다.
    """
    click.echo("[BUILD] 패키지를 빌드합니다...")
    
    if increment_build:
        # 빌드번호 증가 및 버전 업데이트
        new_build_number = increment_build_number()
        click.echo(f"[BUILD] 빌드번호 증가: {new_build_number}")
        write_version_with_build()
    else:
        # 순수 버전만 사용
        current_version = read_version()
        write_version(current_version)
        click.echo(f"[BUILD] 빌드번호 없이 빌드합니다. 버전: {current_version}")
    
    # 버전 파일 업데이트
    if version_file:
        write_version_file(version_file)
    
    # uvx build 실행 (출력 스트리밍)
    try:
        run_command(
            ["uvx", "--from", "build", "pyproject-build"],
            capture_output=False,
            check=True
        )
        click.echo("[OK] 빌드가 완료되었습니다.")
        
    except Exception:
        click.echo("[ERROR] 빌드 실패", err=True)
        raise


def install_package() -> None:
    """빌드된 패키지를 현재 환경에 설치합니다."""
    click.echo("[INSTALL] 패키지를 설치합니다...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        click.echo("[ERROR] dist 디렉토리를 찾을 수 없습니다.", err=True)
        return
    
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        click.echo("[ERROR] wheel 파일을 찾을 수 없습니다.", err=True)
        return
    
    # 가장 최근 wheel 파일 사용
    latest_wheel = max(wheel_files, key=lambda x: x.stat().st_mtime)
    
    # uv로 설치
    try:
        run_command(
            f"uv pip install {latest_wheel}",
            capture_output=False,
            check=True
        )
        click.echo("[OK] 설치가 완료되었습니다.")
    except Exception:
        click.echo("[ERROR] 설치 실패", err=True)
        raise
