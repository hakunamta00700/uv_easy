"""
빌드 및 정리 관련 기능
"""

import os
import subprocess
from pathlib import Path

import click

from .versioning import run_command


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


def build_package() -> None:
    """패키지를 빌드합니다."""
    click.echo("[BUILD] 패키지를 빌드합니다...")
    
    # Windows에서 UTF-8 환경 변수 설정
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    env['PYTHONUTF8'] = '1'
    
    try:
        # Windows에서 인코딩 문제를 피하기 위해 바이트로 받은 후 디코딩
        result = subprocess.run(
            ["uvx", "--from", "build", "pyproject-build"],
            check=True,
            capture_output=True,
            text=False,  # 바이트로 받기
            env=env
        )
        
        # 안전하게 디코딩
        if result.stdout:
            try:
                stdout_text = result.stdout.decode('utf-8', errors='replace')
                click.echo(stdout_text)
            except Exception:
                # UTF-8 디코딩 실패 시 시스템 기본 인코딩 시도
                import sys
                encoding = sys.getdefaultencoding()
                stdout_text = result.stdout.decode(encoding, errors='replace')
                click.echo(stdout_text)
        
        if result.stderr:
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
                if stderr_text.strip():
                    click.echo(stderr_text, err=True)
            except Exception:
                import sys
                encoding = sys.getdefaultencoding()
                stderr_text = result.stderr.decode(encoding, errors='replace')
                if stderr_text.strip():
                    click.echo(stderr_text, err=True)
        
        click.echo("[OK] 빌드가 완료되었습니다.")
        
    except subprocess.CalledProcessError as e:
        click.echo("[ERROR] 빌드 실패:", err=True)
        if e.stdout:
            try:
                stdout_text = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else e.stdout
                click.echo(f"stdout: {stdout_text}", err=True)
            except Exception:
                import sys
                encoding = sys.getdefaultencoding()
                stdout_text = e.stdout.decode(encoding, errors='replace') if isinstance(e.stdout, bytes) else e.stdout
                click.echo(f"stdout: {stdout_text}", err=True)
        if e.stderr:
            try:
                stderr_text = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                click.echo(f"stderr: {stderr_text}", err=True)
            except Exception:
                import sys
                encoding = sys.getdefaultencoding()
                stderr_text = e.stderr.decode(encoding, errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                click.echo(f"stderr: {stderr_text}", err=True)
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
    
    if install_result.stdout:
        click.echo(install_result.stdout)
    
    click.echo("[OK] 설치가 완료되었습니다.")
