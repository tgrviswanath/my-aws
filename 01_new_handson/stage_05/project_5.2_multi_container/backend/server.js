/**
 * server.js — Express backend API
 * Connects to MySQL and Redis
 */

const express = require('express');
const mysql   = require('mysql2/promise');
const redis   = require('redis');

const app  = express();
const PORT = process.env.PORT || 4000;

app.use(express.json());

// ─── Database Connection ──────────────────────────────────────────────────────

let db;
async function connectDB() {
  db = await mysql.createPool({
    host:     process.env.DB_HOST,
    port:     parseInt(process.env.DB_PORT || '3306'),
    database: process.env.DB_NAME,
    user:     process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    waitForConnections: true,
    connectionLimit:    10,
  });
  console.log('Connected to MySQL');
}

// ─── Redis Connection ─────────────────────────────────────────────────────────

let cache;
async function connectRedis() {
  cache = redis.createClient({
    socket:   { host: process.env.REDIS_HOST, port: parseInt(process.env.REDIS_PORT || '6379') },
    password: process.env.REDIS_PASSWORD,
  });
  cache.on('error', (err) => console.error('Redis error:', err));
  await cache.connect();
  console.log('Connected to Redis');
}

// ─── Routes ───────────────────────────────────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'backend', timestamp: new Date().toISOString() });
});

app.get('/items', async (req, res) => {
  try {
    // Try cache first
    const cached = await cache.get('items:all');
    if (cached) {
      return res.json({ items: JSON.parse(cached), source: 'cache' });
    }

    const [rows] = await db.execute('SELECT * FROM items ORDER BY created_at DESC');

    // Cache for 60 seconds
    await cache.setEx('items:all', 60, JSON.stringify(rows));

    res.json({ items: rows, source: 'database' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

app.post('/items', async (req, res) => {
  const { name, description } = req.body;
  if (!name) return res.status(400).json({ error: 'name is required' });

  try {
    const id = require('crypto').randomUUID();
    await db.execute(
      'INSERT INTO items (id, name, description) VALUES (?, ?, ?)',
      [id, name, description || '']
    );

    // Invalidate cache
    await cache.del('items:all');

    res.status(201).json({ id, name, description });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error' });
  }
});

// ─── Start ────────────────────────────────────────────────────────────────────

async function start() {
  await connectDB();
  await connectRedis();
  app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));
}

start().catch(console.error);
