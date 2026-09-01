"use strict";
const net = require("net");
const host = process.env.RPI_SENSOR_HOST || "127.0.0.1";
const port = Number(process.env.RPI_SENSOR_PORT || 9000);
let packetSequence=0, thermalSequence=0, telemetrySequence=0, phase=0;
const socket=net.createConnection({host,port},()=>{console.log(`ESP32 protocol simulator → ${host}:${port}`);sendAll();});
socket.on("error",error=>{console.error(error.message);process.exitCode=1;});
function packet(type, sequence, payload){const header=Buffer.alloc(16);header.write("SNST",0,"ascii");header.writeUInt8(1,4);header.writeUInt8(type,5);header.writeUInt16BE(0,6);header.writeUInt32BE(sequence,8);header.writeUInt32BE(payload.length,12);return Buffer.concat([header,payload]);}
function telemetry(){phase+=.22;const payload=Buffer.from(JSON.stringify({schema:"safenest.telemetry.v1",device_id:"esp32-01",seq:++telemetrySequence,uptime_ms:Date.now()%4294967295,resp_rate_bpm:Number((16+Math.sin(phase)*1.5).toFixed(2)),heart_rate_bpm:Number((72+Math.sin(phase*.7)*4).toFixed(2)),co2_ppm:Math.round(820+Math.sin(phase*.4)*80),pir_motion:true,valid:{respiration:true,heart:true,co2:true}}));socket.write(packet(1,++packetSequence,payload));}
function thermal(){const width=80,height=62,sequence=++thermalSequence,payload=Buffer.alloc(16+width*height*2);payload.writeUInt16BE(width,0);payload.writeUInt16BE(height,2);payload.writeUInt32BE(sequence,4);payload.writeUInt32BE(Date.now()%4294967295,8);let min=65535,max=0;for(let y=0;y<height;y++)for(let x=0;x<width;x++){const dx=(x-40)/18,dy=(y-31)/24,body=Math.max(0,1-(dx*dx+dy*dy)),hot=Math.max(0,1-((x-47)**2+(y-18)**2)/70),c=24+body*10+hot*3+Math.sin((x+y+phase*8)/8)*.25,raw=Math.round((c+273.15)*10),i=y*width+x;payload.writeUInt16BE(raw,16+i*2);min=Math.min(min,raw);max=Math.max(max,raw);}payload.writeUInt16BE(min,12);payload.writeUInt16BE(max,14);socket.write(packet(2,sequence,payload));}
function sendAll(){telemetry();thermal();setInterval(telemetry,1000);setInterval(thermal,250);}
