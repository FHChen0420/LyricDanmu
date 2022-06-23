from aiohttp import ClientSession, web

import jsonpath

from utils.util import resource_path, showInfoDialog


async def _fetchFlvUrl(roomId: str) -> str:
    async with ClientSession() as session:
        async with session.get(f'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={roomId}&protocol=0,1&format=0,1,2&codec=0,1&qn=10000&platform=web&ptype=8') as resp:
            data = await resp.json()
            if data.get('data').get('live_status') == 1:
                # living
                hosts = jsonpath.jsonpath(data, "$...?(@.format_name=='flv').codec[?(@.codec_name=='avc')]")[0]
                urlInfo = hosts['url_info'][0]
                result = f'{urlInfo["host"]}{hosts["base_url"]}{urlInfo["extra"]}'
                print(f'flv path for room {roomId}: {result}')
                return result

class RoomPlayerChaser:
    def __init__(self, roomId: str) -> None:
        self.roomId = roomId
        self.app = web.Application()
        self.routes = web.RouteTableDef()
        @self.routes.get('/url')
        async def _getUrl(request):
            print(f'room id {self.roomId}')
            return web.json_response({'url': await _fetchFlvUrl(self.roomId)})
        path = resource_path('../static/','./static')
        self.routes.static('/', path)
        try:
            self.app.add_routes(self.routes)
        except:
            showInfoDialog(f"追帧相关的静态资源路径有误，请反馈给开发者\nPATH:{path}","提示")

    def serve(self, port):
        web.run_app(self.app, port=port, handle_signals=False)
