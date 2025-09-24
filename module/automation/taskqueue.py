from collections import deque
from typing import Any, Deque, Iterable, Optional, Iterator

class TaskQueue:
    """
    任务队列
    - push_back(x) / push(x)      末尾压入
    - push_front(x)               头部压入
    - pop_front() / pop()         弹出并返回队首
    - pop_back()                  弹出并返回队尾
    - front()                     查看队首元素 (空则抛 IndexError)
    - back()                      查看队尾元素 (空则抛 IndexError)
    - size() / len(q)             当前数量
    - empty()                     是否为空
    - clear()                     清空
    - try_pop_front()             若空返回 None
    - full()                      是否达到 maxsize (仅当设定 maxsize>0)
    - to_list()                   转为列表
    """

    def __init__(self, maxsize: int = 0, data: Iterable[Any] | None= None):
        """
        初始化队列
        Args:
            maxsize: 最大容量 (0 则不限制)
            data: 初始数据 (可选)
        """
        self._dq: Deque[Any] = deque()
        self._maxsize = maxsize
        if data:
            for x in data:
                self.push_back(x)

    # --- push / emplace 类 ---
    def push_back(self, item: Any) -> None:
        """
        末尾压入元素
        Args:
            item: 任何对象
            Raises: OverflowError: 当队列满时
        """
        if self._maxsize and len(self._dq) >= self._maxsize:
            raise OverflowError("queue full")
        self._dq.append(item)

    def push_front(self, item: Any) -> None:
        """
        头部压入元素
        Args:
            item: 任何对象
            Raises: OverflowError: 当队列满时
        """
        if self._maxsize and len(self._dq) >= self._maxsize:
            raise OverflowError("queue full")
        self._dq.appendleft(item)

    def push(self, item: Any) -> None:
        """
        元素压入队列
        Args:
            item: 任何对象
        """
        self.push_back(item)

    # --- pop / access ---
    def pop_front(self) -> Any:
        """
        弹出并返回队首元素
        Raises: IndexError: 当队列空时
        """
        if not self._dq:
            raise IndexError("pop_front from empty queue")
        return self._dq.popleft()

    def pop_back(self) -> Any:
        """
        弹出并返回队尾元素
        Raises: IndexError: 当队列空时
        """
        if not self._dq:
            raise IndexError("pop_back from empty queue")
        return self._dq.pop()

    def pop(self) -> Any:
        """
        队列弹出元素
        Raises: IndexError: 当队列空时
        """
        return self.pop_front()

    def try_pop_front(self) -> Any:
        """
        弹出并返回队首元素
        """
        return self._dq.popleft() if self._dq else None

    def front(self) -> Any:
        """
        查看队首元素
        Raises: IndexError: 当队列空时
        """
        if not self._dq:
            raise IndexError("front from empty queue")
        return self._dq[0]

    def back(self) -> Any:
        """
        查看队尾元素
        Raises: IndexError: 当队列空时
        """
        if not self._dq:
            raise IndexError("back from empty queue")
        return self._dq[-1]

    # --- capacity / status ---
    def size(self) -> int:
        """
        获取当前队列大小
        """
        return len(self._dq)

    def empty(self) -> bool:
        """
        判断队列是否为空
        """
        return not self._dq

    def full(self) -> bool:
        """
        判断队列是否已满
        """
        return bool(self._maxsize and len(self._dq) >= self._maxsize)

    def clear(self) -> None:
        """
        清空队列
        """
        self._dq.clear()

    def __len__(self) -> int:
        return len(self._dq)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._dq)

    def to_list(self) -> list:
        return list(self._dq)
