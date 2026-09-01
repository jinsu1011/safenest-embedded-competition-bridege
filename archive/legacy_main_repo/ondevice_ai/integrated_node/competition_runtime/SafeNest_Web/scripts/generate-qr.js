"use strict";
const QRCode = require("qrcode");
const fs = require("fs");
const path = require("path");

loadEnv(path.join(__dirname, "..", ".env"));
const baseUrl = process.env.PUBLIC_BASE_URL || "http://localhost:3000";
const output = path.join(__dirname, "..", "qr-codes");
const samples = [
  ["A01", "밀폐공간_A-01"],
  ["B02", "통학차량_B-02"],
  ["C03", "창고_C-03"]
];

(async () => {
  fs.mkdirSync(output, { recursive:true });
  for (const [id, name] of samples) {
    const url = `${baseUrl}/guest/dashboard/${id}`;
    const target = path.join(output, `${name}_${id}`);
    await QRCode.toFile(`${target}.png`, url, { width:600, margin:3, errorCorrectionLevel:"H" });
    await QRCode.toFile(`${target}.svg`, url, { type:"svg", width:600, margin:3, errorCorrectionLevel:"H" });
  }
  console.log(`QR files created: ${output}`);
})().catch(error => { console.error(error); process.exitCode=1; });

function loadEnv(file) {
  try {
    for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
      const match = line.match(/^([^#=]+)=(.*)$/);
      if (match && process.env[match[1]] === undefined) process.env[match[1]] = match[2];
    }
  } catch {}
}
