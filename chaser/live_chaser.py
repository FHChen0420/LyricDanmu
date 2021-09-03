import aiohttp
import jsonpath
from aiohttp import web

async def _fetchFlvUrl(roomId: str) -> str:
    async with aiohttp.ClientSession() as session:
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
        self.routes.static('/', './chaser/static/')
        self.app.add_routes(self.routes)

    def serve(self, port):
        web.run_app(self.app, port=port, handle_signals=False)

if __name__ == '__main__':
    player = RoomPlayerChaser('6')
    player.serve(8080)
    
    