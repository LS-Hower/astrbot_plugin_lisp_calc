from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from eval_lisp import eval_lisp

@register("astrbot_plugin_lisp_calc", "LS_Hower", "语法形如 Lisp 的简单计算器", "0.0.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 发送 `/calc` 触发本指令
    @filter.command("calc")
    async def helloworld(self, event: AstrMessageEvent):
        """运行 Lisp 代码""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        #user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"运行结果：{eval_lisp(message_str)}") # 发送一条纯文本消息

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
