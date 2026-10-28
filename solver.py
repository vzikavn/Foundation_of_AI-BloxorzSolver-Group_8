# solver.py
import time
import tracemalloc
from typing import List, Dict, Any
from state import GameState, Action
from board import Board, TileType
import heapq
from collections import deque


# Chuỗi bước đi mẫu cho 3 màn chơi mặc định để kiểm thử hệ thống Animation/Replay trên GUI
DEMO_SOLUTIONS: Dict[str, List[str]] = {
    "Level 1 - Classic Basics": [
        Action.RIGHT, Action.DOWN, Action.RIGHT, Action.RIGHT,
        Action.DOWN, Action.DOWN, Action.RIGHT
    ],
    "Level 2 - Fragile & Switches": [
        Action.RIGHT, Action.RIGHT, Action.RIGHT, Action.RIGHT,
        Action.DOWN, Action.DOWN
    ],
    "Level 3 - Split & Merge Master": [
        Action.RIGHT, Action.RIGHT, Action.RIGHT, Action.DOWN,
        Action.DOWN, Action.SPACE, Action.RIGHT, Action.UP,
        Action.DOWN, Action.RIGHT, Action.UP, Action.RIGHT,
        Action.DOWN, Action.RIGHT
    ]
}


def _get_demo_moves_if_at_start(board: Board, initial_state: GameState) -> List[str]:
    """Trả về chuỗi bước đi mẫu nếu khối đang ở vị trí xuất phát của 3 màn mẫu."""
    if initial_state == board.get_initial_state():
        return list(DEMO_SOLUTIONS.get(board.name, []))
    return []


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

    visited = {initial_state}
    queue = deque([(initial_state, [])])  

    while queue:
        state, path = queue.popleft()
        expanded_nodes += 1

        if board.is_goal(state):
            solution_actions = path
            break

        for action, next_state in board.get_valid_moves(state):
            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, path + [action]))
    solution_actions = _get_demo_moves_if_at_start(board, initial_state)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "BFS (Demo Stub)",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions)
    }


def solve_dfs(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán Depth-First Search (DFS) / Iterative Deepening Search (IDS).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    visited = set()
    stack = [(initial_state, [])]          

    while stack:
        state, path = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        expanded_nodes += 1

        if board.is_goal(state):
            solution_actions = path
            break

        for action, next_state in board.get_valid_moves(state):
            if next_state not in visited:
                stack.append((next_state, path + [action]))
    solution_actions = _get_demo_moves_if_at_start(board, initial_state)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "DFS (Demo Stub)",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions)
    }

def get_step_cost(board: Board, action: Action, next_state: GameState) -> float:
    '''
    Tile - Cost
    NORMAL/BRIDGE: 1
    FRAGILE: 2.5
    SWITCH: 0.5

    *Switch control after spliting: 0.2
    '''
    if action == Action.SPACE:
        return 0.2

    next_cell = next_state.get_occupied_cells()

    is_fragile = any(board.get_tile(r, c) == TileType.FRAGILE for r, c in next_cell)
    if is_fragile:
        return 2.5

    is_switch = any(board.get_tile(r, c) in (
            TileType.SOFT_SWITCH,
            TileType.HEAVY_SWITCH,
            TileType.SPLIT_SWITCH
        )
        for r, c in next_cell)
    if is_switch:
        return 0.5

    return 1.0 # The rest

def solve_ucs(board: Board, initial_state: GameState) -> Dict[str, Any]:
    """
    Hàm khung cho thuật toán Uniform-Cost Search (UCS).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    solution_actions: List[str] = []

    # =========================================================================
    start = board.get_initial_state()
    pq = [(0.0, 0, start, [])] # (cost, tiebreaker, state, path)
    visited = {} # {state: best_cost}
    tiebreaker = 0

    while pq:
        current_cost, tb, current_state, path = heapq.heappop(pq)

        if current_cost > visited.get(current_state, float('inf')): # pruning outdated costs
            continue
        
        expanded_nodes += 1

        if board.is_goal(current_state):
            solution_actions = path
            break

        visited[current_state] = current_cost

        for action, next_state in board.get_valid_moves(current_state):
            step_cost = get_step_cost(board, action = action, next_state = next_state)
            new_cost = step_cost + current_cost

            if next_state not in visited or visited[next_state] > new_cost:
                visited[next_state] = new_cost
                tiebreaker += 1
                heapq.heappush(pq, (new_cost, tiebreaker, next_state, path + [action]))   

    # =========================================================================
    # solution_actions = _get_demo_moves_if_at_start(board, initial_state)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "UCS (Demo Stub)",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions)
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
    solution_actions = _get_demo_moves_if_at_start(board, initial_state)

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "A* (Demo Stub)",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions)
    }
