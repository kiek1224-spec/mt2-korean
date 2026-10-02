-- 여신전생 2 자동지도 — 별도 창 브리지   -- Mesen 2 전용, 원판·한글판 공용
--
-- 지도 창(mt2_map_window.py)에 **지금 위치와 방향**, 전투 중이면 **적 칸(악마 번호·HP·MP)**만 보낸다.
-- 지도 계산과 그리기는 전부 창 쪽(파이썬)이 한다. 게임 화면에는 아무것도 안 그린다.
--
-- 쓰는 법
--   1) Mesen 에서 Debug > Script Window 로 이 파일을 열고 실행(F5)
--   2) python mt2_map_window.py   (순서는 상관없다. 창이 알아서 다시 붙는다)
--
-- 통신
--   127.0.0.1:9877 에서 기다린다 (1편 브리지 9876 과 안 겹치게).
--   한 줄에 JSON 하나:  {"f":0,"x":6,"y":4,"d":0,"ts":0,"a":12,"fl":4}
--     f  = 1 필드 / 0 던전($0429 비트7)    x,y = 필드면 $0431/$0432, 던전이면 $042F/$0430
--     d  = 방향 $042B(0북 1동 2남 3서)     ts = 필드 지역 종류 $0438   a = $0429   fl = $040B
--     m  = 마카(소지금) $0404~$0406 (3바이트, 아래가 먼저)   g = MAG $0407~$0408 (2바이트)   (2026-10-02 추가)
--          사용자 세이브 c29_10 화면의 「소지금 18661 / MAG 6379」와 메모리 값이 그대로 일치(2진수, BCD 아님).
--     b  = 전투 중일 때만 붙는다: [[악마번호, HP, 최대HP, MP, 최대MP], ...]  (2026-10-02 추가)
--          전투 깃발 = $0400 비트5 (전투 뱅크 $1A 가 ORA #$20 으로 켜고 AND #$DF 로 끈다)
--          적 8칸: 있음 = $0520+i 비트7, 종류 $05C0+i, HP $0548+i/$055C+i(상위), 최대 HP $0584+i/$0598+i,
--          MP $0570+i, 최대 MP $05AC+i  (참고/MT2_RAM심볼.nl). 전투가 끝나도 지난 값이 남으므로 깃발을 먼저 본다.
--          악마 정보(이름·능력치·상성)는 창 쪽 mt2_demon_info.py 가 롬에서 푼다.
--   값이 바뀔 때 보내고, 안 바뀌어도 60프레임마다 한 번 보낸다(창이 「멈춤」을 알아채게).
--   ★endFrame 콜백 안에서 보내므로 Mesen 이 일시정지면 아무것도 안 간다.
--
-- 근거
--   LuaSocket 은 MesenCore.dll 안에 package.preload["socket.core"] 로 들어 있다(1편 ds_bridge.lua 와 같음).
--   소켓을 못 불러오면 Script Window 설정에서 네트워크/입출력 접근을 허용해야 한다.

local PORT = 9877
local RAM  = emu.memType.nesMemory

local okS, socket = pcall(require, "socket.core")
if not okS then
  emu.displayMessage("MT2", "소켓을 못 불러왔다 - Script Window 설정에서 네트워크 접근을 허용할 것")
  return
end

local server = assert(socket.tcp())
pcall(function() server:setoption("reuseaddr", true) end)
local okB, errB = server:bind("127.0.0.1", PORT)
if not okB then
  emu.displayMessage("MT2", "포트 " .. PORT .. " 을 못 열었다: " .. tostring(errB))
  return
end
server:listen(4)
server:settimeout(0)

local clients = {}
local last, frame = "", 0

local function closeAll()
  for _, c in ipairs(clients) do pcall(function() c:close() end) end
  clients = {}
  pcall(function() server:close() end)
end

emu.addEventCallback(function()
  frame = frame + 1

  local c = server:accept()
  if c then
    c:settimeout(0)
    clients[#clients + 1] = c
    last = ""                                      -- 새로 붙은 창에는 바로 한 번 보낸다
  end
  if #clients == 0 then return end

  local area = emu.read(0x0429, RAM)
  local field = (area & 0x80) ~= 0
  local x, y
  if field then x, y = emu.read(0x0431, RAM), emu.read(0x0432, RAM)
  else x, y = emu.read(0x042F, RAM), emu.read(0x0430, RAM) end
  local battle = ""
  if (emu.read(0x0400, RAM) & 0x20) ~= 0 then             -- 전투 중
    local e = {}
    for i = 0, 7 do
      if (emu.read(0x0520 + i, RAM) & 0x80) ~= 0 then
        e[#e + 1] = string.format("[%d,%d,%d,%d,%d]", emu.read(0x05C0 + i, RAM),
          emu.read(0x0548 + i, RAM) | (emu.read(0x055C + i, RAM) << 8),
          emu.read(0x0584 + i, RAM) | (emu.read(0x0598 + i, RAM) << 8),
          emu.read(0x0570 + i, RAM), emu.read(0x05AC + i, RAM))
      end
    end
    battle = ',"b":[' .. table.concat(e, ",") .. ']'
  end
  local makka = emu.read(0x0404, RAM) | (emu.read(0x0405, RAM) << 8) | (emu.read(0x0406, RAM) << 16)
  local mag = emu.read(0x0407, RAM) | (emu.read(0x0408, RAM) << 8)
  local msg = string.format('{"f":%d,"x":%d,"y":%d,"d":%d,"ts":%d,"a":%d,"fl":%d,"m":%d,"g":%d%s}\n',
    field and 1 or 0, x, y, emu.read(0x042B, RAM) & 3, emu.read(0x0438, RAM) & 7, area, emu.read(0x040B, RAM),
    makka, mag, battle)

  if msg ~= last or frame % 60 == 0 then
    for i = #clients, 1, -1 do
      local _, err = clients[i]:send(msg)
      if err and err ~= "timeout" then               -- 창이 닫혔다
        pcall(function() clients[i]:close() end)
        table.remove(clients, i)
      end
    end
    last = msg
  end
end, emu.eventType.endFrame)

-- 스크립트를 다시 실행할 때 포트가 붙잡혀 있지 않게 닫는다
if emu.eventType.scriptEnded then
  emu.addEventCallback(closeAll, emu.eventType.scriptEnded)
end

MT2_BRIDGE_INFO = { port = PORT, listening = 1 }   -- 헤드리스 검증이 읽는 자리

emu.displayMessage("MT2", "지도 브리지 대기 중 (포트 " .. PORT .. ") - mt2_map_window.py 를 실행하세요")
