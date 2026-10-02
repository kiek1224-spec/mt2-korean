-- 여신전생 2 (NES) 자동지도 — 화면 겹침판   -- Mesen 2 전용, 원판·한글판 공용
--
-- 쓰는 법
--   Mesen 에서 Debug > Script Window 를 열고 이 파일을 Open 한 뒤 실행(F5).
--     M = 켜기/끄기     N = 위치(네 귀퉁이)     V = 밟은 곳만 <-> 전체
--   던전(1인칭)에서는 지금 층 전체 틀 안에 칸을 그리고, 필드(마을·월드맵·마계·데빌 버스터)에서는
--   내 주변을 칸 색으로 줄여 그린다. 지나간 곳은 %TEMP%\mt2_automap_seen.txt 에 저장한다.
--   ★화면에 글자는 안 찍는다(Mesen 의 drawString 이 글자를 세로로 흘리는 문제, 1편 automap.lua 참고).
--
-- 표식 (던전)   노랑 ▲ 올라가는 계단 / 파랑 ▼ 내려가는 계단 / 초록 네모 엘리베이터 / 주황 빈 네모 보물상자
--              흰 고리 함정 / 보라 마름모 회전 바닥 / 빨강 ✕ 데미지 바닥 / 하늘 네모 출입구
--              분홍 점 대화 / 회색 점 간판 / 흰 + 중요 이벤트 / 흰 꽉 찬 네모 체크맨(기록·이동)
--              꽉 찬 네모: 하늘 상점 / 연파랑 회복의 샘 / 연두 사교의 관 / 빨강 바 / 노랑 카지노 등
--              보라 바탕 다크존, 흰 선 벽, 하늘 선 문, 주황빨강 화살표 = 나
--
-- 근거 (자세한 건 작업폴더 docs/자동지도_단서_2026-10-02.md)
--   던전 지도  원판 PRG $0000 (한글판 $40000), 128x64, 칸당 2바이트(벽 7-6북 5-4동 3-2남 1-0서 / 칸 종류)
--   층 표      원판 PRG $2D886 (bank22 $D886), 8x8 블록마다 (구역<<4 | 층)
--   위치       던전 X $042F Y $0430, 필드 X $0431 Y $0432, 방향 $042B(0북 1동 2남 3서),
--              $0429 비트7 = 필드, $0438 = 필드 지역 종류(타일셋)
--   필드 지도  청크 맵 원판 PRG $8EF8(64청크/줄) -> 청크 표 $8004/$8404 -> 칸 번호
--   이벤트 종류·필드 칸 색은 아래 데이터(build_data.py 가 만든 것)

KIND_NAMES = {"arena","bar","casino","checkman","chest","computer","cult","door","elevator","empty","entrance","event","exit","heal","locked","shop_armor","shop_item","shop_jewel","shop_weapon","sign","special","statue","talk"}
DUNGEON_EV = {[1547]=12,[773]=6,[775]=2,[774]=12,[1796]=12,[1797]=9,[1802]=9,[3845]=9,[3850]=9,[13385]=9,[1029]=21,[12361]=13,[13129]=20,[771]=23,[1803]=20,[1031]=20,[1284]=23,[1540]=23,[1030]=20,[3848]=23,[3081]=23,[1541]=23,[1287]=23,[778]=23,[3335]=23,[3083]=23,[2824]=23,[5220]=23,[5476]=23,[5222]=23,[791]=12,[1299]=19,[1307]=23,[1820]=23,[1301]=23,[12]=23,[1]=23,[1043]=23,[1557]=20,[1555]=20,[3098]=12,[3353]=23,[3611]=23,[35]=2,[1573]=14,[1318]=16,[1574]=20,[291]=20,[34]=23,[2851]=18,[59]=12,[830]=12,[1339]=12,[3879]=18,[1336]=2,[3882]=6,[2081]=23,[2858]=23,[3114]=23,[3626]=23,[3875]=12,[314]=23,[315]=23,[316]=23,[570]=23,[571]=23,[572]=23,[1595]=21,[1083]=21,[1855]=23,[1594]=23,[1852]=23,[1085]=23,[1854]=23,[1592]=20,[1834]=20,[3107]=20,[3878]=20,[1585]=12,[64]=12,[326]=14,[1092]=19,[580]=2,[1602]=16,[1606]=16,[1094]=12,[3413]=12,[582]=7,[603]=12,[2151]=12,[3651]=12,[4199]=12,[836]=20,[3653]=23,[1358]=23,[1866]=23,[1359]=23,[2639]=23,[2149]=23,[320]=20,[1350]=20,[1348]=20,[1346]=20,[1841]=20,[6687]=23,[1586]=23,[1331]=21,[1093]=20,[1122]=16,[2917]=12,[1636]=2,[1901]=19,[2665]=7,[5127]=12,[1634]=18,[1641]=18,[379]=12,[1892]=20,[3173]=23,[3431]=23,[5126]=23,[365]=14,[24]=15,[1121]=20,[1890]=20,[1385]=20,[1645]=20,[5148]=12,[7943]=12,[5134]=14,[5915]=12,[4110]=18,[4366]=20,[7960]=8,[7704]=21,[4674]=12,[4174]=23,[5408]=3,[5152]=3,[5410]=3,[5922]=16,[5921]=17,[5670]=18,[5931]=12,[5157]=14,[5932]=23,[5666]=20,[5926]=20,[13135]=12,[12879]=23,[13391]=23,[12367]=12,[14159]=12,[12623]=21,[13647]=21,[13903]=21,[8256]=12,[9280]=23,[11840]=23,[1584]=23,[11800]=12,[6162]=12,[9261]=12,[6756]=12,[6499]=23,[11011]=12,[7537]=12,[7793]=23,[10812]=12,[9239]=12,[8211]=21,[8724]=21,[9745]=21,[9750]=21,[8474]=21,[8476]=21,[9499]=21,[9759]=21,[11046]=21,[11810]=21,[11812]=21,[11815]=21,[10539]=21,[11309]=21,[11562]=21,[12073]=21,[6444]=12,[6440]=12,[6189]=23,[6445]=23,[11115]=12,[11874]=12,[3643]=12,[3124]=23,[2875]=23,[2878]=23,[3130]=23,[3388]=23,[8824]=23,[12549]=23,[12297]=23,[14091]=23,[12347]=12,[14147]=12,[12383]=12,[12395]=12,[2837]=9,[789]=9,[3354]=9,[5216]=9,[816]=9,[851]=9,[4614]=9,[2686]=9,[2678]=9,[638]=9,[630]=9,[2670]=9,[622]=9,[5384]=9,[7424]=9,[7432]=9,[5392]=9,[5400]=9,[11015]=9,[11023]=9,[8975]=9,[4983]=9,[7031]=9}
FIELD_EV = {[36882]=23,[36885]=12,[31283]=12,[31280]=12,[23596]=12,[23599]=12,[6443]=12,[6448]=23,[36903]=23,[36919]=23,[35889]=23,[35879]=23,[2142]=7,[11346]=23,[3161]=14,[3667]=23,[4435]=5,[4440]=17,[4442]=15,[4466]=15,[10586]=15,[10610]=15,[16730]=15,[16754]=15,[22898]=15,[29042]=15,[4437]=23,[4459]=23,[2649]=23,[2678]=23,[11355]=23,[4438]=23,[4464]=23,[5234]=23,[8042]=23,[11357]=23,[11348]=23,[9078]=23,[14939]=23,[14966]=23,[21102]=23,[15723]=23,[26474]=23,[23659]=23,[21106]=23,[27254]=23,[27242]=15,[38153]=8,[55637]=4,[54620]=7,[56410]=14,[56169]=16,[56175]=23,[55151]=23,[56179]=23,[50543]=15,[50549]=7,[48756]=14,[50005]=1,[51025]=3,[51029]=3,[51033]=3,[48985]=17,[48981]=2,[49489]=18,[48929]=10,[48939]=18,[50987]=23,[43815]=4,[44839]=23,[45347]=23,[45357]=18,[43566]=23,[45370]=14,[43845]=23,[43839]=23,[48957]=1,[48961]=3,[49987]=3,[51009]=3,[49981]=23,[51003]=23,[45395]=23,[49423]=4,[49939]=12,[50955]=12,[50961]=12,[44811]=23,[43277]=16,[34367]=4,[22599]=4,[22795]=12,[23323]=8,[25405]=23,[36413]=23,[28456]=23,[9507]=12,[2872]=8,[6438]=10,[5414]=12,[5903]=23,[9028]=23,[2343]=23,[17191]=23,[32601]=4,[32605]=16,[33371]=14,[33625]=23,[33629]=23,[21849]=16,[20827]=23,[22877]=14,[23385]=10,[26971]=14,[27481]=10,[27485]=23,[27742]=14,[28505]=17,[28509]=4,[55051]=4,[55059]=14,[56075]=16,[55822]=14,[55055]=17,[56589]=23,[56081]=23,[56595]=10,[55587]=16,[55595]=4,[55591]=14,[56103]=14,[56609]=23,[56619]=23,[55101]=4,[55105]=14,[56125]=17,[55614]=14,[56639]=23,[56643]=23,[16444]=23,[16701]=23,[16448]=23,[16705]=23,[16189]=23,[44864]=22,[44865]=22,[44609]=22,[44353]=22,[44352]=22,[44351]=22,[44607]=22,[44863]=22,[50983]=22,[50984]=22,[50728]=22,[50472]=22,[50471]=22,[50470]=22,[50726]=22,[50982]=22,[28712]=22,[28713]=22,[28457]=22,[28201]=22,[28200]=22,[28199]=22,[28455]=22,[28711]=22,[9269]=22,[9268]=22,[9012]=22,[8756]=22,[8757]=22,[8758]=22,[9014]=22,[9270]=22,[9527]=23,[9241]=22,[9240]=22,[8984]=22,[8728]=22,[8729]=22,[8730]=22,[8986]=22,[9242]=22,[9499]=23,[10021]=23,[7457]=12,[7981]=12,[11563]=12,[6951]=12,[12057]=12,[3346]=12,[34586]=11,[34082]=11,[30487]=11,[29460]=11,[22812]=11,[26898]=11,[37697]=11,[29486]=11,[55404]=11,[50501]=11,[44867]=11,[55129]=11,[55145]=11,[43883]=11,[43891]=11,[45417]=11,[45427]=11,[49957]=11,[43807]=11,[44322]=11,[44330]=11,[43327]=11,[45401]=11,[45837]=11,[44059]=11,[45128]=11,[43601]=11,[44662]=11,[51983]=11,[50207]=11,[51270]=11,[50255]=11,[51567]=11,[57197]=11,[55889]=11,[25359]=11,[31531]=11,[27445]=11,[25381]=11,[30493]=11,[26907]=11,[29465]=11,[25899]=11,[34603]=11,[31521]=11,[33567]=11,[37149]=11,[11036]=11,[12064]=11,[12046]=11,[13081]=11,[12561]=11,[14090]=11,[15118]=11,[15629]=11,[15645]=11,[16147]=11,[17166]=11,[17184]=11,[18196]=11,[18186]=11,[7437]=11,[2364]=11,[2369]=11,[10032]=11,[11577]=11,[13107]=11,[13623]=11,[14129]=11,[17196]=11,[15155]=11,[13125]=11,[13633]=11,[14149]=11,[14649]=11,[15678]=11,[3368]=11,[4370]=11,[5680]=11,[6451]=11,[55863]=11,[55878]=11,[38744]=11,[38775]=11,[55305]=11,[54311]=11,[29533]=11,[32347]=11,[22104]=11,[4935]=11,[16956]=11,[4887]=11,[11025]=11,[16139]=11,[3159]=11,[3183]=11,[3190]=11,[9310]=11,[8286]=11,[8310]=11,[10073]=11,[10097]=11,[10836]=11,[10860]=11,[10838]=11,[10862]=11,[11601]=11,[11625]=11,[11614]=11,[11638]=11,[15190]=11,[15214]=11,[17006]=11,[23150]=11,[23148]=11,[29292]=11}
FIELD_COLORS = {[0]={0x000000,0x1C798A,0x50622E,0x46603F,0x495A27,0x267676,0x24767B,0x307666,0x23757B,0x2C746B,0x1D798A,0x1C788A,0x237A86,0x1F7885,0x247985,0x217784,0x757C00,0x2F3300,0x393D00,0x2F3300,0x424600,0x1C798A,0x323500,0x737A01,0x949D01,0x323500,0x393C00,0x3A3E00,0x303300,0x353800,0x84837A,0x393C00,0xB2B684,0xC4C7AD,0xB7BB89,0xC5C8A9,0xDDE0D2,0xCBCEAD,0xB4B981,0xC7CBA5,0xB9BE84,0x192D00,0x051500,0x192C00,0x0C1B00,0x000900,0x0C1B00,0x1E3200,0x0C1E00,0x1D3100,0x3A3D00,0x2E3200,0x3C4000,0x393D00,0x949D01,0x4F5400,0x848D02,0x2F3300,0x121300,0x161800,0x434700,0x717800,0x747C00,0x798100,0x5D6122,0x616519,0x4A4B3B,0x484A2F,0x242700,0x358B9B,0x444444,0x428B99,0x434343,0x4C4B4C,0x434343,0x3E3E3E,0x3E3E3E,0x000000,0x949D01,0x5F8200,0x3F6F00,0x3F6F00,0x597C00,0x2F6400,0x2A6000,0x2A6000,0x2E6200,0x155900,0x155900,0x2A6900,0x165500,0x155900,0x1B5700,0x256500,0x155900,0x4E5200,0x020300,0x2B2E00,0x4D5200,0x252700,0x282B00,0x2B2D00,0x282A00,0x020300,0x393D00,0x6C7300,0x686E03,0x060700,0x2A2A2A,0x989698,0x6F6E6F,0x666654,0x626800,0x333333,0x4D501A,0x464A00,0x3E3E3E,0x5D6130,0x5C5F2E,0x6B6D53,0x5C5F39,0x696F07,0x6F7600,0x2E3000,0x2C2C2C,0x2A2A2A,0x2D2D2D,0x373A00,0x817F81,0x3A3D06,0x444444,0x505321,0x646A00,0x0A0A00,0x121300},[1]={0x000000,0xA64543,0x325137,0x44513F,0x2A4930,0x8D463D,0x934740,0x7A4839,0x93463F,0x80473C,0xA54745,0xA54644,0x9F4B47,0x9F4743,0x9E4B48,0x9E4845,0x162F0E,0x191806,0x182F13,0x221E0F,0x25280F,0x020300,0x003010,0x013110,0x046F25,0x000F05,0x000E05,0x000B03,0x025A1E,0x005A1E,0x532063,0x431950,0x9BC4D7,0xB0CEEC,0x9DC5D7,0xB0CEEC,0xB0CEEC,0xB0CEEC,0x9DC5D7,0xB0CEEC,0x9DC5D7,0x0C310C,0x0C1B04,0x093E11,0x101E04,0x111200,0x0D1E05,0x07370F,0x0D1B04,0x093B11,0x29250F,0x053F14,0x222108,0x073F14,0x046F25,0x1E3137,0x026321,0x1B1D07,0x17140B,0x57728E,0x749AC1,0x7194B8,0x6384A5,0x6689AD,0x3C3C27,0x444029,0x51332B,0x583731,0x29280B,0xB36563,0x3A5361,0xAD7371,0x3A5361,0x046F25,0x171211,0x93463F,0x161010,0x2F555D,0x046F25,0x32542B,0x23401A,0x34522D,0x1C3C15,0x1A551B,0x424021,0x282B0D,0x104B19,0x453B24,0x453B24,0x3C3E20,0x443B21,0x3E3B22,0x20250B,0x443A23,0x272810,0x432054,0x3A204B,0x135B23,0x036421,0x171211,0x3A5361,0x301B43,0x191806,0x1C1B07,0x026221,0x096526,0x20551B,0x166138,0x07682B,0x42372A,0x1F662F,0x096726,0x076B2D,0x0B693A,0x1B592B,0x187243,0x44513F,0x3C254E,0x3D214E,0x332144,0x451555,0x17140B,0x1E3137,0x20551B,0x000502},[2]={0x000000,0x124049,0x1D606D,0x145A67,0x155A67,0x1E6370,0x186573,0x166270,0x226F7E,0x196876,0x176574,0x10606F,0x136B7B,0x1D7484,0x1D7484,0x156E7E,0x1D034F,0x374E67,0x313031,0x3F3F3F,0x000000,0x3C3C3C,0x102B30,0x102B30},[3]={0x000000,0x124049,0x1D606D,0x145A67,0x155A67,0x1E6370,0x186573,0x166270,0x226F7E,0x196876,0x176574,0x10606F,0x136B7B,0x1D7484,0x1D7484,0x156E7E,0x1D034F,0x374E67,0x313031,0x3F3F3F,0x000000,0x3C3C3C,0x102B30,0x102B30},[4]={0x9BA400,0x393939,0x636463,0x616261,0x737473,0x676767,0x6F706F,0x595A59,0x616161,0x5E5E5E,0x696969,0x6A6A6A,0x555655,0x585958,0x595A59,0x555655,0x087600,0x464B46,0x424941,0x4B504B,0x224420,0x4F514F,0x515350,0x575757,0x565656,0x595A59,0x9D9E9D,0x8A8B8A,0xA3A5A3,0x587E7B,0x4C7872,0x2D786C,0x237576,0x2E796F,0x297979,0x197484,0x2A7880,0x2D786C,0x237576,0x2D786E,0x1C7583,0x1D7685,0x1C7583,0x1B7584,0x1F5C00,0x0E6002,0x5D5E5D,0x464646,0x515350,0x4F514F,0x4E514D,0x515251,0x4F524F,0x1C1707,0x126304,0x2D220C,0x0C7201,0x1C3D07,0x115804,0x096C00,0x3B3D3A,0x2C2212,0x184F25,0x1D3A1B,0x257220,0x468542,0x7E9A7C,0x478443,0x668764,0x7B8C7A,0x4B6F48,0x087600,0x2F2F2F,0x087600,0x484B48,0x515350,0x4F514F,0x797A79,0x393A39,0x393A39,0x4A6A47,0x314630,0x314030,0x294627,0x357954,0x184F25},[5]={0x266C00,0x3B3B3B,0x777877,0x777877,0x777877,0x777877,0x777877,0x777877,0x777877,0x777877,0x777877,0x777877,0x4E6840,0x4E6840,0x4E6840,0x4E6840,0x286D00,0x5E6863,0x394745,0x5E6863,0x000000,0x4E6840,0x4E6840,0x153B37,0x183739,0x143836,0x848883,0x6D6F6C,0x828680,0x474A46,0x444742,0x805239,0x8F4437,0x87503E,0x91483C,0x9F3533,0x98463F,0x84513C,0x8F4437,0x86503D,0x9E3835,0x9F3735,0x9E3734,0x9E3634,0x2B4512,0x30370B,0x4E6840,0x474A45,0x4E6840,0x4E6840,0x4E6840,0x4E6840,0x4E6840,0x463A14,0x453F10,0x325110,0x366011,0x2C5205,0x30370B,0x2D5106,0x1E1104,0x6F553B,0x4E371F,0x221406,0x6F553B,0x29630A,0x41473E,0x266703,0x456D30,0x353635,0x24530A,0x6F553B,0x3B3B3B,0x686338,0x4E6840,0x4E6840,0x4E6840,0x276D01}}

local PRG, RAM = emu.memType.nesPrgRom, emu.memType.nesMemory
local OFF = 0
do
  local ok, n = pcall(emu.getMemorySize, PRG)
  if ok and type(n) == "number" and n >= 0x80000 then OFF = 0x40000 end   -- 한글판: 원판 PRG 가 뒤쪽 절반
end
local function R(a) return emu.read(OFF + a, PRG) end

local KIND = {}
for i, n in ipairs(KIND_NAMES) do KIND[n] = i end
local STYLE = {}
local function st(name, col, shape) if KIND[name] then STYLE[KIND[name]] = {col, shape} end end
st("talk", 0xFF70D0, "dot");      st("sign", 0x909090, "dot");     st("event", 0xFFFFFF, "plus")
st("special", 0xB070FF, "dot");   st("elevator", 0x40E080, "fill"); st("computer", 0x00FFC0, "fill")
-- ★2026-10-02 상점·회복의 샘·출입구가 셋 다 하늘색 꽉 찬 네모라 헷갈렸다(사용자) -> 창판과 같은 색·모양으로 나눔
st("exit", 0x40D0FF, "box");      st("door", 0x40D0FF, "dot");     st("entrance", 0x40D0FF, "box")
st("bar", 0xFF5080, "fill");      st("cult", 0x80FF80, "fill");    st("heal", 0x2ECC71, "medkit")
st("casino", 0xE040FF, "fill");   st("arena", 0xE040FF, "fill");   st("statue", 0xC0C0C0, "odiamond")
st("shop_weapon", 0xFFC040, "coin"); st("shop_armor", 0xFFC040, "coin"); st("shop_item", 0xFFC040, "coin")
st("shop_jewel", 0xFFC040, "coin");  st("locked", 0x906040, "cross"); st("empty", 0x505050, "dot")
st("chest", 0xFF9020, "box");     st("checkman", 0xFFFFFF, "fill")
local S_UP, S_DOWN, S_CHEST = {0xFFE040, "up"}, {0x4070FF, "down"}, {0xFF9020, "box"}
local S_PIT, S_TURN, S_DMG, S_EXIT = {0xE0E0E0, "ring"}, {0xB070FF, "diamond"}, {0xFF3030, "cross"}, {0x40D0FF, "fill"}
local C_BACK, C_FLOOR, C_DARK, C_LIM, C_WALL, C_DOOR, C_ME = 0x000000, 0x202830, 0x3A1848, 0x183020, 0xE8E8F0, 0x40B4FF, 0xFF6040

-- ── 던전 지도 ─────────────────────────────────────────────────────────────
local DW, DH = 128, 56
local DWALL, DFLAG, BLK = {}, {}, {}
for y = 0, DH - 1 do
  for x = 0, DW - 1 do
    DWALL[y * DW + x] = R(y * 256 + 2 * x)
    DFLAG[y * DW + x] = R(y * 256 + 2 * x + 1)
  end
end
for i = 0, 127 do BLK[i] = R(0x2D886 + i) end

-- 지금 칸에서 벽을 따라 걸어서 닿는 칸들(같은 층 블록 안). 한 블록에 다른 작은 지도가 같이 들어 있어서
-- 블록째 그리면 남의 지도까지 보인다. 두 칸 사이는 양쪽 기록이 모두 벽(1)이 아닐 때만 잇는다.
local compOf, compInfo = {}, {}
local function component(sx, sy)
  local si = sy * DW + sx
  if compOf[si] then return compInfo[compOf[si]] end
  local id = #compInfo + 1
  local v = BLK[(sy // 8) * 16 + sx // 8]
  local cells, stack = {}, {si}
  compOf[si] = id
  local x0, y0, x1, y1 = sx, sy, sx, sy
  local DXY = {[0] = {0, -1}, {1, 0}, {0, 1}, {-1, 0}}
  while #stack > 0 do
    local i = table.remove(stack)
    cells[i] = true
    local x, y = i % DW, i // DW
    if x < x0 then x0 = x end; if y < y0 then y0 = y end
    if x > x1 then x1 = x end; if y > y1 then y1 = y end
    for d = 0, 3 do
      local nx, ny = x + DXY[d][1], y + DXY[d][2]
      if nx >= 0 and nx < DW and ny >= 0 and ny < DH then
        local j = ny * DW + nx
        if not compOf[j] and BLK[(ny // 8) * 16 + nx // 8] == v and (DFLAG[j] & 0xC0) ~= 0xC0
           and ((DWALL[i] >> (6 - 2 * d)) & 3) ~= 1 and ((DWALL[j] >> (6 - 2 * ((d + 2) % 4))) & 3) ~= 1 then
          compOf[j] = id; stack[#stack + 1] = j
        end
      end
    end
  end
  local info = {cells = cells, x0 = x0, y0 = y0, w = x1 - x0 + 1, h = y1 - y0 + 1}
  compInfo[id] = info
  return info
end

-- ── 필드 지도 (칸 번호를 미리 풀어 둔다: 타일셋 0·1 과 2~5 는 청크 표가 다르다) ──────────
local FW, FH = 128, 232
local FMETA = {[0] = {}, [1] = {}}
for sel = 0, 1 do
  local ctab = R(0x8000 + sel * 2) | (R(0x8001 + sel * 2) << 8)
  local t = FMETA[sel]
  for y = 0, FH - 1 do
    for x = 0, FW - 1 do
      local c = R(0x8EF8 + (y >> 1) * 64 + (x >> 1))
      t[y * 256 + x] = R(ctab + c * 4 + (y & 1) * 2 + (x & 1))
    end
  end
end

-- ── 지나간 곳 ───────────────────────────────────────────────────────────
local SEEN_FILE = (os.getenv("TEMP") or ".") .. "\\mt2_automap_seen.txt"
local DSEEN, FSEEN, dirty = {}, {}, false
pcall(function()
  local f = io.open(SEEN_FILE, "r")
  if not f then return end
  for line in f:lines() do
    local t, v = line:match("^(%a) (%d+)$")
    if t == "d" then DSEEN[tonumber(v)] = true elseif t == "f" then FSEEN[tonumber(v)] = true end
  end
  f:close()
end)
local function saveSeen()
  pcall(function()
    local f = io.open(SEEN_FILE, "w")
    if not f then return end
    for k in pairs(DSEEN) do f:write("d ", k, "\n") end
    for k in pairs(FSEEN) do f:write("f ", k, "\n") end
    f:close()
  end)
  dirty = false
end

-- ── 그리기 도우미 ─────────────────────────────────────────────────────────
local function icon(X, Y, c, sty)
  local col, shape = sty[1], sty[2]
  local s = math.max(2, c - 2)
  if shape == "fill" then emu.drawRectangle(X + 1, Y + 1, s, s, col, true, 1)
  elseif shape == "box" then emu.drawRectangle(X + 1, Y + 1, s, s, col, false, 1)
  elseif shape == "dot" then local h = c // 2; emu.drawRectangle(X + h - 1, Y + h - 1, 2, 2, col, true, 1)
  elseif shape == "ring" then emu.drawRectangle(X + 1, Y + 1, s, s, col, false, 1)
  elseif shape == "coin" then                          -- 상점: 모서리를 깎은 꽉 찬 네모(작은 칸에서 동그라미 대신)
    emu.drawRectangle(X + 2, Y + 1, math.max(1, s - 2), s, col, true, 1)
    emu.drawRectangle(X + 1, Y + 2, s, math.max(1, s - 2), col, true, 1)
  elseif shape == "medkit" then                        -- 회복의 샘: 초록 바탕 + 흰 십자
    local h = c // 2
    emu.drawRectangle(X + 1, Y + 1, s, s, col, true, 1)
    emu.drawLine(X + h, Y + 2, X + h, Y + c - 2, 0xFFFFFF, 1); emu.drawLine(X + 2, Y + h, X + c - 2, Y + h, 0xFFFFFF, 1)
  elseif shape == "plus" then local h = c // 2
    emu.drawLine(X + h, Y + 1, X + h, Y + c - 1, col, 1); emu.drawLine(X + 1, Y + h, X + c - 1, Y + h, col, 1)
  elseif shape == "cross" then
    emu.drawLine(X + 1, Y + 1, X + c - 1, Y + c - 1, col, 1); emu.drawLine(X + c - 1, Y + 1, X + 1, Y + c - 1, col, 1)
  elseif shape == "up" or shape == "down" then
    for r = 0, s - 1 do
      local half = (shape == "up") and (r // 2) or ((s - 1 - r) // 2)
      local cx = X + c // 2
      emu.drawLine(cx - half, Y + 1 + r, cx + half, Y + 1 + r, col, 1)
    end
  elseif shape == "diamond" or shape == "odiamond" then
    local h = c // 2; local rr = math.max(1, h - 1); local cx, cy = X + h, Y + h
    if shape == "diamond" then
      for d = -rr, rr do local hw = rr - math.abs(d); emu.drawLine(cx - hw, cy + d, cx + hw, cy + d, col, 1) end
    else
      emu.drawLine(cx, cy - rr, cx + rr, cy, col, 1); emu.drawLine(cx + rr, cy, cx, cy + rr, col, 1)
      emu.drawLine(cx, cy + rr, cx - rr, cy, col, 1); emu.drawLine(cx - rr, cy, cx, cy - rr, col, 1)
    end
  end
end

local DIRS = {[0] = {0, -1}, {1, 0}, {0, 1}, {-1, 0}}
local function arrow(cx, cy, d, r, col)
  local dx, dy = DIRS[d][1], DIRS[d][2]
  local tipx, tipy, bx, by, px, py = cx + dx * r, cy + dy * r, cx - dx * r, cy - dy * r, -dy, dx
  emu.drawLine(tipx, tipy, bx + px * r, by + py * r, col, 1)
  emu.drawLine(tipx, tipy, bx - px * r, by - py * r, col, 1)
  emu.drawLine(bx + px * r, by + py * r, bx - px * r, by - py * r, col, 1)
end

local show, corner, visitedOnly = true, 3, (MT2_AUTOMAP_VISITED_ONLY == true)   -- 전역은 시험용
local prevM, prevN, prevV = false, false, false
local frame = 0
local MAXPX = 104

local function boxAt(bw, bh)
  local CO = {{6, 6}, {256 - bw - 7, 6}, {6, 240 - bh - 7}, {256 - bw - 7, 240 - bh - 7}}
  return CO[corner + 1][1], CO[corner + 1][2]
end

local function drawDungeon(px, py, dir)
  if px >= DW or py >= DH then return end
  local i0 = py * DW + px
  if not DSEEN[i0] then DSEEN[i0] = true; dirty = true end
  local rg = component(px, py)
  local c = math.max(3, math.min(8, MAXPX // math.max(rg.w, rg.h)))
  local bw, bh = rg.w * c, rg.h * c
  local ox, oy = boxAt(bw, bh)
  emu.drawRectangle(ox - 2, oy - 2, bw + 4, bh + 4, C_BACK, true, 1)
  for y = rg.y0, rg.y0 + rg.h - 1 do
    for x = rg.x0, rg.x0 + rg.w - 1 do
      local i = y * DW + x
      local f = DFLAG[i]
      if rg.cells[i] and (not visitedOnly or DSEEN[i]) then
        local X, Y = ox + (x - rg.x0) * c, oy + (y - rg.y0) * c
        local bg = C_FLOOR
        if (f & 0x20) ~= 0 then bg = C_DARK elseif (f & 0x0F) == 1 then bg = C_LIM end
        emu.drawRectangle(X, Y, c, c, bg, true, 1)
        local w = DWALL[i]
        local n, e, s, wv = (w >> 6) & 3, (w >> 4) & 3, (w >> 2) & 3, w & 3
        if n ~= 0 then emu.drawLine(X, Y, X + c - 1, Y, n == 1 and C_WALL or C_DOOR, 1) end
        if s ~= 0 then emu.drawLine(X, Y + c - 1, X + c - 1, Y + c - 1, s == 1 and C_WALL or C_DOOR, 1) end
        if wv ~= 0 then emu.drawLine(X, Y, X, Y + c - 1, wv == 1 and C_WALL or C_DOOR, 1) end
        if e ~= 0 then emu.drawLine(X + c - 1, Y, X + c - 1, Y + c - 1, e == 1 and C_WALL or C_DOOR, 1) end
        local ev = DUNGEON_EV[y * 256 + x]
        if (f & 0xC0) == 0x80 then icon(X, Y, c, S_UP)
        elseif (f & 0xC0) == 0x40 then icon(X, Y, c, S_DOWN)
        elseif ev and STYLE[ev] then icon(X, Y, c, STYLE[ev])
        elseif (f & 0x10) ~= 0 then icon(X, Y, c, S_CHEST)
        else
          local nib = f & 0x0F
          if nib == 2 then icon(X, Y, c, S_TURN) elseif nib == 3 then icon(X, Y, c, S_DMG)
          elseif nib == 4 then icon(X, Y, c, S_PIT) elseif nib == 5 then icon(X, Y, c, S_EXIT) end
        end
      end
    end
  end
  local h = c // 2
  arrow(ox + (px - rg.x0) * c + h, oy + (py - rg.y0) * c + h, dir & 3, math.max(1, h - 1), C_ME)
end

local FWIN_W, FWIN_H, FC = 40, 30, 3
local function drawField(px, py, dir, ts)
  if px >= FW or py >= FH then return end
  for y = py - 7, py + 7 do                    -- 화면에 보이는 범위를 「본 곳」으로
    for x = px - 8, px + 7 do
      if x >= 0 and y >= 0 and x < FW and y < FH then
        local k = y * 256 + x
        if not FSEEN[k] then FSEEN[k] = true; dirty = true end
      end
    end
  end
  local meta = FMETA[ts < 2 and 0 or 1]
  local cols = FIELD_COLORS[ts] or FIELD_COLORS[4]
  local bw, bh = FWIN_W * FC, FWIN_H * FC
  local ox, oy = boxAt(bw, bh)
  local x0, y0 = px - FWIN_W // 2, py - FWIN_H // 2
  emu.drawRectangle(ox - 2, oy - 2, bw + 4, bh + 4, C_BACK, true, 1)
  for j = 0, FWIN_H - 1 do                     -- 같은 색이 이어지면 한 번에 그린다
    local y = y0 + j
    local runStart, runCol = 0, -1
    for i = 0, FWIN_W do
      local col = -1
      if i < FWIN_W then
        local x = x0 + i
        if x >= 0 and y >= 0 and x < FW and y < FH and (not visitedOnly or FSEEN[y * 256 + x]) then
          col = cols[(meta[y * 256 + x] or 0) + 1] or 0
        end
      end
      if col ~= runCol then
        if runCol >= 0 then emu.drawRectangle(ox + runStart * FC, oy + j * FC, (i - runStart) * FC, FC, runCol, true, 1) end
        runStart, runCol = i, col
      end
    end
  end
  for j = 0, FWIN_H - 1 do
    for i = 0, FWIN_W - 1 do
      local x, y = x0 + i, y0 + j
      local ev = FIELD_EV[y * 256 + x]
      if ev and STYLE[ev] and (not visitedOnly or FSEEN[y * 256 + x]) then
        emu.drawRectangle(ox + i * FC, oy + j * FC, FC, FC, STYLE[ev][1], true, 1)
      end
    end
  end
  local cx, cy = ox + (px - x0) * FC + 1, oy + (py - y0) * FC + 1
  emu.drawRectangle(cx - 2, cy - 2, 5, 5, C_ME, false, 1)
  arrow(cx, cy, dir & 3, 3, C_ME)
end

local function key(k)                          -- 키보드가 없는 환경(헤드리스)에서도 멈추지 않게
  local ok, v = pcall(emu.isKeyPressed, k)
  return ok and v
end

emu.addEventCallback(function()
  frame = frame + 1
  local m, n, v = key("M"), key("N"), key("V")
  if m and not prevM then show = not show end
  if n and not prevN then corner = (corner + 1) % 4 end
  if v and not prevV then visitedOnly = not visitedOnly end
  prevM, prevN, prevV = m, n, v
  if dirty and frame % 300 == 0 then saveSeen() end
  if not show then return end
  -- 전투 중에는 안 그린다: $0400 비트5 = 전투 깃발(전투 뱅크 $1A 가 켜고 끈다, 2026-10-02)
  if (emu.read(0x0400, RAM) & 0x20) ~= 0 then return end
  local dir = emu.read(0x042B, RAM)
  if (emu.read(0x0429, RAM) & 0x80) ~= 0 then
    drawField(emu.read(0x0431, RAM), emu.read(0x0432, RAM), dir, emu.read(0x0438, RAM) & 7)
  else
    drawDungeon(emu.read(0x042F, RAM), emu.read(0x0430, RAM), dir)
  end
end, emu.eventType.endFrame)

if emu.eventType.scriptEnded then emu.addEventCallback(saveSeen, emu.eventType.scriptEnded) end

MT2_AUTOMAP_INFO = { off = OFF, kinds = #KIND_NAMES }
emu.displayMessage("MT2", "자동지도: M 켜기/끄기, N 위치, V 밟은 곳만/전체")
