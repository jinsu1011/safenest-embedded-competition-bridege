const P = require('pptxgenjs');
const path = require('path');
// 이 스크립트(generator/)의 부모, 곧 final-report/ 를 기준으로 삼는다.
const OUT = path.resolve(__dirname, '..');
const A = OUT + '/assets', PV = OUT + '/previews';

const F = 'Apple SD Gothic Neo', M = 'Menlo';
const NAVY='1B2A41', INK='24303F', BLUE='2E6FB7', LBLUE='E8F0F9', RED='C0392B',
      AMBER='E08A1E', GREEN='2E7D5B', GREY='6B7280', LINE='D8DEE6', BG='FFFFFF', SOFT='F5F7FA';

const pptx = new P();
pptx.defineLayout({ name:'W16x9', width:13.333, height:7.5 });
pptx.layout = 'W16x9';
pptx.author='가만있어도SANDI'; pptx.company='경희대학교';
pptx.title='2026ESWContest 자유공모 가만있어도SANDI 개발완료보고서';

const SEC = {
  1:'Ⅰ. 개발 개요', 2:'Ⅰ. 개발 개요', 3:'Ⅰ. 개발 개요',
  4:'Ⅱ. 개발 환경 설명', 5:'Ⅱ. 개발 환경 설명',
  6:'Ⅲ. 개발 프로그램 설명', 7:'Ⅲ. 개발 프로그램 설명', 8:'Ⅲ. 개발 프로그램 설명',
  9:'Ⅲ. 개발 프로그램 설명', 10:'Ⅲ. 개발 프로그램 설명', 11:'Ⅲ. 개발 프로그램 설명',
  12:'Ⅳ. 장애요인과 해결방안', 13:'Ⅳ. 장애요인과 해결방안',
  14:'Ⅴ. 개발 결과물의 차별성', 15:'Ⅴ. 개발 결과물의 차별성', 16:'Ⅴ. 개발 결과물의 차별성',
  17:'Ⅵ. 파급력 및 기대효과', 18:'Ⅵ. 파급력 및 기대효과',
  19:'Ⅶ. 개발 일정 및 업무 분장', 20:'Ⅶ. 개발 일정 및 업무 분장'
};

function page(n, title, sub){
  const s = pptx.addSlide();
  s.background = { color: BG };
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:13.333, h:0.09, fill:{color:NAVY} });
  s.addText(SEC[n], { x:0.55, y:0.22, w:6.5, h:0.26, fontFace:F, fontSize:11.5, color:BLUE, bold:true, charSpacing:0.5 });
  s.addText(title, { x:0.55, y:0.50, w:12.23, h:0.60, fontFace:F, fontSize:23, bold:true, color:NAVY, valign:'top' });
  if (sub) s.addText(sub, { x:0.55, y:1.11, w:12.23, h:0.28, fontFace:F, fontSize:13.5, color:GREY, valign:'top' });
  const ly = sub ? 1.46 : 1.26;
  s.addShape(pptx.ShapeType.line, { x:0.55, y:ly, w:12.23, h:0, line:{color:LINE, width:1} });
  s.addText(String(n), { x:12.4, y:6.98, w:0.42, h:0.28, fontFace:F, fontSize:11, color:GREY, align:'right' });
  s.addText('SafeNest · 가만있어도SANDI', { x:0.55, y:6.98, w:5, h:0.28, fontFace:F, fontSize:9.5, color:GREY });
  return { s, y: ly + 0.12 };
}
function note(s, txt, y){
  s.addText(txt, { x:0.55, y:y||6.62, w:11.7, h:0.28, fontFace:F, fontSize:9.5, color:GREY });
}
function badge(s, x, y, label, kind){
  const map = { ok:[GREEN,'FFFFFF'], sw:[BLUE,'FFFFFF'], hw:[NAVY,'FFFFFF'], warn:[AMBER,'FFFFFF'], no:[RED,'FFFFFF'], grey:['9AA5B1','FFFFFF'] };
  const c = map[kind]||map.grey;
  s.addShape(pptx.ShapeType.roundRect, { x, y, w:1.32, h:0.30, fill:{color:c[0]}, rectRadius:0.14, line:{color:c[0]} });
  s.addText(label, { x, y, w:1.32, h:0.30, fontFace:F, fontSize:10, bold:true, color:c[1], align:'center', valign:'middle' });
}
function box(s, x,y,w,h, fill, line){
  s.addShape(pptx.ShapeType.roundRect, { x,y,w,h, fill:{color:fill||SOFT}, line:{color:line||LINE, width:1}, rectRadius:0.06 });
}
function sub(s, x, y, t){
  s.addText(t, { x, y, w:7, h:0.28, fontFace:F, fontSize:14.5, bold:true, color:NAVY, valign:'middle' });
}
function cap(s, x, y, w, t){
  s.addText(t, { x, y, w, h:0.26, fontFace:F, fontSize:9.5, color:GREY, align:'center' });
}
function down(s, x, y, w){
  s.addText('▼', { x, y, w, h:0.22, fontFace:F, fontSize:11, color:BLUE, align:'center' });
}
const TB = { fontFace:F, fontSize:12, color:INK, valign:'middle', border:{type:'solid',color:LINE,pt:0.5} };
function hdr(t){ return { text:t, options:{ bold:true, color:'FFFFFF', fill:{color:NAVY}, fontSize:12, align:'center' } }; }

/* ================= COVER ================= */
{
  const s = pptx.addSlide(); s.background={color:BG};
  s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:13.333,h:0.5,fill:{color:NAVY}});
  s.addShape(pptx.ShapeType.rect,{x:0,y:7.16,w:13.333,h:0.34,fill:{color:NAVY}});
  s.addText('제24회 임베디드SW경진대회 개발완료보고서',
    {x:1.0,y:1.55,w:11.3,h:0.5,fontFace:F,fontSize:22,color:GREY,align:'center'});
  s.addShape(pptx.ShapeType.roundRect,{x:5.42,y:2.22,w:2.5,h:0.42,fill:{color:LBLUE},line:{color:BLUE,width:1},rectRadius:0.2});
  s.addText('자 유 공 모 부 문',{x:5.42,y:2.22,w:2.5,h:0.42,fontFace:F,fontSize:13.5,bold:true,color:BLUE,align:'center',valign:'middle'});
  s.addText('SafeNest',{x:1.0,y:2.96,w:11.3,h:1.0,fontFace:F,fontSize:60,bold:true,color:NAVY,align:'center'});
  s.addText('엣지 AI 기반 밀폐공간·차량 생명감지 및 위험도 자동경보 시스템',
    {x:1.0,y:4.02,w:11.3,h:0.5,fontFace:F,fontSize:20,color:INK,align:'center'});
  s.addShape(pptx.ShapeType.line,{x:5.17,y:4.82,w:3.0,h:0,line:{color:LINE,width:1.5}});
  s.addText('가만있어도SANDI',{x:1.0,y:5.12,w:11.3,h:0.44,fontFace:F,fontSize:24,bold:true,color:NAVY,align:'center'});
  s.addText('경희대학교 전자공학과',{x:1.0,y:5.64,w:11.3,h:0.36,fontFace:F,fontSize:16,color:GREY,align:'center'});
  s.addText('김진수 · 유승하 · 김태균 · 한준우 · 강유나',
    {x:1.0,y:6.06,w:11.3,h:0.34,fontFace:F,fontSize:14,color:GREY,align:'center'});
}

/* ============ P1 ============ */
{
  const {s,y} = page(1,'1.1  밀폐공간 질식재해 현황과 개발 필요성');
  sub(s,0.55,y,'재해 통계 (최근 10년, 2014~2023)');
  s.addImage({ path: PV+'/chart_victims.png', x:0.62, y:y+0.34, w:3.05, h:2.62 });
  const st=[['174건','밀폐공간 질식재해 발생 건수'],['338명','재해자'],['136명','사망자'],['85.7%','검찰 송치 중대재해 중\n산소·유해가스 농도 미측정 상태에서 발생']];
  st.forEach((v,i)=>{
    const yy=y+0.36+i*0.66;
    box(s,4.05,yy,3.55,0.58,i===3?'FBE9E7':SOFT,i===3?RED:LINE);
    s.addText(v[0],{x:4.20,y:yy,w:1.15,h:0.58,fontFace:F,fontSize:20,bold:true,color:i===3?RED:NAVY,valign:'middle'});
    s.addText(v[1],{x:5.42,y:yy,w:2.05,h:0.58,fontFace:F,fontSize:i===3?9.5:11.5,color:INK,valign:'middle',lineSpacing:13});
  });
  box(s,7.85,y+0.34,4.93,2.62,SOFT,LINE);
  s.addText('제도와 현실의 간극',{x:8.05,y:y+0.44,w:4.5,h:0.28,fontFace:F,fontSize:13.5,bold:true,color:NAVY});
  const law=['산업안전보건법 제619조는 밀폐공간 작업 시 산소·유해가스 농도 측정과 감시인 배치를 사업주 의무로 규정한다.',
             '중대재해처벌법 확대 적용으로 소규모 사업장까지 예방 설비 수요가 늘었다.',
             '감시인 상시 배치가 어려운 소규모 사업장이 대다수여서, 사람의 상태까지 자동으로 확인하는 무인 감시 수단이 필요하다.'];
  law.forEach((t,i)=>{
    s.addText([{text:'· ',options:{bold:true,color:BLUE}},{text:t,options:{color:INK}}],
      {x:8.05,y:y+0.78+i*0.70,w:4.55,h:0.66,fontFace:F,fontSize:12,lineSpacing:17,valign:'top'});
  });
  sub(s,0.55,y+3.14,'사고 진행 단계와 현재 감시 수단의 공백');
  const fy=y+3.56;
  const flow=[['작업자 진입','밀폐공간 내부'],['이상 발생','산소결핍·유해가스'],['움직임 정지','스스로 신고 불가'],['발견 지연','감시인 부재'],['사고 확정','구조 골든타임 경과']];
  flow.forEach((f,i)=>{
    const x=0.55+i*2.47;
    box(s,x,fy+0.46,2.24,0.90, i>=2&&i<=3?'FBE9E7':LBLUE, i>=2&&i<=3?RED:BLUE);
    s.addText(f[0],{x,y:fy+0.54,w:2.24,h:0.30,fontFace:F,fontSize:13.5,bold:true,color:i>=2&&i<=3?RED:NAVY,align:'center'});
    s.addText(f[1],{x,y:fy+0.84,w:2.24,h:0.30,fontFace:F,fontSize:11,color:GREY,align:'center'});
    if(i<4) s.addText('▶',{x:x+2.26,y:fy+0.78,w:0.22,h:0.28,fontFace:F,fontSize:12,color:GREY,align:'center'});
  });
  s.addShape(pptx.ShapeType.roundRect,{x:5.49,y:fy,w:4.7,h:0.40,fill:{color:'FDF3E3'},line:{color:AMBER,width:1.25},rectRadius:0.06});
  s.addText('가스 감지기·PIR·CCTV가 사람의 상태를 놓치는 구간',{x:5.49,y:fy,w:4.7,h:0.40,fontFace:F,fontSize:11.5,bold:true,color:'9A5B0B',align:'center',valign:'middle'});
  s.addText('▼',{x:6.55,y:fy+0.36,w:0.3,h:0.16,fontFace:F,fontSize:9,color:AMBER,align:'center'});
  s.addText('▼',{x:8.85,y:fy+0.36,w:0.3,h:0.16,fontFace:F,fontSize:9,color:AMBER,align:'center'});
  s.addText('SafeNest는 이 구간에서 사람의 존재와 상태를 자동으로 확인하고 현장에 경보를 낸다.',
    {x:0.55,y:fy+1.46,w:12.23,h:0.30,fontFace:F,fontSize:13.5,bold:true,color:NAVY});
  note(s,'※ 출처 : 고용노동부 밀폐공간 질식재해 예방 보도자료(2024), 경향신문 밀폐공간 중대재해 분석 보도(2025). 법령 : 산업안전보건법 제619조.');
}

/* ============ P2 ============ */
{
  const {s,y} = page(2,'1.2  기존 감지 방식의 한계');
  const rows=[[hdr('감지 방식'),hdr('정지 인체'),hdr('사생활 보호'),hdr('착용 불필요'),hdr('환경 위험 감시'),hdr('한계')],
    ['가스 감지기','×','○','○','○','공기질만 측정하므로 사람의 존재를 알지 못한다'],
    ['CCTV','△','×','○','×','정지 인체 판별이 어렵고 사생활 침해 소지가 크다'],
    ['PIR 센서','×','○','○','×','움직일 때만 감지하여 쓰러진 사람을 놓친다'],
    ['웨어러블','○','○','×','×','착용과 충전에 의존하며 미착용 시 무력하다'],
    ['단일 mmWave','○','○','○','×','환경 위험을 모르고 비생체 반사와 구분이 어렵다'],
    ['단일 열화상','△','○','○','×','히터·기계 열원과 사람의 구분이 어렵다']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    const mk=(c==='○'||c==='×'||c==='△');
    return {text:c,options:{align:mk?'center':'left', bold:(mk||ci===0),
      fontSize:mk?15:12, color: mk?(c==='×'?RED:(c==='△'?AMBER:GREEN)):INK}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[1.95,1.30,1.40,1.40,1.55,4.63],rowH:0.46,...TB});
  sub(s,0.55,y+3.72,'공백의 성격');
  s.addText([
    {text:'여섯 가지 방식은 각각 다른 이유로 실패한다. 공통점은 하나다. ',options:{color:INK}},
    {text:'센서가 값을 내지 못하거나 값이 오래된 상황을 스스로 인지하지 못한다는 점이다.',options:{bold:true,color:NAVY}},
    {text:'\n그래서 값이 도착하지 않아도 시스템은 조용하고, 조용한 상태는 안전한 상태로 읽힌다. SafeNest는 서로 다른 성질의 증거를 함께 모으고, 그 증거를 지금 신뢰해도 되는지까지 판정하는 구조로 이 공백에 대응한다.',options:{color:INK}}
  ],{x:0.55,y:y+4.06,w:12.23,h:0.86,fontFace:F,fontSize:13.5,lineSpacing:21,valign:'top'});
  note(s,'○ 충족 · △ 조건부 충족 · × 미충족. 비교는 감지 방식의 범주를 기준으로 하며 특정 제품의 성능을 단정하지 않는다. 유사 제품과의 비교는 15페이지에 별도로 제시한다.');
}

/* ============ P3 ============ */
{
  const {s,y} = page(3,'1.3  개발 목표 및 시스템 구성');
  sub(s,0.55,y,'시스템 구성도');
  const D0=0.55, DW=7.05;
  const sen=[['mmWave\nMR60BHA2','UART2','resp_rate_bpm\nheart_rate_bpm'],
             ['Thermal-44\n(80×62)','I²C + SPI','thermal_max_c'],
             ['PIR','GPIO','pir_motion'],
             ['SCD40\n(CO₂)','I²C','co2_ppm']];
  let dy=y+0.38;
  sen.forEach((v,i)=>{
    const x=D0+i*1.79;
    box(s,x,dy,1.70,0.94,LBLUE,BLUE);
    s.addText(v[0],{x,y:dy+0.06,w:1.70,h:0.36,fontFace:F,fontSize:11.5,bold:true,color:NAVY,align:'center',lineSpacing:14});
    s.addText(v[1],{x,y:dy+0.44,w:1.70,h:0.20,fontFace:M,fontSize:9,color:BLUE,align:'center'});
    s.addText(v[2],{x,y:dy+0.64,w:1.70,h:0.28,fontFace:M,fontSize:8.5,color:GREY,align:'center',lineSpacing:11});
    down(s,x,dy+0.96,1.70);
  });
  dy+=1.22;
  box(s,D0,dy,DW,0.56,SOFT,NAVY);
  s.addText([{text:'ESP32 Dev Module',options:{bold:true,fontSize:13,color:NAVY}},
             {text:'   4센서 수집 · 유효성 판정 · 패킷화',options:{fontSize:11.5,color:INK}}],
    {x:D0,y:dy,w:DW,h:0.56,fontFace:F,align:'center',valign:'middle'});
  dy+=0.58;
  s.addText('▼   SafeNest TCP protocol v1  (16 B 헤더 · Wi-Fi · valid{} 동봉)',
    {x:D0,y:dy,w:DW,h:0.30,fontFace:F,fontSize:11,bold:true,color:BLUE,align:'center',valign:'middle'});
  dy+=0.32;
  box(s,D0,dy,DW,0.74,SOFT,NAVY);
  s.addText([{text:'Raspberry Pi 5',options:{bold:true,fontSize:13,color:NAVY}},
             {text:'\n유효성·신선도 재검사  →  INT8 TFLite 추론  →  Risk Engine 가중 융합',options:{fontSize:11.5,color:INK}}],
    {x:D0,y:dy,w:DW,h:0.74,fontFace:F,align:'center',valign:'middle',lineSpacing:17});
  dy+=0.76; down(s,D0,dy,DW); dy+=0.24;
  const lv=[['정상','R < 30',GREEN],['주의','30 ≤ R < 65',AMBER],['위험','R ≥ 65',RED],['판단 보류','증거 부족',GREY]];
  lv.forEach((v,i)=>{
    const x=D0+i*1.79;
    s.addShape(pptx.ShapeType.roundRect,{x,y:dy,w:1.70,h:0.50,fill:{color:v[2]},line:{color:v[2]},rectRadius:0.06});
    s.addText(v[0],{x,y:dy+0.02,w:1.70,h:0.26,fontFace:F,fontSize:11.5,bold:true,color:'FFFFFF',align:'center'});
    s.addText(v[1],{x,y:dy+0.26,w:1.70,h:0.22,fontFace:M,fontSize:9,color:'FFFFFF',align:'center'});
    down(s,x,dy+0.52,1.70);
  });
  dy+=0.78;
  const out=[['부저','GPIO18 · 880 Hz'],['LCD','상태 6종 표시'],['Web 관제','Express 5 · QR 공간코드']];
  out.forEach((v,i)=>{
    const x=D0+i*2.39;
    box(s,x,dy,2.30,0.52,LBLUE,BLUE);
    s.addText(v[0],{x,y:dy+0.03,w:2.30,h:0.26,fontFace:F,fontSize:12,bold:true,color:NAVY,align:'center'});
    s.addText(v[1],{x,y:dy+0.27,w:2.30,h:0.22,fontFace:F,fontSize:9.5,color:GREY,align:'center'});
  });

  sub(s,7.90,y,'개발 목표 (중간계획서 기준 초기 목표)');
  const goals=['① mmWave와 열화상 융합으로 정지 상태의 인체를 비영상 방식으로 감지한다.',
    '② 다중 센서 증거 융합과 온디바이스 AI로 정상·주의·위험 3단계를 자동 판단한다.',
    '③ 위험 감지 시 현장 경보·상태 표시·이벤트 기록을 자동 수행한다.',
    '④ Raspberry Pi 단일 노드 MVP를 완성하고 다중 노드로 확장 가능한 구조를 갖춘다.'];
  goals.forEach((g,i)=>{
    s.addText(g,{x:7.90,y:y+0.40+i*0.60,w:4.88,h:0.56,fontFace:F,fontSize:12,color:INK,lineSpacing:17,valign:'top'});
  });
  box(s,7.90,y+2.90,4.88,0.94,'FFFFFF',BLUE);
  s.addText('소스코드 (GitHub)',{x:8.10,y:y+2.98,w:4.5,h:0.24,fontFace:F,fontSize:11,bold:true,color:BLUE});
  s.addShape(pptx.ShapeType.line,{x:8.10,y:y+3.42,w:4.48,h:0,line:{color:LINE,width:1}});
  s.addText('시연동영상 (YouTube)',{x:8.10,y:y+3.48,w:4.5,h:0.24,fontFace:F,fontSize:11,bold:true,color:BLUE});
  s.addShape(pptx.ShapeType.line,{x:8.10,y:y+3.76,w:4.48,h:0,line:{color:LINE,width:1}});
  s.addText('SafeNest는 mmWave·열화상·PIR·CO₂ 센서의 서로 다른 정보를 결합하고, 각 값의 유효성과 신선도를 확인한 뒤 위험도를 판단하여 현장 경보와 화면으로 전달하는 임베디드 안전 시스템이다.',
    {x:7.90,y:y+4.02,w:4.88,h:0.98,fontFace:F,fontSize:12,color:INK,lineSpacing:17,valign:'top'});
  note(s,'표기 원칙 : 구현 완료 / SW 검증 / 실기기 검증 / 실기기 E2E / 미검증 을 구분해 표기한다. 초기 개발 목표와 달성 결과는 분리하며, 달성 여부는 16페이지 완성도 표에 증거 등급과 함께 제시한다.');
}

/* ============ P4 ============ */
{
  const {s,y} = page(4,'2.1  시스템 계층 구조 및 개발 환경');
  sub(s,0.55,y,'4계층 역할 분담');
  const lay=[['감지','MR60BHA2 · Thermal-44 · SCD40 · PIR'],
             ['수집·검증','ESP32 Dev Module. 버스 판독, valid·freshness 판정, CRC, 패킷화'],
             ['판단','Raspberry Pi 5. 센서 상태 관리, INT8 TFLite 추론, Risk Engine'],
             ['대응','부저·LCD·Web 관제. 등급별 경보와 상태 표시']];
  lay.forEach((L,i)=>{
    const yy=y+0.38+i*0.38;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.35,h:0.34,fill:{color:i%2?NAVY:BLUE},line:{color:i%2?NAVY:BLUE},rectRadius:0.05});
    s.addText(L[0],{x:0.55,y:yy,w:1.35,h:0.34,fontFace:F,fontSize:12,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    s.addText(L[1],{x:2.02,y:yy,w:10.76,h:0.34,fontFace:F,fontSize:12.5,color:INK,valign:'middle'});
  });
  sub(s,0.55,y+1.98,'개발 환경');
  const env=[[hdr('구분'),hdr('사용 기술'),hdr('대상 기기'),hdr('저장소 근거 경로')],
   ['MCU 펌웨어','Arduino / PlatformIO (C++)','ESP32 Dev Module','devices/esp32_node/firmware/'],
   ['수신·표시 서버','Python 3 표준 라이브러리 (http.server, socket, struct)','Raspberry Pi 5','integration/pi_lcd/server.py'],
   ['온디바이스 AI','TensorFlow Lite INT8 추론 / 학습·검증 TensorFlow 2.19.1','Raspberry Pi 5','ondevice_ai/inference/, models/'],
   ['위험도 엔진','Python, 규칙+플로어 융합','Raspberry Pi 5','RaspberryPi/Runtime/risk/formula_v1.py'],
   ['웹 관제','Node.js Express 5 (bcryptjs · jsonwebtoken · qrcode)','Raspberry Pi 5','integration/web/'],
   ['센서 계약','Python 추상 인터페이스','전 영역 공통','shared/contracts/base_sensor.py'],
   ['외함','3D CAD → STL 4종','FDM 출력','hardware/3d_models/']];
  s.addTable(env.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+2.34,w:12.23,colW:[1.85,4.75,2.15,3.48],rowH:0.36,...TB,fontSize:11.5});
  note(s,'저장소 전체 파일 수 1,904개 (패키징 시점 개발 스냅샷, commit 3f22fb1). 위 표는 개발 환경에 해당하는 구성만 발췌한 것이다.');
}

/* ============ P5 ============ */
{
  const {s,y} = page(5,'2.2  센서 구성 및 하드웨어 인터페이스');
  const pin=[[hdr('센서'),hdr('인터페이스'),hdr('ESP32 핀 / 주소'),hdr('수집 값')],
   ['MR60BHA2\n(mmWave)','UART2\n115200 bps','RX GPIO16 / TX GPIO17','호흡수, 심박수,\n재실, phase'],
   ['SCD40\n(CO₂)','I²C\n100 kHz','SDA 21 / SCL 22 / 0x62','co2_ppm'],
   ['PIR','GPIO 디지털 입력','GPIO 13 (20 ms 폴링)','pir_motion'],
   ['Thermal-44\n(MI48xx)','I²C 제어\n+ SPI 1 MHz','0x40 · 0x41 / SCLK18 MISO19\nMOSI23 CS27 READY26 RESET25','80×62 uint16\n프레임']];
  s.addTable(pin.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{bold:ci===0,color:ci===0?NAVY:INK}}:c)),
    {x:0.55,y:y+0.04,w:6.55,colW:[1.55,1.45,2.30,1.25],rowH:0.52,...TB,fontSize:10.5});
  sub(s,0.55,y+2.86,'설계상 중요한 점');
  const pts=['열화상 RESET(GPIO25)을 단독 핀으로 확보해 부팅 시퀀스와 무프레임 자동 재초기화를 구현하였다.',
             '브레드보드·점퍼 배선 환경을 고려해 SPI 1 MHz, I²C 100 kHz로 운용한다.',
             '실행 루프에서 delay()를 사용하지 않고 millis() 주기 판정과 FreeRTOS 네트워크 태스크로 분리하였다.',
             '10개 신호선이 서로 다른 버스에 물리므로 핀 상수를 펌웨어 상단에 모아 배선도와 1:1로 대응시켰다.'];
  pts.forEach((p,i)=>{
    s.addText([{text:'· ',options:{bold:true,color:BLUE}},{text:p,options:{color:INK}}],
      {x:0.58,y:y+3.22+i*0.48,w:6.52,h:0.44,fontFace:F,fontSize:12,lineSpacing:16,valign:'top'});
  });
  s.addImage({ path:A+'/hw_wiring_diagram.png', x:7.35, y:y+0.04, w:5.43, h:4.38 });
  s.addShape(pptx.ShapeType.rect,{x:7.35,y:y+0.04,w:5.43,h:4.38,fill:{type:'none'},line:{color:LINE,width:1}});
  cap(s,7.35,y+4.46,5.43,'[그림 1] ESP32 4센서 결선도. 좌측 표의 핀 배정과 1:1로 대응한다.');
  note(s,'근거 : devices/esp32_node/firmware/esp32_sensor_node.ino (741줄) 의 핀 상수 정의 PIN_*, SCD4X_ADDRESS, THERMAL_ADDRESS_A·B.');
}

/* ============ P6 ============ */
{
  const {s,y} = page(6,'3.1  소프트웨어 모듈 구성');
  const mod=[[hdr('경로'),hdr('역할'),hdr('입력 → 출력')],
   ['devices/esp32_node/firmware/\nesp32_sensor_node.ino','4센서 수집, 유효성 판정, 패킷화 (741줄)','센서 버스 → SafeNest TCP v1 패킷'],
   ['devices/{mmwave,co2,pir,thermal}/src/','센서별 어댑터, mock, 설정','원시 판독 → 공용 센서 계약'],
   ['shared/contracts/base_sensor.py','모든 영역이 의존하는 센서 계약','인터페이스 정의'],
   ['integration/pi_lcd/server.py','TCP 9000 수신, HTTP 8080 API, 상태 6종, 부저','패킷 → 상태·화면·경보'],
   ['ondevice_ai/inference/','TFLite Interpreter, 모델 레지스트리, 검증기','프레임·윈도우 → InferenceResult'],
   ['RaspberryPi/Runtime/risk/\nformula_v1.py','가중 융합 + 채널별 안전기준 플로어','센서·AI → risk_score / WARNING·DANGER'],
   ['ondevice_ai/integrated_node/run_node.py','통합 실행 노드, 외부 provider 주입','센서 provider → 위험도 출력'],
   ['integration/web/','Express 5 관제 웹, QR 생성, 시뮬레이터','상태 → 관리자·방문자 화면'],
   ['hardware/3d_models/','외함 CAD STL 4종 + 설계사양 2종','설계 → FDM 출력']];
  s.addTable(mod.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{fontFace:ci===0?M:F,fontSize:ci===0?10:11.5}}:c)),
    {x:0.55,y:y+0.04,w:12.23,colW:[4.25,4.30,3.68],rowH:0.355,...TB});
  box(s,0.55,y+3.72,12.23,1.32,SOFT,AMBER);
  s.addText('외부 오픈소스 및 데이터셋 고지 (대회 규정 제10조 ③)',{x:0.78,y:y+3.80,w:7,h:0.26,fontFace:F,fontSize:12,bold:true,color:'9A5B0B'});
  s.addText([
    {text:'데이터셋 : ',options:{bold:true,color:NAVY}},
    {text:'Zenodo mmWave vital-sign (DOI 10.5281/zenodo.18599983, CC BY 4.0) · UCI Occupancy Detection (ID 357, CC BY 4.0) · SDT Thermal (TU Wien / Zenodo 4124309, 라이선스 조건 확인 중)\n',options:{color:INK}},
    {text:'라이브러리 : ',options:{bold:true,color:NAVY}},
    {text:'TensorFlow Lite, Sensirion SCD4x, Seeed mmWave, Express 5, gpiozero, NumPy.  위 자산은 학습·추론·통신에 활용하였으며, 센서 통합 펌웨어와 통신 프로토콜, 상태 관리, 위험도 엔진은 팀 자체 구현이다.',options:{color:INK}}
  ],{x:0.78,y:y+4.06,w:11.77,h:0.92,fontFace:F,fontSize:11,lineSpacing:16,valign:'top'});
  note(s,'본 보고서의 저장소 경로는 패키징 시점 스냅샷(commit 3f22fb1) 기준이다. 이후 저장소를 기기 단위로 재편하여 현재 main 에서는 ESP32/ 와 RaspberryPi/ 아래에 있으며, 스냅샷 구조는 archive/legacy_main_repo/ 에 그대로 보존되어 있다.');
}

/* ============ P7 ============ */
{
  const {s,y} = page(7,'3.2  통신 프로토콜 설계','SafeNest TCP protocol v1. 모든 정수는 network byte order');
  sub(s,0.55,y,'16 B 고정 헤더 구조');
  const fields=[['magic','4 B','"SNST"',1],['version','1 B','1',0],['type','1 B','1=JSON, 2=열화상',0],
                ['flags','2 B','0',0],['sequence','4 B','uint32',0],['payload_length','4 B','uint32',1]];
  let px=0.55;
  fields.forEach((f,i)=>{
    const w=[1.55,1.25,1.85,1.25,1.55,2.35][i];
    box(s,px,y+0.38,w,0.86,f[3]?LBLUE:SOFT,f[3]?BLUE:LINE);
    s.addText(f[0],{x:px,y:y+0.44,w,h:0.26,fontFace:M,fontSize:11,bold:true,color:NAVY,align:'center'});
    s.addText(f[1],{x:px,y:y+0.70,w,h:0.22,fontFace:F,fontSize:10.5,color:BLUE,align:'center'});
    s.addText(f[2],{x:px,y:y+0.94,w,h:0.24,fontFace:F,fontSize:10,color:GREY,align:'center'});
    px+=w+0.06;
  });
  sub(s,0.55,y+1.42,'전송 흐름과 페이로드');
  const fl=['센서 판독','유효성 판정','SNST 16 B 헤더 + payload','TCP 9000 송신','Pi 수신·재검사'];
  fl.forEach((t,i)=>{
    const x=0.55+i*1.42;
    box(s,x,y+1.82,1.28,0.44,SOFT,LINE);
    s.addText(t,{x:x+0.04,y:y+1.82,w:1.20,h:0.44,fontFace:F,fontSize:10,color:INK,align:'center',valign:'middle',lineSpacing:12});
    if(i<4) s.addText('▶',{x:x+1.28,y:y+1.90,w:0.14,h:0.26,fontFace:F,fontSize:10,color:GREY,align:'center'});
  });
  box(s,7.60,y+1.82,2.55,0.44,SOFT,LINE);
  s.addText([{text:'Type 1  ',options:{bold:true,color:NAVY}},{text:'스칼라 JSON, 1초 주기',options:{color:INK}}],
    {x:7.60,y:y+1.82,w:2.55,h:0.44,fontFace:F,fontSize:10.5,align:'center',valign:'middle'});
  box(s,10.25,y+1.82,2.53,0.44,SOFT,LINE);
  s.addText([{text:'Type 2  ',options:{bold:true,color:NAVY}},{text:'열화상 프레임, 현재 비활성',options:{color:INK}}],
    {x:10.25,y:y+1.82,w:2.53,h:0.44,fontFace:F,fontSize:10.5,align:'center',valign:'middle'});
  box(s,0.55,y+2.40,6.05,1.30,SOFT,LINE);
  s.addText('Type 1 페이로드 (schema safenest.telemetry.v1)',{x:0.75,y:y+2.48,w:5.7,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('device_id · seq · uptime_ms\nresp_rate_bpm · heart_rate_bpm · co2_ppm\nthermal_max_c · pir_motion\nvalid { respiration, heart, co2, thermal }',
    {x:0.75,y:y+2.74,w:5.7,h:0.90,fontFace:M,fontSize:10.5,color:INK,lineSpacing:16});
  box(s,6.75,y+2.40,6.03,1.30,SOFT,LINE);
  s.addText('Type 2 규격 (12페이지의 구조 변경으로 전송 비활성)',{x:6.95,y:y+2.48,w:5.7,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('16 B 메타 (width 80, height 62, frame_sequence,\nuptime_ms, minimum_raw, maximum_raw)\n+ 4,960 × uint16 = 9,920 B\n→ payload 9,936 B / 패킷 9,952 B',
    {x:6.95,y:y+2.74,w:5.7,h:0.90,fontFace:M,fontSize:10.5,color:INK,lineSpacing:16});
  sub(s,0.55,y+3.80,'무효값 처리');
  s.addText('void formatNullableFloat(char *output, size_t outputSize, bool valid, float value) {\n  if (valid && isfinite(value)) snprintf(output, outputSize, "%.2f", value);\n  else                          strlcpy(output, "null", outputSize);   // 0으로 대체하지 않는다\n}',
    {x:0.55,y:y+4.16,w:8.35,h:0.86,fontFace:M,fontSize:10,color:INK,lineSpacing:16});
  s.addText('0 ppm과 측정 실패를 같은 숫자로 보내면 수신 측은 둘을 구분할 수 없다. 값과 valid 플래그를 함께 보내야 판단 계층이 결측을 정상값으로 오해하지 않는다.',
    {x:9.05,y:y+4.16,w:3.73,h:0.86,fontFace:F,fontSize:11,color:INK,lineSpacing:15,valign:'top'});
  note(s,'근거 : esp32_sensor_node.ino 프로토콜 정의 L113–124, formatNullableFloat L546–553 · integration/pi_lcd/server.py 의 PACKET_HEADER, recv_exact.');
}

/* ============ P8 ============ */
{
  const {s,y} = page(8,'3.3  센서 유효성 및 신선도 검사');
  sub(s,0.55,y,'수신부터 상태 확정까지');
  const steps=[['패킷 수신','recv_exact()로 헤더 16 B를 읽고\npayload_length 만큼 정확히 수신'],
               ['형식 검사','magic·version·flags 확인\npayload > 20,000 B 이면 연결 종료'],
               ['스키마 검사','safenest.telemetry.v1 확인\nvalid{} 객체 존재 확인'],
               ['신선도 검사','ESP32 : mmWave 5 s / CO₂ 15 s / 열화상 30 s\nPi : 5 s 독립 판정'],
               ['상태 확정','LIVE · STALE · INVALID\nDISCONNECTED · WAITING']];
  steps.forEach((st,i)=>{
    const x=0.55+i*2.47;
    box(s,x,y+0.38,2.26,1.18,i===4?LBLUE:SOFT,i===4?BLUE:LINE);
    s.addText(st[0],{x,y:y+0.46,w:2.26,h:0.28,fontFace:F,fontSize:12.5,bold:true,color:NAVY,align:'center'});
    s.addText(st[1],{x:x+0.09,y:y+0.76,w:2.08,h:0.72,fontFace:F,fontSize:10,color:INK,align:'center',lineSpacing:14});
    if(i<4) s.addText('▶',{x:x+2.28,y:y+0.86,w:0.18,h:0.26,fontFace:F,fontSize:12,color:GREY,align:'center'});
  });
  sub(s,0.55,y+1.74,'열화상 프레임 무결성 검사');
  const ig=[[hdr('검사'),hdr('방법'),hdr('불합격 시 처리'),hdr('구현 위치')],
   ['CRC-16/CCITT-FALSE','poly 0x1021, init 0xFFFF 로 계산해 헤더 기록값과 대조','프레임 폐기','thermalFrameCrc()'],
   ['헤더 범위 재계산','min/max 를 픽셀에서 다시 계산해 헤더 값과 대조','프레임 폐기','server.py'],
   ['시퀀스 교차 확인','외부 헤더 sequence 와 내부 frame_sequence 일치 확인','프레임 폐기','server.py'],
   ['죽은 화소 배제','raw 2332–4231 (약 −40~150 ℃) 범위 밖 화소 제외','사용 가능 화소 32개 미만이면 폐기','.ino / server.py'],
   ['무프레임 자동 복구','30 s 무프레임 시 GPIO RESET LOW 20 ms → HIGH 300 ms','센서 재초기화','recoverThermalIfStale()']];
  s.addTable(ig.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+2.14,w:12.23,colW:[2.35,5.25,2.55,2.08],rowH:0.375,...TB,fontSize:11});
  s.addText([{text:'설계 원칙 : ',options:{bold:true,color:NAVY}},
    {text:'센서가 정해진 시간 안에 갱신되지 않으면 해당 입력을 STALE로 분리하고, 마지막 정상값을 현재 증거로 다시 쓰지 않는다. 유효하지 않은 증거는 판단에서 제외하며 0으로 대체하지 않는다.',options:{color:INK}}],
    {x:0.55,y:y+4.62,w:12.23,h:0.50,fontFace:F,fontSize:13,lineSpacing:19,valign:'top'});
  note(s,'검증 : 본 문서 작성 시점에 integration/pi_lcd 테스트 13건을 실행해 전부 통과하였다. 부분 수신, 잘못된 헤더, 시퀀스 불일치, 신선도 판정이 포함된다.');
}

/* ============ P9 ============ */
{
  const {s,y} = page(9,'3.4  온디바이스 AI 모델 구성과 검증 범위');
  const m=[[hdr('기능'),hdr('모델'),hdr('입력 → 출력'),hdr('양자화'),hdr('검증 범위'),hdr('상태')],
   ['열화상 기반\n인체 자세 분석','thermal_fall_int8\nv0.1.0','62×80×1 프레임 → 3-class\nNOT_HUMAN / HUMAN_NORMAL / HUMAN_FALL','full INT8\n318 KB','실제 Thermal 프레임 → Raspberry Pi 5\n→ 실제 INT8 TFLite E2E 관통','허용'],
   ['CO₂ 기반\n재실 분석','co2_occupancy_int8\nv0.1.0','CO₂ slope · 습도 · ppm → 2-class\nVACANT / OCCUPIED','full INT8\n4.4 KB','공개 데이터셋 기반 오프라인 검증\n(실센서 평가 미수행)','허용\n(제한)'],
   ['mmWave 기반\n호흡 패턴 분석','mmwave_resp_int8\nv0.1.0','300샘플 30 s 창 → 3-class\nNORMAL / RAPID / APNEA','full INT8\n466 KB','재현 검증에서 클래스 붕괴 확인\nacc 0.3996 · macro-F1 0.19 · recall 0.0','차단'],
   ['mmWave 기반\n호흡 패턴 분석','mmwave_resp_int8\nv0.2.0 후보','동일','full INT8\n22 KB','합성 데이터 468샘플 한정 smoke\n실센서 성능 검증 불가','후보']];
  s.addTable(m.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+0.04,w:9.35,colW:[1.55,1.60,2.75,1.00,2.30,0.95],rowH:0.70,...TB,fontSize:10});
  badge(s,10.02,y+0.74,'실기기 E2E','hw');
  badge(s,10.02,y+1.44,'오프라인','sw');
  badge(s,10.02,y+2.14,'배포 차단','no');
  badge(s,10.02,y+2.84,'합성 한정','warn');
  box(s,11.50,y+0.04,1.28,3.38,SOFT,LINE);
  s.addText('열화상 채널\n실기기 실측',{x:11.58,y:y+0.14,w:1.12,h:0.48,fontFace:F,fontSize:11.5,bold:true,color:NAVY,align:'center',lineSpacing:15});
  s.addText('Raspberry Pi 5\n30.06 s · 138회',{x:11.58,y:y+0.64,w:1.12,h:0.36,fontFace:F,fontSize:9,color:GREY,align:'center',lineSpacing:12});
  const lat=[['p50','162.70 ms'],['p95','173.90 ms'],['평균','167.92 ms'],['유효 프레임','135/138'],['처리량','4.6 FPS']];
  lat.forEach((l,i)=>{
    s.addText(l[0],{x:11.58,y:y+1.08+i*0.44,w:1.12,h:0.20,fontFace:F,fontSize:9.5,color:GREY,align:'center'});
    s.addText(l[1],{x:11.58,y:y+1.26+i*0.44,w:1.12,h:0.24,fontFace:F,fontSize:11,bold:true,color:NAVY,align:'center'});
  });
  s.addText('※ 네트워크 수신 + 추론 포함, 열화상 채널 한정',{x:11.50,y:y+3.46,w:1.28,h:0.34,fontFace:F,fontSize:8,color:GREY,align:'center',lineSpacing:11});
  box(s,0.55,y+3.62,12.23,1.10,'FDF3E3',AMBER);
  s.addText('표현 범위',{x:0.78,y:y+3.70,w:5,h:0.26,fontFace:F,fontSize:12,bold:true,color:'9A5B0B'});
  s.addText('① HUMAN_FALL 은 눕기(LYING) 정적 자세의 프록시이며 시간축 낙상 사건을 검증한 결과가 아니다.\n② 열화상이 산출하는 값은 표면 온도이며 의료용 체온이 아니다.   ③ mmWave 호흡 관련 신호는 임상 진단 목적이 아니다.   ④ v0.2.0 후보의 합성 데이터 정확도 1.0은 실센서 성능이 아니다.',
    {x:0.78,y:y+3.98,w:11.77,h:0.66,fontFace:F,fontSize:11.5,color:INK,lineSpacing:18,valign:'top'});
  note(s,'근거 : ondevice_ai/models/model_manifest.json · 03_Evidence/Thermal/phase4_6_inference_report.md · phase11_12_fail_closed_benchmark.md');
}

/* ============ P10 ============ */
{
  const {s,y} = page(10,'3.5  위험도 산출과 안전기준');
  s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:y+0.00,w:12.23,h:0.46,fill:{color:LBLUE},line:{color:BLUE,width:1},rectRadius:0.06});
  s.addText('R = 100 × ( 0.25 · mmWave + 0.30 · CO₂ + 0.15 · PIR + 0.30 · Thermal )     정상 R < 30  ·  주의 30 ≤ R < 65  ·  위험 R ≥ 65',
    {x:0.55,y:y+0.00,w:12.23,h:0.46,fontFace:F,fontSize:12,bold:true,color:NAVY,align:'center',valign:'middle'});
  badge(s,11.46,y+0.52,'SW 검증','sw');
  sub(s,0.55,y+0.50,'채널별 안전기준. 플로어가 가중합보다 등급을 올릴 수 있다');
  const pol=[[hdr('채널'),hdr('주의 플로어'),hdr('즉시 위험'),hdr('점수에 넣는 방식')],
    ['CO₂','≥ 1,500 ppm 또는 기준값+700 ppm\n상승 ≥ 15 ppm/min','≥ 5,000 ppm 비상\n2,500 ppm 은 주의 유지','ppm 곡선. occupancy 모델은 제외'],
    ['열화상','HUMAN_FALL_PROXY 점수 0.4\n비상 없음','HUMAN_FALL 신뢰도 ≥ 0.8\n현재 모델은 프록시만 출력','눕기 자세 프록시. 낙상 사건 검증 전'],
    ['mmWave','미검증 APNEA 2회 연속\n호흡 10–24 rpm 이탈 지속','하드웨어 확인 apnea 만','신경망은 관측 전용. 스펙트럼 호흡수 우선'],
    ['PIR','재실 확인 후 180 s 무움직임','해당 없음','재실 미확인이면 비가용 (0점으로 채우지 않음)']];
  s.addTable(pol.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{bold:ci===0,color:ci===0?NAVY:INK,align:ci===0?'center':'left'}}:c)),
    {x:0.55,y:y+0.82,w:12.23,colW:[1.45,3.55,3.55,3.68],rowH:0.40,...TB,fontSize:10.5});
  sub(s,0.55,y+2.90,'계산 예시 : CO₂ 1,500 ppm, 사람 상태는 평온');
  box(s,0.55,y+3.24,7.35,1.36,SOFT,LINE);
  s.addText([
    {text:'입력   ',options:{bold:true,color:NAVY}},
    {text:'호흡 16 rpm · CO₂ 1,500 ppm (성분 0.325) · 움직임 있음 · 열화상 HUMAN_NORMAL\n',options:{color:INK}},
    {text:'가중합   ',options:{bold:true,color:NAVY}},
    {text:'R = 100 × (0.25×0 + 0.30×0.325 + 0.15×0 + 0.30×0) = ',options:{color:INK}},
    {text:'9.75  →  점수 등급 정상\n',options:{bold:true,color:GREEN}},
    {text:'플로어   ',options:{bold:true,color:NAVY}},
    {text:'co2_warning  →  ',options:{color:INK}},
    {text:'주의',options:{bold:true,color:AMBER}},
    {text:'   · 비상 아님 · mmWave 신경망 관측 전용이라 health = DEGRADED',options:{color:GREY}}
  ],{x:0.75,y:y+3.32,w:6.95,h:1.20,fontFace:F,fontSize:11,lineSpacing:17,valign:'top'});
  box(s,8.10,y+3.24,4.68,1.36,'FFFFFF',RED);
  s.addText('fail-closed (formula_v1.py)',{x:8.30,y:y+3.32,w:4.3,h:0.22,fontFace:F,fontSize:11,bold:true,color:RED});
  s.addText('전 채널 무효 → score·level = None\n유효 가중치 < 0.5 이고 정상이면\nINDETERMINATE (정상으로 채우지 않음)\n점수가 낮아도 플로어가 주의를 올린다',
    {x:8.30,y:y+3.56,w:4.3,h:0.96,fontFace:F,fontSize:11,color:INK,lineSpacing:16});
  s.addText([
    {text:'임계값의 근거   ',options:{bold:true,color:NAVY}},
    {text:'1,500 ppm 은 별표2 비고(자연환기 불가+기계환기)이며 기본 유지기준은 1,000 ppm 이다. 5,000 ppm 은 OSHA/NIOSH 8h TWA와 같은 값이며 순간 비상으로 쓴다. 제618조 적정공기는 15,000 ppm.  ',options:{color:INK}},
    {text:'인증 준수 주장은 하지 않는다. 출처는 docs/09_SAFETY_CRITERIA_V1.md.',options:{bold:true,color:RED}}
  ],{x:0.55,y:y+4.70,w:12.23,h:0.52,fontFace:F,fontSize:11,lineSpacing:16,valign:'top'});
  note(s,'계산 예시는 RaspberryPi/Runtime/risk/formula_v1.py 실행 값. 검증 : tests/test_risk_formula_v1.py. occupancy 로컬라이징은 본 식에서 제외한다.');
}

/* ============ P11 ============ */
{
  const {s,y} = page(11,'3.6  실측 검증 결과','서로 다른 조건에서 채널별로 수행하였으며, 통합 시스템 성능으로 합산하지 않는다');
  sub(s,0.55,y,'① CO₂ 센서 연속 수신 검증');
  s.addText('ESP32 192.168.1.16 → Pi 5 192.168.1.44:9000, TCP 실경로, 2026-08-12',
    {x:3.05,y:y+0.02,w:3.55,h:0.26,fontFace:F,fontSize:9.5,color:GREY,valign:'middle'});
  s.addImage({ path: PV+'/chart_co2.png', x:0.55, y:y+0.34, w:6.03, h:2.48 });
  const co2=[[hdr('세션'),hdr('유효 표본'),hdr('결측률'),hdr('판정')],
    ['프리플라이트 30초','30 / 30','0 %','PASS'],
    ['baseline 5분 (최초)','277 / 300','7.67 %','FAIL'],
    ['baseline 5분 (재측정)','300 / 300','0 %','PASS'],
    ['호기 6분','329 / 360','8.61 %','PASS']];
  s.addTable(co2.map(r=>r.map(c=>typeof c==='string'?{text:c,options:{align:c==='PASS'||c==='FAIL'?'center':'left',
    bold:c==='PASS'||c==='FAIL', color:c==='FAIL'?RED:(c==='PASS'?GREEN:INK)}}:c)),
    {x:0.55,y:y+2.92,w:6.03,colW:[2.34,1.40,1.19,1.10],rowH:0.32,...TB,fontSize:11});
  s.addText('최초 baseline 의 결측은 채우거나 삭제하지 않고 원본을 실패 증거로 보존한 뒤 재측정하였다. 호기 세션 최고 1,493 ppm, 종료 634 ppm.',
    {x:0.55,y:y+4.60,w:6.03,h:0.52,fontFace:F,fontSize:11,color:INK,lineSpacing:16,valign:'top'});

  sub(s,6.85,y,'② mmWave 수신 안정성 및 리플레이 결과');
  s.addImage({ path: PV+'/chart_mmwave.png', x:6.85, y:y+0.34, w:5.93, h:1.98 });
  box(s,6.85,y+2.42,5.93,0.92,SOFT,LINE);
  s.addText('라이브 UART 수신 (2026-08-08)',{x:7.03,y:y+2.48,w:5.6,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('9.990 Hz · 1,201 레코드 · 199/199 창 파싱 · 시퀀스 누락 0 · UART / checksum / parser 오류 0 / 0 / 0',
    {x:7.03,y:y+2.72,w:5.6,h:0.56,fontFace:F,fontSize:11,color:INK,lineSpacing:17,valign:'top'});
  sub(s,6.85,y+3.46,'③ Thermal 실기기 End-to-End');
  box(s,6.85,y+3.82,5.93,1.58,SOFT,LINE);
  s.addText('Raspberry Pi 5, 30.06 s / 138회 측정',{x:7.03,y:y+3.88,w:5.6,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('p50 162.70 ms · p95 173.90 ms · 평균 167.92 ms\n유효 프레임 135 / 138 (97.8 %) · 처리량 4.6 FPS\nfail-closed 6종(순서위반 · NaN/Inf · 형식오류 · 물리적 단선 · 복구 · close 후 read) 실기기 PASS',
    {x:7.03,y:y+4.12,w:5.6,h:1.22,fontFace:F,fontSize:11,color:INK,lineSpacing:17,valign:'top'});
  note(s,'ESP32 펌웨어 빌드 자원 : RAM 32,356 / 327,680 B (9.9 %), Flash 268,765 / 1,310,720 B (20.5 %).  4센서 동시 수신 로그는 아직 확보하지 않았다 [추가 검증 필요].');
}

/* ============ P12 ============ */
{
  const {s,y} = page(12,'4.1  열화상 전송 구조 개선');
  const st=[
    ['문제', '열화상 프레임을 계속 전송하면 1초 주기 telemetry(호흡·심박·CO₂·PIR)가 밀린다. 화면 값이 갱신되지 않거나 stale 로 떨어졌다.', RED],
    ['원인', '패킷 하나가 9,952 B (메타 16 B + 4,960 × 2 B + 헤더 16 B). 당시 분주비 4로 25 FPS 센서에서 초당 약 6.25 프레임을 요청하여 약 60 KB/s 를 ESP32 Wi-Fi 단일 TCP 연결에 투입하였다. 열화상 write 가 블로킹되면 뒤의 telemetry write 도 함께 지연된다.', NAVY],
    ['시도', '① TCP write 를 별도 FreeRTOS 태스크로 분리   ② 열화상 큐를 길이 1로 두고 xQueueOverwrite 로 최신 프레임만 유지   ③ 512 B 청크 분할 전송   ④ 분주비 4 → 8 (약 3.125 FPS)   ⑤ SPI 8 MHz → 1 MHz', GREY],
    ['실패', '수집이 네트워크 때문에 멈추는 현상은 사라졌지만, 스트리밍을 켠 상태에서 1초 주기는 여전히 유지되지 않았다. 큐를 줄인 것은 지연을 감춘 것이지 전송량을 줄인 것이 아니었다. 링크에 실리는 총 바이트는 그대로였다.', AMBER],
    ['해결', 'THERMAL_STREAM_FRAMES = false 로 전환하였다. 프레임을 보내는 대신 ESP32 가 그 자리에서 요약한다. 측정 범위 밖 죽은 화소를 제외하고, 살아 있는 화소가 32개 이상일 때 가장 뜨거운 16개 중 최저값을 골라 thermal_max_c 하나로 환산해 1초 telemetry 에 싣는다.', GREEN]];
  st.forEach((r,i)=>{
    const yy=y+0.02+i*0.72;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.05,h:0.66,fill:{color:r[2]},line:{color:r[2]},rectRadius:0.06});
    s.addText(r[0],{x:0.55,y:yy,w:1.05,h:0.66,fontFace:F,fontSize:13,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.68,yy,11.10,0.66,i===4?'EAF5EF':SOFT,i===4?GREEN:LINE);
    s.addText(r[1],{x:1.86,y:yy,w:10.74,h:0.66,fontFace:F,fontSize:12,color:INK,valign:'middle',lineSpacing:16.5});
  });
  const yy=y+3.74;
  box(s,0.55,yy,6.05,1.10,'FBE9E7',RED);
  s.addText('개선 전',{x:0.75,y:yy+0.08,w:2,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:RED});
  s.addText('type 2 패킷 9,952 B 를 초당 약 6.25회 전송 시도\n→ 1초 telemetry 주기 붕괴, 화면 값 지연',
    {x:0.75,y:yy+0.34,w:5.65,h:0.68,fontFace:F,fontSize:11.5,color:INK,lineSpacing:17});
  box(s,6.73,yy,6.05,1.10,'EAF5EF',GREEN);
  s.addText('개선 후',{x:6.93,y:yy+0.08,w:2,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:GREEN});
  s.addText('type 2 전송 없음. telemetry JSON 1개(상한 512 B)로 1초 주기 유지\n대신 LCD 열화상 영상은 제외하였고, 프레임 자체는 별도 리그에서만 검증한다.',
    {x:6.93,y:yy+0.34,w:5.65,h:0.68,fontFace:F,fontSize:11.5,color:INK,lineSpacing:17});
  s.addText('배운 점 : 대역폭이 한정된 링크에서는 판정에 필요한 최소 정보를 송신 측에서 뽑아 보내야 한다. 9,936 B 프레임에서 실제 판정에 쓰인 정보는 최고온도 하나였다.',
    {x:0.55,y:y+5.06,w:12.23,h:0.34,fontFace:F,fontSize:12,color:NAVY,bold:true,valign:'top'});
  note(s,'근거 : esp32_sensor_node.ino 의 THERMAL_STREAM_FRAMES, THERMAL_FRAME_RATE_DIVIDER, xQueueOverwrite 사용부.', 6.66);
}

/* ============ P13 ============ */
{
  const {s,y} = page(13,'4.2  자원·버스·재현성 장애요인');
  const cases=[
    ['① GPIO 자원 제약으로 자동 복구 기능이 막힌 문제', 1.52, NAVY,
     'XIAO ESP32-C6 의 외부 디지털 핀 11개 중 D6/D7 은 보드 내부에서 MR60BHA2 와 UART 로 묶여 외부 사용이 불가능하고, D3 은 레이더 부트·리셋 회로에, D1 은 온보드 RGB LED 에 물려 있었다.',
     'nRESET 을 연결하지 않는 방안을 시도하였으나, 초기화가 I²C 주소를 찾기 전에 RESET 을 LOW 20 ms → HIGH 300 ms 로 토글해야 해서 부팅 시퀀스가 성립하지 않았다. 사람이 버튼을 눌러야 복구되는 장치는 무인 감시에 쓸 수 없다.',
     'ESP32 DevKit V1(30-pin)으로 교체하고 10개 신호선을 모두 단독 핀에 배정하였다. RESET(GPIO25) 제어를 확보하여 30초 무프레임 자동 재초기화가 동작한다.'],
    ['② 브레드보드 배선이 버스 속도를 견디지 못한 문제', 1.26, NAVY,
     'SPI 8 MHz, I²C 400 kHz 에서 MI48 과 SCD4x 양쪽에서 판독 누락이 재현되었다. 배선을 다시 꽂고 길이를 줄여도 동일하였다.',
     '속도를 낮추면 프레임 판독 시간이 늘어 요청 주기를 넘길 위험이 있었으므로, 시간 예산 안에 들어오는지를 함께 계산해야 했다.',
     'SPI 1 MHz, I²C 100 kHz 로 조정하였다. 1 MHz 에서 한 프레임 판독이 약 81 ms 로, 분주비 8이 요구하는 160 ms 예산 안에 들어가 READOUT_TOO_SLOW 정지가 사라졌다.'],
    ['③ 학습이 끝난 모델이 재현 검증을 통과하지 못한 문제', 1.52, RED,
     'mmWave 호흡 이상 분류 모델 v0.1.0 을 저장소 데이터로 재현 평가한 결과, 468개 표본 전부를 NORMAL 로 예측하는 클래스 붕괴가 확인되었다. 정확도 0.3996, macro-F1 0.19, RAPID·APNEA 재현율 0.0 이다.',
     '아티팩트는 존재하였고 SHA-256 과 텐서 계약도 일치하였다. 모델 파일이 있다는 것이 검증을 통과했다는 뜻은 아니라는 사실이 드러났다.',
     '매니페스트에 deployment_allowed = false 와 차단 사유 CLASS_COLLAPSE_ON_REPOSITORY_NPZ 를 기록해 배포를 차단하고 후보를 다시 세웠다. 안전 판단 경로에 검증되지 않은 모델을 올리지 않는 것을 우선하였다.']];
  let cy=y+0.04;
  cases.forEach((c)=>{
    const H=c[1];
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:cy,w:12.23,h:0.36,fill:{color:c[2]}});
    s.addText(c[0],{x:0.72,y:cy,w:12,h:0.36,fontFace:F,fontSize:12.5,bold:true,color:'FFFFFF',valign:'middle'});
    const labs=['문제·원인','시도·실패','해결'];
    for(let k=0;k<3;k++){
      const x=0.55+k*4.13;
      box(s,x,cy+0.40,3.86,H-0.44,k===2?'EAF5EF':SOFT,k===2?GREEN:LINE);
      s.addText(labs[k],{x:x+0.14,y:cy+0.45,w:2,h:0.22,fontFace:F,fontSize:10,bold:true,color:k===2?GREEN:GREY});
      s.addText(c[k+3],{x:x+0.14,y:cy+0.66,w:3.58,h:H-0.72,fontFace:F,fontSize:10.5,color:INK,lineSpacing:14.5,valign:'top'});
    }
    cy+=H+0.14;
  });
  s.addText('세 번째 사례가 특히 중요하다. 성능이 나오지 않은 모델을 팀이 스스로 찾아내 배포를 차단한 것은, 검증되지 않은 구성요소를 안전 경로에 올리지 않는다는 원칙을 실제로 적용한 결과다.',
    {x:0.55,y:cy+0.02,w:12.23,h:0.44,fontFace:F,fontSize:12,bold:true,color:NAVY,lineSpacing:18,valign:'top'});
  note(s,'근거 : esp32_sensor_node.ino (핀 상수 · THERMAL_SPI_HZ · Wire.setClock · recoverThermalIfStale) · ondevice_ai/models/model_manifest.json (validation_status: BLOCKED).', 6.66);
}

/* ============ P14 ============ */
{
  const {s,y} = page(14,'5.1  기술적 차별성');
  const big=[
    ['fail-closed 판단 보류','증거가 무효이거나 결측이면 마지막 정상값을 재사용하지 않는다. 네 채널이 모두 무효이면 위험도를 산출하지 않고 risk_score 와 risk_level 을 None 으로 두며 system_health 를 FAILED 로 기록한다. 침묵을 안전의 증거로 삼지 않는다.','RaspberryPi/Runtime/risk/formula_v1.py','SW 검증','sw'],
    ['유효성·신선도의 1급 상태 관리','값과 함께 valid 플래그를 전송하며, 유효하지 않은 수치는 0으로 대체하지 않고 null 로 보낸다. ESP32 와 Raspberry Pi 가 신선도를 각각 독립적으로 판정하고, STALE 입력은 판단에서 제외한다.','formatNullableFloat() · SensorStore','SW 검증','sw'],
    ['카메라 없는 이종 센서 증거 융합','영상 센서를 쓰지 않는다. mmWave 의 미세 움직임, 열화상의 저해상도 열 분포, CO₂ 의 환경 추세, PIR 의 움직임 이벤트가 서로 다른 실패 모드를 상쇄한다. 열화상은 80×62 해상도로 개인 식별용 영상이 아니다.','RaspberryPi/Runtime/risk/formula_v1.py','SW 검증','sw']];
  big.forEach((r,i)=>{
    const yy=y+0.06+i*1.22;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:0.56,h:1.12,fill:{color:BLUE},line:{color:BLUE},rectRadius:0.06});
    s.addText(String(i+1),{x:0.55,y:yy,w:0.56,h:1.12,fontFace:F,fontSize:20,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.19,yy,7.11,1.12,SOFT,LINE);
    s.addText(r[0],{x:1.36,y:yy+0.10,w:2.86,h:0.58,fontFace:F,fontSize:13,bold:true,color:NAVY,valign:'top',lineSpacing:17});
    s.addText(r[2],{x:1.36,y:yy+0.72,w:2.86,h:0.26,fontFace:M,fontSize:8.5,color:BLUE,valign:'middle'});
    s.addText(r[1],{x:4.34,y:yy+0.06,w:3.80,h:1.00,fontFace:F,fontSize:10.5,color:INK,lineSpacing:15,valign:'middle'});
  });
  const small=[['검증 등급에 따른 배포 통제','모델마다 검증 범위와 배포 허용 여부를 매니페스트에 기록한다. 재현 검증에 실패한 모델은 실제로 배포가 차단되었다.','models/model_manifest.json','오프라인 검증','warn'],
               ['프레임 무결성과 자동 복구','CRC-16/CCITT-FALSE 검사, 헤더 범위 재계산, 시퀀스 교차 확인을 거치며 30초 무프레임 시 GPIO RESET 으로 센서를 재초기화한다.','thermalFrameCrc() · recoverThermalIfStale()','실기기 검증','hw']];
  small.forEach((r,i)=>{
    const yy=y+3.86+i*0.76;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:0.56,h:0.66,fill:{color:'9AA5B1'},line:{color:'9AA5B1'},rectRadius:0.06});
    s.addText(String(i+4),{x:0.55,y:yy,w:0.56,h:0.66,fontFace:F,fontSize:14,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.19,yy,7.11,0.66,'FFFFFF',LINE);
    s.addText(r[0],{x:1.36,y:yy,w:2.50,h:0.66,fontFace:F,fontSize:11.5,bold:true,color:NAVY,valign:'middle',lineSpacing:15});
    s.addText(r[1],{x:3.98,y:yy,w:4.16,h:0.66,fontFace:F,fontSize:10,color:INK,valign:'middle',lineSpacing:13.5});
  });
  [...big,...small].forEach((r,i)=>{
    const yy = i<3 ? y+0.47+i*1.22 : y+4.04+(i-3)*0.76;
    badge(s,8.44,yy,r[3],r[4]);
  });
  s.addImage({ path:A+'/ui_lcd_6_failed.jpg', x:9.90, y:y+0.06, w:2.88, h:1.66 });
  s.addShape(pptx.ShapeType.rect,{x:9.90,y:y+0.06,w:2.88,h:1.66,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 2] 전 센서 무효 시 표시 화면. 정상으로 표시하지 않고 점검 필요 상태를 출력한다. 표시 계층 검증용 시나리오 화면이며 실센서 측정값이 아니다.',
    {x:9.90,y:y+1.78,w:2.88,h:1.00,fontFace:F,fontSize:9.5,color:GREY,lineSpacing:13,valign:'top'});
  note(s,'각 항목은 03_CLAIM_EVIDENCE_LEDGER 의 근거 파일과 1:1로 연결되어 있으며, 근거가 확인되지 않은 주장은 포함하지 않았다.', 6.62);
}

/* ============ P15 ============ */
{
  const {s,y} = page(15,'5.2  기존 방식 및 유사 사례 비교');
  const rows=[[hdr('비교 축'),hdr('가스감지기'),hdr('CCTV'),hdr('PIR'),hdr('웨어러블'),hdr('Vayyar Care'),hdr('TI IWR6843'),hdr('SafeNest')],
   ['사생활 보호 (비영상)','○','×','○','○','○','○','○'],
   ['정지 인체에 대한 증거','×','△','×','○','○','○','○'],
   ['환경 위험 감시','○','×','×','×','×','×','○'],
   ['다중 증거 교차 확인','×','×','×','×','×','×','○'],
   ['무효·결측 데이터 인지','×','×','×','△','확인 불가','확인 불가','○'],
   ['증거 부재 시 판단 보류','×','×','×','×','확인 불가','확인 불가','○'],
   ['통합 실기기 검증 완료','○','○','○','○','○','○','×']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    const mk=(c==='○'||c==='×'||c==='△');
    let col=INK, fill=undefined, fs=12;
    if(mk){ col = c==='×'?RED:(c==='△'?AMBER:GREEN); fs=15; }
    if(c==='확인 불가'){ col=GREY; fs=9.5; }
    if(ci===7 && ri>0) fill={color: c==='×' ? 'FBE9E7' : LBLUE};
    return {text:c,options:{align:(mk||c==='확인 불가')?'center':'left',color:col,bold:mk,fill,fontSize:fs}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[3.03,1.28,1.05,1.00,1.25,1.42,1.55,1.65],rowH:0.28,...TB});
  s.addText([{text:'SafeNest 가 다르게 한 지점은 감지 성능보다 증거를 다루는 정책에 있다. ',options:{bold:true,color:NAVY}},
   {text:'조사한 세 사례 모두 공개 자료에서 무효·결측 인지와 판단 보류 정책을 확인할 수 없었다. 다만 SafeNest 는 4센서 통합 실기기 검증을 완료하지 않았으므로 마지막 행을 그대로 표기한다.',options:{color:INK}}],
   {x:0.55,y:y+3.04,w:12.23,h:0.48,fontFace:F,fontSize:12,lineSpacing:18,valign:'top'});
  const ref=[['Vayyar Care\n(상용 제품)','60 GHz 4D 이미징 레이더 기반 낙상 감지 장치. 카메라·마이크·웨어러블을 쓰지 않고 1대가 약 16 m²를 감시하며 낙상을 3단계로 구분한다. 환경 가스 감시 기능은 제품 설명에서 확인되지 않는다.'],
    ['TI IWR6843\n(상용 부품)','60~64 GHz FMCW 단일칩 mmWave 센서. 재실 감지와 생체신호 검출 레퍼런스 디자인이 공개되어 있다. 센서 단위 부품이므로 환경 센서 융합과 판단 보류 정책은 범위 밖이다.'],
    ['학술 연구\n(arXiv 2403.05634, 2024)','TI mmWave 레이더 3대로 다중 인체 추적과 낙상 감지를 수행하여 정확도 96.3 %를 보고하였다. 단일 모달리티 실험이며 센서 무효·결측 시의 처리 정책은 다루지 않는다.']];
  ref.forEach((r,i)=>{
    const yy=y+3.60+i*0.50;
    s.addText(r[0],{x:0.55,y:yy,w:2.55,h:0.46,fontFace:F,fontSize:10.5,bold:true,color:NAVY,valign:'middle',lineSpacing:13});
    box(s,3.20,yy,9.58,0.46,SOFT,LINE);
    s.addText(r[1],{x:3.38,y:yy,w:9.22,h:0.46,fontFace:F,fontSize:10.5,color:INK,valign:'middle',lineSpacing:14});
  });
  note(s,'○ 충족 · △ 조건부 충족 · × 미충족 · 확인 불가는 공개 자료에서 판정 근거를 찾지 못한 항목이다.  출처 : vayyar.com/care-pages/how, ti.com/tool/IWR6843ISK, arXiv:2403.05634.');
}

/* ============ P16 ============ */
{
  const {s,y} = page(16,'5.3  구현 결과 및 검증 수준');
  const rows=[[hdr('구성요소'),hdr('구현'),hdr('검증 수준'),hdr('증거'),hdr('남은 과제')],
   ['ESP32 4센서 통합 노드','완료','SW 검증','esp32_sensor_node.ino 741줄 · 빌드 RAM 9.9 % / Flash 20.5 %','4센서 동시 수신 실측'],
   ['TCP v1 송·수신 및 유효성 검사','완료','SW 검증','수신기 테스트 13건 통과 · CRC-16 · 범위 재계산 · 이중 TTL','실환경 장시간 수신'],
   ['Risk Engine · fail-closed','완료','SW 검증','위험도 테스트 22건 실행 통과','실입력 기반 HIL'],
   ['mmWave 채널','완료','실기기 검증','9.990 Hz · 1,201 레코드 · 오류 0 · 리플레이 MAE 0.270 rpm','통합 노드 편입'],
   ['CO₂ 채널','완료','실기기 검증(부분)','실측 4세션 · 재측정 결측 0 % · 호기 최고 1,493 ppm','센서 분리 결측 계약'],
   ['Thermal 채널','완료','실기기 E2E','Pi 5 p50 162.70 / p95 173.90 ms · 유효 97.8 % · fail-closed 6종 통과','정본 노드 경유 검증'],
   ['Web · LCD · 부저 · 외함','완료','SW 검증 + 실물','상태 6종 표시·경보 확인 · 하우징 2종 출력·조립 완료','실센서 구동 화면'],
   ['4센서 통합 HIL','미착수','미검증','해당 없음','최우선 과제']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    let col=INK,bold=false;
    if(ci===2){ if(c.indexOf('실기기')>=0||c.indexOf('실물')>=0){col=GREEN;bold=true;} else if(c==='미검증'){col=RED;bold=true;} else {col=BLUE;bold=true;} }
    if(ci===1 && c==='미착수'){ col=RED; bold=true; }
    return {text:c,options:{color:col,bold,align:(ci===1||ci===2)?'center':'left'}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[2.72,0.92,1.48,4.51,2.60],rowH:0.25,...TB,fontSize:10});
  box(s,0.55,y+2.76,12.23,0.56,'FDF3E3',AMBER);
  s.addText('테스트 수치의 의미',{x:0.78,y:y+2.80,w:2.6,h:0.22,fontFace:F,fontSize:11,bold:true,color:'9A5B0B'});
  s.addText('하드웨어 없이 실행 가능한 테스트를 직접 실행하여 57건 통과, 2건 실패(데이터 파일 부재)하였다. 저장소의 테스트 함수 1,483개는 소스에 정의된 개수이며 실행·통과 건수와 다르다.',
    {x:0.78,y:y+3.00,w:11.77,h:0.26,fontFace:F,fontSize:10.5,color:INK,valign:'top'});
  s.addImage({ path:A+'/hw_product_full_crop.jpg', x:0.55, y:y+3.38, w:3.08, h:1.40 });
  s.addShape(pptx.ShapeType.rect,{x:0.55,y:y+3.38,w:3.08,h:1.40,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 3] 완성품. 좌측 표시부, 우측 센서 노드. 하우징 2종은 자체 설계 STL 출력물이다.',
    {x:0.55,y:y+4.84,w:3.08,h:0.62,fontFace:F,fontSize:9,color:GREY,lineSpacing:12,valign:'top'});
  const lcds=[['ui_lcd_2_normal_occupied.jpg','안전 · 재실'],
              ['ui_lcd_3_caution.jpg','주의 · CO₂ 높음'],
              ['ui_lcd_4_danger.jpg','위험 · 호흡 이상'],
              ['ui_lcd_5_emergency.jpg','긴급 · 복합 위험']];
  lcds.forEach((v,i)=>{
    const x=4.09+i*2.19;
    s.addImage({ path:A+'/'+v[0], x, y:y+3.38, w:2.06, h:1.20 });
    s.addShape(pptx.ShapeType.rect,{x,y:y+3.38,w:2.06,h:1.20,fill:{type:'none'},line:{color:LINE,width:1}});
    s.addText(v[1],{x,y:y+4.62,w:2.06,h:0.22,fontFace:F,fontSize:10.5,bold:true,color:NAVY,align:'center'});
  });
  s.addText('[그림 4] 위험도 등급별 표시·경보 화면. 주의는 화면 경고, 위험부터는 부저 경보가 함께 출력된다. 화면 값은 표시 계층 검증용 시나리오 입력이며 실센서 측정값이 아니다.',
    {x:4.09,y:y+4.86,w:8.69,h:0.44,fontFace:F,fontSize:9,color:GREY,align:'center',lineSpacing:12,valign:'top'});
  note(s,'검증 수준 : SW 검증은 소프트웨어 테스트 통과, 실기기 검증은 실제 센서·보드에서 확인, 실기기 E2E 는 실센서부터 추론까지 관통, 통합 HIL 은 4센서 동시 실기기 검증(미완)을 뜻한다.');
}

/* ============ P17 ============ */
{
  const {s,y} = page(17,'6.1  적용 분야 및 기대효과');
  sub(s,0.55,y,'1차 적용 : 밀폐공간 무인 감시');
  const main=['맨홀·정화조·집수정 등 산업안전보건법 시행규칙 별표18이 정한 밀폐공간',
    '감시인 상시 배치가 어려운 소규모 사업장의 보조 감시 수단',
    '공기질(CO₂)과 사람의 상태를 함께 확인하여 가스 감지기 단독 운용의 공백을 메운다',
    '카메라를 쓰지 않으므로 작업자 사생활 문제를 설계 단계에서 줄인다'];
  main.forEach((m,i)=>{
    s.addText([{text:'· ',options:{bold:true,color:BLUE}},{text:m,options:{color:INK}}],
      {x:0.58,y:y+0.38+i*0.44,w:6.00,h:0.42,fontFace:F,fontSize:12,valign:'top',lineSpacing:16});
  });
  sub(s,0.55,y+2.24,'확장 적용과 실측 감지 특성의 대응');
  const ext=[['통학차량 잔류 감지','좌석까지의 거리가 0.6~0.9 m 구간에 해당한다. 해당 구간의 재실 검출률은 리플레이 기준 1.000 이다.',GREEN],
    ['창고·냉동·양생 공간','작업자 고립 감지와 환경 악화 추세를 동시에 관측한다. 1.2 m 이상에서는 검출률이 0.814로 낮아지므로 노드 배치 간격을 좁혀야 한다.',AMBER],
    ['다중 노드 확장','1.5 m 에서는 lock loss 로 유효 창이 0이었다. 따라서 대형 공간은 단일 노드를 키우는 대신 노드를 분산 배치하여 대응한다.',AMBER]];
  ext.forEach((e,i)=>{
    const yy=y+2.62+i*0.60;
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:yy,w:0.06,h:0.56,fill:{color:e[2]}});
    s.addText(e[0],{x:0.72,y:yy,w:2.10,h:0.56,fontFace:F,fontSize:11.5,bold:true,color:NAVY,valign:'middle',lineSpacing:15});
    s.addText(e[1],{x:2.90,y:yy,w:3.68,h:0.56,fontFace:F,fontSize:10.5,color:INK,valign:'middle',lineSpacing:14});
  });
  sub(s,0.55,y+4.44,'공간 식별 체계');
  s.addImage({path:A+'/qr_confined.png',x:0.55,y:y+4.80,w:0.76,h:0.76});
  s.addText('QR 로 공간을 식별한다. 관제 웹에 밀폐공간 A-01, 통학차량 B-02, 창고 C-03 등록.',
    {x:1.44,y:y+4.80,w:5.14,h:0.76,fontFace:F,fontSize:10,color:INK,valign:'middle',lineSpacing:14});
  s.addImage({ path:A+'/ui_web.png', x:6.85, y:y+0.04, w:5.93, h:3.51 });
  s.addShape(pptx.ShapeType.rect,{x:6.85,y:y+0.04,w:5.93,h:3.51,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 5] Express 5 관제 웹. 공간 단위 상태 조회와 다중 노드 관제로의 확장 근거다. 표시 계층 구현 결과이며 화면 값은 시나리오 입력이다.',
    {x:6.85,y:y+3.60,w:5.93,h:0.44,fontFace:F,fontSize:9.5,color:GREY,lineSpacing:13,valign:'top'});
  box(s,6.85,y+4.14,5.93,1.50,'FDF3E3',AMBER);
  s.addText('기대효과 서술의 범위',{x:7.05,y:y+4.20,w:4,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:'9A5B0B'});
  s.addText('확장 시나리오는 동일한 노드 구조로 대응 가능하다는 설계 판단과 리플레이 실측 감지 특성에 근거한다. 현장 파일럿과 정량 효과, 시장 규모는 아직 검증하지 않았다. 매출·판매가·시장 점유 수치는 제시하지 않으며, 부품 단가도 공개 출처로 전 항목을 확인하기 전까지 기재하지 않는다.',
    {x:7.05,y:y+4.44,w:5.53,h:1.14,fontFace:F,fontSize:10.5,color:INK,lineSpacing:16,valign:'top'});
  note(s,'적용 근거 : 산업안전보건법 시행규칙 별표18 밀폐공간의 범위. 감지 거리 근거 : devices/mmwave/validation_results/replay_v5/benchmark_summary.csv.');
}

/* ============ P18 ============ */
{
  const {s,y} = page(18,'6.2  발전 가능성 및 외함 설계');
  sub(s,0.55,y,'단계별 진행 상황');
  const road=[['1단계','채널별 실기기 검증\n+ SW 검증','done'],
    ['2단계','하우징 출력·조립\n완제품 형상 확보','done'],
    ['3단계','4센서 통합 HIL\n실입력 → Risk → 경보','next'],
    ['4단계','현장 데이터 수집\n임계값·보정 확정','todo'],
    ['5단계','다중 노드 확장\n무선 관제','todo'],
    ['6단계','인증·현장 평가','todo']];
  road.forEach((r,i)=>{
    const x=0.55+i*2.06;
    const c = r[2]==='done'?GREEN:(r[2]==='next'?AMBER:GREY);
    s.addShape(pptx.ShapeType.ellipse,{x:x+0.72,y:y+0.38,w:0.46,h:0.46,fill:{color:c},line:{color:c}});
    s.addText(r[2]==='done'?'✓':String(i+1),{x:x+0.72,y:y+0.38,w:0.46,h:0.46,fontFace:F,fontSize:14,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    if(i<5) s.addShape(pptx.ShapeType.line,{x:x+1.20,y:y+0.61,w:1.56,h:0,line:{color:LINE,width:2}});
    box(s,x,y+0.94,1.90,1.00,r[2]==='done'?'EAF5EF':(r[2]==='next'?'FDF3E3':SOFT),c);
    s.addText(r[0],{x,y:y+1.00,w:1.90,h:0.26,fontFace:F,fontSize:11.5,bold:true,color:NAVY,align:'center'});
    s.addText(r[1],{x:x+0.08,y:y+1.26,w:1.74,h:0.62,fontFace:F,fontSize:10,color:INK,align:'center',lineSpacing:13});
  });
  sub(s,0.55,y+2.12,'설계에서 실물까지');
  const imgs=[[A+'/3d_sensor_housing_front_openings.png','[그림 6] 센서 하우징 전면 개구부 설계'],
              [A+'/3d_lcd_housing_front.png','[그림 7] LCD·부저 하우징 전면 설계']];
  imgs.forEach((im,i)=>{
    const x=0.55+i*3.05;
    s.addImage({path:im[0],x,y:y+2.50,w:2.86,h:1.62});
    s.addShape(pptx.ShapeType.rect,{x,y:y+2.50,w:2.86,h:1.62,fill:{type:'none'},line:{color:LINE,width:1}});
    cap(s,x,y+4.16,2.86,im[1]);
  });
  s.addText('▶',{x:6.66,y:y+3.20,w:0.30,h:0.30,fontFace:F,fontSize:16,color:BLUE,align:'center'});
  s.addImage({ path:A+'/hw_product_emergency_crop.jpg', x:7.06, y:y+2.50, w:5.72, h:2.60 });
  s.addShape(pptx.ShapeType.rect,{x:7.06,y:y+2.50,w:5.72,h:2.60,fill:{type:'none'},line:{color:LINE,width:1}});
  cap(s,7.06,y+5.14,5.72,'[그림 8] FDM 출력·조립을 마친 실물. 긴급 등급 표시 상태이며 화면 값은 시나리오 입력이다.');
  s.addText('센서 하우징 137×80×60 mm (벽 3 mm) · LCD·부저 하우징 240×140 mm · 슬라이딩 슬롯 3.5 mm · 편측 유격 0.25 mm. STL 4종과 설계사양 2종을 전달하였고 출력·조립을 완료하였다. 장시간 체결 강도와 발열 특성은 아직 확인하지 않았다.',
    {x:0.55,y:y+4.52,w:6.05,h:0.98,fontFace:F,fontSize:11,color:INK,lineSpacing:16,valign:'top'});
  note(s,'CAD 설계와 STL 출력물 모두 팀 자체 산출물이다.', 6.66);
}

/* ============ P19 ============ */
{
  const {s,y} = page(19,'7.1  개발 일정 및 주요 설계 변경');
  sub(s,0.55,y,'실제 수행 일정');
  const tl=[['7월','요구사항 정의 · 시스템 설계 · 부품 확보 · 개발환경 구축 · 센서별 드라이버 착수'],
    ['8/01','mmWave 장시간 실측. 빈 공간 30분 / 재실 31분 원시 로그 확보'],
    ['8/02–8/03','저장소 통합 및 기기·책임 영역 재편 · CODEOWNERS 정의 · 회귀 테스트'],
    ['8/08','mmWave 라이브 검증(9.990 Hz, 오류 0) · 실측 로그 리플레이 벤치마크 12종'],
    ['8/11','Thermal-44 실기기 E2E 검증 · fail-closed 6종 · Pi 5 지연 실측'],
    ['8/12','SCD40 실기기 4세션 측정 · ESP32 → Pi TCP 실경로 확인 · 검증 리포트 작성'],
    ['8/16–8/21','mmWave 물리 측정 정합 감사 · 패키징 시점 개발 스냅샷(3f22fb1) 확정'],
    ['8/23','하우징 STL 출력·조립 완료 · 표시·경보 계층 상태 6종 확인'],
    ['이후','4센서 통합 HIL · 시연동영상 촬영 (미완료)']];
  tl.forEach((t,i)=>{
    const yy=y+0.36+i*0.36;
    const last = i===tl.length-1;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.35,h:0.36,fill:{color:last?'FBE9E7':LBLUE},line:{color:last?RED:BLUE},rectRadius:0.06});
    s.addText(t[0],{x:0.55,y:yy,w:1.35,h:0.36,fontFace:F,fontSize:11,bold:true,color:last?RED:BLUE,align:'center',valign:'middle'});
    s.addText(t[1],{x:2.05,y:yy,w:10.7,h:0.36,fontFace:F,fontSize:12.5,color:last?RED:INK,valign:'middle',bold:last});
  });
  sub(s,0.55,y+3.78,'개발 과정에서 내린 주요 설계 변경');
  const dec=[['MCU 교체','XIAO ESP32-C6 → ESP32 DevKit V1','GPIO 자원 부족으로 열화상 RESET 제어가 불가능해 자동 복구 요구사항을 충족할 수 없었다.'],
    ['열화상 전송 구조','전 프레임 스트리밍 → 송신측 요약','9,952 B 패킷을 초당 약 6.25회 보내면서 1초 telemetry 주기가 무너졌다.'],
    ['모델 배포 통제','mmWave v0.1.0 배포 차단','재현 검증에서 클래스 붕괴를 확인하여 검증 실패 모델을 안전 경로에 올리지 않기로 하였다.']];
  dec.forEach((d,i)=>{
    const x=0.55+i*4.13;
    box(s,x,y+4.14,3.86,0.98,SOFT,AMBER);
    s.addText(d[0],{x:x+0.14,y:y+4.19,w:3.58,h:0.24,fontFace:F,fontSize:11.5,bold:true,color:'9A5B0B'});
    s.addText(d[1],{x:x+0.14,y:y+4.44,w:3.58,h:0.24,fontFace:F,fontSize:11,bold:true,color:NAVY});
    s.addText(d[2],{x:x+0.14,y:y+4.69,w:3.58,h:0.40,fontFace:F,fontSize:10,color:INK,lineSpacing:14,valign:'top'});
  });
  note(s,'일정은 저장소 커밋 이력과 검증 문서의 실제 일자를 기준으로 작성하였으며, 계획서의 예정 간트를 그대로 옮기지 않았다.');
}

/* ============ P20 ============ */
{
  const {s,y} = page(20,'7.2  업무 분장 및 협업 구조');
  const team=[
   ['김진수','팀장','mmWave 펌웨어·어댑터·실측, 저장소 구조 통합, 문서 총괄','devices/mmwave/ · docs/ · 저장소 전체 기본 리뷰어','MR60 실측 로그 30분·31분, 라이브 검증(9.990 Hz), 리플레이 벤치 12종'],
   ['유승하','팀원','CO₂(SCD40) 연동·실측, ESP32 4센서 노드 펌웨어, Pi LCD·부저 서버, 회로','devices/co2/ · devices/esp32_node/ · integration/','esp32_sensor_node.ino(741줄), CO₂ 실측 4세션·검증 리포트, TCP v1 송·수신'],
   ['김태균','팀원','Thermal-44 드라이버·프레임 파서·전처리, 열화상 온디바이스 AI 검증','devices/thermal/ · docs/thermal/','실기기 E2E 관통, fail-closed 6종, Pi 5 지연 실측(p95 173.9 ms)'],
   ['한준우','팀원','데이터셋 출처·분할, 모델 학습·비교·재현, Pi AI 준비, 위험 판단 연계','ondevice_ai/ · shared/contracts/','모델 3종 매니페스트, 재현 검증·클래스 붕괴 발견 및 배포 차단'],
   ['강유나','팀원','PIR 어댑터, 3D 하우징 CAD 설계 및 출력, LCD·Web 초기 골격','devices/pir/ · hardware/3d_models/','STL 4종 + 설계사양 2종, 하우징 출력·조립, PIR 어댑터, LCD 초기 서버']];
  const rows=[[hdr('성명'),hdr('구분'),hdr('담당 업무'),hdr('책임 영역 (CODEOWNERS)'),hdr('주요 산출물')]];
  team.forEach(t=>rows.push(t));
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{bold:ci===0,align:ci<=1?'center':'left'}}:c)),
    {x:0.55,y:y+0.04,w:12.23,colW:[1.05,0.80,3.35,3.08,3.95],rowH:0.48,...TB,fontSize:10.5});
  sub(s,0.55,y+3.16,'담당 경계를 고정한 협업 인터페이스');
  const ifc=[['센서 계약','shared/contracts/base_sensor.py','모든 센서 담당자 ↔ AI 담당자'],
    ['텔레메트리 스키마','safenest.telemetry.v1 (valid 블록 포함)','ESP32 담당 ↔ 수신 서버 담당'],
    ['패킷 규격','SafeNest TCP protocol v1 (16 B 헤더)','ESP32 담당 ↔ Pi 수신 담당'],
    ['추론 결과 계약','InferenceResult / SensorState','센서 담당 ↔ 위험도 담당'],
    ['위험도 출력','SafeNestRiskOutput (schema 5.0)','위험도 담당 ↔ 표시·경보 담당']];
  ifc.forEach((f,i)=>{
    const yy=y+3.52+i*0.32;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:2.30,h:0.30,fill:{color:LBLUE},line:{color:BLUE},rectRadius:0.05});
    s.addText(f[0],{x:0.55,y:yy,w:2.30,h:0.30,fontFace:F,fontSize:11,bold:true,color:BLUE,align:'center',valign:'middle'});
    s.addText(f[1],{x:3.05,y:yy,w:4.80,h:0.30,fontFace:M,fontSize:10,color:INK,valign:'middle'});
    s.addText(f[2],{x:8.05,y:yy,w:4.73,h:0.30,fontFace:F,fontSize:11,color:GREY,valign:'middle'});
  });
  note(s,'담당 표기는 저장소 CODEOWNERS 와 실제 산출물로 확인한 범위만 기재하였으며, 기여도를 인위적으로 균등화하지 않았다.');
}

pptx.writeFile({ fileName: OUT + '/2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx' })
  .then(f => console.log('WROTE:', f));
