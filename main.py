import aiohttp
import logging
from typing import Optional, Dict, List, Union # Added Union for clarity
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("netcourse", "作者名", "网课任务查询插件", "1.0.1") # Minor version bump for the change
class NetCoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "http://hanlin.icu/api.php?act=chadan"
        self.quote_url = "https://api.qqsuu.cn/api/dm-mgjuzi"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def fetch_netcourse(self, username: str) -> Optional[Dict[str, Union[int, str, List[Dict]]]]: # Adjusted type hint
        """获取网课任务数据"""
        try:
            data = {"username": username}
            # !!! 使用你插件中原有的请求头 !!!
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Compatible; Bot/2.0)"
            }
            logger.debug(f"NetCourse: 请求参数：{data}")
            logger.debug(f"NetCourse: 请求头: {headers}")


            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(self.api_url, data=data, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"NetCourse: API请求失败 HTTP {resp.status}. Response: {await resp.text()}")
                        # Return a dict indicating error, useful for _format_message
                        return {"error": True, "message": f"API请求失败 (HTTP {resp.status})", "http_status": resp.status, "code": resp.status}

                    try:
                        result = await resp.json()
                        logger.debug(f"NetCourse: API原始响应:\n{result}")
                        return result
                    except aiohttp.ContentTypeError: # Handle cases where response is not JSON
                        logger.error(f"NetCourse: API响应不是有效的JSON. Status: {resp.status}. Response: {await resp.text()}")
                        return {"error": True, "message": "API返回非JSON格式数据", "http_status": resp.status, "code": resp.status}


        except aiohttp.ClientError as e:
            logger.error(f"NetCourse: 网络请求异常: {str(e)}")
            return {"error": True, "message": f"网络请求异常: {type(e).__name__}", "code": -1} # Added code for consistency
        except Exception as e:
            logger.error(f"NetCourse: 未知异常: {str(e)}", exc_info=True)
            return {"error": True, "message": f"发生未知错误: {type(e).__name__}", "code": -2} # Added code for consistency

    async def fetch_quote(self) -> str:
        """获取励志名言"""
        fallback_quote = "🌟 今天也要加油哦，未来的你会感谢现在努力的自己！" # Moved fallback to a variable
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session: # Shorter timeout for quotes
                async with session.get(self.quote_url) as resp:
                    if resp.status != 200:
                        return fallback_quote

                    result = await resp.json()
                    if result.get("code") == 200 and isinstance(result.get("data"), dict): # Check if data is a dict
                        content = result["data"].get("content", "坚持不懈的努力，才有精彩的明天！")
                        author = result["data"].get("author", "佚名")
                        return f"🌟 『{content}』 —— {author}"
                    return fallback_quote

        except Exception as e:
            logger.error(f"NetCourse: 获取名言失败: {str(e)}")
            return fallback_quote

    def _format_message(self, data: Dict[str, Union[int, str, List[Dict]]], quote: str) -> str: # Adjusted type hint
        """生成格式化消息"""
        # Handle potential errors passed from fetch_netcourse
        if data.get("error"):
            return f"🙁 糟糕，查询出错了: {data.get('message', '未知API错误')}"
        
        if data.get("code") != 1: # Check the API's own success code
            api_msg = data.get("message", "API返回了错误或非预期的数据结构")
            return f"🙁 查询失败: {api_msg} (API Code: {data.get('code')})"

        tasks = data.get("data", [])
        if not isinstance(tasks, list) or not tasks: # Ensure tasks is a list and not empty
            return "📭 没有找到该用户的任何网课任务记录！"

        task_count = len(tasks)
        task_details = f"🎉 查询到该用户共有 {task_count} 条网课任务记录：\n"
        task_details += "═"*20 + "\n" # Separator

        for i, task in enumerate(tasks, start=1):
            # Extracting existing and new data fields with defaults
            name = task.get("name", "未知用户")
            school = task.get("school", "未知学校") # 新增：学校
            ptname = task.get("ptname", "未知项目")
            kcname = task.get("kcname", "未知课程名") # 新增：课程名
            status = task.get("status", "状态未知")
            progress = task.get("process", "0.0%")
            addtime = task.get("addtime", "未知时间")
            
            course_start_time = task.get("courseStartTime") or "未提供" # 新增
            course_end_time = task.get("courseEndTime") or "未提供"     # 新增
            exam_start_time = task.get("examStartTime") or "未提供"       # 新增
            exam_end_time = task.get("examEndTime") or "未提供"         # 新增
            
            remarks_raw = task.get("remarks", "无备注信息")
            formatted_remarks = "无"
            if remarks_raw and remarks_raw != "无备注信息":
                # Simple split, you can format this further if needed (e.g., bullet points)
                remarks_list = [f"    • {r.strip()}" for r in remarks_raw.split('|')]
                formatted_remarks = "\n" + "\n".join(remarks_list)


            # Determine status emoji
            status_emoji = "✅" if status == "已完成" else \
                           "🔄" if "进行中" in status or "学习中" in status else \
                           "⏳" if "待处理" in status or "排队中" in status else \
                           "❓"
            
            # Simple text progress bar (optional, can be removed if too much)
            try:
                progress_val = float(progress.replace('%',''))
                bar_len = 10
                filled_len = int(bar_len * progress_val // 100)
                progress_bar_text = '🟩' * filled_len + '⬜' * (bar_len - filled_len)
                progress_display = f"{progress_bar_text} {progress}"
            except ValueError:
                progress_display = progress


            task_details += (
                f"\n📘 **任务 {i} / {task_count}**\n"
                f"👤 学生姓名：{name}\n"
                f"🏫 所属学校：{school}\n"
                f"📚 项目平台：{ptname}\n"
                f"📖 课程名称：{kcname}\n"
                f"🚦 当前状态：{status_emoji} {status}\n"
                f"📈 完成进度：{progress_display}\n"
                f"📅 添加时间：{addtime}\n"
                f"⏳ 课程起止：{course_start_time} 至 {course_end_time}\n"
                f"✍️ 考试起止：{exam_start_time} 至 {exam_end_time}\n"
                f"📝 备注信息：{formatted_remarks}\n"
            )
            if i < task_count: # Add separator between tasks
                task_details += "-----------------------\n"

        task_details += f"\n{quote}\n"
        task_details += "\n🌈 再难的任务也要坚持完成，聂半仙网课小助手和你一起努力！💪"
        return task_details

    @filter.command("网课查询", "查网课") # Added an alias "查网课" for convenience
    async def netcourse_query(self, event: AstrMessageEvent):
        '''查询网课任务，格式：/网课查询 [手机号/学号]'''
        try:
            args = event.message_str.split()
            if len(args) < 2:
                yield CommandResult().error("😅 请输入手机号或学号进行查询，例如：\n/网课查询 1234567890")
                return

            query = ''.join(args[1:]) # Allow for potential spaces if a username could have them (though unlikely for digits)
            if not query.strip().isdigit(): # Basic validation
                yield CommandResult().error("📵 学号/手机号通常是数字哦，请检查您的输入！")
                return

            yield CommandResult().message("📡 正在查询该用户的所有网课任务数据，请稍候...✨")

            data = await self.fetch_netcourse(query)
            # _format_message will now handle the error display based on the structure of 'data'
            
            quote = await self.fetch_quote()
            formatted_message = self._format_message(data, quote)

            # Check if the formatted message indicates an error (starts with specific emojis)
            # to decide if it should be sent as an error or success message
            if formatted_message.startswith("🙁") or formatted_message.startswith("📭"):
                yield CommandResult().error(formatted_message)
            else:
                yield CommandResult().message(formatted_message)


        except Exception as e:
            logger.error(f"NetCourse: 处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 网课查询服务暂时不可用，请稍后再试或联系管理员。")
