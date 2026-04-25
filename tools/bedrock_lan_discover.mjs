import dgram from "node:dgram";
import crypto from "node:crypto";

const MAGIC = Buffer.from("00ffff00fefefefefdfdfdfd12345678", "hex");
const host = process.argv[2] || "255.255.255.255";
const ports = (process.env.PORTS || "19132,19133").split(",").map(Number);
const timeoutMs = Number(process.env.TIMEOUT_MS || 12000);

const targets = new Map();

function addTarget(address, port) {
  targets.set(`${address}:${port}`, { address, port });
}

for (const port of ports) {
  addTarget(host, port);
  addTarget("255.255.255.255", port);

  const pieces = host.split(".");
  if (pieces.length === 4) {
    pieces[3] = "255";
    addTarget(pieces.join("."), port);
  }
}

function makePingPacket() {
  const packet = Buffer.alloc(33);
  packet[0] = 0x01; // RakNet unconnected ping
  packet.writeBigUInt64BE(BigInt(Date.now()), 1);
  MAGIC.copy(packet, 9);
  crypto.randomBytes(8).copy(packet, 25);
  return packet;
}

const socket = dgram.createSocket({ type: "udp4", reuseAddr: true });
const seen = new Set();

socket.on("message", (msg, rinfo) => {
  if (msg[0] !== 0x1c) {
    console.log(`[ignored] packet type 0x${msg[0].toString(16)} from ${rinfo.address}:${rinfo.port}`);
    return;
  }

  if (msg.length < 35) {
    console.log(`[ignored] short pong from ${rinfo.address}:${rinfo.port}`);
    return;
  }

  const length = msg.readUInt16BE(33);
  const motd = msg.subarray(35, 35 + length).toString("utf8");
  const parts = motd.split(";");

  const [
    edition,
    motd1,
    protocol,
    version,
    players,
    maxPlayers,
    serverGuid,
    worldName,
    gameMode,
    gameModeId,
    port4,
    port6,
  ] = parts;

  const key = `${rinfo.address}:${rinfo.port}:${motd}`;
  if (seen.has(key)) return;
  seen.add(key);

  console.log("");
  console.log("FOUND BEDROCK LAN RESPONSE");
  console.log(`From: ${rinfo.address}:${rinfo.port}`);
  console.log(`Edition: ${edition}`);
  console.log(`MOTD: ${motd1}`);
  console.log(`World name: ${worldName}`);
  console.log(`Version: ${version}`);
  console.log(`Protocol: ${protocol}`);
  console.log(`Players: ${players}/${maxPlayers}`);
  console.log(`Game mode: ${gameMode} (${gameModeId})`);
  console.log(`Reported IPv4 port: ${port4}`);
  console.log(`Reported IPv6 port: ${port6}`);
  console.log(`Raw: ${motd}`);
});

socket.on("error", (err) => {
  console.error("UDP discovery error:", err);
  process.exit(1);
});

socket.bind(0, () => {
  socket.setBroadcast(true);

  console.log("Sending Bedrock LAN discovery pings to:");
  for (const target of targets.values()) {
    console.log(`- ${target.address}:${target.port}`);
  }

  const sendAll = () => {
    const packet = makePingPacket();

    for (const target of targets.values()) {
      socket.send(packet, target.port, target.address);
    }
  };

  sendAll();
  const interval = setInterval(sendAll, 1000);

  setTimeout(() => {
    clearInterval(interval);

    if (seen.size === 0) {
      console.log("");
      console.log("No Bedrock LAN responses found.");
      console.log("That means the Mac is not seeing the PlayStation-hosted world over direct LAN discovery.");
    }

    socket.close();
  }, timeoutMs);
});
