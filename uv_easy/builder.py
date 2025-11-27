"""
빌드 및 정리 관련 기능
"""

import os
import subprocess
from pathlib import Path

import click

from .versioning import run_command, increment_build_number, write_version_with_build, read_version, write_version, write_version_file


def clean_build_artifacts() -> None:
    """빌드 잔여물을 정리합니다."""
    click.echo("[CLEAN] 빌드 잔여물 정리 중...")
    
    artifacts_to_remove = [
        "dist",
        "build", 
        "*.egg-info"
    ]
    
    for artifact in artifacts_to_remove:
        if artifact == "dist" or artifact == "build":
            # 디렉토리 삭제
            artifact_path = Path(artifact)
            if artifact_path.exists():
                import shutil
                shutil.rmtree(artifact_path)
                click.echo(f"  [OK] {artifact}/ 디렉토리 삭제됨")
        else:
            # 패턴 매칭으로 파일 삭제
            for file_path in Path(".").glob(artifact):
                if file_path.is_file():
                    file_path.unlink()
                    click.echo(f"  [OK] {file_path.name} 삭제됨")


def build_package(increment_build: bool = True, version_file: str = None) -> None:
    """
    패키지를 빌드합니다.
    
    Args:
        increment_build: True이면 빌드번호를 증가시키고 버전에 추가, False이면 빌드번호 없이 빌드
        version_file: 버전 파일 경로 (지정되면 빌드 전에 __version__ 변수를 업데이트)
    """
    click.echo("[BUILD] 패키지를 빌드합니다...")
    
    if increment_build:
        # 빌드 전에 빌드번호 증가 및 버전 업데이트
        new_build_number = increment_build_number()
        click.echo(f"[BUILD] 빌드번호 증가: {new_build_number}")
        write_version_with_build()
    else:
        # 빌드번호 없이 순수 버전만 사용
        current_version = read_version()
        write_version(current_version)
        click.echo(f"[BUILD] 빌드번호 없이 빌드합니다. 버전: {current_version}")
    
    # 빌드 전에 버전 파일 업데이트 (옵션이 있는 경우)
    if version_file:
        write_version_file(version_file)
    
    # Windows에서 UTF-8 환경 변수 설정
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    env['PYTHONUTF8'] = '1'
    
    try:
        proc = subprocess.Popen(
            ["uvx", "--from", "build", "pyproject-build"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        stdout = proc.stdout.read()  # str
        stderr = proc.stderr.read()  # str
        proc.wait()
        
        if stdout:
            click.echo(stdout)
        
        if stderr and stderr.strip():
            click.echo(stderr, err=True)
        
        if proc.returncode != 0:
            click.echo("[ERROR] 빌드 실패:", err=True)
            if stdout:
                click.echo(f"stdout: {stdout}", err=True)
            if stderr:
                click.echo(f"stderr: {stderr}", err=True)
            raise subprocess.CalledProcessError(proc.returncode, ["uvx", "--from", "build", "pyproject-build"])
        
        click.echo("[OK] 빌드가 완료되었습니다.")
        
    except subprocess.CalledProcessError as e:
        click.echo("[ERROR] 빌드 실패:", err=True)
        raise


def install_package() -> None:
    """빌드된 패키지를 현재 환경에 설치합니다."""
    click.echo("[INSTALL] 패키지를 설치합니다...")
    
    # dist 디렉토리에서 wheel 파일 찾기
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
    
    # uv를 사용하여 설치
    install_result = run_command(f"uv pip install {latest_wheel}")
    
    if hasattr(install_result, 'stdout_text') and install_result.stdout_text:
        click.echo(install_result.stdout_text)
    
    click.echo("[OK] 설치가 완료되었습니다.")
