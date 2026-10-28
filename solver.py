# solver.py
import time
import tracemalloc
from typing import List, Dict, Any
from state import GameState
from board import Board


def solve_bfs(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán Breadth-First Search (BFS).
    Bạn chỉ cần viết thuật toán vào phần TODO bên dưới.

    Gợi ý sử dụng:
    - Kiểm tra đích: board.is_goal(state)
    - Sinh trạng thái kế tiếp: for action, next_state in board.get_valid_moves(state): ...
    - Tập visited: visited = {initial_state} (do GameState đã cài đặt chuẩn __hash__ và __eq__)
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    # =========================================================================
    # TODO: Cài đặt thuật toán BFS của bạn tại đây
    # =========================================================================

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "BFS",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions),
    }


def solve_dfs(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán Depth-First Search (DFS) / Iterative Deepening Search (IDS).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    # =========================================================================
    # TODO: Cài đặt thuật toán DFS / IDS của bạn tại đây
    # =========================================================================

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "DFS",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions),
    }


def solve_ucs(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán Uniform-Cost Search (UCS).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    # =========================================================================
    # TODO: Cài đặt thuật toán UCS của bạn tại đây
    # =========================================================================

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "UCS",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions),
    }


def solve_astar(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán A* Search.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    # =========================================================================
    # TODO: Cài đặt thuật toán A* và hàm Heuristic của bạn tại đây
    # =========================================================================

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "A*",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions),
    }
