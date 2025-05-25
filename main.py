import aiohttp
import logging
from typing import Optional, Dict, List, Union # Added Union
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

# --- IMPORTANT: SENSITIVE COOKIE AND HEADERS ---
# This Cookie string is from your抓包数据. It IS SENSITIVE and WILL EXPIRE.
# For long-term use, you need a dynamic way to get these.
# Especially the 'admin_token' is critical.
# Keep this secure if you use it.
RAW_COOKIE_STRING = (
    'PHPSESSID=v830bhrlo3gb4a8et9mtkto91o; '
    'admin_token=7ad7dWBrIvBMdfa9s1NABx%2B7Z7pNJFSNX1vEUx5a9QsLHsWvTG8TFdcZ0KONEzH1DhixGJ4sikJhxXDDnYX0YsUl9aHSF5BN; '
    'cf_clearance=YUwRygU6IlCqdR5Ki1R.Lao7TQkFQHNUv9QOT5WEEOM-1748173018-1.2.1.1-GhTSlONld6YerTCvJ5WJ5xaBE776Z25xviBfG6_xz4WmEvDj_2.LvXQZEPuVTCEROkabnfvvA2zBhLRB6A9tNMmu887913vRc1FzNnqbw17KhQutvSmyLP5dKtRbGJSBrQt3gX9ROz0sNCaCsL9zqvSrJh_g1UgT5hdRgozaUOJC.eH0ey8gbXFu87Yv_5oXuvHPHtxDZH98gFhQq3WYAI8WmktrS98eb26TzKry1kGJoHQsEy.gSJFRHoXIOa0tqGSX0Mgyh6T8KWwA0v6mQM7Pur6KhjcXbp..haEhac.kKWoyVhmUK1eQW_qKop9sx.qn3OdTJ2j5_6Mi3I8XAvSzs6CKnWXn0kDNIT5Kr58'
)

DEFAULT_HEADERS = {
    'Host': 'hanlin.icu',
    'Connection': 'keep-alive',
    'sec-ch-ua-platform': '"Windows"',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'sec-ch-ua-mobile': '?0',
    'Origin': 'https://hanlin.icu',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://hanlin.icu/get',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cookie': RAW_COOKIE_STRING
}
# --- END OF SENSITIVE DATA ---

@register("netcourse", "聂半仙", "网课任务查询插件 (升级版)", "1.1.0") # Updated version and name
class NetCoursePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "https://hanlin.icu/api.php?act=chadan" # Using HTTPS
        self.quote_url = "https://api.qqsuu.cn/api/dm-mgjuzi"
        self.timeout = aiohttp.ClientTimeout(total=20) # Increased timeout slightly
        self.headers = DEFAULT_HEADERS # Use the defined headers

    async def fetch_netcourse(self, username: str) -> Optional[Dict[str, Union[int, str, List[Dict]]]]:
        """获取网课任务数据"""
        try:
            payload = {"username": username}
            logger.info(f"NetCourse: 发起请求到 {self.api_url} for user {username}")
            logger.debug(f"NetCourse: 请求参数: {payload}")
            # logger.debug(f"NetCourse: 请求头: {self.headers}") # Careful logging cookies

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Using self.headers which includes the vital Cookie
                async with session.post(self.api_url, data=payload, headers=self.headers) as resp:
                    if resp.status != 200:
                        logger.error(f"NetCourse: API请求失败 HTTP {resp.status}. Response: {await resp.text()}")
                        return {"error": True, "message": f"API请求失败 (HTTP {resp.status})", "http_status": resp.status}

                    try:
                        result = await resp.json()
                        logger.debug(f"NetCourse: API原始响应:\n{result}")
                        return result
                    except aiohttp.ContentTypeError: # Handle non-JSON responses
                        logger.error(f"NetCourse: API响应不是有效的JSON. Status: {resp.status}. Response: {await resp.text()}")
                        return {"error": True, "message": "API返回非JSON格式数据", "http_status": resp.status}


        except aiohttp.ClientError as e:
            logger.error(f"NetCourse: 网络请求异常: {str(e)}")
            return {"error": True, "message": f"网络请求异常: {type(e).__name__}"}
        except Exception as e:
            logger.error(f"NetCourse: 未知异常在 fetch_netcourse: {str(e)}", exc_info=True)
            return {"error": True, "message": f"发生未知错误: {type(e).__name__}"}

    async def fetch_quote(self) -> str:
        """获取励志名言"""
        fallback_quote = "🌟 今天也要加油哦，未来的你会感谢现在努力的自己！"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session: # Shorter timeout for quotes
                async with session.get(self.quote_url) as resp:
                    if resp.status != 200:
                        return fallback_quote

                    result = await resp.json()
                    if result.get("code") == 200 and isinstance(result.get("data"), dict):
                        content = result["data"].get("content", "坚持不懈的努力，才有精彩的明天！")
                        author = result["data"].get("author", "佚名")
                        return f"🌟 『{content}』 —— {author}"
                    return fallback_quote
        except Exception as e:
            logger.error(f"NetCourse: 获取名言失败: {str(e)}")
            return fallback_quote

    def _format_progress_bar(self, progress_str: str, length: int = 10) -> str:
        """生成简单的文本进度条"""
        try:
            progress_val = float(progress_str.replace('%', ''))
            filled_length = int(length * progress_val // 100)
            bar = '🟩' * filled_length + '⬜' * (length - filled_length) # Green and white squares
            return f"[{bar}] {progress_val:.1f}%"
        except ValueError:
            return progress_str # Return original if parsing fails

    def _format_message(self, api_data: Dict[str, Union[int, str, List[Dict]]], quote: str) -> str:
        """生成格式化消息"""
        if api_data.get("error"): # Check for our custom error structure
            return f"🙁 糟糕，查询出错了: {api_data.get('message', '未知API错误')}"

        if api_data.get("code") != 1:
            error_msg = api_data.get("message", "API返回未知错误状态")
            return f"🙁 查询失败: {error_msg} (API Code: {api_data.get('code')})"

        tasks = api_data.get("data", [])
        if not isinstance(tasks, list) or not tasks:
            return "📭 没有找到该用户的任何网课任务记录！"

        task_count = len(tasks)
        task_details = f"🎉 哇！成功为用户查询到 {task_count} 条网课任务：\n"
        task_details += "═"*20 + "\n"

        for i, task in enumerate(tasks, start=1):
            ptname = task.get("ptname", "未知平台")
            school = task.get("school", "N/A")
            name = task.get("name", "未知姓名")
            kcname = task.get("kcname", "未知课程") # Course name
            status = task.get("status", "状态未知")
            progress = task.get("process", "0.0%")
            addtime = task.get("addtime", "N/A")
            
            course_start = task.get("courseStartTime") or "未开始"
            course_end = task.get("courseEndTime") or "未结束"
            exam_start = task.get("examStartTime") or "未开始"
            exam_end = task.get("examEndTime") or "未结束"

            status_emoji = "✅" if status == "已完成" else \
                           "🔄" if "进行中" in status or "学习中" in status else \
                           "⏳" if "待处理" in status or "排队中" in status else \
                           "❓"

            remarks_raw = task.get("remarks", "无备注信息")
            formatted_remarks = "无"
            if remarks_raw and remarks_raw != "无备注信息":
                remarks_list = [f"    🔸 {r.strip()}" for r in remarks_raw.split('|')]
                formatted_remarks = "\n" + "\n".join(remarks_list)


            task_details += (
                f"\n📘 **任务 {i} / {task_count}**\n"
                f"🎓 学生: {name}\n"
                f"🏫 学校: {school}\n"
                f"✍️ 课程: {kcname} ({ptname})\n"
                f"🚦 状态: {status_emoji} {status}\n"
                f"📊 进度: {self._format_progress_bar(progress)}\n"
                f"📅 添加: {addtime}\n"
                f"⏱️ 课程时间: {course_start} 至 {course_end}\n"
                f"🏆 考试时间: {exam_start} 至 {exam_end}\n"
                f"💬 备注: {formatted_remarks}\n"
                f"─"*15 + "\n"
            )

        task_details += f"\n{quote}\n"
        task_details += "\n🌈 再难的任务也要坚持完成，网课小助手和你一起努力！💪"
        return task_details

    @filter.command("网课查询", "查网课") # Added an alias
    async def netcourse_query(self, event: AstrMessageEvent):
        '''查询网课任务，格式：/网课查询 [手机号/学号]'''
        try:
            args = event.message_str.split()
            if len(args) < 2:
                yield CommandResult().error("😅 请输入手机号或学号进行查询，例如：\n/网课查询 13800138000")
                return

            query = ''.join(args[1:]) # Join all subsequent parts to handle spaces in username if ever needed, though unlikely for numbers
            if not query.strip().isdigit(): # Basic validation
                yield CommandResult().error("📵 学号/手机号通常是数字哦，请检查输入！")
                return

            yield CommandResult().message("📡 正在努力查询中，请稍候片刻...✨")

            api_response = await self.fetch_netcourse(query) # This now returns a dict, possibly with error info

            if not api_response: # Should ideally not happen if fetch_netcourse returns a dict
                yield CommandResult().error("💥 查询时发生内部错误，请联系管理员。")
                return

            # The _format_message function will handle error messages based on api_response content
            quote = await self.fetch_quote()
            formatted_msg = self._format_message(api_response, quote)

            # Check if the formatted message indicates an error before sending as success
            if formatted_msg.startswith("🙁") or formatted_msg.startswith("📭"):
                 yield CommandResult().error(formatted_msg) # Send as error if it's an error/no data message
            else:
                 yield CommandResult().message(formatted_msg)


        except Exception as e:
            logger.error(f"NetCourse: 处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 网课查询服务暂时不可用，请稍后再试或联系管理员。")
