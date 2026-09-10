# 2026-09-07  eval_lisp.py
import sys
import threading
from astrbot.api import logger
from . import lispy

class TimeoutException(Exception):
    """自定义超时异常"""
    pass

def eval_lisp(code: str, timeout_seconds: float = 5) -> object | None:
    logger.info(f"尝试执行 Lisp 代码：\n{code}\n")
    # 获取当前执行该 Lisp 任务的线程 ID
    target_thread = threading.current_thread()

    # 触发超时的内部标记
    interrupted = False

    def trigger_timeout():
        nonlocal interrupted
        interrupted = True

        # 追踪函数
        def time_out_hook(frame, event, arg):
            if interrupted:
                raise TimeoutException("Lisp code execution timed out!")
            return time_out_hook

        # 强制抛出异常
        sys.settrace(time_out_hook)

    # 后台定时器线程
    timer = threading.Timer(timeout_seconds, trigger_timeout)
    timer.start()

    try:
        res = lispy.Interpreter().run(code)
        logger.info(f"Lisp 代码已完成运行。运行结果：\n{res}")
        return res
    except TimeoutException:
        logger.warning(f"Lisp 代码已运行超时，强制中断成功。")
        return "运行超时"
    except Exception as e:
        logger.error(f"Lisp 解释器内部执行出错: {e}")
        return f"执行失败: {e}"
    finally:
        timer.cancel()
        sys.settrace(None)
