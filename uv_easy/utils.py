"""
공통 유틸리티 함수
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import toml


def get_encoding_env() -> Dict[str, str]:
    """
    Windows 등에서 인코딩 문제를 방지하기 위한 환경 변수를 반환합니다.
    """
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    env['PYTHONUTF8'] = '1'
    return env


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    capture_output: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """
    명령어를 실행합니다.

    Args:
        command: 실행할 명령어 (문자열 또는 리스트)
        cwd: 실행 경로
        capture_output: 출력 캡처 여부 (True면 반환값의 stdout/stderr에 저장, False면 콘솔 출력)
        check: 실패 시 예외 발생 여부
        env: 추가 환경 변수

    Returns:
        CompletedProcess 객체 (stdout, stderr 포함)
    """
    # 기본 환경 변수에 인코딩 설정 병합
    run_env = get_encoding_env()
    if env:
        run_env.update(env)

    # 명령어 리스트 변환
    if isinstance(command, str):
        # 쉘이 아닌 경우 리스트로 분할
        cmd_list = command.split()
    else:
        cmd_list = command

    try:
        # 캡처 모드 설정
        stdout_target = subprocess.PIPE if capture_output else None
        stderr_target = subprocess.PIPE if capture_output else None

        # subprocess.run 사용
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            check=check,
            stdout=stdout_target,
            stderr=stderr_target,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=run_env
        )
        return result

    except subprocess.CalledProcessError as e:
        if capture_output:
            # 캡처된 에러 메시지 출력
            if e.stdout:
                click.echo(f"stdout: {e.stdout}", err=True)
            if e.stderr:
                click.echo(f"stderr: {e.stderr}", err=True)
        else:
            # 캡처하지 않은 경우 이미 콘솔에 출력되었을 것임
            pass
        
        click.echo(f"[ERROR] 명령어 실행 실패: {' '.join(cmd_list)} (Exit Code: {e.returncode})", err=True)
        # check=True인 경우 이미 예외가 발생했으나, 상위 호출자를 위해 다시 raise
        raise e
    except Exception as e:
        click.echo(f"[ERROR] 예기치 않은 오류 발생: {e}", err=True)
        sys.exit(1)


def get_pyproject_path() -> Path:
    """pyproject.toml 파일의 경로를 반환합니다."""
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"
    
    if not pyproject_path.exists():
        click.echo("❌ pyproject.toml 파일을 찾을 수 없습니다.", err=True)
        click.echo("   현재 디렉토리에서 pyproject.toml이 있는 프로젝트 루트로 이동하세요.", err=True)
        sys.exit(1)
    
    return pyproject_path


def load_toml(path: Optional[Path] = None) -> Dict[str, Any]:
    """TOML 파일을 읽어옵니다."""
    target_path = path or get_pyproject_path()
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except Exception as e:
        click.echo(f"[ERROR] TOML 파일 읽기 실패 ({target_path}): {e}", err=True)
        sys.exit(1)


def save_toml(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    """데이터를 TOML 파일로 저장합니다."""
    target_path = path or get_pyproject_path()
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            toml.dump(data, f)
    except Exception as e:
        click.echo(f"[ERROR] TOML 파일 쓰기 실패 ({target_path}): {e}", err=True)
        sys.exit(1)

