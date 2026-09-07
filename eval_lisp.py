# 2026-09-07  eval_lisp.py

from multiprocessing import Process, Queue

from astrbot.api import logger

import lispy

def eval_lisp(code: str, timeout_seconds: float = 5) -> object | None:
    def eval_lisp_internal(q: Queue, code: str) -> None:
        q.put(lispy.Interpreter().run(code))

    # 用于获取子进程返回值
    q = Queue()
    p = Process(target=eval_lisp_internal, args=(q, code))
    p.start()
    p.join(timeout=timeout_seconds)

    # 检查进程是否还在运行
    if p.is_alive():
        logger.info(f"Lisp 代码已运行超时，开始关闭子进程。代码：\n{code}\n")
        p.terminate()
        p.join()  # 清理进程资源
        logger.info(f"子进程已关闭")
        return None
    else:
        logger.info(f"Lisp 代码已完成运行。代码：\n{code}\n")
        res = q.get() if not q.empty() else None
        logger.info(f"运行结果：\n{res}")
        return res
