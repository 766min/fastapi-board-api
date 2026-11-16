from fastapi import FastAPI

from wiring.auth import wire_auth_dependencies
from wiring.board import wire_board_dependencies
from wiring.user import wire_user_dependencies


def wire_dependencies(app: FastAPI) -> None:
    """presentation 의 자리표시자를 실제 구현으로 바꿔 끼운다 (도메인별로 나눠서 관리)"""
    wire_user_dependencies(app)
    wire_auth_dependencies(app)
    wire_board_dependencies(app)
