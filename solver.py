# solver.py
import time
import tracemalloc
from typing import List, Dict, Any
from state import GameState, Action
from board import Board, TileType
import heapq
from collections import deque


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

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "BFS",
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

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "DFS",
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
    *Each step after splitting takes x1.5 cost to encourage merging
    '''
    # return 1
    if action == Action.SPACE:
        return 0.2

    next_cell = next_state.get_occupied_cells()
    if not next_state.is_split():
    # if True:
        is_fragile = any(board.get_tile(r, c) == TileType.FRAGILE for r, c in next_cell)
        if is_fragile:
            return 2.5
    
    split_penalty = 1.5 if next_state.is_split() else 1
    is_switch = any(board.get_tile(r, c) in (
            TileType.SOFT_SWITCH,
            TileType.HEAVY_SWITCH,
            TileType.SPLIT_SWITCH
        )
        for r, c in next_cell)
    if is_switch:
        return 0.5 * split_penalty

    return 1.0 * split_penalty # The rest

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
    visited = {start: 0.0} # {state: best_cost}
    tiebreaker = 0

    while pq:
        current_cost, tb, current_state, path = heapq.heappop(pq)

        if current_cost > visited.get(current_state, float('inf')): # pruning outdated costs
            continue
        
        expanded_nodes += 1

        if board.is_goal(current_state):
            solution_actions = path
            break

        for action, next_state in board.get_valid_moves(current_state):
            step_cost = get_step_cost(board, action = action, next_state = next_state)
            new_cost = step_cost + current_cost

            if next_state not in visited or visited[next_state] > new_cost:
                visited[next_state] = new_cost
                tiebreaker += 1
                heapq.heappush(pq, (new_cost, tiebreaker, next_state, path + [action]))   

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
        "solution_length": len(solution_actions)
    }


def heuristic(state: GameState, goal: tuple[int, int]) -> float:
    """
    Hàm Heuristic tính khoảng cách Manhattan từ khối đến ô đích.
    Nếu khối đang nằm hoặc bị tách, lấy khoảng cách nhỏ nhất từ các phần của khối đến đích.
    """
    cells = state.get_occupied_cells()
    min_manhattan = min(abs(r - goal[0]) + abs(c - goal[1]) for r, c in cells)
    
    # Nhân với 0.25 để đảm bảo tính Admissible (h(n) <= h*(n)) 
    # vì bước đi nhỏ nhất có thể tốn 0.5 (công tắc) nhưng lại di chuyển được khoảng cách 2 ô.
    return min_manhattan * 0.25

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
    
    # Hàng đợi ưu tiên PQ lưu các tuple: (f_cost, tiebreaker, g_cost, state, path)
    # tiebreaker giúp tránh lỗi so sánh 2 GameState khi f_cost bằng nhau
    
    tiebreaker = 0
    start_h = heuristic(initial_state, board.goal)
    pq = [(start_h, tiebreaker, 0.0, initial_state, [])]
    
    # Từ điển visited lưu chi phí g(n) tốt nhất đã tìm thấy để đi đến state đó
    visited: Dict[GameState, float] = {initial_state: 0.0}

    while pq:
        current_f, _, current_g, current_state, path = heapq.heappop(pq)

        # Pruning (cắt tỉa): Nếu trạng thái này đã được duyệt với chi phí g rẻ hơn trước đó, bỏ qua
        if current_g > visited.get(current_state, float('inf')):
            continue

        expanded_nodes += 1

        # Nếu đạt trạng thái đích -> Dừng và ghi nhận kết quả
        if board.is_goal(current_state):
            solution_actions = path
            break

        # Khai triển các bước đi hợp lệ
        for action, next_state in board.get_valid_moves(current_state):
            # Tính g(n) mới bằng g_hiện_tại + cost của bước đi
            step_cost = get_step_cost(board, action=action, next_state=next_state)
            new_g = current_g + step_cost

            # Cập nhật nếu tìm được đường đi mới rẻ hơn hoặc chưa từng ghé thăm
            if next_state not in visited or new_g < visited[next_state]:
                visited[next_state] = new_g
                new_f = new_g + heuristic(next_state, board.goal)
                
                tiebreaker += 1
                heapq.heappush(pq, (new_f, tiebreaker, new_g, next_state, path + [action]))

    elapsed_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "algorithm": "A*",
        "actions": solution_actions,
        "time_sec": elapsed_time,
        "memory_kb": peak_mem / 1024.0,
        "expanded_nodes": expanded_nodes,
        "solution_length": len(solution_actions)
    }
