# 璁烘枃鎼滄悳

璁烘枃鎼滄悳鏄竴涓湰鍦拌繍琛岀殑璁烘枃妫€绱€佺瓫閫変笌 AI 鎽樿宸ュ叿銆傞」鐩敮鎸佷粠澶氫釜璁烘枃鏉ユ簮妫€绱㈣鏂囷紝鎸夊叧閿瘝鍏ュ簱锛岃嚜鍔ㄥ尮閰?SCI 鍒嗗尯锛屽苟鍙€氳繃 OpenAI 鍏煎鎺ュ彛鐢熸垚涓枃璁烘枃鎬荤粨銆?
椤圭洰褰撳墠涓昏闈㈠悜鏈湴妗岄潰浣跨敤锛氬墠绔敱 React 鏋勫缓锛屽悗绔敱 FastAPI 鎻愪緵鎺ュ彛锛屾暟鎹粯璁や繚瀛樺湪鏈湴 SQLite 鏁版嵁搴撲腑锛屼篃鍙互閫氳繃 PyInstaller 鎵撳寘涓?Windows 鍗曟枃浠?exe銆?
> 涓嬭浇 Windows 鐗堟湰锛氳鍦ㄤ粨搴撳彸渚х殑 Releases 椤甸潰涓嬭浇鏈€鏂扮増 exe銆傞娆¤繍琛屼細鍦?exe 鎵€鍦ㄧ洰褰曟梺鍒涘缓鏈湴鏁版嵁鏂囦欢銆?
## 涓昏鍔熻兘

- 澶氬叧閿瘝璁烘枃妫€绱笌绠＄悊
- 鏀寔 arXiv銆丼emantic Scholar銆丏BLP銆丟oogle Scholar銆佹毃澶у浘涔﹂绛夋潵婧?- 璁烘枃鍘婚噸銆佸叧閿瘝鍏宠仈銆佹敹钘忋€佸凡璇荤姸鎬?- SCI Q1-Q4 鍒嗗尯鍖归厤涓庡垎鍖轰紭鍏堟帓搴?- 鎸夋爣棰樸€佹憳瑕併€佹潵婧愩€佹棩鏈熴€佸紩鐢ㄦ暟銆佸垎鍖虹瓫閫夎鏂?- CSV 瀵煎嚭褰撳墠绛涢€夌粨鏋?- AI 涓枃鎽樿鐢熸垚锛屾敮鎸?PDF銆佺綉椤垫鏂囥€佹憳瑕佸拰鍏冧俊鎭厹搴?- AI 鑷姩鎽樿寮€鍏抽粯璁ゅ叧闂紝閬垮厤鏃犳剰娑堣€楃敤鎴?token
- 鏈湴閰嶇疆 API Key锛岀増鏈洿鏂版椂灏介噺淇濈暀鏃х敤鎴烽厤缃?- Windows 妗岄潰 exe 鎵撳寘杩愯

## 鎶€鏈爤

| 灞傜骇 | 鎶€鏈?|
| --- | --- |
| 鍓嶇 | React 19, TypeScript, Vite, Tailwind CSS |
| 鍚庣 | FastAPI, SQLAlchemy Async, SQLite, APScheduler |
| AI | OpenAI-compatible Chat Completions API |
| 妗岄潰鎵撳寘 | PyWebView, PyInstaller |

## 鐩綍缁撴瀯

```text
.
鈹溾攢鈹€ backend/
鈹?  鈹溾攢鈹€ app/
鈹?  鈹?  鈹溾攢鈹€ models/          # SQLAlchemy 妯″瀷
鈹?  鈹?  鈹溾攢鈹€ routers/         # FastAPI 璺敱
鈹?  鈹?  鈹溾攢鈹€ schemas/         # Pydantic 鍝嶅簲/璇锋眰妯″瀷
鈹?  鈹?  鈹溾攢鈹€ services/        # 鐖櫕銆佹憳瑕併€佽皟搴︺€丼CI 鍖归厤
鈹?  鈹?  鈹溾攢鈹€ config.py        # 閰嶇疆涓庢湰鍦版暟鎹洰褰?鈹?  鈹?  鈹溾攢鈹€ database.py      # 寮傛 SQLite 杩炴帴
鈹?  鈹?  鈹斺攢鈹€ main.py          # FastAPI 搴旂敤鍏ュ彛
鈹?  鈹溾攢鈹€ data/
鈹?  鈹?  鈹斺攢鈹€ jcr_seed.csv     # 鍒濆 SCI 鍒嗗尯鏁版嵁
鈹?  鈹溾攢鈹€ run.py               # Windows 妗岄潰鍏ュ彛
鈹?  鈹溾攢鈹€ paperfind.spec       # PyInstaller 鎵撳寘閰嶇疆
鈹?  鈹斺攢鈹€ requirements.txt
鈹溾攢鈹€ frontend/
鈹?  鈹斺攢鈹€ src/
鈹?      鈹溾攢鈹€ api/             # 鍓嶇 API 灏佽
鈹?      鈹溾攢鈹€ components/      # UI 缁勪欢
鈹?      鈹溾攢鈹€ contexts/        # 鍏ㄥ眬鐘舵€?鈹?      鈹溾攢鈹€ hooks/           # React hooks
鈹?      鈹溾攢鈹€ pages/           # 椤甸潰
鈹?      鈹斺攢鈹€ types/           # TypeScript 绫诲瀷
鈹溾攢鈹€ PROJECT_SUMMARY.md
鈹溾攢鈹€ PROJECT_IMPROVEMENT_PLAN.md
鈹斺攢鈹€ README.md
```

## 鏈湴寮€鍙?
### 鐜瑕佹眰

- Python 3.10+
- Node.js 18+
- Windows 鐜涓嬫墦鍖?exe 闇€瑕?PyInstaller 涓?PyWebView

### 瀹夎渚濊禆

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install pywebview pyinstaller
```

```bash
cd frontend
npm install
```

### 閰嶇疆鐜鍙橀噺

澶嶅埗 `.env.example` 涓?`.env`锛屼篃鍙互鍦ㄨ蒋浠剁殑璁剧疆椤典腑閰嶇疆 AI 鎺ュ彛銆?
```bash
copy .env.example .env
```

甯哥敤 AI 閰嶇疆绀轰緥锛?
```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

涔熷彲浠ヤ娇鐢ㄥ叾浠?OpenAI 鍏煎鏈嶅姟锛屼緥濡?OpenAI銆丟roq銆佺鍩烘祦鍔ㄧ瓑銆傝纭繚 `LLM_BASE_URL`銆乣LLM_MODEL` 涓?API Key 灞炰簬鍚屼竴涓湇鍔″晢銆?
### 鍚姩寮€鍙戠幆澧?
鍚庣榛樿浣跨敤 `8001` 绔彛锛?
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

鍓嶇寮€鍙戞湇鍔″櫒锛?
```bash
cd frontend
npm run dev
```

娴忚鍣ㄨ闂?Vite 杈撳嚭鐨勬湰鍦板湴鍧€锛屽墠绔細鎶?`/api` 璇锋眰浠ｇ悊鍒?`http://localhost:8001`銆?
## 鎵撳寘 Windows exe

鍏堟瀯寤哄墠绔細

```bash
cd frontend
npm run build
```

鍐嶆墦鍖呭悗绔闈㈠叆鍙ｏ細

```bash
cd backend
pyinstaller --clean paperfind.spec
```

鎵撳寘缁撴灉浣嶄簬锛?
```text
backend/dist/璁烘枃鎼滄悳.exe
```

娉ㄦ剰锛歚backend/dist/`銆乣backend/build/`銆佹暟鎹簱鏂囦欢鍜屾棩蹇楀睘浜庢湰鍦扮敓鎴愪骇鐗╋紝涓嶅缓璁彁浜ゅ埌 Git銆?
## 甯歌闂

### AI 鎽樿鏄剧ず Request Blocked 鎴?HTML 閿欒

杩欓€氬父璇存槑 AI 鏈嶅姟杩斿洖浜嗙綉椤垫嫤鎴〉锛岃€屼笉鏄甯哥殑 API 鍝嶅簲銆傝妫€鏌ワ細

- `LLM_BASE_URL` 鏄惁涓?API 鍦板潃锛岃€屼笉鏄畼缃戝湴鍧€
- API Key 鏄惁灞炰簬褰撳墠鏈嶅姟鍟?- 妯″瀷鍚嶆槸鍚︽纭?- 缃戠粶銆佷唬鐞嗘垨鏈嶅姟鍟嗛鎺ф槸鍚︽嫤鎴姹?
### 涓轰粈涔堣嚜鍔ㄦ憳瑕侀粯璁ゅ叧闂紵

鑷姩鎽樿浼氭寔缁秷鑰?API token銆備负浜嗛伩鍏嶇敤鎴锋棤鎰忎骇鐢熻垂鐢紝鏈蒋浠堕粯璁ゅ叧闂嚜鍔ㄦ憳瑕侊紝闇€瑕佸湪璁剧疆椤垫墜鍔ㄥ紑鍚€?
### 涓轰粈涔堟绱㈠畬鎴愬悗鎸夊垎鍖烘帓搴忥紵

璁烘枃鍒楄〃浠ュ悗绔?`/api/papers` 杩斿洖缁撴灉涓哄噯锛岄粯璁ゆ寜 `Q1 鈫?Q2 鈫?Q3 鈫?Q4 鈫?鏈敹褰昤 鎺掑簭锛屼繚璇佹绱㈠畬鎴愬悗浼樺厛灞曠ず楂樺垎鍖鸿鏂囥€?
## AI 涓庡悎瑙勮鏄?
鏈」鐩寘鍚?AI 鎽樿鍔熻兘鍜岃鏂囨潵婧愭绱㈠姛鑳斤紝浣跨敤鍓嶈娉ㄦ剰浠ヤ笅浜嬮」锛?
- 鏈蒋浠朵笉浼氬唴缃换浣曠涓夋柟 AI API Key銆傜敤鎴烽渶瑕佽嚜琛屽湪璁剧疆椤垫垨 `.env` 涓厤缃嚜宸辩殑 API Key銆?- AI 鎽樿浼氭秷鑰楃敤鎴锋墍閰嶇疆鏈嶅姟鍟嗙殑 token 鎴栭搴︼紝鑷姩鎽樿榛樿鍏抽棴锛岄渶瑕佺敤鎴疯嚜琛屽紑鍚€?- AI 鐢熸垚鍐呭鍙兘瀛樺湪閿欒銆侀仐婕忋€佸够瑙夋垨鐞嗚В鍋忓樊锛屽彧鑳戒綔涓鸿緟鍔╅槄璇诲弬鑰冿紝涓嶈兘鏇夸唬闃呰鍘熸枃鎴栦笓涓氬垽鏂€?- 璇峰嬁鎶婃秹瀵嗐€佹晱鎰熴€佸彈淇濇姢鎴栨棤鏉冨鐞嗙殑鍐呭鎻愪氦缁欑涓夋柟 AI 鏈嶅姟銆?- 浣跨敤 DeepSeek銆丱penAI銆丟roq銆佺鍩烘祦鍔ㄧ瓑鏈嶅姟鏃讹紝璇疯嚜琛岄伒瀹堝搴旀湇鍔″晢鐨勬湇鍔℃潯娆俱€侀殣绉佹斂绛栥€佽璐硅鍒欏拰閫傜敤娉曞緥娉曡銆?- 鏈」鐩細浠庡叕寮€璁烘枃鏉ユ簮鎴栫敤鎴峰彲璁块棶鐨勭綉椤垫绱俊鎭€備笉鍚岀綉绔欏彲鑳芥湁鑷繁鐨?robots銆佽闂鐜囥€佺増鏉冨拰浣跨敤鏉℃锛岃鍦ㄥ悎娉曞悎瑙勮寖鍥村唴浣跨敤銆?- 鏈」鐩笉鎻愪緵瑙勯伩楠岃瘉鐮併€佺粫杩囦粯璐瑰銆佺牬瑙ｆ満鏋勬潈闄愭垨鎵归噺涓嬭浇鍙楃増鏉冧繚鎶ゅ叏鏂囩殑鑳藉姏銆侷EEE/ACM 绛夋満鏋勮闂渶瑕佺敤鎴锋嫢鏈夊悎娉曟満鏋勬潈闄愬拰 Cookie銆?- 瀵煎嚭鐨勮鏂囦俊鎭€丄I 鎽樿鍜屾湰鍦版暟鎹簱浠呬緵瀛︿範銆佺鐮旇緟鍔╁拰涓汉绠＄悊浣跨敤銆傚叕寮€浼犳挱銆佸晢涓氫娇鐢ㄦ垨鍐嶅垎鍙戞椂锛岃鑷纭鍘熷璁烘枃鍜屾暟鎹潵婧愮殑璁稿彲瑕佹眰銆?- 鏈」鐩粛澶勪簬鏃╂湡闃舵锛屽彲鑳藉瓨鍦?bug銆佹暟鎹笉鍑嗙‘銆佹帴鍙ｅ彉鏇村鑷寸殑澶辫触鎴栨€ц兘闂锛岃璋ㄦ厧浣跨敤銆?
## 寮€鍙戦獙璇?
鍓嶇鏋勫缓锛?
```bash
cd frontend
npm run build
```

鍚庣娴嬭瘯锛?
```bash
cd backend
python -m unittest discover -s tests -v
```

## 璇存槑

鏈」鐩敤浜庢湰鍦拌鏂囨绱笌杈呭姪闃呰銆備笉鍚岃鏂囨潵婧愬彲鑳藉瓨鍦ㄨ闂鐜囬檺鍒躲€侀獙璇佺爜銆佺綉缁滀笉鍙揪鎴栨帴鍙ｅ彉鏇达紝鐖彇缁撴灉浼氬彈褰撳墠缃戠粶鐜褰卞搷銆?
