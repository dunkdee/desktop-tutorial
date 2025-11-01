const crypto = require('crypto');
const fetch = (...args) => import('node-fetch').then(({default: f}) => f(...args));
function cors(){ return {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,X-Agent-HMAC,X-Source',
  'Access-Control-Allow-Methods': 'POST,OPTIONS'
}; }
exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: cors() };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: cors(), body: 'Method not allowed' };
  try {
    const bodyText = event.body || '{}';
    const secret = process.env.AGENT_HMAC_SECRET || '';
    const hmac = crypto.createHmac('sha256', secret).update(bodyText).digest('hex');
    const base = (process.env.N8N_WEBHOOK_BASE || '').replace(/\/$/, '');
    const url = `${base}/webhook/clean2`;
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Agent-HMAC': hmac, 'X-Source': 'site' },
      body: bodyText
    });
    const text = await r.text();
    return { statusCode: r.ok ? 200 : r.status, headers: cors(), body: text };
  } catch (e) {
    return { statusCode: 500, headers: cors(), body: JSON.stringify({ error: String(e) }) };
  }
};
